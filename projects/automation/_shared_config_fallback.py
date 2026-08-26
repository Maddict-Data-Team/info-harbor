"""Self-contained fallback for the subset of shared/config/settings.py's
values that projects/automation/variables.py needs.

Cloud Functions deploys only `projects/automation` (--source
projects/automation, .github/workflows/deploy.yml:31) -- shared/config/
lives outside that directory and is never part of the deployed artifact.
variables.py imports from shared.config.settings when it's reachable (any
checkout of the full repository: tests, custom_codename.py, local runs),
and falls back to this module -- an exact, byte-for-byte copy of the
values it needs -- only when it isn't (the deployed Cloud Function).

Every value below must stay identical to its shared/config/settings.py
counterpart. tests/unit/test_automation_deploy_artifact_isolated.py
enforces that with a direct parity check, and separately proves that a
copy of projects/automation/ alone (with shared/ genuinely unimportable)
still imports variables.py and main.py correctly through this fallback,
producing byte-identical values.
"""

PROJECT_ID = "maddictdata"

DATASET_LOCATION_SIGNALS = "Location_Signals"
DATASET_FOOTFALL = "Back_End_Footfall"
DATASET_BACKEND_REPORTS = "Back_End_Reports"
DATASET_CAMPAIGN_SEGMENTS = "Placelift_Campaign_Segments"
DATASET_DISTRICT_MAPPING = "District_Mapping"
DATASET_AUTOMATED_HWG = "Automated_HWG"
DATASET_METADATA = "Metadata"
DATASET_METADATA_PLACELIFT = "maddictdata.Metadata.Placelift"

TABLE_HOME_GRAPH = "Home_Graph_Cumulative"
TABLE_CAMPAIGN_TRACKER = "Campaign_Tracker"
TABLE_CAMPAIGN_TEST = "test"
TABLE_BEHAVIOR_LOOKUP = "Lookup_Behavior"
TABLE_DEVICE_OS_MAPPING = "device_os_mapping"

AUTOMATION_COUNTRY_POI_TABLES = {
    "KSA": "POI_DB_KSA",
    "UAE": "POI_DB_UAE",
    "QAT": "POI_DB_QTR",
    "KWT": "POI_DB_KWT",
    "OMN": "POI_DB_OMN",
    "BHR": "POI_DB_BHR",
}

STATUS_PRE_VALIDATION = "Pre-Validation"
STATUS_VALIDATION = "Validation"
STATUS_ACTIVE = "Active"
STATUS_COMPLETION_PERIOD = "Completion Period"
STATUS_FINISHED = "Finished"
STATUS_ERROR = "Error"
STATUS_ON_HOLD = "On Hold"

DRIVE_BACKEND_REPORTS_FOLDER_ID = "1vKOH8eDs92jHSaGyPILAa9p3qH8YUHNo"

SECRET_BACKEND_REPORT_TOKEN = "projects/maddictdata/secrets/token-ber/versions/latest"
SECRET_BIGQUERY_CREDENTIALS = "projects/maddictdata/secrets/secret-bq/versions/latest"

LEGACY_BIGQUERY_KEY_PATH = "keys/maddictdata-bq.json"
LEGACY_GOOGLE_SHEETS_KEY_PATH = "keys/maddictdata-google-sheets.json"
