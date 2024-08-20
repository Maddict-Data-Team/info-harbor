# this code gets the raw segments from Big Query
from google.cloud import bigquery
from google.oauth2 import service_account
import datetime
import sys
import os
import query_orchestrator
from tqdm import tqdm  # Import tqdm for the progress bar

from variables import *
# Get the path to the directory containing this script (main.py)
script_dir = os.path.dirname(__file__)

# Get the parent directory of 'scripts'
project_root = os.path.abspath(os.path.join(script_dir, '..'))

# Add the parent directory to sys.path
sys.path.append(project_root)

from input import *

def get_raw_segments(countries, segments, bq_client):
    # Wrap the outer loop with tqdm for a progress bar
    for country in tqdm(countries, desc="Processing countries"):
        for segment in tqdm(segments, desc=f"Processing segments for {country}", leave=False):
            if country in table_mapping:
                value = table_mapping[country]
                
                # Run the query using the query orchestrator
                rows = query_orchestrator.run_query_behavior(segment, bq_client, country, code_name)
                
                if "custom" in segment:
                    segment = segment.split("_", 1)[1]

                print(f"Query for {country} - {segment} added to BigQuery dataset {dataset_campaign_segments}")
                now = datetime.datetime.now().strftime("%Y%m%d")
                segment_name = segment.replace(" ", "_")
                #segment_name = segment.replace("/", "-")
                row_count = 0
                with open(f"projects/segments/data/raw/{code_name}_{country}_{segment_name}_{now}.csv", 'a') as outf:
                    outf.write("DID\n")
                    for row in rows:
                        row_count += 1
                        if row_count % 200000 == 0:
                            print("downloaded ", row_count, " DIDs")
                        did = row.DID
                        outf.write(f"{did}\n")
            else:
                print(f"No mapping found for country: {country}")

def main():
    get_raw_segments(countries, segments)

if __name__ == "__main__":
    main()
