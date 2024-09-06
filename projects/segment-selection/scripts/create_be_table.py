# This code creates an empty table to be populated later on with the back end report from the adops team.

from google.cloud import bigquery
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from variables import *
from input import *

# # Authenticate with BigQuery
# credentials = service_account.Credentials.from_service_account_file(
#     key_bq,
#     scopes=[
#         "https://www.googleapis.com/auth/cloud-platform",
#         "https://www.googleapis.com/auth/drive",
#     ],
# )

# bq_client = bigquery.Client(credentials=credentials, project=project)

# # Load credentials and create an authorized Google Drive service client
# creds = Credentials.from_authorized_user_file("token.json")
# service = build("drive", "v3", credentials=creds)


def create_BER_Table(code,bq_client):
    try:
        # Define BigQuery Table Schema
        schema = schema_back_end
        # Define Table Reference
        table_ref = bq_client.dataset(dataset_BERs).table(f"{code}")
        # Create an empty table first
        table = bigquery.Table(table_ref, schema=schema)

        # Create the table
        table = bq_client.create_table(table)
        print(f"Backend table for code {table.table_id} is created successfully.")
    except:
        print(f"Table {table.table_id} was already created!!")

def main():
    create_BER_Table(code_name)


if __name__ == "__main__":
    main()