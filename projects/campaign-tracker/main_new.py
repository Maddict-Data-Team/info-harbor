#!/usr/bin/env python3
"""
Campaign Tracker Main Script - Updated Version
Uses shared configuration instead of input.py files
"""
import sys
import argparse
from pathlib import Path

# Add project root to path for shared imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.utils.compatibility import setup_shared_imports, inject_campaign_variables
from shared.config.campaigns import get_campaign, list_campaigns
from shared.config.base_config import PROJECT

# Setup shared imports
setup_shared_imports()

from google.cloud import bigquery
from google.oauth2 import service_account

def create_client():
    """Create BigQuery client"""
    from shared.config.base_config import KEY_BQ_PATH
    
    # Authenticate with BigQuery
    credentials = service_account.Credentials.from_service_account_file(
        KEY_BQ_PATH,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    bq_client = bigquery.Client(credentials=credentials, project=PROJECT)
    return bq_client

def metadata_placelift(campaign_code_name):
    """
    Add campaign metadata to the tracker table
    
    Args:
        campaign_code_name: Campaign code name (e.g., "143")
    """
    # Get campaign configuration
    campaign = get_campaign(campaign_code_name)
    
    # Inject campaign variables for compatibility
    inject_campaign_variables(campaign_code_name, globals())
    
    # Initialize the BigQuery client
    client = create_client()

    # Fetch the last code name from the table
    query_last_code_name = f"""
        SELECT MAX(code_name) AS last_code_name
        FROM `{project}.{dataset_metadata}.{tbl_campaign_tracker}`;
    """
    last_code_name_result = client.query(query_last_code_name).result()
    last_code_name = next(last_code_name_result).last_code_name

    # It will increment the code name
    new_code_name = last_code_name + 1 if last_code_name else 1
    
    print(f"📋 Adding campaign metadata for: {campaign.campaign_name}")
    print(f"🔢 New code name: {new_code_name}")
    
    # Generate and execute queries
    for index, country in enumerate(campaign.countries):
        if country in table_mapping:
            # Get the corresponding backend report for the country
            backend_report = campaign.backend_reports[index] if index < len(campaign.backend_reports) else 0
            
            # Generate the query string
            query = f"""INSERT INTO
                        {project}.{dataset_metadata}.{tbl_campaign_tracker} (
                            id,
                            code_name,
                            campaign_name,
                            start_date,
                            end_date,
                            country,
                            status,
                            type,
                            backend_report,
                            last_update,
                            time_interval,
                            segments
                        )
                        SELECT
                        COALESCE(MAX(id), 0) + 1 + {index},
                        {new_code_name},
                        '{campaign.campaign_name}-{country}-{backend_report}',
                        DATE '{campaign.start_date}',
                        DATE '{campaign.end_date}',
                        '{country}',
                        '{stage_0}',
                        '{campaign.type}',
                        {backend_report},
                        TIMESTAMP '{campaign.start_date}',
                        {campaign.time_interval},
                        {campaign.has_segments}
                        FROM
                        maddictdata.Metadata.Campaign_Tracker;"""

            # Execute the query
            client.query(query)
            print(f"✅ Added metadata for {country}")

        # Log the new code name for the campaign
        print(f"🎯 New code name {new_code_name} assigned to campaign {campaign.campaign_name} - {country}")

def main(campaign_code_name=None):
    """
    Main function for campaign tracker
    
    Args:
        campaign_code_name: Campaign code name (e.g., "143")
    """
    # Parse command line arguments if not provided
    if campaign_code_name is None:
        parser = argparse.ArgumentParser(description='Add campaign metadata to tracker')
        parser.add_argument('campaign', nargs='?', default='143', 
                          help='Campaign code name (default: 143)')
        parser.add_argument('--list', action='store_true', 
                          help='List available campaigns')
        args = parser.parse_args()
        
        if args.list:
            campaigns = list_campaigns()
            print("Available campaigns:")
            for code in campaigns:
                campaign = get_campaign(code)
                print(f"  {code}: {campaign.campaign_name}")
            return
        
        campaign_code_name = args.campaign
    
    print(f"🚀 Starting campaign tracker for campaign: {campaign_code_name}")
    
    try:
        metadata_placelift(campaign_code_name)
        print(f"✅ Campaign tracker completed successfully for campaign {campaign_code_name}")
        
    except Exception as e:
        print(f"❌ Error in campaign tracker for {campaign_code_name}: {e}")
        raise

if __name__ == "__main__":
    main() 