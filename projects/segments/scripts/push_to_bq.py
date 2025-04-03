# this code is for pushing the audience segment to big query in preparation for the reports
import sys
import os

from google.cloud import bigquery
from google.oauth2 import service_account

from variables import *
from transfer_to_drive import transfer_files_to_drive

# aaa
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, ".."))
sys.path.append(project_root)

from input import *

# # Authenticate with BigQuery
# credentials = service_account.Credentials.from_service_account_file(
#     key_bq,
#     scopes=["https://www.googleapis.com/auth/cloud-platform","https://www.googleapis.com/auth/drive"],
# )
# bq_client = bigquery.Client(credentials=credentials, project=project)


def create_Combined_table(country, bq_client):
    # this functions creates a table that will include all the segments
    # the try catch is here since in case the code was ran twice an error will be returned because the table already exists
    # the input parameter is the country code
    try:
        # create a table ref object
        table_ref = bq_client.dataset(dataset_campaign_segments).table(
            f"{code_name}_Segments"
        )
        # provide the table ref and the schema to create a table object
        table = bigquery.Table(table_ref, schema=schema_Combined)
        # create the table
        bq_client.create_table(table)
    except:
        print(
            f"{code_name}_Segments was already created. If not intended, delete the table and run again"
        )


def insert_to_combined(table_name, bq_client):
    # this function iserts the table which's name is provided as a parameter into the combined segments table

    # split the table name
    table_split = table_name.split("_")
    # get the country code
    country = table_split[1]
    # get the segment name with spaces insetead of "_"
    Segment = " ".join(table_split[2:-2])
    # get if the table is a controlled or served segment
    control = table_split[-1]

    # check if the table is from the controlled or exposed and create a boolean for BQ
    if control == "controlled":
        control = "True"
        Segment = "Controlled"
    else:
        control = "False"

    # create the query for the insert
    query = f"""
    Insert INTO {project}.{dataset_campaign_segments}.{code_name}_Segments
    (DID,Segment,Country,Controlled)
    (
        Select DID,'{Segment}','{country}',{control}
        FROM `{project}.{dataset_campaign_segments}.{table_name}`
    )
    """

    # Execute the query
    query_job = bq_client.query(query)

    # Wait for the query to complete
    query_job.result()


def create_external_table(file_id, table_name, bq_client):
    # this function creates a table on Big Query using drive file id of a csv file

    # from the ID create the drive link
    drive_uri = f"https://drive.google.com/open?id={file_id}"
    # create the external table configuration
    external_config = bigquery.ExternalConfig("CSV")
    external_config.source_uris = [drive_uri]
    external_config.autodetect = True
    # read the schema from variables.py
    schema = schema_DID
    # create table ref object
    table_ref = bq_client.dataset(dataset_campaign_segments).table(table_name)
    # create table object
    table = bigquery.Table(table_ref, schema=schema)
    # provide the external table configuration
    table.external_data_configuration = external_config
    # create the table
    table = bq_client.create_table(table)
    # print the table name for code progress monitoring
    print(f"External table {table.table_id} created successfully.")

    return table_name


def delete_table(table_name, bq_client):
    # Specify the dataset and table to delete
    table_ref = bq_client.dataset(dataset_campaign_segments).table(table_name)

    # Delete the table
    bq_client.delete_table(table_ref, not_found_ok=True)


def run_push_to_bq(drive_files_dict, bq_client):
    # this function runs the other functions in turn

    # For each country create the combined segment table
    for country in countries:
        create_Combined_table(country, bq_client)

    # list to save the table names
    table_names = []
    # for each drive file provided create a BQ table and save the table name
    for file_id, name in drive_files_dict.items():
        table_name = create_external_table(file_id, name, bq_client)
        table_names.append(table_name)

    # for each table, insert it into its corresponding country combined segments table and delete the table
    for table_name in table_names:
        insert_to_combined(table_name, bq_client)
        delete_table(table_name, bq_client)


# main function
def main():
    run_push_to_bq(transfer_files_to_drive(), bq_client)


# main if needs to run separately
if __name__ == "__main__":

    main()
