"""
Groups Mixin
=============
Group management functionality including members, bans, instances, and audit logs.
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, List
from services.debug_logger import get_logger
from services.cache_manager import get_cache

logger = get_logger("api.groups")


class GroupsMixin:
    """
    Mixin providing group-related functionality:
    - Get user's groups
    - Get group details
    - Get group instances
    - Get/handle join requests
    - Get/manage bans
    - Get/search members
    - Get audit logs
    - Create/close instances
    """
    
    async def get_my_groups(self, force_refresh: bool = False) -> List[Dict]:
        """
        Fetch all groups where the user has moderation permissions.
        Uses CacheManager for caching (1 hour TTL).
        """
        # Ensure we have user ID
        user_id = self._current_user.get("id") if self._current_user else None
        if not user_id:
            # Try to get user info if missing
            chk = await self.check_session()
            if not chk.get("valid"):
                return []
            user_id = self._current_user.get("id") if self._current_user else None
        
        if not user_id:
            return []
        
        # Check CacheManager
        cache = get_cache()
        cache_key = f"my_groups_{user_id}"
        
        if not force_refresh:
            cached = cache.groups.get(cache_key)
            if cached:
                logger.info("Using cached group list from CacheManager")
                return cached
        
        logger.info(f"Fetching groups for {user_id} (API)...")

        try:
            # First get user's group memberships (lite)
            response = await self._request(
                "GET",
                f"/users/{user_id}/groups",
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to get groups: {response.status_code}")
                return []
            
            memberships = response.json()
            
            # Helper for parallel processing
            async def process_membership(membership):
                group_id = membership.get("groupId")
                if not group_id:
                    return None
                
                # Get full group info
                group_info = await self.get_group(group_id)
                if not group_info:
                    return None
                    
                # Check permissions - with defensive type checking
                my_member = group_info.get("myMember")
                
                # Debug: log the structure
                logger.debug(f"Group {group_id} myMember type: {type(my_member).__name__}")
                
                # Handle different API response formats
                if my_member is None:
                    my_member = {}
                elif isinstance(my_member, list):
                    # If it's a list, try to get first element or create empty dict
                    my_member = my_member[0] if my_member else {}
                elif not isinstance(my_member, dict):
                    # Unexpected type - log and use empty dict
                    logger.warning(f"Unexpected myMember type for group {group_id}: {type(my_member)}")
                    my_member = {}
                
                permissions = my_member.get("permissions", []) if isinstance(my_member, dict) else []
                mod_perms = ["group-bans-manage", "group-members-manage", "group-instance-moderate", "group-data-manage", "group-audit-view", "*"]
                
                has_mod_perms = any(p in permissions for p in mod_perms)
                is_owner = my_member.get("isOwner", False) if isinstance(my_member, dict) else False
                
                if has_mod_perms or is_owner:
                    # Construct Image URLs if missing
                    icon_url = group_info.get("iconUrl")
                    if not icon_url and group_info.get("iconId"):
                        icon_url = f"https://api.vrchat.cloud/api/1/file/{group_info['iconId']}/image/file"
                    
                    banner_url = group_info.get("bannerUrl")
                    if not banner_url and group_info.get("bannerId"):
                        banner_url = f"https://api.vrchat.cloud/api/1/file/{group_info['bannerId']}/image/file"

                    # Fetch pending requests count (if we have permission)
                    request_count = 0
                    if any(p in permissions for p in ["group-members-manage", "*"]) or is_owner:
                         # We use a safe separate call here
                         try:
                             reqs = await self.get_group_join_requests(group_id)
                             request_count = len(reqs)
                         except:
                             pass

                    group_data = {
                        "id": group_id,
                        "name": group_info.get("name", "Unknown Group"),
                        "shortCode": group_info.get("shortCode", ""),
                        "discriminator": group_info.get("discriminator", ""),
                        "description": group_info.get("description", ""),
                        "iconUrl": icon_url,
                        "bannerUrl": banner_url,
                        "memberCount": group_info.get("memberCount", 0),
                        "onlineMemberCount": group_info.get("onlineMemberCount", 0),
                        "pendingRequestCount": request_count,
                        "isOwner": is_owner,
                        "permissions": permissions,
                        "roles": my_member.get("roleIds", []),
                    }
                    # No image caching, rely on Flet remote URLs
                    return group_data
                return None

            # Run all tasks in parallel
            # Run tasks in batches to avoid overwhelming the rate limiter
            logger.info(f"Fetching details for {len(memberships)} groups (batched)...")
            
            mod_groups = []
            batch_size = 5
            
            for i in range(0, len(memberships), batch_size):
                batch = memberships[i:i + batch_size]
                logger.debug(f"Processing batch {i//batch_size + 1}: {len(batch)} groups")
                
                tasks = [process_membership(m) for m in batch]
                batch_results = await asyncio.gather(*tasks)
                
                # Filter valid results
                for res in batch_results:
                    if res:
                        mod_groups.append(res)
                        
                # Small delay between batches if there are more to come
                if i + batch_size < len(memberships):
                    await asyncio.sleep(1.0)
            
            # Results are already aggregated
            results = [] # Unused now, but keeping variable logic consistent if needed
            
            logger.info(f"Processing complete: {len(mod_groups)} mod groups found")
            
            if mod_groups:
                # Cache with 1 hour TTL using CacheManager
                cache.groups.set(cache_key, mod_groups, ttl=3600.0)
            
            return mod_groups
            
        except Exception as e:
            logger.error(f"Error fetching groups: {e}")
            return []
    
    async def get_group(self, group_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific group.
        
        Args:
            group_id: The group ID
            
        Returns:
            Group info dict or None
        """
        try:
            response = await self._request(
                "GET",
                f"/groups/{group_id}",
                params={"includeRoles": "true"},
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get group {group_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching group: {e}")
            return None
    
    async def get_group_instances(self, group_id: str) -> list:
        """Get active instances for a group"""
        try:
            response = await self._request(
                "GET",
                f"/groups/{group_id}/instances",
            )
            
            if response.status_code == 200:
                return response.json()
            return []
            
        except Exception as e:
            logger.error(f"Error fetching group instances: {e}")
            return []
    
    async def close_group_instance(self, world_id: str, instance_id: str, hard_close: bool = False) -> bool:
        """Close a group instance
        
        This matches VRCX's implementation in misc.js:
        - DELETE /instances/{location}
        - location is passed directly without URL encoding
        - hardClose is a query parameter
        
        Args:
            world_id: The world ID (wrld_xxx)
            instance_id: The instance ID (includes the full location string after the world ID)
            hard_close: If True, forces immediate close
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build the full location string (matching VRCX: params.location)
            location = f"{world_id}:{instance_id}"
            
            logger.info(f"Closing instance: {location}")
            logger.debug(f"Using VRCX-style DELETE /instances/{location}")
            
            # VRCX passes hardClose as a query param, not in the body
            # Only include params if hard_close is True
            request_kwargs = {}
            if hard_close:
                request_kwargs["params"] = {"hardClose": "true"}
            
            # Make the request - do NOT URL encode the path, pass it raw
            # The httpx library will handle path encoding appropriately
            response = await self._request(
                "DELETE",
                f"/instances/{location}",
                **request_kwargs,
            )
            
            logger.debug(f"Close instance response: status={response.status_code}")
            if response.text:
                logger.debug(f"Response body: {response.text[:500]}")
            
            if response.status_code in [200, 204]:
                logger.info(f"Instance closed successfully: {location}")
                return True
            else:
                logger.warning(f"Failed to close instance: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error closing instance: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    async def get_group_join_requests(self, group_id: str) -> list:
        """Get pending join requests for a group"""
        try:
            logger.info(f"Fetching join requests for group {group_id}")
            response = await self._request(
                "GET",
                f"/groups/{group_id}/requests",
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Found {len(data)} join requests")
                if data:
                    logger.debug(f"Sample Request Data: {data[0]}")
                return data
            else:
                logger.warning(f"Failed to fetch requests: {response.status_code} - {response.text}")
                return []
            
        except Exception as e:
            logger.error(f"Error fetching join requests: {e}")
            return []
    
    async def get_group_bans(self, group_id: str) -> list:
        """Get banned members for a group"""
        try:
            response = await self._request(
                "GET",
                f"/groups/{group_id}/bans",
            )
            
            if response.status_code == 200:
                return response.json()
            return []
            
        except Exception as e:
            logger.error(f"Error fetching group bans: {e}")
            return []
    
    async def get_group_audit_logs(self, group_id: str, n: int = 50) -> list:
        """Get audit logs for a group"""
        try:
            response = await self._request(
                "GET",
                f"/groups/{group_id}/auditLogs",
                params={"n": n},
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            return []
            
        except Exception as e:
            logger.error(f"Error fetching audit logs: {e}")
            return []

    async def search_group_members(self, group_id: str, query: str = None, limit: int = 50, offset: int = 0) -> list:
        """Search group members"""
        try:
            params = {"n": limit, "offset": offset}
            if query:
                params["query"] = query
                
            response = await self._request(
                "GET",
                f"/groups/{group_id}/members",
                params=params,
            )
            
            if response.status_code == 200:
                return response.json()
            return []
            
        except Exception as e:
            logger.error(f"Error searching group members: {e}")
            return []

    async def get_group_online_members(self, group_id: str, limit: int = 1000) -> List[Dict]:
        """
        Fetch all online members of a group.
        Since the API doesn't support filtering by 'online' directly for groups,
        we fetch members and filter client-side.
        """
        online_members = []
        offset = 0
        batch_size = 100
        
        logger.debug(f"[DEBUG] Fetching online members for group {group_id} (limit={limit})")
        
        while len(online_members) < limit:
            try:
                batch = await self.search_group_members(group_id, limit=batch_size, offset=offset)
                
                if not batch:
                    logger.debug(f"[DEBUG] No more members found at offset {offset}")
                    break
                
                # Filter for online members
                # Group member objects have different structure than regular users
                for member in batch:
                    user_data = member.get("user", member)
                    user_id = member.get("userId") or user_data.get("id")
                    display_name = user_data.get("displayName", "Unknown")
                    status = user_data.get("status", "offline")
                    location = user_data.get("location", "")
                    
                    # Consider "online" as: status is online/active, OR has a valid location
                    is_online = (
                        status in ["active", "join me", "ask me", "busy"] or
                        (location and location not in ["", "offline", "private"])
                    )
                    
                    if is_online:
                        online_members.append({
                            "userId": user_id,
                            "displayName": display_name,
                            "status": status,
                            "location": location,
                            "user": user_data,
                            "member": member,
                        })
                
                logger.debug(f"[DEBUG] Batch {offset//batch_size + 1}: {len(batch)} members, {len(online_members)} online so far")
                
                if len(batch) < batch_size:
                    break
                    
                offset += batch_size
                
            except Exception as e:
                logger.error(f"[DEBUG] Error fetching members at offset {offset}: {e}")
                break
        
        logger.info(f"Found {len(online_members)} online members in group {group_id}")
        return online_members[:limit]

    async def handle_join_request(self, group_id: str, user_id: str, action: str = "accept") -> bool:
        """
        Handle a group join request.
        
        Args:
            group_id: The group ID
            user_id: The requesting user ID (usr_...)
            action: 'accept' or 'reject' (maps to 'deny' in API)
            
        Returns:
            True if successful
        """
        try:
            # VRChat API uses PUT with JSON body containing action
            # Action must be "accept" or "reject"
            api_action = "accept" if action.lower() == "accept" else "reject"
            
            response = await self._request(
                "PUT",
                f"/groups/{group_id}/requests/{user_id}",
                json={"action": api_action},
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"Join request {action}ed for {user_id}")
                return True
            else:
                logger.warning(f"Failed to {action} join request: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error handling join request: {e}")
            return False

    async def kick_user(self, group_id: str, user_id: str) -> bool:
        """Kick (remove) a user from the group"""
        try:
            response = await self._request(
                "DELETE",
                f"/groups/{group_id}/members/{user_id}",
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"Kicked user {user_id} from group {group_id}")
                return True
            else:
                logger.warning(f"Failed to kick user: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error kicking user: {e}")
            return False

    async def ban_user(self, group_id: str, user_id: str) -> bool:
        """Ban a user from the group"""
        try:
            response = await self._request(
                "POST",
                f"/groups/{group_id}/bans",
                json={"userId": user_id},
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Banned user {user_id} from group {group_id}")
                return True
            else:
                logger.warning(f"Failed to ban user: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error banning user: {e}")
            return False

    async def unban_user(self, group_id: str, user_id: str) -> bool:
        """Unban a user from the group"""
        try:
            response = await self._request(
                "DELETE",
                f"/groups/{group_id}/bans/{user_id}",
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"Unbanned user {user_id} from group {group_id}")
                return True
            else:
                logger.warning(f"Failed to unban user: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error unbanning user: {e}")
            return False

    async def invite_user_to_group(self, group_id: str, user_id: str) -> bool:
        """Invite a user to join the group"""
        try:
            response = await self._request(
                "POST",
                f"/groups/{group_id}/invites",
                json={"userId": user_id},
            )
            
            return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Error inviting user to group: {e}")
            return False

    async def get_group_roles(self, group_id: str) -> list:
        """Fetch roles for a group"""
        try:
            response = await self._request("GET", f"/groups/{group_id}/roles")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error fetching group roles: {e}")
            return []
