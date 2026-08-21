import os
import sys

from google.cloud import bigquery

# projects/campaign-tracker/main.py loads this file as a flat,
# unqualified `from variables import *`, with no other sys.path setup
# of its own -- it relies entirely on however Python itself was invoked
# (a direct script run puts this file's own directory on sys.path,
# nothing more). The shared settings module below lives outside that
# directory, so it must be reachable regardless of the caller's working
# directory. Computed from this file's own location, not inherited from
# a caller-provided sys.path or cwd -- same fix, same reasoning, as
# projects/poi/variables.py's IH-048 migration: relying on cwd alone
# breaks when invoked as `cd projects/campaign-tracker && python
# main.py`, a plausible real invocation pattern. main_new.py does not
# import this file at all (confirmed: it uses shared/config/campaigns
# directly), so this only affects the legacy main.py path.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from shared.config import settings

# Metadata Status

stage_0 = settings.STATUS_PRE_VALIDATION
stage_1 = settings.STATUS_VALIDATION
stage_2 = settings.STATUS_ACTIVE
stage_3 = settings.STATUS_COMPLETION_PERIOD
stage_4 = settings.STATUS_FINISHED

# Dictionaries

table_mapping = dict(settings.CAMPAIGN_TRACKER_COUNTRY_POI_TABLES)

# Folders

project = settings.PROJECT_ID
dataset = settings.DATASET_BACKEND_REPORTS
dir_data = settings.CAMPAIGN_TRACKER_DATA_DIR

# Keys

key_bq = settings.LEGACY_BIGQUERY_KEY_PATH
key_google_sheets = settings.LEGACY_GOOGLE_SHEETS_KEY_PATH

# Campaign Tracker's own Drive folder is a different, legacy location
# from the Segments/AdOps one -- deliberately kept distinct, not
# collapsed into the shared DRIVE_ADOPS_FOLDER_URL.
drive_link_folder_Adops = settings.LEGACY_CAMPAIGN_TRACKER_DRIVE_FOLDER_URL
#https://drive.google.com/drive/u/0/folders/1GuOSGxq5AlLxzaqbkzQBDQ8n7HcuhWWM
# Table

tbl_campaign_tracker = settings.TABLE_CAMPAIGN_TRACKER
#'Campaign_Tracker'
# BQ Datasets
# 'test'

dataset_LS = settings.DATASET_LOCATION_SIGNALS
dataset_footfall = settings.DATASET_FOOTFALL
dataset_BERs = settings.DATASET_BACKEND_REPORTS
dataset_campaign_segments = settings.DATASET_CAMPAIGN_SEGMENTS
dataset_metadata = settings.DATASET_METADATA

#BQ Schemas

schema_DID = [bigquery.SchemaField("DID", "STRING")]

schema_back_end = [
    bigquery.SchemaField("campaign", "STRING"),
    bigquery.SchemaField("LINE", "STRING"),
    bigquery.SchemaField("TIMESTAMP", "TIMESTAMP"),
    bigquery.SchemaField("udid", "STRING"),
    bigquery.SchemaField("devraw", "STRING"),
    bigquery.SchemaField("country", "STRING"),
    bigquery.SchemaField("city", "STRING"),
    bigquery.SchemaField("latitude", "FLOAT64"),
    bigquery.SchemaField("longitude", "FLOAT64"),
    bigquery.SchemaField("dev_os", "STRING"),
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

schema_Combined = [
    bigquery.SchemaField("DID", "STRING"),
    bigquery.SchemaField("Segment", "STRING"),
    bigquery.SchemaField("Country", "STRING"),
    bigquery.SchemaField("Controlled", "BOOLEAN")
]