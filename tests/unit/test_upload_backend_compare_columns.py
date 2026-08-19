"""
Pure-logic tests for projects/automation/upload_backend.compare_columns,
the CSV-vs-schema column validator added on this branch as part of the
IH (Fixed) stale-external-table remediation.
"""
from __future__ import annotations

from tests.conftest import import_automation_query_orchestrator  # noqa: F401 (path side effect)
from tests.conftest import import_module_from_path


def _load(repo_root):
    path = repo_root / "projects" / "automation" / "upload_backend.py"
    return import_module_from_path("upload_backend_under_test", path)


def test_exact_match_is_all_present(repo_root):
    mod = _load(repo_root)
    result = mod.compare_columns(["a", "b", "c"], ["a", "b", "c"])
    assert result["all_present"] is True
    assert result["missing"] == []
    assert result["extra"] == []


def test_missing_columns_are_reported(repo_root):
    mod = _load(repo_root)
    result = mod.compare_columns(["a"], ["a", "b", "c"])
    assert result["all_present"] is False
    assert result["missing"] == ["b", "c"]


def test_extra_columns_are_reported_but_do_not_block_all_present(repo_root):
    mod = _load(repo_root)
    result = mod.compare_columns(["a", "b", "c", "extra1"], ["a", "b", "c"])
    assert result["all_present"] is True
    assert result["extra"] == ["extra1"]


def test_expected_cols_derived_from_the_real_schema(repo_root):
    mod = _load(repo_root)
    names = [f.name for f in mod.schema_back_end]
    assert mod.EXPECTED_COLS == names
    assert "campaign" in names
    assert "udid_idfa" in names
