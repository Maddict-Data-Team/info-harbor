#!/usr/bin/env python3
"""
Info-Harbor Campaign Manager
Command-line tool to manage campaigns and run different components
"""
import sys
import argparse
from pathlib import Path

# Add project root to path for shared imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.utils.compatibility import setup_shared_imports
from shared.config.campaigns import get_campaign, list_campaigns, add_campaign
from shared.models.campaign import CampaignConfig, CustomSegment

# Setup shared imports
setup_shared_imports()

def list_campaigns_cmd():
    """List all available campaigns"""
    campaigns = list_campaigns()
    if not campaigns:
        print("No campaigns found.")
        return
    
    print("📋 Available Campaigns:")
    print("-" * 50)
    for code in campaigns:
        campaign = get_campaign(code)
        print(f"Code: {code}")
        print(f"  Name: {campaign.campaign_name}")
        print(f"  Countries: {', '.join(campaign.countries)}")
        print(f"  Type: {campaign.type}")
        if campaign.start_date:
            print(f"  Period: {campaign.start_date} to {campaign.end_date}")
        print()

def show_campaign_cmd(code_name):
    """Show detailed campaign information"""
    try:
        campaign = get_campaign(code_name)
        print(f"📋 Campaign Details: {code_name}")
        print("=" * 50)
        print(f"Name: {campaign.campaign_name}")
        print(f"Countries: {', '.join(campaign.countries)}")
        print(f"Type: {campaign.type}")
        
        if campaign.start_date:
            print(f"Start Date: {campaign.start_date}")
            print(f"End Date: {campaign.end_date}")
        
        print(f"Controlled Size: {campaign.controlled_size:,}")
        print(f"HG Radius: {campaign.hg_radius}")
        print(f"Time Interval: {campaign.time_interval}")
        
        if campaign.segments:
            print(f"\nSegments ({len(campaign.segments)}):")
            for segment in campaign.segments:
                print(f"  • {segment}")
        
        if campaign.custom_segments:
            print(f"\nCustom Segments ({len(campaign.custom_segments)}):")
            for name, segment in campaign.custom_segments.items():
                print(f"  • {name}")
                print(f"    Type: {segment.type}, Radius: {segment.radius}")
                if segment.Category:
                    print(f"    Category: {', '.join(segment.Category)}")
                if segment.General_Category:
                    print(f"    General Category: {', '.join(segment.General_Category)}")
                if segment.Chain:
                    print(f"    Chain: {', '.join(segment.Chain)}")
        
        if campaign.excluded_segments:
            print(f"\nExcluded Segments: {', '.join(campaign.excluded_segments)}")
        
        print(f"\nBackend Reports: {campaign.backend_reports}")
        
        # Validation
        errors = campaign.validate()
        if errors:
            print(f"\n⚠️  Validation Issues:")
            for error in errors:
                print(f"  • {error}")
        else:
            print(f"\n✅ Campaign configuration is valid")
            
    except ValueError as e:
        print(f"❌ Error: {e}")

def run_segments_cmd(code_name):
    """Run segments processing for a campaign"""
    try:
        print(f"🚀 Running segments processing for campaign: {code_name}")
        
        # Import and run the new segments main
        from projects.segments.main_new import main as segments_main
        segments_main(code_name)
        
    except Exception as e:
        print(f"❌ Error running segments: {e}")
        raise

def run_tracker_cmd(code_name):
    """Run campaign tracker for a campaign"""
    try:
        print(f"🚀 Running campaign tracker for campaign: {code_name}")
        
        # Import and run the new tracker main
        from projects.campaign_tracker.main_new import main as tracker_main
        tracker_main(code_name)
        
    except Exception as e:
        print(f"❌ Error running tracker: {e}")
        raise

def run_automation_cmd():
    """Run automation process"""
    try:
        print(f"🚀 Running automation process...")
        
        # Import and run the automation main
        from projects.automation.main import main as automation_main
        automation_main()
        
    except Exception as e:
        print(f"❌ Error running automation: {e}")
        raise

def validate_campaign_cmd(code_name):
    """Validate a campaign configuration"""
    try:
        campaign = get_campaign(code_name)
        errors = campaign.validate()
        
        if errors:
            print(f"❌ Campaign {code_name} has validation errors:")
            for error in errors:
                print(f"  • {error}")
            return False
        else:
            print(f"✅ Campaign {code_name} is valid")
            return True
            
    except ValueError as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description='Info-Harbor Campaign Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                    # List all campaigns
  %(prog)s show 143               # Show campaign 143 details
  %(prog)s segments 143           # Run segments for campaign 143
  %(prog)s tracker 143            # Run tracker for campaign 143
  %(prog)s automation             # Run automation process
  %(prog)s validate 143           # Validate campaign 143
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    subparsers.add_parser('list', help='List all campaigns')
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show campaign details')
    show_parser.add_argument('campaign', help='Campaign code name')
    
    # Segments command
    segments_parser = subparsers.add_parser('segments', help='Run segments processing')
    segments_parser.add_argument('campaign', help='Campaign code name')
    
    # Tracker command
    tracker_parser = subparsers.add_parser('tracker', help='Run campaign tracker')
    tracker_parser.add_argument('campaign', help='Campaign code name')
    
    # Automation command
    subparsers.add_parser('automation', help='Run automation process')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate campaign')
    validate_parser.add_argument('campaign', help='Campaign code name')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'list':
            list_campaigns_cmd()
        elif args.command == 'show':
            show_campaign_cmd(args.campaign)
        elif args.command == 'segments':
            run_segments_cmd(args.campaign)
        elif args.command == 'tracker':
            run_tracker_cmd(args.campaign)
        elif args.command == 'automation':
            run_automation_cmd()
        elif args.command == 'validate':
            validate_campaign_cmd(args.campaign)
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 