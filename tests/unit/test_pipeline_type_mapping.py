"""
Characterization tests for IH-005 and IH-006: whether a campaign's `type`
value (as stored in Campaign_Tracker) resolves to a real section in
projects/automation/queries.ini.

These import and call the REAL projects/automation/query_orchestrator.py
functions (get_metadata, get_campaign_tracker_data) against a
FakeBigQueryClient -- no network, no credentials.
"""
from __future__ import annotations

import configparser

import pytest

from tests.conftest import import_automation_query_orchestrator
from tests.fakes.fake_bigquery import FakeBigQueryClient
from tests.fixtures import campaign_metadata as md


@pytest.fixture
def orchestrator():
    # Load projects/automation/query_orchestrator.py specifically -- see
    # tests/conftest.py's note on the query_orchestrator.py name collision
    # between projects/automation and projects/segments/scripts.
    return import_automation_query_orchestrator()


@pytest.fixture
def queries_ini_config(orchestrator):
    """The REAL queries.ini shipped in projects/automation, read exactly
    the way the production code reads it (query_orchestrator.read_config).
    """
    return orchestrator.read_config()


def _resolve_pipeline_type(orchestrator, config, rows):
    client = FakeBigQueryClient()
    client.set_default_rows(rows)
    _countries, pipeline_type, _end, _interval, _last_update, _start = (
        orchestrator.get_metadata("999", config, client)
    )
    return pipeline_type


class TestConfirmedPlacementNoBerMismatch:
    """IH-005: exact reproduction of the case given by the project owner --
    code_name=113, type="Placelift NO BER", backend_report=0, segments=1.
    """

    def test_type_string_bypasses_the_normalizer(self, orchestrator, queries_ini_config):
        pipeline_type = _resolve_pipeline_type(
            orchestrator, queries_ini_config, md.placelift_no_ber_113()
        )
        # get_metadata's normalizer (query_orchestrator.py:223-229) only
        # rewrites five exact literals. "Placelift NO BER" is not one of
        # them, so it must pass through completely unchanged.
        assert pipeline_type == "Placelift NO BER"

    def test_unchanged_type_does_not_match_any_queries_ini_section(
        self, queries_ini_config
    ):
        # configparser section names are case-sensitive; the real section
        # is "[Placelift No BER]" (queries.ini:429), not "[Placelift NO BER]".
        assert not queries_ini_config.has_section("Placelift NO BER")
        assert queries_ini_config.has_section("Placelift No BER")

    def test_end_to_end_no_section_error_is_raised(
        self, orchestrator, queries_ini_config
    ):
        """This is the exact failure that reaches the bare `except:` at
        query_orchestrator.py:427-429 in run_by_codename, which is then
        swallowed and reported as HTTP 200 success (IH-002). This test
        proves the NoSectionError occurs; it does not exercise the
        swallowing itself (that requires a live BigQuery round trip and is
        out of scope for the offline suite).
        # BUG: IH-005
        """
        pipeline_type = _resolve_pipeline_type(
            orchestrator, queries_ini_config, md.placelift_no_ber_113()
        )
        with pytest.raises(configparser.NoSectionError):
            queries_ini_config.get(pipeline_type, "queries")


class TestConfirmedRetailIntelligenceDashboardMismatch:
    """IH-006: campaign_144_retail.py sets
    type="Retail Intelligence Dashboard"; the only matching section is
    "[Retail Intelligence]" (no "Dashboard")."""

    def test_type_is_not_rewritten(self, orchestrator, queries_ini_config):
        pipeline_type = _resolve_pipeline_type(
            orchestrator, queries_ini_config, md.retail_intelligence_dashboard_144()
        )
        assert pipeline_type == "Retail Intelligence Dashboard"

    def test_no_matching_section(self, orchestrator, queries_ini_config):
        # BUG: IH-006
        pipeline_type = _resolve_pipeline_type(
            orchestrator, queries_ini_config, md.retail_intelligence_dashboard_144()
        )
        assert not queries_ini_config.has_section(pipeline_type)
        with pytest.raises(configparser.NoSectionError):
            queries_ini_config.get(pipeline_type, "queries")


class TestConfirmedUnknownTypeMismatch:
    """database_loader.py:78 emits type='Unknown' for a NULL type column."""

    def test_unknown_has_no_section(self, orchestrator, queries_ini_config):
        pipeline_type = _resolve_pipeline_type(
            orchestrator, queries_ini_config, md.unknown_type_null_metadata()
        )
        assert pipeline_type == "Unknown"
        assert not queries_ini_config.has_section("Unknown")


class TestWorkingCasesForContrast:
    """These prove the normalizer DOES work for the literals it explicitly
    handles, so the failures above are attributable to the specific
    unmatched strings, not to the whole mechanism being broken."""

    @pytest.mark.parametrize(
        "rows_fn, expected_section",
        [
            (md.plain_placelift_with_ber_and_segments_143, "Placelift"),
            (md.placelift_no_segments_via_normalizer, "Placelift No Segments"),
            (md.placelift_no_ber_via_normalizer, "Placelift No BER"),
            (md.ooh_multi_country_145, "OOH"),
        ],
    )
    def test_normalized_or_direct_type_resolves_to_a_real_section(
        self, orchestrator, queries_ini_config, rows_fn, expected_section
    ):
        pipeline_type = _resolve_pipeline_type(orchestrator, queries_ini_config, rows_fn())
        assert pipeline_type == expected_section
        assert queries_ini_config.has_section(pipeline_type)
        # Must not raise:
        queries_ini_config.get(pipeline_type, "queries")

    def test_placelift_no_ber_via_normalizer_reaches_the_correct_section_by_a_different_path(
        self, orchestrator, queries_ini_config
    ):
        """Documents the irony noted in the audit: a plain type of
        "Standard Placelift" with backend_report=0 and segments=1 resolves,
        via the normalizer, to EXACTLY the same section a human meant when
        they wrote "Placelift NO BER" directly -- but only the normalized
        path succeeds (see TestConfirmedPlacementNoBerMismatch above)."""
        pipeline_type = _resolve_pipeline_type(
            orchestrator, queries_ini_config, md.placelift_no_ber_via_normalizer()
        )
        assert pipeline_type == "Placelift No BER"
