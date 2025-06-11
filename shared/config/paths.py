"""
Centralized path configuration for Info-Harbor
Handles all file paths dynamically based on project root
"""
import os
from pathlib import Path

# Get the project root directory (info-harbor/)
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()

# Key files
KEYS_DIR = PROJECT_ROOT / "keys"
KEY_BQ = KEYS_DIR / "maddictdata-bq.json"
KEY_GOOGLE_SHEETS = KEYS_DIR / "maddictdata-google-sheets.json"

# Project directories
PROJECTS_DIR = PROJECT_ROOT / "projects"
SEGMENTS_DIR = PROJECTS_DIR / "segments"
AUTOMATION_DIR = PROJECTS_DIR / "automation"
CAMPAIGN_TRACKER_DIR = PROJECTS_DIR / "campaign-tracker"

# Segments specific paths
SEGMENTS_DATA_DIR = SEGMENTS_DIR / "data"
SEGMENTS_RAW_DIR = SEGMENTS_DATA_DIR / "raw"
SEGMENTS_SERVED_DIR = SEGMENTS_DATA_DIR / "served"
SEGMENTS_CONTROLLED_DIR = SEGMENTS_DATA_DIR / "controlled"
SEGMENTS_SCRIPTS_DIR = SEGMENTS_DIR / "scripts"

# Configuration files
SEGMENTS_QUERIES_INI = SEGMENTS_DIR / "queries.ini"
AUTOMATION_QUERIES_INI = AUTOMATION_DIR / "queries.ini"

# Shared configuration directory
SHARED_CONFIG_DIR = PROJECT_ROOT / "shared" / "config"
CAMPAIGNS_CONFIG_DIR = SHARED_CONFIG_DIR / "campaigns"

def ensure_directories():
    """Create necessary directories if they don't exist"""
    directories = [
        KEYS_DIR,
        SEGMENTS_DATA_DIR,
        SEGMENTS_RAW_DIR,
        SEGMENTS_SERVED_DIR,
        SEGMENTS_CONTROLLED_DIR,
        CAMPAIGNS_CONFIG_DIR
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

def get_relative_path(target_path, from_path=None):
    """Get relative path from current working directory or specified path"""
    if from_path is None:
        from_path = Path.cwd()
    else:
        from_path = Path(from_path)
    
    try:
        return os.path.relpath(target_path, from_path)
    except ValueError:
        # If relative path can't be computed, return absolute path
        return str(target_path)

def verify_file_exists(file_path, description=""):
    """Verify that a file exists and is accessible"""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"{description} not found: {file_path}")
    if not file_path.is_file():
        raise ValueError(f"{description} is not a file: {file_path}")
    return True

def verify_directory_exists(dir_path, description=""):
    """Verify that a directory exists and is accessible"""
    dir_path = Path(dir_path)
    if not dir_path.exists():
        raise FileNotFoundError(f"{description} not found: {dir_path}")
    if not dir_path.is_dir():
        raise ValueError(f"{description} is not a directory: {dir_path}")
    return True

# Verify critical paths on import
def verify_critical_paths():
    """Verify that critical paths exist"""
    try:
        verify_directory_exists(PROJECT_ROOT, "Project root")
        verify_directory_exists(PROJECTS_DIR, "Projects directory")
        verify_directory_exists(SEGMENTS_DIR, "Segments directory")
        
        # Create data directories if they don't exist
        ensure_directories()
        
        # Check for key files (warn if missing but don't fail)
        if not KEY_BQ.exists():
            print(f"WARNING: BigQuery key file missing: {KEY_BQ}")
        if not KEY_GOOGLE_SHEETS.exists():
            print(f"WARNING: Google Sheets key file missing: {KEY_GOOGLE_SHEETS}")
            
        return True
    except Exception as e:
        print(f"Path verification failed: {e}")
        return False

# Run verification on import
_paths_verified = verify_critical_paths() 