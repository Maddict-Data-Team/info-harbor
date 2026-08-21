"""
Phase 2b (IH-048 follow-up, IH-036): projects/poi/variables.py's primitive
values now delegate to shared/config/settings.py instead of hardcoding
their own copies. schema_poi is untouched (not a "primitive configuration
value" -- structural BigQuery schema, explicitly out of scope). No call
in this file constructs a real Google client or touches network/
credentials: variables.py only imports `bigquery` for `SchemaField`
objects (plain data classes), never a client.
"""
from __future__ import annotations

import subprocess
import sys

from tests.conftest import import_module_from_path


def _load_poi_variables(repo_root):
    path = repo_root / "projects" / "poi" / "variables.py"
    return import_module_from_path("poi_variables_under_test", path)


class TestDelegatedValuesMatchSharedSettings:
    """Every primitive value poi/variables.py now sources from
    shared/config/settings.py must be identical to what it hardcoded
    before this migration (docs/code-audit.md IH-048's original evidence
    for projects/poi/variables.py:4-28)."""

    def test_project_and_datasets(self, repo_root):
        from shared.config import settings

        mod = _load_poi_variables(repo_root)
        assert mod.project == settings.PROJECT_ID == "maddictdata"
        assert mod.dataset_footfall == settings.DATASET_FOOTFALL == "Back_End_Footfall"
        # POI intentionally differs from automation/tracker/segments here.
        assert mod.dataset_metadata == settings.DATASET_POI_LOOKUPS == "Lookups"

    def test_key_bq_legacy_path(self, repo_root):
        from shared.config import settings

        mod = _load_poi_variables(repo_root)
        assert mod.key_bq == settings.LEGACY_BIGQUERY_KEY_PATH == "keys/maddictdata-bq.json"

    def test_lookup_tables(self, repo_root):
        from shared.config import settings

        mod = _load_poi_variables(repo_root)
        assert mod.lookup_country_table == settings.TABLE_COUNTRY_LOOKUP == "lu_country"
        assert mod.lookup_city_table == settings.TABLE_CITY_LOOKUP == "lu_city"

    def test_table_mapping_matches_settings_and_stays_a_plain_mutable_dict(self, repo_root):
        from shared.config import settings

        mod = _load_poi_variables(repo_root)
        assert mod.table_mapping == dict(settings.POI_COUNTRY_POI_TABLES)
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
        # mapping -- preserve exact behavior, including mutability, for
        # anything that might assign into it.
        assert type(mod.table_mapping) is dict
        mod.table_mapping["TEST"] = "should not raise"  # would raise on a MappingProxyType


class TestSchemaPoiUnchanged:
    """schema_poi is explicitly out of scope for this migration -- must
    remain the exact same list of SchemaField objects as before."""

    def test_schema_poi_field_names_and_types_unchanged(self, repo_root):
        mod = _load_poi_variables(repo_root)
        actual = [(f.name, f.field_type) for f in mod.schema_poi]
        assert actual == [
            ("POI_ID", "INT64"),
            ("poi_name", "STRING"),
            ("longitude", "FLOAT64"),
            ("latitude", "FLOAT64"),
            ("country", "STRING"),
            ("city", "STRING"),
            ("country_id", "INT64"),
            ("city_id", "INT64"),
            ("radius", "INT64"),
        ]


class TestImportableTheWayTheStandaloneEntryPointLoadsIt:
    """Critical import guardrail (IH-048 follow-up). projects/poi/main.py
    loads variables.py as a flat `from variables import *`, with no
    sys.path setup of its own -- it relies entirely on whatever sys.path
    Python already has when it's invoked. A direct script run
    (`python projects/poi/main.py`, or `cd projects/poi && python
    main.py`) puts ONLY that script's own directory on sys.path -- not
    the repository root.

    This is NOT reproducible from inside the current pytest process:
    tests/conftest.py's session-scoped autouse fixture already added the
    repo root to sys.path for the whole test session (which would mask
    exactly this bug), and `shared` may already be cached in
    sys.modules from other tests (Python checks sys.modules before
    sys.path at all). Both process each test in this class runs a real,
    separate subprocess with only projects/poi/ on sys.path, confirming
    `from shared.config import settings` resolves regardless of the
    caller's current working directory -- empirically confirmed to FAIL
    before variables.py added its own repo-root sys.path handling (see
    docs/modernization-log.md).

    Only imports `variables`/`main` -- never calls `main()` or
    `process_pois()` (would construct a real BigQuery client).
    """

    def _run_in_subprocess(self, cwd, poi_dir, import_target: str):
        code = (
            "import sys; sys.path.insert(0, sys.argv[1]); "
            f"import {import_target} as m; "
            "print('OK', m.project, m.dataset_footfall, m.dataset_metadata, "
            "m.table_mapping['KSA'], m.lookup_country_table)"
        )
        return subprocess.run(
            [sys.executable, "-c", code, str(poi_dir)],
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=30,
        )

    def test_variables_importable_with_cwd_at_repo_root(self, repo_root):
        poi_dir = repo_root / "projects" / "poi"
        result = self._run_in_subprocess(repo_root, poi_dir, "variables")
        assert result.returncode == 0, result.stderr
        assert "OK maddictdata Back_End_Footfall Lookups POI_DB_KSA lu_country" in result.stdout

    def test_variables_importable_with_cwd_inside_poi_directory(self, repo_root):
        """The scenario that actually fails without variables.py's own
        sys.path handling: an operator who `cd`s into projects/poi/
        before running `python main.py` -- a plausible, ordinary way to
        invoke a script literally named main.py."""
        poi_dir = repo_root / "projects" / "poi"
        result = self._run_in_subprocess(poi_dir, poi_dir, "variables")
        assert result.returncode == 0, (
            f"variables.py failed to import with cwd=projects/poi (IH-048 "
            f"follow-up guardrail): {result.stderr}"
        )
        assert "OK maddictdata Back_End_Footfall Lookups POI_DB_KSA lu_country" in result.stdout

    def test_main_module_importable_with_cwd_inside_poi_directory_without_calling_main(
        self, repo_root
    ):
        poi_dir = repo_root / "projects" / "poi"
        result = self._run_in_subprocess(poi_dir, poi_dir, "main")
        assert result.returncode == 0, result.stderr
        assert "OK maddictdata Back_End_Footfall Lookups POI_DB_KSA lu_country" in result.stdout
