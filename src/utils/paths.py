"""
Path Utilities
==============
Handles path resolution for portable EXE and dev mode.
All data files should use these utilities to ensure consistent paths.
"""

import os
import sys
from pathlib import Path

_app_data_dir = None

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


def get_data_dir() -> Path:
    """
    Get the data directory for storing user data.
    Creates the directory if it doesn't exist.
    """
    global _app_data_dir
    if _app_data_dir is None:
        _app_data_dir = get_app_dir() / "data"
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
