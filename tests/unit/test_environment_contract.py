"""Phase A: test-vs-production environment validation.

Contract only -- these modules are additive, imported by no live entry
point, and enforce nothing at runtime. See
docs/architecture-and-test-environment-plan.md.

Structure: for each contract, the positive case, the negative case, and
the boundary where a caller mistake could turn a refusal into an accept.
Where the module is deliberately fail-closed, the test asserts the
refusal rather than merely that nothing raised.

No test here reaches a cloud service, reads credentials, or opens keys/.
"""
from __future__ import annotations

import re

import pytest

from shared.config import settings
from shared.config.environment import (
    APPROVED_TEST_PROJECTS,
    ENVIRONMENT_ENV_VAR,
    Environment,
    EnvironmentConfigurationError,
    PRODUCTION_DRIVE_FOLDER_IDS,
    PRODUCTION_DRIVE_LOCATIONS,
    RunRequest,
    is_refused,
    names_production_drive_folder,
    normalise_drive_folder,
    parse_environment,
    refusal_reasons,
    resolve_environment,
)


APPROVED_SOURCE = f"{settings.PROJECT_ID}.{settings.DATASET_AUTOMATED_HWG}.{settings.TABLE_HOME_GRAPH}"


def _test_project() -> str:
    """A placeholder non-production project id (plan lines 87-91)."""
    return "ih-test-project"


class TestEnvironmentParsingFailsClosed:
    """Mirrors the fail-closed precedent ui/app.py:38-47 already sets:
    unset/empty/unrecognised must raise, never silently resolve."""

    # -- positive
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("test", Environment.TEST),
            ("  test  ", Environment.TEST),
            ("Production", Environment.PRODUCTION),
        ],
    )
    def test_exact_names_resolve_case_and_whitespace_insensitively(self, raw, expected):
        assert parse_environment(raw) is expected

    # -- negative
    @pytest.mark.parametrize("raw", [None, "", "   ", "prod", "testing", "tst", "dev"])
    def test_unset_empty_and_near_misses_all_raise(self, raw):
        """A near-miss must be rejected, not guessed at: resolving "prod"
        to PRODUCTION is how an unconfigured run reaches real data."""
        with pytest.raises(EnvironmentConfigurationError):
            parse_environment(raw)

    def test_the_message_names_the_variable_and_the_valid_values(self):
        with pytest.raises(EnvironmentConfigurationError) as caught:
            parse_environment(None)
        assert ENVIRONMENT_ENV_VAR in str(caught.value)
        assert "test" in str(caught.value)

    # -- boundary
    @pytest.mark.parametrize("raw", [123, b"test", [], object()])
    def test_a_non_string_raises_THIS_module_s_error_type(self, raw):
        """A caller reading the value from a config object rather than
        os.environ can hand over a non-string. `except
        EnvironmentConfigurationError: abort()` must still catch it, so
        an AttributeError from .strip() is not good enough."""
        with pytest.raises(EnvironmentConfigurationError):
            parse_environment(raw)

    def test_there_is_no_third_or_default_environment(self):
        assert {e.value for e in Environment} == {"production", "test"}


class TestResolveEnvironmentReadsTheVariable:
    def test_reads_from_a_supplied_mapping(self):
        assert resolve_environment({ENVIRONMENT_ENV_VAR: "test"}) is Environment.TEST

    def test_missing_key_in_supplied_mapping_raises(self):
        with pytest.raises(EnvironmentConfigurationError):
            resolve_environment({})

    def test_defaults_to_os_environ(self, monkeypatch):
        monkeypatch.setenv(ENVIRONMENT_ENV_VAR, "test")
        assert resolve_environment() is Environment.TEST
        monkeypatch.delenv(ENVIRONMENT_ENV_VAR)
        with pytest.raises(EnvironmentConfigurationError):
            resolve_environment()


class TestTheFiveRefusalGates:
    """docs/architecture-and-test-environment-plan.md:98-105. Each gate
    is asserted on its own so a future change cannot quietly drop one
    while the others keep the suite green."""

    def _clean_request(self, **overrides):
        """A request that satisfies every gate. The approved-test-project
        allowlist is passed EXPLICITLY: the module default is empty, so a
        positive case has to name its project on purpose."""
        base = dict(
            environment=Environment.TEST,
            output_project=_test_project(),
            published_tables=("Campaign_Tracker_test",),
            source_tables=(APPROVED_SOURCE,),
            drive_folder="<TEST_DRIVE_FOLDER_ID>",
            approved_test_projects=frozenset({_test_project()}),
        )
        base.update(overrides)
        return RunRequest(**base)

    # -- positive
    def test_a_fully_compliant_request_draws_no_refusal(self):
        assert refusal_reasons(self._clean_request()) == []
        assert is_refused(self._clean_request()) is False

    # -- negative, one per gate
    def test_gate_1_refuses_the_production_output_project(self):
        request = self._clean_request(output_project=settings.PROJECT_ID)
        assert any("production project" in r for r in refusal_reasons(request))
        assert is_refused(request)

    def test_gate_2_refuses_a_published_table_without_the_test_suffix(self):
        request = self._clean_request(published_tables=("Campaign_Tracker",))
        assert any("_test" in r for r in refusal_reasons(request))

    def test_gate_3_refuses_a_source_that_is_not_on_the_allowlist(self):
        request = self._clean_request(
            source_tables=(f"{settings.PROJECT_ID}.Some_Dataset.some_table",)
        )
        assert any("allowlist" in r for r in refusal_reasons(request))

    def test_gate_3_refuses_a_control_table_offered_as_a_source(self):
        """Campaign_Tracker is written by Automation, so it must never
        pass as a read-only source even though it is a known table."""
        request = self._clean_request(
            source_tables=(
                f"{settings.PROJECT_ID}.{settings.DATASET_METADATA}."
                f"{settings.TABLE_CAMPAIGN_TRACKER}",
            )
        )
        assert any("allowlist" in r for r in refusal_reasons(request))

    def test_gate_4_refuses_a_production_drive_location(self):
        request = self._clean_request(drive_folder=settings.DRIVE_MAIN_FOLDER_ID)
        assert any("production folder" in r for r in refusal_reasons(request))

    def test_gate_5_refuses_a_non_test_environment(self):
        request = self._clean_request(environment=Environment.PRODUCTION)
        assert any("not 'test'" in r for r in refusal_reasons(request))

    # -- boundary
    def test_gate_1_refuses_the_production_project_even_if_it_is_allowlisted(self):
        """The production check runs before the allowlist check, so a
        misconfigured allowlist cannot re-admit maddictdata."""
        request = self._clean_request(
            output_project=settings.PROJECT_ID,
            approved_test_projects=frozenset({settings.PROJECT_ID, _test_project()}),
        )
        assert any("production project" in r for r in refusal_reasons(request))

    def test_gate_1_refuses_when_no_allowlist_is_configured(self):
        """The module-level allowlist ships empty until a human confirms
        a test project, so omitting it must refuse rather than permit."""
        assert APPROVED_TEST_PROJECTS == frozenset()
        request = RunRequest(
            environment=Environment.TEST,
            output_project=_test_project(),
            published_tables=("Campaign_Tracker_test",),
            source_tables=(APPROVED_SOURCE,),
        )
        assert any(
            "no approved test-project allowlist" in r for r in refusal_reasons(request)
        )

    @pytest.mark.parametrize("blank", ["", "   ", "\t"])
    def test_gate_1_refuses_a_blank_output_project(self, blank):
        request = self._clean_request(output_project=blank)
        assert any("empty or whitespace" in r for r in refusal_reasons(request))

    def test_every_gate_reports_independently_rather_than_short_circuiting(self):
        """A caller must see every reason a run was refused, not the
        first one -- otherwise fixing one problem reveals the next."""
        request = RunRequest(
            environment=Environment.PRODUCTION,
            output_project=settings.PROJECT_ID,
            published_tables=("Campaign_Tracker",),
            source_tables=(f"{settings.PROJECT_ID}.Nope.nope",),
            drive_folder=settings.DRIVE_MAIN_FOLDER_ID,
            approved_test_projects=frozenset({_test_project()}),
        )
        assert len(refusal_reasons(request)) >= 5


class TestGateTwoValidatesTheDestinationProject:
    """A `_test` suffix alone is not enough: a fully qualified
    destination must also name the run's own output project, so a
    production-qualified table cannot ride through on its suffix."""

    def _request(self, published, project="ih-test-project"):
        return RunRequest(
            environment=Environment.TEST,
            output_project=project,
            published_tables=(published,),
            approved_test_projects=frozenset({project}),
        )

    # -- positive
    def test_a_correctly_qualified_table_is_accepted(self):
        assert refusal_reasons(self._request("ih-test-project.Metadata.CT_test")) == []

    def test_a_bare_table_name_is_still_accepted(self):
        assert refusal_reasons(self._request("Campaign_Tracker_test")) == []

    # -- negative
    def test_a_production_qualified_table_is_refused_despite_the_suffix(self):
        request = self._request(
            f"{settings.PROJECT_ID}.{settings.DATASET_METADATA}.Campaign_Tracker_test"
        )
        assert any("production project" in r for r in refusal_reasons(request))

    def test_a_table_in_another_non_production_project_is_refused(self):
        request = self._request("some-other-project.Metadata.Campaign_Tracker_test")
        assert any("not the run's output project" in r for r in refusal_reasons(request))

    def test_a_qualified_table_still_needs_the_test_suffix(self):
        request = self._request("ih-test-project.Metadata.Campaign_Tracker")
        assert any("_test" in r for r in refusal_reasons(request))

    # -- boundary
    @pytest.mark.parametrize(
        "malformed",
        [
            "Metadata.Campaign_Tracker_test",
            "a.b.c.d_test",
            "..Campaign_Tracker_test",
            "proj..Campaign_Tracker_test",
            "   ",
        ],
    )
    def test_a_malformed_destination_is_refused_rather_than_guessed_at(self, malformed):
        reasons = refusal_reasons(self._request(malformed))
        assert reasons
        assert any(("malformed" in r) or ("empty or whitespace" in r) for r in reasons)


class TestGateFourRecognisesEveryFormOfAProductionFolder:
    """settings records some Drive locations as bare ids and others as
    share URLs. A folder blocked in one form and waved through in the
    other is the same as not blocking it."""

    def _refused(self, folder):
        request = RunRequest(
            environment=Environment.TEST,
            output_project=_test_project(),
            approved_test_projects=frozenset({_test_project()}),
            drive_folder=folder,
        )
        return any("production folder" in r for r in refusal_reasons(request))

    # -- positive (i.e. correctly allowed)
    def test_a_non_production_folder_is_allowed(self):
        assert not self._refused("1TESTtestTESTtestTESTtest")
        assert not self._refused(
            "https://drive.google.com/drive/folders/1TESTtestTESTtestTEST"
        )

    def test_no_drive_location_is_not_a_refusal(self):
        assert not self._refused(None)

    # -- negative
    @pytest.mark.parametrize(
        "folder",
        [
            # Pinned to settings explicitly, NOT parametrised over the
            # module's own constant -- otherwise deleting an entry from
            # that constant would delete the case that guards it.
            settings.DRIVE_MAIN_FOLDER_ID,
            settings.DRIVE_BACKEND_REPORTS_FOLDER_ID,
            settings.DRIVE_ADOPS_FOLDER_URL,
            settings.LEGACY_CAMPAIGN_TRACKER_DRIVE_FOLDER_URL,
        ],
    )
    def test_every_configured_production_location_is_refused_as_configured(self, folder):
        assert self._refused(folder)

    @pytest.mark.parametrize(
        "template",
        [
            "{f}",
            "https://drive.google.com/drive/folders/{f}",
            "https://drive.google.com/drive/u/0/folders/{f}",
            "https://drive.google.com/open?id={f}",
            "https://drive.google.com/file/d/{f}/view",
            "id:{f}",
            "'{f}'",
        ],
    )
    def test_a_production_folder_is_refused_in_every_shape_drive_emits(self, template):
        """`open?id=` and `/file/d/<id>/view` are formats Drive itself
        produces, and `id:<id>` is how one gets pasted into a ticket."""
        assert self._refused(template.format(f=settings.DRIVE_MAIN_FOLDER_ID))

    # -- boundary
    def test_percent_encoding_does_not_hide_a_production_folder(self):
        folder = settings.DRIVE_MAIN_FOLDER_ID
        assert self._refused(
            "https://drive.google.com/drive/folders/" + folder.replace("-", "%2D")
        )

    def test_an_invisible_character_does_not_hide_a_production_folder(self):
        """A paste out of Docs/Sheets carries zero-width and bidi
        characters, and one of them inside an id is enough to make the
        id unequal to itself."""
        folder = settings.DRIVE_MAIN_FOLDER_ID
        assert self._refused(folder[:10] + "​" + folder[10:])

    def test_a_non_string_drive_location_is_refused_not_ignored(self):
        """This gate asks "does a production id appear in this text?", so
        a value it cannot read answers "no" -- silence, not a refusal.
        An object holding the id in an attribute stringifies to
        `<... object at 0x...>` and would otherwise be ACCEPTED."""

        class DriveFolder:
            def __init__(self, folder_id):
                self.folder_id = folder_id

        request = RunRequest(
            environment=Environment.TEST,
            output_project=_test_project(),
            approved_test_projects=frozenset({_test_project()}),
            drive_folder=DriveFolder(settings.DRIVE_MAIN_FOLDER_ID),
        )
        assert any("not a string" in r for r in refusal_reasons(request))

    def test_the_production_set_is_derived_from_settings_and_is_id_shaped(self):
        """A settings entry that yielded no extractable id would put a
        generic token like "folders" in the production set, which would
        then refuse every Drive URL."""
        assert settings.DRIVE_MAIN_FOLDER_ID in PRODUCTION_DRIVE_LOCATIONS
        assert len(PRODUCTION_DRIVE_FOLDER_IDS) >= 3
        for folder in PRODUCTION_DRIVE_FOLDER_IDS:
            assert re.fullmatch(r"[A-Za-z0-9_-]{15,}", folder), folder
        for raw in PRODUCTION_DRIVE_LOCATIONS:
            assert normalise_drive_folder(raw) in PRODUCTION_DRIVE_FOLDER_IDS

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("abc123", "abc123"),
            ("  abc123  ", "abc123"),
            ("https://drive.google.com/drive/folders/abc123", "abc123"),
            ("https://drive.google.com/drive/u/0/folders/abc123", "abc123"),
            ("https://drive.google.com/drive/folders/abc123?usp=sharing", "abc123"),
            (None, None),
            ("   ", None),
        ],
    )
    def test_normalisation_covers_the_shapes_drive_emits(self, raw, expected):
        assert normalise_drive_folder(raw) == expected


class TestTheGatesFailClosedOnInputTheyCannotRead:
    """A caller mistake must produce a REFUSAL, never an exception and
    never silence. A caller written as `if is_refused(req): abort()`
    inside a broad `except` would otherwise proceed."""

    def _reasons(self, **overrides):
        base = dict(
            environment=Environment.TEST,
            output_project=_test_project(),
            approved_test_projects=frozenset({_test_project()}),
        )
        base.update(overrides)
        return refusal_reasons(RunRequest(**base))

    @pytest.mark.parametrize("value", [123, None, object(), 1.5])
    def test_a_non_string_output_project_is_refused(self, value):
        assert self._reasons(output_project=value)

    @pytest.mark.parametrize("field", ["published_tables", "source_tables"])
    @pytest.mark.parametrize("value", [183, object()])
    def test_a_non_sequence_table_argument_is_refused(self, field, value):
        assert any("not a sequence" in r for r in self._reasons(**{field: value}))

    def test_a_bare_string_table_is_one_entry_not_a_stream_of_characters(self):
        """`for t in "abc"` yields 'a','b','c'. A single table name
        passed without a tuple must be validated as one name."""
        reasons = self._reasons(published_tables="Campaign_Tracker")
        assert len(reasons) == 1
        assert "Campaign_Tracker" in reasons[0]

    def test_a_string_allowlist_is_one_entry_not_a_substring_haystack(self):
        """`"test" in "ih-test-project"` is True, so treating a bare
        string as the allowlist would admit any project whose name is a
        substring of it -- the one place a type mistake fails OPEN."""
        reasons = refusal_reasons(
            RunRequest(
                environment=Environment.TEST,
                output_project="test",
                approved_test_projects="ih-test-project",
            )
        )
        assert any("not on the approved" in r for r in reasons)

    @pytest.mark.parametrize("allowlist", [None, 123, object()])
    def test_an_unreadable_allowlist_refuses_every_project(self, allowlist):
        reasons = self._reasons(approved_test_projects=allowlist)
        assert any("no approved test-project allowlist" in r for r in reasons)

    def test_the_environment_name_as_a_string_is_refused_not_raised(self):
        """parse_environment() accepts the string "test", so passing that
        instead of the enum member is an easy mistake. Gate 5 compares
        with `is`, so it must type-check rather than fall through."""
        reasons = refusal_reasons(
            RunRequest(
                environment="test",
                output_project=_test_project(),
                approved_test_projects=frozenset({_test_project()}),
            )
        )
        assert any("not an Environment member" in r for r in reasons)

    def test_the_answer_does_not_change_between_calls(self):
        """A generator is drained by the first evaluation, so every later
        one sees zero tables. The permissive answer would be the LATER
        one -- exactly the order `log(reasons); if is_refused(): abort()`
        asks in."""
        table = f"{settings.PROJECT_ID}.Metadata.Campaign_Tracker_test"
        request = RunRequest(
            environment=Environment.TEST,
            output_project=_test_project(),
            approved_test_projects=frozenset({_test_project()}),
            published_tables=(t for t in [table]),
        )
        first = refusal_reasons(request)
        assert first
        assert refusal_reasons(request) == first
        assert is_refused(request) is True

    @pytest.mark.parametrize("error", [TypeError, ValueError])
    def test_an_iterable_that_raises_is_refused_not_propagated(self, error):
        """A generator terminated by an exception is CLOSED, so leaving
        it in place means the gate re-iterates it, sees nothing, and
        accepts a request whose tables it never examined."""

        def exploding():
            yield f"{settings.PROJECT_ID}.Metadata.Campaign_Tracker_test"
            raise error("backing store went away")

        reasons = self._reasons(published_tables=exploding())
        assert any("not a sequence" in r for r in reasons), reasons

    def test_is_refused_never_raises_on_hostile_input(self):
        assert is_refused(
            RunRequest(
                environment=Environment.TEST,
                output_project=object(),
                published_tables=(object(),),
                source_tables=(object(),),
                drive_folder=object(),
            )
        )


class TestPhaseAModulesAreAdditiveAndUnimported:
    """The whole Phase A layer must remain unreferenced by live code: it
    establishes a contract and enforces nothing. This mirrors the check
    the shared-config foundation applied to settings.py when it landed."""

    PHASE_A_MODULES = (
        "shared.config.environment",
        "shared.config.source_allowlist",
        "shared.config.output_policy",
    )

    def test_no_production_module_imports_the_phase_a_layer(self, repo_root):
        searched = []
        for directory in ("projects", "ui", "shared"):
            searched.extend((repo_root / directory).rglob("*.py"))
        searched.append(repo_root / "campaign_manager.py")

        phase_a_files = {
            repo_root / "shared" / "config" / "environment.py",
            repo_root / "shared" / "config" / "source_allowlist.py",
            repo_root / "shared" / "config" / "output_policy.py",
        }

        offenders = []
        for path in searched:
            if not path.exists() or path in phase_a_files:
                continue
            source = path.read_text(encoding="utf-8", errors="replace")
            for module in self.PHASE_A_MODULES:
                tail = module.rsplit(".", 1)[-1]
                if re.search(rf"\b(import|from)\s+{re.escape(module)}\b", source):
                    offenders.append(f"{path.relative_to(repo_root)} imports {module}")
                elif re.search(
                    rf"\bfrom\s+shared\.config\s+import\s+[^\n]*\b{tail}\b", source
                ):
                    offenders.append(f"{path.relative_to(repo_root)} imports {tail}")

        assert offenders == [], (
            "Phase A modules must stay additive and unimported by live "
            f"entry points: {offenders}"
        )

    def test_importing_the_layer_has_no_filesystem_or_client_side_effects(
        self, tmp_path, repo_root
    ):
        """Import the whole layer in a REAL, fresh interpreter whose cwd
        is an empty directory: if any module touched the filesystem or
        built a client at import time, the exit status or a stray file
        would show it.

        Deliberately a subprocess rather than importlib.reload(): a
        reload rebuilds the Environment enum in THIS process, so any
        module holding a reference to the previous class object (as
        output_policy does) would start failing identity comparisons --
        a test-harness artifact that would leak into unrelated tests.
        """
        import subprocess
        import sys

        code = (
            "import sys; sys.path.insert(0, sys.argv[1]);"
            + "".join(f"import {module};" for module in self.PHASE_A_MODULES)
            + "print('OK')"
        )
        result = subprocess.run(
            [sys.executable, "-c", code, str(repo_root)],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            timeout=60,
        )
        assert result.returncode == 0, result.stderr
        assert "OK" in result.stdout
        assert list(tmp_path.iterdir()) == [], "import created files on disk"
