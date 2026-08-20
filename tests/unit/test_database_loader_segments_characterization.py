"""
Characterization test for IH-004 (Critical, on the stop-list -- read-only
investigation and characterization only, per this session's authorization;
NOT fixed here).

create_campaign_config_from_db() hardcodes segments=[], custom_segments={},
excluded_segments=[] regardless of what db_data contains, because those
fields are never read from the database in the first place (see
load_campaigns_from_database()'s SELECT, which has no segments/custom_
segments/excluded_segments columns at all). Combined with
shared/config/campaigns/__init__.py's "replace, don't merge" campaign
registry logic, a campaign that previously had real segment data via the
hardcoded fallback silently loses it as soon as the database path
succeeds.

This test calls the real, pure create_campaign_config_from_db() directly
with a hand-built db_data dict -- no BigQuery client is constructed or
used (load_campaigns_from_database(), the function that queries BigQuery,
is not exercised at all). No network, no credentials.
"""
from __future__ import annotations

from shared.config.campaigns.database_loader import create_campaign_config_from_db


def test_db_loaded_campaign_always_has_empty_segment_fields_regardless_of_input():
    """# BUG: IH-004 -- proves the information loss directly. If this
    assertion starts failing, IH-004's segments/custom_segments/
    excluded_segments loss has been fixed (or load_campaigns_from_database
    now reads these fields) -- flip this test to assert the real values
    are preserved instead, and update docs/code-audit.md IH-004."""
    db_data = {
        "campaign_name": "Test Campaign",
        "countries": ["UAE"],
        "type": "Placelift",
        "start_date": "2026-01-01",
        "end_date": "2026-02-01",
        "backend_reports": [0],
        "time_interval": -1,
        "has_segments": 1,
    }

    config = create_campaign_config_from_db("143", db_data)

    assert config.segments == []
    assert config.custom_segments == {}
    assert config.excluded_segments == []
    # has_segments (from the database) says this campaign DOES have
    # segments, yet the segments list itself is unconditionally empty --
    # this specific contradiction is the core of IH-004's business impact.
    assert config.has_segments == 1
