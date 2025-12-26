"""
Cache Manager
=============
VRCX-style centralized in-memory cache for VRChat entities.

Key features:
- In-memory caching with configurable TTL per entity type
- Automatic cleanup of expired entries
- Disk persistence for important data (groups, users)
- Entity-specific caches (users, groups, instances)
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, TypeVar, Generic
from pathlib import Path
from services.debug_logger import get_logger
from utils.paths import get_data_dir

logger = get_logger("cache_manager")

T = TypeVar('T')


class CacheEntry(Generic[T]):
    """A single cached entry with value and expiry time."""
    
    def __init__(self, value: T, ttl_seconds: float):
        self.value = value
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=ttl_seconds)
    
    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at
    
    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.created_at).total_seconds()


class EntityCache(Generic[T]):
    """
    A cache for a specific entity type (users, groups, etc).
    
    Features:
    - TTL-based expiration
    - Optional `apply` function to merge/update cached data
    - Memory limit with LRU eviction
    """
    
    def __init__(
        self,
        name: str,
        default_ttl: float = 300.0,  # 5 minutes
        max_entries: int = 1000,
        apply_fn: Optional[Callable[[T, T], T]] = None,
    ):
        self.name = name
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self.apply_fn = apply_fn  # Function to merge new data with existing
        self._cache: Dict[str, CacheEntry[T]] = {}
        self._access_order: list = []  # For LRU eviction
    
    def get(self, key: str) -> Optional[T]:
        """Get a cached value if it exists and is not expired."""
        entry = self._cache.get(key)
        if entry is None:
            return None
        
        if entry.is_expired:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            return None
        
        # Update access order for LRU
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        
        return entry.value
    
    def set(self, key: str, value: T, ttl: Optional[float] = None) -> T:
        """
        Set a cached value. If `apply_fn` is defined and entry exists,
        the new value is merged with the old one.
        """
        ttl = ttl if ttl is not None else self.default_ttl
        
        # Apply merge function if we have existing data
        existing = self.get(key)
        if existing is not None and self.apply_fn is not None:
            value = self.apply_fn(existing, value)
        
        self._cache[key] = CacheEntry(value, ttl)
        
        # Update access order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        
        # Evict oldest if over limit
        self._evict_if_needed()
        
        return value
    
    def has(self, key: str) -> bool:
        """Check if a valid (non-expired) entry exists."""
        return self.get(key) is not None
    
    def invalidate(self, key: str):
        """Remove a specific entry from cache."""
        if key in self._cache:
            del self._cache[key]
        if key in self._access_order:
            self._access_order.remove(key)
    
    def clear(self):
        """Clear all entries."""
        self._cache.clear()
        self._access_order.clear()
    
    def cleanup_expired(self):
        """Remove all expired entries."""
        expired_keys = [k for k, v in self._cache.items() if v.is_expired]
        for key in expired_keys:
            self.invalidate(key)
        if expired_keys:
            logger.debug(f"[{self.name}] Cleaned up {len(expired_keys)} expired entries")
    
    def _evict_if_needed(self):
        """Evict oldest entries if over max_entries limit."""
        while len(self._cache) > self.max_entries and self._access_order:
            oldest_key = self._access_order.pop(0)
            if oldest_key in self._cache:
                del self._cache[oldest_key]
                logger.debug(f"[{self.name}] Evicted LRU entry: {oldest_key}")
    
    @property
    def size(self) -> int:
        return len(self._cache)
    
    def values(self):
        """Iterate over all non-expired cached values."""
        self.cleanup_expired()
        return [e.value for e in self._cache.values()]
    
    def items(self):
        """Iterate over all non-expired (key, value) pairs."""
        self.cleanup_expired()
        return [(k, e.value) for k, e in self._cache.items()]


def _merge_user_data(existing: dict, new: dict) -> dict:
    """VRCX-style user data merge - preserve VRCX-specific fields."""
    result = existing.copy()
    for key, value in new.items():
        if value is not None:  # Don't overwrite with None
            result[key] = value
    return result


def _merge_group_data(existing: dict, new: dict) -> dict:
    """VRCX-style group data merge."""
    result = existing.copy()
    for key, value in new.items():
        if value is not None:
            result[key] = value
    # Preserve myMember if it exists and has more data
    if "myMember" in existing and "myMember" in new:
        result["myMember"] = _merge_user_data(existing["myMember"], new["myMember"])
    return result


class CacheManager:
    """
    Centralized cache manager for all VRChat entities.
    
    Usage:
        cache = CacheManager()
        
        # Get cached user or None
        user = cache.users.get("usr_xxx")
        
        # Set/update cached user
        cache.users.set("usr_xxx", user_data)
        
        # Check if we have a cached user
        if cache.users.has("usr_xxx"):
            ...
    """
    
    # Cache TTLs (in seconds) - VRCX-style intervals
    USER_TTL = 300.0       # 5 minutes
    GROUP_TTL = 600.0      # 10 minutes (groups change less often)
    INSTANCE_TTL = 60.0    # 1 minute (instances are dynamic)
    WORLD_TTL = 3600.0     # 1 hour (worlds rarely change)
    MEMBER_TTL = 120.0     # 2 minutes
    REQUEST_TTL = 60.0     # 1 minute (join requests)
    BAN_TTL = 120.0        # 2 minutes
    
    def __init__(self):
        # Entity caches with appropriate TTLs and merge functions
        self.users = EntityCache[dict](
            name="users",
            default_ttl=self.USER_TTL,
            max_entries=500,
            apply_fn=_merge_user_data,
        )
        
        self.groups = EntityCache[dict](
            name="groups",
            default_ttl=self.GROUP_TTL,
            max_entries=50,
            apply_fn=_merge_group_data,
        )
        
        self.instances = EntityCache[list](
            name="instances",
            default_ttl=self.INSTANCE_TTL,
            max_entries=50,
        )
        
        self.worlds = EntityCache[dict](
            name="worlds",
            default_ttl=self.WORLD_TTL,
            max_entries=100,
        )
        
        self.group_members = EntityCache[list](
            name="group_members",
            default_ttl=self.MEMBER_TTL,
            max_entries=20,
        )
        
        self.join_requests = EntityCache[list](
            name="join_requests",
            default_ttl=self.REQUEST_TTL,
            max_entries=20,
        )
        
        self.group_bans = EntityCache[list](
            name="group_bans",
            default_ttl=self.BAN_TTL,
            max_entries=20,
        )
        
        # Disk persistence for critical data
        self._disk_cache_path = get_data_dir() / "entity_cache.json"
        
        # Start periodic cleanup task
        self._cleanup_task = None
        
        logger.info("CacheManager initialized")
    
    def start_cleanup_task(self, loop=None):
        """Start periodic cache cleanup (call after event loop is running)."""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(60)  # Every minute
                self.cleanup_all()
        
        if loop:
            self._cleanup_task = loop.create_task(cleanup_loop())
    
    def cleanup_all(self):
        """Clean up all expired entries from all caches."""
        self.users.cleanup_expired()
        self.groups.cleanup_expired()
        self.instances.cleanup_expired()
        self.worlds.cleanup_expired()
        self.group_members.cleanup_expired()
        self.join_requests.cleanup_expired()
        self.group_bans.cleanup_expired()
    
    def clear_all(self):
        """Clear all caches (e.g., on logout)."""
        self.users.clear()
        self.groups.clear()
        self.instances.clear()
        self.worlds.clear()
        self.group_members.clear()
        self.join_requests.clear()
        self.group_bans.clear()
        logger.info("All caches cleared")
    
    def get_stats(self) -> dict:
        """Get cache statistics for debugging."""
        return {
            "users": self.users.size,
            "groups": self.groups.size,
            "instances": self.instances.size,
            "worlds": self.worlds.size,
            "group_members": self.group_members.size,
            "join_requests": self.join_requests.size,
            "group_bans": self.group_bans.size,
        }
    
    def save_to_disk(self):
        """Persist important cached data to disk."""
        try:
            data = {
                "groups": {k: v for k, v in self.groups.items()},
                "saved_at": datetime.now().isoformat(),
            }
            self._disk_cache_path.write_text(json.dumps(data, default=str))
            logger.debug("Saved cache to disk")
        except Exception as e:
            logger.warning(f"Failed to save cache to disk: {e}")
    
    def load_from_disk(self):
        """Load cached data from disk."""
        if not self._disk_cache_path.exists():
            return
        
        try:
            data = json.loads(self._disk_cache_path.read_text())
            
            # Restore groups with fresh TTL
            for group_id, group_data in data.get("groups", {}).items():
                self.groups.set(group_id, group_data)
            
            logger.info(f"Loaded {self.groups.size} groups from disk cache")
        except Exception as e:
            logger.warning(f"Failed to load cache from disk: {e}")


# Global cache instance
_cache_instance: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance
