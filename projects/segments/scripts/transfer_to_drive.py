from variables import *
import datetime
import sys
import os
from tqdm import tqdm  # Import tqdm for the progress bar

from oauth2client.service_account import ServiceAccountCredentials
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..'))
sys.path.append(project_root)

from input import *

def find_or_create_folder(drive, parent_id, folder_name):
    if True:
        # Search for the folder
        file_list = drive.ListFile({
            'q': f"'{parent_id}' in parents and trashed=false and title='{folder_name}' and mimeType='application/vnd.google-apps.folder'", 
            'supportsAllDrives': True
        }).GetList()
            
        if file_list:
            # Folder found
            return file_list[0]['id']
        else:
            # Folder not found, create it
            folder_metadata = {
                'title': folder_name,
                'parents': [{'id': parent_id}],
                'mimeType': 'application/vnd.google-apps.folder',
                'supportsAllDrives': True
            }
            folder = drive.CreateFile(folder_metadata)
            folder.Upload()
            return folder['id']

# Create a folder on drive for the campaign segments
def create_folder(drive, campaign_name, parent_link):
    # Get the id of the folder where we want to create the campaign folder
    parent_id = parent_link.split("/")[-1]

    # Get the current year and quarter
    current_date = datetime.datetime.now()
    current_year = str(current_date.year)
    current_quarter = f'Q{(current_date.month - 1) // 3 + 1}'

    # Find or create the year folder
    year_folder_id = find_or_create_folder(drive, parent_id, current_year)
    if not year_folder_id:
        print(f"Failed to create or find the year folder: {current_year}")
        return None
    
    # Find or create the quarter folder
    quarter_folder_id = find_or_create_folder(drive, year_folder_id, current_quarter)
    if not quarter_folder_id:
        print(f"Failed to create or find the quarter folder: {current_quarter}")
        return None
    
    # Find or create the campaign folder
    campaign_folder_id = find_or_create_folder(drive, quarter_folder_id, campaign_name)
    if not campaign_folder_id:
        print(f"Failed to create or find the campaign folder: {campaign_name}")
        return None
    
    print(f"Campaign folder '{campaign_name}' created with ID: {campaign_folder_id}")
    return campaign_folder_id

# Transfer the files with progress tracking
def transfer(drive, folder_id):
    """
    Transfer CSV files from local directory to a Google Drive folder.

    Args:
    - folder_link (str): Link to the Google Drive folder.
    - directory (str): Path to the local directory containing CSV files.
    """

    # Upload each CSV file in the directory to Google Drive
    uploaded_ids = {}
    for root, dirs, files in os.walk(dir_data):
        for filename in files:
            # Skip the raw files
            if "raw" in root:
                continue
            # Only upload CSV files
            if filename.endswith(".csv"):
                file_path = os.path.join(root, filename)

                # Track the number of lines in the file for progress
                with open(file_path, 'r') as f:
                    total_lines = sum(1 for _ in f)

                # Initialize tqdm progress bar
                with tqdm(total=total_lines, desc=f"Uploading {filename}", unit="line") as pbar:
                    # Create drive file object
                    file = drive.CreateFile(
                        {
                            "title": filename,
                            "parents": [{"id": folder_id}],
                            "mimeType": "text/csv",
                            "supportsAllDrives": True
                        }
                    )
                    # Set the path for the content of the file
                    with open(file_path, 'r') as f:
                        for line_number, line in enumerate(f, start=1):
                            # Check if we should update the progress
                            if line_number % 200000 == 0:
                                pbar.update(200000)
                            # Write the line to the Google Drive file object
                            file.SetContentFile(file_path)

                    # Upload the file after processing
                    file.Upload()
                    # Update for any remaining lines
                    remaining = total_lines % 200000
                    if remaining > 0:
                        pbar.update(remaining)

                # Save the id with the name in a dictionary for future use in creating big query tables
                uploaded_ids[file["id"]] = filename[:-4]
                print(f"Uploaded {filename} to Google Drive")

    print("All files uploaded successfully.")
    return uploaded_ids

def transfer_files_to_drive():
    # Connect to drive
    scope = ["https://www.googleapis.com/auth/drive"]
    gauth = GoogleAuth()
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
        key_google_sheets, scope
    )
    drive = GoogleDrive(gauth)

    # Create folder
    folder_id = create_folder(drive, campaign_name, drive_link_folder_Adops)

    if folder_id:
        # Upload segments to drive
        uploaded_ids = transfer(drive, folder_id)
        return uploaded_ids
    else:
        print("Failed to create the campaign folder.")
        return None

def main():
    transfer_files_to_drive()
    
if __name__ == "__main__":
    main()
