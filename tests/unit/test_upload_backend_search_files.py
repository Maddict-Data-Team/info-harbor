"""
Regression test for IH-021: projects/automation/upload_backend.py's
search_files_in_folder() used only a Drive `name contains '{file_prefix}'`
query, with no anchoring. A backend-report id that is a substring of
another report id (e.g. "1001" inside "21001_report.csv") could match the
wrong file and, combined with the append/dedupe flow, merge another
campaign's backend data into the wrong campaign's table.

Pure-logic and offline-only: no real Drive service is used.
"""
from __future__ import annotations

from tests.conftest import import_automation_query_orchestrator  # noqa: F401 (path side effect)
from tests.conftest import import_module_from_path


def _load(repo_root):
    path = repo_root / "projects" / "automation" / "upload_backend.py"
    return import_module_from_path("upload_backend_under_test_ih021", path)


class _FakeExecutable:
    def __init__(self, result):
        self._result = result

    def execute(self):
        return self._result


class _FakeFilesResource:
    def __init__(self, files):
        self._files = files

    def list(self, q, fields=None):
        # Mirrors the real Drive API: the query is a broad `contains`
        # match, so return everything containing file_prefix anywhere --
        # search_files_in_folder() is responsible for anchoring correctly.
        return _FakeExecutable({"files": self._files})


class _FakeDriveServiceForSearch:
    def __init__(self, files):
        self._files = files

    def files(self):
        return _FakeFilesResource(self._files)


def test_file_name_starts_with_prefix_rejects_a_substring_match(repo_root):
    mod = _load(repo_root)
    assert mod._file_name_starts_with_prefix("1001_report.csv", "1001") is True
    assert mod._file_name_starts_with_prefix("21001_report.csv", "1001") is False


def test_search_files_in_folder_excludes_a_prefix_substring_collision(repo_root):
    mod = _load(repo_root)
    service = _FakeDriveServiceForSearch(
        [
            {"id": "correct", "name": "1001_report.csv"},
            {"id": "wrong", "name": "21001_report.csv"},
        ]
    )

    matches = mod.search_files_in_folder(service, "folder-id", "1001")

    names = {f["name"] for f in matches}
    assert names == {"1001_report.csv"}, (
        "search_files_in_folder must not match a backend-report id that is "
        "only a substring of another file's name (IH-021)"
    )
