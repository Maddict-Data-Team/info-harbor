from google.cloud import bigquery


# credentials

project = "maddictdata"

# Folders

folder_id_Backend_Reports = "1vKOH8eDs92jHSaGyPILAa9p3qH8YUHNo"

# Secret Manager

secret_ber = f"projects/maddictdata/secrets/token-ber/versions/latest"
secret_bq = f"projects/maddictdata/secrets/secret-bq/versions/latest"

# Keys

key_bq = "keys/maddictdata-bq.json"
key_google_sheets = "keys/maddictdata-google-sheets.json"

# BQ Datasets

dataset_LS = "Location_Signals"
dataset_footfall = "Back_End_Footfall"
dataset_BERs = "Back_End_Reports"
dataset_campaign_segments = "Placelift_Campaign_Segments"
dataset_Districts = "District_Mapping"
dataset_HWG = "Automated_HWG"
dataset_mt_Placelift = "maddictdata.Metadata.Placelift"
table_HG = "Home_Graph_Cumulative"

dataset_metadata = "Metadata"
table_campaign_tracker = "Campaign_Tracker"
table_behavior_lookup = "Lookup_Behavior"
table_os_mapping = "device_os_mapping"


# Metadata Status

stage_0 = "Pre-Validation"
stage_1 = "Validation"
stage_2 = "Active"
stage_3 = "Completion Period"
stage_4 = "Finished"

# BQ Schemas

schema_back_end = [
    bigquery.SchemaField("campaign", "STRING"),
    bigquery.SchemaField("LINE", "STRING"),
    bigquery.SchemaField("TIMESTAMP", "TIMESTAMP"),
    bigquery.SchemaField("udid", "STRING"),
    bigquery.SchemaField("devraw", "STRING"),
    bigquery.SchemaField("country", "STRING"),
    bigquery.SchemaField("city", "STRING"),
    bigquery.SchemaField("latitude", "FLOAT64"),
    bigquery.SchemaField("longitude", "FLOAT64"),
    bigquery.SchemaField("dev_os", "STRING"),
    bigquery.SchemaField("dev_make", "STRING"),
    bigquery.SchemaField("dev_type", "STRING"),
    bigquery.SchemaField("connection_type", "STRING"),
    bigquery.SchemaField("carrier", "STRING"),
    bigquery.SchemaField("exchange", "STRING"),
    bigquery.SchemaField("dev_ip", "STRING"),
    bigquery.SchemaField("zip", "STRING"),
    bigquery.SchemaField("creative", "STRING"),
    bigquery.SchemaField("ad_size", "STRING"),
    bigquery.SchemaField("App_ID", "INT64"),
    bigquery.SchemaField("environment", "STRING"),
    bigquery.SchemaField("publisher", "STRING"),
    bigquery.SchemaField("App_Name", "STRING"),
    bigquery.SchemaField("impressions", "INT64"),
    bigquery.SchemaField("clicks", "INT64"),
]


table_mapping = {
    "KSA": "POI_DB_KSA",
    "UAE": "POI_DB_UAE",
    "QAT": "POI_DB_QTR",
    "KWT": "POI_DB_KWT",
    "OMN": "POI_DB_OMN",
    "BHR": "POI_DB_BHR",
}


def get_country_beh(country):
    if country == "QAT":
        return "QTR"
    else:
        return country


# QUERY
def get_query_dict(code_name, country, start_date, end_date):

    q_reaction_time = f"""
      SELECT
      COUNT(devraw)  AS Count,
      daydiff
      FROM (
      SELECT
          DISTINCT devraw,
          MIN(e.timestamp) AS exposure,
          MIN(v.Local_Time) AS visit,
          DATE_DIFF(MIN(v.Local_Time), MIN(e.timestamp), day) AS daydiff
      FROM
          `{project}.{dataset_BERs}.{code_name}` AS e
      JOIN
          `{project}.{dataset_footfall}.{code_name}_{country}_visitors` AS v
      ON
          devraw=DID
       where v.controlled = false
      GROUP BY
          devraw
      HAVING
          daydiff >0 )
      GROUP BY
      daydiff
      ORDER BY
      daydiff asc
      """

    q_per_branch = f"""

  SELECT
  COUNT(DISTINCT(ls.did))   AS Count,
  COUNT(DISTINCT(ls.did))/foot.visitors_count*100  AS Count_perc,
  concat(poi.Name,", ",poi.desc) as Name
  FROM
  `{project}.{dataset_footfall}.{code_name}_{country}_visitors` AS ls
  JOIN
  `{project}.{dataset_footfall}.{code_name}_{country}_POIs` AS poi
  ON
  ST_DISTANCE(ST_GEOGPOINT(ls.longitude,ls.latitude),ST_GEOGPOINT(poi.longitude,poi.latitude)) < radius
  join `{project}.{dataset_footfall}.{code_name}_{country}_footfall` as foot
  on foot.controlled=ls.controlled
   where ls.controlled = false
  GROUP BY
  poi.id,
  poi.Name,
  poi.desc,
  foot.visitors_count
  ORDER BY Count desc
  limit 5
  """

    q_weekday = f"""
  SELECT
  COUNT(DISTINCT(did))  AS Count,
  FORMAT_DATE('%A', Local_Day) AS weekday_name_full,
  EXTRACT(DAYOFWEEK FROM Local_Day) as weekday_nbr
  FROM
  `{project}.{dataset_footfall}.{code_name}_{country}_visitors`
   where controlled = false
  GROUP BY
  weekday_name_full,
  weekday_nbr
  ORDER BY
  weekday_nbr asc
  """

    q_per_segment = f"""
  SELECT
  COUNT(DISTINCT(ls.did))  AS Count,
  seg.segment
  FROM
  `{project}.{dataset_footfall}.{code_name}_{country}_visitors` AS ls
  JOIN
  `{project}.{dataset_campaign_segments}.{code_name}_{country}_Segments` AS seg
  ON
  seg.did = ls.did
   where ls.controlled = false
  GROUP BY
  seg.Segment
  """

    q_hourly = f"""
  SELECT
  COUNT(DISTINCT(did))  AS Count,
  Local_Hour
  FROM
  `{project}.{dataset_footfall}.{code_name}_{country}_visitors`
   where controlled = false
  GROUP BY
  Local_Hour
  ORDER BY
  Local_Hour asc
  """

    q_daily = f""" 
  SELECT
  COUNT(DISTINCT(did))  AS Count,
  Local_Day
  FROM
  `{project}.{dataset_footfall}.{code_name}_{country}_visitors`
   where controlled = false
  GROUP BY
  Local_Day
  ORDER BY
  Local_Day
  """

    q_HG_district = f"""
  SELECT Name, COUNT(DID)  AS Count
  FROM `{project}.{dataset_Districts}.{country}_Districts` AS DIS
  JOIN `{project}.{dataset_HWG}.{table_HG}` AS HWG

  ON ST_WITHIN(ST_GEOGPOINT(HWG.Long1, HWG.Lat1), DIS.Polygon)

  WHERE HWG.DID IN (
  SELECT DID FROM {project}.{dataset_footfall}.{code_name}_{country}_visitors
   where controlled = false
  )

  GROUP BY NAME
  ORDER BY Count desc
  limit 10
  """
    q_visits_district = f"""
  SELECT
  COUNT(DISTINCT(ls.did))  AS Count,
  dist.Name,
  COUNT(DISTINCT(ls.did))/foot.visitors_count*100  AS Count_perc,
  dist.id
  FROM
  `{project}.{dataset_footfall}.{code_name}_{country}_visitors` AS ls
  JOIN
  `{project}.{dataset_Districts}.{country}_Districts` AS dist
  ON
  ST_WITHIN(ST_GEOGPOINT(ls.longitude,ls.latitude),dist.Polygon)
  join `{project}.{dataset_footfall}.{code_name}_{country}_footfall` as foot
  on foot.controlled=ls.controlled
  where ls.controlled = false
  GROUP BY
  dist.id,
  dist.Name3,
  dist.Name,
  foot.visitors_count
  ORDER BY Count desc
  limit 5
  """

    q_get_visitors = f"""
          Select ls.did,ls.Local_Day,ls.Timestamp,ls.Local_Hour,ls.Longitude,ls.latitude,ls.Local_time,seg.controlled,concat(cast(ls.latitude AS String),",",cast(ls.Longitude AS String)) as geoloc 
          from `{project}.{dataset_LS}.{country}_Data` as ls
          join `{project}.{dataset_footfall}.{code_name}_{country}_POIs` as poi
          on st_distance(st_geogpoint(ls.Longitude,ls.latitude),st_geogpoint(poi.longitude,poi.latitude))<poi.Radius
          join `{project}.{dataset_campaign_segments}.{code_name}_{country}_Segments` as seg
          on seg.did = ls.did
          where ls.timestamp between "{start_date}" and "{end_date}"
          and ls.did in (SELECT distinct(devraw) FROM `{project}.{dataset_BERs}.{code_name}` )
          and poi.Country='{country}'
          and seg.controlled = false

          Union All

          Select ls.did,ls.Local_Day,ls.Timestamp,ls.Local_Hour,ls.Longitude,ls.latitude,ls.Local_time,seg.controlled,concat(cast(ls.latitude AS String),",",cast(ls.Longitude AS String)) as geoloc 
          from `{project}.{dataset_LS}.{country}_Data` as ls
          join `{project}.{dataset_footfall}.{code_name}_{country}_POIs` as poi
          on st_distance(st_geogpoint(ls.Longitude,ls.latitude),st_geogpoint(poi.longitude,poi.latitude))<poi.Radius
          join `{project}.{dataset_campaign_segments}.{code_name}_{country}_Segments` as seg
          on seg.did = ls.did
          where ls.timestamp between "{start_date}" and "{end_date}"
          and seg.controlled = true
          and poi.Country='{country}'

      """

    # TODO
    q_get_footfall = f"""
          Select visitors_count,uniques_count,uniques.controlled From 
      (
      Select Count(distinct(vis.did)) as visitors_count,seg.controlled from `{project}.{dataset_footfall}.{code_name}_{country}_visitors` as vis
      join `{project}.{dataset_campaign_segments}.{code_name}_{country}_Segments` as seg
      on vis.did = seg.DID
      where vis.controlled = false
      group by seg.controlled
      ) as visitors
      join
      (Select Count(distinct(vis.devraw)) as uniques_count,seg.controlled from `{project}.{dataset_BERs}.{code_name}` as vis
      join `{project}.{dataset_campaign_segments}.{code_name}_{country}_Segments` as seg
      on vis.devraw = seg.DID
      group by seg.controlled) as uniques
      on visitors.controlled = uniques.controlled

      UNION ALL

      Select visitors_count,uniques_count,uniques.controlled From 
      (
      Select Count(distinct(vis.did)) as visitors_count,seg.controlled from `{project}.{dataset_footfall}.{code_name}_{country}_visitors` as vis
      join `{project}.{dataset_campaign_segments}.{code_name}_{country}_Segments` as seg
      on vis.did = seg.DID
      where vis.controlled = true
      group by seg.controlled
      ) as visitors
      join
      (Select Count(distinct(did)) as uniques_count,controlled from `{project}.{dataset_campaign_segments}.{code_name}_{country}_Segments` as seg
        where controlled = true
        group by controlled) as uniques
      on visitors.controlled = uniques.controlled

  """
    # TODO
    q_get_lookalikes = f"""
      Select count(distinct(vis.did)) as count_vis,beh.Behavior_name from `{project}.{dataset_footfall}.{code_name}_{country}_visitors` as vis
      join `maddictdata.POI_DB_{get_country_beh(country)}.Behavioral_{country}_RAW_Cumulative` as beh
      on beh.did = vis.did
       where vis.controlled = false
       and beh.Behavior_name not in (Select distinct(segment) from `{project}.{dataset_campaign_segments}.{code_name}_{country}_Segments`)
      group by Behavior_Name
      order by count_vis desc
      limit 5
  """
    q_get_SOV = f"""
  SELECT
  Count_uniques,
  serv.segment,
  Count_total,
  (Count_uniques/Count_total) AS Share_of_Volume
  FROM (
    SELECT
      COUNT(DISTINCT(devraw)) AS Count_uniques,
      seg.segment
    FROM
      `{project}.{dataset_BERs}.{code_name}` AS ber
    JOIN
      `{project}.{dataset_campaign_segments}.{code_name}_{country}_Segments` AS seg
    ON
      seg.did = ber.devraw
    GROUP BY
      segment) AS serv
  JOIN (
    SELECT
      COUNT(DISTINCT(did)) AS Count_total,
      seg.segment
    FROM
      `{project}.{dataset_campaign_segments}.{code_name}_{country}_Segments` AS seg
    GROUP BY
      segment) AS total
  ON
    total.segment = serv.segment
  WHERE
    serv.segment !="Controlled"
  """

    queries = [
        {
            "query": q_get_visitors,
            "description": "All visitors",
            "destination": f"{project}.{dataset_footfall}.{code_name}_{country}_visitors",
        },
        {
            "query": q_get_footfall,
            "description": "footfall",
            "destination": f"{project}.{dataset_footfall}.{code_name}_{country}_footfall",
        },
    ]

    queries2 = [
        {
            "query": q_get_visitors,
            "description": "All visitors",
            "destination": f"{project}.{dataset_footfall}.{code_name}_{country}_visitors",
        },
        {
            "query": q_get_lookalikes,
            "description": "Lookalikes table",
            "destination": f"{project}.{dataset_footfall}.{code_name}_{country}_lookalikes",
        },
        {
            "query": q_get_footfall,
            "description": "footfall",
            "destination": f"{project}.{dataset_footfall}.{code_name}_{country}_footfall",
        },
        {
            "query": q_visits_district,
            "description": "Visitors per district",
            "destination": f"{project}.{dataset_footfall}.{code_name}_{country}_visits_district",
            "restrited_to": ["UAE", "KSA"],
        },
        {
            "query": q_reaction_time,
            "description": "Reaction time",
            "destination": f"{project}.{dataset_footfall}.{code_name}_{country}_reaction_time",
        },
        {
            "query": q_per_branch,
            "description": "Visits per branch",
            "destination": f"{project}.{dataset_footfall}.{code_name}_{country}_branch",
        },
        {
            "query": q_weekday,
            "description": "Visits distribution by weekday",
            "destination": f"{project}.{dataset_footfall}.{code_name}_{country}_weekday",
        },
        {
            "query": q_per_segment,
            "description": "Visits per segment",
            "destination": f"{project}.{dataset_footfall}.{code_name}_{country}_visits_per_segment",
        },
        {
            "query": q_hourly,
            "description": "Visits distribution by hour of day",
            "destination": f"{project}.{dataset_footfall}.{code_name}_{country}_hourly",
        },
        {
            "query": q_daily,
            "description": "Daily distribution of visits",
            "destination": f"{project}.{dataset_footfall}.{code_name}_{country}_daily",
        },
        {
            "query": q_HG_district,
            "description": "Home graph by district for visitors",
            "destination": f"{project}.{dataset_footfall}.{code_name}_{country}_HG_district",
            "restrited_to": ["UAE", "KSA"],
        },
        {
            "query": q_get_SOV,
            "description": "Share of Value By audience Segment",
            "destination": f"{project}.{dataset_footfall}.{code_name}_{country}_SOV",
        },
    ]

    return queries


# Main Queries

update_status_1 = f"""
UPDATE
  `{dataset_mt_Placelift}`
SET
  status = 'In Progress'
WHERE
  status = 'On Hold'
  AND type = 'Dashboard'
"""

update_status_2 = f"""
SELECT
  *
FROM
  `{dataset_mt_Placelift}`
WHERE
  status = 'Break'
  OR status = 'In Progress'
"""

update_status_3 = f"""
UPDATE
 `{dataset_mt_Placelift}`
SET
  status = 'Break'
WHERE
  DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) > DATE(end_date)
"""

update_status_4 = f"""
UPDATE
  `{dataset_mt_Placelift}`
SET
  status = 'Done'
WHERE
  status = 'Break'
"""


def q_deduplicate_ber(code_name):

    return f"""
CREATE OR REPLACE TABLE
  `{project}.{dataset_BERs}.{code_name}` AS
SELECT
  DISTINCT *
FROM
  `{project}.{dataset_BERs}.{code_name}`;
"""
