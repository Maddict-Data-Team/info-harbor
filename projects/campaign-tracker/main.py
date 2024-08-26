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

    # Fetch the last code name from the table
    query_last_code_name = f"""
        SELECT MAX(code_name) AS last_code_name
        FROM `{project}.{dataset_metadata}.{tbl_campaign_tracker}`;
    """
    last_code_name_result = client.query(query_last_code_name).result()
    last_code_name = next(last_code_name_result).last_code_name

    # It will increment the code name
    new_code_name = last_code_name + 1 
    
    # Generate and execute queries
    for index, country in enumerate(countries):
        if country in table_mapping:
            # Get the corresponding backend report for the country
            backend_report = backend_reports[index]
            # Generate the query string
            query = f"""INSERT INTO
                        {project}.{dataset_metadata}.{tbl_campaign_tracker} (
                            id,
                            code_name,
                            campaign_name,
                            start_date,
                            end_date,
                            country,
                            status,
                            type,
                            backend_report,
                            last_update,
                            time_interval
                        )
                        SELECT
                        COALESCE(MAX(id), 0) + 1,
                        {new_code_name},
                        '{campaign_name}',
                        DATE '{start_date}',
                        DATE '{end_date}',
                        '{country}',
                        '{stage_0}',
                        '{type}',
                        {backend_report},
                        TIMESTAMP '{start_date}',
                        {time_interval}
                        FROM
                        `maddictdata.Metadata.Campaign_Tracker`;"""

            # Execute the query
            client.query(query)


        # Log the new code name for the campaign
        print(f"New code name {new_code_name} assigned to campaign {campaign_name} - {countries[index]}")


def main():
    metadata_placelift()


if __name__ == "__main__":
    main()
