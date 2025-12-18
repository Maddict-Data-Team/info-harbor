from google.cloud import bigquery
from google.oauth2 import service_account
from google.cloud.exceptions import NotFound
from variables import *
from input import *


def create_client():
    """Authenticate with BigQuery"""
    credentials = service_account.Credentials.from_service_account_file(
        key_bq,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    bq_client = bigquery.Client(credentials=credentials, project=project)
    return bq_client


def get_country_id(bq_client, country_name):
    """
    Get country id from lookup table based on country name or code.
    Table structure: id, name, code
    """
    query = f"""
        SELECT id
        FROM `{project}.{dataset_metadata}.{lookup_country_table}`
        WHERE name = '{country_name}'
        OR code = '{country_name}'
        LIMIT 1
    """
    
    try:
        results = bq_client.query(query).result()
        row = next(results, None)
        if row:
            return row.id
        else:
            print(f"⚠️ Warning: Country '{country_name}' not found in lookup table. Using NULL.")
            return None
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch country_id for '{country_name}': {e}")
        return None


def get_city_id(bq_client, city_name, country_name):
    """
    Get city id from lookup table based on city name and country.
    Table structure: id, name, country_id
    First gets country_id, then uses it to find the city.
    """
    # First, get the country_id
    country_id = get_country_id(bq_client, country_name)
    if country_id is None:
        print(f"⚠️ Warning: Cannot find city '{city_name}' - country '{country_name}' not found.")
        return None
    
    query = f"""
        SELECT id
        FROM `{project}.{dataset_metadata}.{lookup_city_table}`
        WHERE name = '{city_name}'
        AND country_id = {country_id}
        LIMIT 1
    """
    
    try:
        results = bq_client.query(query).result()
        row = next(results, None)
        if row:
            return row.id
        else:
            print(f"⚠️ Warning: City '{city_name}' in '{country_name}' not found in lookup table. Using NULL.")
            return None
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch city_id for '{city_name}': {e}")
        return None


def table_exists(bq_client, dataset_id, table_id):
    """Check if a table exists in BigQuery"""
    try:
        bq_client.get_table(f"{project}.{dataset_id}.{table_id}")
        return True
    except NotFound:
        return False


def create_poi_table(bq_client, table_name):
    """
    Create the POI table if it doesn't exist.
    Table name format: {code_name}_pois
    """
    table_ref = bq_client.dataset(dataset_footfall).table(table_name)
    
    # Create table with schema
    table = bigquery.Table(table_ref, schema=schema_poi)
    
    try:
        table = bq_client.create_table(table)
        print(f"✅ Created table: {project}.{dataset_footfall}.{table_name}")
        return True
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        return False


def get_max_poi_id(bq_client, table_name):
    """
    Get the maximum POI_ID from the POI table.
    Returns 0 if table is empty or doesn't exist.
    """
    query = f"""
        SELECT MAX(POI_ID) as max_id
        FROM `{project}.{dataset_footfall}.{table_name}`
    """
    
    try:
        results = bq_client.query(query).result()
        row = next(results, None)
        if row and row.max_id is not None:
            return row.max_id
        return 0
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch max POI_ID: {e}")
        print(f"   Assuming table is empty, starting from 1")
        return 0


def insert_pois(bq_client, pois_data, table_name):
    """
    Insert POIs into the POI table in Back_End_Footfall dataset.
    """
    # Check if table exists, create if not
    if not table_exists(bq_client, dataset_footfall, table_name):
        print(f"📋 Table {table_name} does not exist. Creating it...")
        if not create_poi_table(bq_client, table_name):
            return False
    else:
        print(f"✅ Table {table_name} already exists. Inserting data...")
    
    # Get the starting POI_ID
    max_poi_id = get_max_poi_id(bq_client, table_name)
    starting_poi_id = max_poi_id + 1
    
    # Prepare insert values
    values = []
    default_radius = 80  # Default radius in meters if not specified in input
    
    for idx, poi in enumerate(pois_data):
        poi_id = starting_poi_id + idx
        country_id = get_country_id(bq_client, poi["country"])
        city_id = get_city_id(bq_client, poi["city"], poi["country"])
        
        # Get radius from input or use default
        radius = poi.get("radius", default_radius)
        
        # Escape single quotes in name
        name_escaped = poi['name'].replace("'", "''")
        city_escaped = poi['city'].replace("'", "''")
        
        values.append(
            f"({poi_id}, '{name_escaped}', {poi['longitude']}, {poi['latitude']}, "
            f"'{poi['country']}', '{city_escaped}', "
            f"{country_id if country_id is not None else 'NULL'}, "
            f"{city_id if city_id is not None else 'NULL'}, "
            f"{radius})"
        )
    
    # Build insert query
    query = f"""
        INSERT INTO `{project}.{dataset_footfall}.{table_name}`
        (POI_ID, poi_name, longitude, latitude, country, city, country_id, city_id, radius)
        VALUES
        {', '.join(values)}
    """
    
    try:
        job = bq_client.query(query)
        job.result()  # Wait for the job to complete
        print(f"✅ Successfully inserted {len(pois_data)} POI(s) into {project}.{dataset_footfall}.{table_name}")
        print(f"   POI IDs: {starting_poi_id} to {starting_poi_id + len(pois_data) - 1}")
        return True
    except Exception as e:
        print(f"❌ Error inserting POIs: {e}")
        return False


def process_pois():
    """
    Main function to process POIs and insert into {code_name}_pois table.
    """
    bq_client = create_client()
    
    # Create table name from code_name
    table_name = f"{code_name}_pois"
    
    print(f"📊 Processing {len(pois)} POI(s) for table: {table_name}")
    print(f"   Dataset: {project}.{dataset_footfall}")
    
    # Insert all POIs into the table
    insert_pois(bq_client, pois, table_name)


def main():
    if not pois:
        print("⚠️ No POIs to process. Please add POIs to input.py")
        return
    
    if not code_name:
        print("⚠️ No code_name specified. Please set code_name in input.py")
        return
    
    print(f"🚀 Starting POI processing...")
    print(f"   Code Name: {code_name}")
    print(f"   Table: {code_name}_pois")
    print(f"   POIs to process: {len(pois)}\n")
    
    process_pois()
    print("\n✅ POI processing completed!")


if __name__ == "__main__":
    main()

