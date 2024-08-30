from google.cloud import bigquery
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
from google.cloud import secretmanager
import json

from variables import *


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

    print(f"Attempting to navigate to the 'Backend Reports' folder.")

    # Navigate to the year folder
    year_folders = list_folders_inside(drive_service, backend_reports_folder_id, year)
    if not year_folders:
        print(f"Year folder '{year}' not found.")
        return 0,0,0
    year_folder_id = year_folders[0]["id"]
    print(f"Year folder '{year}' found.")

    # Navigate to the month folder
    # print(f"Looking for month folder '{month_name}'")
    month_folders = list_folders_inside(drive_service, year_folder_id, month_name)
    if not month_folders:
        print(f"Month folder '{month_name}' not found.")
        return 0,0,0

    month_folder_id = month_folders[0]["id"]
    print(f"Month folder '{month_name}' found.")

    # New code: Check for the "Used" folder within the month folder
    used_folder_id = None
    used_folder_name = "Used"
    used_folders = list_folders_inside(drive_service, month_folder_id, used_folder_name)
    if not used_folders:
        print(f"'{used_folder_name}' folder not found. Creating it...")
        used_folder_id = create_folder_used(
            drive_service, month_folder_id, used_folder_name
        )
    else:
        print(f"'{used_folder_name}' folder already exists.")
        used_folder_id = used_folders[0][
            "id"
        ]  # Assuming list_folders_inside returns a similar structure

    matching_files = search_files_in_folder(
        drive_service, month_folder_id, backend_report
    )
    if not matching_files:
        print(
            f"No files starting with '{backend_report}' found in folder '{month_name}'."
        )
        return 0,0,0
    else:
        print(f"Files starting with '{backend_report}' found in folder '{month_name}':")

        moved_file_ids = []  # List to store IDs of files successfully moved
        for file in matching_files:
            moved_file_ids.append(
                file["id"]
            )  # Update with the ID of the last file successfully moved
            # return file["id"]

        return moved_file_ids,matching_files,used_folder_id



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


def insert_new_BER(id, backend_report, bq_client, code_name):

    
    # Construct the new link
    new_link = f"https://drive.google.com/open?id={id}"
    # Define Google Sheets URL
    spreadsheet_url = new_link
    # Define BigQuery External Table Configuration
    external_config = bigquery.ExternalConfig("CSV")
    external_config.source_uris = [spreadsheet_url]
    external_config.autodetect = True
    # Define BigQuery Table Schema
    schema = schema_back_end
    # Define Table Reference
    table_ref = bq_client.dataset(dataset_BERs).table(f"{backend_report}_new")
    # Create an empty table first
    table = bigquery.Table(table_ref, schema=schema)
    # Set the external data configuration
    table.external_data_configuration = external_config
    # Create the table
    table = bq_client.create_table(table)
    print(f"External table {table.table_id} created successfully.")
    insert_to_main_BER(backend_report, bq_client, code_name)
    delete_table(backend_report, bq_client)
    remove_dups(bq_client, code_name)


# Function to run a query
def remove_dups(bq_client, code_name):

    query_job = bq_client.query(q_deduplicate_ber(code_name))  # Start the query job
    query_job.result()  # Wait for the query to finish
    print(f"Query executed successfully", end=": ")
    print("(Removed duplication)")


def insert_to_main_BER(backend_report, bq_client, code_name):

    query = f"""
    Insert INTO `{project}.{dataset_BERs}.{code_name}`
    (
        Select *
        FROM {project}.{dataset_BERs}.{f"{backend_report}_new"}
    )
    """

    # Execute the query
    query_job = bq_client.query(query)
    # Wait for the query to complete
    query_job.result()


def delete_table(backend_report, bq_client):
    # Specify the dataset and table to delete
    table_ref = bq_client.dataset(dataset_BERs).table(f"{backend_report}_new")

    # Delete the table
    bq_client.delete_table(table_ref, not_found_ok=True)


# code_name
def main(drive_service, bq_client, backend_report, code_name):

    get_file_id,matching_files,used_folder_id = navigate_and_search_file(
        drive_service, folder_id_Backend_Reports, backend_report
    )
    print(get_file_id)

    today = datetime.now()

    if 1 <= today.day <= 7:
        print("Running extended month...")
        # Get the last day of the previous month by subtracting current day from today
        last_month_date = today - timedelta(days=today.day)
        last_month = last_month_date.strftime("%B")
        get_file_id_last_month,matching_files_last_month,used_folder_id = navigate_and_search_file(
            drive_service, folder_id_Backend_Reports, backend_report, last_month
        )

        if get_file_id == 0:
            if get_file_id_last_month == 0:
                pass
            else:
                get_file_id = get_file_id_last_month

        elif get_file_id_last_month != 0:

            get_file_id.extend(get_file_id_last_month)
            matching_files.extend(matching_files_last_month)

    if get_file_id:
        print(f"Moved files: {get_file_id}")
    else:
        print("No files were moved to 'Used'.")

    if get_file_id == 0:
        # today = datetime.now()
        print(f"No Backend reports found for {backend_report} this week")
    else:
        print(f"New backend reports are being moved to {backend_report} in BigQuery")
        for i in range(0,len(get_file_id)):
            curr_id = get_file_id[i]
            curr_drive_file = matching_files[i]
            print(f"Inserting: {backend_report} into {code_name} BER table")
            insert_new_BER(curr_id, backend_report, bq_client, code_name)
            print(f"Moving file: {curr_drive_file['name']} to 'Used' folder")
            move_file_to_folder(drive_service, curr_drive_file["id"], used_folder_id)

if __name__ == "__main__":
    main()
