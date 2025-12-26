"""
Path Utilities
==============
Handles path resolution for portable EXE and dev mode.
All data files should use these utilities to ensure consistent paths.

The data folder location is configurable by the user on first launch.
Default: Documents/VRCGG
"""

import os
import sys
import json
from pathlib import Path

# Cached paths
_app_data_dir = None
_config_loaded = False

# Config file is always stored next to the EXE (or in project root for dev)
def get_app_dir() -> Path:
    """
    Get the application directory.
    - For frozen EXE: Directory containing the EXE
    - For dev mode: Project root (parent of src/)
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE
        return Path(sys.executable).parent
    else:
        # Running in dev mode - go up from utils/ to src/ to project root
        return Path(__file__).parent.parent.parent


def get_config_path() -> Path:
    """Get path to the app config file (stores data folder location)."""
    return get_app_dir() / "vrcgg_config.json"


def get_default_data_dir() -> Path:
    """Get the default data directory (Documents/VRCGG)."""
    # Use user's Documents folder
    if sys.platform == "win32":
        documents = Path(os.environ.get("USERPROFILE", "")) / "Documents"
    else:
        documents = Path.home() / "Documents"
    
    return documents / "VRCGG"


def load_config() -> dict:
    """Load app configuration from config file."""
    config_path = get_config_path()
    if config_path.exists():
        try:
            return json.loads(config_path.read_text())
        except:
            pass
    return {}


def save_config(config: dict):
    """Save app configuration to config file."""
    config_path = get_config_path()
    try:
        config_path.write_text(json.dumps(config, indent=2))
    except Exception as e:
        print(f"Failed to save config: {e}")


def is_data_folder_configured() -> bool:
    """Check if the data folder has been configured by the user."""
    config = load_config()
    return "data_folder" in config and config["data_folder"]


def set_data_folder(path: str):
    """Set the data folder location."""
    global _app_data_dir
    
    config = load_config()
    config["data_folder"] = str(path)
    save_config(config)
    
    # Update cached path
    _app_data_dir = Path(path)
    _app_data_dir.mkdir(parents=True, exist_ok=True)


def get_data_dir() -> Path:
    """
    Get the data directory for storing user data.
    Creates the directory if it doesn't exist.
    """
    global _app_data_dir
    
    if _app_data_dir is None:
        config = load_config()
        
        if "data_folder" in config and config["data_folder"]:
            _app_data_dir = Path(config["data_folder"])
        else:
            # Use default - Documents/VRCGG
            _app_data_dir = get_default_data_dir()
        
        _app_data_dir.mkdir(parents=True, exist_ok=True)
    
    return _app_data_dir


def get_cache_dir() -> Path:
    """Get the cache directory for temporary files like images."""
    cache_dir = get_data_dir() / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_image_cache_dir() -> Path:
    """Get the image cache directory."""
    img_dir = get_cache_dir() / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    return img_dir


def get_logs_dir() -> Path:
    """Get the logs directory."""
    logs_dir = get_data_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_cookies_path() -> Path:
    """Get the path to the cookies file."""
    return get_data_dir() / "cookies.json"


def get_api_cache_path() -> Path:
    """Get the path to the API cache file."""
    return get_data_dir() / "api_cache.json"


def get_database_path() -> Path:
    """Get the path to the SQLite database file."""
    return get_data_dir() / "group_guardian.db"
