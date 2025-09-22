#!/usr/bin/env python3
"""
Segments Main Script - Updated Version
Uses shared configuration instead of input.py files
"""
import sys
import os
import argparse
from pathlib import Path

# Add project root to path for shared imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.utils.compatibility import setup_shared_imports, inject_campaign_variables
from shared.config.campaigns import get_campaign, list_campaigns

# Setup shared imports
setup_shared_imports()

# Import the existing scripts (they will use injected variables)
from projects.segments.scripts.reset_folders import reset_folders
from projects.segments.scripts.get_segments_raw import get_raw_segments
from projects.segments.scripts.split_segments import split_files, move_without_splitting
from projects.segments.scripts.transfer_to_drive import transfer_files_to_drive
from projects.segments.scripts.push_to_bq import run_push_to_bq
from projects.segments.scripts.authenticate_to_cloud import authenticate_get_clients
from projects.segments.scripts.create_be_table import create_BER_Table

def main(campaign_code_name=None):
    """
    Main function for segment processing
    
    Args:
        campaign_code_name: Campaign code name (e.g., "143")
    """
    # Parse command line arguments if not provided
    if campaign_code_name is None:
        parser = argparse.ArgumentParser(description='Process campaign segments')
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
    
    print(f"🚀 Starting segment processing for campaign: {campaign_code_name}")
    
    try:
        # Get campaign configuration
        campaign = get_campaign(campaign_code_name)
        print(f"📋 Campaign: {campaign.campaign_name}")
        print(f"🌍 Countries: {', '.join(campaign.countries)}")
        print(f"🎯 Segments: {', '.join(campaign.segments)}")
        
        # Inject campaign variables into global namespace for compatibility
        inject_campaign_variables(campaign_code_name, globals())
        
        # Authenticate with cloud services
        print("🔐 Authenticating with cloud services...")
        bq_client, drive_service = authenticate_get_clients()
        
        # Reset folders
        print("🗂️  Resetting data folders...")
        reset_folders()
        
        # Get raw segments
        print("📊 Getting raw segments...")
        get_raw_segments(countries, segments, bq_client)
        
        # Process segments (choose one)
        print("⚙️  Processing segments...")
        # Option 1: Split files (default)
        split_files()
        
        # Option 2: Move without splitting (uncomment to use)
        # move_without_splitting()
        
        # Transfer to drive
        print("☁️  Transferring files to Google Drive...")
        segment_dict = transfer_files_to_drive()
        
        # Push to BigQuery
        print("📤 Pushing segments to BigQuery...")
        run_push_to_bq(segment_dict, bq_client)
        
        # Create BER table
        print("📋 Creating BER table...")
        create_BER_Table(code_name, bq_client)
        
        print(f"✅ Segment processing completed successfully for campaign {campaign_code_name}")
        
    except Exception as e:
        print(f"❌ Error processing campaign {campaign_code_name}: {e}")
        raise

if __name__ == "__main__":
    main() 