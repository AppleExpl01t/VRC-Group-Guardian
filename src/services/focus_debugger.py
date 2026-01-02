"""
Focus Debugger - Specialized logging for input focus issues
=============================================================
This module provides extremely detailed logging for diagnosing
why text input fields lose focus after each keystroke.

Logs to separate file: data/logs/FOCUS_DEBUG.txt
"""

import logging
import os
import sys
from pathlib import Path
from datetime import datetime
import traceback
import threading

# Create dedicated focus logger
_focus_logger = None

def _get_focus_log_path() -> Path:
    """Get path for focus debug log"""
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent.parent.parent
    
    log_dir = base_dir / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "FOCUS_DEBUG.txt"

def init_focus_debugger():
    """Initialize the focus debugger with its own file handler"""
    global _focus_logger
    
    if _focus_logger:
        return _focus_logger
    
    log_path = _get_focus_log_path()
    
    # Create logger
    _focus_logger = logging.getLogger("focus_debug")
    _focus_logger.setLevel(logging.DEBUG)
    _focus_logger.propagate = False  # Don't propagate to root logger
    
    # Remove existing handlers
    for h in _focus_logger.handlers[:]:
        _focus_logger.removeHandler(h)
    
    # Create file handler
    handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    handler.setLevel(logging.DEBUG)
    
    # Detailed format with thread info
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d | %(levelname)-5s | T:%(thread)d | %(message)s',
        datefmt='%H:%M:%S'
    )
    handler.setFormatter(formatter)
    _focus_logger.addHandler(handler)
    
    _focus_logger.info("=" * 80)
    _focus_logger.info("FOCUS DEBUGGER INITIALIZED")
    _focus_logger.info(f"Log file: {log_path}")
    _focus_logger.info(f"Start time: {datetime.now()}")
    _focus_logger.info("=" * 80)
    
    return _focus_logger

def get_focus_logger():
    """Get the focus debug logger"""
    global _focus_logger
    if not _focus_logger:
        init_focus_debugger()
    return _focus_logger

# Convenience functions
def log_page_update(source: str, extra: str = ""):
    """Log when page.update() is called"""
    log = get_focus_logger()
    stack = ''.join(traceback.format_stack()[-4:-1])
    log.warning(f"📱 PAGE.UPDATE called from [{source}] {extra}")
    log.debug(f"   Call stack:\n{stack}")

def log_control_update(control_type: str, control_key: str = "", extra: str = ""):
    """Log when a specific control's update() is called"""
    log = get_focus_logger()
    log.info(f"🔄 CONTROL.UPDATE: {control_type} key={control_key} {extra}")

def log_text_change(field_key: str, old_val: str, new_val: str):
    """Log text field changes"""
    log = get_focus_logger()
    log.info(f"⌨️  TEXT_CHANGE: {field_key} '{old_val}' -> '{new_val}'")

def log_focus_event(field_key: str, event_type: str):
    """Log focus events"""
    log = get_focus_logger()
    log.info(f"🎯 FOCUS: {event_type} on {field_key}")

def log_view_rebuild(view_name: str, reason: str = ""):
    """Log when a view is rebuilt"""
    log = get_focus_logger()
    log.error(f"🏗️  VIEW REBUILD: {view_name} reason={reason}")
    stack = ''.join(traceback.format_stack()[-5:-1])
    log.debug(f"   Call stack:\n{stack}")

def log_event(source: str, event_type: str, data: str = ""):
    """Log general events"""
    log = get_focus_logger()
    log.debug(f"📣 EVENT [{source}] {event_type}: {data}")

def log_warning(message: str):
    """Log a warning"""
    log = get_focus_logger()
    log.warning(f"⚠️  {message}")

def log_info(message: str):
    """Log info"""
    log = get_focus_logger()
    log.info(message)
