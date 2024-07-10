import configparser
from variables import *
import pyperclip

#will transfere to variables later, and change some of the names
static_query_replace = {
    "{hwg_dataset}": dataset_HWG,
    "{footfall_dataset}":dataset_footfall,
    "{project}":project,
    "{metadata_dataset}":dataset_metadata,
    "{campaign_tracker_table}":table_campaign_tracker,
    "{location_signals_dataset}":dataset_LS,
    "{device_os_mapping_table}":table_os_mapping,
    "{hwg_table}":table_HG,
    "{lookup_behavior_table}":table_behavior_lookup,
}

country_id_dict = {
    "UAE":"1",
    "KSA":"2",
    "KWT":"3"}

def run_query(query, bq_client):
    query_job = bq_client.query(query)
    query_job.result()
    print("Query executed successfully")

def run_query_get_res(query, bq_client):
    query_job = bq_client.query(query)
    rows = query_job.result()
    return rows

def run_query_save_table(query,destination_table,bq_client):

    job_config = bigquery.QueryJobConfig(destination=destination_table, write_disposition="WRITE_TRUNCATE")
    query_job = bq_client.query(query, job_config=job_config)
    query_job.result()



def get_country_beh(country):
    if country == "QAT":
        return "QTR"
    else:
        return country


def read_config():
    config = configparser.ConfigParser()
    config.read('scripts/automation/queries.ini')
    return config


def build_query(query,codename,last_update="",today="",countries=[],union_countries=False):
    # This function builds the query by replacing the placeholders with the necessary
    # strings, and sets up some queries with union in case of multiple country input

    #parameters:
    #       1. query: the query with the placeholders   (string)
    #       2. codename: the metadata unique code for the campaign (int)
    #       3. start_date: the start data of the campaign (string) (yyyy-mm-dd) 
    #       4. end_date: the end data of the campaign (string) (yyyy-mm-dd) 
    #       5. countries: list of country 3 letter abbreviation (list) ex: ["UAE","KSA"]

    codename = str(codename)
    # union_countries= False
    if len(countries)==1:union_countries=False
    for key in static_query_replace:
        query = query.replace(key,static_query_replace[key])

    query = query.replace("{codename}",codename)
    query = query.replace("{last_update}",last_update)
    query = query.replace("{today}",today)
    

    if union_countries:
        union_query = ""
        for country in countries:
            if union_query !="":
                union_query +="\nUNION ALL\n"
            union_query += query.replace("{country}",country)\
            .replace("{country_beh}",get_country_beh(country))
            # .replace("{country_id}",country_id_dict[country])
        return union_query
    else:
        if len(countries)>0:
            query = query.replace("{country}",countries[0])\
            .replace("{country_beh}",get_country_beh(countries[0]))
            # .replace("{country_id}",country_id_dict[countries[0]])
        return query




def get_metadata(codename,config,bq_client):

    query_metadata_raw = config.get('Setup','query_metadata')
    
    query_metadata = build_query(query_metadata_raw,codename)

    metadata_raw = run_query_get_res(query_metadata, bq_client)

    countries = []
    for row in metadata_raw:
        countries.append(row[2])

    last_update = row[0].strftime("%Y-%m-%d")#   %m/%d/%Y")
    today = row[1].strftime("%Y-%m-%d")
    pipelie_type = row[3]
    return countries,last_update,today,pipelie_type
    


def run_pipeline_queries(config,codename,last_update,today,countries,pipeline_type,bq_client):
    print("Stared with the queries")
    queries = config.get(pipeline_type,'queries').split(",")
    queries_union_countries = config.get(pipeline_type,'queries_union_countries').split(",")

    for query_name in queries:
        print("Parsing Query: ",query_name)
        union_countries = False
        if query_name in queries_union_countries:
            union_countries = True
        query_raw = config.get(pipeline_type,query_name)
        parsed_query = build_query(query_raw,codename,last_update,today,countries,union_countries)
        destination = f"{project}.{dataset_footfall}.{codename}_{query_name}"
        # input(destination)
        print("Running Query: ",query_name)
        run_query_save_table(parsed_query,destination,bq_client)
        print("Finished Query: ",query_name)
        print("-------------------------------------------------")

def run_by_pipeline_type(codename,bq_client):

    config = read_config()
    print("Read te ini file")
    countries,last_update,today,pipelie_type = get_metadata(codename,config,bq_client)
    print("Got the metadata")
    run_pipeline_queries(config,codename,last_update,today,countries,pipelie_type,bq_client)
