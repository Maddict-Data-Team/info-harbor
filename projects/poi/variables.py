import os
import sys

from google.cloud import bigquery

# projects/poi/main.py loads this file as a flat, unqualified `from
# variables import *`, with no other sys.path setup of its own -- it
# relies entirely on however Python itself was invoked (a direct script
# run puts this file's own directory on sys.path, nothing more). The
# shared settings module below lives outside that directory, so it must
# be reachable regardless of the caller's working directory. Computed
# from this file's own location, not inherited from a caller-provided
# sys.path or cwd (IH-048 follow-up): confirmed empirically that
# relying on cwd alone breaks when invoked as `cd projects/poi &&
# python main.py`, a plausible real invocation pattern.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from shared.config import settings

# Project configuration
project = settings.PROJECT_ID

# Keys
key_bq = settings.LEGACY_BIGQUERY_KEY_PATH

# BQ Datasets
dataset_footfall = settings.DATASET_FOOTFALL  # Dataset where POI tables are created
dataset_metadata = settings.DATASET_POI_LOOKUPS  # Dataset containing lookup tables

# Table mappings (for lookup purposes)
table_mapping = dict(settings.POI_COUNTRY_POI_TABLES)

# Lookup tables for country and city IDs
# These tables should contain country_id and city_id mappings
lookup_country_table = settings.TABLE_COUNTRY_LOOKUP  # Adjust based on actual table name
lookup_city_table = settings.TABLE_CITY_LOOKUP  # Adjust based on actual table name

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
]

