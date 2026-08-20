#!/usr/bin/env python3
"""
Info-Harbor Campaign Manager Web UI
Flask web application for managing campaigns
"""
import sys
import os
import json
import hmac
import traceback
from functools import wraps
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash

# Add project root to path for shared imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.utils.compatibility import setup_shared_imports
from shared.config.campaigns.database_loader import get_database_campaigns
from shared.models.campaign import CampaignConfig, CustomSegment

# Setup shared imports
setup_shared_imports()

app = Flask(__name__)

# IH-027: the Flask secret key (used for session signing -- flash()
# messages ride on Flask's session cookie) must come from the
# environment, never be hardcoded, and never fall back to a value
# generated fresh on each process start (that would silently invalidate
# every in-flight session/flash message on every restart, masking the
# real problem: no key was configured). If this app is ever run without
# INFO_HARBOR_FLASK_SECRET_KEY set, refuse to start rather than either
# of those.
FLASK_SECRET_KEY_ENV_VAR = "INFO_HARBOR_FLASK_SECRET_KEY"
_flask_secret_key = os.environ.get(FLASK_SECRET_KEY_ENV_VAR)
if not _flask_secret_key:
    raise RuntimeError(
        f"{FLASK_SECRET_KEY_ENV_VAR} is not set. This app uses Flask "
        "sessions (flash() messages ride on the session cookie), so it "
        "cannot start without a real secret key -- refusing to fall "
        "back to a hardcoded value or a freshly-generated random one "
        "(IH-027). Set it in the deployment environment before running "
        "this app."
    )
app.secret_key = _flask_secret_key

# IH-025: bearer-token auth for every state-changing route. Interim
# internal-control mechanism -- see README.md for the operational note
# and docs/code-audit.md IH-025 for the full route classification and
# rationale.
API_TOKEN_ENV_VAR = "INFO_HARBOR_API_TOKEN"


def _get_expected_api_token():
    # Read fresh on every request, not cached at import time, so a token
    # set or rotated after the process starts is picked up without a
    # restart.
    return os.environ.get(API_TOKEN_ENV_VAR, "")


def require_api_token(view_func):
    """Require `Authorization: Bearer <token>` matching
    INFO_HARBOR_API_TOKEN. Fails closed: if the env var is unset or
    empty, every wrapped route rejects every request with 401 -- there
    is no "no token configured, allow everything" fallback. Uses
    hmac.compare_digest for the comparison. Never logs, echoes, or
    otherwise reveals the configured or submitted token, and never
    distinguishes "no token configured" from "wrong token supplied" in
    the response, so the error itself can't be used to probe deployment
    state.
    """

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        expected = _get_expected_api_token()
        auth_header = request.headers.get("Authorization", "")

        provided = None
        if auth_header.startswith("Bearer "):
            provided = auth_header[len("Bearer "):]

        if not expected or not provided or not hmac.compare_digest(provided, expected):
            return jsonify({
                "success": False,
                "error": "Unauthorized: a valid Authorization: Bearer <token> header is required."
            }), 401

        return view_func(*args, **kwargs)

    return wrapped

def get_live_campaigns():
    """Get live campaigns from database"""
    try:
        return get_database_campaigns()
    except Exception as e:
        print(f"Error loading live campaigns: {e}")
        # Fallback to cached system if database fails
        from shared.config.campaigns import list_campaigns as fallback_list, get_campaign as fallback_get
        fallback_codes = fallback_list()
        fallback_campaigns = {}
        for code in fallback_codes:
            try:
                fallback_campaigns[code] = fallback_get(code)
            except Exception as fallback_error:
                print(f"Error loading fallback campaign {code}: {fallback_error}")
        return fallback_campaigns

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        campaigns = get_live_campaigns()
        campaign_data = []
        
        for code, campaign in campaigns.items():
            try:
                campaign_data.append({
                    'code': code,
                    'name': campaign.campaign_name,
                    'countries': ', '.join(campaign.countries),
                    'type': campaign.type,
                    'start_date': campaign.start_date,
                    'end_date': campaign.end_date,
                    'status': getattr(campaign, 'status', 'Unknown')
                })
            except Exception as e:
                print(f"Error processing campaign {code}: {e}")
                
        return render_template('index.html', campaigns=campaign_data)
    except Exception as e:
        flash(f'Error loading campaigns: {str(e)}', 'error')
        return render_template('index.html', campaigns=[])

@app.route('/documentation')
def documentation():
    """Documentation page"""
    return render_template('documentation.html')

@app.route('/campaign-tracker')
def campaign_tracker():
    """Campaign tracker page"""
    return render_template('campaign_tracker.html')

@app.route('/campaign/<code>')
def campaign_detail(code):
    """Campaign detail page"""
    try:
        campaigns = get_live_campaigns()
        
        if code not in campaigns:
            flash(f'Campaign {code} not found', 'error')
            return redirect(url_for('index'))
            
        campaign = campaigns[code]
        
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
    except Exception as e:
        flash(f'Error loading campaign: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/campaign/<code>/run/<action>', methods=['POST'])
@require_api_token
def run_campaign_action(code, action):
    """Run campaign actions (segments, tracker, etc.)"""
    try:
        if action == 'segments':
            from projects.segments.main_new import main as segments_main
            segments_main(code)
            flash(f'Segments processing completed for campaign {code}', 'success')
            
        elif action == 'tracker':
            from shared.utils.compatibility import get_campaign_tracker_main_new
            tracker_main = get_campaign_tracker_main_new()
            tracker_main(code)
            flash(f'Campaign tracker completed for campaign {code}', 'success')
            
        elif action == 'validate':
            campaigns = get_live_campaigns()
            if code not in campaigns:
                flash(f'Campaign {code} not found', 'error')
            else:
                campaign = campaigns[code]
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

@app.route('/api/campaign/<code>/run/<action>', methods=['POST'])
@require_api_token
def api_run_campaign_action(code, action):
    """API endpoint to run campaign actions (segments, tracker, etc.)"""
    try:
        if action == 'segments':
            from projects.segments.main_new import main as segments_main
            segments_main(code)
            return jsonify({'success': True, 'message': f'Segments processing completed for campaign {code}'})
            
        elif action == 'tracker':
            from shared.utils.compatibility import get_campaign_tracker_main_new
            tracker_main = get_campaign_tracker_main_new()
            tracker_main(code)
            return jsonify({'success': True, 'message': f'Campaign tracker completed for campaign {code}'})
            
        elif action == 'validate':
            campaigns = get_live_campaigns()
            if code not in campaigns:
                return jsonify({'success': False, 'error': f'Campaign {code} not found'}), 404
            else:
                campaign = campaigns[code]
                errors = campaign.validate()
                if errors:
                    return jsonify({'success': False, 'error': f'Campaign {code} has validation errors: {", ".join(errors)}'})
                else:
                    return jsonify({'success': True, 'message': f'Campaign {code} is valid'})
                
        else:
            return jsonify({'success': False, 'error': f'Unknown action: {action}'}), 400
            
    except Exception as e:
        print(f"Error details: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': f'Error running {action} for campaign {code}: {str(e)}'}), 500

@app.route('/api/run-all-trackers', methods=['POST'])
@require_api_token
def api_run_all_trackers():
    """API endpoint to run trackers for all campaigns"""
    try:
        campaigns = get_live_campaigns()
        results = []
        
        for code in campaigns.keys():
            try:
                from shared.utils.compatibility import get_campaign_tracker_main_new
                tracker_main = get_campaign_tracker_main_new()
                tracker_main(code)
                results.append({'code': code, 'status': 'success'})
            except Exception as e:
                results.append({'code': code, 'status': 'error', 'error': str(e)})
        
        success_count = len([r for r in results if r['status'] == 'success'])
        error_count = len([r for r in results if r['status'] == 'error'])
        
        return jsonify({
            'success': True,
            'message': f'Completed trackers for {len(campaigns)} campaigns. {success_count} successful, {error_count} failed.',
            'results': results
        })
        
    except Exception as e:
        print(f"Error details: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': f'Error running all trackers: {str(e)}'}), 500

@app.route('/api/campaigns/add', methods=['POST'])
@require_api_token
def api_add_campaign():
    """API endpoint to add new campaign to database"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        campaign_name = data.get('campaign_name')
        
        if not campaign_name:
            return jsonify({'success': False, 'error': 'Campaign name is required'}), 400
        
        # Generate campaign code automatically
        campaigns = get_live_campaigns()
        existing_codes = [int(code) for code in campaigns.keys() if code.isdigit()]
        campaign_code = str(max(existing_codes) + 1) if existing_codes else "143"
        
        # Create new campaign configuration
        from shared.models.campaign import CampaignConfig
        
        new_campaign = CampaignConfig(
            campaign_name=campaign_name,
            countries=data.get('countries', []),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            type=data.get('type', 'Placelift'),
            controlled_size=data.get('controlled_size', 1000),
            hg_radius=data.get('hg_radius', 100),
            time_interval=data.get('time_interval', -1),
            segments=data.get('segments', []),
            custom_segments=data.get('custom_segments', {}),
            excluded_segments=data.get('excluded_segments', []),
            backend_reports=data.get('backend_reports', [0, 0]),
            has_segments=data.get('has_segments', 0)
        )
        
        # Here you would typically save to database
        # For now, we'll just validate and return success
        errors = new_campaign.validate()
        if errors:
            return jsonify({
                'success': False, 
                'error': f'Campaign validation failed: {", ".join(errors)}'
            }), 400
        
        # TODO: Implement actual database save
        # This would involve creating a new campaign configuration file
        # or inserting into the database

        # IH-041: persistence above is not implemented -- the response
        # must say so rather than claiming success for something that
        # didn't happen. 'campaign' is kept (validated, not persisted) so
        # a caller can still see what would have been saved.
        return jsonify({
            'success': False,
            'error': f'Campaign {campaign_code} passed validation, but saving it is not yet implemented.',
            'campaign': {
                'code': campaign_code,
                'name': campaign_name,
                'type': new_campaign.type,
                'countries': new_campaign.countries,
                'start_date': new_campaign.start_date,
                'end_date': new_campaign.end_date,
                'is_valid': True,
                'persisted': False
            }
        }), 501
        
    except Exception as e:
        print(f"Error details: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': f'Error adding campaign: {str(e)}'}), 500

@app.route('/automation', methods=['POST'])
@require_api_token
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
        campaigns = get_live_campaigns()
        campaign_data = []
        
        for code, campaign in campaigns.items():
            try:
                campaign_data.append({
                    'code': code,
                    'name': campaign.campaign_name,
                    'countries': campaign.countries,
                    'type': campaign.type,
                    'start_date': campaign.start_date,
                    'end_date': campaign.end_date,
                    'segments': campaign.segments,
                    'status': getattr(campaign, 'status', 'Unknown'),
                    'is_valid': len(campaign.validate()) == 0
                })
            except Exception as e:
                print(f"Error processing campaign {code}: {e}")
                
        return jsonify({'campaigns': campaign_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/campaign/<code>')
def api_campaign_detail(code):
    """API endpoint to get campaign details"""
    try:
        campaigns = get_live_campaigns()
        
        if code not in campaigns:
            return jsonify({'error': f'Campaign {code} not found'}), 404
            
        campaign = campaigns[code]
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/refresh', methods=['POST'])
def refresh_campaigns():
    """Refresh campaigns from database - now returns live data directly"""
    try:
        campaigns = get_live_campaigns()
        return jsonify({
            'success': True,
            'message': f'Loaded {len(campaigns)} campaigns from database',
            'campaign_count': len(campaigns)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
    
    app.run(debug=False, host='127.0.0.1', port=5000)