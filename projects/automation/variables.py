from google.cloud import bigquery


# credentials

project = "maddictdata"

# Folders

folder_id_Backend_Reports = "1vKOH8eDs92jHSaGyPILAa9p3qH8YUHNo"

# Secret Manager

secret_ber = f"projects/maddictdata/secrets/token-ber/versions/latest"
secret_bq = f"projects/maddictdata/secrets/secret-bq/versions/latest"

# Keys

key_bq = "keys/maddictdata-bq.json"
key_google_sheets = "keys/maddictdata-google-sheets.json"

# BQ Datasets

dataset_LS = "Location_Signals"
dataset_footfall = "Back_End_Footfall"
dataset_BERs = "Back_End_Reports"
dataset_campaign_segments = "Placelift_Campaign_Segments"
dataset_Districts = "District_Mapping"
dataset_HWG = "Automated_HWG"
dataset_mt_Placelift = "maddictdata.Metadata.Placelift"
dataset_metadata = "Metadata"

table_HG = "Home_Graph_Cumulative"
tbl_cmpgn_tracker = "Campaign_Tracker"
tbl_cmpgn_test = "test"
table_behavior_lookup = "Lookup_Behavior"
table_os_mapping = "device_os_mapping"


# Metadata Status

stage_0 = "Pre-Validation"
stage_1 = "Validation"
stage_2 = "Active"
stage_3 = "Completion Period"
stage_4 = "Finished"

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


table_mapping = {
    "KSA": "POI_DB_KSA",
    "UAE": "POI_DB_UAE",
    "QAT": "POI_DB_QTR",
    "KWT": "POI_DB_KWT",
    "OMN": "POI_DB_OMN",
    "BHR": "POI_DB_BHR",
}


#will transfere to variables later, and change some of the names
static_query_replace = {
    "{hwg_dataset}": dataset_HWG,
    "{footfall_dataset}":dataset_footfall,
    "{project}":project,
    "{metadata_dataset}":dataset_metadata,
    "{campaign_tracker_table}":tbl_cmpgn_tracker,
    "{location_signals_dataset}":dataset_LS,
    "{device_os_mapping_table}":table_os_mapping,
    "{hwg_table}":table_HG,
    "{lookup_behavior_table}":table_behavior_lookup,
    "{back_end_report_dataset}":dataset_BERs,
    "{Campaign_segments_dataset}":dataset_campaign_segments,
    "{tbl_cmpgn_test}":tbl_cmpgn_test
}

country_id_dict = {
    "UAE":"1",
    "KSA":"2",
    "KWT":"3"}


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
  code_name,
  backend_report
FROM
  `maddictdata.Metadata.{tbl_cmpgn_tracker}`
WHERE
  ( status = 'Active'
    AND time_interval > 0
    AND DATE_SUB(CURRENT_DATE(), INTERVAL time_interval DAY) >= DATE(last_update) )
  OR ( status = 'Completion Period'
    AND DATE_SUB(CURRENT_DATE(), INTERVAL 9 DAY) >= DATE(end_date) );"""
  

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
