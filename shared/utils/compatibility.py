"""
Compatibility layer for Info-Harbor
Provides backward compatibility for existing projects while transitioning to shared config
"""
import sys
import os
from pathlib import Path

# Import shared configuration at module level
from shared.config.base_config import (
    PROJECT, TABLE_MAPPING, DATASET_LS, DATASET_FOOTFALL, DATASET_BERS,
    DATASET_CAMPAIGN_SEGMENTS, DATASET_METADATA, DATASET_HWG, TABLE_HG,
    TABLE_WG, TABLE_HWG_POL_MAP, TBL_CMPGN_TRACKER, TABLE_BEHAVIOR_LOOKUP,
    TABLE_OS_MAPPING, TABLE_PLACELIFT, MAIN_DRIVE_FOLDER_ID,
    FOLDER_ID_BACKEND_REPORTS, DRIVE_LINK_FOLDER_ADOPS, SECRET_BER, SECRET_BQ,
    STAGE_0, STAGE_1, STAGE_2, STAGE_3, STAGE_4, STAGE_5, STAGE_6,
    POI_FILTER_FIELDS, STATIC_QUERY_REPLACE, KEY_BQ_PATH, KEY_GOOGLE_SHEETS_PATH
)
from shared.config.schemas import SCHEMA_DID, SCHEMA_BACK_END, SCHEMA_COMBINED
from shared.config.paths import SEGMENTS_DATA_DIR

# Add shared package to Python path
def setup_shared_imports():
    """Add shared package to sys.path for imports"""
    # Get the project root (info-harbor directory)
    current_file = Path(__file__).absolute()
    project_root = current_file.parent.parent.parent
    
    # Add project root to sys.path if not already there
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

def get_legacy_variables_from_campaign(campaign_config):
    """
    Convert CampaignConfig to legacy variables format
    Returns a dictionary that can be used like the old variables.py files
    """
    # Create legacy variables dictionary
    legacy_vars = {
        # Campaign specific
        'code_name': campaign_config.code_name,
        'campaign_name': campaign_config.campaign_name,
        'countries': campaign_config.countries,
        'segments': campaign_config.segments,
        'dict_custom_segments': campaign_config.to_segments_input()['dict_custom_segments'],
        'excluded_segments': campaign_config.excluded_segments,
        'controlled_size': campaign_config.controlled_size,
        'hg_radius': campaign_config.hg_radius,
        
        # Campaign tracker specific
        'start_date': campaign_config.start_date,
        'end_date': campaign_config.end_date,
        'type': campaign_config.type,
        'backend_reports': campaign_config.backend_reports,
        'time_interval': campaign_config.time_interval,
        'has_segments': campaign_config.has_segments,
        
        # Shared configuration
        'project': PROJECT,
        'table_mapping': TABLE_MAPPING,
        'key_bq': KEY_BQ_PATH,
        'key_google_sheets': KEY_GOOGLE_SHEETS_PATH,
        
        # Datasets
        'dataset_LS': DATASET_LS,
        'dataset_footfall': DATASET_FOOTFALL,
        'dataset_BERs': DATASET_BERS,
        'dataset_campaign_segments': DATASET_CAMPAIGN_SEGMENTS,
        'dataset_metadata': DATASET_METADATA,
        'dataset_HWG': DATASET_HWG,
        
        # Tables
        'table_HG': TABLE_HG,
        'table_WG': TABLE_WG,
        'table_hwg_pol_map': TABLE_HWG_POL_MAP,
        'tbl_cmpgn_tracker': TBL_CMPGN_TRACKER,
        'table_behavior_lookup': TABLE_BEHAVIOR_LOOKUP,
        'table_os_mapping': TABLE_OS_MAPPING,
        'table_placelift': TABLE_PLACELIFT,
        
        # Schemas
        'schema_DID': SCHEMA_DID,
        'schema_back_end': SCHEMA_BACK_END,
        'schema_Combined': SCHEMA_COMBINED,
        
        # Drive configuration
        'MAIN_DRIVE_FOLDER_ID': MAIN_DRIVE_FOLDER_ID,
        'folder_id_Backend_Reports': FOLDER_ID_BACKEND_REPORTS,
        'drive_link_folder_Adops': DRIVE_LINK_FOLDER_ADOPS,
        
        # Secrets
        'secret_ber': SECRET_BER,
        'secret_bq': SECRET_BQ,
        
        # Status stages
        'stage_0': STAGE_0,
        'stage_1': STAGE_1,
        'stage_2': STAGE_2,
        'stage_3': STAGE_3,
        'stage_4': STAGE_4,
        'stage_5': STAGE_5,
        'stage_6': STAGE_6,
        
        # Other
        'poi_filter_fields': POI_FILTER_FIELDS,
        'static_query_replace': STATIC_QUERY_REPLACE,
        
        # Paths (as strings for compatibility)
        'dir_data': str(SEGMENTS_DATA_DIR),
    }
    
    return legacy_vars

def inject_campaign_variables(campaign_code_name, target_globals):
    """
    Inject campaign variables into the target module's globals
    This allows existing code to work without modification
    """
    setup_shared_imports()
    
    from shared.config.campaigns import get_campaign
    
    # Get campaign configuration
    campaign = get_campaign(campaign_code_name)
    
    # Get legacy variables
    legacy_vars = get_legacy_variables_from_campaign(campaign)
    
    # Inject into target globals
    target_globals.update(legacy_vars)
    
    return campaign

def create_legacy_input_module(campaign_code_name):
    """
    Create a module-like object that behaves like the old input.py files
    """
    setup_shared_imports()
    
    from shared.config.campaigns import get_campaign
    
    campaign = get_campaign(campaign_code_name)
    legacy_vars = get_legacy_variables_from_campaign(campaign)
    
    # Create a simple object that allows attribute access
    class LegacyInputModule:
        def __init__(self, variables):
            for key, value in variables.items():
                setattr(self, key, value)
    
    return LegacyInputModule(legacy_vars) 