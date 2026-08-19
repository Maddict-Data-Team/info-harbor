"""
Minimal in-memory stand-in for the Google Drive v3 API surface used by
projects/segments/scripts/transfer_to_drive.py and
projects/automation/upload_backend.py. Offline only -- no network calls.

Deliberately permits duplicate file titles within one folder (Drive itself
allows this), which is what makes it possible to write a regression test
for IH-011 (reruns duplicate Drive uploads) without contacting real Drive.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class FakeDriveFile:
    id: str
    name: str
    parents: list[str]
    mimeType: str = "text/csv"


class _FilesResource:
    def __init__(self, store: "FakeDriveService"):
        self._store = store

    def list(self, q: str = "", spaces=None, fields=None, supportsAllDrives=None):
        return _Executable(lambda: {"files": self._store._match(q)})

    def create(self, body: dict, media_body=None, supportsAllDrives=None, fields=None):
        file_id = str(uuid.uuid4())
        f = FakeDriveFile(
            id=file_id,
            name=body.get("name") or body.get("title", ""),
            parents=body.get("parents", []),
            mimeType=body.get("mimeType", "text/csv"),
        )
        self._store.files_created.append(f)
        return _Executable(lambda: {"id": file_id})


class _Executable:
    def __init__(self, fn):
        self._fn = fn

    def execute(self):
        return self._fn()


class FakeDriveService:
    """Stands in for `googleapiclient.discovery.build("drive", "v3", ...)`."""

    def __init__(self):
        self.files_created: list[FakeDriveFile] = []

    def files(self):
        return _FilesResource(self)

    def _match(self, q: str) -> list[dict]:
        # Very small subset of Drive query language: supports the
        # "'<parent>' in parents ... name='<name>' ... mimeType='...folder'"
        # shape used by find_or_create_folder().
        results = []
        for f in self.files_created:
            if f"name='{f.name}'" in q or f"name contains '{f.name}'" in q:
                results.append({"id": f.id, "name": f.name})
        return results
