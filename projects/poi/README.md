# POI Management

This project manages Points of Interest (POI) data in BigQuery. It automatically:
- Takes input with longitude, latitude, name, country, and city
- Looks up country_id and city_id from lookup tables
- Generates sequential POI_ID starting from 1 (or continues from existing max)
- Creates table `{code_name}_pois` in `Back_End_Footfall` dataset if it doesn't exist
- Inserts POIs into the table

## Structure

Similar to `campaign-tracker`, this project follows the same pattern:
- `input.py` - Input data (code_name parameter and list of POIs to add)
- `variables.py` - Configuration and constants
- `main.py` - Main processing logic

## Usage

1. **Edit `input.py`** to set the code_name and add your POIs:
```python
# Campaign code name (e.g., 122) - this will be used to create table {code_name}_pois
code_name = 122

pois = [
    {
        "longitude": 55.2708,
        "latitude": 25.2048,
        "name": "Dubai Mall",
        "country": "UAE",
        "city": "Dubai"
    },
    # Add more POIs...
]
```

2. **Run the script**:
```bash
python3 projects/poi/main.py
```

## Features

- **Automatic Table Creation**: Creates `{code_name}_pois` table in `Back_End_Footfall` dataset if it doesn't exist
- **Automatic ID Lookup**: Fetches country_id and city_id from lookup tables in the `Lookups` dataset
- **Sequential POI IDs**: Automatically generates POI_ID starting from 1 (or continues from max existing ID)
- **Table Reuse**: If table already exists, just inserts new data
- **Error Handling**: Gracefully handles missing lookup data (sets IDs to NULL with warnings)
- **Custom Radius**: Supports per-POI radius specification (default: 50 meters)

## Table Schema

The table `{code_name}_pois` is created with the following schema:
- `POI_ID` (INT64) - Sequential ID starting from 1
- `poi_name` (STRING) - Name of the POI
- `longitude` (FLOAT64) - Longitude coordinate
- `latitude` (FLOAT64) - Latitude coordinate
- `country` (STRING) - Country code (e.g., "UAE", "KSA")
- `city` (STRING) - City name
- `country_id` (INT64) - Country ID from lookup table (nullable)
- `city_id` (INT64) - City ID from lookup table (nullable)
- `radius` (INT64) - Default radius in meters (default: 50)

## Configuration

Edit `variables.py` to adjust:
- Project name (`project` - default: "maddictdata")
- BigQuery key file path (`key_bq` - default: "keys/maddictdata-bq.json")
- Dataset names (`dataset_footfall`, `dataset_metadata`)
- Lookup table names (`lookup_country_table`, `lookup_city_table`)
- Table mapping dictionary (`table_mapping`)
- POI table schema (`schema_poi`)

The default radius is set to 50 meters in `main.py` but can be overridden per POI in `input.py`.

## Input Format

Each POI in the `pois` list can have the following fields:
- `longitude` (required) - Longitude coordinate
- `latitude` (required) - Latitude coordinate
- `name` (required) - Name of the POI
- `country` (required) - Country code (e.g., "UAE", "KSA", "BHR") or country name
- `city` (required) - City name
- `radius` (optional) - Radius in meters (default: 50 if not specified)

Example with optional radius:
```python
pois = [
    {
        "longitude": 55.2708,
        "latitude": 25.2048,
        "name": "Dubai Mall",
        "country": "UAE",
        "city": "Dubai",
        "radius": 325  # Optional: custom radius in meters
    },
]
```

## Lookup Tables

The script uses lookup tables to find country and city IDs:
- **Country Lookup**: `maddictdata.Lookups.lu_country`
  - Columns: `id`, `name`, `code`
  - Matches by country name or code
- **City Lookup**: `maddictdata.Lookups.lu_city`
  - Columns: `id`, `name`, `country_id`
  - Matches by city name and country_id

## Notes

- The script creates/uses tables in `maddictdata.Back_End_Footfall` dataset
- Table name format: `{code_name}_pois` (e.g., `173_pois`)
- The script assumes lookup tables exist in the `Lookups` dataset
- Uses BigQuery credentials from `keys/maddictdata-bq.json` (relative path from project root)
- The script handles SQL injection by escaping single quotes in text fields
- If lookup tables don't have matching entries, country_id and city_id will be NULL
- **Run from project root**: The script should be executed from the `info-harbor/` directory
- Follows the same pattern as `campaign-tracker` and `segments` projects (self-contained, no shared module dependencies)

