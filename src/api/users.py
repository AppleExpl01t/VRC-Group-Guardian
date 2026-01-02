"""
Users Mixin
============
User and friends management functionality.
"""

from typing import Optional, Dict, List
from services.debug_logger import get_logger

logger = get_logger("api.users")


class UsersMixin:
    """
    Mixin providing user-related functionality:
    - Get user details
    - Search users
    - Get friends list
    - Get all friends with pagination
    """
    
    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Fetch full user details"""
        try:
            response = await self._request("GET", f"/users/{user_id}")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None

    async def get_friends(self, offline: bool = False, n: int = 100, offset: int = 0) -> List[Dict]:
        """
        Fetch the authenticated user's friends list.
        
        Args:
            offline: If True, return only offline friends. If False, return online/active friends.
            n: Number of friends to return (max 100 per request)
            offset: Offset for pagination
            
        Returns:
            List of friend user objects
        """
        try:
            params = {
                "n": min(n, 100),
                "offset": offset,
                "offline": str(offline).lower(),
            }
            
            response = await self._request(
                "GET",
                "/auth/user/friends",
                params=params,
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch friends: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching friends: {e}")
            return []

    async def get_all_friends(self, on_progress=None) -> List[Dict]:
        """
        Fetch ALL friends (both online and offline) with pagination.
        
        Args:
            on_progress: Optional callback(current, is_online_phase) for progress updates
            
        Returns:
            Complete list of all friends
        """
        all_friends = []
        
        # Get online friends first
        logger.info("Fetching online friends...")
        offset = 0
        while True:
            batch = await self.get_friends(offline=False, n=100, offset=offset)
            if not batch:
                break
            all_friends.extend(batch)
            logger.info(f"Fetched {len(batch)} online friends (total: {len(all_friends)})")
            if on_progress:
                try:
                    on_progress(len(all_friends), True)
                except:
                    pass
            if len(batch) < 100:
                break
            offset += 100
        
        # Get offline friends
        logger.info("Fetching offline friends...")
        offset = 0
        while True:
            batch = await self.get_friends(offline=True, n=100, offset=offset)
            if not batch:
                break
            all_friends.extend(batch)
            logger.info(f"Fetched {len(batch)} offline friends (total: {len(all_friends)})")
            if on_progress:
                try:
                    on_progress(len(all_friends), False)
                except:
                    pass
            if len(batch) < 100:
                break
            offset += 100
        
        logger.info(f"Fetched {len(all_friends)} total friends")
        return all_friends

    async def search_users(self, query: str, n: int = 20, offset: int = 0) -> List[Dict]:
        """
        Search for VRChat users by displayName.
        
        Args:
            query: The search term to match against displayName
            n: Number of results to return (max 100)
            offset: Offset for pagination
            
        Returns:
            List of user objects matching the search
        """
        try:
            params = {
                "search": query,
                "n": min(n, 100),
                "offset": offset,
            }
            
            response = await self._request(
                "GET",
                "/users",
                params=params,
            )
            
            if response.status_code == 200:
                results = response.json()
                logger.info(f"User search '{query}' returned {len(results)} results")
                return results
            else:
                logger.warning(f"User search failed: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return []
