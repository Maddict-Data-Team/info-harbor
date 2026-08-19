"""
Tests for projects/automation/query_orchestrator.build_query (SQL
placeholder substitution) and a regression guard on the latent
"[Common Queries]" date-argument swap.
"""
from __future__ import annotations

import configparser

from tests.conftest import import_automation_query_orchestrator


def _orchestrator():
    return import_automation_query_orchestrator()


def test_placeholder_substitution_is_literal_and_order_independent():
    orch = _orchestrator()
    raw = "SELECT * FROM {project}.{footfall_dataset}.{codename}_visitors WHERE d = '{start_date_q}'"
    built = orch.build_query(raw, codename=143, start_date_q="2026-01-01")
    assert "{project}" not in built
    assert "{footfall_dataset}" not in built
    assert "143_visitors" in built
    assert "'2026-01-01'" in built


def test_country_placeholder_expands_to_a_union_per_country():
    orch = _orchestrator()
    raw = "SELECT DID FROM POI_DB_{country}.table"
    built = orch.build_query(raw, codename=143, countries=["UAE", "KSA"])
    assert built.count("UNION ALL") == 1
    assert "POI_DB_UAE.table" in built
    assert "POI_DB_KSA.table" in built


def test_radius_placeholder_expands_to_a_union_per_radius():
    orch = _orchestrator()
    raw = "SELECT * FROM t WHERE distance < {radius}"
    built = orch.build_query(raw, codename=143, radiuses=[100, 250])
    assert built.count("UNION ALL") == 1
    assert "distance < 100" in built
    assert "distance < 250" in built


def test_country_beh_uses_qat_and_egy_special_cases():
    orch = _orchestrator()
    assert orch.get_country_beh("QAT") == "QTR"
    assert orch.get_country_beh("EGY") == "EGP"
    assert orch.get_country_beh("UAE") == "UAE"


class TestCommonQueriesDateSwapIsCurrentlyLatentNotActive:
    """IH (latent): the recursive call to run_pipeline_queries for
    "common_queries" (query_orchestrator.py:297-306) passes
    (start_date_q, end_date_q) into parameter slots declared as
    (end_date_q, start_date_q) -- the two are transposed relative to the
    top-level call (query_orchestrator.py:413-424).

    This is provably harmless RIGHT NOW only because [Common Queries] in
    queries.ini contains zero {start_date_q}/{end_date_q} placeholders.
    This test is a regression guard: if a future edit adds a date
    placeholder to any query under [Common Queries], this test starts
    failing and should be treated as "the latent bug just went live",
    not as a broken test.
    """

    def test_common_queries_section_has_no_date_window_placeholders(self, repo_root):
        config = configparser.ConfigParser()
        config.read(repo_root / "projects" / "automation" / "queries.ini")
        for name, value in config.items("Common Queries"):
            assert "{start_date_q}" not in value, (
                f"Common Queries option '{name}' now uses {{start_date_q}} -- "
                "the swapped recursive call at query_orchestrator.py:297-306 "
                "will invert this window. Fix the call before this can pass."
            )
            assert "{end_date_q}" not in value, (
                f"Common Queries option '{name}' now uses {{end_date_q}} -- "
                "the swapped recursive call at query_orchestrator.py:297-306 "
                "will invert this window. Fix the call before this can pass."
            )
