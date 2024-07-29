# this code gets the raw segments from Big Query
from google.cloud import bigquery
from google.oauth2 import service_account
import datetime

from variables import *
from input import *

def create_client():
    # Authenticate with BigQuery
    credentials = service_account.Credentials.from_service_account_file(
        key_bq,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    bq_client = bigquery.Client(credentials=credentials, project=project)

    return bq_client

def get_raw_segments(countries, segments):

    # Initialize the BigQuery client
    client = create_client()
    # Generate and execute queries
    for country in countries:
        for segment in segments:
            if country in table_mapping:
                value = table_mapping[country]
                
                # Generate the query string
                query = f"SELECT DISTINCT(DID) FROM {project}.{value}.Behavioral_{country}_RAW_Cumulative WHERE Behavior_Name = '{segment}'"

                # Execute the query
                query_job = client.query(query)

                # Wait for the query to complete
                rows = query_job.result()

                print(f"Query for {country} - {segment} added to BigQuery dataset {dataset_campaign_segments}")
                now = datetime.datetime.now().strftime("%Y%m%d")
                segment_name = segment.replace(" ", "_")
                #segment_name = segment.replace("/", "-")
                row_count = 0
                with open(f"data/raw/{code_name}_{country}_{segment_name}_{now}.csv",'a') as outf:
                    outf.write("DID\n")
                    for row in rows:
                        row_count+=1
                        if row_count%200000==0:print("downloaded ",row_count," DIDs")
                        did = row["DID"]
                        outf.write(f"{did}\n")
            else:
                print(f"No mapping found for country: {country}")


def main():
    get_raw_segments(countries, segments)

if __name__ == "__main__":
    main()