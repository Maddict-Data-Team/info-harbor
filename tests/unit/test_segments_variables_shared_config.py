"""
Phase 2d (IH-048 follow-up): projects/segments/scripts/variables.py's
primitive/shared values now delegate to shared/config/settings.py instead
of hardcoding their own copies. schema_DID, schema_back_end, and
schema_Combined are untouched. table_mapping and static_query_replace stay
plain mutable dicts; poi_filter_fields stays a list. main.py, main_new.py,
input.py, every worker script, ui/app.py, campaign_manager.py, and
queries.ini are all unmodified.

Unlike projects/poi/ and projects/campaign-tracker/'s legacy path, this
file has REAL active callers (main.py, main_new.py, wired into ui/app.py
and campaign_manager.py) -- the values and behavior of every caller remain
identical; only where the primitive values are sourced from changes.

IH-001 (wrong-campaign global override in query_orchestrator.build_query)
is a separate, still-open, pre-existing defect, deliberately NOT touched
or fixed as part of this configuration-only migration. This file does not
re-characterize it; tests/unit/test_segments_wrong_campaign_global.py
already does, and running the full suite (which includes it) confirms this
migration didn't change its behavior either way.

No test in this file constructs a real Google client or touches network/
credentials: variables.py only imports `bigquery` for `SchemaField`
objects, never a client; delete_from_drive.py's DELETE_MODE stays False
(IH-028) and is never invoked; no operational function
(main(), split_files(), transfer_files_to_drive(), run_push_to_bq(),
authenticate_get_clients(), create_BER_Table(), reset_folders(),
get_raw_segments(), or anything in delete_from_drive.py) is ever called.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys

from tests.conftest import import_module_from_path


def _load_segments_variables(repo_root):
    path = repo_root / "projects" / "segments" / "scripts" / "variables.py"
    return import_module_from_path("segments_variables_under_test", path)


class TestDelegatedValuesMatchSharedSettings:
    """Every primitive value now sourced from shared/config/settings.py
    must be identical to what projects/segments/scripts/variables.py
    hardcoded before this migration (docs/code-audit.md IH-048's
    original evidence for this file, lines 5-49,92-112)."""

    def test_project_and_datasets(self, repo_root):
        from shared.config import settings

        mod = _load_segments_variables(repo_root)
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
        assert mod.dataset_HWG == settings.DATASET_AUTOMATED_HWG == "Automated_HWG"

    def test_tables(self, repo_root):
        from shared.config import settings

        mod = _load_segments_variables(repo_root)
        assert mod.table_placelift == settings.TABLE_PLACELIFT == "Placelift"
        assert mod.table_HG == settings.TABLE_HOME_GRAPH == "Home_Graph_Cumulative"
        assert mod.table_WG == settings.TABLE_WORK_GRAPH == "Work_Graph_Cumulative"
        assert mod.table_hwg_pol_map == settings.TABLE_HWG_POL_MAPPING == "All_Pols_Mapping"

    def test_dir_and_legacy_keys(self, repo_root):
        from shared.config import settings

        mod = _load_segments_variables(repo_root)
        assert mod.dir_data == settings.SEGMENTS_DATA_DIR == "projects/segments/data"
        assert mod.key_bq == settings.LEGACY_BIGQUERY_KEY_PATH == "keys/maddictdata-bq.json"
        assert (
            mod.key_google_sheets
            == settings.LEGACY_GOOGLE_SHEETS_KEY_PATH
            == "keys/maddictdata-google-sheets.json"
        )

    def test_drive_folder_matches_the_segments_adops_url_not_the_tracker_one(self, repo_root):
        """Segments' Drive folder is the AdOps location -- distinct from
        Campaign Tracker's separate legacy URL (Phase 2c). Must not be
        collapsed into the wrong one."""
        from shared.config import settings

        mod = _load_segments_variables(repo_root)
        assert mod.MAIN_DRIVE_FOLDER_ID == settings.DRIVE_MAIN_FOLDER_ID
        assert (
            mod.drive_link_folder_Adops
            == settings.DRIVE_ADOPS_FOLDER_URL
            == "https://drive.google.com/drive/folders/1HEJQ-0gc8VgICB6NK2yZO-aBweuTVrRf"
        )
        assert mod.drive_link_folder_Adops != settings.LEGACY_CAMPAIGN_TRACKER_DRIVE_FOLDER_URL

    def test_secrets(self, repo_root):
        from shared.config import settings

        mod = _load_segments_variables(repo_root)
        assert mod.secret_ber == settings.SECRET_BACKEND_REPORT_TOKEN
        assert mod.secret_bq == settings.SECRET_BIGQUERY_CREDENTIALS

    def test_table_mapping_matches_settings_and_stays_a_plain_mutable_dict(self, repo_root):
        """Segments intentionally supports 7 countries -- one fewer than
        Campaign Tracker/POI's 8 (no MAR). Must preserve exactly that
        set, not silently broaden or narrow it."""
        from shared.config import settings

        mod = _load_segments_variables(repo_root)
        assert mod.table_mapping == dict(settings.SEGMENTS_COUNTRY_POI_TABLES)
        assert mod.table_mapping == {
            "KSA": "POI_DB_KSA",
            "UAE": "POI_DB_UAE",
            "QAT": "POI_DB_QTR",
            "KWT": "POI_DB_KWT",
            "OMN": "POI_DB_OMN",
            "BHR": "POI_DB_BHR",
            "EGY": "POI_DB_EGP",
        }
        assert "MAR" not in mod.table_mapping
        assert type(mod.table_mapping) is dict
        mod.table_mapping["TEST"] = "should not raise"  # would raise on a MappingProxyType

    def test_static_query_replace_matches_settings_and_stays_a_plain_mutable_dict(self, repo_root):
        from shared.config import settings

        mod = _load_segments_variables(repo_root)
        assert mod.static_query_replace == settings.SEGMENTS_QUERY_REPLACEMENTS
        assert mod.static_query_replace == {
            "{hwg_dataset}": "Automated_HWG",
            "{footfall_dataset}": "Back_End_Footfall",
            "{project}": "maddictdata",
            "{location_signals_dataset}": "Location_Signals",
            "{hg_table}": "Home_Graph_Cumulative",
            "{wg_table}": "Work_Graph_Cumulative",
            "{pol_map_table}": "All_Pols_Mapping",
        }
        assert type(mod.static_query_replace) is dict
        mod.static_query_replace["{TEST}"] = "should not raise"

    def test_poi_filter_fields_matches_settings_and_stays_a_list(self, repo_root):
        from shared.config import settings

        mod = _load_segments_variables(repo_root)
        assert tuple(mod.poi_filter_fields) == settings.POI_FILTER_FIELDS
        assert mod.poi_filter_fields == [
            "General_Category",
            "Category",
            "Subcategory",
            "GM_Subcategory",
            "Chain",
        ]
        assert type(mod.poi_filter_fields) is list


class TestSchemasUnchanged:
    """schema_DID, schema_back_end, and schema_Combined are explicitly
    out of scope for this migration -- must remain the exact same
    SchemaField lists as before."""

    def test_schema_did_unchanged(self, repo_root):
        mod = _load_segments_variables(repo_root)
        actual = [(f.name, f.field_type) for f in mod.schema_DID]
        assert actual == [("DID", "STRING")]

    def test_schema_back_end_unchanged(self, repo_root):
        mod = _load_segments_variables(repo_root)
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

    def test_schema_combined_unchanged(self, repo_root):
        mod = _load_segments_variables(repo_root)
        actual = [(f.name, f.field_type) for f in mod.schema_Combined]
        assert actual == [
            ("DID", "STRING"),
            ("Segment", "STRING"),
            ("Country", "STRING"),
            ("Controlled", "BOOLEAN"),
        ]


class TestBothLoadingStylesResolveSharedSettings:
    """Two different loading styles are used across projects/segments/
    scripts/: a flat `from variables import *` (split_segments.py,
    create_be_table.py) and importlib.util.spec_from_file_location under
    alias "variables_local" (get_segments_raw.py, query_orchestrator.py,
    authenticate_to_cloud.py, transfer_to_drive.py, push_to_bq.py,
    delete_from_drive.py). Both must resolve `shared.config.settings`
    correctly -- tested here in isolation, independent of any specific
    caller file."""

    def test_flat_import_style_resolves_shared_settings(self, repo_root, monkeypatch):
        """A plain `import variables` checks sys.modules['variables']
        before sys.path at all -- projects/poi/main.py (and others) do
        their own flat `from variables import *`, so an earlier test in
        the same session can leave a DIFFERENT project's variables.py
        cached under this exact plain name (the same class of collision
        as IH-047, just against projects/poi/ this time instead of
        projects/automation/). Force a fresh resolution regardless of
        what an earlier test left behind, and restore afterward so this
        test doesn't itself become the polluter for a later one."""
        monkeypatch.syspath_prepend(str(repo_root))
        scripts_dir = repo_root / "projects" / "segments" / "scripts"
        monkeypatch.syspath_prepend(str(scripts_dir))

        pre_existing = sys.modules.pop("variables", None)
        try:
            namespace: dict = {}
            exec("from variables import *", namespace)  # noqa: S102 -- mirrors the real caller's own statement
            assert namespace["project"] == "maddictdata"
            assert namespace["dataset_metadata"] == "Metadata"
        finally:
            if pre_existing is None:
                sys.modules.pop("variables", None)
            else:
                sys.modules["variables"] = pre_existing

    def test_spec_from_file_location_style_resolves_shared_settings(self, repo_root):
        path = repo_root / "projects" / "segments" / "scripts" / "variables.py"
        spec = importlib.util.spec_from_file_location("variables_local", path)
        variables_local = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(variables_local)
        assert variables_local.project == "maddictdata"
        assert variables_local.secret_ber == "projects/maddictdata/secrets/token-ber/versions/latest"


class TestCallersImportableTheWayTheyRealyLoadVariables:
    """Critical import guardrail (IH-048 follow-up, same class of check
    already applied to POI and Campaign Tracker). Neither loading style
    projects/segments/scripts/*.py uses puts the repository root on
    sys.path, and this file's own directory is the only thing
    guaranteed reachable. A direct script run (`python
    projects/segments/main.py`, or `cd projects/segments && python
    main.py`) puts ONLY that script's own directory on sys.path.

    Not reproducible from inside the current pytest process: tests/
    conftest.py's session-scoped autouse fixture already added the repo
    root to sys.path for the whole test session (which would mask this
    exact bug). Every test in this class runs a real, separate
    subprocess.

    main.py (old) transitively exercises 7 of the 8 listed callers
    (reset_folders, get_segments_raw, split_segments, transfer_to_drive,
    push_to_bq, authenticate_to_cloud, create_be_table) plus
    query_orchestrator.py (imported internally by get_segments_raw.py).
    main_new.py exercises the same 7 via dotted imports.
    delete_from_drive.py is never imported by either entry point (a
    deliberately standalone, dangerous script per IH-028) and is
    verified separately, standalone.

    Several of these worker scripts also do `from input import *`;
    when imported standalone (not via main.py/main_new.py, which import
    input.py first) that can raise ModuleNotFoundError for 'input' --
    a PRE-EXISTING characteristic unrelated to this variables.py
    migration. This class verifies each caller through the same
    sequence its real entry point actually uses, not in isolation, so
    it measures whether *this* migration broke anything, not whether
    an unrelated, already-existing import quirk exists.

    No test calls main(), create_client(), split_files(),
    transfer_files_to_drive(), run_push_to_bq(),
    authenticate_get_clients(), create_BER_Table(), reset_folders(),
    get_raw_segments(), or anything in delete_from_drive.py.
    """

    def _cwd_scenarios(self, repo_root):
        return [
            repo_root,
            repo_root / "projects" / "segments",
            repo_root / "projects" / "segments" / "scripts",
        ]

    def test_main_py_real_import_sequence_across_all_cwd_scenarios(self, repo_root):
        segments_dir = repo_root / "projects" / "segments"
        code = (
            "import sys; sys.path.insert(0, sys.argv[1]); import main; "
            "assert callable(main.reset_folders); "
            "assert callable(main.get_raw_segments); "
            "assert callable(main.split_files); "
            "assert callable(main.transfer_files_to_drive); "
            "assert callable(main.run_push_to_bq); "
            "assert callable(main.authenticate_get_clients); "
            "assert callable(main.create_BER_Table); "
            "print('OK')"
        )
        for cwd in self._cwd_scenarios(repo_root):
            result = subprocess.run(
                [sys.executable, "-c", code, str(segments_dir)],
                capture_output=True,
                text=True,
                cwd=str(cwd),
                timeout=30,
            )
            assert result.returncode == 0, (
                f"main.py's real import sequence failed with cwd={cwd} "
                f"(IH-048 follow-up guardrail): {result.stderr}"
            )
            assert "OK" in result.stdout

    def test_main_new_importable_across_all_cwd_scenarios(self, repo_root):
        code = (
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "import projects.segments.main_new as m; "
            "assert callable(m.main); print('OK')"
        )
        for cwd in self._cwd_scenarios(repo_root):
            result = subprocess.run(
                [sys.executable, "-c", code, str(repo_root)],
                capture_output=True,
                text=True,
                cwd=str(cwd),
                timeout=30,
            )
            assert result.returncode == 0, (
                f"main_new.py failed to import with cwd={cwd}: {result.stderr}"
            )
            assert "OK" in result.stdout

    def test_delete_from_drive_importable_standalone_across_all_cwd_scenarios(self, repo_root):
        """The one named caller not reachable via main.py/main_new.py --
        verified on its own. Does not depend on input.py (wrapped in its
        own try/except), so this is a true standalone import, matching
        how an operator would invoke it directly."""
        scripts_dir = repo_root / "projects" / "segments" / "scripts"
        code = (
            "import sys; sys.path.insert(0, sys.argv[1]); import delete_from_drive as m; "
            "assert m.project == 'maddictdata'; "
            "assert m.DELETE_MODE is False; "  # IH-028: must stay safe by default
            "print('OK')"
        )
        for cwd in self._cwd_scenarios(repo_root):
            result = subprocess.run(
                [sys.executable, "-c", code, str(scripts_dir)],
                capture_output=True,
                text=True,
                cwd=str(cwd),
                timeout=30,
            )
            assert result.returncode == 0, (
                f"delete_from_drive.py failed to import with cwd={cwd} "
                f"(IH-048 follow-up guardrail): {result.stderr}"
            )
            assert "OK" in result.stdout
