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

# Get the parent directory to 'scripts'
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

                # print(f"Query for {segment}-{country} added to BigQuery dataset {dataset_campaign_segments}")
                now = datetime.datetime.now().strftime("%Y%m%d")
                segment_name = segment.replace(" ", "_").replace("/","-")
                
                row_count = 0
                with tqdm(desc=f"Downloading DIDs for {segment} - {country}", unit=" DID", leave=False) as pbar:
                    with open(f"projects/segments/data/raw/{code_name}_{country}_{segment_name}_{now}.csv", 'a') as outf:
                        outf.write("DID\n")
                        for row in rows:
                            row_count += 1
                            did = row.DID
                            outf.write(f"{did}\n")
                            # print(row_count)
                            if row_count % 50000 == 0:
                                pbar.update(50000)  # Update tqdm for every 50,000 segments

                        # Update the remaining rows if they don't add up to 50,000
                        remaining = row_count % 50000
                        if remaining > 0:
                            pbar.update(remaining)
            else:
                print(f"No mapping found for country: {country}")

def main():
    get_raw_segments(countries, segments, bq_client)

if __name__ == "__main__":
    main()
