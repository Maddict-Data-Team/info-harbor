import configparser
from variables import *
from datetime import datetime,timedelta
import traceback
import os

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
    # the relative path to the configuration
    rel_path = "queries.ini"
    # join the two above paths
    abs_file_path = os.path.join(script_dir, rel_path)

    config = configparser.ConfigParser()
    config.read(abs_file_path)
    return config


def build_query(
    query, codename, start_date_q="", end_date_q="", countries=[], radiuses=[], custom_replace_dict={}
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
    # Convert codename to str
    codename = str(codename)

    # Replace the set of predefined placeholders with inputs from variables file
    for key in static_query_replace:
        query = query.replace(key, static_query_replace[key])

    # Set the codenameif the campaign
    query = query.replace("{codename}", codename)
    # Set the start date of the query
    query = query.replace("{start_date_q}", start_date_q)
    # Set the end date of the query
    query = query.replace("{end_date_q}", end_date_q)

    # set last_update as now if available
    now = datetime.now()
    query = query.replace("{new_last_update}",str(now))

    # If there is a country placeholder there should be a union repeating the query for each country
    # This is done because countries each have separate tables.
    if "{country}" in query:
        union_query = ""
        for country in countries:
            # if there were more than one country add a union between them
            if union_query != "":
                union_query += "\nUNION ALL\n"
            # Replace the country placeholders
            union_query += query.replace("{country}", country).replace(
                "{country_beh}", get_country_beh(country)
            )

        query = union_query

    # If there is a radius placeholder there should be a union repeating the query for each radius
    # This is done this way since it will execute faster than using the radius column
    if "{radius}" in query:
        union_query = ""
        for radius in radiuses:
            # if there were more than one radius add a union between them
            if union_query != "":
                union_query += "\nUNION ALL\n"
            # Replace the radius placeholders
            union_query += query.replace("{radius}", str(radius))
        query = union_query
    return query

def get_campaign_tracker_data(codename, config, bq_client):
    # Get the raw metadata query
    query_metadata_raw = config.get("Setup", "query_metadata")
    # Build te query
    query_metadata = build_query(query_metadata_raw, codename)
    # run the query and retreive the results
    metadata_raw = run_query_get_res(query_metadata, bq_client)
    # extract the list of countries

    return metadata_raw

def get_metadata(codename, config, bq_client):
    """Query the tracher table using th ecodename to get the pipeline metadata
    parameters:
        codename: identification for the campaign
        config: parsed configuration file
        bq_client: authenticated connection to bq for query execution
    return:
        countries: list of countries.
        end_date: end date of the campaign "YYYY-MM-DD"
        pipeline_type: preset strings that indicates the type if the pipeline
            Values:
                -Retail Intelligence Dashboard: for retail intelligece dashboards
                -Placelift: for placelift dashboards and reports

    """

    metadata_raw = get_campaign_tracker_data(codename, config, bq_client)
    countries = []
    for row in metadata_raw:
        countries.append(row.country)

    # The following metadata are the same for all rows of a certain codename
    # Extract end date
    end_date = row.end_date
    # Extract the pipeline type
    pipeline_type = row.type
    # Extract the interval
    interval = row.time_interval
    # Extract start date
    last_update = row.last_update
    # Extract the pipeline type
    backend_report = row.backend_report
    # Get the field that indicates if there are segments
    segments =  row.segments
    
    if pipeline_type == "Placelift Report" or pipeline_type == "Placelift Dashboard" or pipeline_type == "Placelift":
        if segments == 0:
            pipeline_type = "Placelift No Segments"
        elif backend_report == 0:
            pipeline_type = "Placelift No BER"
        else:
            pipeline_type = "Placelift"

    return countries, pipeline_type, end_date, interval, last_update


def get_radiuses(codename, config, bq_client):
    """Get radiuses used in the POIs
    parameters:
        codename: identification for the campaign
        config: parsed configuration file
        bq_client: authenticated connection to bq for query execution
    return:
        radiuses: list of radiuses.
    """

    # read the query from the config file
    query = config.get("Setup", "radius_query")
    # build the query
    query = build_query(query, codename)

    # run the query and fetch the results
    result = run_query_get_res(query, bq_client)
    # create a list of the radiuses
    radiuses = []
    for row in result:
        radiuses.append(row[0])
    return radiuses


def run_pipeline_queries(
    config,
    codename,
    end_date_q,
    start_date_q,
    countries,
    pipeline_type,
    bq_client,
    radiuses,
):
    """Builds and runs the necessary queries for a given pipeline type
    parameters:
        config: parsed configuration file
        codename: identification for the campaign
        end_date_q: last date for the run "YYYY-MM-DD"
        start_date_q: start date for the run "YYYY-MM-DD"
        countries: list of countries assigned for the codename
        pipeline_type:
        bq_client: authenticated connection to bq for query execution
    return:
        radiuses: list of radiuses.
    """
    print("Started with the queries:\n")
    # Read the query list from the config file for the given pipeline type
    queries = config.get(pipeline_type, "queries").split(",")
    # Loop over the list of query names
    for query_name in queries:
        # If the quey name is common_queries then run the common queries specified in the config file
        if query_name == "common_queries":
            # Re-call the function with "Common ueries" as the pipeline type
            run_pipeline_queries(
                config,
                codename,
                start_date_q,
                end_date_q,
                countries,
                "Common Queries",
                bq_client,
                radiuses,
            )
            # skip the rest of the steps for this iteration
            continue

        print("Parsing Query: ", query_name)
        # Get the raw query for the given query name
        query_raw = config.get(pipeline_type, query_name)
        # Build the query from the raw
        parsed_query = build_query(
            query_raw, codename, start_date_q, end_date_q, countries, radiuses
        )
        # Set the destiation table using the codename and query name
        destination = f"{project}.{dataset_footfall}.{codename}_{query_name}"

        print("Running Query: ", query_name)

        # In all queries except visitors the table should be entirely replaced
        in_write_disposition = "WRITE_TRUNCATE"
        if query_name == "visitors":
           in_write_disposition = "WRITE_APPEND"
        
        # Run the query and save the result in the destination table
        run_query_save_table(parsed_query, destination, bq_client, in_write_disposition)
        print("Finished Query: ", query_name)
        print("-------------------------------------------------")


def get_run_dates(end_date, last_update, interval):
    end_date = datetime(end_date.year, end_date.month, end_date.day)
    last_update = datetime(last_update.year, last_update.month, last_update.day)
    today = datetime.today()


    end_date_q = today - timedelta(days=9)
    
    end_date_p7 = end_date + timedelta(days=7)

    if end_date_q > end_date_p7:
        end_date_q = end_date_p7

    return last_update.strftime("%Y-%m-%d"), end_date_q.strftime("%Y-%m-%d")

def update_last_update(config,codename,bq_client):
    
    query = config.get("Setup", "update_last_update")
    query = build_query(query,codename)

    run_query(query,bq_client)


def run_by_codename(codename, bq_client):
    """This function calls the other functions in turn to execute the pipeline
    parameters:
        codename: identification for the campaign
        bq_client: authenticated connection to bq for query execution
    return:
        Nothing
    """
    try:
            
        # read configuration file
        config = read_config()
        print("Read the ini file")
        # Retreive necessary metadata parameters
        countries, pipeline_type, end_date, interval, last_update = get_metadata(
            codename, config, bq_client
        )
        # # Get the list of radiuses used
        radiuses = get_radiuses(codename, config, bq_client)
        # Get dates for the current run
        start_date_q, end_date_q = get_run_dates(end_date, last_update, interval)
        print("Got the metadata")

        print(start_date_q, end_date_q)
        # Run the pipeline using the metadata parameters
        run_pipeline_queries(
            config,
            codename,
            end_date_q,
            start_date_q,
            countries,
            pipeline_type,
            bq_client,
            radiuses,
        )  
        

        update_last_update(config,codename,bq_client)
    except:
        traceback.print_exc()
        return "error"