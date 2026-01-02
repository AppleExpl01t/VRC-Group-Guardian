"""
VRChat API Client
=================
Main API client that composes all mixins for a complete VRChat API interface.

This is the main entry point for the VRChat API. It combines:
- BaseAPI: HTTP client and shared state
- RequestMixin: Rate limiting and request handling
- AuthMixin: Authentication and session management
- ImagesMixin: Image caching
- UsersMixin: User operations
- GroupsMixin: Group operations
- InvitesMixin: Invite operations
- WorldsMixin: World operations
- CacheMixin: Cached fetch methods
"""

from .base import BaseAPI
from .request_handler import RequestMixin
from .auth import AuthMixin
from .images import ImagesMixin
from .users import UsersMixin
from .groups import GroupsMixin
from .invites import InvitesMixin
from .worlds import WorldsMixin
from .cache import CacheMixin
from services.debug_logger import get_logger

logger = get_logger("api.client")


class VRChatAPI(
    BaseAPI,
    RequestMixin,
    AuthMixin,
    ImagesMixin,
    UsersMixin,
    GroupsMixin,
    InvitesMixin,
    WorldsMixin,
    CacheMixin,
):
    """
    VRChat API Client with VRCX-style request handling:
    
    1. Request Deduplication - Pending GET requests are cached for 10s
    2. Failed Request Cache - 403/404 errors are cached for 15min to avoid retries
    3. Rate Limiter - Token bucket style, X requests per Y interval
    4. Exponential Backoff - Retry with exponential delays on failures
    5. Global 429 Blocking - All requests pause on rate limit
    
    Usage:
        api = VRChatAPI()
        
        # Login
        result = await api.login(username, password)
        if result.get("requires_2fa"):
            result = await api.verify_2fa(code)
        
        # Or check existing session
        session = await api.check_session()
        if session.get("valid"):
            user = session["user"]
        
        # Get groups
        groups = await api.get_my_groups()
        
        # Always close when done
        await api.close()
    """
    
    def __init__(self, cookies_path: str = None):
        """
        Initialize the VRChat API client.
        
        Args:
            cookies_path: Optional path to cookies file. If not provided,
                         uses the default path from utils.paths.
        """
        # Initialize base class (which sets up all shared state)
        super().__init__(cookies_path)
        logger.info("VRChatAPI client initialized")
