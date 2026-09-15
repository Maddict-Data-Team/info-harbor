# Info-Harbor - Restructured

> **Superseded (marked 2026-09-15).** This pre-modernization document is
> kept for history only. It is not an accurate description of the current
> system:
> - `test_paths.py` does not exist.
> - Both `main_new.py` entry points failed at import until IH-014 and IH-015 were fixed.
> - Database-loaded campaigns lose their segments (IH-004, open).
>
> For the current state read `docs/PROJECT_STATE.md`; for working rules read `AGENTS.md`.

## 🎯 Overview
Info-Harbor is a comprehensive campaign workflow management system for Maddict, now restructured with a unified configuration system and improved maintainability.

### ✨ What's New in the Restructured Version
- **🔧 Unified Configuration**: Single source of truth for all campaign settings
- **📁 Centralized Paths**: Dynamic path resolution that works from any directory
- **🔄 Backward Compatibility**: Existing scripts work without modification
- **🎮 Command-Line Interface**: Easy-to-use campaign manager
- **✅ Validation**: Built-in configuration validation
- **🏗️ Modular Architecture**: Shared components across all projects

## 📂 New Project Structure

```
info-harbor/
├── shared/                          # 🆕 Shared configuration and utilities
│   ├── config/
│   │   ├── base_config.py          # Common constants and settings
│   │   ├── paths.py                # Dynamic path management
│   │   ├── schemas.py              # BigQuery schemas
│   │   └── campaigns/              # Campaign configurations
│   │       ├── __init__.py         # Campaign registry
│   │       └── campaign_143_adnoc.py
│   ├── models/
│   │   └── campaign.py             # Unified campaign data model
│   └── utils/
│       └── compatibility.py        # Backward compatibility layer
├── projects/
│   ├── segments/
│   │   ├── main_new.py             # 🆕 Updated main script
│   │   └── scripts/                # Existing scripts (unchanged)
│   ├── campaign-tracker/
│   │   ├── main_new.py             # 🆕 Updated main script
│   │   └── ...
│   └── automation/
│       └── ...
├── campaign_manager.py             # 🆕 CLI tool for campaign management
├── test_paths.py                   # 🆕 Verification script
└── README_NEW.md                   # This file
```

## 🚀 Quick Start

### 1. Verify Installation
```bash
# Test that everything is working
python3 test_paths.py
```

### 2. List Available Campaigns
```bash
python3 campaign_manager.py list
```

### 3. View Campaign Details
```bash
python3 campaign_manager.py show 143
```

### 4. Run Campaign Components
```bash
# Run segments processing
python3 campaign_manager.py segments 143

# Run campaign tracker
python3 campaign_manager.py tracker 143

# Run automation
python3 campaign_manager.py automation
```

## 🔧 Configuration Management

### Campaign Configuration
Campaigns are now defined in Python files under `shared/config/campaigns/`:

```python
# shared/config/campaigns/campaign_143_adnoc.py
CAMPAIGN_143_ADNOC = CampaignConfig(
    code_name="143",
    campaign_name="ADNOC",
    countries=["UAE"],
    segments=["Hotels and Resorts Frequenters"],
    custom_segments={
        "Custom_QSR Frequenters": CustomSegment(
            type="POI",
            Category=["QSR"],
            radius=50
        ),
    },
    start_date="2024-11-26",
    end_date="2024-12-20",
    # ... other settings
)
```

### Adding New Campaigns
1. Create a new campaign file in `shared/config/campaigns/`
2. Add it to the registry in `shared/config/campaigns/__init__.py`
3. Use the campaign manager to validate and run

## 🔄 Migration from Legacy System

### For Existing Scripts
The restructured system maintains **100% backward compatibility**. Your existing scripts will work without any changes because:

1. **Automatic Variable Injection**: The compatibility layer injects all required variables
2. **Path Resolution**: Paths are automatically resolved regardless of working directory
3. **Legacy Format Support**: All existing `input.py` formats are supported

### Running Legacy Scripts
```bash
# Old way (still works)
cd projects/segments
python3 main.py

# New way (recommended)
python3 campaign_manager.py segments 143
```

## 📋 Campaign Manager CLI

The new campaign manager provides a unified interface:

```bash
# List all campaigns
python3 campaign_manager.py list

# Show campaign details
python3 campaign_manager.py show <campaign_code>

# Run segments processing
python3 campaign_manager.py segments <campaign_code>

# Run campaign tracker
python3 campaign_manager.py tracker <campaign_code>

# Run automation
python3 campaign_manager.py automation

# Validate campaign configuration
python3 campaign_manager.py validate <campaign_code>
```

## 🔍 Troubleshooting

### Path Issues
If you encounter path-related errors:
```bash
# Run the verification script
python3 test_paths.py
```

### Missing Key Files
The system will warn about missing authentication keys but continue to work:
- `keys/maddictdata-bq.json` - BigQuery authentication
- `keys/maddictdata-google-sheets.json` - Google Sheets authentication

### Import Errors
If you get import errors, ensure you're running from the project root:
```bash
cd /path/to/info-harbor
python3 campaign_manager.py list
```

## 🏗️ Architecture Benefits

### Before (Legacy)
- ❌ Duplicated configuration across projects
- ❌ Hardcoded paths breaking when run from different directories
- ❌ Manual synchronization between projects
- ❌ No validation of configuration
- ❌ Difficult to add new campaigns

### After (Restructured)
- ✅ Single source of truth for configuration
- ✅ Dynamic path resolution
- ✅ Automatic synchronization
- ✅ Built-in validation
- ✅ Easy campaign management
- ✅ Backward compatibility
- ✅ Modular and maintainable

## 🔮 Future Enhancements

The restructured system provides a solid foundation for:

1. **Web UI**: The unified configuration makes it easy to build a web interface
2. **API Integration**: RESTful APIs can be built on top of the campaign models
3. **Advanced Validation**: More sophisticated validation rules
4. **Configuration Templates**: Template-based campaign creation
5. **Automated Testing**: Comprehensive test suites for all components

## 📚 Development Guide

### Adding a New Campaign
1. Create campaign configuration:
```python
# shared/config/campaigns/campaign_XXX_name.py
CAMPAIGN_XXX_NAME = CampaignConfig(
    code_name="XXX",
    campaign_name="Campaign Name",
    # ... configuration
)
```

2. Register in `shared/config/campaigns/__init__.py`:
```python
from .campaign_XXX_name import CAMPAIGN_XXX_NAME

CAMPAIGNS = {
    "143": CAMPAIGN_143_ADNOC,
    "XXX": CAMPAIGN_XXX_NAME,  # Add here
}
```

3. Validate and test:
```bash
python3 campaign_manager.py validate XXX
python3 campaign_manager.py show XXX
```

### Extending the System
- **New Components**: Add to `projects/` directory
- **Shared Utilities**: Add to `shared/utils/`
- **Configuration**: Extend `shared/config/`
- **Models**: Add to `shared/models/`

## 🤝 Contributing

1. Always run tests before committing:
   ```bash
   python3 test_paths.py
   ```

2. Validate campaigns after changes:
   ```bash
   python3 campaign_manager.py validate <campaign_code>
   ```

3. Maintain backward compatibility for existing scripts

## 📄 License

MIT License - Copyright (c) 2024 Maddict Data Team 