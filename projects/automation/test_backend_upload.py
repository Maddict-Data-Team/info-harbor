"""
Test script for backend report upload functionality.
Allows testing upload_backend without running the full automation pipeline.
"""

from google.cloud import bigquery
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google.cloud import secretmanager
import json

import upload_backend
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


def delete_ber_table(bq_client, code_name):
    """
    Delete the main BER table for a given code_name.
    Useful for testing - allows you to start fresh.
    """
    table_ref = bq_client.dataset(dataset_BERs).table(str(code_name))
    try:
        bq_client.delete_table(table_ref, not_found_ok=True)
        print(f"✅ Deleted table: {project}.{dataset_BERs}.{code_name}")
        return True
    except Exception as e:
        print(f"❌ Error deleting table: {e}")
        return False


def recreate_ber_table(bq_client, code_name):
    """
    Recreate the main BER table with the correct schema.
    """
    try:
        table_ref = bq_client.dataset(dataset_BERs).table(str(code_name))
        schema = schema_back_end
        table = bigquery.Table(table_ref, schema=schema)
        bq_client.create_table(table)
        print(f"✅ Created table: {project}.{dataset_BERs}.{code_name}")
        return True
    except Exception as e:
        error_str = str(e).lower()
        if "already exists" in error_str or "duplicate" in error_str:
            print(f"⚠️ Table {code_name} already exists (this is okay)")
            return True
        print(f"❌ Error creating table: {e}")
        return False


def test_backend_upload(backend_report, code_name, delete_first=False, recreate_table=False):
    """
    Test the backend report upload process.
    
    Args:
        backend_report: The backend report number (e.g., 123)
        code_name: The campaign code name (e.g., 173)
        delete_first: If True, delete the main BER table before uploading
        recreate_table: If True, recreate the main BER table after deletion
    """
    print("=" * 80)
    print("TESTING BACKEND REPORT UPLOAD".center(80))
    print("=" * 80)
    print(f"Backend Report: {backend_report}")
    print(f"Code Name: {code_name}")
    print(f"Delete First: {delete_first}")
    print(f"Recreate Table: {recreate_table}")
    print("=" * 80 + "\n")
    
    # Authenticate
    print("🔐 Authenticating...")
    secret_client = secretmanager.SecretManagerServiceClient()
    secret_data_token_info = get_secret(secret_client, secret_ber)
    secret_data_bq_info = get_secret(secret_client, secret_bq)
    
    bq_client = authenticate_with_bigquery(secret_data_bq_info)
    drive_service = create_drive_service(secret_data_token_info)
    print("✅ Authentication successful\n")
    
    # Delete table if requested
    if delete_first:
        print(f"🗑️  Deleting existing table {code_name}...")
        delete_ber_table(bq_client, code_name)
        print()
    
    # Recreate table if requested
    if recreate_table or delete_first:
        print(f"📋 Creating table {code_name}...")
        recreate_ber_table(bq_client, code_name)
        print()
    
    # Run the backend processing
    print("🚀 Starting backend report upload...")
    print("-" * 80)
    try:
        result = upload_backend.backend_processing(
            drive_service, bq_client, backend_report, code_name
        )
        print("-" * 80)
        if result:
            print(f"\n✅ Backend report upload completed successfully!")
        else:
            print(f"\n⚠️ Backend report upload completed but no files were found")
    except Exception as e:
        print("-" * 80)
        print(f"\n❌ Error during backend report upload: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED".center(80))
    print("=" * 80)
    return True


def main():
    """
    Main function - modify these parameters to test different scenarios
    """
    # ===== CONFIGURE THESE PARAMETERS =====
    BACKEND_REPORT = 123  # Change this to your backend report number
    CODE_NAME = 173       # Change this to your code name
    DELETE_FIRST = True   # Set to True to delete the table before uploading
    RECREATE_TABLE = True # Set to True to recreate the table after deletion
    # =======================================
    
    test_backend_upload(
        backend_report=BACKEND_REPORT,
        code_name=CODE_NAME,
        delete_first=DELETE_FIRST,
        recreate_table=RECREATE_TABLE
    )


if __name__ == "__main__":
    main()

