"""
Worlds Mixin
=============
World search and retrieval functionality.
"""

from typing import Optional, Dict, List
from services.debug_logger import get_logger

logger = get_logger("api.worlds")


class WorldsMixin:
    """
    Mixin providing world-related functionality:
    - Get world details
    - Search worlds
    - Create instances
    """
    
    async def get_world(self, world_id: str) -> Optional[Dict]:
        """
        Get details of a specific world.
        
        Args:
            world_id: The world ID (wrld_xxx)
            
        Returns:
            World object or None
        """
        try:
            response = await self._request("GET", f"/worlds/{world_id}")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error fetching world {world_id}: {e}")
            return None
    
    async def search_worlds(self, query: str, n: int = 10, offset: int = 0, sort: str = "relevance") -> List[Dict]:
        """
        Search for VRChat worlds by name/keyword.
        
        Args:
            query: Search term
            n: Number of results (default 10, max 100)
            offset: Offset for pagination
            sort: Sort order - "relevance", "popularity", "heat", "publicationDate", etc.
            
        Returns:
            List of world objects
        """
        try:
            params = {
                "search": query,
                "n": min(n, 100),
                "offset": offset,
                "sort": sort,
            }
            
            response = await self._request(
                "GET",
                "/worlds",
                params=params,
            )
            
            if response.status_code == 200:
                results = response.json()
                logger.info(f"World search '{query}' returned {len(results)} results")
                return results
            else:
                logger.warning(f"World search failed: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error searching worlds: {e}")
            return []
    
    async def create_instance(self, world_id: str, type: str = "group", region: str = "us",
                              group_id: str = None, group_access_type: str = None, 
                              queue_enabled: bool = True, role_ids: list = None,
                              age_gate: bool = False, name: str = None) -> Optional[Dict]:
        """
        Create a new instance.
        
        Args:
            world_id: The world ID (wrld_xxx)
            type: Instance type - 'public', 'friends', 'hidden', 'private', 'group'
            region: Region code - 'us', 'use', 'eu', 'jp'
            group_id: Required for group instances - the group ID
            group_access_type: Access type for group instances - 'public', 'plus', 'members'
            queue_enabled: Whether to enable queue for the instance
            role_ids: List of role IDs allowed to join (for group instances)
            age_gate: Whether to enable age gate
            name: Optional custom instance name
            
        Returns:
            Instance object or None if failed
        """
        try:
            json_data = {
                "worldId": world_id,
                "type": type,
                "region": region,
                "queueEnabled": queue_enabled,
            }
            
            # For group instances, VRChat requires ownerId to be set to the group ID
            if type == "group" and group_id:
                json_data["ownerId"] = group_id
            
            if group_id:
                json_data["groupId"] = group_id
            
            if group_access_type:
                json_data["groupAccessType"] = group_access_type
            
            if role_ids:
                json_data["roleIds"] = role_ids
            
            if age_gate:
                json_data["ageGate"] = age_gate
            
            # VRChat API expects "displayName" not "name" for custom instance names
            if name:
                json_data["displayName"] = name
            
            logger.info(f"Creating instance: {json_data}")
            
            response = await self._request(
                "POST",
                "/instances",
                json=json_data,
            )
            
            if response.status_code in [200, 201]:
                instance = response.json()
                logger.info(f"Created instance: {instance.get('id', 'unknown')}")
                return instance
            else:
                # Try to get error details from response
                error_msg = f"HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    if isinstance(error_data, dict):
                        error_msg = error_data.get("error", {}).get("message", error_msg)
                except:
                    error_msg = response.text[:200] if response.text else error_msg
                
                logger.warning(f"Failed to create instance: {response.status_code} - {error_msg}")
                # Return error info in a way the UI can detect
                return {"error": True, "message": error_msg, "status_code": response.status_code}
                
        except Exception as e:
            logger.error(f"Error creating instance: {e}")
            return {"error": True, "message": str(e)}
