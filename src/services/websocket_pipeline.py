"""
VRChat WebSocket Pipeline Service
==================================
Connects to VRChat's real-time pipeline for push notifications.
This eliminates the need for constant API polling.

Events received:
- friend-online, friend-offline, friend-update, friend-location
- notification (invites, friend requests, etc.)
- group-member-updated, group-joined, group-left
- user-update, user-location
- instance-queue events
"""

import asyncio
import json
import websockets
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime
from services.debug_logger import get_logger

logger = get_logger("websocket.pipeline")

PIPELINE_URL = "wss://pipeline.vrchat.cloud"


class VRChatPipeline:
    """
    Real-time WebSocket connection to VRChat's pipeline.
    Receives push notifications for friend status, group updates, etc.
    """
    
    def __init__(self):
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._auth_token: Optional[str] = None
        self._listeners: Dict[str, List[Callable]] = {}
        self._running = False
        self._reconnect_delay = 5  # seconds
        self._last_message = ""  # Dedupe spam
        self._connection_task: Optional[asyncio.Task] = None
        
    def add_listener(self, event_type: str, callback: Callable[[Dict[str, Any]], None]):
        """
        Add a listener for a specific event type.
        
        Event types:
        - "friend-online", "friend-offline", "friend-update", "friend-location"
        - "notification", "notification-v2"
        - "group-member-updated", "group-joined", "group-left"
        - "user-update", "user-location"
        - "*" for all events
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        if callback not in self._listeners[event_type]:
            self._listeners[event_type].append(callback)
            
    def remove_listener(self, event_type: str, callback: Callable):
        """Remove a listener"""
        if event_type in self._listeners and callback in self._listeners[event_type]:
            self._listeners[event_type].remove(callback)
    
    async def connect(self, auth_token: str):
        """
        Connect to VRChat pipeline with auth token.
        The token comes from GET /auth endpoint.
        """
        self._auth_token = auth_token
        self._running = True
        
        # Cancel any existing connection task
        if self._connection_task and not self._connection_task.done():
            self._connection_task.cancel()
            
        self._connection_task = asyncio.create_task(self._connection_loop())
        logger.info("Pipeline connection started")
        
    async def disconnect(self):
        """Disconnect from pipeline"""
        self._running = False
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception as e:
                logger.debug(f"Error closing websocket: {e}")
            self._websocket = None
            
        if self._connection_task:
            self._connection_task.cancel()
            try:
                await self._connection_task
            except asyncio.CancelledError:
                pass
            self._connection_task = None
            
        logger.info("Pipeline disconnected")
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to pipeline"""
        return self._websocket is not None and self._websocket.open
    
    async def _connection_loop(self):
        """Main connection loop with auto-reconnect"""
        while self._running:
            try:
                url = f"{PIPELINE_URL}/?auth={self._auth_token}"
                
                async with websockets.connect(
                    url,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5
                ) as ws:
                    self._websocket = ws
                    logger.info("Pipeline connected")
                    self._emit("connected", {"timestamp": datetime.now().isoformat()})
                    
                    # Listen for messages
                    async for message in ws:
                        await self._handle_message(message)
                        
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"Pipeline connection closed: {e}")
            except asyncio.CancelledError:
                logger.debug("Pipeline connection cancelled")
                break
            except Exception as e:
                logger.error(f"Pipeline error: {e}")
            
            # Connection lost
            self._websocket = None
            self._emit("disconnected", {"timestamp": datetime.now().isoformat()})
            
            if self._running:
                logger.info(f"Reconnecting in {self._reconnect_delay}s...")
                await asyncio.sleep(self._reconnect_delay)
    
    async def _handle_message(self, raw_message: str):
        """Parse and handle a pipeline message"""
        # Dedupe spam
        if raw_message == self._last_message:
            return
        self._last_message = raw_message
        
        try:
            data = json.loads(raw_message)
            
            # Parse nested content
            if "content" in data and isinstance(data["content"], str):
                try:
                    data["content"] = json.loads(data["content"])
                except:
                    pass
            
            event_type = data.get("type", "unknown")
            content = data.get("content", {})
            
            # Handle errors
            if "err" in data:
                logger.error(f"Pipeline error: {data['err']}")
                self._emit("error", {"error": data["err"]})
                return
            
            logger.debug(f"Pipeline event: {event_type}")
            
            # Emit to specific listeners
            self._emit(event_type, content)
            
            # Also emit to wildcard listeners
            self._emit("*", {"type": event_type, "content": content})
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse pipeline message: {e}")
        except Exception as e:
            logger.error(f"Error handling pipeline message: {e}")
    
    def _emit(self, event_type: str, data: Dict[str, Any]):
        """Emit an event to all listeners"""
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                try:
                    # Check if callback is async
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(data))
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"Error in pipeline listener: {e}")


class PipelineEventHandler:
    """
    Default event handlers for common pipeline events.
    Extend this to customize behavior.
    """
    
    def __init__(self, pipeline: VRChatPipeline):
        self.pipeline = pipeline
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Register default event handlers"""
        # Friend events
        self.pipeline.add_listener("friend-online", self._on_friend_online)
        self.pipeline.add_listener("friend-offline", self._on_friend_offline)
        self.pipeline.add_listener("friend-update", self._on_friend_update)
        self.pipeline.add_listener("friend-location", self._on_friend_location)
        self.pipeline.add_listener("friend-add", self._on_friend_add)
        self.pipeline.add_listener("friend-delete", self._on_friend_delete)
        
        # Notification events
        self.pipeline.add_listener("notification", self._on_notification)
        self.pipeline.add_listener("notification-v2", self._on_notification)
        
        # Group events
        self.pipeline.add_listener("group-member-updated", self._on_group_member_updated)
        self.pipeline.add_listener("group-joined", self._on_group_joined)
        self.pipeline.add_listener("group-left", self._on_group_left)
        
        # User events
        self.pipeline.add_listener("user-update", self._on_user_update)
        
    def _on_friend_online(self, data: Dict):
        """Friend came online"""
        user_id = data.get("userId", "")
        location = data.get("location", "")
        logger.info(f"Friend online: {user_id} at {location}")
        
    def _on_friend_offline(self, data: Dict):
        """Friend went offline"""
        user_id = data.get("userId", "")
        logger.info(f"Friend offline: {user_id}")
        
    def _on_friend_update(self, data: Dict):
        """Friend updated their profile"""
        user = data.get("user", {})
        logger.debug(f"Friend update: {user.get('displayName', 'Unknown')}")
        
    def _on_friend_location(self, data: Dict):
        """Friend changed location"""
        user_id = data.get("userId", "")
        location = data.get("location", "")
        logger.debug(f"Friend location: {user_id} -> {location}")
        
    def _on_friend_add(self, data: Dict):
        """New friend added"""
        user_id = data.get("userId", "")
        logger.info(f"Friend added: {user_id}")
        
    def _on_friend_delete(self, data: Dict):
        """Friend removed"""
        user_id = data.get("userId", "")
        logger.info(f"Friend removed: {user_id}")
        
    def _on_notification(self, data: Dict):
        """Received a notification (invite, friend request, etc.)"""
        noty_type = data.get("type", "unknown")
        sender_id = data.get("senderUserId", "")
        logger.info(f"Notification: {noty_type} from {sender_id}")
        
    def _on_group_member_updated(self, data: Dict):
        """Group member updated"""
        member = data.get("member", {})
        group_id = member.get("groupId", "")
        user_id = member.get("userId", "")
        logger.info(f"Group member updated: {user_id} in {group_id}")
        
    def _on_group_joined(self, data: Dict):
        """Joined a group"""
        group_id = data.get("groupId", "")
        logger.info(f"Joined group: {group_id}")
        
    def _on_group_left(self, data: Dict):
        """Left a group"""
        group_id = data.get("groupId", "")
        logger.info(f"Left group: {group_id}")
        
    def _on_user_update(self, data: Dict):
        """Current user updated"""
        user = data.get("user", {})
        logger.debug(f"User update: {user.get('displayName', 'Self')}")


# Singleton instance
_pipeline: Optional[VRChatPipeline] = None
_handler: Optional[PipelineEventHandler] = None


def get_pipeline() -> VRChatPipeline:
    """Get the singleton pipeline instance"""
    global _pipeline
    if _pipeline is None:
        _pipeline = VRChatPipeline()
    return _pipeline


def get_event_handler() -> PipelineEventHandler:
    """Get the singleton event handler"""
    global _handler
    if _handler is None:
        _handler = PipelineEventHandler(get_pipeline())
    return _handler


async def connect_pipeline(api_client) -> bool:
    """
    Connect to VRChat pipeline using the API client.
    Returns True if connected successfully.
    """
    pipeline = get_pipeline()
    
    try:
        # Get auth token from VRChat API
        auth_response = await api_client._request("GET", "/auth")
        if not auth_response or not auth_response.get("ok"):
            logger.error("Failed to get auth token for pipeline")
            return False
            
        token = auth_response.get("token")
        if not token:
            logger.error("No token in auth response")
            return False
            
        # Initialize default event handler
        get_event_handler()
        
        # Connect
        await pipeline.connect(token)
        return True
        
    except Exception as e:
        logger.error(f"Failed to connect pipeline: {e}")
        return False


async def disconnect_pipeline():
    """Disconnect from the pipeline"""
    pipeline = get_pipeline()
    await pipeline.disconnect()
