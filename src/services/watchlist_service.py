"""
Watchlist Service
================
Centralized service for checking and managing watchlist status across the entire app.
All user profile displays should use this service to determine watchlist status.

Features:
- Centralized watchlist lookup with caching
- Automatic user recording in database when encountered
- Event publishing for real-time UI updates
- Efficient batch checking for multiple users
"""

import logging
from typing import Dict, List, Optional, Any
from services.database import get_database
from services.event_bus import get_event_bus

logger = logging.getLogger(__name__)

# Singleton instance
_watchlist_service: Optional['WatchlistService'] = None


class WatchlistService:
    """
    Centralized watchlist management service.
    
    Use this service to:
    - Check if a user is on the watchlist
    - Ensure users are recorded in the database when encountered
    - Get watchlist status efficiently for multiple users at once
    - Toggle watchlist status with automatic UI sync
    """
    
    def __init__(self):
        self._db = get_database()
        self._event_bus = get_event_bus()
        self._cache: Dict[str, Dict[str, Any]] = {}  # user_id -> status data
        self._cache_loaded = False
    
    def _ensure_cache_loaded(self):
        """Load all watchlisted users into cache on first access."""
        if self._cache_loaded:
            return
        
        try:
            watchlisted = self._db.get_watchlisted_users()
            for user in watchlisted:
                uid = user.get("user_id")
                if uid:
                    self._cache[uid] = {
                        "is_watchlisted": True,
                        "note": user.get("note"),
                        "tags": user.get("tags", []),
                        "username": user.get("username"),
                    }
            self._cache_loaded = True
            logger.debug(f"Watchlist cache loaded with {len(self._cache)} users")
        except Exception as e:
            logger.error(f"Failed to load watchlist cache: {e}")
    
    def refresh_cache(self):
        """Force refresh of the watchlist cache."""
        self._cache.clear()
        self._cache_loaded = False
        self._ensure_cache_loaded()
    
    def is_watchlisted(self, user_id: str) -> bool:
        """
        Check if a user is on the watchlist.
        
        Args:
            user_id: VRChat user ID
            
        Returns:
            True if user is on watchlist, False otherwise
        """
        if not user_id:
            return False
        
        self._ensure_cache_loaded()
        
        # Check cache first
        if user_id in self._cache:
            return self._cache[user_id].get("is_watchlisted", False)
        
        # Not in cache - check database directly
        try:
            profile = self._db.get_user_profile(user_id)
            if profile:
                is_wl = profile.get("is_watchlisted", False)
                # Cache the result
                self._cache[user_id] = {
                    "is_watchlisted": is_wl,
                    "note": profile.get("note"),
                    "tags": profile.get("tags", []),
                }
                return is_wl
        except Exception as e:
            logger.error(f"Error checking watchlist status for {user_id}: {e}")
        
        return False
    
    def get_user_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get full watchlist status for a user.
        
        Args:
            user_id: VRChat user ID
            
        Returns:
            Dict with is_watchlisted, note, tags
        """
        if not user_id:
            return {"is_watchlisted": False, "note": None, "tags": []}
        
        self._ensure_cache_loaded()
        
        if user_id in self._cache:
            return self._cache[user_id].copy()
        
        # Check database
        try:
            profile = self._db.get_user_profile(user_id)
            if profile:
                status = {
                    "is_watchlisted": profile.get("is_watchlisted", False),
                    "note": profile.get("note"),
                    "tags": profile.get("tags", []),
                }
                self._cache[user_id] = status.copy()
                return status
        except Exception as e:
            logger.error(f"Error getting user status for {user_id}: {e}")
        
        return {"is_watchlisted": False, "note": None, "tags": []}
    
    def check_and_record_user(self, user_id: str, username: str) -> Dict[str, Any]:
        """
        Check if a user is on the watchlist and ensure they are recorded in the database.
        
        This should be called whenever a user is encountered in the app (e.g., from API responses)
        to ensure all users are tracked for potential watchlist matching.
        
        Args:
            user_id: VRChat user ID
            username: Display name
            
        Returns:
            Dict with is_watchlisted, note, tags
        """
        if not user_id or not username:
            return {"is_watchlisted": False, "note": None, "tags": []}
        
        self._ensure_cache_loaded()
        
        # Check cache first
        cached = self._cache.get(user_id)
        if cached is not None:
            return cached.copy()
        
        # Check database and record if needed
        try:
            profile = self._db.get_user_profile(user_id)
            
            if not profile:
                # User not in database - record them now
                self._db.record_user_sighting(user_id, username)
                profile = self._db.get_user_profile(user_id)
            
            if profile:
                status = {
                    "is_watchlisted": profile.get("is_watchlisted", False),
                    "note": profile.get("note"),
                    "tags": profile.get("tags", []),
                }
                self._cache[user_id] = status.copy()
                return status
                
        except Exception as e:
            logger.error(f"Error checking/recording user {user_id}: {e}")
        
        return {"is_watchlisted": False, "note": None, "tags": []}
    
    def batch_check_users(self, users: List[Dict[str, Any]], id_key: str = "id", name_key: str = "displayName") -> Dict[str, Dict[str, Any]]:
        """
        Efficiently check watchlist status for multiple users at once.
        
        Args:
            users: List of user dicts
            id_key: Key to get user ID from dict (default: "id")
            name_key: Key to get display name from dict (default: "displayName")
            
        Returns:
            Dict mapping user_id -> status dict
        """
        result = {}
        
        for user in users:
            user_id = user.get(id_key) or user.get("userId")
            username = user.get(name_key) or user.get("name", "Unknown")
            
            if user_id:
                result[user_id] = self.check_and_record_user(user_id, username)
        
        return result
    
    def toggle_watchlist(self, user_id: str, state: bool, username: str = None):
        """
        Toggle watchlist status for a user and publish event.
        
        Args:
            user_id: VRChat user ID
            state: True to add to watchlist, False to remove
            username: Optional display name for recording
        """
        if not user_id:
            return
        
        try:
            # Ensure user exists in database
            if username:
                self._db.record_user_sighting(user_id, username)
            
            self._db.toggle_watchlist(user_id, state)
            
            # Update cache
            if user_id in self._cache:
                self._cache[user_id]["is_watchlisted"] = state
            else:
                self._cache[user_id] = {"is_watchlisted": state, "note": None, "tags": []}
            
            # Publish event for UI synchronization
            self._event_bus.publish("watchlist_updated", {
                "user_id": user_id,
                "is_watchlisted": state,
            })
            
            # Also publish user_updated for UserCard components
            self._event_bus.publish("user_updated", {
                "user_id": user_id,
                "is_watchlisted": state,
            })
            
            logger.info(f"Watchlist {'added' if state else 'removed'}: {user_id}")
            
        except Exception as e:
            logger.error(f"Error toggling watchlist for {user_id}: {e}")
    
    def set_user_note(self, user_id: str, note: str, username: str = None):
        """
        Set a note for a user and publish event.
        
        Args:
            user_id: VRChat user ID
            note: Note text
            username: Optional display name for recording
        """
        if not user_id:
            return
        
        try:
            # Ensure user exists
            if username:
                self._db.record_user_sighting(user_id, username)
            
            self._db.set_user_note(user_id, note)
            
            # Update cache
            if user_id in self._cache:
                self._cache[user_id]["note"] = note
            else:
                self._cache[user_id] = {"is_watchlisted": False, "note": note, "tags": []}
            
            # Publish event
            self._event_bus.publish("user_updated", {
                "user_id": user_id,
                "note": note,
            })
            
        except Exception as e:
            logger.error(f"Error setting note for {user_id}: {e}")
    
    def get_watchlisted_users(self) -> List[Dict[str, Any]]:
        """Get all users on the watchlist."""
        return self._db.get_watchlisted_users()
    
    def invalidate_user(self, user_id: str):
        """Remove a user from cache to force refresh on next access."""
        if user_id in self._cache:
            del self._cache[user_id]


def get_watchlist_service() -> WatchlistService:
    """Get or create the singleton watchlist service."""
    global _watchlist_service
    if _watchlist_service is None:
        _watchlist_service = WatchlistService()
    return _watchlist_service
