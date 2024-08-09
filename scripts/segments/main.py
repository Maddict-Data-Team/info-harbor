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
from split_segments import split_files
from transfer_to_drive import transfer_files_to_drive
from push_to_bq import run_push_to_bq
from create_be_table import create_BER_Table


def main():
    pass
    # reset_folders()
    # get_raw_segments(countries, segments)
    # split_files()
    # drive_files_dict = transfer_files_to_drive()
    # run_push_to_bq(drive_files_dict)
    # create_BER_Table(code_name)
    
if __name__ == "__main__":
    main()