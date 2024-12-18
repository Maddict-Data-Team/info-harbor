import sys
import os
import subprocess

from input import *

# Get the path to the directory containing this script (main.py)
main_dir = os.path.dirname(__file__)

# Get the 'scripts' directory path
scripts_dir = os.path.join(main_dir, 'scripts')

# Add the 'scripts' directory to sys.path
sys.path.append(scripts_dir)

# Now you can import variables from scripts/variables.py if needed

from reset_folders import reset_folders
from get_segments_raw import get_raw_segments
from split_segments import split_files,move_without_splitting
from transfer_to_drive import transfer_files_to_drive
from push_to_bq import run_push_to_bq
from authenticate_to_cloud import authenticate_get_clients
from create_be_table import create_BER_Table

def main():

    bq_client, drive_service = authenticate_get_clients()
    reset_folders()   
    get_raw_segments(countries, segments, bq_client)
    # move_without_splitting()
    split_files()
    segment_dict = transfer_files_to_drive()
    # run_push_to_bq(segment_dict, bq_client)
    # create_BER_Table(code_name,bq_client)
    
    


    
if __name__ == "__main__":
    main()