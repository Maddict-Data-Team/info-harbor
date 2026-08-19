"""
Minimal in-memory stand-in for a google.cloud.bigquery.Client, used only by
this offline test suite. It never opens a socket, never reads credentials,
and never talks to Google Cloud.

It supports exactly the surface the repository's own code calls:
`client.query(sql)` returning an object whose `.result()` yields canned
rows, plus a call log so tests can assert on emitted SQL text, destination
tables, and write dispositions (see docs/modernization-spec.md, "Testing
strategy" and docs/code-audit.md parity manifest section).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable


@dataclass
class RecordedJob:
    sql: str
    destination: str | None = None
    write_disposition: str | None = None


class FakeQueryJob:
    def __init__(self, rows: Iterable[Any]):
        self._rows = list(rows)

    def result(self):
        return iter(self._rows)


class FakeBigQueryClient:
    """Records every query issued and returns pre-programmed rows.

    Usage:
        client = FakeBigQueryClient()
        client.set_response_for_contains("query_metadata", metadata_rows)
        # code under test calls client.query(sql).result()
    """

    def __init__(self):
        self.jobs: list[RecordedJob] = []
        self._responders: list[tuple[Callable[[str], bool], Iterable[Any]]] = []
        self._default_rows: list[Any] = []

    def set_default_rows(self, rows: Iterable[Any]):
        self._default_rows = list(rows)

    def set_response_when(self, predicate: Callable[[str], bool], rows: Iterable[Any]):
        self._responders.append((predicate, rows))

    def set_response_for_contains(self, needle: str, rows: Iterable[Any]):
        self.set_response_when(lambda sql, _n=needle: _n in sql, rows)

    def dataset(self, dataset_id):  # pragma: no cover - trivial passthrough
        return FakeDatasetRef(dataset_id)

    def query(self, sql: str, job_config: Any = None) -> FakeQueryJob:
        destination = getattr(job_config, "destination", None)
        write_disposition = getattr(job_config, "write_disposition", None)
        self.jobs.append(
            RecordedJob(sql=sql, destination=str(destination) if destination else None,
                        write_disposition=write_disposition)
        )
        for predicate, rows in self._responders:
            if predicate(sql):
                return FakeQueryJob(rows)
        return FakeQueryJob(self._default_rows)

    def create_table(self, table):  # pragma: no cover - not exercised yet
        raise NotImplementedError("FakeBigQueryClient.create_table not needed by current tests")

    def delete_table(self, table_ref, not_found_ok: bool = False):  # pragma: no cover
        return None


@dataclass
class FakeDatasetRef:
    dataset_id: str

    def table(self, table_id):
        return f"{self.dataset_id}.{table_id}"
