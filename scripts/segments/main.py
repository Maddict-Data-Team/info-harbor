import subprocess

from input import *

from create_be_table import create_BER_Table
from add_to_metadata import metadata_placelift
from push_to_bq import run_push_to_bq
from split_segments import split_files
from get_segments_raw import get_raw_segments
from reset_folders import reset_folders
from transfer_to_drive import transfere_files_to_drive


def main():    

    get_raw_segments(countries, segments)
    split_files()
    drive_files_dict = transfere_files_to_drive()
    run_push_to_bq(drive_files_dict)
    metadata_placelift()
    create_BER_Table(code_name)
    # reset_folders()
    
if __name__ == "__main__":
    main()