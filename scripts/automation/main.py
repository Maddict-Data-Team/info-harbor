from google.cloud import bigquery
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google.cloud import secretmanager
import json

import doc_to_bq
import footfall

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
########################################################
def start_the_process(bq_client, drive_service, query):
    
    query_job = bq_client.query(query)
    results = query_job.result()

    # TODO
    #### CHOOSE ACCORDING
    #CODENAME []
    for row in results:
        code_name = row.code_name
        campaign_name = row.campaign_name
        country = row.country
        start_date = str(row.start_date)
        end_date = str(row.end_date)
        
        print(f"Processing row: code = {code_name}")

        doc_to_bq.main(code_name, drive_service, bq_client)
        #APPEND TO LIST IF NOT IN IT
    #ITERATE OVER LIST
    footfall.main(bq_client, code_name, country, start_date, end_date)

def run_query(query, bq_client):
    query_job = bq_client.query(query)
    query_job.result()
    print("Query executed successfully")


def query_bigquery_and_process(q_md_get_placelift, update_status_2):
    
    secret_client = secretmanager.SecretManagerServiceClient()
    
    # Get secrets
    secret_data_token_info = get_secret(secret_client, secret_ber)
    secret_data_bq_info = get_secret(secret_client, secret_bq)
    
    # Authenticate with BigQuery and create Drive service
    bq_client = authenticate_with_bigquery(secret_data_bq_info)
    drive_service = create_drive_service(secret_data_token_info)

    # Run queries and process data
    q_campagin_tracker = [
        (q_update_status, "(Updating Status)")
    ]
    
    for query, message in q_campagin_tracker:
        run_query(query, bq_client)
        print(message)
        
    # Run the process
    start_the_process(bq_client, drive_service, q_select_active_interval)
    
    return 'Main Automation Done!'

def main():
    query_bigquery_and_process(update_status_2)

if __name__ == "__main__":
    main()
