"""
Debug Logging Service
=====================
Comprehensive logging for Group Guardian with:
- Session-based log files (one per app launch)
- Auto-cleanup (keeps only 2 most recent logs)
- PII filtering for auth requests
- Network request logging
- Error tracking
"""

import logging
import os
import sys
import re
import glob
import atexit
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Import version
try:
    from services.updater import UpdateService
    APP_VERSION = UpdateService.CURRENT_VERSION
except:
    APP_VERSION = "unknown"


class PIIFilter(logging.Filter):
    """Filter to redact PII from log messages"""
    
    # Patterns to redact
    PII_PATTERNS = [
        (r'(auth[_-]?token)["\']?\s*[:=]\s*["\']?([^"\'&\s]+)', r'\1=***REDACTED***'),
        (r'(password)["\']?\s*[:=]\s*["\']?([^"\'&\s]+)', r'\1=***REDACTED***'),
        (r'(apiKey|api_key)["\']?\s*[:=]\s*["\']?([^"\'&\s]+)', r'\1=***REDACTED***'),
        (r'(cookie)["\']?\s*[:=]\s*["\']?([^"\'&\s;]+)', r'\1=***REDACTED***'),
        (r'(authorization)["\']?\s*[:=]\s*["\']?([^"\'&\s]+)', r'\1=***REDACTED***'),
        (r'(Bearer\s+)([A-Za-z0-9\-_.]+)', r'\1***REDACTED***'),
        (r'(twoFactorAuth|totp)["\']?\s*[:=]\s*["\']?([^"\'&\s]+)', r'\1=***REDACTED***'),
        (r'(email)["\']?\s*[:=]\s*["\']?([^"\'&\s@]+@[^"\'&\s]+)', r'\1=***REDACTED***'),
        # VRChat specific
        (r'(auth=)([a-zA-Z0-9_-]+)', r'\1***REDACTED***'),
        (r'(twoFactorAuth=)([a-zA-Z0-9_-]+)', r'\1***REDACTED***'),
    ]
    
    def filter(self, record):
        # Redact PII from the message
        msg = record.getMessage()
        for pattern, replacement in self.PII_PATTERNS:
            msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
        record.msg = msg
        record.args = ()
        return True


class DebugLogger:
    """Singleton debug logger for the application"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if DebugLogger._initialized:
            return
        DebugLogger._initialized = True
        
        self.start_time = datetime.now()
        self.log_file_path = None
        self.logger = None
        self.file_handler = None
        
        self._setup_logging()
        atexit.register(self._finalize_log)
    
    def _get_data_dir(self) -> Path:
        """Get the application data directory"""
        if getattr(sys, 'frozen', False):
            # Running as compiled EXE
            base_dir = Path(sys.executable).parent
        else:
            # Running in dev mode
            base_dir = Path(__file__).parent.parent.parent
        
        data_dir = base_dir / "data" / "logs"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    
    def _cleanup_old_logs(self, log_dir: Path, keep_count: int = 2):
        """Remove old log files, keeping only the most recent ones"""
        pattern = str(log_dir / "VRCGG*.txt")
        log_files = glob.glob(pattern)
        
        # Sort by modification time (oldest first)
        log_files.sort(key=os.path.getmtime)
        
        # Remove oldest files if we have too many
        # We subtract 1 because we're about to create a new one
        while len(log_files) >= keep_count:
            oldest = log_files.pop(0)
            try:
                os.remove(oldest)
            except Exception as e:
                print(f"Failed to remove old log: {e}")
    
    def _setup_logging(self):
        """Initialize the logging system"""
        log_dir = self._get_data_dir()
        
        # Clean up old logs (keep only 1, since we're creating 1 more = 2 total)
        self._cleanup_old_logs(log_dir, keep_count=2)
        
        # Create filename with start time (end time added on close)
        start_str = self.start_time.strftime("%m-%d-%y_%H%M")
        self.temp_filename = f"VRCGG{APP_VERSION}-LOG-{start_str}-RUNNING.txt"
        self.log_file_path = log_dir / self.temp_filename
        
        # Configure root logger
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # File handler with PII filter
        self.file_handler = logging.FileHandler(
            self.log_file_path, 
            mode='w', 
            encoding='utf-8'
        )
        self.file_handler.setLevel(logging.DEBUG)
        self.file_handler.addFilter(PIIFilter())
        
        # Detailed format for file
        file_format = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.file_handler.setFormatter(file_format)
        self.logger.addHandler(self.file_handler)
        
        # Console handler (less verbose)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.addFilter(PIIFilter())
        console_format = logging.Formatter('%(levelname)s | %(name)s | %(message)s')
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # Log startup
        self.logger.info("=" * 60)
        self.logger.info(f"GROUP GUARDIAN v{APP_VERSION} - Session Started")
        self.logger.info(f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Log File: {self.log_file_path}")
        self.logger.info(f"Python: {sys.version}")
        self.logger.info(f"Frozen: {getattr(sys, 'frozen', False)}")
        self.logger.info("=" * 60)
        
        # Reduce verbosity for noisy third-party loggers
        logging.getLogger("flet").setLevel(logging.WARNING)
        logging.getLogger("flet_desktop").setLevel(logging.INFO)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("httpcore.http11").setLevel(logging.WARNING)
        logging.getLogger("httpcore.connection").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.INFO)  # Keep HTTP requests visible
        logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    def _finalize_log(self):
        """Rename log file with end time when app closes"""
        if not self.log_file_path or not self.log_file_path.exists():
            return
        
        end_time = datetime.now()
        
        # Log shutdown
        self.logger.info("=" * 60)
        self.logger.info(f"SESSION ENDED")
        self.logger.info(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        duration = end_time - self.start_time
        self.logger.info(f"Duration: {duration}")
        self.logger.info("=" * 60)
        
        # Close the file handler
        if self.file_handler:
            self.file_handler.close()
            self.logger.removeHandler(self.file_handler)
        
        # Rename file with end time
        start_str = self.start_time.strftime("%m-%d-%y_%H%M")
        end_str = end_time.strftime("%H%M")
        final_filename = f"VRCGG{APP_VERSION}-LOG-{start_str}-{end_str}.txt"
        final_path = self.log_file_path.parent / final_filename
        
        try:
            self.log_file_path.rename(final_path)
        except Exception as e:
            print(f"Failed to rename log file: {e}")
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a named logger for a specific module"""
        return logging.getLogger(name)


# Global instance
_debug_logger = None

def init_logging():
    """Initialize the debug logging system. Call this early in app startup."""
    global _debug_logger
    if _debug_logger is None:
        _debug_logger = DebugLogger()
    return _debug_logger

def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module"""
    if _debug_logger is None:
        init_logging()
    return logging.getLogger(name)


# Network logging utilities
def log_request(logger: logging.Logger, method: str, url: str, status: int = None, error: str = None):
    """Log an HTTP request with PII filtering"""
    # Redact auth endpoints
    if any(x in url.lower() for x in ['auth', 'login', 'token', '2fa', 'twofactor']):
        url = re.sub(r'\?.*', '?***PARAMS_REDACTED***', url)
    
    if error:
        logger.error(f"HTTP {method} {url} - ERROR: {error}")
    elif status:
        level = logging.INFO if 200 <= status < 400 else logging.WARNING
        logger.log(level, f"HTTP {method} {url} - {status}")
    else:
        logger.debug(f"HTTP {method} {url} - Sending...")


def log_exception(logger: logging.Logger, exc: Exception, context: str = ""):
    """Log an exception with full traceback"""
    import traceback
    tb = traceback.format_exc()
    logger.error(f"EXCEPTION in {context}: {exc}")
    logger.debug(f"Traceback:\n{tb}")
