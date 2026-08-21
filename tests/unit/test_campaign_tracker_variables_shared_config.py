"""
Phase 2c (IH-048 follow-up): projects/campaign-tracker/variables.py's
primitive values now delegate to shared/config/settings.py instead of
hardcoding their own copies. schema_DID, schema_back_end, and
schema_Combined (structural BigQuery schemas) are untouched -- not
"primitive configuration values", explicitly out of scope. main.py,
main_new.py, input.py, ui/app.py, and campaign_manager.py are all
unmodified by this migration.

No test in this file constructs a real Google client or touches
network/credentials: variables.py only imports `bigquery` for
`SchemaField` objects (plain data classes), never a client; main.py's
`create_client()`/`metadata_placelift()`/`main()` are checked for
existence/callability only, never called.
"""
from __future__ import annotations

import subprocess
import sys

from tests.conftest import import_module_from_path


def _load_ct_variables(repo_root):
    path = repo_root / "projects" / "campaign-tracker" / "variables.py"
    return import_module_from_path("campaign_tracker_variables_under_test", path)


class TestDelegatedValuesMatchSharedSettings:
    """Every primitive value now sourced from shared/config/settings.py
    must be identical to what projects/campaign-tracker/variables.py
    hardcoded before this migration (docs/code-audit.md IH-048's
    original evidence for this file, lines 5-51)."""

    def test_statuses(self, repo_root):
        from shared.config import settings

        mod = _load_ct_variables(repo_root)
        assert mod.stage_0 == settings.STATUS_PRE_VALIDATION == "Pre-Validation"
        assert mod.stage_1 == settings.STATUS_VALIDATION == "Validation"
        assert mod.stage_2 == settings.STATUS_ACTIVE == "Active"
        assert mod.stage_3 == settings.STATUS_COMPLETION_PERIOD == "Completion Period"
        assert mod.stage_4 == settings.STATUS_FINISHED == "Finished"

    def test_project_and_datasets(self, repo_root):
        from shared.config import settings

        mod = _load_ct_variables(repo_root)
        assert mod.project == settings.PROJECT_ID == "maddictdata"
        assert mod.dataset == settings.DATASET_BACKEND_REPORTS == "Back_End_Reports"
        assert mod.dataset_LS == settings.DATASET_LOCATION_SIGNALS == "Location_Signals"
        assert mod.dataset_footfall == settings.DATASET_FOOTFALL == "Back_End_Footfall"
        assert mod.dataset_BERs == settings.DATASET_BACKEND_REPORTS == "Back_End_Reports"
        assert (
            mod.dataset_campaign_segments
            == settings.DATASET_CAMPAIGN_SEGMENTS
            == "Placelift_Campaign_Segments"
        )
        assert mod.dataset_metadata == settings.DATASET_METADATA == "Metadata"

    def test_table_and_dir(self, repo_root):
        from shared.config import settings

        mod = _load_ct_variables(repo_root)
        assert mod.tbl_campaign_tracker == settings.TABLE_CAMPAIGN_TRACKER == "Campaign_Tracker"
        assert mod.dir_data == settings.CAMPAIGN_TRACKER_DATA_DIR == "data"

    def test_legacy_key_paths(self, repo_root):
        from shared.config import settings

        mod = _load_ct_variables(repo_root)
        assert mod.key_bq == settings.LEGACY_BIGQUERY_KEY_PATH == "keys/maddictdata-bq.json"
        assert (
            mod.key_google_sheets
            == settings.LEGACY_GOOGLE_SHEETS_KEY_PATH
            == "keys/maddictdata-google-sheets.json"
        )

    def test_distinct_legacy_drive_url_is_preserved_not_collapsed(self, repo_root):
        """Campaign Tracker's Drive folder is a different, legacy
        location from the Segments/AdOps one -- must stay separate, not
        silently become settings.DRIVE_ADOPS_FOLDER_URL."""
        from shared.config import settings

        mod = _load_ct_variables(repo_root)
        assert (
            mod.drive_link_folder_Adops
            == settings.LEGACY_CAMPAIGN_TRACKER_DRIVE_FOLDER_URL
            == "https://drive.google.com/drive/folders/1GuOSGxq5AlLxzaqbkzQBDQ8n7HcuhWWM"
        )
        assert mod.drive_link_folder_Adops != settings.DRIVE_ADOPS_FOLDER_URL

    def test_table_mapping_matches_settings_and_stays_a_plain_mutable_dict(self, repo_root):
        from shared.config import settings

        mod = _load_ct_variables(repo_root)
        assert mod.table_mapping == dict(settings.CAMPAIGN_TRACKER_COUNTRY_POI_TABLES)
        assert mod.table_mapping == {
            "KSA": "POI_DB_KSA",
            "UAE": "POI_DB_UAE",
            "QAT": "POI_DB_QTR",
            "KWT": "POI_DB_KWT",
            "OMN": "POI_DB_OMN",
            "BHR": "POI_DB_BHR",
            "EGY": "POI_DB_EGP",
            "MAR": "POI_DB_MAR",
        }
        # The legacy value was a plain dict literal, not a read-only
        # mapping -- preserve exact behavior and type, including
        # mutability, for anything that might assign into it.
        assert type(mod.table_mapping) is dict
        mod.table_mapping["TEST"] = "should not raise"  # would raise on a MappingProxyType


class TestSchemasUnchanged:
    """schema_DID, schema_back_end, and schema_Combined are explicitly
    out of scope for this migration -- must remain the exact same
    SchemaField lists as before."""

    def test_schema_did_unchanged(self, repo_root):
        mod = _load_ct_variables(repo_root)
        actual = [(f.name, f.field_type) for f in mod.schema_DID]
        assert actual == [("DID", "STRING")]

    def test_schema_back_end_unchanged(self, repo_root):
        mod = _load_ct_variables(repo_root)
        actual = [(f.name, f.field_type) for f in mod.schema_back_end]
        assert actual == [
            ("campaign", "STRING"),
            ("LINE", "STRING"),
            ("TIMESTAMP", "TIMESTAMP"),
            ("udid", "STRING"),
            ("devraw", "STRING"),
            ("country", "STRING"),
            ("city", "STRING"),
            ("latitude", "FLOAT64"),
            ("longitude", "FLOAT64"),
            ("dev_os", "STRING"),
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

    def test_schema_combined_unchanged(self, repo_root):
        mod = _load_ct_variables(repo_root)
        actual = [(f.name, f.field_type) for f in mod.schema_Combined]
        assert actual == [
            ("DID", "STRING"),
            ("Segment", "STRING"),
            ("Country", "STRING"),
            ("Controlled", "BOOLEAN"),
        ]


class TestMainNewDoesNotImportVariables:
    """main_new.py sources its configuration from shared/config/campaigns
    directly and must not import projects/campaign-tracker/variables.py
    at all -- this migration must not create a new coupling between the
    two entry points."""

    def test_main_new_source_does_not_reference_variables_module(self, repo_root):
        source = (
            repo_root / "projects" / "campaign-tracker" / "main_new.py"
        ).read_text(encoding="utf-8")
        assert "import variables" not in source
        assert "from variables" not in source


class TestImportableTheWayTheLegacyEntryPointLoadsIt:
    """Critical import guardrail (IH-048 follow-up, same class of check
    already applied to projects/poi/variables.py). main.py loads
    variables.py as a flat `from variables import *`, with no sys.path
    setup of its own -- it relies entirely on whatever sys.path Python
    already has when invoked. A direct script run (`python
    projects/campaign-tracker/main.py`, or `cd projects/campaign-tracker
    && python main.py`) puts ONLY that script's own directory on
    sys.path -- not the repository root.

    Not reproducible from inside the current pytest process:
    tests/conftest.py's session-scoped autouse fixture already added the
    repo root to sys.path for the whole test session (which would mask
    this exact bug), and `shared` may already be cached in sys.modules
    from other tests. Every test in this class runs a real, separate
    subprocess with only projects/campaign-tracker/ on sys.path.

    Only imports `variables`/`main` -- never calls `main()`,
    `create_client()`, or `metadata_placelift()` (would construct a real
    BigQuery client).
    """

    def _run_in_subprocess(self, cwd, ct_dir, import_target: str):
        code = (
            "import sys; sys.path.insert(0, sys.argv[1]); "
            f"import {import_target} as m; "
            "print('OK', m.project, m.dataset, m.dataset_metadata, "
            "m.table_mapping['KSA'], m.drive_link_folder_Adops)"
        )
        return subprocess.run(
            [sys.executable, "-c", code, str(ct_dir)],
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=30,
        )

    _EXPECTED_STDOUT = (
        "OK maddictdata Back_End_Reports Metadata POI_DB_KSA "
        "https://drive.google.com/drive/folders/1GuOSGxq5AlLxzaqbkzQBDQ8n7HcuhWWM"
    )

    def test_variables_importable_with_cwd_at_repo_root(self, repo_root):
        ct_dir = repo_root / "projects" / "campaign-tracker"
        result = self._run_in_subprocess(repo_root, ct_dir, "variables")
        assert result.returncode == 0, result.stderr
        assert self._EXPECTED_STDOUT in result.stdout

    def test_variables_importable_with_cwd_inside_campaign_tracker_directory(self, repo_root):
        """The scenario that actually fails without variables.py's own
        sys.path handling: an operator who `cd`s into
        projects/campaign-tracker/ before running `python main.py`."""
        ct_dir = repo_root / "projects" / "campaign-tracker"
        result = self._run_in_subprocess(ct_dir, ct_dir, "variables")
        assert result.returncode == 0, (
            f"variables.py failed to import with cwd=projects/campaign-tracker "
            f"(IH-048 follow-up guardrail): {result.stderr}"
        )
        assert self._EXPECTED_STDOUT in result.stdout

    def test_main_module_importable_with_cwd_inside_campaign_tracker_directory_without_calling_main(
        self, repo_root
    ):
        ct_dir = repo_root / "projects" / "campaign-tracker"
        result = self._run_in_subprocess(ct_dir, ct_dir, "main")
        assert result.returncode == 0, result.stderr
        assert self._EXPECTED_STDOUT in result.stdout
