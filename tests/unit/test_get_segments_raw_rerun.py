"""
Regression test for IH-009: get_raw_segments() opened the per-segment raw
CSV in append mode ('a') and unconditionally wrote a "DID\\n" header on
every call, keyed only by a same-day timestamp in the filename. Rerunning
segment extraction for the same campaign/segment/country on the same day
appended a second header into the middle of the file and duplicated every
device ID already fetched.

Calls the real get_raw_segments() twice against a monkeypatched
query_orchestrator.run_query_behavior (no BigQuery), using the
isolated_segments_workspace fixture so it writes into a tmp_path, not the
repo's own data/ folder. No network, no credentials.
"""
from __future__ import annotations

import datetime
from types import SimpleNamespace

from tests.conftest import import_module_from_path


def _load(repo_root):
    path = repo_root / "projects" / "segments" / "scripts" / "get_segments_raw.py"
    return import_module_from_path("get_segments_raw_under_test", path)


def test_rerunning_the_same_day_does_not_duplicate_header_or_rows(
    repo_root, isolated_segments_workspace, monkeypatch
):
    mod = _load(repo_root)
    monkeypatch.setattr(mod, "table_mapping", {"UAE": 1}, raising=False)
    monkeypatch.setattr(mod, "code_name", 183, raising=False)

    dids = [f"did-{i:03d}" for i in range(10)]

    def fake_run_query_behavior(segment, bq_client, country, code_name):
        return [SimpleNamespace(DID=d) for d in dids]

    monkeypatch.setattr(mod.query_orchestrator, "run_query_behavior", fake_run_query_behavior)

    # First run, then a same-day rerun -- exactly the scenario IH-009 broke.
    mod.get_raw_segments(["UAE"], ["CarOwners"], bq_client=None)
    mod.get_raw_segments(["UAE"], ["CarOwners"], bq_client=None)

    now = datetime.datetime.now().strftime("%Y%m%d")
    raw_path = (
        isolated_segments_workspace
        / "projects" / "segments" / "data" / "raw"
        / f"183_UAE_CarOwners_{now}.csv"
    )
    lines = raw_path.read_text().splitlines()

    assert lines[0] == "DID"
    assert lines.count("DID") == 1, "header must not be duplicated on rerun (IH-009)"
    assert lines[1:] == dids, "rows must not be duplicated on rerun (IH-009)"
