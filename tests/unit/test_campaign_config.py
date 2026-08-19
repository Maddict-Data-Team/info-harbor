"""
Pure-logic tests for shared/models/campaign.CampaignConfig -- no I/O, no
sys.path tricks needed (it's a normal package under shared/).
"""
from __future__ import annotations

from shared.models.campaign import CampaignConfig, CustomSegment


def test_backend_reports_defaults_to_one_zero_per_country():
    cfg = CampaignConfig(code_name="1", campaign_name="X", countries=["UAE", "KSA"])
    assert cfg.backend_reports == [0, 0]


def test_backend_reports_padded_when_shorter_than_countries():
    cfg = CampaignConfig(
        code_name="1", campaign_name="X", countries=["UAE", "KSA", "QAT"],
        backend_reports=[5],
    )
    assert cfg.backend_reports == [5, 0, 0]


def test_backend_reports_truncated_when_longer_than_countries():
    cfg = CampaignConfig(
        code_name="1", campaign_name="X", countries=["UAE"],
        backend_reports=[5, 6, 7],
    )
    assert cfg.backend_reports == [5]


def test_custom_segments_dicts_are_upgraded_to_customsegment_objects():
    cfg = CampaignConfig(
        code_name="1", campaign_name="X", countries=["UAE"],
        custom_segments={"foo": {"type": "POI", "radius": 50}},
    )
    assert isinstance(cfg.custom_segments["foo"], CustomSegment)
    assert cfg.custom_segments["foo"].radius == 50


def test_validate_flags_missing_required_fields():
    cfg = CampaignConfig(code_name="", campaign_name="", countries=[])
    errors = cfg.validate()
    assert "code_name is required" in errors
    assert "campaign_name is required" in errors
    assert "At least one country is required" in errors


def test_validate_flags_non_positive_sizes():
    cfg = CampaignConfig(
        code_name="1", campaign_name="X", countries=["UAE"],
        controlled_size=0, hg_radius=-1,
    )
    errors = cfg.validate()
    assert "controlled_size must be positive" in errors
    assert "hg_radius must be positive" in errors


def test_validate_flags_incomplete_custom_segment():
    cfg = CampaignConfig(
        code_name="1", campaign_name="X", countries=["UAE"],
        custom_segments={"bad": CustomSegment(type="", radius=0)},
    )
    errors = cfg.validate()
    assert any("missing type" in e for e in errors)
    assert any("radius must be positive" in e for e in errors)


def test_valid_campaign_has_no_errors():
    cfg = CampaignConfig(
        code_name="143", campaign_name="ADNOC", countries=["UAE"],
        controlled_size=50000, hg_radius=3000,
    )
    assert cfg.validate() == []


def test_from_legacy_inputs_round_trips_segments_input_shape():
    segments_input = {
        "code_name": "143",
        "campaign_name": "ADNOC",
        "countries": ["UAE"],
        "segments": ["Hotels"],
        "dict_custom_segments": {"foo": {"type": "POI", "radius": 50}},
        "excluded_segments": [],
        "controlled_size": 1000,
        "hg_radius": 500,
    }
    cfg = CampaignConfig.from_legacy_inputs(segments_input)
    assert cfg.code_name == "143"
    assert cfg.segments == ["Hotels"]
    back = cfg.to_segments_input()
    assert back["code_name"] == "143"
    assert back["dict_custom_segments"]["foo"]["radius"] == 50
