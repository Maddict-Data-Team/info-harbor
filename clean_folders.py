from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time
import sys

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]

SERVICE_ACCOUNT_FILE = 'maddictdata-8a4562e58328.json'

def create_drive_service():
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        return build('drive', 'v3', credentials=credentials)
    except Exception as e:
        print(f"Error creating Drive service: {str(e)}")
        return None

def list_files(service, folder_id):
    try:
        query = f"'{folder_id}' in parents and mimeType='text/csv'"
        results = service.files().list(
            q=query,
            fields="files(id, name, permissions)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        return results.get('files', [])
    except HttpError as error:
        print(f"An error occurred while listing files: {error}")
        return []

def delete_file(service, file_id, file_name):
    try:
        service.files().delete(
            fileId=file_id,
            supportsAllDrives=True
        ).execute()
        print(f"Successfully deleted: {file_name}")
        return True
    except HttpError as error:
        print(f"Error deleting {file_name}: {error}")
        return False

def process_folder(service, folder_id):
    print(f"\nProcessing folder ID: {folder_id}")
    files = list_files(service, folder_id)

    if not files:
        print('No CSV files found in this folder.')
        return 0, 0

    print('Found the following CSV files:')
    success_count = 0
    fail_count = 0

    for file in files:
        print(f"\nProcessing file: {file['name']} (ID: {file['id']})")
        if delete_file(service, file['id'], file['name']):
            success_count += 1
        else:
            fail_count += 1
        time.sleep(1)  # Add delay to avoid rate limiting

    return success_count, fail_count

def main():
    if len(sys.argv) < 2:
        print("Usage: python test.py <folder_id1> [folder_id2] [folder_id3] ...")
        print("Example: python test.py 10nqwatGfYP2kkkDHmwR2gQHyplvPaJs8 1dOpqSggiAiUgWbWw4UibDVrO_wZEEZ0B")
        return

    service = create_drive_service()
    if not service:
        return

    total_success = 0
    total_fail = 0

    # Process each folder ID provided as argument
    for folder_id in sys.argv[1:]:
        success, fail = process_folder(service, folder_id)
        total_success += success
        total_fail += fail
        print(f"\nCompleted processing folder: {folder_id}")
        print(f"Folder summary - Successfully deleted: {success}, Failed: {fail}")
        print("-" * 50)

    print(f'\nFinal Summary:')
    print(f'Total successfully deleted: {total_success}')
    print(f'Total failed to delete: {total_fail}')

if __name__ == '__main__':
    main() 