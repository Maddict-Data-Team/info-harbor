"""Field-parity coverage for the additive shared-settings foundation."""

import importlib

from shared.config import settings
from tests.conftest import import_module_from_path


def _load_legacy_settings(repo_root):
    paths = {
        "automation": repo_root / "projects" / "automation" / "variables.py",
        "tracker": repo_root / "projects" / "campaign-tracker" / "variables.py",
        "segments": repo_root / "projects" / "segments" / "scripts" / "variables.py",
        "poi": repo_root / "projects" / "poi" / "variables.py",
    }
    return {
        name: import_module_from_path(f"shared_settings_parity_{name}", path)
        for name, path in paths.items()
    }


def test_shared_project_and_dataset_values_match_every_legacy_copy(repo_root):
    legacy = _load_legacy_settings(repo_root)

    for component in legacy.values():
        assert component.project == settings.PROJECT_ID

    for name in ("automation", "tracker", "segments"):
        component = legacy[name]
        assert component.dataset_LS == settings.DATASET_LOCATION_SIGNALS
        assert component.dataset_footfall == settings.DATASET_FOOTFALL
        assert component.dataset_BERs == settings.DATASET_BACKEND_REPORTS
        assert component.dataset_campaign_segments == settings.DATASET_CAMPAIGN_SEGMENTS
        assert component.dataset_metadata == settings.DATASET_METADATA

    assert legacy["automation"].dataset_Districts == settings.DATASET_DISTRICT_MAPPING
    assert legacy["automation"].dataset_HWG == settings.DATASET_AUTOMATED_HWG
    assert (
        legacy["automation"].dataset_mt_Placelift
        == settings.DATASET_METADATA_PLACELIFT
    )
    assert legacy["tracker"].dataset == settings.DATASET_BACKEND_REPORTS
    assert legacy["segments"].dataset == settings.DATASET_BACKEND_REPORTS
    assert legacy["poi"].dataset_footfall == settings.DATASET_FOOTFALL
    assert legacy["poi"].dataset_metadata == settings.DATASET_POI_LOOKUPS


def test_shared_table_and_country_values_preserve_component_differences(repo_root):
    legacy = _load_legacy_settings(repo_root)

    assert legacy["automation"].tbl_cmpgn_tracker == settings.TABLE_CAMPAIGN_TRACKER
    assert legacy["tracker"].tbl_campaign_tracker == settings.TABLE_CAMPAIGN_TRACKER
    assert legacy["segments"].table_placelift == settings.TABLE_PLACELIFT
    assert legacy["poi"].lookup_country_table == settings.TABLE_COUNTRY_LOOKUP
    assert legacy["poi"].lookup_city_table == settings.TABLE_CITY_LOOKUP

    expected_views = {
        "automation": settings.AUTOMATION_COUNTRY_POI_TABLES,
        "tracker": settings.CAMPAIGN_TRACKER_COUNTRY_POI_TABLES,
        "segments": settings.SEGMENTS_COUNTRY_POI_TABLES,
        "poi": settings.POI_COUNTRY_POI_TABLES,
    }
    for name, expected in expected_views.items():
        assert legacy[name].table_mapping == expected


def test_shared_status_drive_secret_and_legacy_path_values_match(repo_root):
    legacy = _load_legacy_settings(repo_root)
    automation = legacy["automation"]
    tracker = legacy["tracker"]
    segments = legacy["segments"]
    poi = legacy["poi"]

    assert (
        automation.stage_0,
        automation.stage_1,
        automation.stage_2,
        automation.stage_3,
        automation.stage_4,
        automation.stage_5,
        automation.stage_6,
    ) == (
        settings.STATUS_PRE_VALIDATION,
        settings.STATUS_VALIDATION,
        settings.STATUS_ACTIVE,
        settings.STATUS_COMPLETION_PERIOD,
        settings.STATUS_FINISHED,
        settings.STATUS_ERROR,
        settings.STATUS_ON_HOLD,
    )
    assert tracker.stage_0 == settings.STATUS_PRE_VALIDATION
    assert tracker.stage_4 == settings.STATUS_FINISHED

    assert automation.folder_id_Backend_Reports == settings.DRIVE_BACKEND_REPORTS_FOLDER_ID
    assert segments.MAIN_DRIVE_FOLDER_ID == settings.DRIVE_MAIN_FOLDER_ID
    assert segments.drive_link_folder_Adops == settings.DRIVE_ADOPS_FOLDER_URL
    assert (
        tracker.drive_link_folder_Adops
        == settings.LEGACY_CAMPAIGN_TRACKER_DRIVE_FOLDER_URL
    )

    assert automation.secret_ber == settings.SECRET_BACKEND_REPORT_TOKEN
    assert automation.secret_bq == settings.SECRET_BIGQUERY_CREDENTIALS
    assert segments.secret_ber == settings.SECRET_BACKEND_REPORT_TOKEN
    assert segments.secret_bq == settings.SECRET_BIGQUERY_CREDENTIALS
    assert tracker.dir_data == settings.CAMPAIGN_TRACKER_DATA_DIR
    assert segments.dir_data == settings.SEGMENTS_DATA_DIR
    assert tuple(segments.poi_filter_fields) == settings.POI_FILTER_FIELDS

    for component in (automation, tracker, segments):
        assert component.key_bq == settings.LEGACY_BIGQUERY_KEY_PATH
    assert poi.key_bq == settings.LEGACY_BIGQUERY_KEY_PATH
    assert tracker.key_google_sheets == settings.LEGACY_GOOGLE_SHEETS_KEY_PATH
    assert segments.key_google_sheets == settings.LEGACY_GOOGLE_SHEETS_KEY_PATH


def test_shared_query_replacements_match_current_component_maps(repo_root):
    legacy = _load_legacy_settings(repo_root)

    assert legacy["automation"].static_query_replace == settings.AUTOMATION_QUERY_REPLACEMENTS
    assert legacy["segments"].static_query_replace == settings.SEGMENTS_QUERY_REPLACEMENTS


def test_shared_defaults_match_campaign_model_and_segment_input(repo_root):
    from shared.models.campaign import CampaignConfig

    segments_input = import_module_from_path(
        "shared_settings_parity_segments_input",
        repo_root / "projects" / "segments" / "input.py",
    )
    model_defaults = CampaignConfig(code_name="test", campaign_name="test", countries=[])

    assert segments_input.controlled_size == settings.DEFAULT_CONTROLLED_SIZE
    assert segments_input.hg_radius == settings.DEFAULT_HOME_GRAPH_RADIUS
    assert model_defaults.controlled_size == settings.DEFAULT_CONTROLLED_SIZE
    assert model_defaults.hg_radius == settings.DEFAULT_HOME_GRAPH_RADIUS
    assert model_defaults.time_interval == settings.DEFAULT_TIME_INTERVAL
    assert model_defaults.has_segments == settings.DEFAULT_HAS_SEGMENTS


def test_shared_settings_import_has_no_filesystem_or_cloud_side_effects(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("shared settings must not perform filesystem writes")

    monkeypatch.setattr("pathlib.Path.mkdir", forbidden)

    # Reload under the guard so the module body itself is exercised.  The
    # suite's autouse fixture separately rejects Google client construction.
    reloaded = importlib.reload(settings)
    assert reloaded.PROJECT_ID == "maddictdata"
