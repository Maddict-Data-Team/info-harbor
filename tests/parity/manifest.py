"""
Parity manifest helpers -- hashing/normalization utilities used to prove
"same results" between a baseline run and a refactored run, per
docs/modernization-spec.md's Compatibility Contract.

These are NEW test-support utilities, not extracted from and not calling
production code. They compute hashes/manifests OVER data that a real (or
fixture) pipeline run would have already produced (metadata rows, DID
lists, CSV files) -- they never invoke BigQuery/Drive themselves.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))


def hash_metadata_rows(
    rows: Sequence[Mapping[str, Any]], *, ignore_fields: Sequence[str] = ("last_update", "id")
) -> str:
    """Hash Campaign_Tracker-shaped rows, excluding fields that are
    inherently non-deterministic across runs (last_update: wall clock;
    id: table-state-dependent, see docs/code-audit.md compatibility
    contract notes) unless the caller overrides `ignore_fields`.
    """
    cleaned = []
    for row in rows:
        cleaned.append({k: v for k, v in row.items() if k not in ignore_fields})
    cleaned.sort(key=_stable_json)
    return hashlib.sha256(_stable_json(cleaned).encode("utf-8")).hexdigest()


def hash_did_set(dids: Iterable[str]) -> str:
    """Order-independent hash of a DID collection -- proves logical
    equivalence even if two implementations iterate in different order."""
    normalized = sorted(d.strip() for d in dids)
    return hashlib.sha256("\n".join(normalized).encode("utf-8")).hexdigest()


def hash_csv_file_normalized(path: Path) -> str:
    """Order-independent, header-stripped hash of a CSV file's DID column.
    Use alongside hash_csv_file_bytes to distinguish "same data, different
    order" from "actually different data".
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    body = sorted(line.strip() for line in lines[1:] if line.strip())
    return hashlib.sha256("\n".join(body).encode("utf-8")).hexdigest()


def hash_csv_file_bytes(path: Path) -> str:
    """Byte-exact hash. NOT portable across platforms if line endings
    differ (CRLF on Windows vs LF on Linux) -- record that fact in the
    manifest rather than assuming portability."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def served_control_disjointness_report(
    served_by_segment: Mapping[str, Iterable[str]], control: Iterable[str]
) -> dict:
    """Computes the invariant every served/control split must satisfy:
    each served segment and the control group must not overlap. Returns a
    report rather than asserting, so callers can decide whether to treat a
    violation as a known bug (IH-007) or a real regression.
    """
    control_set = {d.strip() for d in control}
    overlaps = {}
    for name, dids in served_by_segment.items():
        served_set = {d.strip() for d in dids}
        overlap = served_set & control_set
        if overlap:
            overlaps[name] = sorted(overlap)
    return {
        "is_disjoint": not overlaps,
        "overlaps_by_segment": overlaps,
        "control_size": len(control_set),
    }


def date_window_manifest(start_date_q: str, end_date_q: str, start_date_before: str, end_date_before: str) -> dict:
    return {
        "start_date_q": start_date_q,
        "end_date_q": end_date_q,
        "start_date_before": start_date_before,
        "end_date_before": end_date_before,
    }
