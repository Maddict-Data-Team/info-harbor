from google.cloud import bigquery
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google.cloud import secretmanager
import json

import upload_backend
import query_orchestrator

from variables import *


def get_secret(secret_client, secret_name):
    response = secret_client.access_secret_version(request={"name": secret_name})
    secret_data = response.payload.data.decode("UTF-8")
    return json.loads(secret_data)


def authenticate_with_bigquery(secret_data_bq_info):
    credentials = service_account.Credentials.from_service_account_info(
        secret_data_bq_info,
        scopes=[
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return bigquery.Client(credentials=credentials, project=project)


def create_drive_service(secret_data_token_info):
    creds = Credentials.from_authorized_user_info(secret_data_token_info)
    return build("drive", "v3", credentials=creds)





def start_the_process(bq_client, drive_service, code_name):
    config = query_orchestrator.read_config()

    metadata_raw = query_orchestrator.get_campaign_tracker_data(code_name, config, bq_client)

    # List to collect unique code names
    unique_code_names = set()

    # Process each rows
    for row in metadata_raw:
        backend_report = row.backend_report
        
        print(f"Processing row: code_name = {code_name}")
        
        # Check if the code_name has already been processed
        # if code_name not in processed_code_names:

        if backend_report != 0:
            # Upload backend for this code_name
            upload_backend.main(drive_service, bq_client, backend_report, code_name)
        
        # Add the code_name to the set and list
        # processed_code_names.add(code_name)
        unique_code_names.add(code_name)

    # Iterate over unique code names and call query_orchestrator
    for code_name in unique_code_names:
        query_orchestrator.run_by_codename(code_name, bq_client)


def run_query(query, bq_client):
    query_job = bq_client.query(query)
    query_job.result()
    print("Query executed successfully")


def query_bigquery_and_process(code_name):

    secret_client = secretmanager.SecretManagerServiceClient()

    # Get secrets
    secret_data_token_info = get_secret(secret_client, secret_ber)
    secret_data_bq_info = get_secret(secret_client, secret_bq)

    # Authenticate with BigQuery and create Drive service
    bq_client = authenticate_with_bigquery(secret_data_bq_info)
    drive_service = create_drive_service(secret_data_token_info)



    # Run the process
    start_the_process(bq_client, drive_service, code_name)

    return "Main Automation Done!"


def main():
    query_bigquery_and_process(122)


if __name__ == "__main__":
    main()
