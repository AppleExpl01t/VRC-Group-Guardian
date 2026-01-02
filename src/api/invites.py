"""
Invites Mixin
==============
Invite management functionality including instance invites and notification alerts.
"""

from typing import Optional, Dict, List
from services.debug_logger import get_logger

logger = get_logger("api.invites")


class InvitesMixin:
    """
    Mixin providing invite-related functionality:
    - Send instance invites
    - Self-invite for notifications
    - Manage invite messages
    - Send alert notifications
    """
    
    async def self_invite(self, world_id: str, instance_id: str, message_slot: int = None) -> bool:
        """
        Send an invite to yourself at the specified instance.
        This creates a notification in VRChat that can be used for alerts.
        
        If message_slot is specified, uses POST /invite/{userId} with messageSlot
        to send a custom message.
        
        Args:
            world_id: The world ID
            instance_id: The instance ID
            message_slot: Optional slot number (0-11) for custom message
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self._current_user:
                logger.error("self_invite failed: no current user")
                return False
            
            user_id = self._current_user.get("id")
            if not user_id:
                logger.error("self_invite failed: no user ID")
                return False
            
            location = f"{world_id}:{instance_id}"
            
            if message_slot is not None:
                # Use POST /invite/{userId} with messageSlot
                logger.debug(f"Sending self-invite with messageSlot={message_slot}")
                
                response = await self._request(
                    "POST",
                    f"/invite/{user_id}",
                    json={
                        "instanceId": location,
                        "messageSlot": message_slot,
                    },
                )
            else:
                # Use standard invite endpoint
                response = await self._request(
                    "POST",
                    f"/instances/{location}/invite",
                    json={"userId": user_id},
                )
            
            if response.status_code in [200, 201]:
                logger.info(f"Self-invite sent successfully to {location}")
                return True
            else:
                logger.warning(f"Self-invite failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending self-invite: {e}")
            return False
    
    async def get_invite_messages(self, message_type: str = "message") -> Optional[list]:
        """
        Get the list of invite messages for the current user.
        
        Args:
            message_type: Type of messages:
                - 'message' - normal invite messages (default)
                - 'request' - request invite messages
                - 'response' - invite response messages
                - 'requestResponse' - request response messages
            
        Returns:
            List of message objects or None on failure
        """
        try:
            user_id = self._current_user.get("id") if self._current_user else None
            if not user_id:
                logger.error("Cannot get invite messages - not logged in")
                return None
                
            response = await self._request(
                "GET",
                f"/message/{user_id}/{message_type}",
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get invite messages: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting invite messages: {e}")
            return None
    
    async def update_invite_message(self, message_type: str, slot: int, message: str) -> bool:
        """
        Update an invite message slot.
        
        NOTE: There is a 60-minute cooldown on editing invite messages.
        Use reset_invite_message first then this method to bypass the cooldown.
        
        Args:
            message_type: Type of message ('message', 'request', 'response')
            slot: Slot number (0-11)
            message: The new message text (max 64 characters)
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            user_id = self._current_user.get("id") if self._current_user else None
            if not user_id:
                logger.error("Cannot update invite message - not logged in")
                return False
            
            # Truncate message to 64 chars (VRChat limit)
            message = message[:64]
            
            response = await self._request(
                "PUT",
                f"/message/{user_id}/{message_type}/{slot}",
                json={"message": message},
            )
            
            if response.status_code in (200, 204):
                logger.info(f"Updated invite message slot {slot}: '{message}'")
                return True
            else:
                logger.warning(f"Failed to update invite message: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error updating invite message: {e}")
            return False
    
    async def reset_invite_message(self, message_type: str, slot: int) -> bool:
        """
        Reset an invite message slot to its default value.
        
        NOTE: Resetting does NOT trigger the same 60-min cooldown as editing.
        You can reset → edit immediately after each other.
        
        Args:
            message_type: Type of message ('message', 'request', 'response')
            slot: Slot number (0-11)
            
        Returns:
            True if reset successfully, False otherwise
        """
        try:
            user_id = self._current_user.get("id") if self._current_user else None
            if not user_id:
                logger.error("Cannot reset invite message - not logged in")
                return False
            
            response = await self._request(
                "DELETE",
                f"/message/{user_id}/{message_type}/{slot}",
            )
            
            if response.status_code in (200, 204):
                logger.info(f"Reset invite message slot {slot}")
                return True
            else:
                logger.warning(f"Failed to reset invite message: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error resetting invite message: {e}")
            return False
    
    async def send_invite_to_user(self, user_id: str, instance_id: str, message_slot: int = None) -> bool:
        """
        Send an invite notification to a user.
        
        Args:
            user_id: The user to invite
            instance_id: Full instance location (wrld_xxx:instanceId)
            message_slot: Optional slot number for custom message (0-11)
            
        Returns:
            True if invite sent successfully, False otherwise
        """
        try:
            json_data = {"instanceId": instance_id}
            if message_slot is not None:
                json_data["messageSlot"] = message_slot
            
            response = await self._request(
                "POST",
                f"/invite/{user_id}",
                json=json_data,
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Invite sent to {user_id}")
                return True
            else:
                logger.warning(f"Failed to send invite: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error sending invite: {e}")
            return False
    
    async def invite_to_instance(self, user_id: str, world_id: str, instance_id: str, 
                                  world_name: str = None, message_slot: int = None) -> bool:
        """
        Send an instance invite to a user.
        
        Args:
            user_id: The user ID (usr_xxx)
            world_id: The world ID (wrld_xxx)
            instance_id: The instance ID
            world_name: Optional world name (for logging)
            message_slot: Optional slot number for custom message (0-11)
            
        Returns:
            True if successful
        """
        try:
            location = f"{world_id}:{instance_id}"
            
            json_data = {"instanceId": location}
            if message_slot is not None:
                json_data["messageSlot"] = message_slot
            
            response = await self._request(
                "POST",
                f"/invite/{user_id}",
                json=json_data,
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Invited {user_id} to {world_name or location}")
                return True
            else:
                logger.warning(f"Failed to invite to instance: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error inviting to instance: {e}")
            return False
    
    async def send_alert_notification(self, message: str, slot: int = 11) -> bool:
        """
        Send an alert to yourself as a VRChat notification.
        
        This uses the Reset → Edit → Self-Invite trick to send dynamic messages.
        It first resets the slot, then updates it with the message, then self-invites.
        
        Args:
            message: The alert message (max 64 chars)
            slot: Slot to use for the alert (default: 11, the last slot)
            
        Returns:
            True if alert sent successfully, False otherwise
        """
        try:
            # Get current location
            location = await self.get_my_location()
            if not location:
                logger.warning("Cannot send alert - not in an instance")
                return False
            
            world_id = location["world_id"]
            instance_id = location["instance_id"]
            
            # Step 1: Reset the slot
            logger.debug(f"Resetting invite message slot {slot}")
            reset_ok = await self.reset_invite_message("message", slot)
            if not reset_ok:
                logger.warning("Failed to reset invite message slot, trying anyway...")
            
            # Step 2: Update with our message
            logger.debug(f"Updating invite message slot {slot} with: {message}")
            update_ok = await self.update_invite_message("message", slot, message)
            if not update_ok:
                logger.warning("Failed to update invite message slot")
                # Try to send generic invite as fallback
                return await self.self_invite(world_id, instance_id)
            
            # Step 3: Send self-invite with the message slot
            logger.debug(f"Sending self-invite with message slot {slot}")
            return await self.self_invite(world_id, instance_id, message_slot=slot)
            
        except Exception as e:
            logger.error(f"Error sending alert notification: {e}")
            return False
