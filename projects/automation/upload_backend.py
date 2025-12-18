from google.cloud import bigquery
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
from google.cloud import secretmanager
import json
import csv
import requests
from google.api_core.exceptions import Conflict


from variables import *

# Expected columns from schema (for validation)
EXPECTED_COLS = [field.name for field in schema_back_end]


def navigate_and_search_file(
    drive_service,
    backend_reports_folder_id,
    backend_report,
    month_name=datetime.now().strftime("%B"),
):

    # Specifying the date you want to test with
    today = datetime.now()
    year = str(today.year)
    # month_name = today.strftime("%B")  # Full month name
    day = str(today.day - 1)
    month_abbr = today.strftime("%b")  # Abbreviated month name, e.g., Feb for February
    # day_folder_name = f"{day}{month_abbr}"  # Day folder name, e.g., 7Feb

    # print(f"Attempting to navigate to the 'Backend Reports' folder.")

    # Navigate to the year folder
    year_folders = list_folders_inside(drive_service, backend_reports_folder_id, year)
    if not year_folders:
        # print(f"Year folder '{year}' not found.")
        return 0, 0, 0
    year_folder_id = year_folders[0]["id"]
    # print(f"Year folder '{year}' found.")

    # Navigate to the month folder
    # print(f"Looking for month folder '{month_name}'")
    month_folders = list_folders_inside(drive_service, year_folder_id, month_name)
    if not month_folders:
        # print(f"Month folder '{month_name}' not found.")
        return 0, 0, 0

    month_folder_id = month_folders[0]["id"]
    # print(f"Month folder '{month_name}' found.")

    # New code: Check for the "Used" folder within the month folder
    used_folder_id = None
    used_folder_name = "Used"
    used_folders = list_folders_inside(drive_service, month_folder_id, used_folder_name)
    if not used_folders:
        # print(f"'{used_folder_name}' folder not found. Creating it...")
        used_folder_id = create_folder_used(
            drive_service, month_folder_id, used_folder_name
        )
    else:
        # print(f"'{used_folder_name}' folder already exists.")
        used_folder_id = used_folders[0][
            "id"
        ]  # Assuming list_folders_inside returns a similar structure

    matching_files = search_files_in_folder(
        drive_service, month_folder_id, backend_report
    )
    if not matching_files:
        # print(f"No files starting with '{backend_report}' found in folder '{month_name}'.")
        return 0, 0, 0
    else:
        # print(f"Files starting with '{backend_report}' found in folder '{month_name}':")

        used_folder_id_list = []
        moved_file_ids = []  # List to store IDs of files successfully moved
        for file in matching_files:
            moved_file_ids.append(file["id"])
            used_folder_id_list.append(used_folder_id)

            # Update with the ID of the last file successfully moved
            # return file["id"]

        return moved_file_ids, matching_files, used_folder_id_list


def list_folders_inside(service, parent_folder_id, folder_name):
    """
    List all folders inside the specified parent folder that match folder_name.
    """
    query = f"'{parent_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and name = '{folder_name}'"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    return results.get("files", [])


def search_files_in_folder(service, folder_id, file_prefix):
    """
    Search for files within a folder that start with a specific prefix.
    """
    query = f"'{folder_id}' in parents and name contains '{file_prefix}' and mimeType != 'application/vnd.google-apps.folder'"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    return results.get("files", [])


def move_file_to_folder(service, file_id, new_parent_id):

    # First, retrieve the existing parents to remove
    file = service.files().get(fileId=file_id, fields="parents").execute()
    previous_parents = ",".join(file.get("parents"))
    # Move the file to the new folder
    service.files().update(
        fileId=file_id,
        addParents=new_parent_id,
        removeParents=previous_parents,
        fields="id, parents",
    ).execute()


def create_folder_used(service, parent_folder_id, folder_name):

    # Implementation depends on the specific API you're using, e.g., Google Drive API v3
    # This would typically involve creating a folder resource and setting its 'parents' attribute to parent_folder_id
    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_folder_id],
    }
    file = service.files().create(body=file_metadata, fields="id").execute()
    print(f"Folder '{folder_name}' created with ID: {file['id']}")


# ===================== VALIDATION FUNCTIONS =====================

def get_access_token(drive_service) -> str:
    """
    Get OAuth access token from the built service credentials.
    """
    token = getattr(drive_service._http.credentials, "token", None)
    if token:
        return token

    # Force-refresh if token not present yet
    from google.auth.transport.requests import Request as GoogleAuthRequest

    drive_service._http.credentials.refresh(GoogleAuthRequest())
    token = drive_service._http.credentials.token
    if not token:
        raise RuntimeError("Could not obtain access token from credentials.")
    return token


def get_csv_header_via_range(
    file_id: str, access_token: str, max_bytes: int = 65536
) -> list:
    """
    Downloads only the first max_bytes of the file to parse the header row.
    Assumes header row fits within first max_bytes (usually true).
    """
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Range": f"bytes=0-{max_bytes-1}",
    }
    r = requests.get(url, headers=headers, timeout=60)
    r.raise_for_status()

    text = r.content.decode("utf-8", errors="replace")
    first_line = text.splitlines()[0]  # header row
    return next(csv.reader([first_line]))


def compare_columns(actual: list, expected: list) -> dict:
    """
    Compare actual CSV columns with expected schema columns.
    Returns dict with missing, extra columns, and validation status.
    """
    missing = [c for c in expected if c not in actual]
    extra = [c for c in actual if c not in expected]
    all_present = len(missing) == 0
    
    return {
        "all_present": all_present,
        "missing": missing,
        "extra": extra,
        "actual_cols": actual,
        "expected_cols": expected,
    }


def validate_csv_columns(drive_service, file_id: str) -> dict:
    """
    Validate CSV file columns against expected schema.
    Returns validation result dict.
    """
    try:
        access_token = get_access_token(drive_service)
        actual_cols = get_csv_header_via_range(file_id, access_token)
        validation_result = compare_columns(actual_cols, EXPECTED_COLS)
        return validation_result
    except Exception as e:
        return {
            "all_present": False,
            "missing": [],
            "extra": [],
            "actual_cols": [],
            "expected_cols": EXPECTED_COLS,
            "error": str(e),
        }


def insert_new_BER(id, backend_report, bq_client, code_name, drive_service=None):
    """
    Insert new Backend Report from Google Drive CSV.
    Validates CSV columns and handles mismatches by selecting only schema columns.
    Always uses autodetect for external tables to avoid schema conflicts.
    """
    # Validate CSV columns if drive_service is provided
    validation_result = None
    use_column_filtering = False  # Flag to determine if we need to filter columns
    
    if drive_service:
        print(f"🔍 Validating CSV columns for file ID: {id}")
        validation_result = validate_csv_columns(drive_service, id)
        
        if "error" in validation_result:
            print(f"⚠️ Warning: Could not validate CSV columns: {validation_result['error']}")
            print("   Will use autodetect and filter columns during insert to ensure compatibility")
            use_column_filtering = True  # Be safe, filter columns if validation failed
        elif not validation_result.get("all_present", True):
            use_column_filtering = True  # Need to filter if there are mismatches
            if validation_result.get("missing"):
                missing_str = ", ".join(validation_result["missing"])
                print(f"⚠️ Warning: Missing columns in CSV: {missing_str}")
                print("   Missing columns will be set to NULL in BigQuery")
            if validation_result.get("extra"):
                extra_str = ", ".join(validation_result["extra"])
                print(f"⚠️ Warning: Extra columns in CSV: {extra_str}")
                print("   Extra columns will be dropped during insertion")
        else:
            print("✅ CSV columns match expected schema")
    
    # Construct the new link
    new_link = f"https://drive.google.com/open?id={id}"
    # Define Google Sheets URL
    spreadsheet_url = new_link
    # Define BigQuery External Table Configuration
    external_config = bigquery.ExternalConfig("CSV")
    external_config.source_uris = [spreadsheet_url]
    external_config.autodetect = True
    
    # Define Table Reference
    table_ref = bq_client.dataset(dataset_BERs).table(f"{backend_report}_new")
    
    # ALWAYS use autodetect without fixed schema to avoid conflicts
    # This allows the external table to include all CSV columns, then we filter during insert
    table = bigquery.Table(table_ref)
    table.external_data_configuration = external_config
    print("📋 Creating external table with autodetect (will include all CSV columns)")

    try:
        # Delete existing table if it exists to ensure fresh state
        bq_client.delete_table(table_ref, not_found_ok=True)
        # Attempt to create the table
        table = bq_client.create_table(table)
        print(f"✅ External table {table.table_id} created successfully.")
    except Conflict:
        # If the table already exists, delete and recreate to ensure fresh state
        print(f"Table {backend_report}_new already exists. Deleting and recreating...")
        bq_client.delete_table(table_ref, not_found_ok=True)
        table = bq_client.create_table(table)
        print(f"✅ External table {table.table_id} recreated successfully.")
    except Exception as e:
        # If creation still fails, raise error with details
        error_msg = str(e)
        print(f"❌ Error creating external table: {error_msg}")
        # Check if it's a schema-related error
        if "schema" in error_msg.lower() or "column" in error_msg.lower():
            print("   This appears to be a schema/column mismatch issue.")
            print("   The table will be created with autodetect, and columns will be filtered during insert.")
        raise RuntimeError(f"Failed to create external table: {error_msg}")

    # Always use column filtering if validation found issues or failed
    # This ensures extra columns are dropped and missing ones are handled
    if use_column_filtering or (validation_result and not validation_result.get("all_present", True)):
        # Force column filtering
        if not validation_result:
            # If validation failed, create a result that forces filtering
            validation_result = {
                "all_present": False,
                "missing": [],
                "extra": [],
                "actual_cols": [],  # Unknown, will need to query table schema
            }

    # Verify external table has data before proceeding
    try:
        check_query = f"SELECT COUNT(*) as row_count FROM `{project}.{dataset_BERs}.{backend_report}_new`"
        check_job = bq_client.query(check_query)
        check_result = check_job.result()
        row_count = next(check_result).row_count
        print(f"📊 External table has {row_count} row(s)")
        
        if row_count == 0:
            print("⚠️ Warning: External table is empty! No data to insert.")
            print("   This could mean:")
            print("   - The CSV file is empty")
            print("   - The CSV file is not accessible from BigQuery")
            print("   - The external table configuration is incorrect")
            delete_table(backend_report, bq_client)
            return
    except Exception as e:
        print(f"⚠️ Warning: Could not verify external table data: {e}")
        print("   Proceeding with insert anyway...")

    # Call the other functions to proceed with the rest of the process
    # Pass validation_result to handle column selection
    insert_to_main_BER(backend_report, bq_client, code_name, validation_result)
    delete_table(backend_report, bq_client)
    remove_dups(bq_client, code_name)



# Function to run a query
def remove_dups(bq_client, code_name):

    query_job = bq_client.query(q_deduplicate_ber(code_name))  # Start the query job
    query_job.result()  # Wait for the query to finish
    print(f"Query executed successfully", end=": ")
    print("(Removed duplication)")


def insert_to_main_BER(backend_report, bq_client, code_name, validation_result=None):
    """
    Insert data from external table to main BER table.
    If validation_result is provided and there are extra/missing columns,
    only select columns that match the schema.
    """
    # Determine if we need column filtering
    needs_filtering = (
        validation_result 
        and not validation_result.get("all_present", True)
    )
    
    # If validation found issues or we need to filter, select only expected columns
    if needs_filtering:
        # Get actual columns from validation or query the table
        actual_cols = validation_result.get("actual_cols", [])
        
        # If we don't have actual_cols (validation failed), query the table schema
        if not actual_cols:
            try:
                table_ref = bq_client.dataset(dataset_BERs).table(f"{backend_report}_new")
                table = bq_client.get_table(table_ref)
                actual_cols = [field.name for field in table.schema]
                print(f"📋 Queried table schema: found {len(actual_cols)} columns")
                print(f"   Columns in external table: {', '.join(actual_cols[:10])}{'...' if len(actual_cols) > 10 else ''}")
            except Exception as e:
                print(f"⚠️ Warning: Could not query table schema: {e}")
                print("   Will attempt to select all expected columns (missing ones will be NULL)")
                actual_cols = []  # Will treat all as missing
        
        # Build column list - select columns that exist in CSV, add NULL for missing ones
        select_cols = []
        for col in EXPECTED_COLS:
            if col in actual_cols:
                # Column exists in CSV, select it
                select_cols.append(col)
            else:
                # Column is missing in CSV, use NULL with proper type
                col_type = _get_column_type(col)
                select_cols.append(f"CAST(NULL AS {col_type}) AS {col}")
        
        select_clause = ",\n        ".join(select_cols)
        query = f"""
    Insert INTO `{project}.{dataset_BERs}.{code_name}`
    (
        Select {select_clause}
        FROM `{project}.{dataset_BERs}.{backend_report}_new`
    )
    """
        print(f"📋 Using column-filtered insert (dropping extra columns, handling missing)")
    else:
        # All columns match, use SELECT * (but only if validation passed)
        if validation_result and validation_result.get("all_present", True):
            query = f"""
    Insert INTO `{project}.{dataset_BERs}.{code_name}`
    (
        Select *
        FROM `{project}.{dataset_BERs}.{backend_report}_new`
    )
    """
        else:
            # No validation or uncertain, query table to get actual columns
            try:
                table_ref = bq_client.dataset(dataset_BERs).table(f"{backend_report}_new")
                table = bq_client.get_table(table_ref)
                actual_cols = [field.name for field in table.schema]
                print(f"📋 Queried table schema: found {len(actual_cols)} columns")
                
                # Build column list based on actual columns
                select_cols = []
                for col in EXPECTED_COLS:
                    if col in actual_cols:
                        select_cols.append(col)
                    else:
                        col_type = _get_column_type(col)
                        select_cols.append(f"CAST(NULL AS {col_type}) AS {col}")
                
                select_clause = ",\n        ".join(select_cols)
                query = f"""
    Insert INTO `{project}.{dataset_BERs}.{code_name}`
    (
        Select {select_clause}
        FROM `{project}.{dataset_BERs}.{backend_report}_new`
    )
    """
                print(f"📋 Using column-filtered insert (safe mode - queried schema)")
            except Exception as e:
                print(f"⚠️ Warning: Could not query table schema: {e}")
                print("   Using SELECT * (may fail if columns don't match)")
                query = f"""
    Insert INTO `{project}.{dataset_BERs}.{code_name}`
    (
        Select *
        FROM `{project}.{dataset_BERs}.{backend_report}_new`
    )
    """

    # Execute the query
    try:
        # First, check how many rows will be inserted
        count_query = f"SELECT COUNT(*) as row_count FROM `{project}.{dataset_BERs}.{backend_report}_new`"
        count_job = bq_client.query(count_query)
        count_result = count_job.result()
        source_row_count = next(count_result).row_count
        print(f"📊 Source table has {source_row_count} row(s) to insert")
        
        if source_row_count == 0:
            print("⚠️ Warning: No rows to insert - source table is empty")
            return
        
        query_job = bq_client.query(query)
        query_job.result()  # Wait for the query to complete
        
        # Verify rows were actually inserted
        verify_query = f"SELECT COUNT(*) as row_count FROM `{project}.{dataset_BERs}.{code_name}`"
        verify_job = bq_client.query(verify_query)
        verify_result = verify_job.result()
        final_row_count = next(verify_result).row_count
        print(f"✅ Data inserted successfully into {code_name}")
        print(f"📊 Total rows in {code_name} table: {final_row_count}")
    except Exception as e:
        error_msg = str(e)
        # If error is about missing columns, query table schema and retry
        if "Unrecognized name" in error_msg or "column" in error_msg.lower() or "not found" in error_msg.lower():
            print(f"⚠️ Warning: Column error during insert: {error_msg}")
            print("   Retrying by querying table schema and selecting only existing columns...")
            try:
                # Query the actual table schema
                table_ref = bq_client.dataset(dataset_BERs).table(f"{backend_report}_new")
                table = bq_client.get_table(table_ref)
                actual_cols = [field.name for field in table.schema]
                
                # Build column list - only select columns that actually exist
                select_cols = []
                for col in EXPECTED_COLS:
                    if col in actual_cols:
                        select_cols.append(col)
                    else:
                        col_type = _get_column_type(col)
                        select_cols.append(f"CAST(NULL AS {col_type}) AS {col}")
                
                select_clause = ",\n        ".join(select_cols)
                query = f"""
    Insert INTO `{project}.{dataset_BERs}.{code_name}`
    (
        Select {select_clause}
        FROM `{project}.{dataset_BERs}.{backend_report}_new`
    )
    """
                query_job = bq_client.query(query)
                query_job.result()
                print(f"✅ Data inserted successfully with error recovery")
            except Exception as e2:
                print(f"❌ Error recovery failed: {e2}")
                raise RuntimeError(f"Failed to insert data even after error recovery: {e2}")
        else:
            raise


def _get_column_type(column_name: str) -> str:
    """
    Get BigQuery type for a column from schema.
    """
    for field in schema_back_end:
        if field.name == column_name:
            return field.field_type
    return "STRING"  # Default fallback


def delete_table(backend_report, bq_client):
    # Specify the dataset and table to delete
    table_ref = bq_client.dataset(dataset_BERs).table(f"{backend_report}_new")

    # Delete the table
    bq_client.delete_table(table_ref, not_found_ok=True)


# code_name
def backend_processing(drive_service, bq_client, backend_report, code_name):

    get_file_id, matching_files, used_folder_id_list = navigate_and_search_file(
        drive_service, folder_id_Backend_Reports, backend_report
    )
    # print(get_file_id)

    today = datetime.now()

    if 1 <= today.day <= 7:
        print("Running extended month...")
        # Get the last day of the previous month by subtracting current day from today
        last_month_date = today - timedelta(days=today.day)
        last_month = last_month_date.strftime("%B")
        (
            get_file_id_last_month,
            matching_files_last_month,
            used_folder_id_list_last_month,
        ) = navigate_and_search_file(
            drive_service, folder_id_Backend_Reports, backend_report, last_month
        )

        if get_file_id == 0:
            if get_file_id_last_month == 0:
                pass
            else:
                get_file_id = get_file_id_last_month
                matching_files = matching_files_last_month
                used_folder_id_list = used_folder_id_list_last_month

        elif get_file_id_last_month != 0:
            print('reached')
            get_file_id.extend(get_file_id_last_month)
            matching_files.extend(matching_files_last_month)
            used_folder_id_list.extend(used_folder_id_list_last_month)

    if get_file_id:
        print(f"Moved files: {get_file_id}")
    else:
        print("No files were moved to 'Used' folder")

    if get_file_id == 0:
        # today = datetime.now()
        print(f"No Backend reports for {backend_report} were found this week")
        return False
    else:
        print(f"New backend reports are being moved to {backend_report} in BigQuery")
        for i in range(0, len(get_file_id)):
            curr_id = get_file_id[i]
            curr_drive_file = matching_files[i]
            used_folder_id = used_folder_id_list[i]
            print(f"Inserting: {backend_report} into {code_name} BER table")
            # Pass drive_service for validation
            insert_new_BER(curr_id, backend_report, bq_client, code_name, drive_service)
            print(f"Moving file: {curr_drive_file['name']} to 'Used' folder")
            move_file_to_folder(drive_service, curr_drive_file["id"], used_folder_id)

        print(f"Backend report uploaded successfully for {code_name}")
        return True


def main():
    """
    Main function for standalone execution.
    Note: This module is typically imported and used by main.py.
    For standalone use, you need to provide authentication and parameters.
    """
    print("⚠️ This module is designed to be imported and used by main.py")
    print("   It requires drive_service, bq_client, backend_report, and code_name")
    print("   Please use: python projects/automation/main.py")
    print("   Or import and call backend_processing() with proper arguments")


if __name__ == "__main__":
    main()
    print("\nFor proper execution, use: python projects/automation/main.py")
