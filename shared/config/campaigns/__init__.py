"""
Campaign Registry for Info-Harbor
Central registry for all campaign configurations
"""
from .campaign_143_adnoc import CAMPAIGN_143_ADNOC
from .campaign_144_retail import CAMPAIGN_144_RETAIL
from .campaign_145_ooh import CAMPAIGN_145_OOH

# Campaign Registry - Add new campaigns here
CAMPAIGNS = {
    "143": CAMPAIGN_143_ADNOC,
    "144": CAMPAIGN_144_RETAIL,
    "145": CAMPAIGN_145_OOH,
}

def get_campaign(code_name: str):
    """Get campaign configuration by code name"""
    if code_name not in CAMPAIGNS:
        raise ValueError(f"Campaign {code_name} not found. Available campaigns: {list(CAMPAIGNS.keys())}")
    return CAMPAIGNS[code_name]

def list_campaigns():
    """List all available campaign code names"""
    return list(CAMPAIGNS.keys())

def add_campaign(campaign_config):
    """Add a new campaign to the registry"""
    CAMPAIGNS[campaign_config.code_name] = campaign_config 