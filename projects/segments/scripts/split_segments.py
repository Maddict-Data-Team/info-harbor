import os

import sys

from variables import *
import random
import shutil

# Get the path to the directory containing this script (main.py)
script_dir = os.path.dirname(__file__)

# Get the parent directory of 'scripts'
project_root = os.path.abspath(os.path.join(script_dir, ".."))

# Add the parent directory to sys.path
sys.path.append(project_root)

from input import *


control_candidate_limit = 100000


def read_data_folder(country):

    # This function reads the files in the data/raw directory and saves them into three results:
    # 1. list of the sets of data
    # 2. list of names for the segments
    # 3. set of dids to be used in the controll segment

    # No parameters are needed
    # Folder with data source data/raw
    # input needed: excluded segments

    # initialize results lists
    names = []

    # initalize result sets
    for_controlled = set([])
    exclude = set([])

    # iterate over the files in the "raw" directory
    for file in os.listdir("projects/segments/data/raw"):
        # skip files not from the intended country
        if country not in file:
            continue
        # open the file
        with open("projects/segments/data/raw/" + file) as inpf:
            # skip the title in the first line
            inpf.readline()
            # get the segment name from the file name
            name = file.split(".")[0]
            # append the name to a list
            names.append(name)
            # boolean for list exclusion
            is_excluded = False
            # iterate over the names of lists to be excluded
            for segment in excluded_segments:
                # if the name is in the exclusion list append the data to the exclusion set
                # and set the exclusion boolean to true
                segment = segment.replace("custom_", "")
                segment = segment.replace("_", "")
                if segment.replace(" ", "_") in name:
                    is_excluded = True
            if is_excluded:
                continue
            # strip any spaces or new lines and save the DID in a set
            population = [line.strip() for line in inpf]
            temp_set = set(
                random.sample(population, k=min(control_candidate_limit, len(population)))
            )
            # if the data is not to be excluded append it to the set of dids to be used in the control segment
            for_controlled.update(temp_set)
    # remove the excluded dids from the for_controlled set to get the dids that will be used to get the control segment
    for_controlled = list(for_controlled - exclude)

    # returrn the data sets, names and the dids to be used to get the control
    return names, for_controlled


def get_control(for_controlled):
    # this function gets a random sample of a pre-determined size to be used as a control segment
    # parameter: for_controlled, is a list of dids from the audience segments used, and with the dids
    # from the excluded segments removed from it
    # input needed: controlled size, which is the size of the controlled segment

    # Preserve the configured 50,000-of-100,000 control ratio for smaller
    # eligible pools instead of requesting more distinct DIDs than exist.
    population_size = len(for_controlled)
    proportional_size = round(
        population_size * controlled_size / control_candidate_limit
    )
    sample_size = min(
        controlled_size,
        max(1, proportional_size) if population_size else 0,
    )

    # get a random sample from the list
    controlled_segment = random.sample(sorted(for_controlled), sample_size)
    # convert the list to a set to remove any duplicates
    controlled_segment = set(controlled_segment)

    # return the result segment
    return controlled_segment


def Write_output_to_files(control, names,country):
    #this function writes the output sets into files
    # output directories:
    #   - data/controlled: for the controlled segment
    #   - data/served for the served segments
    # parameters:
    #   -sets: sets of segments to be served
    #   -control: control segment
    #   -names: namesof the semgments on the same order as "sets" list

    # get the name fot the control segment from the first segment (codename_country)
    name_split = names[0].split("_")
    # open the file
    with open(
        f"projects/segments/data/controlled/{name_split[0]}_{name_split[1]}_{country}_controlled.csv", "w"
    ) as outf:
        # write the column title
        outf.write("DID\n")
        # write the lines
        for did in control:
            outf.write(did + "\n")

    i=0
    # iterate over the files in the "raw" directory
    for file in os.listdir("projects/segments/data/raw"):
        # skip files not from the intended country
        if country not in file:
            continue
        # open the file
        with open("projects/segments/data/raw/" + file) as inpf:
            # skip the title in the first line
            inpf.readline()


            with open(
            "projects/segments/data/served/" + names[i] + "_served.csv", "w"
            ) as outf:
                # write the column title
                outf.write("DID\n")
                # write the lines
                for did in inpf:
                    if did.strip() not in control:
                        outf.write(did.strip() + "\n")
        i+=1

def split_files():

    for country in countries:
        # Thin function runs all the other functions in turn
        names, for_controlled = read_data_folder(country)  # read data
        controlled_segment = get_control(for_controlled)  # get control segment
        # exclude_control_from_segments(
        #     sets, controlled_segment
        # )  # exclude control from the segment
        Write_output_to_files(controlled_segment, names,country)  # write segments to files

def move_without_splitting():
    # iterate over the raw files
    for file in os.listdir("projects/segments/data/raw"):

        # move the files to the served folder so they could be uploaded to drive
        curr = "projects/segments/data/raw/" + file
        dest = "projects/segments/data/served/" + file
        shutil.move(curr, dest)


if __name__ == "__main__":
    split_files()
