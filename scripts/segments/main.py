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
    for index, country in enumerate(countries):
        if country in table_mapping:
            # Get the corresponding backend report for the country
            backend_report = backend_reports[index]
            # Generate the query string
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
                        {code_name},
                        '{campaign_name}',
                        DATE '{start_date}',
                        DATE '{end_date}',
                        '{country}',
                        '{stage_0}',
                        '{type}',
                        {backend_report},
                        NULL,
                        {time_interval}
                        FROM
                        `maddictdata.Metadata.Campaign_Tracker`;"""

            # print(
            #     f"Query for {campaign_name} - {country} added to BigQuery dataset {dataset_campaign_segments}"
            # )

        else:
            print(f"No mapping found for country: {country}")

        # Execute the query
        query_job = client.query(query)

        # Wait for the query to complete
        rows = query_job.result()

        print(
            f"{campaign_name} - {countries[index]} added to {tbl_campaign_tracker}"
        )


def main():
    metadata_placelift()


if __name__ == "__main__":
    main()
