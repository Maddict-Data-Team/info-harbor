"""
Phase 2e (IH-048 follow-up): projects/automation/variables.py's primitive
values now delegate to shared/config/settings.py instead of hardcoding
their own copies. schema_back_end (structural BigQuery schema) is
untouched -- not a "primitive configuration value", explicitly out of
scope, same as the POI/Campaign Tracker/Segments migrations. main.py,
query_orchestrator.py, upload_backend.py, custom_codename.py, and
queries.ini are all unmodified by this migration.

No test in this file constructs a real Google client or touches
network/credentials: variables.py only imports `bigquery` for
`SchemaField` objects (plain data classes), never a client; main.py's
`main()`/`query_bigquery_and_process()` and upload_backend.py's/
query_orchestrator.py's operational functions are never called.
"""
from __future__ import annotations

import subprocess
import sys

from tests.conftest import import_module_from_path


def _load_automation_variables(repo_root):
    path = repo_root / "projects" / "automation" / "variables.py"
    return import_module_from_path("automation_variables_under_test", path)


class TestDelegatedValuesMatchSharedSettings:
    """Every primitive value projects/automation/variables.py now sources
    from shared/config/settings.py must be identical to what it
    hardcoded before this migration (docs/code-audit.md IH-048's
    original evidence for this file, lines 6-48,83-107)."""

    def test_project(self, repo_root):
        from shared.config import settings

        mod = _load_automation_variables(repo_root)
        assert mod.project == settings.PROJECT_ID == "maddictdata"

    def test_backend_reports_folder(self, repo_root):
        from shared.config import settings

        mod = _load_automation_variables(repo_root)
        assert (
            mod.folder_id_Backend_Reports
            == settings.DRIVE_BACKEND_REPORTS_FOLDER_ID
            == "1vKOH8eDs92jHSaGyPILAa9p3qH8YUHNo"
        )

    def test_secret_manager_resource_names(self, repo_root):
        from shared.config import settings

        mod = _load_automation_variables(repo_root)
        assert (
            mod.secret_ber
            == settings.SECRET_BACKEND_REPORT_TOKEN
            == "projects/maddictdata/secrets/token-ber/versions/latest"
        )
        assert (
            mod.secret_bq
            == settings.SECRET_BIGQUERY_CREDENTIALS
            == "projects/maddictdata/secrets/secret-bq/versions/latest"
        )

    def test_legacy_key_paths(self, repo_root):
        from shared.config import settings

        mod = _load_automation_variables(repo_root)
        assert mod.key_bq == settings.LEGACY_BIGQUERY_KEY_PATH == "keys/maddictdata-bq.json"
        assert (
            mod.key_google_sheets
            == settings.LEGACY_GOOGLE_SHEETS_KEY_PATH
            == "keys/maddictdata-google-sheets.json"
        )

    def test_datasets(self, repo_root):
        from shared.config import settings

        mod = _load_automation_variables(repo_root)
        assert mod.dataset_LS == settings.DATASET_LOCATION_SIGNALS == "Location_Signals"
        assert mod.dataset_footfall == settings.DATASET_FOOTFALL == "Back_End_Footfall"
        assert mod.dataset_BERs == settings.DATASET_BACKEND_REPORTS == "Back_End_Reports"
        assert (
            mod.dataset_campaign_segments
            == settings.DATASET_CAMPAIGN_SEGMENTS
            == "Placelift_Campaign_Segments"
        )
        assert mod.dataset_Districts == settings.DATASET_DISTRICT_MAPPING == "District_Mapping"
        assert mod.dataset_HWG == settings.DATASET_AUTOMATED_HWG == "Automated_HWG"
        assert (
            mod.dataset_mt_Placelift
            == settings.DATASET_METADATA_PLACELIFT
            == "maddictdata.Metadata.Placelift"
        )
        assert mod.dataset_metadata == settings.DATASET_METADATA == "Metadata"

    def test_tables(self, repo_root):
        from shared.config import settings

        mod = _load_automation_variables(repo_root)
        assert mod.table_HG == settings.TABLE_HOME_GRAPH == "Home_Graph_Cumulative"
        assert mod.tbl_cmpgn_tracker == settings.TABLE_CAMPAIGN_TRACKER == "Campaign_Tracker"
        assert mod.tbl_cmpgn_test == settings.TABLE_CAMPAIGN_TEST == "test"
        assert (
            mod.table_behavior_lookup
            == settings.TABLE_BEHAVIOR_LOOKUP
            == "Lookup_Behavior"
        )
        assert mod.table_os_mapping == settings.TABLE_DEVICE_OS_MAPPING == "device_os_mapping"

    def test_statuses(self, repo_root):
        from shared.config import settings

        mod = _load_automation_variables(repo_root)
        assert mod.stage_0 == settings.STATUS_PRE_VALIDATION == "Pre-Validation"
        assert mod.stage_1 == settings.STATUS_VALIDATION == "Validation"
        assert mod.stage_2 == settings.STATUS_ACTIVE == "Active"
        assert mod.stage_3 == settings.STATUS_COMPLETION_PERIOD == "Completion Period"
        assert mod.stage_4 == settings.STATUS_FINISHED == "Finished"
        assert mod.stage_5 == settings.STATUS_ERROR == "Error"
        assert mod.stage_6 == settings.STATUS_ON_HOLD == "On Hold"

    def test_table_mapping_matches_settings_and_stays_a_plain_mutable_dict(self, repo_root):
        from shared.config import settings

        mod = _load_automation_variables(repo_root)
        assert mod.table_mapping == dict(settings.AUTOMATION_COUNTRY_POI_TABLES)
        assert mod.table_mapping == {
            "KSA": "POI_DB_KSA",
            "UAE": "POI_DB_UAE",
            "QAT": "POI_DB_QTR",
            "KWT": "POI_DB_KWT",
            "OMN": "POI_DB_OMN",
            "BHR": "POI_DB_BHR",
        }
        # The legacy value was a plain dict literal, not a read-only
        # mapping -- preserve exact behavior and type, including
        # mutability, for anything that might assign into it.
        assert type(mod.table_mapping) is dict
        mod.table_mapping["TEST"] = "should not raise"  # would raise on a MappingProxyType

    def test_static_query_replace_picks_up_delegated_values_transitively(self, repo_root):
        """static_query_replace's dict literal was left completely
        unmodified -- it's built from the already-delegated local names
        above, so it must contain the exact same 12 entries with the
        exact same resolved values as the legacy hardcoded file."""
        mod = _load_automation_variables(repo_root)
        assert mod.static_query_replace == {
            "{hwg_dataset}": "Automated_HWG",
            "{footfall_dataset}": "Back_End_Footfall",
            "{project}": "maddictdata",
            "{metadata_dataset}": "Metadata",
            "{campaign_tracker_table}": "Campaign_Tracker",
            "{location_signals_dataset}": "Location_Signals",
            "{device_os_mapping_table}": "device_os_mapping",
            "{hwg_table}": "Home_Graph_Cumulative",
            "{lookup_behavior_table}": "Lookup_Behavior",
            "{back_end_report_dataset}": "Back_End_Reports",
            "{Campaign_segments_dataset}": "Placelift_Campaign_Segments",
            "{tbl_cmpgn_test}": "test",
        }


class TestSchemaUnchanged:
    """schema_back_end is explicitly out of scope for this migration --
    must remain the exact same SchemaField list as before."""

    def test_schema_back_end_unchanged(self, repo_root):
        mod = _load_automation_variables(repo_root)
        actual = [(f.name, f.field_type) for f in mod.schema_back_end]
        assert actual == [
            ("campaign", "STRING"),
            ("LINE", "STRING"),
            ("TIMESTAMP", "TIMESTAMP"),
            ("req_id", "STRING"),
            ("udid_idfa", "STRING"),
            ("devraw", "STRING"),
            ("country", "STRING"),
            ("city", "STRING"),
            ("latitude", "FLOAT64"),
            ("longitude", "FLOAT64"),
            ("dev_os", "STRING"),
            ("dev_language", "STRING"),
            ("dev_make", "STRING"),
            ("dev_type", "STRING"),
            ("connection_type", "STRING"),
            ("carrier", "STRING"),
            ("exchange", "STRING"),
            ("dev_ip", "STRING"),
            ("zip", "STRING"),
            ("creative", "STRING"),
            ("ad_size", "STRING"),
            ("App_ID", "INT64"),
            ("environment", "STRING"),
            ("publisher", "STRING"),
            ("App_Name", "STRING"),
            ("impressions", "INT64"),
            ("clicks", "INT64"),
        ]


class TestQueriesUnchanged:
    """q_update_status, q_select_active_interval, and q_deduplicate_ber()
    were left completely unmodified in source -- they reference the
    already-delegated local names (tbl_cmpgn_tracker, project,
    dataset_BERs) via f-strings, so their resolved text must be
    byte-identical to the legacy hardcoded values."""

    def test_q_update_status_resolved_text(self, repo_root):
        mod = _load_automation_variables(repo_root)
        assert "UPDATE `maddictdata.Metadata.Campaign_Tracker`" in mod.q_update_status

    def test_q_select_active_interval_resolved_text(self, repo_root):
        mod = _load_automation_variables(repo_root)
        assert "FROM\n  `maddictdata.Metadata.Campaign_Tracker`" in mod.q_select_active_interval

    def test_q_deduplicate_ber_resolved_text(self, repo_root):
        mod = _load_automation_variables(repo_root)
        query = mod.q_deduplicate_ber("183")
        assert "`maddictdata.Back_End_Reports.183`" in query


class TestImportableTheWayEachLegacyCallerLoadsIt:
    """Critical import guardrail (IH-048 follow-up, same class of check
    already applied to POI/Campaign Tracker/Segments). main.py,
    query_orchestrator.py, and upload_backend.py all load
    variables.py via importlib.util.spec_from_file_location (the IH-047
    fix), and custom_codename.py loads it as a flat `from variables
    import *` -- none of those put the repository root on sys.path
    themselves. A direct script run (`python projects/automation/main.py`,
    or `cd projects/automation && python main.py`) puts only that
    script's own directory on sys.path -- not the repository root.

    Not reproducible from inside the current pytest process:
    tests/conftest.py's session-scoped autouse fixture already added the
    repo root to sys.path for the whole test session (which would mask
    this exact bug), and `shared` may already be cached in sys.modules
    from other tests. Every test in this class runs a real, separate
    subprocess with only projects/automation/ on sys.path.

    Only imports `variables`/`main` -- never calls `main()`,
    `query_bigquery_and_process()`, or any function that would construct
    a real Google client.
    """

    def _run_in_subprocess(self, cwd, automation_dir, import_target: str):
        code = (
            "import sys; sys.path.insert(0, sys.argv[1]); "
            f"import {import_target} as m; "
            "print('OK', m.project, m.dataset_metadata, "
            "m.table_mapping['KSA'], m.stage_3, m.tbl_cmpgn_tracker)"
        )
        return subprocess.run(
            [sys.executable, "-c", code, str(automation_dir)],
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=30,
        )

    _EXPECTED_STDOUT = "OK maddictdata Metadata POI_DB_KSA Completion Period Campaign_Tracker"

    def test_variables_importable_with_cwd_at_repo_root(self, repo_root):
        automation_dir = repo_root / "projects" / "automation"
        result = self._run_in_subprocess(repo_root, automation_dir, "variables")
        assert result.returncode == 0, result.stderr
        assert self._EXPECTED_STDOUT in result.stdout

    def test_variables_importable_with_cwd_inside_automation_directory(self, repo_root):
        """The scenario that actually fails without variables.py's own
        sys.path handling: an operator who `cd`s into
        projects/automation/ before running `python main.py` or
        `python custom_codename.py <code_name>`."""
        automation_dir = repo_root / "projects" / "automation"
        result = self._run_in_subprocess(automation_dir, automation_dir, "variables")
        assert result.returncode == 0, (
            f"variables.py failed to import with cwd=projects/automation "
            f"(IH-048 follow-up guardrail): {result.stderr}"
        )
        assert self._EXPECTED_STDOUT in result.stdout

    def test_main_module_importable_with_cwd_inside_automation_directory_without_calling_main(
        self, repo_root
    ):
        automation_dir = repo_root / "projects" / "automation"
        result = self._run_in_subprocess(automation_dir, automation_dir, "main")
        assert result.returncode == 0, result.stderr
        assert self._EXPECTED_STDOUT in result.stdout

    def test_query_orchestrator_module_importable_with_cwd_inside_automation_directory(
        self, repo_root
    ):
        automation_dir = repo_root / "projects" / "automation"
        result = self._run_in_subprocess(automation_dir, automation_dir, "query_orchestrator")
        assert result.returncode == 0, result.stderr
        assert self._EXPECTED_STDOUT in result.stdout

    def test_upload_backend_module_importable_with_cwd_inside_automation_directory(
        self, repo_root
    ):
        automation_dir = repo_root / "projects" / "automation"
        result = self._run_in_subprocess(automation_dir, automation_dir, "upload_backend")
        assert result.returncode == 0, result.stderr
        assert self._EXPECTED_STDOUT in result.stdout

    def test_custom_codename_module_importable_with_cwd_inside_automation_directory(
        self, repo_root
    ):
        """custom_codename.py itself uses plain, unaliased imports of
        upload_backend/query_orchestrator/variables (a pre-existing
        IH-047-class same-name-collision risk this migration does not
        fix -- out of scope, tracked separately). This test only proves
        variables.py's own sys.path fix lets custom_codename.py's flat
        `from variables import *` resolve at all when invoked directly;
        it does not call main() or query_bigquery_and_process()."""
        automation_dir = repo_root / "projects" / "automation"
        result = self._run_in_subprocess(automation_dir, automation_dir, "custom_codename")
        assert result.returncode == 0, result.stderr
        assert self._EXPECTED_STDOUT in result.stdout
