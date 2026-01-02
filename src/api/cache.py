"""
Cache Mixin
============
VRCX-style cached fetch methods and cache invalidation.
"""

from typing import Optional, Dict
from services.debug_logger import get_logger
from services.cache_manager import get_cache

logger = get_logger("api.cache")


class CacheMixin:
    """
    Mixin providing cached fetch functionality:
    - Cached user fetching
    - Cached group fetching
    - Cached instances fetching
    - Cached join requests fetching
    - Cached bans fetching
    - Cached members fetching
    - Cached world fetching
    - Cache invalidation methods
    """
    
    async def get_cached_user(self, user_id: str, force_refresh: bool = False) -> Optional[Dict]:
        """
        VRCX-style cached user fetch.
        Returns cached user if available, otherwise fetches from API.
        
        Args:
            user_id: The user ID
            force_refresh: If True, bypasses cache and fetches fresh data
            
        Returns:
            User dict or None
        """
        cache = get_cache()
        
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached = cache.users.get(user_id)
            if cached:
                logger.debug(f"Cache hit: user {user_id}")
                return cached
        
        # Fetch from API
        user = await self.get_user(user_id)
        if user:
            cache.users.set(user_id, user)
        return user
    
    async def get_cached_group(self, group_id: str, force_refresh: bool = False) -> Optional[Dict]:
        """
        VRCX-style cached group fetch.
        Returns cached group if available, otherwise fetches from API.
        """
        cache = get_cache()
        
        if not force_refresh:
            cached = cache.groups.get(group_id)
            if cached:
                logger.debug(f"Cache hit: group {group_id}")
                return cached
        
        group = await self.get_group(group_id)
        if group:
            cache.groups.set(group_id, group)
        return group
    
    async def get_cached_group_instances(self, group_id: str, force_refresh: bool = False) -> list:
        """
        VRCX-style cached group instances fetch.
        Instances are cached for a shorter duration (1 min) since they're dynamic.
        """
        cache = get_cache()
        cache_key = f"instances_{group_id}"
        
        if not force_refresh:
            cached = cache.instances.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: instances for group {group_id}")
                return cached
        
        instances = await self.get_group_instances(group_id)
        cache.instances.set(cache_key, instances)
        return instances
    
    async def get_cached_join_requests(self, group_id: str, force_refresh: bool = False) -> list:
        """
        VRCX-style cached join requests fetch.
        """
        cache = get_cache()
        cache_key = f"requests_{group_id}"
        
        if not force_refresh:
            cached = cache.join_requests.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: join requests for group {group_id}")
                return cached
        
        requests = await self.get_group_join_requests(group_id)
        cache.join_requests.set(cache_key, requests)
        return requests
    
    async def get_cached_group_bans(self, group_id: str, force_refresh: bool = False) -> list:
        """
        VRCX-style cached group bans fetch.
        """
        cache = get_cache()
        cache_key = f"bans_{group_id}"
        
        if not force_refresh:
            cached = cache.group_bans.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: bans for group {group_id}")
                return cached
        
        bans = await self.get_group_bans(group_id)
        cache.group_bans.set(cache_key, bans)
        return bans
    
    async def get_cached_group_members(self, group_id: str, limit: int = 50, offset: int = 0, force_refresh: bool = False) -> list:
        """
        VRCX-style cached group members fetch.
        """
        cache = get_cache()
        cache_key = f"members_{group_id}_{limit}_{offset}"
        
        if not force_refresh:
            cached = cache.group_members.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: members for group {group_id}")
                return cached
        
        members = await self.search_group_members(group_id, limit=limit, offset=offset)
        cache.group_members.set(cache_key, members)
        return members
    
    async def get_cached_world(self, world_id: str, force_refresh: bool = False) -> Optional[Dict]:
        """
        VRCX-style cached world fetch.
        Worlds are cached for longer (1 hour) since they rarely change.
        """
        cache = get_cache()
        
        if not force_refresh:
            cached = cache.worlds.get(world_id)
            if cached:
                logger.debug(f"Cache hit: world {world_id}")
                return cached
        
        world = await self.get_world(world_id)
        if world:
            cache.worlds.set(world_id, world)
        return world
    
    # ==================== CACHE INVALIDATION ====================
    # Call these after mutations to ensure fresh data on next fetch
    
    def invalidate_join_requests_cache(self, group_id: str):
        """Invalidate cached join requests after accepting/rejecting."""
        cache = get_cache()
        cache.join_requests.invalidate(f"requests_{group_id}")
        logger.debug(f"Invalidated join requests cache for group {group_id}")
    
    def invalidate_bans_cache(self, group_id: str):
        """Invalidate cached bans after banning/unbanning."""
        cache = get_cache()
        cache.group_bans.invalidate(f"bans_{group_id}")
        logger.debug(f"Invalidated bans cache for group {group_id}")
    
    def invalidate_members_cache(self, group_id: str):
        """Invalidate all cached member pages for a group."""
        cache = get_cache()
        # Clear all member cache entries for this group
        keys_to_remove = [k for k in cache.group_members._cache.keys() if k.startswith(f"members_{group_id}")]
        for key in keys_to_remove:
            cache.group_members.invalidate(key)
        logger.debug(f"Invalidated members cache for group {group_id}")
    
    def invalidate_instances_cache(self, group_id: str):
        """Invalidate cached instances after instance changes."""
        cache = get_cache()
        cache.instances.invalidate(f"instances_{group_id}")
        logger.debug(f"Invalidated instances cache for group {group_id}")
    
    def invalidate_group_cache(self, group_id: str):
        """Invalidate all cached data for a group."""
        self.invalidate_join_requests_cache(group_id)
        self.invalidate_bans_cache(group_id)
        self.invalidate_members_cache(group_id)
        self.invalidate_instances_cache(group_id)
        cache = get_cache()
        cache.groups.invalidate(group_id)
        logger.debug(f"Invalidated all caches for group {group_id}")
    
    def invalidate_my_groups_cache(self):
        """Invalidate the user's groups list cache."""
        if self._current_user:
            user_id = self._current_user.get("id")
            if user_id:
                cache = get_cache()
                cache_key = f"my_groups_{user_id}"
                cache.groups.invalidate(cache_key)
                logger.debug(f"Invalidated my_groups cache for user {user_id}")
    
    def clear_all_caches(self):
        """Clear all entity caches (call on logout)."""
        cache = get_cache()
        cache.clear_all()
