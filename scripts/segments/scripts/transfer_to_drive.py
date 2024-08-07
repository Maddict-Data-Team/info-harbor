# this code transferes the control and served segment to drive

from variables import *
from input import *
import os

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials


# create a folder on drive for the campaign segments
def create_folder(drive, folderName, parent_link):
    # Get the id of the folder where we want to create the campaign folder
    parent_id = parent_link.split("/")[-1]

    #create the folder metadata
    folder_metadata = {
        "title": folderName,
        "parents": [{"id": parent_id}],  # parent folder
        "mimeType": "application/vnd.google-apps.folder",
    }
    # create the folder object
    folder = drive.CreateFile(folder_metadata)
    #upload the folder to drive
    folder.Upload()
    #return the folder id to be used in uploading the data
    return folder["id"]


# transfere the files
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
        # iterate over the files
        for filename in files:
            # skip the raw files
            if "raw" in root:
                continue
            # only upload csv files
            if filename.endswith(".csv"):
                file_path = os.path.join(root, filename)

                # create drive file object
                file = drive.CreateFile(
                    {
                        "title": filename,
                        "parents": [{"id": folder_id}],
                        "mimeType": "text/csv",
                    }
                )
                # set the path for the content of the file
                file.SetContentFile(file_path)
                #upload the file
                file.Upload()
                #save the id with the name in a dictionary for future use in creating big query tables
                uploaded_ids[file["id"]] = filename[:-4]
                print(f"Uploaded {filename} to Google Drive")

    print("All files uploaded successfully.")
    return uploaded_ids


def transfere_files_to_drive():
    # connect to drive
    scope = ["https://www.googleapis.com/auth/drive"]
    gauth = GoogleAuth()
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
        key_google_sheets, scope
    )
    drive = GoogleDrive(gauth)

    # create folder
    folder_id = create_folder(drive, campaign_name, drive_link_folder_Adops)

    # upload segments to drive
    uploaded_ids = transfer(drive, folder_id)
    return uploaded_ids