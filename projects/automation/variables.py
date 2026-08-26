import os
import sys

from google.cloud import bigquery

# main.py, query_orchestrator.py, and upload_backend.py all load this
# file via importlib.util.spec_from_file_location (the IH-047 fix), and
# custom_codename.py loads it as a flat `from variables import *` -- none
# of those four callers put the repository root on sys.path themselves.
# The shared settings module below lives outside this file's own
# directory, so it must be reachable regardless of which loading style
# or working directory the caller used. Computed from this file's own
# location, not inherited from a caller-provided sys.path or cwd -- same
# fix, same reasoning, as projects/poi/variables.py,
# projects/campaign-tracker/variables.py, and
# projects/segments/scripts/variables.py's IH-048 migrations.
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_script_dir))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# IH-050: Cloud Functions deploys ONLY this directory (--source
# projects/automation, .github/workflows/deploy.yml:31) -- shared/ lives
# outside it and is never uploaded, so `from shared.config import
# settings` unconditionally would import-fail in the deployed Cloud
# Function even though it works in every local/test context where the
# full repository is checked out. Prefer the real, parity-checked
# shared/config/settings.py when it's reachable; fall back to this
# directory's own byte-identical copy (_shared_config_fallback.py, which
# IS part of the deployed source tree) when it isn't. Loaded by explicit
# path, not a bare `import`, so it does not depend on _script_dir being
# on sys.path (matching the IH-047 loading pattern already used for this
# file itself). tests/unit/test_automation_deploy_artifact_isolated.py
# proves both branches produce identical values and that the fallback is
# actually exercised when shared/ is genuinely absent.
try:
    from shared.config import settings
except ModuleNotFoundError as _import_error:
    # Narrowed to exactly "the shared package/module isn't present"
    # (the deployed-artifact case) -- NOT a bare `except ImportError`,
    # which would also silently swallow a genuine internal import error
    # raised from inside an actually-present shared/config/settings.py
    # (e.g. one of its own imports breaking) and route to the fallback
    # instead of failing loudly. Re-raise anything else.
    if _import_error.name not in ("shared", "shared.config", "shared.config.settings"):
        raise

    import importlib.util as _importlib_util

    _fallback_spec = _importlib_util.spec_from_file_location(
        "automation_shared_config_fallback",
        os.path.join(_script_dir, "_shared_config_fallback.py"),
    )
    settings = _importlib_util.module_from_spec(_fallback_spec)
    _fallback_spec.loader.exec_module(settings)


# credentials

project = settings.PROJECT_ID

# Folders

folder_id_Backend_Reports = settings.DRIVE_BACKEND_REPORTS_FOLDER_ID

# Secret Manager

secret_ber = settings.SECRET_BACKEND_REPORT_TOKEN
secret_bq = settings.SECRET_BIGQUERY_CREDENTIALS

# Keys

key_bq = settings.LEGACY_BIGQUERY_KEY_PATH
key_google_sheets = settings.LEGACY_GOOGLE_SHEETS_KEY_PATH

# BQ Datasets

dataset_LS = settings.DATASET_LOCATION_SIGNALS
dataset_footfall = settings.DATASET_FOOTFALL
dataset_BERs = settings.DATASET_BACKEND_REPORTS
dataset_campaign_segments = settings.DATASET_CAMPAIGN_SEGMENTS
dataset_Districts = settings.DATASET_DISTRICT_MAPPING
dataset_HWG = settings.DATASET_AUTOMATED_HWG
dataset_mt_Placelift = settings.DATASET_METADATA_PLACELIFT
dataset_metadata = settings.DATASET_METADATA

table_HG = settings.TABLE_HOME_GRAPH
tbl_cmpgn_tracker = settings.TABLE_CAMPAIGN_TRACKER
tbl_cmpgn_test = settings.TABLE_CAMPAIGN_TEST
table_behavior_lookup = settings.TABLE_BEHAVIOR_LOOKUP
table_os_mapping = settings.TABLE_DEVICE_OS_MAPPING


# Metadata Status

stage_0 = settings.STATUS_PRE_VALIDATION
stage_1 = settings.STATUS_VALIDATION
stage_2 = settings.STATUS_ACTIVE
stage_3 = settings.STATUS_COMPLETION_PERIOD
stage_4 = settings.STATUS_FINISHED
stage_5 = settings.STATUS_ERROR
stage_6 = settings.STATUS_ON_HOLD

# BQ Schemas

schema_back_end = [
    bigquery.SchemaField("campaign", "STRING"),
    bigquery.SchemaField("LINE", "STRING"),
    bigquery.SchemaField("TIMESTAMP", "TIMESTAMP"),
    bigquery.SchemaField("req_id", "STRING"),
    bigquery.SchemaField("udid_idfa", "STRING"),
    bigquery.SchemaField("devraw", "STRING"),
    bigquery.SchemaField("country", "STRING"),
    bigquery.SchemaField("city", "STRING"),
    bigquery.SchemaField("latitude", "FLOAT64"),
    bigquery.SchemaField("longitude", "FLOAT64"),
    bigquery.SchemaField("dev_os", "STRING"),
    bigquery.SchemaField("dev_language", "STRING"),
    bigquery.SchemaField("dev_make", "STRING"),
    bigquery.SchemaField("dev_type", "STRING"),
    bigquery.SchemaField("connection_type", "STRING"),
    bigquery.SchemaField("carrier", "STRING"),
    bigquery.SchemaField("exchange", "STRING"),
    bigquery.SchemaField("dev_ip", "STRING"),
    bigquery.SchemaField("zip", "STRING"),
    bigquery.SchemaField("creative", "STRING"),
    bigquery.SchemaField("ad_size", "STRING"),
    bigquery.SchemaField("App_ID", "INT64"),
    bigquery.SchemaField("environment", "STRING"),
    bigquery.SchemaField("publisher", "STRING"),
    bigquery.SchemaField("App_Name", "STRING"),
    bigquery.SchemaField("impressions", "INT64"),
    bigquery.SchemaField("clicks", "INT64"),
]


table_mapping = dict(settings.AUTOMATION_COUNTRY_POI_TABLES)


# will transfere to variables later, and change some of the names
static_query_replace = {
    "{hwg_dataset}": dataset_HWG,
    "{footfall_dataset}": dataset_footfall,
    "{project}": project,
    "{metadata_dataset}": dataset_metadata,
    "{campaign_tracker_table}": tbl_cmpgn_tracker,
    "{location_signals_dataset}": dataset_LS,
    "{device_os_mapping_table}": table_os_mapping,
    "{hwg_table}": table_HG,
    "{lookup_behavior_table}": table_behavior_lookup,
    "{back_end_report_dataset}": dataset_BERs,
    "{Campaign_segments_dataset}": dataset_campaign_segments,
    "{tbl_cmpgn_test}": tbl_cmpgn_test,
}

# Campaign Tracker

q_update_status = f"""
UPDATE `maddictdata.Metadata.{tbl_cmpgn_tracker}`
SET status = CASE
    WHEN CURRENT_DATE() BETWEEN start_date + 9 AND end_date + 9 THEN 'Active'
    WHEN CURRENT_DATE() < start_date + 9 THEN 'Validation'
    WHEN CURRENT_DATE() > end_date + 9 THEN 'Completion Period'
    ELSE status
END
WHERE status NOT IN ('Finished', 'On Hold');"""

q_select_active_interval = f"""SELECT
  id,
  campaign_name,
  code_name,
  backend_report,
  status
FROM
  `maddictdata.Metadata.{tbl_cmpgn_tracker}`
WHERE
  ( status = 'Active'
    AND time_interval > 0
    AND DATE_SUB(CURRENT_DATE(), INTERVAL time_interval DAY) >= DATE(last_update) )
  OR status = 'Completion Period';"""


# q_select_by_codename = """SELECT
#   code_name,
#   backend_report
#   FROM
#   `maddictdata.Metadata.{campaign_tracker_table}`
#   where
#   code_name = {codename}
# """


# Main Queries

#########################


def q_deduplicate_ber(code_name):

    return f"""
CREATE OR REPLACE TABLE
  `{project}.{dataset_BERs}.{code_name}` AS
SELECT
  DISTINCT *
FROM
  `{project}.{dataset_BERs}.{code_name}`;
"""
