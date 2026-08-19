"""
Pure-function characterization tests for
projects/automation/query_orchestrator.get_run_dates.

get_run_dates has no I/O beyond datetime.today() (the current wall clock),
so these tests inject a frozen "today" via monkeypatch on the datetime
class used inside the module -- WITHOUT changing production code (the
function itself is not modified; only the test process's view of "now"
is patched for the duration of each test).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from tests.conftest import import_automation_query_orchestrator


@pytest.fixture
def orchestrator():
    return import_automation_query_orchestrator()


class _FrozenDatetime(datetime):
    _frozen_now: datetime

    @classmethod
    def today(cls):
        return cls._frozen_now

    @classmethod
    def now(cls, tz=None):
        return cls._frozen_now


def _freeze(monkeypatch, orchestrator, when: datetime):
    frozen = type("Frozen", (_FrozenDatetime,), {"_frozen_now": when})
    monkeypatch.setattr(orchestrator, "datetime", frozen)
    return frozen


def test_happy_path_window_is_today_minus_nine_days(monkeypatch, orchestrator):
    _freeze(monkeypatch, orchestrator, datetime(2026, 3, 20))
    start_q, end_q, start_before, end_before = orchestrator.get_run_dates(
        end_date=date(2026, 6, 1),
        last_update=date(2026, 3, 10),
        start_date=date(2026, 1, 1),
        interval=7,
    )
    assert end_q == "2026-03-11"  # today - 9 days
    assert start_q == "2026-03-01"  # last_update - 9 days


def test_end_date_clamp_when_campaign_ended_over_a_week_ago(monkeypatch, orchestrator):
    """end_date_q is clamped to end_date + 7 days when today - 9 days would
    otherwise run past it (query_orchestrator.py:350-351)."""
    _freeze(monkeypatch, orchestrator, datetime(2026, 6, 1))
    start_q, end_q, _start_before, _end_before = orchestrator.get_run_dates(
        end_date=date(2026, 3, 1),
        last_update=date(2026, 2, 20),
        start_date=date(2026, 1, 1),
        interval=7,
    )
    assert end_q == "2026-03-08"  # end_date + 7, not today - 9


def test_start_date_floor_when_last_update_predates_campaign_start(
    monkeypatch, orchestrator
):
    """start_date_q is floored at start_date when last_update - 9 days
    would otherwise precede it (query_orchestrator.py:355-356)."""
    _freeze(monkeypatch, orchestrator, datetime(2026, 2, 1))
    start_q, _end_q, _start_before, _end_before = orchestrator.get_run_dates(
        end_date=date(2026, 6, 1),
        last_update=date(2026, 1, 3),
        start_date=date(2026, 1, 1),
        interval=7,
    )
    assert start_q == "2026-01-01"


def test_before_baseline_lengthens_every_call_relative_to_start_date(
    monkeypatch, orchestrator
):
    """IH: get_run_dates:361-366 recomputes start_date_before as
    start_date - (end_date_q - start_date), so successive calls with a
    later "today" produce a LONGER comparison baseline for the same
    campaign, not a fixed one. This characterizes current behavior; it
    does not assert this is correct. # BUG: IH (baseline lengthens on rerun)
    """
    start_date = date(2026, 1, 1)
    end_date = date(2026, 12, 1)

    _freeze(monkeypatch, orchestrator, datetime(2026, 2, 1))
    _s1, _e1, before1, _eb1 = orchestrator.get_run_dates(
        end_date=end_date, last_update=start_date, start_date=start_date, interval=7
    )

    _freeze(monkeypatch, orchestrator, datetime(2026, 4, 1))
    _s2, _e2, before2, _eb2 = orchestrator.get_run_dates(
        end_date=end_date, last_update=start_date, start_date=start_date, interval=7
    )

    d1 = date.fromisoformat(before1)
    d2 = date.fromisoformat(before2)
    assert d2 < d1, "later re-runs should push the baseline earlier under current logic"


def test_time_interval_parameter_does_not_affect_the_result(monkeypatch, orchestrator):
    """IH: `interval` is accepted but never referenced inside get_run_dates
    (query_orchestrator.py:340-346) -- the 9-day lag is hardcoded. This
    test proves the parameter is inert; it is a regression guard, not an
    endorsement. # BUG: IH (time_interval unused in date window)
    """
    _freeze(monkeypatch, orchestrator, datetime(2026, 3, 20))
    kwargs = dict(end_date=date(2026, 6, 1), last_update=date(2026, 3, 10), start_date=date(2026, 1, 1))
    result_a = orchestrator.get_run_dates(interval=1, **kwargs)
    result_b = orchestrator.get_run_dates(interval=999, **kwargs)
    assert result_a == result_b
