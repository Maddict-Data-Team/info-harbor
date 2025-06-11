#!/usr/bin/env python3
"""
Info-Harbor Campaign Manager Web UI
Flask web application for managing campaigns
"""
import sys
import os
import json
import traceback
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash

# Add project root to path for shared imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.utils.compatibility import setup_shared_imports
from shared.config.campaigns import get_campaign, list_campaigns, add_campaign
from shared.models.campaign import CampaignConfig, CustomSegment

# Setup shared imports
setup_shared_imports()

app = Flask(__name__)
app.secret_key = 'info-harbor-secret-key-2024'

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        campaigns = list_campaigns()
        campaign_data = []
        
        for code in campaigns:
            try:
                campaign = get_campaign(code)
                campaign_data.append({
                    'code': code,
                    'name': campaign.campaign_name,
                    'countries': ', '.join(campaign.countries),
                    'type': campaign.type,
                    'start_date': campaign.start_date,
                    'end_date': campaign.end_date,
                    'status': 'Active' if campaign.start_date and campaign.end_date else 'Draft'
                })
            except Exception as e:
                print(f"Error loading campaign {code}: {e}")
                
        return render_template('index.html', campaigns=campaign_data)
    except Exception as e:
        flash(f'Error loading campaigns: {str(e)}', 'error')
        return render_template('index.html', campaigns=[])

@app.route('/campaign/<code>')
def campaign_detail(code):
    """Campaign detail page"""
    try:
        campaign = get_campaign(code)
        
        # Validate campaign
        errors = campaign.validate()
        
        campaign_data = {
            'code': code,
            'name': campaign.campaign_name,
            'countries': campaign.countries,
            'type': campaign.type,
            'start_date': campaign.start_date,
            'end_date': campaign.end_date,
            'controlled_size': campaign.controlled_size,
            'hg_radius': campaign.hg_radius,
            'time_interval': campaign.time_interval,
            'segments': campaign.segments,
            'custom_segments': campaign.custom_segments,
            'excluded_segments': campaign.excluded_segments,
            'backend_reports': campaign.backend_reports,
            'validation_errors': errors,
            'is_valid': len(errors) == 0
        }
        
        return render_template('campaign_detail.html', campaign=campaign_data)
    except ValueError as e:
        flash(f'Campaign not found: {str(e)}', 'error')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error loading campaign: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/campaign/<code>/run/<action>', methods=['POST'])
def run_campaign_action(code, action):
    """Run campaign actions (segments, tracker, etc.)"""
    try:
        if action == 'segments':
            from projects.segments.main_new import main as segments_main
            segments_main(code)
            flash(f'Segments processing completed for campaign {code}', 'success')
            
        elif action == 'tracker':
            from projects.campaign_tracker.main_new import main as tracker_main
            tracker_main(code)
            flash(f'Campaign tracker completed for campaign {code}', 'success')
            
        elif action == 'validate':
            campaign = get_campaign(code)
            errors = campaign.validate()
            if errors:
                flash(f'Campaign {code} has validation errors: {", ".join(errors)}', 'error')
            else:
                flash(f'Campaign {code} is valid', 'success')
                
        else:
            flash(f'Unknown action: {action}', 'error')
            
    except Exception as e:
        flash(f'Error running {action} for campaign {code}: {str(e)}', 'error')
        print(f"Error details: {traceback.format_exc()}")
    
    return redirect(url_for('campaign_detail', code=code))

@app.route('/automation', methods=['POST'])
def run_automation():
    """Run automation process"""
    try:
        from projects.automation.main import main as automation_main
        automation_main()
        flash('Automation process completed successfully', 'success')
    except Exception as e:
        flash(f'Error running automation: {str(e)}', 'error')
        print(f"Error details: {traceback.format_exc()}")
    
    return redirect(url_for('index'))

@app.route('/api/campaigns')
def api_campaigns():
    """API endpoint to get all campaigns"""
    try:
        campaigns = list_campaigns()
        campaign_data = []
        
        for code in campaigns:
            try:
                campaign = get_campaign(code)
                campaign_data.append({
                    'code': code,
                    'name': campaign.campaign_name,
                    'countries': campaign.countries,
                    'type': campaign.type,
                    'start_date': campaign.start_date,
                    'end_date': campaign.end_date,
                    'segments': campaign.segments,
                    'is_valid': len(campaign.validate()) == 0
                })
            except Exception as e:
                print(f"Error loading campaign {code}: {e}")
                
        return jsonify({'campaigns': campaign_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/campaign/<code>')
def api_campaign_detail(code):
    """API endpoint to get campaign details"""
    try:
        campaign = get_campaign(code)
        errors = campaign.validate()
        
        campaign_data = {
            'code': code,
            'name': campaign.campaign_name,
            'countries': campaign.countries,
            'type': campaign.type,
            'start_date': campaign.start_date,
            'end_date': campaign.end_date,
            'controlled_size': campaign.controlled_size,
            'hg_radius': campaign.hg_radius,
            'time_interval': campaign.time_interval,
            'segments': campaign.segments,
            'custom_segments': {name: {
                'type': seg.type,
                'radius': seg.radius,
                'Category': seg.Category,
                'General_Category': seg.General_Category,
                'Chain': seg.Chain
            } for name, seg in campaign.custom_segments.items()},
            'excluded_segments': campaign.excluded_segments,
            'backend_reports': campaign.backend_reports,
            'validation_errors': errors,
            'is_valid': len(errors) == 0
        }
        
        return jsonify(campaign_data)
    except ValueError as e:
        return jsonify({'error': f'Campaign not found: {str(e)}'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    templates_dir = Path(__file__).parent / 'templates'
    templates_dir.mkdir(exist_ok=True)
    
    # Create static directory if it doesn't exist
    static_dir = Path(__file__).parent / 'static'
    static_dir.mkdir(exist_ok=True)
    
    print("🚀 Starting Info-Harbor Campaign Manager UI...")
    print("📱 Access the web interface at: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000) 