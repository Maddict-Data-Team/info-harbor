"""
Regression test for IH-044: navigate_and_search_file()'s month_name
parameter defaulted to datetime.now().strftime("%B") in the function
signature, which Python evaluates once at function-definition time
(module import), not per call. On a warm Cloud Function instance reused
across a month boundary, every call omitting month_name would keep
searching the *previous* month's Drive folder indefinitely, with no error
-- just an increasingly wrong "no backend report found" result.

Freezes the module's `datetime` name the same way
test_get_run_dates.py does (a subclass with a fixed `.now()`), and checks
which month name reaches the Drive query -- no real Drive service, no
network, no credentials.
"""
from __future__ import annotations

from datetime import datetime

from tests.conftest import import_automation_query_orchestrator  # noqa: F401 (path side effect)
from tests.conftest import import_module_from_path


def _load(repo_root):
    path = repo_root / "projects" / "automation" / "upload_backend.py"
    return import_module_from_path("upload_backend_under_test_ih044", path)


class _FrozenDatetime(datetime):
    _frozen_now: datetime

    @classmethod
    def now(cls, tz=None):
        return cls._frozen_now


def _freeze(monkeypatch, mod, when: datetime):
    frozen = type("Frozen", (_FrozenDatetime,), {"_frozen_now": when})
    monkeypatch.setattr(mod, "datetime", frozen)


class _FakeExecutable:
    def __init__(self, result):
        self._result = result

    def execute(self):
        return self._result


class _RecordingFilesResource:
    def __init__(self, queries, responses):
        self._queries = queries
        self._responses = responses

    def list(self, q, fields=None):
        self._queries.append(q)
        index = len(self._queries) - 1
        result = self._responses[index] if index < len(self._responses) else {"files": []}
        return _FakeExecutable(result)


class _RecordingDriveService:
    def __init__(self, queries, responses):
        self._queries = queries
        self._responses = responses

    def files(self):
        return _RecordingFilesResource(self._queries, self._responses)


def _month_searched_with_default_month_name(mod, when: datetime) -> str:
    """Calls navigate_and_search_file with no month_name (using its
    default), against a fake service that finds the year folder but not
    the month folder, and returns the month string that reached the
    second (month-lookup) Drive query."""
    queries: list[str] = []
    responses = [
        {"files": [{"id": "year-folder-id", "name": str(when.year)}]},
        {"files": []},
    ]
    service = _RecordingDriveService(queries, responses)

    mod.navigate_and_search_file(service, "backend-reports-folder-id", "1001")

    month_query = queries[1]
    return month_query


def test_default_month_name_reflects_the_current_call_time_not_import_time(
    repo_root, monkeypatch
):
    mod = _load(repo_root)

    _freeze(monkeypatch, mod, datetime(2026, 1, 15))
    january_query = _month_searched_with_default_month_name(mod, datetime(2026, 1, 15))
    assert "'January'" in january_query

    _freeze(monkeypatch, mod, datetime(2026, 6, 15))
    june_query = _month_searched_with_default_month_name(mod, datetime(2026, 6, 15))
    assert "'June'" in june_query, (
        "navigate_and_search_file's default month_name must reflect the "
        "current call time, not whatever month it was when the module "
        "was first imported (IH-044)"
    )
