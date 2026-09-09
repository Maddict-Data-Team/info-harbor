"""Phase A: test-vs-production environment validation.

Contract only -- these modules are additive, imported by no live entry
point, and enforce nothing at runtime. See
docs/architecture-and-test-environment-plan.md.

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
    drive_folder_candidates,
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

    def test_unset_raises_and_names_the_variable(self):
        with pytest.raises(EnvironmentConfigurationError) as excinfo:
            parse_environment(None)
        assert ENVIRONMENT_ENV_VAR in str(excinfo.value)

    def test_empty_string_raises(self):
        with pytest.raises(EnvironmentConfigurationError):
            parse_environment("")

    def test_whitespace_only_raises(self):
        with pytest.raises(EnvironmentConfigurationError):
            parse_environment("   ")

    @pytest.mark.parametrize("raw", ["prod", "tst", "testing", "staging", "dev", "TEST_"])
    def test_near_misses_raise_rather_than_being_guessed(self, raw):
        with pytest.raises(EnvironmentConfigurationError):
            parse_environment(raw)

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("test", Environment.TEST),
            ("  test  ", Environment.TEST),
            ("Test", Environment.TEST),
            ("production", Environment.PRODUCTION),
            ("PRODUCTION", Environment.PRODUCTION),
        ],
    )
    def test_exact_names_resolve_case_and_whitespace_insensitively(self, raw, expected):
        assert parse_environment(raw) is expected

    def test_there_is_no_third_or_default_environment(self):
        assert {e.value for e in Environment} == {"production", "test"}


class TestResolveEnvironmentReadsTheVariable:
    def test_reads_from_a_supplied_mapping(self):
        assert resolve_environment({ENVIRONMENT_ENV_VAR: "test"}) is Environment.TEST

    def test_missing_key_in_supplied_mapping_raises(self):
        with pytest.raises(EnvironmentConfigurationError):
            resolve_environment({})

    def test_defaults_to_os_environ(self, monkeypatch):
        monkeypatch.setenv(ENVIRONMENT_ENV_VAR, "production")
        assert resolve_environment() is Environment.PRODUCTION
        monkeypatch.delenv(ENVIRONMENT_ENV_VAR, raising=False)
        with pytest.raises(EnvironmentConfigurationError):
            resolve_environment()


class TestTheFiveRefusalGates:
    """docs/architecture-and-test-environment-plan.md:98-105. Each gate is
    asserted on its own so a future change cannot quietly drop one while
    the others keep the suite green."""

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

    def test_a_fully_compliant_request_draws_no_refusal(self):
        assert refusal_reasons(self._clean_request()) == []
        assert is_refused(self._clean_request()) is False

    def test_gate_1_output_project_is_production(self):
        request = self._clean_request(output_project=settings.PROJECT_ID)
        reasons = refusal_reasons(request)
        assert any("production project" in r for r in reasons)
        assert is_refused(request)

    def test_gate_1_production_project_is_refused_even_if_someone_allowlists_it(self):
        """The production check runs before the allowlist check, so a
        misconfigured allowlist cannot re-admit maddictdata."""
        request = self._clean_request(
            output_project=settings.PROJECT_ID,
            approved_test_projects=frozenset({settings.PROJECT_ID, _test_project()}),
        )
        assert any("production project" in r for r in refusal_reasons(request))

    @pytest.mark.parametrize("blank", ["", "   ", "\t", "\n"])
    def test_gate_1_blank_output_project_is_refused(self, blank):
        request = self._clean_request(output_project=blank)
        assert any("empty or whitespace" in r for r in refusal_reasons(request))

    def test_gate_1_refuses_when_no_allowlist_is_configured(self):
        """The module-level allowlist is empty until a human confirms a
        test project, so omitting it must refuse rather than permit."""
        assert APPROVED_TEST_PROJECTS == frozenset()
        request = RunRequest(
            environment=Environment.TEST,
            output_project=_test_project(),
            published_tables=("Campaign_Tracker_test",),
            source_tables=(APPROVED_SOURCE,),
            drive_folder="<TEST_DRIVE_FOLDER_ID>",
        )
        assert any("no approved test-project allowlist" in r for r in refusal_reasons(request))

    def test_gate_1_refuses_a_project_absent_from_the_allowlist(self):
        request = self._clean_request(
            output_project="some-other-project",
            approved_test_projects=frozenset({_test_project()}),
        )
        assert any("not on the approved" in r for r in refusal_reasons(request))

    def test_gate_1_accepts_only_the_explicitly_named_project(self):
        request = self._clean_request(
            output_project=_test_project(),
            approved_test_projects=frozenset({_test_project()}),
        )
        assert refusal_reasons(request) == []

    def test_gate_2_published_table_missing_test_suffix(self):
        request = self._clean_request(published_tables=("Campaign_Tracker",))
        assert any("_test" in r for r in refusal_reasons(request))

    def test_gate_3_source_table_not_on_the_allowlist(self):
        request = self._clean_request(
            source_tables=(f"{settings.PROJECT_ID}.Some_Dataset.some_table",)
        )
        assert any("allowlist" in r for r in refusal_reasons(request))

    def test_gate_3_rejects_a_control_table_offered_as_a_source(self):
        """Campaign_Tracker is written by Automation, so it must never
        pass as a read-only source even though it is a known table."""
        request = self._clean_request(
            source_tables=(
                f"{settings.PROJECT_ID}.{settings.DATASET_METADATA}."
                f"{settings.TABLE_CAMPAIGN_TRACKER}",
            )
        )
        assert any("allowlist" in r for r in refusal_reasons(request))

    @pytest.mark.parametrize(
        "folder",
        [
            # Pinned to settings explicitly, NOT parametrised over the
            # module's own constant -- otherwise deleting an entry from
            # that constant would delete the test case that guards it.
            settings.DRIVE_MAIN_FOLDER_ID,
            settings.DRIVE_BACKEND_REPORTS_FOLDER_ID,
            settings.DRIVE_ADOPS_FOLDER_URL,
            settings.LEGACY_CAMPAIGN_TRACKER_DRIVE_FOLDER_URL,
        ],
    )
    def test_gate_4_production_drive_location_as_configured(self, folder):
        request = self._clean_request(drive_folder=folder)
        assert any("production folder" in r for r in refusal_reasons(request))

    @pytest.mark.parametrize(
        "folder",
        [
            settings.DRIVE_MAIN_FOLDER_ID,
            settings.DRIVE_BACKEND_REPORTS_FOLDER_ID,
            settings.DRIVE_ADOPS_FOLDER_URL,
            settings.LEGACY_CAMPAIGN_TRACKER_DRIVE_FOLDER_URL,
        ],
    )
    def test_gate_4_refuses_every_production_folder_in_both_forms(self, folder):
        """settings records some of these as bare IDs and others as
        URLs. Each must be refused in BOTH forms, plus the common URL
        variants -- otherwise the same folder is blocked one way and
        waved through the other."""
        folder_id = normalise_drive_folder(folder)
        assert folder_id
        variants = [
            folder_id,
            f"https://drive.google.com/drive/folders/{folder_id}",
            f"https://drive.google.com/drive/folders/{folder_id}/",
            f"https://drive.google.com/drive/u/0/folders/{folder_id}",
            f"https://drive.google.com/drive/folders/{folder_id}?usp=sharing",
        ]
        for variant in variants:
            request = self._clean_request(drive_folder=variant)
            assert any(
                "production folder" in r for r in refusal_reasons(request)
            ), f"not refused: {variant}"

    def test_gate_4_allows_a_non_production_folder(self):
        request = self._clean_request(drive_folder="1TESTtestTESTtestTESTtest")
        assert refusal_reasons(request) == []

    def test_every_configured_production_location_normalises_to_a_folder_id(self):
        assert len(PRODUCTION_DRIVE_FOLDER_IDS) >= 3
        for raw in PRODUCTION_DRIVE_LOCATIONS:
            assert normalise_drive_folder(raw) in PRODUCTION_DRIVE_FOLDER_IDS

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("abc123", "abc123"),
            ("  abc123  ", "abc123"),
            ("https://drive.google.com/drive/folders/abc123", "abc123"),
            ("https://drive.google.com/drive/folders/abc123/", "abc123"),
            ("https://drive.google.com/drive/u/0/folders/abc123", "abc123"),
            ("https://drive.google.com/drive/folders/abc123?usp=sharing", "abc123"),
            ("https://drive.google.com/drive/folders/abc123#x", "abc123"),
            (None, None),
            ("", None),
            ("   ", None),
        ],
    )
    def test_drive_normalisation(self, raw, expected):
        assert normalise_drive_folder(raw) == expected



    def test_gate_5_environment_is_not_test(self):
        request = self._clean_request(environment=Environment.PRODUCTION)
        assert any("not 'test'" in r for r in refusal_reasons(request))

    def test_every_gate_reports_independently_rather_than_short_circuiting(self):
        request = RunRequest(
            environment=Environment.PRODUCTION,
            output_project=settings.PROJECT_ID,
            published_tables=("Campaign_Tracker",),
            source_tables=(f"{settings.PROJECT_ID}.Nope.nope",),
            drive_folder=settings.DRIVE_MAIN_FOLDER_ID,
            approved_test_projects=frozenset({_test_project()}),
        )
        assert len(refusal_reasons(request)) >= 5

    def test_production_drive_locations_come_from_settings(self):
        assert settings.DRIVE_MAIN_FOLDER_ID in PRODUCTION_DRIVE_LOCATIONS
        assert settings.DRIVE_BACKEND_REPORTS_FOLDER_ID in PRODUCTION_DRIVE_LOCATIONS



class TestGateTwoValidatesTheDestinationProject:
    """A `_test` suffix alone is not enough: a fully qualified
    destination must also name the run's own output project, so a
    production-qualified table cannot ride through on its suffix."""

    def _request(self, published, project="ih-test-project"):
        return RunRequest(
            environment=Environment.TEST,
            output_project=project,
            published_tables=(published,),
            source_tables=(),
            drive_folder=None,
            approved_test_projects=frozenset({project}),
        )

    def test_production_qualified_table_is_refused_despite_the_test_suffix(self):
        request = self._request(
            f"{settings.PROJECT_ID}.{settings.DATASET_METADATA}.Campaign_Tracker_test"
        )
        reasons = refusal_reasons(request)
        assert any("production project" in r for r in reasons), reasons

    def test_a_table_in_another_non_production_project_is_refused(self):
        request = self._request("some-other-project.Metadata.Campaign_Tracker_test")
        assert any("not the run's output project" in r for r in refusal_reasons(request))

    def test_a_correctly_qualified_table_is_accepted(self):
        request = self._request("ih-test-project.Metadata.Campaign_Tracker_test")
        assert refusal_reasons(request) == []

    def test_a_bare_table_name_is_still_accepted(self):
        assert refusal_reasons(self._request("Campaign_Tracker_test")) == []

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
    def test_malformed_destinations_are_refused(self, malformed):
        reasons = refusal_reasons(self._request(malformed))
        assert reasons
        assert any(("malformed" in r) or ("empty or whitespace" in r) for r in reasons)

    def test_a_qualified_table_still_needs_the_test_suffix(self):
        request = self._request("ih-test-project.Metadata.Campaign_Tracker")
        assert any("_test" in r for r in refusal_reasons(request))
class TestPhaseAModulesAreAdditiveAndUnimported:
    """The whole Phase A layer must remain unreferenced by live code:
    it establishes a contract and enforces nothing. This mirrors the
    check the shared-config foundation applied to settings.py when it
    landed."""

    PHASE_A_MODULES = (
        "shared.config.environment",
        "shared.config.source_allowlist",
        "shared.config.output_policy",
        "shared.observability",
        "shared.observability.redaction",
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
            repo_root / "shared" / "observability" / "__init__.py",
            repo_root / "shared" / "observability" / "redaction.py",
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
                elif re.search(rf"\bfrom\s+shared\.(config|observability)\s+import\s+[^\n]*\b{tail}\b", source):
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
        This mirrors the subprocess pattern the deploy-artifact tests
        already use for the same isolation reason.
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


class TestDriveGateResistsEveryUrlShape:
    """Regression for the security review's F1: the first normalisation
    handled only the shapes it anticipated. `open?id=<id>` and
    `/file/d/<id>/view` -- both formats Drive itself emits -- normalised
    to a trailing word ("open", "view") that matched nothing, so a
    production folder named that way passed gate 4 silently."""

    def _refused(self, location):
        request = RunRequest(
            environment=Environment.TEST,
            output_project=_test_project(),
            published_tables=(),
            source_tables=(),
            drive_folder=location,
            approved_test_projects=frozenset({_test_project()}),
        )
        return bool(refusal_reasons(request))

    @pytest.mark.parametrize(
        "raw",
        [
            settings.DRIVE_MAIN_FOLDER_ID,
            settings.DRIVE_BACKEND_REPORTS_FOLDER_ID,
            settings.DRIVE_ADOPS_FOLDER_URL,
            settings.LEGACY_CAMPAIGN_TRACKER_DRIVE_FOLDER_URL,
        ],
    )
    def test_every_production_folder_is_refused_in_every_shape(self, raw):
        folder_id = normalise_drive_folder(raw)
        assert folder_id
        shapes = [
            folder_id,
            f"https://drive.google.com/drive/folders/{folder_id}",
            f"https://drive.google.com/drive/folders/{folder_id}/",
            f"https://drive.google.com/drive/u/0/folders/{folder_id}",
            f"https://drive.google.com/drive/folders/{folder_id}?usp=sharing",
            f"https://drive.google.com/drive/folders/{folder_id}#anchor",
            # the two shapes that bypassed the first fix
            f"https://drive.google.com/open?id={folder_id}",
            f"https://drive.google.com/file/d/{folder_id}/view",
            f"https://drive.google.com/uc?id={folder_id}&export=download",
            # percent-encoded, and embedded mid-path
            "https://drive.google.com/drive/folders/" + folder_id.replace("-", "%2D"),
            f"https://drive.google.com/a/b/{folder_id}/c",
            f"  {folder_id}  ",
        ]
        for shape in shapes:
            assert self._refused(shape), f"not refused: {shape}"

    def test_a_non_production_folder_is_still_allowed_in_those_shapes(self):
        for shape in [
            "1TESTtestTESTtestTEST",
            "https://drive.google.com/drive/folders/1TESTtestTESTtestTEST",
            "https://drive.google.com/open?id=1TESTtestTESTtestTEST",
        ]:
            assert not self._refused(shape), f"wrongly refused: {shape}"

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("https://drive.google.com/open?id=abc123", "abc123"),
            ("https://drive.google.com/uc?id=abc123&export=download", "abc123"),
            ("https://drive.google.com/file/d/abc123/view", "abc123"),
            ("https://drive.google.com/drive/folders/abc%2D123", "abc-123"),
        ],
    )
    def test_normalisation_covers_the_shapes_drive_emits(self, raw, expected):
        assert normalise_drive_folder(raw) == expected

    def test_candidates_include_every_token_so_unknown_shapes_still_match(self):
        folder = settings.DRIVE_MAIN_FOLDER_ID
        candidates = drive_folder_candidates(
            f"https://some.host/unexpected/{folder}/layout?x=1"
        )
        assert folder in candidates


class TestGatesAreTotalForNonStringInput:
    """The gates must refuse bad input, not raise out of the caller. A
    caller written as `if is_refused(req): abort()` inside a broad
    `except` would otherwise proceed on an AttributeError."""

    def _reasons(self, **overrides):
        base = dict(
            environment=Environment.TEST,
            output_project=_test_project(),
            published_tables=(),
            source_tables=(),
            drive_folder=None,
            approved_test_projects=frozenset({_test_project()}),
        )
        base.update(overrides)
        return refusal_reasons(RunRequest(**base))

    @pytest.mark.parametrize("value", [123, None, object(), 1.5, True])
    def test_non_string_output_project_is_refused_not_raised(self, value):
        assert self._reasons(output_project=value)

    @pytest.mark.parametrize("value", [183, None, object()])
    def test_non_string_published_table_is_refused_not_raised(self, value):
        assert self._reasons(published_tables=(value,))

    @pytest.mark.parametrize("value", [12345, object(), 1.5])
    def test_non_string_drive_folder_does_not_raise(self, value):
        self._reasons(drive_folder=value)  # must not raise

    @pytest.mark.parametrize("value", [183, None, object()])
    def test_non_string_source_table_is_refused_not_raised(self, value):
        assert self._reasons(source_tables=(value,))

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


class TestGatesResistCallerTypeMistakes:
    """Round-3 regressions. Every one of these fails OPEN or raises in
    the version before this round, and each is a plausible caller
    mistake rather than an exotic input."""

    def test_a_string_allowlist_does_not_become_substring_containment(self):
        """`"test" in "ih-test-project"` is True. A bare string must be
        treated as a ONE-entry allowlist, not a haystack."""
        request = RunRequest(
            environment=Environment.TEST,
            output_project="test",
            approved_test_projects="ih-test-project",
        )
        assert any("not on the approved" in r for r in refusal_reasons(request))

    def test_a_string_allowlist_still_admits_its_own_single_entry(self):
        request = RunRequest(
            environment=Environment.TEST,
            output_project=_test_project(),
            approved_test_projects=_test_project(),
        )
        assert refusal_reasons(request) == []

    @pytest.mark.parametrize("allowlist", [None, 123, object(), 0])
    def test_a_non_iterable_allowlist_refuses_everything(self, allowlist):
        request = RunRequest(
            environment=Environment.TEST,
            output_project=_test_project(),
            approved_test_projects=allowlist,
        )
        assert any("no approved test-project allowlist" in r for r in refusal_reasons(request))

    def test_the_environment_name_as_a_string_is_refused_not_raised(self):
        """parse_environment() accepts the string "test", so passing that
        string here instead of the Environment member is a very easy
        mistake -- it must refuse, not raise AttributeError past a
        caller's `except`."""
        request = RunRequest(
            environment="test",
            output_project=_test_project(),
            approved_test_projects=frozenset({_test_project()}),
        )
        assert any("not an Environment member" in r for r in refusal_reasons(request))

    @pytest.mark.parametrize("value", [183, object(), 4.5])
    def test_a_non_iterable_table_sequence_is_refused_not_raised(self, value):
        for field_name in ("published_tables", "source_tables"):
            request = RunRequest(
                environment=Environment.TEST,
                output_project=_test_project(),
                approved_test_projects=frozenset({_test_project()}),
                **{field_name: value},
            )
            reasons = refusal_reasons(request)
            assert any("is not a sequence" in r for r in reasons), (field_name, reasons)

    def test_a_bare_string_table_is_one_entry_not_a_stream_of_characters(self):
        """`for t in "abc"` yields 'a','b','c'. A single table name passed
        without a tuple must be validated as one name."""
        request = RunRequest(
            environment=Environment.TEST,
            output_project=_test_project(),
            approved_test_projects=frozenset({_test_project()}),
            published_tables="Campaign_Tracker",
        )
        reasons = refusal_reasons(request)
        assert len(reasons) == 1
        assert "Campaign_Tracker" in reasons[0]


class TestDriveGateResistsSeparatorTricks:
    """Round-3 regression: token membership alone missed a production id
    sitting next to a separator the splitter does not know about."""

    def _refused(self, location):
        return bool(
            refusal_reasons(
                RunRequest(
                    environment=Environment.TEST,
                    output_project=_test_project(),
                    approved_test_projects=frozenset({_test_project()}),
                    drive_folder=location,
                )
            )
        )

    @pytest.mark.parametrize(
        "template",
        [
            "id:{f}",
            "{f},",
            "'{f}'",
            '"{f}"',
            "({f})",
            "folder={f};",
            "https://drive.google.com/open?id={f}",
            "https://drive.google.com/file/d/{f}/view",
            "\u200b{f}\u200b",
        ],
    )
    def test_a_production_folder_is_refused_in_awkward_punctuation(self, template):
        folder = settings.DRIVE_MAIN_FOLDER_ID
        assert self._refused(template.format(f=folder)), template

    def test_a_double_encoded_production_id_is_refused(self):
        folder = settings.DRIVE_MAIN_FOLDER_ID
        assert self._refused(
            "https://drive.google.com/drive/folders/" + folder.replace("-", "%252D")
        )

    def test_non_production_folders_are_still_allowed_in_those_shapes(self):
        for template in ["id:{f}", "{f},", "'{f}'", "https://drive.google.com/open?id={f}"]:
            assert not self._refused(template.format(f="1TESTtestTESTtestTEST")), template

    def test_derived_production_ids_all_look_like_real_drive_ids(self):
        """A settings entry that yields no extractable id would otherwise
        put a generic token like "folders" in the production set, which
        would then match -- and refuse -- every Drive URL."""
        assert PRODUCTION_DRIVE_FOLDER_IDS
        for folder in PRODUCTION_DRIVE_FOLDER_IDS:
            assert re.fullmatch(r"[A-Za-z0-9_-]{15,}", folder), folder
        for raw in PRODUCTION_DRIVE_LOCATIONS:
            assert normalise_drive_folder(raw) in PRODUCTION_DRIVE_FOLDER_IDS


class TestGatesReturnTheSameAnswerEveryTime:
    """A validation function that answers differently on the second call
    is worse than one that is merely wrong: the caller shape `log(
    refusal_reasons(r)); if is_refused(r): abort()` then aborts on the
    FIRST answer and proceeds on the second."""

    def _production_table(self):
        return f"{settings.PROJECT_ID}.{settings.DATASET_METADATA}.Campaign_Tracker_test"

    def _request(self, tables):
        return RunRequest(
            environment=Environment.TEST,
            output_project=_test_project(),
            published_tables=tables,
            approved_test_projects=frozenset({_test_project()}),
        )

    def test_a_generator_of_tables_is_not_drained_by_the_first_call(self):
        table = self._production_table()
        request = self._request(t for t in [table])
        first = refusal_reasons(request)
        assert first, "the production project should be refused on the first call"
        assert refusal_reasons(request) == first
        assert is_refused(request) is True

    def test_an_iterator_of_tables_is_not_drained_either(self):
        table = self._production_table()
        request = self._request(iter([table]))
        assert refusal_reasons(request)
        assert refusal_reasons(request)
        assert is_refused(request) is True

    def test_a_set_of_tables_is_accepted_as_a_sequence(self):
        request = self._request({self._production_table()})
        assert len(refusal_reasons(request)) == 1
        assert len(refusal_reasons(request)) == 1

    def test_repeated_evaluation_is_stable_for_a_compliant_request(self):
        request = self._request((f"{_test_project()}.scratch.Campaign_Tracker_test",))
        assert refusal_reasons(request) == []
        assert refusal_reasons(request) == []

    def test_source_tables_are_materialised_too(self):
        request = RunRequest(
            environment=Environment.TEST,
            output_project=_test_project(),
            source_tables=(t for t in ["not.an.approved_source"]),
            approved_test_projects=frozenset({_test_project()}),
        )
        first = refusal_reasons(request)
        assert first
        assert refusal_reasons(request) == first


class TestTheProductionDriveSetTracksSettings:
    def test_every_DRIVE_setting_is_covered_by_the_production_set(self):
        """_PRODUCTION_DRIVE_SETTINGS is hand-maintained. A fifth DRIVE_*
        constant added to settings.py would otherwise be unguarded by
        gate 4 with the whole suite green."""
        def values_of(value):
            """Flatten a settings value to the strings inside it, so a
            tuple or dict of folders is not silently skipped -- that is
            exactly the shape a fifth Drive constant would take."""
            if isinstance(value, str):
                return [value] if value.strip() else []
            if isinstance(value, dict):
                found = []
                for item in value.values():
                    found.extend(values_of(item))
                return found
            if isinstance(value, (list, tuple, set, frozenset)):
                found = []
                for item in value:
                    found.extend(values_of(item))
                return found
            return []

        declared = {
            name: values_of(getattr(settings, name))
            for name in dir(settings)
            if name.startswith("DRIVE_") or "DRIVE_FOLDER" in name
        }
        covered = set(PRODUCTION_DRIVE_LOCATIONS)
        missing = sorted(
            name
            for name, values in declared.items()
            if values and any(value not in covered for value in values)
        )
        assert not missing, (
            f"settings.py declares Drive location(s) {missing} that gate 4 does not "
            f"know about; add them to _PRODUCTION_DRIVE_SETTINGS"
        )


class TestReEntrancyCoversEveryIterableField:
    """Round-five regression. The first re-entrancy fix covered the two
    table fields and missed the allowlist, so the answer still changed
    between calls -- fail-closed rather than open, but the guarantee is
    that it does not change at all."""

    def test_an_iterator_allowlist_gives_the_same_answer_twice(self):
        request = RunRequest(
            environment=Environment.TEST,
            output_project=_test_project(),
            approved_test_projects=iter([_test_project()]),
        )
        first = refusal_reasons(request)
        assert first == []
        assert refusal_reasons(request) == first
        assert is_refused(request) is False

    def test_a_generator_allowlist_gives_the_same_answer_twice(self):
        request = RunRequest(
            environment=Environment.TEST,
            output_project=_test_project(),
            approved_test_projects=(p for p in [_test_project()]),
        )
        assert refusal_reasons(request) == []
        assert refusal_reasons(request) == []

    def test_a_frozenset_allowlist_is_left_exactly_as_it_came_in(self):
        allowlist = frozenset({_test_project()})
        request = RunRequest(
            environment=Environment.TEST,
            output_project=_test_project(),
            approved_test_projects=allowlist,
        )
        assert request.approved_test_projects is allowlist

    def test_a_string_allowlist_is_still_one_entry_after_materialising(self):
        """The __post_init__ guard must not turn a string into a
        character sequence -- that is the substring-containment bug the
        earlier round fixed."""
        request = RunRequest(
            environment=Environment.TEST,
            output_project="test",
            approved_test_projects="ih-test-project",
        )
        assert any("not on the approved" in r for r in refusal_reasons(request))

    def test_an_iterable_that_raises_is_refused_not_raised_at_construction(self):
        """__post_init__ runs inside the CONSTRUCTOR, where no `try`
        around is_refused() can catch anything it lets escape."""

        def exploding():
            yield "a"
            raise ValueError("backing store went away")

        request = RunRequest(
            environment=Environment.TEST,
            output_project=_test_project(),
            approved_test_projects=frozenset({_test_project()}),
            published_tables=exploding(),
        )
        reasons = refusal_reasons(request)
        assert reasons
        assert refusal_reasons(request) == reasons


class TestInvisibleCharacterStrippingIsCategoryBased:
    """Round-five regression. Every enumerated list drawn up so far has
    been missing a neighbour of something already on it, so the rule is
    now Unicode category "Cf" plus the variation selectors."""

    @pytest.mark.parametrize(
        "codepoint",
        [
            0x00AD,  # soft hyphen
            0x061C,  # Arabic letter mark
            0x200B,  # zero-width space
            0x200D,  # zero-width joiner
            0x202E,  # right-to-left override
            0x2060,  # word joiner
            0x206A,  # deprecated: directly beside the ranges once listed
            0x206F,
            0x2066,  # bidi isolate
            0xFE0F,  # variation selector
            0xFEFF,  # BOM
            0xFFF9,  # interlinear annotation anchor
            0xE0100,  # variation selector supplement
        ],
    )
    def test_an_invisible_character_cannot_hide_a_production_folder(self, codepoint):
        folder = settings.DRIVE_MAIN_FOLDER_ID
        mangled = folder[:10] + chr(codepoint) + folder[10:]
        assert names_production_drive_folder(mangled), hex(codepoint)

    def test_visible_characters_are_not_stripped(self):
        """Stripping too much would make unrelated folders collide."""
        assert not names_production_drive_folder("1TESTtestTESTtestTEST")
        assert normalise_drive_folder("1TESTtestTESTtestTEST") == "1TESTtestTESTtestTEST"


class TestAnIterableThatRaisesIsRefusedWhateverItRaises:
    """Round-six regression. `except TypeError` around `tuple(value)`
    cannot tell "this object is not iterable" from "iterating it raised
    TypeError", and the two need opposite handling. Conflating them let
    a generator that raised TypeError -- already closed, so re-iterating
    yields nothing -- be seen as an empty table list and ACCEPTED."""

    @pytest.mark.parametrize(
        "error", [TypeError, ValueError, RuntimeError, KeyError, OSError]
    )
    def test_the_request_is_refused_whatever_the_iterable_raises(self, error):
        def exploding():
            yield f"{settings.PROJECT_ID}.Metadata.Campaign_Tracker_test"
            raise error("backing store went away")

        request = RunRequest(
            environment=Environment.TEST,
            output_project=_test_project(),
            published_tables=exploding(),
            approved_test_projects=frozenset({_test_project()}),
        )
        reasons = refusal_reasons(request)
        assert reasons, f"{error.__name__} produced an ACCEPT"
        assert any("not a sequence" in r for r in reasons), reasons
        assert refusal_reasons(request) == reasons

    def test_a_sequence_subclass_whose_iteration_raises_is_refused_not_raised(self):
        """__post_init__ skips anything already a Sequence, so this
        arrives at the gate intact and the gate must survive it."""

        class Hostile(list):
            def __iter__(self):
                raise RuntimeError("backing store went away")

        request = RunRequest(
            environment=Environment.TEST,
            output_project=_test_project(),
            published_tables=Hostile(["x"]),
            approved_test_projects=frozenset({_test_project()}),
        )
        assert refusal_reasons(request)

    def test_a_hostile_allowlist_refuses_rather_than_raising(self):
        class Hostile(set):
            def __iter__(self):
                raise RuntimeError("backing store went away")

        request = RunRequest(
            environment=Environment.TEST,
            output_project=_test_project(),
            approved_test_projects=Hostile({_test_project()}),
        )
        assert any("no approved test-project allowlist" in r for r in refusal_reasons(request))


class TestParseEnvironmentRaisesItsDeclaredErrorType:
    """A caller reading the value from a config object rather than
    os.environ can hand over a non-string. `except
    EnvironmentConfigurationError: abort()` must still catch it."""

    @pytest.mark.parametrize("raw", [123, 4.5, object(), b"test", [], {"a": 1}])
    def test_a_non_string_raises_the_declared_error(self, raw):
        with pytest.raises(EnvironmentConfigurationError):
            parse_environment(raw)

    def test_the_message_names_the_variable_and_the_valid_values(self):
        with pytest.raises(EnvironmentConfigurationError) as caught:
            parse_environment(123)
        assert ENVIRONMENT_ENV_VAR in str(caught.value)
        assert "test" in str(caught.value)


class TestTheDriveGateRefusesWhatItCannotRead:
    """Round-seven regression, and the last gate to fail OPEN on an
    unreadable value. Gate 4 asks "does a production id appear in this
    text?", so a value with no useful text answers "no" -- silence, not
    a refusal. Every other gate turns an unreadable value into a
    refusal, and this one now does too."""

    def _reasons(self, folder):
        return refusal_reasons(
            RunRequest(
                environment=Environment.TEST,
                output_project=_test_project(),
                approved_test_projects=frozenset({_test_project()}),
                drive_folder=folder,
            )
        )

    def test_an_object_hiding_the_id_in_an_attribute_is_refused(self):
        """The default repr is `<... object at 0x...>`, which contains no
        folder id at all -- so containment matched nothing and the run
        was ACCEPTED while naming a production folder."""

        class DriveFolder:
            def __init__(self, folder_id):
                self.folder_id = folder_id

        reasons = self._reasons(DriveFolder(settings.DRIVE_MAIN_FOLDER_ID))
        assert reasons
        assert any("not a string" in r for r in reasons), reasons

    @pytest.mark.parametrize("folder", [123, 4.5, object(), b"id", [], {}, ()])
    def test_any_non_string_drive_location_is_refused(self, folder):
        assert self._reasons(folder)

    def test_none_still_means_no_drive_location(self):
        assert self._reasons(None) == []

    def test_a_string_location_is_still_judged_on_its_content(self):
        assert self._reasons("1TESTtestTESTtestTEST") == []
        assert self._reasons(settings.DRIVE_MAIN_FOLDER_ID)
