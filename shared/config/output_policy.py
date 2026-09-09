"""Published `_test` output-name policy, and the staging exemption.

Contract only: additive, imported by no live entry point, enforces
nothing at runtime. Rationale: docs/architecture-and-test-environment-plan.md.

Side-effect free: pure string logic, no I/O, no client.
"""
from __future__ import annotations

from enum import Enum

from shared.config.environment import Environment


PUBLISHED_TEST_SUFFIX = "_test"


def _as_name(value: object) -> str:
    """Coerce an output name to text.

    Campaign codenames are integers in places (source_allowlist.py:88-93
    builds its patterns around an INTEGER campaign code), so a caller
    passing one is an ordinary mistake, not an exotic input.
    shared/config/environment.py is deliberately total for non-string
    input; this module matches it rather than raising AttributeError
    from inside a name-building call.
    """
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    try:
        return str(value)
    except Exception:  # pragma: no cover - hostile __str__
        return ""


class OutputKind(Enum):
    """Why an output exists, which decides whether the policy applies."""

    #: Durable, consumer-facing output (a Power BI-facing mart, a
    #: campaign result table). Carries the _test suffix in a test run.
    PUBLISHED = "published"

    #: Short-lived staging (external CSV/Drive-backed tables created and
    #: dropped inside one run). EXEMPT from the _test suffix -- see
    #: would_corrupt_segments_parse() for the concrete reason.
    STAGING = "staging"


def resolve_output_name(
    base_name: str, kind: OutputKind, environment: Environment
) -> str:
    """Return the name to use for `base_name` in `environment`.

    Production is always the identity function: this policy must never
    alter a production output name. Only a PUBLISHED output in a TEST
    run is suffixed.

    Anything that is not an Environment member is treated as production,
    which is the fail-safe direction here: the harm this function can do
    is RENAMING a production output, not leaving a test output unmarked.
    The identity check below is `is`, so the string "test" -- which
    parse_environment() accepts elsewhere, making it an easy thing to
    pass -- would otherwise fall through and suffix a production table.
    Same for `kind`: an unrecognised kind is not assumed PUBLISHED.

    PRECONDITION, worth stating because the fail-safe direction depends
    on it: a test run writes to a DIFFERENT project (gate 1,
    environment.py). Returning the unsuffixed name is only safe while
    that holds. If test outputs were ever colocated in the production
    project, this same fallback would let a caller's type slip overwrite
    a production table, and the safe direction would reverse.
    """
    name = _as_name(base_name)
    if not isinstance(environment, Environment) or environment is Environment.PRODUCTION:
        return name
    if kind is not OutputKind.PUBLISHED:
        return name
    if name.endswith(PUBLISHED_TEST_SUFFIX):
        return name
    return f"{name}{PUBLISHED_TEST_SUFFIX}"


def is_published_test_name(name: str) -> bool:
    """True only for a genuine `<something>_test` published name.

    A table literally named "test" does NOT qualify: settings.py:38
    defines TABLE_CAMPAIGN_TEST = "test" as a *production* table name,
    so requiring the underscore-prefixed suffix keeps the two apart --
    "test".endswith("_test") is already False, which is the whole
    mechanism. (An earlier version added `and name != "test"` as a
    second clause; it could never be reached, and reading it suggested
    the suffix check was weaker than it is.)
    """
    return _as_name(name).endswith(PUBLISHED_TEST_SUFFIX)


def published_policy_violation(
    name: str, kind: OutputKind, environment: Environment
) -> str | None:
    """Return why `name` violates the policy, or None if it complies.

    Note the deliberate asymmetry with resolve_output_name(): a value
    that is not an Environment member is treated as a TEST run here, so
    it REPORTS a violation rather than staying silent. Each function
    fails in its own safe direction -- that one must not rename a
    production output, this one must not bless an unmarked test one.
    """
    if isinstance(environment, Environment) and environment is Environment.PRODUCTION:
        return None
    name = _as_name(name)
    if kind is OutputKind.STAGING:
        if name.endswith(PUBLISHED_TEST_SUFFIX):
            return (
                f"staging name {name!r} carries the published "
                f"{PUBLISHED_TEST_SUFFIX!r} suffix; staging is exempt and "
                f"suffixing it breaks the segments control parser"
            )
        return None
    if not is_published_test_name(name):
        return (
            f"published name {name!r} does not end in "
            f"{PUBLISHED_TEST_SUFFIX!r}"
        )
    return None


# --- The staging exemption, stated as executable evidence -------------
#
# projects/segments/scripts/push_to_bq.py:64,67 reads the FINAL
# underscore-delimited token of a staging table name and compares it to
# "controlled":
#
#     control = table_split[-1]
#     if control == "controlled":
#
# Appending "_test" makes that final token "test", so the comparison
# fails and the row is written as served. Suffixing segments staging
# tables would therefore silently mislabel every controlled row.
#
# The boolean is not the only casualty. push_to_bq.py:62 also derives
# the segment name from `" ".join(table_split[2:-2])`, and appending a
# token shifts that slice -- so a SERVED table keeps the right boolean
# while gaining a wrong segment label. Both directions corrupt data;
# only the controlled one is visible as a served/control error.

SEGMENTS_CONTROL_TOKEN = "controlled"


def segments_control_token(staging_table_name: str) -> str:
    """The token push_to_bq.py:64 actually inspects (`table_split[-1]`)."""
    return _as_name(staging_table_name).split("_")[-1]


def segments_label(staging_table_name: str) -> str:
    """The label push_to_bq.py:62 derives (`" ".join(split[2:-2])`)."""
    return " ".join(_as_name(staging_table_name).split("_")[2:-2])


def would_flip_served_control_flag(staging_table_name: str) -> bool:
    """True if suffixing this staging name would flip its served/control
    classification, per push_to_bq.py:64-71.

    Narrow ON PURPOSE, and named for exactly what it measures. It is
    False for a served table -- which is NOT the same as "suffixing that
    table is safe", because the label shifts instead. Use
    would_corrupt_segments_parse() to ask whether suffixing is safe; a
    caller that exempts on this predicate alone will suffix served
    tables and silently mislabel their segments.
    """
    name = _as_name(staging_table_name)
    before = segments_control_token(name) == SEGMENTS_CONTROL_TOKEN
    after = segments_control_token(f"{name}{PUBLISHED_TEST_SUFFIX}") == (
        SEGMENTS_CONTROL_TOKEN
    )
    return before != after


def would_corrupt_segments_parse(staging_table_name: str) -> bool:
    """True if suffixing this staging name would change ANYTHING
    push_to_bq.py derives from it -- the served/control flag (`:64`) or
    the segment label (`:62`). This is the predicate the staging
    exemption rests on, and it is True for served and controlled names
    alike -- but only for names with the arity push_to_bq.py assumes.
    `split[2:-2]` is empty below five tokens, so a degenerate name like
    "183_served" changes nothing measurable and returns False. Real
    staging names are `<code>_<country>_<segment words>_<served|
    controlled>`; a caller handed something shorter has a different
    problem than the suffix."""
    # Both sides are coerced the same way. Suffixing the RAW value while
    # comparing the coerced one makes the two disagree: None became ""
    # on one side and "None_test" on the other, so a value that is not a
    # name at all reported "suffixing this would corrupt the parse".
    name = _as_name(staging_table_name)
    suffixed = f"{name}{PUBLISHED_TEST_SUFFIX}"
    return (
        segments_control_token(name) != segments_control_token(suffixed)
        or segments_label(name) != segments_label(suffixed)
    )


# --- Today's production names, reproduced exactly ---------------------
#
# Each function returns byte-for-byte what production builds today. They
# exist so the tests can prove this policy layer does not drift from the
# live code while nothing imports it.


def reporting_output_table(project: str, dataset_footfall: str, codename, query_name: str) -> str:
    """projects/automation/query_orchestrator.py:380"""
    return f"{project}.{dataset_footfall}.{codename}_{query_name}"


def segments_combined_table(code_name) -> str:
    """projects/segments/scripts/push_to_bq.py:41-42"""
    return f"{code_name}_Segments"


def backend_report_table(code) -> str:
    """projects/segments/scripts/create_be_table.py:32"""
    return f"{code}"


def backend_report_external_table(backend_report) -> str:
    """projects/automation/upload_backend.py:289 (staging, not published)"""
    return f"{backend_report}_new"
