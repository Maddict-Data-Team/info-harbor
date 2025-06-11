"""
Campaign data model for Info-Harbor
Unified configuration model that replaces separate input.py files
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class CustomSegment:
    """Custom segment configuration"""
    type: str
    radius: int
    General_Category: Optional[List[str]] = None
    Category: Optional[List[str]] = None
    Subcategory: Optional[List[str]] = None
    GM_Subcategory: Optional[List[str]] = None
    Chain: Optional[List[str]] = None

@dataclass
class CampaignConfig:
    """
    Unified campaign configuration
    Combines all settings from segments/input.py, campaign-tracker/input.py
    """
    # Basic Campaign Info
    code_name: str
    campaign_name: str
    countries: List[str]
    
    # Segment Configuration
    segments: List[str] = field(default_factory=list)
    custom_segments: Dict[str, CustomSegment] = field(default_factory=dict)
    excluded_segments: List[str] = field(default_factory=list)
    controlled_size: int = 50000
    hg_radius: int = 3000
    
    # Campaign Tracker Configuration
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    type: str = "Placelift"
    backend_reports: List[int] = field(default_factory=list)
    time_interval: int = -1
    has_segments: int = 0
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Post-initialization validation and setup"""
        if not self.backend_reports:
            self.backend_reports = [0] * len(self.countries)
        elif len(self.backend_reports) != len(self.countries):
            # Pad or truncate to match countries length
            if len(self.backend_reports) < len(self.countries):
                self.backend_reports.extend([0] * (len(self.countries) - len(self.backend_reports)))
            else:
                self.backend_reports = self.backend_reports[:len(self.countries)]
        
        # Convert custom_segments dict to CustomSegment objects if needed
        for name, config in self.custom_segments.items():
            if isinstance(config, dict):
                self.custom_segments[name] = CustomSegment(**config)
    
    @classmethod
    def from_legacy_inputs(cls, segments_input: dict, tracker_input: dict = None):
        """Create CampaignConfig from legacy input.py dictionaries"""
        config = cls(
            code_name=segments_input.get('code_name', ''),
            campaign_name=segments_input.get('campaign_name', ''),
            countries=segments_input.get('countries', []),
            segments=segments_input.get('segments', []),
            excluded_segments=segments_input.get('excluded_segments', []),
            controlled_size=segments_input.get('controlled_size', 50000),
            hg_radius=segments_input.get('hg_radius', 3000),
        )
        
        # Handle custom segments
        custom_segments_dict = segments_input.get('dict_custom_segments', {})
        for name, segment_config in custom_segments_dict.items():
            config.custom_segments[name] = CustomSegment(**segment_config)
        
        # Add tracker configuration if provided
        if tracker_input:
            config.start_date = tracker_input.get('start_date')
            config.end_date = tracker_input.get('end_date')
            config.type = tracker_input.get('type', 'Placelift')
            config.backend_reports = tracker_input.get('backend_reports', [])
            config.time_interval = tracker_input.get('time_interval', -1)
            config.has_segments = tracker_input.get('has_segments', 0)
        
        return config
    
    def to_segments_input(self) -> dict:
        """Convert to legacy segments input format"""
        custom_segments_dict = {}
        for name, segment in self.custom_segments.items():
            segment_dict = {
                'type': segment.type,
                'radius': segment.radius
            }
            for field_name in ['General_Category', 'Category', 'Subcategory', 'GM_Subcategory', 'Chain']:
                value = getattr(segment, field_name)
                if value is not None:
                    segment_dict[field_name] = value
            custom_segments_dict[name] = segment_dict
        
        return {
            'code_name': self.code_name,
            'campaign_name': self.campaign_name,
            'countries': self.countries,
            'segments': self.segments,
            'dict_custom_segments': custom_segments_dict,
            'excluded_segments': self.excluded_segments,
            'controlled_size': self.controlled_size,
            'hg_radius': self.hg_radius,
        }
    
    def to_tracker_input(self) -> dict:
        """Convert to legacy campaign tracker input format"""
        return {
            'campaign_name': self.campaign_name,
            'countries': self.countries,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'type': self.type,
            'backend_reports': self.backend_reports,
            'time_interval': self.time_interval,
            'has_segments': self.has_segments,
        }
    
    def validate(self) -> List[str]:
        """Validate campaign configuration and return list of errors"""
        errors = []
        
        if not self.code_name:
            errors.append("code_name is required")
        
        if not self.campaign_name:
            errors.append("campaign_name is required")
        
        if not self.countries:
            errors.append("At least one country is required")
        
        if self.controlled_size <= 0:
            errors.append("controlled_size must be positive")
        
        if self.hg_radius <= 0:
            errors.append("hg_radius must be positive")
        
        # Validate custom segments
        for name, segment in self.custom_segments.items():
            if not segment.type:
                errors.append(f"Custom segment '{name}' missing type")
            if segment.radius <= 0:
                errors.append(f"Custom segment '{name}' radius must be positive")
        
        return errors 