"""
Regression test for IH-016: get_metadata() iterated
`for row in metadata_raw: countries.append(row.country)`, then read
`row.end_date` etc. AFTER the loop, relying on Python's loop-variable
leakage. If metadata_raw was empty (e.g. a deleted or mistyped
code_name), `row` was never bound and the function raised an opaque
NameError -- swallowed by IH-002's bare except in run_by_codename.

Calls the real get_metadata() against a FakeBigQueryClient configured to
return zero rows. No network, no credentials.
"""
from __future__ import annotations

import pytest

from tests.conftest import import_automation_query_orchestrator
from tests.fakes.fake_bigquery import FakeBigQueryClient


def test_get_metadata_raises_a_clear_error_for_an_empty_result_set():
    orchestrator = import_automation_query_orchestrator()
    config = orchestrator.read_config()

    client = FakeBigQueryClient()
    client.set_default_rows([])

    with pytest.raises(ValueError, match="No Campaign_Tracker rows found"):
        orchestrator.get_metadata("999999", config, client)
