import sys
import os
import subprocess
from datetime import datetime

from input import *

# Get the path to the directory containing this script (main.py)
main_dir = os.path.dirname(__file__)

# Get the 'scripts' directory path
scripts_dir = os.path.join(main_dir, "scripts")

# Add the 'scripts' directory to sys.path
sys.path.append(scripts_dir)

# Now you can import variables from scripts/variables.py if needed

from reset_folders import reset_folders
from get_segments_raw import get_raw_segments
from split_segments import split_files, move_without_splitting
from transfer_to_drive import transfer_files_to_drive
from push_to_bq import run_push_to_bq
from authenticate_to_cloud import authenticate_get_clients
from create_be_table import create_BER_Table

def print_title():
    """Print a beautiful title design for the segments processing script"""
    print("\n" + "="*80)
    print("🚀 INFO HARBOR - SEGMENTS PROCESSING PIPELINE 🚀".center(80))
    print("="*80)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Campaign: {campaign_name}")
    print(f"🔢 Code Name: {code_name}")
    print(f"🌍 Countries: {', '.join(countries)}")
    print(f"📊 Segments: {len(segments)} segments")
    print("="*80)
    print("🔄 Processing pipeline initiated...")
    print("-"*80)

def main():
    # Print the beautiful title
    print_title()
    
    bq_client, drive_service = authenticate_get_clients()
    
    # print("🗂️  Resetting folders...")
    # reset_folders()   
    
    # print("📊 Getting raw segments from BigQuery...")
    # get_raw_segments(countries, segments, bq_client)

    # Choose One
    print("✂️  Splitting segment files...")
    # move_without_splitting()
    split_files()

    print("☁️  Transferring files to Google Drive...")
    segment_dict = transfer_files_to_drive()
    
    print("📈 Pushing segments to BigQuery...")
    run_push_to_bq(segment_dict, bq_client)
    
    print("🏗️  Creating Back-End Reports table...")
    create_BER_Table(code_name,bq_client)
    
    # Print completion message
    print("\n" + "="*80)
    print("✅ SEGMENTS PROCESSING PIPELINE COMPLETED SUCCESSFULLY! ✅".center(80))
    print("="*80)
    print(f"🏁 Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎉 All segments have been processed and uploaded!")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
