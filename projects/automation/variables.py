import importlib.util
import os

from google.cloud import bigquery

# IH-050/IH-051: Cloud Functions deploys ONLY this directory (--source
# projects/automation, .github/workflows/deploy.yml:31) -- shared/ lives
# outside it and is never uploaded. Two successive security reviews
# found problems with sourcing shared/config/settings.py:
#
#   IH-050 (fixed): an unconditional `from shared.config import
#   settings` import-fails outright in the deployed artifact, since
#   shared/ genuinely isn't there.
#
#   IH-051 (fixed here): the IH-050 fix's own remedy -- inserting a
#   computed repository root into sys.path and then `from shared.config
#   import settings` -- reintroduced a subtler problem. Importing the
#   generic package name `shared.config.settings` lets Python's import
#   machinery resolve it against ANYTHING already on sys.path, not
#   necessarily this repository's own shared/config/settings.py --
#   inside the deployed, source-only artifact, the computed "repository
#   root" can point outside the artifact entirely, and if the Cloud
#   Functions runtime or any dependency happens to expose an unrelated
#   top-level `shared` namespace, Automation could silently load THAT
#   instead of failing over to its own bundled fallback, running
#   unrelated code or configuration under the same import statement.
#
# Fixed by never mutating sys.path and never importing the generic
# `shared.config.settings` package name at all. Instead, resolve this
# file's own expected canonical settings file by its OWN exact,
# computed filesystem path (not a package lookup), and load whichever
# file actually exists there -- the real shared/config/settings.py in a
# full repository checkout, or projects/automation/_shared_config_fallback.py
# (bundled inside the deployed source tree) when it doesn't -- by exact
# path via importlib.util.spec_from_file_location. This can never
# resolve to an unrelated same-named package, because it never performs
# a name-based import at all.
#
# tests/unit/test_automation_deploy_artifact_isolated.py proves both
# branches produce identical values, that the fallback is exercised
# when the canonical file is genuinely absent, and that a conflicting
# fake `shared.config.settings` module injected into sys.modules/
# sys.path does not get picked up in either case.
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_script_dir))
_canonical_settings_path = os.path.join(_repo_root, "shared", "config", "settings.py")
_fallback_settings_path = os.path.join(_script_dir, "_shared_config_fallback.py")

if os.path.isfile(_canonical_settings_path):
    _settings_module_name = "automation_shared_config_settings"
    _settings_path = _canonical_settings_path
else:
    _settings_module_name = "automation_shared_config_fallback"
    _settings_path = _fallback_settings_path

_settings_spec = importlib.util.spec_from_file_location(_settings_module_name, _settings_path)
if _settings_spec is None or _settings_spec.loader is None:
    raise ImportError(
        f"Could not load a settings module for projects/automation/variables.py "
        f"from {_settings_path!r} (spec_from_file_location returned "
        f"{_settings_spec!r})"
    )
settings = importlib.util.module_from_spec(_settings_spec)
_settings_spec.loader.exec_module(settings)


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
