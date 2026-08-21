import os
import sys

from google.cloud import bigquery

# This file is loaded two different ways across projects/segments/scripts/:
#   - a flat `from variables import *` (split_segments.py, create_be_table.py)
#   - importlib.util.spec_from_file_location under alias "variables_local"
#     (get_segments_raw.py, query_orchestrator.py, authenticate_to_cloud.py,
#     transfer_to_drive.py, push_to_bq.py, delete_from_drive.py)
# Neither loading style puts the repository root on sys.path, and this
# file's own directory is the only thing guaranteed to be reachable (a
# direct script run puts the invoked script's own directory on sys.path;
# spec_from_file_location doesn't touch sys.path at all). The shared
# settings module lives outside this directory, so it must be reachable
# regardless of the caller's working directory or which of the two
# loading styles is used. Computed from this file's own __file__, not
# inherited from a caller-provided sys.path or cwd -- same fix, same
# reasoning, as projects/poi/variables.py (Phase 2b) and
# projects/campaign-tracker/variables.py (Phase 2c).
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from shared.config import settings

# Dictionaries

table_mapping = dict(settings.SEGMENTS_COUNTRY_POI_TABLES)

# Folders

project = settings.PROJECT_ID
dataset = settings.DATASET_BACKEND_REPORTS
dir_data = settings.SEGMENTS_DATA_DIR

# Keys

key_bq = settings.LEGACY_BIGQUERY_KEY_PATH
key_google_sheets = settings.LEGACY_GOOGLE_SHEETS_KEY_PATH

# Folders

MAIN_DRIVE_FOLDER_ID = settings.DRIVE_MAIN_FOLDER_ID

drive_link_folder_Adops = settings.DRIVE_ADOPS_FOLDER_URL
# https://drive.google.com/drive/u/0/folders/1GuOSGxq5AlLxzaqbkzQBDQ8n7HcuhWWM https://drive.google.com/drive/u/0/folders/1HEJQ-0gc8VgICB6NK2yZO-aBweuTVrRf
# Table

table_placelift = settings.TABLE_PLACELIFT

# BQ Datasets

dataset_LS = settings.DATASET_LOCATION_SIGNALS
dataset_footfall = settings.DATASET_FOOTFALL
dataset_BERs = settings.DATASET_BACKEND_REPORTS
dataset_campaign_segments = settings.DATASET_CAMPAIGN_SEGMENTS
dataset_metadata = settings.DATASET_METADATA

dataset_HWG = settings.DATASET_AUTOMATED_HWG
table_HG = settings.TABLE_HOME_GRAPH
table_WG = settings.TABLE_WORK_GRAPH
table_hwg_pol_map = settings.TABLE_HWG_POL_MAPPING
# BQ Schemas

schema_DID = [bigquery.SchemaField("DID", "STRING")]

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

schema_Combined = [
    bigquery.SchemaField("DID", "STRING"),
    bigquery.SchemaField("Segment", "STRING"),
    bigquery.SchemaField("Country", "STRING"),
    bigquery.SchemaField("Controlled", "BOOLEAN"),
]


static_query_replace = {
    "{hwg_dataset}": dataset_HWG,
    "{footfall_dataset}": dataset_footfall,
    "{project}": project,
    "{location_signals_dataset}": dataset_LS,
    "{hg_table}": table_HG,
    "{wg_table}": table_WG,
    "{pol_map_table}": table_hwg_pol_map,
}

poi_filter_fields = list(settings.POI_FILTER_FIELDS)


secret_ber = settings.SECRET_BACKEND_REPORT_TOKEN
secret_bq = settings.SECRET_BIGQUERY_CREDENTIALS
