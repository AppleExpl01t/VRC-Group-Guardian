"""
Watchlist Alert Service
=======================
Monitors VRChat log events and sends notifications when
watchlisted users join the current instance.

Supports multiple notification methods:
1. XSOverlay - VR-native toast notifications (preferred)
2. VRChat invite messages - Fallback in-game notifications
"""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Import XSOverlay service (lazy import to avoid circular deps)
_xsoverlay_service = None

def _get_xsoverlay():
    """Lazy import XSOverlay service"""
    global _xsoverlay_service
    if _xsoverlay_service is None:
        try:
            from services.xsoverlay import get_xsoverlay_service
            _xsoverlay_service = get_xsoverlay_service()
        except ImportError:
            logger.warning("XSOverlay service not available")
    return _xsoverlay_service

# Default tags that users will likely want
DEFAULT_TAGS = [
    {"name": "Crasher", "emoji": "🚨", "color": "#FF4444", "description": "Known to crash sessions"},
    {"name": "Predator", "emoji": "⚠️", "color": "#FF0000", "description": "Dangerous individual"},
    {"name": "Zoophile", "emoji": "🚫", "color": "#880000", "description": "Known zoophile"},
    {"name": "Suspicious", "emoji": "👀", "color": "#FF9800", "description": "Suspicious behavior"},
    {"name": "Bad Vibes", "emoji": "💀", "color": "#9C27B0", "description": "Generally unpleasant"},
    {"name": "VIP", "emoji": "⭐", "color": "#FFD700", "description": "Very important person"},
    {"name": "Friend", "emoji": "💚", "color": "#4CAF50", "description": "Trusted friend"},
    {"name": "Mute Evader", "emoji": "🔇", "color": "#607D8B", "description": "Uses alts to evade mutes"},
    {"name": "Bot/Alt", "emoji": "🤖", "color": "#795548", "description": "Bot or alternate account"},
    {"name": "Harassment", "emoji": "📛", "color": "#E91E63", "description": "Known harasser"},
    {"name": "Ripper", "emoji": "🏴‍☠️", "color": "#673AB7", "description": "Rips avatars/worlds"},
    {"name": "Leaker", "emoji": "💧", "color": "#03A9F4", "description": "Leaks private content"},
]


class WatchlistAlertService:
    """
    Service that monitors player joins and sends notifications
    for watchlisted users.
    
    Supports:
    - XSOverlay: VR-native toast notifications (preferred)
    - VRChat Invite: In-game notification fallback
    """
    
    # Alert message must fit in 64 characters (for VRC invite fallback)
    MAX_MESSAGE_LENGTH = 64
    
    # Use slot 11 (last slot) for dynamic alerts
    ALERT_SLOT = 11
    
    def __init__(self, api_client=None):
        """
        Initialize the alert service.
        
        Args:
            api_client: VRChatAPI instance for sending notifications
        """
        self.api = api_client
        self.enabled = True
        self.last_alert_time: Optional[datetime] = None
        self._current_world_id: Optional[str] = None
        self._current_instance_id: Optional[str] = None
        self._pending_alerts: List[Dict] = []
        self._alert_cooldown = 2.0  # seconds between alerts
        
        # XSOverlay settings
        self.xsoverlay_enabled = True  # Prefer XSOverlay when available
        self.xsoverlay_connected = False
        self.vrc_invite_fallback = True  # Fall back to VRC invites if XSOverlay unavailable
        
    def set_api(self, api_client):
        """Set the API client (can be done after init)"""
        self.api = api_client
        
    def update_instance(self, world_id: str, instance_id: str):
        """Update the current instance location (called by log watcher)"""
        self._current_world_id = world_id
        self._current_instance_id = instance_id
        logger.debug(f"Alert service: instance updated to {world_id}:{instance_id}")
        
    def get_current_instance(self) -> Optional[str]:
        """Get the current instance location as a string"""
        if self._current_world_id and self._current_instance_id:
            return f"{self._current_world_id}:{self._current_instance_id}"
        return None
    
    def format_alert_message(self, username: str, tags: List[str]) -> str:
        """
        Format an alert message that fits in 64 characters.
        
        Format priority:
        1. "⚠️ WATCHLIST: Username [Tag]"
        2. "⚠️ Username [Tag]" (if too long)
        3. "⚠️ Username" (if still too long)
        
        Args:
            username: Display name of the user
            tags: List of tag names
            
        Returns:
            Formatted message <= 64 characters
        """
        # Get primary tag (first one)
        primary_tag = tags[0] if tags else "Watchlist"
        
        # Try full format: "⚠️ WATCHLIST: Username [Tag]"
        full_msg = f"⚠️ WATCHLIST: {username} [{primary_tag}]"
        if len(full_msg) <= self.MAX_MESSAGE_LENGTH:
            return full_msg
        
        # Try shorter: "⚠️ Username [Tag]"
        short_msg = f"⚠️ {username} [{primary_tag}]"
        if len(short_msg) <= self.MAX_MESSAGE_LENGTH:
            return short_msg
        
        # Try minimal: "⚠️ Username"
        minimal_msg = f"⚠️ {username}"
        if len(minimal_msg) <= self.MAX_MESSAGE_LENGTH:
            return minimal_msg
        
        # Truncate username if necessary
        max_name_len = self.MAX_MESSAGE_LENGTH - 3  # "⚠️ " prefix
        return f"⚠️ {username[:max_name_len]}"
    
    async def send_alert(self, username: str, user_id: str, tags: List[str], user_thumbnail: Optional[str] = None) -> bool:
        """
        Send an alert notification when a watchlisted user joins.
        
        Tries XSOverlay first for VR-native notifications, then falls back
        to VRChat invite messages if XSOverlay is unavailable.
        
        Args:
            username: Display name of the watchlisted user
            user_id: VRChat user ID
            tags: List of tag names for this user
            user_thumbnail: Optional base64 user thumbnail for XSOverlay
            
        Returns:
            True if alert sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Alert service disabled")
            return False
        
        # Determine severity based on tags
        danger_tags = {"Crasher", "Predator", "Zoophile"}
        warning_tags = {"Suspicious", "Harassment", "Bad Vibes", "Mute Evader"}
        
        severity = "info"
        for tag in tags:
            if tag in danger_tags:
                severity = "danger"
                break
            elif tag in warning_tags:
                severity = "warning"
        
        # Try XSOverlay first (preferred VR-native method)
        xso_sent = False
        if self.xsoverlay_enabled:
            xso = _get_xsoverlay()
            if xso:
                try:
                    xso_sent = await xso.send_watchlist_alert(
                        username=username,
                        tags=tags,
                        user_thumbnail=user_thumbnail,
                        severity=severity
                    )
                    if xso_sent:
                        self.xsoverlay_connected = True
                        self.last_alert_time = datetime.now()
                        logger.info(f"✅ XSOverlay alert sent: {username} [{', '.join(tags)}]")
                        
                        # Also trigger haptics for danger alerts
                        if severity == "danger" and xso.config.haptics_enabled:
                            await xso.play_haptics(duration_ms=200, intensity=1.0)
                        
                        return True
                except Exception as e:
                    logger.warning(f"XSOverlay alert failed: {e}")
                    self.xsoverlay_connected = False
        
        # Fall back to VRC invite if XSOverlay failed or disabled
        if not xso_sent and self.vrc_invite_fallback:
            return await self._send_vrc_invite_alert(username, user_id, tags)
        
        return False
    
    async def _send_vrc_invite_alert(self, username: str, user_id: str, tags: List[str]) -> bool:
        """
        Legacy VRC invite-based alert (fallback method).
        
        Uses the Reset → Edit → Self-Invite pattern to bypass the 60-minute
        message edit cooldown and include a custom alert message.
        """
        if not self.api:
            logger.warning("No API client set for alert service")
            return False
            
        instance = self.get_current_instance()
        if not instance:
            logger.warning("Cannot send alert - no current instance")
            return False
        
        try:
            # Format the alert message
            message = self.format_alert_message(username, tags)
            logger.info(f"Sending VRC invite alert: {message}")
            
            # Try to set up custom message (may fail due to rate limit)
            message_ready = False
            
            # CHECK EXISTING MESSAGE FIRST to avoid rate limits
            try:
                current_slots = await self.api.get_invite_messages("message")
                
                # Find our slot
                matching_slot = None
                for slot in current_slots:
                    if slot.get("slot") == self.ALERT_SLOT:
                        matching_slot = slot
                        break
                
                if matching_slot and matching_slot.get("message") == message:
                    message_ready = True
            except Exception as e:
                # Continue to update attempt
                pass
            
            
            if not message_ready:
                # Step 1: Reset the slot (bypasses 60-min cooldown)
                try:
                    reset_ok = await self.api.reset_invite_message("message", self.ALERT_SLOT)
                    
                    if reset_ok:
                        # Step 2: Update with our alert message
                        await asyncio.sleep(0.5)  # Increased delay for safety
                        update_ok = await self.api.update_invite_message("message", self.ALERT_SLOT, message)
                        
                        if update_ok:
                            message_ready = True
                            await asyncio.sleep(0.5)  # Increased delay
                except Exception as e:
                    # Continue with fallback
                    pass
            
            # Step 3: Send self-invite
            
            if message_ready:
                # Use message slot for custom message
                invite_ok = await self.api.self_invite(
                    self._current_world_id,
                    self._current_instance_id,
                    message_slot=self.ALERT_SLOT
                )
            else:
                # Fallback to simple invite (no custom message)
                invite_ok = await self.api.self_invite(
                    self._current_world_id,
                    self._current_instance_id
                )
            
            if invite_ok:
                self.last_alert_time = datetime.now()
                if message_ready:
                    logger.info(f"✅ VRC invite alert sent: {message}")
                else:
                    logger.info(f"✅ VRC invite alert sent (generic)")
                return True
            else:
                logger.warning("Self-invite failed - alert may not appear")
                return False
                
        except Exception as e:
            logger.error(f"Error sending VRC invite alert: {e}")
            return False
    
    def on_event(self, event: Dict[str, Any]):
        """
        Handle log watcher events.
        
        Call this from the log watcher callback to process events.
        
        Args:
            event: Event dict from log watcher
        """
        event_type = event.get("type")
        
        # Update instance location
        if event_type == "instance_change":
            self.update_instance(
                event.get("world_id", ""),
                event.get("instance_id", "")
            )
            return
        
        # Check for watchlisted player joins
        if event_type == "player_join":
            if event.get("is_watchlisted"):
                # Queue alert for async processing
                self._pending_alerts.append({
                    "username": event.get("display_name", "Unknown"),
                    "user_id": event.get("user_id", ""),
                    "tags": event.get("tags", []),
                })
                
    async def process_pending_alerts(self):
        """
        Process any pending alerts asynchronously.
        
        Call this periodically from the main async loop.
        """
        while self._pending_alerts:
            alert = self._pending_alerts.pop(0)
            await self.send_alert(
                alert["username"],
                alert["user_id"],
                alert["tags"]
            )
            # Brief delay between multiple alerts
            if self._pending_alerts:
                await asyncio.sleep(self._alert_cooldown)
    
    async def connect_xsoverlay(self) -> bool:
        """
        Connect to XSOverlay for VR notifications.
        
        Returns:
            True if connected successfully
        """
        if not self.xsoverlay_enabled:
            return False
            
        xso = _get_xsoverlay()
        if xso:
            connected = await xso.connect()
            self.xsoverlay_connected = connected
            return connected
        return False
    
    async def disconnect_xsoverlay(self):
        """Disconnect from XSOverlay"""
        xso = _get_xsoverlay()
        if xso:
            await xso.disconnect()
            self.xsoverlay_connected = False
    
    async def test_xsoverlay(self) -> bool:
        """
        Send a test notification to XSOverlay.
        
        Returns:
            True if test notification sent successfully
        """
        xso = _get_xsoverlay()
        if xso:
            return await xso.test_notification()
        return False
    
    def get_xsoverlay_status(self) -> dict:
        """
        Get the current XSOverlay status.
        
        Returns:
            Dict with enabled, connected status
        """
        xso = _get_xsoverlay()
        return {
            "enabled": self.xsoverlay_enabled,
            "connected": self.xsoverlay_connected,
            "available": xso is not None,
            "vrc_fallback": self.vrc_invite_fallback,
        }


# Singleton instance
_alert_service: Optional[WatchlistAlertService] = None

def get_alert_service(api_client=None) -> WatchlistAlertService:
    """Get or create the singleton alert service instance"""
    global _alert_service
    if not _alert_service:
        _alert_service = WatchlistAlertService(api_client)
    elif api_client:
        _alert_service.set_api(api_client)
    return _alert_service
