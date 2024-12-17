from google.oauth2 import service_account
from google.cloud import secretmanager
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from google.cloud import bigquery
import json
from variables import *


# Authenticate with BigQuery
def authenticate_with_bigquery(secret_data_bq_info):
    credentials = service_account.Credentials.from_service_account_info(
        secret_data_bq_info,
        scopes=[
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return bigquery.Client(credentials=credentials, project=project)


# Create Google Drive Service
def create_drive_service(secret_data_token_info):
    creds = Credentials.from_authorized_user_info(secret_data_token_info)
    return build("drive", "v3", credentials=creds)


# Fetch secrets from Secret Manager
def get_secret(secret_client, secret_name):
    response = secret_client.access_secret_version(request={"name": secret_name})
    secret_data = response.payload.data.decode("UTF-8")
    return json.loads(secret_data)


# Check Google Drive storage status
def check_drive_storage(drive_service):
    try:
        about = drive_service.about().get(fields="storageQuota").execute()
        used_storage = int(about['storageQuota']['usage'])
        total_storage = int(about['storageQuota']['limit'])
        print(f"Storage Used: {used_storage / (1024**3):.2f} GB")
        print(f"Storage Limit: {total_storage / (1024**3):.2f} GB")
        if used_storage >= total_storage:
            print("Drive storage quota exceeded!")
            return False
        return True
    except HttpError as error:
        print(f"An error occurred: {error}")
        return False


# Main authentication and client creation
def authenticate_get_clients():
    secret_client = secretmanager.SecretManagerServiceClient()

    # Get secrets
    secret_data_token_info = get_secret(secret_client, secret_ber)
    secret_data_bq_info = get_secret(secret_client, secret_bq)

    # Authenticate BigQuery and Drive
    bq_client = authenticate_with_bigquery(secret_data_bq_info)
    drive_service = create_drive_service(secret_data_token_info)

    # Check Google Drive quota
    if not check_drive_storage(drive_service):
        print("Cannot proceed with Drive operations. Free up space and retry.")
        return None, None

    return bq_client, drive_service


# Example usage
if __name__ == "__main__":
    bq_client, drive_service = authenticate_get_clients()
    if bq_client and drive_service:
        print("Clients authenticated successfully.")
    else:
        print("Authentication failed due to storage quota issues.")
