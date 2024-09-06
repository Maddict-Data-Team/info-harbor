import configparser
from variables import *
import sys
import os
from pathlib import Path


# Get the path to the directory containing this script (main.py)
script_dir = os.path.dirname(__file__)

# Get the parent directory of 'scripts'
project_root = os.path.abspath(os.path.join(script_dir, '..'))

# Add the parent directory to sys.path
sys.path.append(project_root)

from input import *


class NoFilterForPoiQuery(Exception):
    pass



def run_query(query, bq_client): 
    """Run a query
    parameters:
        auery: query to run
        bq_client: connection to big query
    return:
        Nothing
    """
    # run the query
    query_job = bq_client.query(query)

    query_job.result()
    print("Query executed successfully")


def run_query_get_res(query, bq_client):
    """Run a query and retreive the results
    parameters:
        query: query to run
        bq_client: connection to big query
    return:
        rows: rows of the result of the query
    """
    # Run the query
    query_job = bq_client.query(query)
    # Retreive the results
    rows = query_job.result()
    return rows


def run_query_save_table(
    query, destination_table, bq_client, in_write_disposition="WRITE_EMPTY"
):
    """Run a query and save the result in a destination table
    parameters:
        auery: query to run
        bq_client: connection to big query
        destination_table: table where the result should be saved
        in_write_disposition: string indicating how should the result be saved (override, append ...)
            allowed strings:
                WRITE_TRUNCATE: If the table already exists, BigQuery overwrites the data, removes the constraints, and uses the schema from the query result.
                WRITE_APPEND: If the table already exists, BigQuery appends the data to the table.
                WRITE_EMPTY: If the table already exists and contains data, a 'duplicate' error is returned in the job result.
            reference:
            https://cloud.google.com/bigquery/docs/reference/rest/v2/Job#JobConfigurationQuery.FIELDS.write_disposition
    return:
        Nothing
    """
    # Create the big-query job configuration
    job_config = bigquery.QueryJobConfig(
        destination=destination_table, write_disposition=in_write_disposition
    )
    # Run the query
    query_job = bq_client.query(query, job_config=job_config)
    query_job.result()


def get_country_beh(country):
    """Get the behavior abbreviation for the country
    since QAT has a different dataset name for the behavior (Should be fixed later)
    parameters:
        country: Country Abbreviation ex: ("UAE")
    return:
        country: Country Abbreviation ex: ("UAE")
    """

    # Only QAT has a different Name
    if country == "QAT":
        return "QTR"
    elif country == "EGY":
        return "EGP"
    else:
        return country


def read_config():
    """Read the .ini file
    parameters:
        Nothing
    Return:
        config: parsed .ini file
    """

    #get the absolute directory of the current script
    script_dir = os.path.dirname(__file__)
    path = Path(script_dir)

    # the relative path to the configuration
    rel_path = "queries.ini"
    # join the two above paths
    abs_file_path = os.path.join(path.parent.absolute(), rel_path)

    config = configparser.ConfigParser()
    config.read(abs_file_path)
    return config


def build_query(
    query, country, codename=0, radius=0, segment="",filters = ""
):
    """This function builds the query by replacing the placeholders with the necessary
    strings, and sets up some queries with union in case of multiple country input

    parameters:
        query: the query with the placeholders   (string)
        codename: the metadata unique code for the campaign (int)
        end_date_q: last date for the run "YYYY-MM-DD"
        start_date_q: start date for the run "YYYY-MM-DD"
        countries: list of country 3 letter abbreviation (list) ex: ["UAE","KSA"]
    """

    

    query = query.replace("{filters}", filters)
            
    # Convert codename to str
    codename = str(codename)

    # Replace the set of predefined placeholders with inputs from variables file
    for key in static_query_replace:
        query = query.replace(key, static_query_replace[key])

    query = query.replace("{segment}", segment)

    query = query.replace("{code_name}", code_name)

    # If there is a country placeholder there should be a union repeating the query for each country
    # This is done because countries each have separate tables.
    query = query.replace("{country}", country).replace(
                "{country_beh}", get_country_beh(country)
            )

    # If there is a radius placeholder there should be a union repeating the query for each radius
    # This is done this way since it will execute faster than using the radius column
    query = query.replace("{radius}", str(radius))

    return query



def run_query_behavior(segment,bq_client,country,codename=0):
    config = read_config()

    q_filters = ""
    radius = 0
    if "hg" in segment.lower() or "near by residents" in segment.lower():
        query = config.get("queries","query_HG")
        radius = hg_radius
    elif "hnwi" in segment.lower():
        query = config.get("queries","query_HNWI")
    elif "custom" in segment.lower():
        query = config.get("queries","query_POI")
        q_filters,radius = get_custom_query_params(segment)
    else:
        query = config.get("queries","query_behavior")


    query = build_query(query,country, codename, radius, segment,q_filters)


    rows = run_query_get_res(query,bq_client)
    return rows

def get_custom_query_params(query_name):
    query_dict = dict_custom_segments[query_name]

    

    query_filters_str = ""
    for key in poi_filter_fields:
        if key in query_dict:
            query_filters_str += f"\n and {key} in ("
            filter_list = query_dict[key]
            i=0
            for filter in filter_list:
                if i>0:query_filters_str+=','
                query_filters_str+=f"'{filter}'"
                i+=1
            query_filters_str += ")"


    if query_filters_str == "":
        raise NoFilterForPoiQuery("The POI query should have at least one filter")


    return query_filters_str, query_dict["radius"]

    





