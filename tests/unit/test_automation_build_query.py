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


class TestCommonQueriesDateSwapFixed:
    """# FIXED: IH-017 -- the recursive call to run_pipeline_queries for
    "common_queries" used to pass (start_date_q, end_date_q) positionally
    into parameter slots declared as (end_date_q, start_date_q), transposed
    relative to the top-level call. It now passes every argument by
    keyword, so a parameter reorder can't silently reintroduce the swap.
    """

    def test_common_queries_section_has_no_date_window_placeholders(self, repo_root):
        """Defense-in-depth, kept from the original characterization test:
        [Common Queries] in queries.ini still has no {start_date_q}/
        {end_date_q} placeholders, so even an unrelated future regression
        in the date-argument order would stay silent there specifically."""
        config = configparser.ConfigParser()
        config.read(repo_root / "projects" / "automation" / "queries.ini")
        for name, value in config.items("Common Queries"):
            assert "{start_date_q}" not in value, (
                f"Common Queries option '{name}' now uses {{start_date_q}} -- "
                "verify the recursive call at query_orchestrator.py's "
                "run_pipeline_queries still passes end_date_q/start_date_q "
                "correctly before this can pass."
            )
            assert "{end_date_q}" not in value, (
                f"Common Queries option '{name}' now uses {{end_date_q}} -- "
                "verify the recursive call at query_orchestrator.py's "
                "run_pipeline_queries still passes end_date_q/start_date_q "
                "correctly before this can pass."
            )

    def test_common_queries_recursive_call_preserves_date_argument_order(self):
        """Directly exercises the fix: calls the real run_pipeline_queries
        with distinct, unmistakable start/end dates and a synthetic config
        whose only query name is "common_queries", intercepting the
        recursive call (by reassigning the module-global name it resolves
        against) instead of letting it actually recurse, and asserts the
        intercepted call received end_date_q/start_date_q unswapped."""
        orch = _orchestrator()

        config = configparser.ConfigParser()
        config.read_string(
            "[TestType]\nqueries = common_queries\n\n"
            "[Common Queries]\nplaceholder = SELECT 1\n"
        )

        calls = []

        def spy(**kwargs):
            calls.append(kwargs)

        real_run_pipeline_queries = orch.run_pipeline_queries
        orch.run_pipeline_queries = spy
        try:
            real_run_pipeline_queries(
                config=config,
                codename="999",
                end_date_q="2026-08-20",
                start_date_q="2026-08-01",
                countries=["UAE"],
                pipeline_type="TestType",
                bq_client=None,
                radiuses=[100],
            )
        finally:
            orch.run_pipeline_queries = real_run_pipeline_queries

        assert len(calls) == 1, "expected exactly one recursive call for common_queries"
        assert calls[0]["end_date_q"] == "2026-08-20"
        assert calls[0]["start_date_q"] == "2026-08-01"
        assert calls[0]["pipeline_type"] == "Common Queries"
