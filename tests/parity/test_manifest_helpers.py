"""Tests for the parity manifest helpers themselves (tests/parity/manifest.py)."""
from __future__ import annotations

from tests.parity.manifest import (
    date_window_manifest,
    hash_csv_file_bytes,
    hash_csv_file_normalized,
    hash_did_set,
    hash_metadata_rows,
    served_control_disjointness_report,
)


def test_hash_metadata_rows_ignores_last_update_and_id_by_default():
    rows_a = [{"id": 1, "code_name": "143", "last_update": "2026-01-01T00:00:00"}]
    rows_b = [{"id": 2, "code_name": "143", "last_update": "2026-06-01T00:00:00"}]
    assert hash_metadata_rows(rows_a) == hash_metadata_rows(rows_b)


def test_hash_metadata_rows_is_order_independent():
    rows_a = [{"code_name": "1"}, {"code_name": "2"}]
    rows_b = [{"code_name": "2"}, {"code_name": "1"}]
    assert hash_metadata_rows(rows_a) == hash_metadata_rows(rows_b)


def test_hash_metadata_rows_detects_real_differences():
    rows_a = [{"code_name": "143", "status": "Active"}]
    rows_b = [{"code_name": "143", "status": "Finished"}]
    assert hash_metadata_rows(rows_a) != hash_metadata_rows(rows_b)


def test_hash_did_set_is_order_and_whitespace_independent():
    a = hash_did_set(["did-1\n", "did-2", " did-3 "])
    b = hash_did_set(["did-3", "did-2\n", "did-1"])
    assert a == b


def test_hash_csv_normalized_ignores_row_order_but_not_content(tmp_path):
    f1 = tmp_path / "a.csv"
    f1.write_text("DID\nx\ny\nz\n")
    f2 = tmp_path / "b.csv"
    f2.write_text("DID\nz\nx\ny\n")
    f3 = tmp_path / "c.csv"
    f3.write_text("DID\nx\ny\nq\n")

    assert hash_csv_file_normalized(f1) == hash_csv_file_normalized(f2)
    assert hash_csv_file_normalized(f1) != hash_csv_file_normalized(f3)


def test_hash_csv_bytes_is_order_sensitive(tmp_path):
    f1 = tmp_path / "a.csv"
    f1.write_text("DID\nx\ny\n")
    f2 = tmp_path / "b.csv"
    f2.write_text("DID\ny\nx\n")
    assert hash_csv_file_bytes(f1) != hash_csv_file_bytes(f2)


def test_served_control_disjointness_report_flags_ih_007_style_overlap():
    report = served_control_disjointness_report(
        served_by_segment={"CarOwners": ["did-1", "did-2", "did-3"]},
        control=["did-2"],
    )
    assert report["is_disjoint"] is False
    assert report["overlaps_by_segment"] == {"CarOwners": ["did-2"]}


def test_served_control_disjointness_report_passes_when_clean():
    report = served_control_disjointness_report(
        served_by_segment={"CarOwners": ["did-1", "did-3"]},
        control=["did-2"],
    )
    assert report["is_disjoint"] is True


def test_date_window_manifest_is_a_plain_dict():
    m = date_window_manifest("2026-01-01", "2026-01-10", "2025-12-01", "2025-12-31")
    assert m == {
        "start_date_q": "2026-01-01",
        "end_date_q": "2026-01-10",
        "start_date_before": "2025-12-01",
        "end_date_before": "2025-12-31",
    }
