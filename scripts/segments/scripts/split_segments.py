import os

# import shutil

from variables import *
from input import *
import random


def read_data_folder(country):
    
    # This function reads the files in the data/raw directory and saves them into three results:
    # 1. list of the sets of data
    # 2. list of names for the segments
    # 3. set of dids to be used in the controll segment

    # No parameters are needed
    # Folder with data source data/raw
    # input needed: excluded segments


    # initialize results lists
    sets = []
    names = []
    
    # initalize result sets
    for_controlled = set([])
    exclude = set([])

    # iterate over the files in the "raw" directory
    for file in os.listdir("scripts/segments/data/raw"):
        # skip files not from the intended country
        if country not in file: continue
        #open the file
        with open("scripts/segments/data/raw/" + file) as inpf:
            #skip the title in the first line
            inpf.readline()
            #strip any spaces or new lines and save the DID in a set
            temp_set = set([line.strip() for line in inpf])
            #append to the list of sets
            sets.append(temp_set)
            #get the segment name from the file name
            name = file.split(".")[0]
            # append the name to a list
            names.append(name)
            #boolean for list exclusion
            is_excluded = False
            #iterate over the names of lists to be excluded
            for segment in excluded_segments:
                #if the name is in the exclusion list append the data to the exclusion set 
                # and set the exclusion boolean to true
                if segment.replace(" ","_") in name:
                    print("Segment ",segment," added to the exclusion set")
                    exclude.update(temp_set)
                    is_excluded=True
            # if the data is not to be excluded append it to the set of dids to be used in the control segment
            if not is_excluded:
                for_controlled.update(temp_set)
    # remove the excluded dids from the for_controlled set to get the dids that will be used to get the control segment
    for_controlled = list(for_controlled - exclude)

    # returrn the data sets, names and the dids to be used to get the control
    return sets, names, for_controlled


def get_control(for_controlled):
    # this function gets a random sample of a pre-determined size to be used as a control segment
    # parameter: for_controlled, is a list of dids from the audience segments used, and with the dids 
    # from the excluded segments removed from it
    # input needed: controlled size, which is the size of the controlled segment

    # get a random sample from the list
    controlled_segment = random.sample(sorted(for_controlled), controlled_size)
    # convert the list to a set to remove any duplicates
    controlled_segment = set(controlled_segment)

    # return the result segment
    return controlled_segment



def exclude_control_from_segments(sets, controlled_segment):
    # this function iterates over the segment sets and excludes the control segment from them
    # parameters:
    #   -control_segment a random sample from the audiences used for the campaign
    #   -sets: sets of dids from the audiences used in the campaign
    for i in range(0, len(sets)):
        # subtract the two sets to get a new set with the control excluded
        sets[i] = sets[i] - controlled_segment

    return sets


def Write_output_to_files(sets, control, names):
    #this function writes the output sets into files
    # output directories:
    #   - data/controlled: for the controlled segment
    #   - data/served for the served segments
    # parameters:
    #   -sets: sets of segments to be served
    #   -control: control segment
    #   -names: namesof the semgments on the same order as "sets" list

    #get the name fot the control segment from the first segment (codename_country)
    name_split = names[0].split("_")
    #open the file
    with open(
        f"scripts/segments/data/controlled/{name_split[0]}_{name_split[1]}_controlled.csv", "w"
    ) as outf:
        # write the column title
        outf.write("DID\n")
        #write the lines
        for did in control:
            outf.write(did + "\n")

    # iterate over the segments sets indexes
    for i in range(0, len(sets)):
        # get the segment
        served = sets[i]
        # write into a file using the name on the same index 
        with open("scripts/segments/data/served/" + names[i] + "_served.csv", "w") as outf:
            # write the column title
            outf.write("DID\n")
            # write the lines
            for did in served:
                outf.write(did + "\n")



def split_files():

    for country in countries:
        # Thin function runs all the other functions in turn
        sets, names, for_controlled = read_data_folder(country)  # read data
        controlled_segment = get_control(for_controlled)  # get control segment
        exclude_control_from_segments(
            sets, controlled_segment
        )  # exclude control from the segment
        Write_output_to_files(sets, controlled_segment, names)  # write segments to files


