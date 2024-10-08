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


def start_the_process(bq_client, drive_service, query):
    query_job = bq_client.query(query)
    results = query_job.result()

    # Set to keep track of processed code names
    # processed_code_names = set()

    # List to collect unique code names
    unique_code_names = set()

    # Process each rows
    for row in results:
        id = row.id
        campaign_name = row.campaign_name
        code_name = row.code_name
        backend_report = row.backend_report
        status = row.status
        print('-------------------------------------------------\n')
        print(f"Processing info: code_name={code_name}, campaign_name={campaign_name}, id={id}")

        
        # Check if the code_name has already been processed
        # if code_name not in processed_code_names:
        proceed = True
        if backend_report != 0:
            try:
                # Upload backend for this code_name
                BER_updated = upload_backend.backend_processing(
                    drive_service, bq_client, backend_report, code_name
                )
                if not BER_updated and status != stage_3:
                    proceed = False
            except Exception as e:
                print(f"Error in BER, for codename {code_name}, error is : {e}")
                continue
        if not proceed:
            print(f"Skipped {code_name} because it's BER was not updated")
            continue
        
        # Finishes if status is at stage_3
        if status == stage_3:
            print(f"Updating for {code_name} because it's status is {status}")
            # Update the status to "Finished" in BigQuery
            update_query = f"""
                UPDATE `maddictdata.Metadata.{tbl_cmpgn_tracker}`
                SET status = 'Finished'
                WHERE id = {id};
            """
            run_query(update_query, bq_client)

        # Add the code_name to the set and list
        # processed_code_names.add(code_name)
        unique_code_names.add(code_name)

    # Iterate over unique code names and call query_orchestrator
    for code_name in unique_code_names:
        query_orchestrator.run_by_codename(code_name, bq_client)

    print('Codenames that ran during this process: ')
    if not unique_code_names:
        print('None')
    else:
        print(unique_code_names)



def run_query(query, bq_client):
    query_job = bq_client.query(query)
    query_job.result()
    print("Query executed successfully")


def query_bigquery_and_process():

    secret_client = secretmanager.SecretManagerServiceClient()

    # Get secrets
    secret_data_token_info = get_secret(secret_client, secret_ber)
    secret_data_bq_info = get_secret(secret_client, secret_bq)

    # Authenticate with BigQuery and create Drive service
    bq_client = authenticate_with_bigquery(secret_data_bq_info)
    drive_service = create_drive_service(secret_data_token_info)

    # Run queries and process data
    q_campagin_tracker = [(q_update_status, "(Updating Status)")]

    for query, message in q_campagin_tracker:
        run_query(query, bq_client)
        print(message)

    # Run the process
    start_the_process(bq_client, drive_service, q_select_active_interval)

    return "Main Automation Done!"


def main(request=None):
    query_bigquery_and_process()

    return ("Function executed successfully", 200)


if __name__ == "__main__":
    main()