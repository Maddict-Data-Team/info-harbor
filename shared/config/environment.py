"""Deployment-environment settings and the pre-flight refusal gates.

Contract only: additive, imported by no live entry point, enforces
nothing at runtime. Rationale: docs/architecture-and-test-environment-plan.md.

Side-effect free: no I/O and no client, at import time or after.
"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Final, Mapping, Sequence
from urllib.parse import unquote

from shared.config import settings
from shared.config.source_allowlist import ReferenceCategory, classify_reference


ENVIRONMENT_ENV_VAR = "INFO_HARBOR_ENVIRONMENT"


class Environment(Enum):
    """The only two environments this contract recognises.

    There is deliberately no third "unknown"/"default" member: an
    unrecognised value must raise, never degrade into a usable
    environment. See parse_environment().
    """

    PRODUCTION = "production"
    TEST = "test"


class EnvironmentConfigurationError(RuntimeError):
    """Raised when the environment cannot be resolved unambiguously."""


def parse_environment(raw: str | None) -> Environment:
    """Resolve an explicit environment name, or raise.

    Fail-closed, matching the precedent ui/app.py:38-47 already sets for
    INFO_HARBOR_FLASK_SECRET_KEY: unset, empty, whitespace-only, or
    unrecognised all raise. There is no fallback and no default -- in
    particular an unset value must never resolve to PRODUCTION (which
    would let an unconfigured run reach real data) nor to TEST (which
    would let a misconfigured run believe it is safely sandboxed).

    Matching is exact after stripping surrounding whitespace and
    lowercasing, so "Production" and " test " resolve, while "prod",
    "tst", and "testing" raise rather than being guessed at.
    """
    if raw is None:
        raise EnvironmentConfigurationError(
            f"{ENVIRONMENT_ENV_VAR} is not set. This contract refuses to "
            f"guess an environment: set it explicitly to one of "
            f"{sorted(e.value for e in Environment)}."
        )

    if not isinstance(raw, str):
        # A caller reading the value out of a config object rather than
        # os.environ can hand over a non-string. It must still fail with
        # THIS module's declared error type: a Phase B caller written as
        # `except EnvironmentConfigurationError: abort()` would not catch
        # an AttributeError from .strip().
        raise EnvironmentConfigurationError(
            f"{ENVIRONMENT_ENV_VAR}={raw!r} is not a string. Set it "
            f"explicitly to one of {sorted(e.value for e in Environment)}."
        )

    normalised = raw.strip().lower()
    if not normalised:
        raise EnvironmentConfigurationError(
            f"{ENVIRONMENT_ENV_VAR} is set but empty. Set it explicitly to "
            f"one of {sorted(e.value for e in Environment)}."
        )

    for environment in Environment:
        if normalised == environment.value:
            return environment

    raise EnvironmentConfigurationError(
        f"{ENVIRONMENT_ENV_VAR}={raw!r} is not a recognised environment. "
        f"Expected exactly one of {sorted(e.value for e in Environment)}; "
        f"near-misses are rejected rather than guessed."
    )


def resolve_environment(environ: Mapping[str, str] | None = None) -> Environment:
    """Read and parse ENVIRONMENT_ENV_VAR from `environ` (default os.environ).

    The environment is read here, when called -- never at import time.
    """
    source = os.environ if environ is None else environ
    return parse_environment(source.get(ENVIRONMENT_ENV_VAR))


# Drive locations that belong to production. Settings records some of
# these as bare folder IDs and others as share URLs wrapping an ID, so
# both forms are normalised to a single canonical folder ID before any
# comparison -- otherwise the same production folder is refused in one
# form and silently accepted in the other.
_PRODUCTION_DRIVE_SETTINGS: tuple[str, ...] = (
    settings.DRIVE_MAIN_FOLDER_ID,
    settings.DRIVE_BACKEND_REPORTS_FOLDER_ID,
    settings.DRIVE_ADOPS_FOLDER_URL,
    settings.LEGACY_CAMPAIGN_TRACKER_DRIVE_FOLDER_URL,
)


#: Path markers Drive puts immediately before a file/folder id.
_DRIVE_ID_MARKERS: Final = ("folders", "d", "file")

#: Characters that separate identifiers in a Drive URL or query string.
_DRIVE_SPLIT: Final = re.compile(r"[/?&=#\s]+")

#: Invisible characters that survive .strip() and would break an
#: exact-token comparison. A paste out of Docs/Sheets or a chat client
#: carries these, and one of them inside a production folder id is
#: enough to make the id unequal to itself -- and so to turn a refusal
#: into an accept.
#:
#: Decided by Unicode CATEGORY, not by an enumerated list. Enumerating
#: loses this race by construction: each list drawn up so far has been
#: missing a neighbour of something already on it (U+206A-206F sit
#: directly beside the covered U+2066-2069). "Cf" is the format-control
#: category -- soft hyphen, Arabic letter mark, the zero-width joiners,
#: every bidi embedding and isolate control, the word joiner, and the
#: BOM -- and the variation selectors, which are "Mn", are added
#: explicitly. Both are unconditionally invisible in an identifier.
_INVISIBLE_RANGES: Final = (
    (0xFE00, 0xFE0F),  # variation selectors
    (0xE0100, 0xE01EF),  # variation selectors supplement
)


def _strip_invisible(text: str) -> str:
    """Remove invisible formatting characters from `text`."""
    return "".join(
        char
        for char in text
        if unicodedata.category(char) != "Cf"
        and not any(low <= ord(char) <= high for low, high in _INVISIBLE_RANGES)
    )


class _UnreadableInput:
    """Stands in for an argument whose own iteration raised.

    Deliberately not a Sequence and not iterable, so every gate reports
    it as a bad argument instead of quietly seeing zero entries.
    """

    __slots__ = ("error",)

    def __init__(self, error: BaseException) -> None:
        self.error = error

    def __repr__(self) -> str:
        return f"<unreadable input: {type(self.error).__name__}: {self.error}>"


#: A plausible Drive folder id: long and opaque. Used to sanity-check the
#: ids derived from settings, so a malformed entry cannot poison the
#: production set with a generic token like "folders" that would then
#: match -- and refuse -- every Drive URL.
_DRIVE_ID_SHAPE: Final = re.compile(r"^[A-Za-z0-9_-]{15,}$")


def _decode_fully(text: str, limit: int = 4) -> str:
    """Percent-decode until stable, so a double-encoded id still
    resolves. Bounded, because decoding is not guaranteed to converge on
    adversarial input."""
    for _ in range(limit):
        decoded = unquote(text)
        if decoded == text:
            break
        text = decoded
    return text


def _as_text(value: object) -> str:
    """Coerce any input to text so validation can refuse it rather than
    raise. A caller that passes an int, None, or an object still gets a
    refusal, never an AttributeError escaping a gate."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return str(value)
    except Exception:  # pragma: no cover - hostile __str__
        return ""


def normalise_drive_folder(location: object) -> str | None:
    """Reduce a Drive folder ID or share URL to its canonical folder ID.

    Handles every shape Drive itself emits: a bare ID,
    `/drive/folders/<id>`, the `/drive/u/0/` variant, `open?id=<id>`,
    `/file/d/<id>/view`, and any of those percent-encoded or carrying a
    trailing slash, query string, or fragment.

    This is the single-value answer, used for reporting and for deriving
    PRODUCTION_DRIVE_FOLDER_IDS from settings.py. It is NOT what gate 4
    decides on: that guesses which token is "the" id, and a shape this
    function does not anticipate reduces to the wrong token. Gate 4 uses
    names_production_drive_folder(), which asks the opposite question --
    does any known production id appear anywhere in the input -- and so
    does not depend on the guess being right.
    """
    text = _strip_invisible(_decode_fully(_as_text(location))).strip()
    if not text:
        return None

    if "/" not in text and "?" not in text and "=" not in text:
        return text

    without_fragment = text.split("#", 1)[0]
    path, _, query = without_fragment.partition("?")

    # open?id=<id> / uc?id=<id>
    for pair in query.split("&"):
        key, sep, value = pair.partition("=")
        if sep and key.strip().lower() == "id" and value.strip():
            return value.strip()

    segments = [segment for segment in path.split("/") if segment]
    for index, segment in enumerate(segments[:-1]):
        if segment.lower() in _DRIVE_ID_MARKERS and segments[index + 1]:
            candidate = segments[index + 1]
            if candidate.lower() not in _DRIVE_ID_MARKERS:
                return candidate

    return segments[-1] if segments else None


def drive_folder_candidates(location: object) -> frozenset[str]:
    """Every token in `location` that could be a Drive folder id.

    Deliberately over-inclusive, and offered for reporting -- "which
    parts of this string did we consider?" -- not for the decision.
    Gate 4 does NOT call this: token splitting only knows the separators
    listed in _DRIVE_SPLIT, so a production id sitting next to a
    separator it does not know (`id:<prod>`, `<prod>,`, `'<prod>'`)
    produces no matching token. names_production_drive_folder() answers
    the membership question by containment instead, which has no such
    blind spot.
    """
    text = _strip_invisible(_decode_fully(_as_text(location))).strip()
    if not text:
        return frozenset()
    tokens = {token for token in _DRIVE_SPLIT.split(text) if token}
    tokens.add(text)
    return frozenset(tokens)


#: Canonical folder IDs for every production Drive location.
PRODUCTION_DRIVE_FOLDER_IDS: frozenset[str] = frozenset(
    folder
    for folder in (normalise_drive_folder(v) for v in _PRODUCTION_DRIVE_SETTINGS)
    if folder and _DRIVE_ID_SHAPE.match(folder)
)

#: Retained for readability in messages/tests: the raw settings values.
PRODUCTION_DRIVE_LOCATIONS: frozenset[str] = frozenset(_PRODUCTION_DRIVE_SETTINGS)

PUBLISHED_TEST_TABLE_SUFFIX = "_test"

#: Projects a test run may write to. Deliberately EMPTY: no test project
#: has been confirmed yet (plan lines 87-91 use a `<GCP_TEST_PROJECT_ID>`
#: placeholder, and "Open decisions before Phase C" item 1 is to confirm
#: it). An empty allowlist means every output project is refused, which
#: is the correct posture until a human names one. Callers pass their own
#: allowlist explicitly; nothing here grants access to any project.
APPROVED_TEST_PROJECTS: frozenset[str] = frozenset()


@dataclass(frozen=True)
class RunRequest:
    """The inputs the five gates are evaluated against.

    Plain data: constructing one performs no I/O and reaches no service.
    `approved_test_projects` defaults to the empty module-level
    allowlist, so a request that omits it is refused rather than
    accidentally permitted.
    """

    environment: Environment
    output_project: str
    published_tables: Sequence[str] = field(default_factory=tuple)
    source_tables: Sequence[str] = field(default_factory=tuple)
    drive_folder: str | None = None
    approved_test_projects: frozenset[str] = APPROVED_TEST_PROJECTS

    def __post_init__(self) -> None:
        """Materialise any one-shot iterable exactly once.

        A generator passed for a table sequence is drained by the first
        validation pass; every later pass then sees ZERO entries, so the
        gates that read it fall silent and the request is ACCEPTED. The
        permissive answer is the later one, which makes the natural
        caller shape -- log the reasons, then ask again whether to abort
        -- fail open on a production table name. Draining it here, once,
        makes repeated evaluation return the same answer.

        Strings are left alone: _as_entries() must still see them as a
        caller mistake and refuse, not silently accept one character per
        table. Anything that cannot be iterated is also left alone, so
        _as_entries() reports it as "not a sequence".

        `approved_test_projects` is included. Draining it fails CLOSED
        rather than open -- the second call sees an empty allowlist and
        refuses -- but an answer that changes between calls is a defect
        in either direction, and the guarantee this method exists to
        provide is that it does not change.
        """
        for name in ("published_tables", "source_tables", "approved_test_projects"):
            value = getattr(self, name)
            if isinstance(value, (str, bytes)) or isinstance(value, Sequence):
                continue
            if isinstance(value, (frozenset, set)):
                continue
            # Whether the object is iterable AT ALL is asked first, and
            # separately. Catching TypeError around tuple(value) cannot
            # tell "not iterable" from "iteration raised TypeError", and
            # the two need opposite handling: the first must be left
            # alone so the gate names it, the second must be replaced --
            # a generator terminated by an exception is closed, so
            # leaving it in place means the gate re-iterates it, sees
            # nothing, and accepts a request whose tables it never
            # examined. Conflating them was itself a fail-open.
            try:
                iter(value)
            except TypeError:
                continue
            except Exception as error:  # pragma: no cover - hostile __iter__
                object.__setattr__(self, name, _UnreadableInput(error))
                continue

            try:
                frozen = tuple(value)
            except Exception as error:
                object.__setattr__(self, name, _UnreadableInput(error))
                continue
            object.__setattr__(self, name, frozen)


def _as_allowlist(value: object) -> frozenset[str]:
    """Coerce an approved-project allowlist to a real set of names.

    A bare `str` is the dangerous case: `"proj" in "ih-test-project"` is
    substring containment, so an unlisted project could satisfy the
    membership test. A string is therefore treated as a ONE-entry
    allowlist, and anything non-iterable becomes empty -- which refuses
    every project, the safe direction.
    """
    if value is None:
        return frozenset()
    if isinstance(value, str):
        return frozenset({value.strip()}) if value.strip() else frozenset()
    try:
        return frozenset(_as_text(item).strip() for item in value if _as_text(item).strip())
    except Exception:
        # Not iterable, or a Sequence/set subclass whose own __iter__
        # raised -- __post_init__ skips those, so this is the only place
        # that sees them. Either way the answer is an empty allowlist,
        # which refuses every project.
        return frozenset()


def _as_entries(value: object, field_name: str) -> tuple[tuple, str | None]:
    """Coerce a table sequence to a tuple of entries.

    Returns (entries, error). A bare `str` is one entry, not a stream of
    characters. A non-iterable is refused by name rather than raising a
    TypeError out of the gate that was meant to stop it.
    """
    if value is None:
        return (), None
    if isinstance(value, str):
        return (value,), None
    if isinstance(value, _UnreadableInput):
        return (), (
            f"{field_name} is not a sequence: reading it raised "
            f"{type(value.error).__name__}: {value.error}"
        )
    try:
        return tuple(value), None
    except Exception as error:
        # Broad on purpose: a Sequence subclass whose __iter__ raises is
        # skipped by __post_init__ and arrives here intact, and a gate
        # must refuse it by name rather than let the exception escape
        # the check that exists to stop it.
        return (), f"{field_name} is not a sequence ({error!r}): {value!r}"


def _published_table_reasons(table: str, output_project: str) -> list[str]:
    """Validate one published-table destination.

    A destination is either a bare table name or a fully qualified
    `project.dataset.table`. Anything else -- two components, four or
    more, or an empty component -- is malformed and refused rather than
    guessed at. A fully qualified name must sit in the same project the
    run writes to, and must never sit in the production project, no
    matter what suffix it carries.
    """
    reasons: list[str] = []
    name = _as_text(table).strip()

    if not name:
        reasons.append("published table name is empty or whitespace")
        return reasons

    parts = name.split(".")
    if len(parts) == 1:
        table_name = parts[0]
    elif len(parts) == 3 and all(part.strip() for part in parts):
        table_project, _dataset, table_name = (part.strip() for part in parts)
        if table_project == settings.PROJECT_ID:
            reasons.append(
                f"published table {name!r} is qualified with the production "
                f"project {settings.PROJECT_ID!r}"
            )
        elif table_project != output_project:
            reasons.append(
                f"published table {name!r} names project {table_project!r}, "
                f"which is not the run's output project {output_project!r}"
            )
    else:
        reasons.append(
            f"published table {name!r} is malformed: expected a bare table "
            f"name or 'project.dataset.table'"
        )
        return reasons

    if not table_name.endswith(PUBLISHED_TEST_TABLE_SUFFIX):
        reasons.append(
            f"published table {name!r} does not end in "
            f"{PUBLISHED_TEST_TABLE_SUFFIX!r}"
        )

    return reasons


def refusal_reasons(request: RunRequest) -> list[str]:
    """Return every reason this run must be refused before any cloud call.

    Implements docs/architecture-and-test-environment-plan.md:98-105
    verbatim. Every gate is evaluated (rather than short-circuiting) so a
    caller sees all problems at once instead of fixing them one round
    trip at a time. An empty list means no gate objected -- it does NOT
    mean the run is authorised; nothing in Phase A authorises a cloud
    run at all.
    """
    reasons: list[str] = []

    # Gate 5 (checked first because it frames the others): the
    # environment must be explicitly TEST. A caller who passes the
    # STRING "test" -- an easy mistake, since parse_environment() accepts
    # exactly that -- must get a refusal, not an AttributeError raised
    # past their `except`.
    if not isinstance(request.environment, Environment):
        reasons.append(
            f"environment {request.environment!r} is not an Environment "
            f"member; pass Environment.TEST, not its name"
        )
    elif request.environment is not Environment.TEST:
        reasons.append(
            f"environment is {request.environment.value!r}, not "
            f"{Environment.TEST.value!r}"
        )

    # Gate 1: the output project must be a named, approved, non-production
    # project. Fail-closed at every step -- an unset, blank, production,
    # or merely-unlisted project is refused, and an absent allowlist
    # refuses everything rather than waving the run through.
    project = _as_text(request.output_project).strip()
    # Coerced to a real set: a bare string would turn the membership
    # test below into substring containment, so "test" would satisfy an
    # allowlist of "ih-test-project" -- the one place in this module
    # where a caller's type mistake could fail OPEN.
    allowlist = _as_allowlist(request.approved_test_projects)
    if not project:
        reasons.append("output project is empty or whitespace")
    elif project == settings.PROJECT_ID:
        reasons.append(
            f"output project is the production project {settings.PROJECT_ID!r}"
        )
    elif not allowlist:
        reasons.append(
            "no approved test-project allowlist is configured, so no output "
            "project can be accepted"
        )
    elif project not in allowlist:
        reasons.append(
            f"output project {project!r} is not on the approved "
            f"test-project allowlist"
        )

    # Gate 2: every published table must carry the _test suffix AND, when
    # it is fully qualified, name the same project the run writes to. A
    # `_test` suffix on a production-qualified destination is exactly the
    # shape that must not slip through.
    published, published_error = _as_entries(request.published_tables, "published_tables")
    if published_error:
        reasons.append(published_error)
    for table in published:
        reasons.extend(_published_table_reasons(table, project))

    # Gate 3: every source table must be an approved production source.
    sources, sources_error = _as_entries(request.source_tables, "source_tables")
    if sources_error:
        reasons.append(sources_error)
    for source in sources:
        if classify_reference(source) is not ReferenceCategory.APPROVED_PRODUCTION_SOURCE:
            reasons.append(f"source table {source!r} is not on the approved allowlist")

    # Gate 4: the run must not name a production Drive location, in ANY
    # shape -- bare id, /folders/<id>, open?id=<id>, /file/d/<id>/view,
    # percent-encoded, or a form nobody has thought of yet. Membership is
    # tested against every token in the input, so an unanticipated URL
    # layout cannot hide a production id behind a trailing word.
    #
    # This gate is the one place where an unreadable value would fail
    # OPEN rather than closed. Every other gate turns a value it cannot
    # read into a refusal -- an empty project is refused, an
    # unclassifiable source is refused -- but "no text to search" here
    # means "no production id found", which is silence. An object with
    # the default repr hides the id in an attribute:
    # `DriveFolder(DRIVE_MAIN_FOLDER_ID)` stringifies to
    # `<...object at 0x...>` and matches nothing. So the type is checked
    # first, and anything that is not a string is refused by name.
    if request.drive_folder is not None and not isinstance(request.drive_folder, str):
        reasons.append(
            f"Drive location is not a string, so it cannot be checked "
            f"against the production folders: {request.drive_folder!r}"
        )
    else:
        matched = names_production_drive_folder(request.drive_folder)
        if matched:
            reasons.append(
                f"Drive location {request.drive_folder!r} names production "
                f"folder {sorted(matched)[0]!r}"
            )

    return reasons


def is_refused(request: RunRequest) -> bool:
    """True when at least one gate objects to this run."""
    return bool(refusal_reasons(request))


def names_production_drive_folder(location: object) -> frozenset[str]:
    """Production folder ids named anywhere in `location`.

    Token membership alone was not enough: a production id sitting next
    to a separator this module does not split on (`id:<id>`, a trailing
    comma, surrounding quotes) survived tokenisation as part of a larger
    token and matched nothing. Drive ids are long, opaque and
    high-entropy, so plain containment over the decoded, invisible-
    stripped text is both stricter and simpler -- and erring toward
    refusal is the safe direction for this gate.
    """
    text = _strip_invisible(_decode_fully(_as_text(location)))
    if not text:
        return frozenset()
    return frozenset(
        folder for folder in PRODUCTION_DRIVE_FOLDER_IDS if folder in text
    )
