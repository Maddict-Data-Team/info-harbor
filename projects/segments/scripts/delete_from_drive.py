import datetime
import sys
import os
import importlib.util

script_dir = os.path.dirname(os.path.abspath(__file__))
# Load variables from same folder (scripts/) so key_google_sheets etc. are always defined
_vars_path = os.path.join(script_dir, "variables.py")
_spec = importlib.util.spec_from_file_location("variables_local", _vars_path)
_vars = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vars)
for _name in dir(_vars):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_vars, _name)

from tqdm import tqdm
from oauth2client.service_account import ServiceAccountCredentials
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

project_root = os.path.abspath(os.path.join(script_dir, ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

# ============================================================================
# CONFIGURATION - CHANGE THESE VALUES AS NEEDED
# ============================================================================

# Set the folder ID you want to delete files from
# Get this from Google Drive URL: https://drive.google.com/drive/folders/FOLDER_ID_HERE
FOLDER_ID_TO_DELETE = "1tTawCZ4ihAfDeKp1Xac9QiDIBICfmMuM"

# Set to True to delete files, False to just list them (dry run)
# Defaults to False (IH-028): running this script with no arguments must
# never permanently delete files with no confirmation. Set to True
# explicitly, deliberately, only when a delete run is actually intended.
DELETE_MODE = False

# Set to True to delete all files created by info-harbor account
# Set to False to only delete files in the specific folder
DELETE_ALL_FILES = False

# ============================================================================
# END CONFIGURATION
# ============================================================================

# Import input only if needed for other variables
try:
    from input import *
except ImportError:
    # If input.py doesn't exist, we'll use the configuration above
    pass

def authenticate_drive():
    """Authenticate with Google Drive using the info-harbor service account"""
    scope = ["https://www.googleapis.com/auth/drive"]
    gauth = GoogleAuth()
    
    # Resolve the key path relative to the project root
    script_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(script_dir, '../../..'))
    key_path = os.path.join(project_root, key_google_sheets)
    
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Google Sheets key file not found at: {key_path}")
    
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
        key_path, scope
    )
    drive = GoogleDrive(gauth)
    return drive

def list_files_by_creator(drive, folder_id=None, creator_email="info-harbor@maddictdata.iam.gserviceaccount.com"):
    """
    List files created by the specified service account
    
    Args:
        drive: GoogleDrive instance
        folder_id: Optional folder ID to search within
        creator_email: Email of the service account that created the files
    
    Returns:
        List of file objects created by the specified account
    """
    query_parts = [
        f"'{creator_email}' in owners",
        "trashed=false",
        "mimeType != 'application/vnd.google-apps.folder'"
    ]
    
    if folder_id:
        query_parts.append(f"'{folder_id}' in parents")
    
    query = " and ".join(query_parts)
    
    file_list = drive.ListFile({
        'q': query,
        'supportsAllDrives': True,
        'fields': 'items(id,title,createdDate,parents,owners)'
    }).GetList()
    
    return file_list

def delete_file(drive, file_id, file_name):
    """
    Delete a specific file from Google Drive
    
    Args:
        drive: GoogleDrive instance
        file_id: ID of the file to delete
        file_name: Name of the file for logging
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if DELETE_MODE:
            file = drive.CreateFile({'id': file_id})
            file.Delete()
            print(f"✅ Deleted: {file_name} (ID: {file_id})")
        else:
            print(f"🔍 [DRY RUN] Would delete: {file_name} (ID: {file_id})")
        return True
    except Exception as e:
        if DELETE_MODE:
            print(f"❌ Failed to delete {file_name} (ID: {file_id}): {str(e)}")
        else:
            print(f"❌ [DRY RUN] Would fail to delete {file_name} (ID: {file_id}): {str(e)}")
        return False

def delete_files_in_folder(drive, folder_id, folder_name):
    """
    Delete all files created by info-harbor account in a specific folder
    
    Args:
        drive: GoogleDrive instance
        folder_id: ID of the folder to search
        folder_name: Name of the folder for logging
    
    Returns:
        dict: Results of deletion operation
    """
    print(f"🔍 Searching for files in folder: {folder_name}")
    
    files = list_files_by_creator(drive, folder_id)
    
    if not files:
        print(f"📭 No files found in {folder_name} created by info-harbor account")
        return {'total': 0, 'deleted': 0, 'failed': 0}
    
    print(f"📁 Found {len(files)} files to delete in {folder_name}")
    
    deleted_count = 0
    failed_count = 0
    
    for file in tqdm(files, desc=f"Deleting files from {folder_name}"):
        if delete_file(drive, file['id'], file['title']):
            deleted_count += 1
        else:
            failed_count += 1
    
    return {
        'total': len(files),
        'deleted': deleted_count,
        'failed': failed_count
    }

def delete_campaign_files(drive, campaign_name):
    """
    Delete all files for a specific campaign created by info-harbor account
    
    Args:
        drive: GoogleDrive instance
        campaign_name: Name of the campaign to delete files for
    
    Returns:
        dict: Results of deletion operation
    """
    print(f"🎯 Deleting files for campaign: {campaign_name}")
    
    # Get the current year and quarter
    current_date = datetime.datetime.now()
    current_year = str(current_date.year)
    current_quarter = f'Q{(current_date.month - 1) // 3 + 1}'
    
    # Build the folder path
    parent_id = drive_link_folder_Adops.split("/")[-1]
    
    # Search for year folder
    year_query = f"'{parent_id}' in parents and title='{current_year}' and mimeType='application/vnd.google-apps.folder'"
    year_folders = drive.ListFile({'q': year_query, 'supportsAllDrives': True}).GetList()
    
    if not year_folders:
        print(f"❌ Year folder '{current_year}' not found")
        return {'total': 0, 'deleted': 0, 'failed': 0}
    
    year_folder_id = year_folders[0]['id']
    
    # Search for quarter folder
    quarter_query = f"'{year_folder_id}' in parents and title='{current_quarter}' and mimeType='application/vnd.google-apps.folder'"
    quarter_folders = drive.ListFile({'q': quarter_query, 'supportsAllDrives': True}).GetList()
    
    if not quarter_folders:
        print(f"❌ Quarter folder '{current_quarter}' not found")
        return {'total': 0, 'deleted': 0, 'failed': 0}
    
    quarter_folder_id = quarter_folders[0]['id']
    
    # Search for campaign folder
    campaign_query = f"'{quarter_folder_id}' in parents and title='{campaign_name}' and mimeType='application/vnd.google-apps.folder'"
    campaign_folders = drive.ListFile({'q': campaign_query, 'supportsAllDrives': True}).GetList()
    
    if not campaign_folders:
        print(f"❌ Campaign folder '{campaign_name}' not found")
        return {'total': 0, 'deleted': 0, 'failed': 0}
    
    campaign_folder_id = campaign_folders[0]['id']
    
    # Delete files in campaign folder
    return delete_files_in_folder(drive, campaign_folder_id, f"{current_year}/{current_quarter}/{campaign_name}")

def delete_all_info_harbor_files(drive):
    """
    Delete all files created by info-harbor account across all folders
    
    Args:
        drive: GoogleDrive instance
    
    Returns:
        dict: Results of deletion operation
    """
    print("🗑️  Deleting all files created by info-harbor account")
    
    files = list_files_by_creator(drive)
    
    if not files:
        print("📭 No files found created by info-harbor account")
        return {'total': 0, 'deleted': 0, 'failed': 0}
    
    print(f"📁 Found {len(files)} files to delete")
    
    deleted_count = 0
    failed_count = 0
    
    for file in tqdm(files, desc="Deleting all info-harbor files"):
        if delete_file(drive, file['id'], file['title']):
            deleted_count += 1
        else:
            failed_count += 1
    
    return {
        'total': len(files),
        'deleted': deleted_count,
        'failed': failed_count
    }

def delete_files_in_specific_folder(drive, folder_id, folder_name=None):
    """
    Delete all files created by info-harbor account in a specific folder by ID
    
    Args:
        drive: GoogleDrive instance
        folder_id: ID of the folder to delete files from
        folder_name: Optional name for logging (if not provided, will try to get from folder)
    
    Returns:
        dict: Results of deletion operation
    """
    if not folder_name:
        try:
            # Try to get folder name for better logging
            folder = drive.CreateFile({'id': folder_id})
            folder_name = folder['title']
        except:
            folder_name = f"Folder {folder_id}"
    
    print(f"🎯 Deleting files from specific folder: {folder_name}")
    print(f"📁 Folder ID: {folder_id}")
    
    return delete_files_in_folder(drive, folder_id, folder_name)

def main():
    """Main function to run the deletion script"""
    print("🚀 Starting Google Drive file deletion script")
    print(f"🔐 Using service account: info-harbor@maddictdata.iam.gserviceaccount.com")
    
    # Show configuration
    print(f"📁 Target folder ID: {FOLDER_ID_TO_DELETE}")
    print(f"🗑️  Delete mode: {'ENABLED' if DELETE_MODE else 'DRY RUN (files will NOT be deleted)'}")
    print(f"🌍 Scope: {'All files' if DELETE_ALL_FILES else 'Specific folder only'}")
    
    # Authenticate with Drive
    try:
        drive = authenticate_drive()
        print("✅ Successfully authenticated with Google Drive")
    except Exception as e:
        print(f"❌ Authentication failed: {str(e)}")
        return
    
    # Determine what to delete based on configuration
    if DELETE_ALL_FILES:
        print("🗑️  Deleting all files created by info-harbor account")
        results = delete_all_info_harbor_files(drive)
    else:
        print(f"🎯 Deleting files from specific folder: {FOLDER_ID_TO_DELETE}")
        results = delete_files_in_specific_folder(drive, FOLDER_ID_TO_DELETE)
    
    # Print results
    print("\n📊 Deletion Results:")
    print(f"   Total files found: {results['total']}")
    print(f"   Successfully deleted: {results['deleted']}")
    print(f"   Failed to delete: {results['failed']}")
    
    if results['failed'] > 0:
        print("⚠️  Some files failed to delete. Check permissions and try again.")
    else:
        print("✅ All files deleted successfully!")

if __name__ == "__main__":
    main() 