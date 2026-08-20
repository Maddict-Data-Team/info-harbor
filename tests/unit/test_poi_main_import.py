"""
Smoke-import test for IH-036: projects/poi/main.py is a standalone module
added on this branch with no tests, no CI wiring, and (until now) no
verification that it even imports cleanly.

Only confirms the module loads and exposes its documented functions; does
not call any of them (create_client() would construct a real BigQuery
client). Deep correctness of the module's BigQuery write logic remains
unvalidated, per the audit's own "Needs Validation" framing -- this test
narrows, but does not close, that gap. No network, no credentials.
"""
from __future__ import annotations

from tests.conftest import import_module_from_path


def test_poi_main_imports_and_exposes_its_documented_functions(repo_root):
    path = repo_root / "projects" / "poi" / "main.py"
    mod = import_module_from_path("poi_main_under_test", path)

    for name in (
        "create_client",
        "get_country_id",
        "get_city_id",
        "table_exists",
        "create_poi_table",
        "get_max_poi_id",
        "insert_pois",
        "process_pois",
    ):
        assert hasattr(mod, name), f"projects/poi/main.py is missing expected function {name!r}"
        assert callable(getattr(mod, name))
