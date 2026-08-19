import datetime
import sys
import os
import importlib.util

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
sys.path.append(project_root)

# Load variables from this script's directory to avoid importing wrong variables.py
_spec = importlib.util.spec_from_file_location(
    "variables_local",
    os.path.join(script_dir, "variables.py"),
)
_vars = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vars)

from tqdm import tqdm
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError, ResumableUploadError

from input import *

# Resolve key path: support running from repo root or segments dir
def _resolve_key_path():
    raw = getattr(_vars, "key_google_sheets", "keys/maddictdata-google-sheets.json")
    if os.path.isabs(raw) and os.path.isfile(raw):
        return raw
    # Try relative to CWD (repo root when running: python projects/segments/main.py)
    cwd_path = os.path.abspath(os.path.join(os.getcwd(), raw))
    if os.path.isfile(cwd_path):
        return cwd_path
    # Try relative to project (segments) root
    seg_path = os.path.abspath(os.path.join(project_root, raw))
    if os.path.isfile(seg_path):
        return seg_path
    # Try relative to repo root (two levels up from script_dir)
    repo_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    repo_path = os.path.abspath(os.path.join(repo_root, raw))
    if os.path.isfile(repo_path):
        return repo_path
    return cwd_path  # fallback so error message shows intended path


def _get_drive_service():
    scope = ["https://www.googleapis.com/auth/drive"]
    key_path = _resolve_key_path()
    creds = service_account.Credentials.from_service_account_file(key_path, scopes=scope)
    return build("drive", "v3", credentials=creds)


def find_or_create_folder(service, parent_id, folder_name):
    query = (
        f"'{parent_id}' in parents and trashed=false and name='{folder_name}' "
        "and mimeType='application/vnd.google-apps.folder'"
    )
    results = (
        service.files()
        .list(q=query, spaces="drive", fields="files(id, name)", supportsAllDrives=True)
        .execute()
    )
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    metadata = {
        "name": folder_name,
        "parents": [parent_id],
        "mimeType": "application/vnd.google-apps.folder",
        "supportsAllDrives": True,
    }
    folder = (
        service.files()
        .create(body=metadata, supportsAllDrives=True, fields="id")
        .execute()
    )
    return folder["id"]


def create_folder(service, campaign_name, parent_link):
    parent_id = parent_link.rstrip("/").split("/")[-1]

    current_date = datetime.datetime.now()
    current_year = str(current_date.year)
    current_quarter = f"Q{(current_date.month - 1) // 3 + 1}"

    year_folder_id = find_or_create_folder(service, parent_id, current_year)
    if not year_folder_id:
        print(f"Failed to create or find the year folder: {current_year}")
        return None

    quarter_folder_id = find_or_create_folder(service, year_folder_id, current_quarter)
    if not quarter_folder_id:
        print(f"Failed to create or find the quarter folder: {current_quarter}")
        return None

    campaign_folder_id = find_or_create_folder(service, quarter_folder_id, campaign_name)
    if not campaign_folder_id:
        print(f"Failed to create or find the campaign folder: {campaign_name}")
        return None

    print(f"Campaign folder '{campaign_name}' created with ID: {campaign_folder_id}")
    return campaign_folder_id


# Chunk size for resumable uploads (multiple of 256 KB; 8 MB is a good balance)
RESUMABLE_CHUNK_SIZE = 8 * 1024 * 1024
RESUMABLE_THRESHOLD = 5 * 1024 * 1024  # Use resumable for files > 5 MB


def transfer(service, folder_id):
    uploaded_ids = {}
    dir_data = os.path.abspath(
        os.path.join(os.getcwd(), _vars.dir_data)
    )
    if not os.path.isdir(dir_data):
        dir_data = os.path.abspath(os.path.join(project_root, _vars.dir_data))

    for root, dirs, files in os.walk(dir_data):
        if "raw" in root:
            continue
        for filename in files:
            if not filename.endswith(".csv"):
                continue
            file_path = os.path.join(root, filename)
            if not os.path.isfile(file_path):
                continue

            file_size = os.path.getsize(file_path)
            use_resumable = file_size > RESUMABLE_THRESHOLD

            metadata = {
                "name": filename,
                "parents": [folder_id],
                "mimeType": "text/csv",
            }

            try:
                if use_resumable:
                    media = MediaFileUpload(
                        file_path,
                        mimetype="text/csv",
                        resumable=True,
                        chunksize=RESUMABLE_CHUNK_SIZE,
                    )
                    with tqdm(
                        total=file_size,
                        desc=f"Uploading {filename}",
                        unit="B",
                        unit_scale=True,
                        unit_divisor=1024,
                    ) as pbar:
                        request = service.files().create(
                            body=metadata,
                            media_body=media,
                            supportsAllDrives=True,
                            fields="id",
                        )
                        response = None
                        while response is None:
                            status, response = request.next_chunk()
                            if status:
                                progress = status.progress()
                                pbar.update(int(progress * file_size) - pbar.n)
                        pbar.update(file_size - pbar.n)
                    file_id = response.get("id") if response else None
                else:
                    media = MediaFileUpload(file_path, mimetype="text/csv")
                    with tqdm(total=1, desc=f"Uploading {filename}", unit="file") as pbar:
                        file = (
                            service.files()
                            .create(
                                body=metadata,
                                media_body=media,
                                supportsAllDrives=True,
                                fields="id",
                            )
                            .execute()
                        )
                        pbar.update(1)
                    file_id = file.get("id")

                if file_id:
                    uploaded_ids[file_id] = filename[:-4]
                print(f"Uploaded {filename} to Google Drive")

            except (ResumableUploadError, HttpError) as e:
                err_resp = getattr(e, "resp", None)
                status = getattr(err_resp, "status", None) if err_resp else None
                details = str(e).lower()
                if status == 403 and "storagequotaexceeded" in details:
                    print(
                        "\n⚠️  Drive storage quota exceeded. Free up space in Google Drive and re-run.\n"
                        "    Returning the files that were uploaded so far; you can re-run to push those to BigQuery."
                    )
                    if uploaded_ids:
                        print(f"    Uploaded {len(uploaded_ids)} file(s) before quota error.")
                    return uploaded_ids
                raise

    print("All files uploaded successfully.")
    return uploaded_ids


def transfer_files_to_drive():
    service = _get_drive_service()
    folder_id = create_folder(service, campaign_name, _vars.drive_link_folder_Adops)

    if folder_id:
        uploaded_ids = transfer(service, folder_id)
        return uploaded_ids
    else:
        print("Failed to create the campaign folder.")
        return None


def main():
    transfer_files_to_drive()


if __name__ == "__main__":
    main()
