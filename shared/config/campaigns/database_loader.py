#!/usr/bin/env python3
"""
Database Campaign Loader
Loads campaign configurations from BigQuery instead of hardcoded files
"""
import sys
from pathlib import Path
from google.cloud import bigquery
from google.oauth2 import service_account

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.models.campaign import CampaignConfig
from shared.config.base_config import PROJECT, KEY_BQ_PATH, DATASET_METADATA, TBL_CMPGN_TRACKER

def create_bq_client():
    """Create BigQuery client"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            KEY_BQ_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return bigquery.Client(credentials=credentials, project=PROJECT)
    except Exception as e:
        print(f"❌ Error creating BigQuery client: {e}")
        raise

def load_campaigns_from_database():
    """Load all campaigns from BigQuery Campaign_Tracker table"""
    try:
        print("🔄 Loading campaigns from database...")
        client = create_bq_client()
        
        # Query to get campaigns with proper aggregation
        query = f"""
        SELECT 
            code_name,
            MAX(campaign_name) as campaign_name,
            MAX(start_date) as start_date,
            MAX(end_date) as end_date,
            ARRAY_AGG(DISTINCT country IGNORE NULLS) as countries,
            MAX(type) as type,
            ARRAY_AGG(DISTINCT backend_report IGNORE NULLS) as backend_reports,
            MAX(time_interval) as time_interval,
            MAX(segments) as segments,
            MAX(status) as status
        FROM `{PROJECT}.{DATASET_METADATA}.{TBL_CMPGN_TRACKER}`
        GROUP BY code_name
        ORDER BY code_name
        """
        
        print(f"📊 Executing query on {PROJECT}.{DATASET_METADATA}.{TBL_CMPGN_TRACKER}")
        results = client.query(query).result()
        campaigns = {}
        
        for row in results:
            code_name = str(row.code_name)
            
            # Extract base campaign name (remove country and backend report suffixes)
            base_name = row.campaign_name
            if '-' in base_name:
                # Remove country and backend report suffixes like "-UAE-0"
                parts = base_name.split('-')
                if len(parts) > 1:
                    # Keep everything except the last two parts if they look like country-number
                    if len(parts) >= 3 and parts[-1].isdigit():
                        base_name = '-'.join(parts[:-2])
                    elif len(parts) >= 2:
                        base_name = '-'.join(parts[:-1])
            
            campaigns[code_name] = {
                'campaign_name': base_name,
                'countries': list(row.countries) if row.countries else [],
                'start_date': str(row.start_date) if row.start_date else None,
                'end_date': str(row.end_date) if row.end_date else None,
                'type': row.type or 'Unknown',
                'backend_reports': list(row.backend_reports) if row.backend_reports else [],
                'time_interval': row.time_interval or -1,
                'has_segments': row.segments or 0,
                'status': row.status or 'Unknown'
            }
        
        print(f"✅ Successfully loaded {len(campaigns)} campaigns from database")
        return campaigns
        
    except Exception as e:
        print(f"❌ Error loading campaigns from database: {e}")
        print(f"🔍 Check your BigQuery credentials at: {KEY_BQ_PATH}")
        print(f"🔍 Verify table exists: {PROJECT}.{DATASET_METADATA}.{TBL_CMPGN_TRACKER}")
        return {}

def create_campaign_config_from_db(code_name, db_data):
    """Create a CampaignConfig object from database data"""
    return CampaignConfig(
        code_name=code_name,
        campaign_name=db_data['campaign_name'],
        countries=db_data['countries'],
        type=db_data['type'],
        start_date=db_data['start_date'],
        end_date=db_data['end_date'],
        backend_reports=db_data['backend_reports'],
        time_interval=db_data['time_interval'],
        has_segments=db_data['has_segments'],
        
        # Default values for fields not in database
        segments=[],
        custom_segments={},
        excluded_segments=[],
        controlled_size=50000,
        hg_radius=3000,
    )

def get_database_campaigns():
    """Get all campaigns from database as CampaignConfig objects"""
    db_campaigns = load_campaigns_from_database()
    campaigns = {}
    
    for code_name, db_data in db_campaigns.items():
        campaigns[code_name] = create_campaign_config_from_db(code_name, db_data)
        # Add the status to the campaign object
        campaigns[code_name].status = db_data['status']
    
    return campaigns 