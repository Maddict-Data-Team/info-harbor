#!/usr/bin/env python3
"""
Check CSV column headers (order + case sensitive) for selected Google Drive files
WITHOUT downloading full files (uses HTTP Range to read only first bytes).

Usage:
  python check_drive_csv_headers.py <file_id_or_link> <file_id_or_link> ...
  python check_drive_csv_headers.py <folder_id_or_link>

Example:
  python check_drive_csv_headers.py 1fAHtDOYsdrOfLsHKMLW3U14IGAKpbhHI
  python check_drive_csv_headers.py "https://drive.google.com/file/d/1fAHtDOYsdrOfLsHKMLW3U14IGAKpbhHI/view?usp=drive_link"
  python check_drive_csv_headers.py "https://drive.google.com/drive/folders/1fAHtDOYsdrOfLsHKMLW3U14IGAKpbhHI"
"""

from __future__ import annotations

import csv
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build


# ===================== 1) EXPECTED SCHEMA (STRICT order + case) =====================
# Keep types here if you want, but we only validate column names + order for CSV
schema_back_end = [
    ("campaign", "STRING"),
    ("LINE", "STRING"),
    ("TIMESTAMP", "TIMESTAMP"),
    ("req_id", "STRING"),
    ("udid_idfa", "STRING"),
    ("devraw", "STRING"),
    ("country", "STRING"),
    ("city", "STRING"),
    ("latitude", "FLOAT64"),
    ("longitude", "FLOAT64"),
    ("dev_os", "STRING"),
    ("dev_language", "STRING"),
    ("dev_make", "STRING"),
    ("dev_type", "STRING"),
    ("connection_type", "STRING"),
    ("carrier", "STRING"),
    ("exchange", "STRING"),
    ("dev_ip", "STRING"),
    ("zip", "STRING"),
    ("creative", "STRING"),
    ("ad_size", "STRING"),
    ("App_ID", "INT64"),
    ("environment", "STRING"),
    ("publisher", "STRING"),
    ("App_Name", "STRING"),
    ("impressions", "INT64"),
    ("clicks", "INT64"),
]
EXPECTED_COLS = [c for c, _t in schema_back_end]


# ===================== 2) GOOGLE DRIVE AUTH =====================
# Service Account JSON file path.
# IMPORTANT: Share the target files with the Service Account email.
SERVICE_ACCOUNT_JSON = "keys/maddictdata-google-sheets.json"


def build_drive_service():
    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_JSON,
        scopes=scopes,
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


# ===================== 3) HELPERS =====================
def extract_file_id(s: str) -> str:
    """
    Accepts either a raw file ID or a Google Drive link and extracts the file ID.
    Supports common formats:
      - https://drive.google.com/file/d/<ID>/view
      - https://drive.google.com/open?id=<ID>
      - https://drive.google.com/uc?id=<ID>&export=download
    """
    s = s.strip()

    # If it already looks like an ID (Drive IDs are often 25+ chars of [-_A-Za-z0-9])
    if re.fullmatch(r"[-\w]{20,}", s):
        return s

    patterns = [
        r"/file/d/([-\w]{20,})",
        r"[?&]id=([-\w]{20,})",
        r"/d/([-\w]{20,})",
    ]
    for p in patterns:
        m = re.search(p, s)
        if m:
            return m.group(1)

    raise ValueError(f"Could not extract file id from input: {s}")


def extract_folder_id(s: str) -> str:
    """
    Accepts either a raw folder ID or a Google Drive folder link and extracts the folder ID.
    Supports common formats:
      - https://drive.google.com/drive/folders/<ID>
      - https://drive.google.com/drive/u/0/folders/<ID>
    """
    s = s.strip()

    # If it already looks like an ID
    if re.fullmatch(r"[-\w]{20,}", s):
        return s

    patterns = [
        r"/folders/([-\w]{20,})",
        r"[?&]id=([-\w]{20,})",
    ]
    for p in patterns:
        m = re.search(p, s)
        if m:
            return m.group(1)

    raise ValueError(f"Could not extract folder id from input: {s}")


def is_folder_link(s: str) -> bool:
    """Check if the input string is a folder link."""
    s = s.strip().lower()
    return "folders" in s or "/drive/folders" in s


def get_files_from_folder(drive, folder_id: str) -> List[str]:
    """
    Get all file IDs from a Google Drive folder.
    Returns a list of file IDs (not folders).
    """
    file_ids = []
    page_token = None
    
    while True:
        try:
            query = f"'{folder_id}' in parents and trashed=false and mimeType!='application/vnd.google-apps.folder'"
            results = (
                drive.files()
                .list(
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    pageToken=page_token,
                )
                .execute()
            )
            
            items = results.get("files", [])
            for item in items:
                file_ids.append(item["id"])
            
            page_token = results.get("nextPageToken")
            if not page_token:
                break
                
        except Exception as e:
            raise RuntimeError(f"Error listing files in folder {folder_id}: {e}")
    
    return file_ids


def get_access_token(drive) -> str:
    """
    Get OAuth access token from the built service credentials.
    """
    token = getattr(drive._http.credentials, "token", None)
    if token:
        return token

    # Force-refresh if token not present yet
    from google.auth.transport.requests import Request as GoogleAuthRequest

    drive._http.credentials.refresh(GoogleAuthRequest())
    token = drive._http.credentials.token
    if not token:
        raise RuntimeError("Could not obtain access token from credentials.")
    return token


def get_csv_header_via_range(
    file_id: str, access_token: str, max_bytes: int = 65536
) -> List[str]:
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


def compare_columns(actual: List[str], expected: List[str]) -> Dict[str, Any]:
    missing = [c for c in expected if c not in actual]
    extra = [c for c in actual if c not in expected]
    order_ok = actual == expected

    mismatch_at: Optional[Tuple[int, Optional[str], Optional[str]]] = None
    if not order_ok:
        min_len = min(len(actual), len(expected))
        for i in range(min_len):
            if actual[i] != expected[i]:
                mismatch_at = (i, expected[i], actual[i])
                break
        if mismatch_at is None and len(actual) != len(expected):
            mismatch_at = (
                min_len,
                expected[min_len] if len(expected) > min_len else None,
                actual[min_len] if len(actual) > min_len else None,
            )

    return {
        "order_ok": order_ok,
        "missing": missing,
        "extra": extra,
        "mismatch_at": mismatch_at,  # (index, expected_col, actual_col)
        "actual_len": len(actual),
        "expected_len": len(expected),
    }


# ===================== 4) MAIN =====================
def main():
    if len(sys.argv) < 2:
        raise SystemExit(
            "Provide at least 1 file ID, folder ID, or Drive link.\n"
            "Example:\n"
            "  python check_drive_csv_headers.py 1fAHtDOYsdrOfLsHKMLW3U14IGAKpbhHI\n"
            "  python check_drive_csv_headers.py https://drive.google.com/drive/folders/1fAHtDOYsdrOfLsHKMLW3U14IGAKpbhHI\n"
        )

    inputs = sys.argv[1:]
    drive = build_drive_service()
    token = get_access_token(drive)

    # Collect all file IDs (from direct files and from folders)
    file_ids = []
    
    for inp in inputs:
        if is_folder_link(inp):
            folder_id = extract_folder_id(inp)
            print(f"📁 Processing folder: {folder_id}")
            folder_files = get_files_from_folder(drive, folder_id)
            print(f"   Found {len(folder_files)} file(s) in folder\n")
            file_ids.extend(folder_files)
        else:
            # Try to extract as file ID
            try:
                file_id = extract_file_id(inp)
                file_ids.append(file_id)
            except ValueError:
                # If it fails, try as folder ID
                try:
                    folder_id = extract_folder_id(inp)
                    print(f"📁 Processing folder: {folder_id}")
                    folder_files = get_files_from_folder(drive, folder_id)
                    print(f"   Found {len(folder_files)} file(s) in folder\n")
                    file_ids.extend(folder_files)
                except ValueError:
                    raise ValueError(f"Could not extract file or folder ID from: {inp}")

    rows: List[Dict[str, Any]] = []

    if not file_ids:
        print("⚠️ No files found to process.")
        return

    print(f"Scanning {len(file_ids)} selected file(s)...\n")

    for fid in file_ids:
        try:
            meta = (
                drive.files()
                .get(fileId=fid, fields="id,name,size,mimeType", supportsAllDrives=True)
                .execute()
            )

            name = meta.get("name", "")
            mime = meta.get("mimeType", "")

            if mime != "text/csv":
                rows.append(
                    {
                        "file": name,
                        "file_id": fid,
                        "status": "SKIP_NOT_CSV",
                        "expected_cols": len(EXPECTED_COLS),
                        "actual_cols": None,
                        "first_mismatch_index": None,
                        "expected_at_mismatch": None,
                        "actual_at_mismatch": None,
                        "missing": "",
                        "extra": "",
                        "mimeType": mime,
                    }
                )
                print(f"⚠️ SKIP")
                print(f"file: {name}")
                print(f"file_id: {fid}")
                print(f"reason: Not a CSV file ({mime})\n")
                continue

            header_cols = get_csv_header_via_range(fid, token)
            res = compare_columns(header_cols, EXPECTED_COLS)

            is_ok = res["order_ok"] and not res["missing"] and not res["extra"]
            status = "OK" if is_ok else "MISMATCH"

            mismatch_index = res["mismatch_at"][0] if res["mismatch_at"] else None
            exp_m = res["mismatch_at"][1] if res["mismatch_at"] else None
            act_m = res["mismatch_at"][2] if res["mismatch_at"] else None

            rows.append(
                {
                    "file": name,
                    "file_id": fid,
                    "status": status,
                    "expected_cols": res["expected_len"],
                    "actual_cols": res["actual_len"],
                    "first_mismatch_index": mismatch_index,
                    "expected_at_mismatch": exp_m,
                    "actual_at_mismatch": act_m,
                    "missing": ",".join(res["missing"]),
                    "extra": ",".join(res["extra"]),
                    "mimeType": mime,
                }
            )

            if is_ok:
                print(f"✅ OK")
                print(f"file: {name}:{res['actual_len']}")
                print(f"file_id: {fid}\n")
            else:
                print(f"❌ MISMATCH")
                print(f"file: {name}:{res['actual_len']}")
                print(f"file_id: {fid}")
                if res["mismatch_at"]:
                    i, exp, act = res["mismatch_at"]
                    print(f"first_mismatch_index: {i}")
                    print(f"expected_at_mismatch: {exp!r}")
                    print(f"actual_at_mismatch: {act!r}")
                if res["missing"]:
                    missing_str = ", ".join(res["missing"])
                    print(f"missing: {missing_str}")
                if res["extra"]:
                    extra_str = ", ".join(res["extra"])
                    print(f"extra: {extra_str}")
                print()

        except Exception as e:
            rows.append(
                {
                    "file": "",
                    "file_id": fid,
                    "status": "ERROR",
                    "expected_cols": len(EXPECTED_COLS),
                    "actual_cols": None,
                    "first_mismatch_index": None,
                    "expected_at_mismatch": None,
                    "actual_at_mismatch": None,
                    "missing": "",
                    "extra": "",
                    "mimeType": "",
                    "error": str(e),
                }
            )
            print(f"⚠️ ERROR")
            print(f"file_id: {fid}")
            print(f"error: {str(e)}\n")

    df = pd.DataFrame(rows)
    # Sort: errors first, then mismatches, then ok
    order = {"ERROR": 0, "MISMATCH": 1, "SKIP_NOT_CSV": 2, "OK": 3}
    df["status_rank"] = df["status"].map(order).fillna(99).astype(int)
    df = df.sort_values(["status_rank", "file", "file_id"]).drop(
        columns=["status_rank"]
    )

    print("\n" + "=" * 80)
    print("RUN REPORT".center(80))
    print("=" * 80 + "\n")
    
    # Print each row in key-value format
    for idx, row in df.iterrows():
        if row["file"]:
            print(f"file: {row['file']}:{row['actual_cols'] if pd.notna(row['actual_cols']) else 'N/A'}")
        print(f"file_id: {row['file_id']}")
        print(f"status: {row['status']}")
        if pd.notna(row['expected_cols']):
            print(f"expected_cols: {int(row['expected_cols'])}")
        if pd.notna(row['actual_cols']):
            print(f"actual_cols: {int(row['actual_cols'])}")
        if pd.notna(row['first_mismatch_index']):
            print(f"first_mismatch_index: {int(row['first_mismatch_index'])}")
        if pd.notna(row['expected_at_mismatch']) and row['expected_at_mismatch']:
            print(f"expected_at_mismatch: {row['expected_at_mismatch']}")
        if pd.notna(row['actual_at_mismatch']) and row['actual_at_mismatch']:
            print(f"actual_at_mismatch: {row['actual_at_mismatch']}")
        if row['missing']:
            print(f"missing: {row['missing']}")
        if row['extra']:
            print(f"extra: {row['extra']}")
        if row['mimeType']:
            print(f"mimeType: {row['mimeType']}")
        if 'error' in row and pd.notna(row.get('error')) and row['error']:
            print(f"error: {row['error']}")
        print()
    
    # Summary statistics
    print("-" * 80)
    print("SUMMARY".center(80))
    print("-" * 80)
    status_counts = df["status"].value_counts()
    for status, count in status_counts.items():
        print(f"  {status:15s}: {count}")
    print("-" * 80)
    
    df.to_csv("run_report.csv", index=False)
    print(f"\n📄 Detailed report saved to: run_report.csv\n")


if __name__ == "__main__":
    main()
