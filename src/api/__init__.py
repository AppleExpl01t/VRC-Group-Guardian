"""
VRChat API Package
==================
Modular VRChat API client with authentication, rate limiting, and caching.

This package provides:
- VRChatAPI: Full VRChat API client with all features
- MockVRChatAPI: Mock client for demo mode

The VRChatAPI class is composed from multiple mixins:
- BaseAPI: HTTP client and shared state
- RequestMixin: VRCX-style rate limiting and request handling
- AuthMixin: Authentication and session management
- ImagesMixin: Image caching
- UsersMixin: User operations
- GroupsMixin: Group operations
- InvitesMixin: Invite operations
- WorldsMixin: World operations
- CacheMixin: Cached fetch methods with CacheManager integration
"""

from .client import VRChatAPI
from .mock_client import MockVRChatAPI

__all__ = ['VRChatAPI', 'MockVRChatAPI']
