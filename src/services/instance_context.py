"""
Instance Context Service
========================
Tracks the user's current VRChat instance (from local logs) and compares
it against group instances (from API) to determine moderation context.

This enables contextual features:
- If you're IN a group instance you moderate, show enhanced features
- If you're NOT in a group instance, show limited features
- Real-time updates as you switch instances

State Machine:
    OFFLINE -> Not in VRChat / No log data
    IN_UNTRACKED -> In an instance not related to any moderated group
    IN_GROUP_INSTANCE -> In an instance that belongs to one of your groups
"""

import asyncio
import logging
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from services.debug_logger import get_logger

logger = get_logger("instance.context")


class InstanceContextState(Enum):
    """Current moderation context state"""
    OFFLINE = "offline"                     # Not in any instance
    IN_UNTRACKED = "in_untracked"           # In an instance, but not a group instance
    IN_GROUP_INSTANCE = "in_group_instance" # In a group instance you moderate


@dataclass
class InstanceDetails:
    """Details about the current instance"""
    world_id: Optional[str] = None
    instance_id: Optional[str] = None
    group_id: Optional[str] = None
    location: Optional[str] = None  # Full location string: wrld_xxx:instance_yyy
    world_name: Optional[str] = None
    member_count: int = 0
    is_group_instance: bool = False
    group_name: Optional[str] = None
    timestamp: Optional[str] = None


@dataclass
class InstanceContext:
    """Full context about the user's moderation state"""
    state: InstanceContextState = InstanceContextState.OFFLINE
    current_instance: Optional[InstanceDetails] = None
    matching_group: Optional[Dict] = None  # The group dict if in a group instance
    available_features: List[str] = field(default_factory=list)
    last_updated: Optional[datetime] = None


class InstanceContextService:
    """
    Service that correlates local VRChat logs with group instance data
    to determine if the user is actively moderating a group instance.
    
    Features enabled when IN_GROUP_INSTANCE:
    - Real-time player monitoring with moderation actions
    - Quick-kick/ban from live instance
    - Watchlist alerts (in-game notifications)
    - Player join/leave tracking with mod context
    
    Features always available:
    - Watchlist management
    - Join request processing
    - Ban list management
    - Settings
    """
    
    # Feature flags based on context
    FEATURES_ALWAYS_AVAILABLE = [
        "watchlist_management",
        "join_requests",
        "ban_management",
        "member_search",
        "settings",
        "audit_logs",
    ]
    
    FEATURES_REQUIRE_GROUP_INSTANCE = [
        "live_moderation",      # Kick/ban from live view
        "in_game_alerts",       # Send self-invite notifications
        "player_monitoring",    # Real-time join/leave with actions
        "quick_actions",        # Fast mod actions on active players
    ]
    
    def __init__(self):
        self._context = InstanceContext()
        self._listeners: List[Callable[[InstanceContext], None]] = []
        self._group_instances_cache: Dict[str, List[Dict]] = {}  # group_id -> instances
        self._my_groups: List[Dict] = []
        self._api = None  # Set via set_api()
        self._log_watcher = None  # Set via attach_log_watcher()
        self._refresh_task: Optional[asyncio.Task] = None
        self._refresh_interval = 60.0  # Refresh group instances every 60s
        self._running = False
        
    def set_api(self, api):
        """Set the VRChat API client for fetching group instances"""
        self._api = api
        
    def attach_log_watcher(self, log_watcher):
        """
        Attach to a LogWatcher to receive instance change events.
        Call this after LogWatcher is initialized.
        """
        self._log_watcher = log_watcher
        self._log_watcher.add_listener(self._on_log_event)
        logger.info("InstanceContextService attached to LogWatcher")
        
        # Initialize with current state from log watcher
        if log_watcher.current_world_id:
            self._update_current_instance(
                world_id=log_watcher.current_world_id,
                instance_id=log_watcher.current_instance_id,
                group_id=log_watcher.current_group_id,
            )
    
    def set_groups(self, groups: List[Dict]):
        """
        Set the list of groups the user moderates.
        Called when groups are loaded in main app.
        """
        self._my_groups = groups
        logger.info(f"InstanceContextService: Tracking {len(groups)} groups")
        
    def add_listener(self, callback: Callable[[InstanceContext], None]):
        """Add a listener for context changes"""
        if callback not in self._listeners:
            self._listeners.append(callback)
            
    def remove_listener(self, callback: Callable):
        """Remove a context change listener"""
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def get_context(self) -> InstanceContext:
        """Get the current instance context"""
        return self._context
    
    def is_in_group_instance(self) -> bool:
        """Quick check if user is in a moderated group instance"""
        return self._context.state == InstanceContextState.IN_GROUP_INSTANCE
    
    def is_feature_available(self, feature: str) -> bool:
        """Check if a specific feature is available in current context"""
        if feature in self.FEATURES_ALWAYS_AVAILABLE:
            return True
        if feature in self.FEATURES_REQUIRE_GROUP_INSTANCE:
            return self.is_in_group_instance()
        return False
    
    def get_available_features(self) -> List[str]:
        """Get list of features available in current context"""
        features = list(self.FEATURES_ALWAYS_AVAILABLE)
        if self.is_in_group_instance():
            features.extend(self.FEATURES_REQUIRE_GROUP_INSTANCE)
        return features
    
    def get_current_group(self) -> Optional[Dict]:
        """Get the group dict if currently in a group instance, else None"""
        return self._context.matching_group
    
    def has_live_data(self) -> bool:
        """
        Check if we have live log data (user is in any instance).
        
        Returns True if user is in any instance (tracked or untracked).
        Returns False if offline/no log data.
        
        Use this to show/hide live monitoring features.
        """
        return self._context.state != InstanceContextState.OFFLINE
    
    async def start(self):
        """Start the background refresh loop for group instances"""
        if self._running:
            return
        self._running = True
        self._refresh_task = asyncio.create_task(self._refresh_loop())
        logger.info("InstanceContextService started")
        
    async def stop(self):
        """Stop the background refresh loop"""
        self._running = False
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        logger.info("InstanceContextService stopped")
    
    async def refresh_group_instances(self):
        """
        Fetch current instances for all moderated groups.
        This is called periodically and on-demand.
        """
        if not self._api or not self._my_groups:
            return
            
        logger.debug(f"Refreshing group instances for {len(self._my_groups)} groups")
        
        for group in self._my_groups:
            group_id = group.get("id")
            if not group_id:
                continue
                
            try:
                instances = await self._api.get_group_instances(group_id)
                self._group_instances_cache[group_id] = instances
                logger.debug(f"Group {group.get('name')}: {len(instances)} active instances")
            except Exception as e:
                logger.error(f"Error fetching instances for group {group_id}: {e}")
        
        # Re-evaluate current context after refresh
        if self._log_watcher and self._log_watcher.current_world_id:
            self._update_current_instance(
                world_id=self._log_watcher.current_world_id,
                instance_id=self._log_watcher.current_instance_id,
                group_id=self._log_watcher.current_group_id,
            )
    
    async def _refresh_loop(self):
        """Background loop to periodically refresh group instances"""
        while self._running:
            try:
                await self.refresh_group_instances()
            except Exception as e:
                logger.error(f"Error in refresh loop: {e}")
            
            await asyncio.sleep(self._refresh_interval)
    
    def _on_log_event(self, event: Dict[str, Any]):
        """Handle events from LogWatcher"""
        event_type = event.get("type")
        
        if event_type == "instance_change":
            self._update_current_instance(
                world_id=event.get("world_id"),
                instance_id=event.get("instance_id"),
                group_id=event.get("group_id"),
                timestamp=event.get("timestamp"),
            )
        elif event_type == "disconnected":
            self._set_offline()
        elif event_type == "rotation":
            # Log file rotated, wait for new instance data
            self._set_offline()
    
    def _update_current_instance(
        self,
        world_id: Optional[str],
        instance_id: Optional[str],
        group_id: Optional[str],
        timestamp: Optional[str] = None,
    ):
        """
        Update current instance and determine moderation context.
        
        The group_id from logs tells us the group associated with the instance.
        We verify this against our cached group instances to confirm we have
        moderation access.
        """
        if not world_id or not instance_id:
            self._set_offline()
            return
        
        location = f"{world_id}:{instance_id}"
        
        # Create instance details
        instance_details = InstanceDetails(
            world_id=world_id,
            instance_id=instance_id,
            group_id=group_id,
            location=location,
            timestamp=timestamp or datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
        )
        
        # Check if this is a group instance we moderate
        matching_group = None
        
        if group_id:
            # Direct match from log-parsed group ID
            for group in self._my_groups:
                if group.get("id") == group_id:
                    matching_group = group
                    instance_details.is_group_instance = True
                    instance_details.group_name = group.get("name")
                    break
        
        # Also check cached instances for location match
        # (in case the group_id wasn't in the log, but we know about the instance)
        if not matching_group:
            for grp_id, instances in self._group_instances_cache.items():
                for inst in instances:
                    inst_location = inst.get("location", "")
                    inst_world = inst.get("world", {}).get("id", "")
                    inst_instance_id = inst.get("instanceId", "")
                    
                    # Match by full location or world+instance
                    if (inst_location == location or 
                        (inst_world == world_id and instance_id.startswith(inst_instance_id))):
                        # Found matching instance
                        for group in self._my_groups:
                            if group.get("id") == grp_id:
                                matching_group = group
                                instance_details.is_group_instance = True
                                instance_details.group_name = group.get("name")
                                instance_details.world_name = inst.get("world", {}).get("name")
                                instance_details.member_count = inst.get("memberCount", 0)
                                break
                        break
                if matching_group:
                    break
        
        # Determine state
        if matching_group:
            new_state = InstanceContextState.IN_GROUP_INSTANCE
            logger.info(f"✅ In group instance: {matching_group.get('name')} @ {location}")
        else:
            new_state = InstanceContextState.IN_UNTRACKED
            logger.info(f"📍 In untracked instance: {location}")
        
        # Update context
        self._context = InstanceContext(
            state=new_state,
            current_instance=instance_details,
            matching_group=matching_group,
            available_features=self.get_available_features(),
            last_updated=datetime.now(),
        )
        
        # Notify listeners
        self._emit()
    
    def _set_offline(self):
        """Set context to offline state"""
        if self._context.state != InstanceContextState.OFFLINE:
            logger.info("📴 Instance context: OFFLINE")
            
        self._context = InstanceContext(
            state=InstanceContextState.OFFLINE,
            current_instance=None,
            matching_group=None,
            available_features=self.get_available_features(),
            last_updated=datetime.now(),
        )
        self._emit()
    
    def _emit(self):
        """Notify all listeners of context change"""
        for listener in self._listeners:
            try:
                listener(self._context)
            except Exception as e:
                logger.error(f"Error in context listener: {e}")


# Singleton instance
_context_service: Optional[InstanceContextService] = None


def get_instance_context() -> InstanceContextService:
    """Get or create the singleton InstanceContextService"""
    global _context_service
    if not _context_service:
        _context_service = InstanceContextService()
    return _context_service
