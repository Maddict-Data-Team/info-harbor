"""
Campaign Configuration: ADNOC (Code: 143)
Unified configuration for the ADNOC campaign
"""
from shared.models.campaign import CampaignConfig, CustomSegment

# ADNOC Campaign Configuration
CAMPAIGN_143_ADNOC = CampaignConfig(
    # Basic Campaign Info
    code_name="143",
    campaign_name="ADNOC",
    countries=["UAE"],
    
    # Segment Configuration
    segments=["Hotels and Resorts Frequenters"],
    custom_segments={
        "Custom_QSR Frequenters": CustomSegment(
            type="POI",
            Category=["QSR"],
            radius=50
        ),
        "custom_Foodies": CustomSegment(
            type="POI",
            General_Category=["Food"],
            radius=50
        ),
        "custom_Competitor Car Owners": CustomSegment(
            type="POI",
            General_Category=["Automotive"],
            Chain=["Nissan", "Ford", "Tesla", "Jeep"],
            radius=160
        ),
        "custom_Business": CustomSegment(
            type="POI",
            General_Category=["Business"],
            radius=80
        ),
    },
    excluded_segments=[],
    controlled_size=50000,
    hg_radius=3000,
    
    # Campaign Tracker Configuration
    start_date="2024-11-26",
    end_date="2024-12-20",
    type="Placelift",
    backend_reports=[0],  # One entry per country
    time_interval=-1,
    has_segments=0,
) 