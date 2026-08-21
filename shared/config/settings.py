"""Side-effect-free shared settings for Info-Harbor.

This module is the additive foundation for configuration unification.  Legacy
``variables.py`` and ``input.py`` modules continue to own runtime behaviour
until each entry point is migrated and its output parity is proven.  Values
which intentionally differ between legacy components are exposed as scoped
settings rather than silently collapsed.

Credential file paths are recorded only as legacy compatibility values.  New
code must use runtime identity or Secret Manager instead of these paths.
"""

from types import MappingProxyType
from typing import Final, Mapping


# Google Cloud project
PROJECT_ID: Final = "maddictdata"


# BigQuery datasets
DATASET_LOCATION_SIGNALS: Final = "Location_Signals"
DATASET_FOOTFALL: Final = "Back_End_Footfall"
DATASET_BACKEND_REPORTS: Final = "Back_End_Reports"
DATASET_CAMPAIGN_SEGMENTS: Final = "Placelift_Campaign_Segments"
DATASET_DISTRICT_MAPPING: Final = "District_Mapping"
DATASET_AUTOMATED_HWG: Final = "Automated_HWG"
DATASET_METADATA: Final = "Metadata"
DATASET_POI_LOOKUPS: Final = "Lookups"
DATASET_METADATA_PLACELIFT: Final = "maddictdata.Metadata.Placelift"


# BigQuery tables
TABLE_HOME_GRAPH: Final = "Home_Graph_Cumulative"
TABLE_WORK_GRAPH: Final = "Work_Graph_Cumulative"
TABLE_HWG_POL_MAPPING: Final = "All_Pols_Mapping"
TABLE_CAMPAIGN_TRACKER: Final = "Campaign_Tracker"
TABLE_CAMPAIGN_TEST: Final = "test"
TABLE_BEHAVIOR_LOOKUP: Final = "Lookup_Behavior"
TABLE_DEVICE_OS_MAPPING: Final = "device_os_mapping"
TABLE_PLACELIFT: Final = "Placelift"
TABLE_COUNTRY_LOOKUP: Final = "lu_country"
TABLE_CITY_LOOKUP: Final = "lu_city"


# Country-to-POI-table mappings.  The component views preserve today's exact
# supported-country sets; migration must not broaden them implicitly.
COUNTRY_POI_TABLES: Mapping[str, str] = MappingProxyType(
    {
        "KSA": "POI_DB_KSA",
        "UAE": "POI_DB_UAE",
        "QAT": "POI_DB_QTR",
        "KWT": "POI_DB_KWT",
        "OMN": "POI_DB_OMN",
        "BHR": "POI_DB_BHR",
        "EGY": "POI_DB_EGP",
        "MAR": "POI_DB_MAR",
    }
)


def _country_view(*country_codes: str) -> Mapping[str, str]:
    return MappingProxyType(
        {code: COUNTRY_POI_TABLES[code] for code in country_codes}
    )


AUTOMATION_COUNTRY_POI_TABLES: Mapping[str, str] = _country_view(
    "KSA", "UAE", "QAT", "KWT", "OMN", "BHR"
)
CAMPAIGN_TRACKER_COUNTRY_POI_TABLES: Mapping[str, str] = _country_view(
    "KSA", "UAE", "QAT", "KWT", "OMN", "BHR", "EGY", "MAR"
)
SEGMENTS_COUNTRY_POI_TABLES: Mapping[str, str] = _country_view(
    "KSA", "UAE", "QAT", "KWT", "OMN", "BHR", "EGY"
)
POI_COUNTRY_POI_TABLES: Mapping[str, str] = _country_view(
    "KSA", "UAE", "QAT", "KWT", "OMN", "BHR", "EGY", "MAR"
)


# Campaign lifecycle statuses
STATUS_PRE_VALIDATION: Final = "Pre-Validation"
STATUS_VALIDATION: Final = "Validation"
STATUS_ACTIVE: Final = "Active"
STATUS_COMPLETION_PERIOD: Final = "Completion Period"
STATUS_FINISHED: Final = "Finished"
STATUS_ERROR: Final = "Error"
STATUS_ON_HOLD: Final = "On Hold"


# Google Drive locations.  Campaign Tracker's legacy URL is deliberately
# separate because it differs from the segments/AdOps location today.
DRIVE_MAIN_FOLDER_ID: Final = "1HEJQ-0gc8VgICB6NK2yZO-aBweuTVrRf"
DRIVE_BACKEND_REPORTS_FOLDER_ID: Final = "1vKOH8eDs92jHSaGyPILAa9p3qH8YUHNo"
DRIVE_ADOPS_FOLDER_URL: Final = (
    "https://drive.google.com/drive/folders/1HEJQ-0gc8VgICB6NK2yZO-aBweuTVrRf"
)
LEGACY_CAMPAIGN_TRACKER_DRIVE_FOLDER_URL: Final = (
    "https://drive.google.com/drive/folders/1GuOSGxq5AlLxzaqbkzQBDQ8n7HcuhWWM"
)


# Secret Manager resource names
SECRET_BACKEND_REPORT_TOKEN: Final = (
    "projects/maddictdata/secrets/token-ber/versions/latest"
)
SECRET_BIGQUERY_CREDENTIALS: Final = (
    "projects/maddictdata/secrets/secret-bq/versions/latest"
)


# Legacy compatibility only.  New code must not authenticate from key files.
LEGACY_BIGQUERY_KEY_PATH: Final = "keys/maddictdata-bq.json"
LEGACY_GOOGLE_SHEETS_KEY_PATH: Final = "keys/maddictdata-google-sheets.json"


# Component-relative data locations retained for output parity.
CAMPAIGN_TRACKER_DATA_DIR: Final = "data"
SEGMENTS_DATA_DIR: Final = "projects/segments/data"


# Shared defaults represented by today's campaign model and segment input.
DEFAULT_CONTROLLED_SIZE: Final = 50_000
DEFAULT_HOME_GRAPH_RADIUS: Final = 3_000
DEFAULT_TIME_INTERVAL: Final = -1
DEFAULT_HAS_SEGMENTS: Final = 0


POI_FILTER_FIELDS: Final = (
    "General_Category",
    "Category",
    "Subcategory",
    "GM_Subcategory",
    "Chain",
)


# Query-placeholder maps are scoped because automation and segments currently
# expose different placeholder sets.
AUTOMATION_QUERY_REPLACEMENTS: Mapping[str, str] = MappingProxyType(
    {
        "{hwg_dataset}": DATASET_AUTOMATED_HWG,
        "{footfall_dataset}": DATASET_FOOTFALL,
        "{project}": PROJECT_ID,
        "{metadata_dataset}": DATASET_METADATA,
        "{campaign_tracker_table}": TABLE_CAMPAIGN_TRACKER,
        "{location_signals_dataset}": DATASET_LOCATION_SIGNALS,
        "{device_os_mapping_table}": TABLE_DEVICE_OS_MAPPING,
        "{hwg_table}": TABLE_HOME_GRAPH,
        "{lookup_behavior_table}": TABLE_BEHAVIOR_LOOKUP,
        "{back_end_report_dataset}": DATASET_BACKEND_REPORTS,
        "{Campaign_segments_dataset}": DATASET_CAMPAIGN_SEGMENTS,
        "{tbl_cmpgn_test}": TABLE_CAMPAIGN_TEST,
    }
)

SEGMENTS_QUERY_REPLACEMENTS: Mapping[str, str] = MappingProxyType(
    {
        "{hwg_dataset}": DATASET_AUTOMATED_HWG,
        "{footfall_dataset}": DATASET_FOOTFALL,
        "{project}": PROJECT_ID,
        "{location_signals_dataset}": DATASET_LOCATION_SIGNALS,
        "{hg_table}": TABLE_HOME_GRAPH,
        "{wg_table}": TABLE_WORK_GRAPH,
        "{pol_map_table}": TABLE_HWG_POL_MAPPING,
    }
)
