"""
Campaign Registry for Info-Harbor
Central registry for all campaign configurations
Loads campaigns from BigQuery database with fallback to hardcoded configs
"""
from .campaign_143_adnoc import CAMPAIGN_143_ADNOC
from .campaign_144_retail import CAMPAIGN_144_RETAIL
from .campaign_145_ooh import CAMPAIGN_145_OOH

# Hardcoded Campaign Registry - Fallback if database is unavailable
HARDCODED_CAMPAIGNS = {
    "143": CAMPAIGN_143_ADNOC,
    "144": CAMPAIGN_144_RETAIL,
    "145": CAMPAIGN_145_OOH,
}

# Global campaigns cache
_campaigns_cache = None

def _load_campaigns():
    """Load campaigns from database with fallback to hardcoded"""
    global _campaigns_cache
    
    if _campaigns_cache is not None:
        return _campaigns_cache
    
    try:
        # Try to load from database first
        from .database_loader import get_database_campaigns
        db_campaigns = get_database_campaigns()
        
        if db_campaigns:
            print(f"✅ Loaded {len(db_campaigns)} campaigns from database")
            _campaigns_cache = db_campaigns
            return _campaigns_cache
        else:
            print("⚠️ No campaigns found in database, using hardcoded fallback")
            
    except Exception as e:
        print(f"❌ Error loading campaigns from database: {e}")
        print("🔄 Falling back to hardcoded campaigns")
    
    # Fallback to hardcoded campaigns
    _campaigns_cache = HARDCODED_CAMPAIGNS
    return _campaigns_cache

def get_campaign(code_name: str):
    """Get campaign configuration by code name"""
    campaigns = _load_campaigns()
    if code_name not in campaigns:
        raise ValueError(f"Campaign {code_name} not found. Available campaigns: {list(campaigns.keys())}")
    return campaigns[code_name]

def list_campaigns():
    """List all available campaign code names"""
    campaigns = _load_campaigns()
    return list(campaigns.keys())

def add_campaign(campaign_config):
    """Add a new campaign to the registry"""
    campaigns = _load_campaigns()
    campaigns[campaign_config.code_name] = campaign_config

def refresh_campaigns():
    """Refresh campaigns cache from database"""
    global _campaigns_cache
    _campaigns_cache = None
    return _load_campaigns() 