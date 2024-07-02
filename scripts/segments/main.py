from google.cloud import bigquery
from google.oauth2 import service_account
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


def metadata_placelift():
    # Initialize the BigQuery client
    client = create_client()
    # Generate and execute queries

    # Generate the query string
    query = f"""INSERT INTO {project}.{dataset_metadata}.{tbl_campaign_tracker} (code_name, campaign_name, country, start_date, end_date, status, type)
    VALUES ('{code_name}', '{campaign_name}', '{countries}', '{start_date}', '{end_date}', 'On Hold', '{type}');"""

    query = f"""INSERT INTO
  {project}.{dataset_metadata}.{tbl_campaign_tracker} ( id,
    code_name,
    campaign_name,
    start_date,
    end_date,
    country,
    status,
    type,
    backend_report,
    last_update,
    time_interval )
SELECT
  COALESCE(MAX(id), 0) + 1,
  99999,
  'Test Campaign',
  DATE '2024-01-01',
  DATE '2024-12-31',
  'Test Country',
  'Active',
  'Test Type',
  12345,
  TIMESTAMP '2024-01-01 00:00:00 UTC',
  30
FROM
  `maddictdata.Metadata.Campaign_Tracker`;"""

    # Execute the query
    query_job = client.query(query)

    # Wait for the query to complete
    rows = query_job.result()

    print(
        f"Query for {campaign_name} - {countries} added to BigQuery dataset {dataset_campaign_segments}"
    )


def main():
    metadata_placelift()


if __name__ == "__main__":
    main()
