"""
API Base Module
================
Base class with shared state and HTTP client management.
"""

import httpx
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from services.debug_logger import get_logger
from utils.paths import get_cookies_path, get_api_cache_path

logger = get_logger("api.base")


class BaseAPI:
    """
    Base API class with shared state and HTTP client management.
    
    This class provides:
    - HTTP client lifecycle management
    - Cookie storage/retrieval
    - Shared state for authentication
    - Constants and configuration
    """
    
    BASE_URL = "https://api.vrchat.cloud/api/1"
    USER_AGENT = "GroupGuardian/1.0.0 (VRChat Moderation Tool)"
    
    # VRCX-style constants
    PENDING_REQUEST_TTL = 10.0  # seconds - merge duplicate GET requests within this window
    FAILED_REQUEST_TTL = 900.0  # 15 minutes - don't retry 403/404 within this window
    RATE_LIMIT_PER_MINUTE = 60  # requests per minute
    MAX_RETRIES = 5
    BASE_BACKOFF_DELAY = 1.0  # seconds
    
    def __init__(self, cookies_path: str = None):
        # Use centralized path utilities for proper EXE-relative paths
        self._cookies_path = Path(cookies_path) if cookies_path else get_cookies_path()
        self._client: Optional[httpx.AsyncClient] = None
        self._last_request_time: Optional[datetime] = None
        self._min_request_interval = 0.1  # 100ms minimum spacing between requests
        
        # Authentication state
        self._auth_cookie: Optional[str] = None
        self._two_factor_auth_cookie: Optional[str] = None
        self._current_user: Optional[Dict] = None
        self._requires_2fa: bool = False
        self._2fa_type: Optional[str] = None
        
        # VRCX-style request management
        self._pending_requests: Dict[str, Dict] = {}  # URL -> {"task": Task, "time": datetime}
        self._failed_requests: Dict[str, datetime] = {}  # endpoint -> last_fail_time
        self._rate_limiter_stamps: List[datetime] = []  # timestamps of recent requests
        self._request_lock = asyncio.Lock()
        self._api_blocked = asyncio.Event()
        self._api_blocked.set()  # Not blocked initially
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper headers"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "User-Agent": self.USER_AGENT,
                    "Accept": "application/json",
                },
                timeout=30.0,
                follow_redirects=True,
            )
            # Load saved cookies if they exist
            await self._load_cookies()
        return self._client
    
    async def _load_cookies(self):
        """Load saved auth cookies from file"""
        if self._cookies_path.exists():
            try:
                data = json.loads(self._cookies_path.read_text())
                self._auth_cookie = data.get("auth")
                self._two_factor_auth_cookie = data.get("twoFactorAuth")
                logger.info("Loaded saved session cookies")
            except Exception as e:
                logger.warning(f"Could not load cookies: {e}")
    
    async def _save_cookies(self):
        """Save auth cookies to file"""
        try:
            data = {
                "auth": self._auth_cookie,
                "twoFactorAuth": self._two_factor_auth_cookie,
            }
            self._cookies_path.write_text(json.dumps(data))
            logger.info("Saved session cookies")
        except Exception as e:
            logger.warning(f"Could not save cookies: {e}")
    
    def _get_cookies(self) -> Dict[str, str]:
        """Get cookies dict for requests"""
        cookies = {}
        if self._auth_cookie:
            cookies["auth"] = self._auth_cookie
        if self._two_factor_auth_cookie:
            cookies["twoFactorAuth"] = self._two_factor_auth_cookie
        return cookies
    
    def _extract_cookies(self, response: httpx.Response):
        """Extract auth cookies from response"""
        for cookie_name, cookie_value in response.cookies.items():
            if cookie_name == "auth":
                self._auth_cookie = cookie_value
                logger.debug("Got auth cookie")
            elif cookie_name == "twoFactorAuth":
                self._two_factor_auth_cookie = cookie_value
                logger.debug("Got 2FA cookie")
    
    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    @property
    def is_authenticated(self) -> bool:
        """Check if currently authenticated"""
        return self._current_user is not None
    
    @property
    def current_user(self) -> Optional[Dict]:
        """Get current user info"""
        return self._current_user
    
    @property
    def requires_2fa(self) -> bool:
        """Check if 2FA is required"""
        return self._requires_2fa
    
    @property
    def two_factor_type(self) -> Optional[str]:
        """Get the type of 2FA required"""
        return self._2fa_type
