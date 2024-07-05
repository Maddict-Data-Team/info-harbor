import configparser
from variables import *

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
    "UAE":1,
    "KSA":2,
    "KWT":3}

def get_country_beh(country):
    if country == "QAT":
        return "QTR"
    else:
        return country


def read_config():
    config = configparser.ConfigParser()
    config.read('scripts/automation/queries.ini')
    return config

def build_query(query,codename,start_date,end_date,countries,union_countries):
    for key in static_query_replace:
        query = query.replace(key,static_query_replace[key])

    query = query.replace("{codename}",codename)
    query = query.replace("{start_date}",start_date)
    query = query.replace("{end_date}",end_date)
    
    if union_countries:
        union_query = ""
        for country in countries:
            if union_query !="":
                union_query +="\nUNION ALL\n"
            union_query = query.replace("{country}",country)\
            .replace("{country_beh}",get_country_beh(country))\
            .replace("{country_id}",country_id_dict[country])
        return union_query
    else:
        return query