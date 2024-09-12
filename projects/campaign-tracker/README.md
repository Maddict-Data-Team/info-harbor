# Campaign-Tracker

## Overview
The Campaign Tracker project is a metadata populator for the Info-Harbor. It takes the input provided by the user and creates the record in the campaign tracker table in the database.


## Table of Contents
- [Overview](#overview)
- [Technologies](#technologies)
- [Usage Instructions](#usage-instructions)
  - [Steps](#Steps)
  - [Field Description](#field-description)
## Technologies
This project is built using the following technologies:
- **Google Cloud Platform (GCP)** for infrastructure and services.
- **Python** for scripting and data manipulation.
- **SQL** for querying BigQuery.

## Usage Instructions

This section contains all the needed info for using the campaign tracker.

### Steps
1. fill in the necessary info in the **input.py** file (field descriptions in the section below)
2. Run the **main.py** script

### Field Descriptoin

- **campaign_name** string, field for the name of the campaign.
- **countries** list of strings, contains country abbreviations for example **KSA** for **Saudi Arabia**
- **start_date** string, start date of the campaign in the format **YYYY-MM-DD**
- **end_date** string, end date of the campaign in the format **YYYY-MM-DD**
- **type** string, these are preset values for the campaign type.
    - **Retail** is a dashboard reporting on a client's POIs, and a list of competitors (8 by default).
    - **Placelift Report**/**Placelift** is a report of the footfall on the client's POIs runs at the end of the campaign.
    - **Placelift Dashboard** is a Dashboard reporting on the footfall on the client's POIs runs on an interval basis.
    - **Historical Data** is a campaign where the backend report was extracted and saved for future use.
    - **Historical Data - Not Found** is an old campaign where the backend report was not found.
- **backend_reports** list of integers, contains the ids of the backend reports for each country or 0 if it has none.
- **time_interval** integer, the interval for which the automation should run the code, 0 if not used.
- **has_segments** integer, 1 if the campaign uses our segment and 0 if not.