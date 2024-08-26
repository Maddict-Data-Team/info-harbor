from google.cloud import bigquery

# Dictionaries

table_mapping = {
    "KSA": "POI_DB_KSA",
    "UAE": "POI_DB_UAE",
    "QAT": "POI_DB_QTR",
    "KWT": "POI_DB_KWT",
    "OMN": "POI_DB_OMN",
    "BHR": "POI_DB_BHR",
    "EGY": "POI_DB_EGP",
}

# Folders

project = "maddictdata"
dataset = "Back_End_Reports"
dir_data = "projects/segments/data"

# Keys

key_bq = "keys/maddictdata-bq.json"
key_google_sheets = "keys/maddictdata-google-sheets.json"

# Folders

MAIN_DRIVE_FOLDER_ID = '1HEJQ-0gc8VgICB6NK2yZO-aBweuTVrRf'

drive_link_folder_Adops = (
    "https://drive.google.com/drive/folders/1HEJQ-0gc8VgICB6NK2yZO-aBweuTVrRf"
)
#https://drive.google.com/drive/u/0/folders/1GuOSGxq5AlLxzaqbkzQBDQ8n7HcuhWWM https://drive.google.com/drive/u/0/folders/1HEJQ-0gc8VgICB6NK2yZO-aBweuTVrRf
# Table

table_placelift = 'Placelift'

# BQ Datasets

dataset_LS = "Location_Signals"
dataset_footfall = "Back_End_Footfall"
dataset_BERs = "Back_End_Reports"
dataset_campaign_segments = "Placelift_Campaign_Segments"
dataset_metadata = 'Metadata'

dataset_HWG = "Automated_HWG"
table_HG = "Home_Graph_Cumulative"

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



static_query_replace = {
    "{hwg_dataset}": dataset_HWG,
    "{footfall_dataset}":dataset_footfall,
    "{project}":project,
    "{location_signals_dataset}":dataset_LS,
    "{hwg_table}":table_HG,
    
}

poi_filter_fields = ["General_Category","Category","Subcategory","GM_Subcategory","Chain"]


secret_ber = f"projects/maddictdata/secrets/token-ber/versions/latest"
secret_bq = f"projects/maddictdata/secrets/secret-bq/versions/latest"
