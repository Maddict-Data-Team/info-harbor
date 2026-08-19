"""
Canned Campaign_Tracker metadata rows for offline tests.

These mirror the columns selected by [Setup] query_metadata in
projects/automation/queries.ini:

    end_date, type, country, time_interval, last_update, backend_report,
    segments, start_date

Each fixture returns a list of row-like objects (one per country, matching
how one code_name can have multiple Campaign_Tracker rows -- one per
country) using SimpleNamespace, since the real code only ever does
attribute access on BigQuery Row objects (`row.type`, `row.end_date`, ...),
never dict-style access, for these code paths.
"""
from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace


def _row(**kwargs) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)


def placelift_no_ber_113() -> list[SimpleNamespace]:
    """The exact IH-005 reproduction case given by the project owner:
    code_name=113, type="Placelift NO BER", backend_report=0, segments=1.
    """
    return [
        _row(
            end_date=date(2026, 3, 1),
            type="Placelift NO BER",
            country="UAE",
            time_interval=7,
            last_update=datetime(2026, 2, 20, 9, 0, 0),
            backend_report=0,
            segments=1,
            start_date=date(2026, 1, 1),
        )
    ]


def retail_intelligence_dashboard_144() -> list[SimpleNamespace]:
    """Reproduces IH-006: campaign_144_retail.py sets
    type="Retail Intelligence Dashboard", but the only matching queries.ini
    section is "[Retail Intelligence]" (no "Dashboard").
    """
    return [
        _row(
            end_date=date(2026, 4, 1),
            type="Retail Intelligence Dashboard",
            country="KSA",
            time_interval=7,
            last_update=datetime(2026, 3, 15, 9, 0, 0),
            backend_report=1001,
            segments=0,
            start_date=date(2026, 2, 1),
        ),
        _row(
            end_date=date(2026, 4, 1),
            type="Retail Intelligence Dashboard",
            country="UAE",
            time_interval=7,
            last_update=datetime(2026, 3, 15, 9, 0, 0),
            backend_report=1002,
            segments=0,
            start_date=date(2026, 2, 1),
        ),
    ]


def plain_placelift_with_ber_and_segments_143() -> list[SimpleNamespace]:
    """type="Placelift" with a real backend_report and segments -> should
    resolve to the "Placelift" section (the full happy path)."""
    return [
        _row(
            end_date=date(2026, 3, 20),
            type="Placelift",
            country="UAE",
            time_interval=-1,
            last_update=datetime(2026, 2, 25, 9, 0, 0),
            backend_report=64303,
            segments=1,
            start_date=date(2026, 1, 5),
        )
    ]


def placelift_no_segments_via_normalizer() -> list[SimpleNamespace]:
    """type="Placelift Report" with segments=0 -> normalizer should route
    this to "Placelift No Segments" (queries.ini section exists)."""
    return [
        _row(
            end_date=date(2026, 3, 20),
            type="Placelift Report",
            country="KWT",
            time_interval=-1,
            last_update=datetime(2026, 2, 25, 9, 0, 0),
            backend_report=5001,
            segments=0,
            start_date=date(2026, 1, 5),
        )
    ]


def placelift_no_ber_via_normalizer() -> list[SimpleNamespace]:
    """type="Standard Placelift" with backend_report=0, segments=1 ->
    normalizer SHOULD route this to "Placelift No BER" (contrast with
    placelift_no_ber_113 above, where the metadata author wrote the target
    section name directly and it broke)."""
    return [
        _row(
            end_date=date(2026, 3, 20),
            type="Standard Placelift",
            country="QAT",
            time_interval=-1,
            last_update=datetime(2026, 2, 25, 9, 0, 0),
            backend_report=0,
            segments=1,
            start_date=date(2026, 1, 5),
        )
    ]


def ooh_multi_country_145() -> list[SimpleNamespace]:
    """Multi-country OOH campaign fixture."""
    countries = ["UAE", "QAT", "KWT"]
    backend_reports = [2001, 2002, 2003]
    return [
        _row(
            end_date=date(2026, 5, 1),
            type="OOH",
            country=c,
            time_interval=7,
            last_update=datetime(2026, 4, 1, 9, 0, 0),
            backend_report=br,
            segments=0,
            start_date=date(2026, 3, 1),
        )
        for c, br in zip(countries, backend_reports)
    ]


def unknown_type_null_metadata() -> list[SimpleNamespace]:
    """Mirrors shared/config/campaigns/database_loader.py:78, which emits
    type='Unknown' when the BigQuery `type` column is NULL."""
    return [
        _row(
            end_date=date(2026, 6, 1),
            type="Unknown",
            country="OMN",
            time_interval=-1,
            last_update=datetime(2026, 5, 1, 9, 0, 0),
            backend_report=0,
            segments=0,
            start_date=date(2026, 4, 1),
        )
    ]
