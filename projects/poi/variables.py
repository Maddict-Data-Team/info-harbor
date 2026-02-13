from google.cloud import bigquery

# Project configuration
project = "maddictdata"

# Keys
key_bq = "keys/maddictdata-bq.json"

# BQ Datasets
dataset_footfall = "Back_End_Footfall"  # Dataset where POI tables are created
dataset_metadata = "Lookups"  # Dataset containing lookup tables

# Table mappings (for lookup purposes)
table_mapping = {
    "KSA": "POI_DB_KSA",
    "UAE": "POI_DB_UAE",
    "QAT": "POI_DB_QTR",
    "KWT": "POI_DB_KWT",
    "OMN": "POI_DB_OMN",
    "BHR": "POI_DB_BHR",
    "EGY": "POI_DB_EGP",
    "MAR": "POI_DB_MAR",
}

# Lookup tables for country and city IDs
# These tables should contain country_id and city_id mappings
lookup_country_table = "lu_country"  # Adjust based on actual table name
lookup_city_table = "lu_city"  # Adjust based on actual table name

# POI table schema for Back_End_Footfall dataset
# Based on queries.ini, the table uses: POI_ID, longitude, latitude, poi_name, radius
schema_poi = [
    bigquery.SchemaField("POI_ID", "INT64"),
    bigquery.SchemaField("poi_name", "STRING"),
    bigquery.SchemaField("longitude", "FLOAT64"),
    bigquery.SchemaField("latitude", "FLOAT64"),
    bigquery.SchemaField("country", "STRING"),
    bigquery.SchemaField("city", "STRING"),
    bigquery.SchemaField("country_id", "INT64"),
    bigquery.SchemaField("city_id", "INT64"),
    bigquery.SchemaField("radius", "INT64"),  # Default radius, can be adjusted
    bigquery.SchemaField("chain", "STRING"),
    bigquery.SchemaField("data_filter", "INT64"),
]

