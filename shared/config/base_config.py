"""
Base configuration for Info-Harbor
Contains all shared constants, settings, and configurations
"""
from .paths import KEY_BQ, KEY_GOOGLE_SHEETS

# Google Cloud Configuration
PROJECT = "maddictdata"

# BigQuery Datasets
DATASET_LS = "Location_Signals"
DATASET_FOOTFALL = "Back_End_Footfall"
DATASET_BERS = "Back_End_Reports"
DATASET_CAMPAIGN_SEGMENTS = "Placelift_Campaign_Segments"
DATASET_DISTRICTS = "District_Mapping"
DATASET_HWG = "Automated_HWG"
DATASET_MT_PLACELIFT = "maddictdata.Metadata.Placelift"
DATASET_METADATA = "Metadata"

# BigQuery Tables
TABLE_HG = "Home_Graph_Cumulative"
TABLE_WG = "Work_Graph_Cumulative"
TABLE_HWG_POL_MAP = "All_Pols_Mapping"
TBL_CMPGN_TRACKER = "Campaign_Tracker"
TBL_CMPGN_TEST = "test"
TABLE_BEHAVIOR_LOOKUP = "Lookup_Behavior"
TABLE_OS_MAPPING = "device_os_mapping"
TABLE_PLACELIFT = "Placelift"

# Country to Table Mapping
TABLE_MAPPING = {
    "KSA": "POI_DB_KSA",
    "UAE": "POI_DB_UAE",
    "QAT": "POI_DB_QTR",
    "KWT": "POI_DB_KWT",
    "OMN": "POI_DB_OMN",
    "BHR": "POI_DB_BHR",
    "EGY": "POI_DB_EGP",
    "MAR": "POI_DB_MAR",
}

# Campaign Status Stages
STAGE_0 = "Pre-Validation"
STAGE_1 = "Validation"
STAGE_2 = "Active"
STAGE_3 = "Completion Period"
STAGE_4 = "Finished"
STAGE_5 = "Error"
STAGE_6 = "On Hold"

# Google Drive Configuration
MAIN_DRIVE_FOLDER_ID = "1HEJQ-0gc8VgICB6NK2yZO-aBweuTVrRf"
FOLDER_ID_BACKEND_REPORTS = "1vKOH8eDs92jHSaGyPILAa9p3qH8YUHNo"

DRIVE_LINK_FOLDER_ADOPS = (
    "https://drive.google.com/drive/folders/1HEJQ-0gc8VgICB6NK2yZO-aBweuTVrRf"
)

# Secret Manager Configuration
SECRET_BER = f"projects/maddictdata/secrets/token-ber/versions/latest"
SECRET_BQ = f"projects/maddictdata/secrets/secret-bq/versions/latest"

# Authentication Keys (using centralized paths)
KEY_BQ_PATH = str(KEY_BQ)
KEY_GOOGLE_SHEETS_PATH = str(KEY_GOOGLE_SHEETS)

# POI Filter Fields
POI_FILTER_FIELDS = [
    "General_Category",
    "Category",
    "Subcategory",
    "GM_Subcategory",
    "Chain",
]

# Static Query Replacements
STATIC_QUERY_REPLACE = {
    "{hwg_dataset}": DATASET_HWG,
    "{footfall_dataset}": DATASET_FOOTFALL,
    "{project}": PROJECT,
    "{metadata_dataset}": DATASET_METADATA,
    "{campaign_tracker_table}": TBL_CMPGN_TRACKER,
    "{location_signals_dataset}": DATASET_LS,
    "{device_os_mapping_table}": TABLE_OS_MAPPING,
    "{hwg_table}": TABLE_HG,
    "{wg_table}": TABLE_WG,
    "{pol_map_table}": TABLE_HWG_POL_MAP,
    "{lookup_behavior_table}": TABLE_BEHAVIOR_LOOKUP,
    "{back_end_report_dataset}": DATASET_BERS,
    "{Campaign_segments_dataset}": DATASET_CAMPAIGN_SEGMENTS,
    "{tbl_cmpgn_test}": TBL_CMPGN_TEST,
}

# Default Configuration Values
DEFAULT_CONTROLLED_SIZE = 50000
DEFAULT_HG_RADIUS = 3000
DEFAULT_TIME_INTERVAL = -1
DEFAULT_HAS_SEGMENTS = 0 