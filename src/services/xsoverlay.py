"""
XSOverlay Integration Service
=============================
Provides VR-native notifications through XSOverlay's WebSocket API.

XSOverlay is a popular VR overlay that provides desktop access, notifications,
and various utilities within VR. This service connects to its API to send
toast notifications directly to the user's VR headset.

API Documentation: https://xsoverlay-docs.vercel.app
Default Port: 42070 (localhost only)
"""

import asyncio
import json
import logging
import base64
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

logger = logging.getLogger(__name__)


class NotificationType(IntEnum):
    """XSOverlay notification types"""
    DEFAULT = 0        # Uses default settings
    NOTIFICATION = 1   # Standard toast notification
    MEDIA_PLAYER = 2   # Media player notification with controls
    

@dataclass
class XSOverlayConfig:
    """Configuration for XSOverlay connection"""
    host: str = "127.0.0.1"
    
    # UDP port (simple, fire-and-forget like VRCX uses)
    udp_port: int = 42069
    
    # WebSocket port (for advanced features like performance subscription)
    ws_port: int = 42070
    
    # Prefer UDP (simpler, more reliable) over WebSocket
    prefer_udp: bool = True
    
    enabled: bool = True
    auto_reconnect: bool = True
    reconnect_delay: float = 5.0
    max_reconnect_attempts: int = 10
    
    # Notification defaults
    default_duration: float = 3.0
    default_opacity: float = 1.0
    default_height: float = 175.0
    
    # Sound settings
    sound_enabled: bool = True
    custom_sound_path: Optional[str] = None
    
    # Haptic feedback
    haptics_enabled: bool = True
    
    # Performance monitoring
    performance_subscription: bool = True  # Subscribe to performance events
    performance_throttle_enabled: bool = True  # Reduce notification rate when GPU is stressed
    performance_throttle_threshold: float = 0.8  # GPU usage % to trigger throttling (0-1)
    throttled_cooldown: float = 5.0  # Seconds between alerts when throttled
    
    # Theme sync
    theme_sync_enabled: bool = True  # Sync with XSOverlay accent color


@dataclass 
class PerformanceData:
    """Performance data from XSOverlay/SteamVR"""
    cpu_frametime: float = 0.0  # CPU frame time in ms
    gpu_frametime: float = 0.0  # GPU frame time in ms
    target_frametime: float = 11.11  # Target frame time based on HMD refresh rate
    reprojection_ratio: float = 0.0  # % of frames using reprojection
    dropped_frames: int = 0
    is_gpu_bound: bool = False
    is_cpu_bound: bool = False
    
    @property
    def gpu_usage(self) -> float:
        """Estimate GPU usage as ratio of frametime to target (0-1+)"""
        if self.target_frametime <= 0:
            return 0.0
        return self.gpu_frametime / self.target_frametime
    
    @property
    def cpu_usage(self) -> float:
        """Estimate CPU usage as ratio of frametime to target (0-1+)"""
        if self.target_frametime <= 0:
            return 0.0
        return self.cpu_frametime / self.target_frametime
    
    @property 
    def fps(self) -> float:
        """Estimated FPS based on max frametime"""
        max_ft = max(self.cpu_frametime, self.gpu_frametime)
        if max_ft <= 0:
            return 0.0
        return 1000.0 / max_ft


class XSOverlayService:
    """
    Service for sending VR notifications via XSOverlay.
    
    XSOverlay listens on a WebSocket (default port 42070) and accepts
    JSON messages to display toast notifications in VR.
    
    Usage:
        service = XSOverlayService()
        await service.connect()
        await service.send_notification("Alert!", "Watchlisted user joined")
    """
    
    SOURCE_APP = "Group Guardian"
    
    def __init__(self, config: Optional[XSOverlayConfig] = None):
        """
        Initialize the XSOverlay service.
        
        Args:
            config: Optional configuration, uses defaults if not provided
        """
        self.config = config or XSOverlayConfig()
        self._websocket = None
        self._connected = False
        self._reconnect_task: Optional[asyncio.Task] = None
        self._reconnect_attempts = 0
        self._on_connect_callbacks: List[Callable] = []
        self._on_disconnect_callbacks: List[Callable] = []
        self._lock = asyncio.Lock()
        
        # Performance monitoring state
        self._performance_data = PerformanceData()
        self._performance_subscribed = False
        self._on_performance_callbacks: List[Callable] = []
        self._last_notification_time: float = 0.0  # For throttling
        
        # Theme sync state
        self._xso_accent_color: Optional[str] = None
        self._on_theme_change_callbacks: List[Callable] = []
        
    @property
    def performance(self) -> PerformanceData:
        """Get current performance data from XSOverlay"""
        return self._performance_data
    
    @property
    def accent_color(self) -> Optional[str]:
        """Get XSOverlay's current accent color (hex format)"""
        return self._xso_accent_color
    
    @property
    def is_throttled(self) -> bool:
        """Check if notifications are currently throttled due to performance"""
        if not self.config.performance_throttle_enabled:
            return False
        return self._performance_data.gpu_usage >= self.config.performance_throttle_threshold
        
    @property
    def connected(self) -> bool:
        """Check if currently connected to XSOverlay"""
        return self._connected and self._websocket is not None
    
    @property
    def enabled(self) -> bool:
        """Check if XSOverlay integration is enabled"""
        return self.config.enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        """Enable or disable XSOverlay integration"""
        self.config.enabled = value
        
    def on_connect(self, callback: Callable):
        """Register a callback for when connection is established"""
        self._on_connect_callbacks.append(callback)
        
    def on_disconnect(self, callback: Callable):
        """Register a callback for when connection is lost"""
        self._on_disconnect_callbacks.append(callback)
    
    def on_performance_update(self, callback: Callable):
        """
        Register a callback for performance data updates.
        
        Callback receives PerformanceData as argument:
            def my_callback(perf: PerformanceData): ...
        """
        self._on_performance_callbacks.append(callback)
    
    def on_theme_change(self, callback: Callable):
        """
        Register a callback for XSOverlay theme/accent color changes.
        
        Callback receives hex color string as argument:
            def my_callback(color: str): ...  # e.g. "#8b5cf6"
        """
        self._on_theme_change_callbacks.append(callback)
    
    async def connect(self) -> bool:
        """
        Connect to XSOverlay's WebSocket API.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.config.enabled:
            logger.debug("XSOverlay integration disabled")
            return False
            
        if self._connected:
            logger.debug("Already connected to XSOverlay")
            return True
            
        try:
            import websockets
            
            uri = f"ws://{self.config.host}:{self.config.ws_port}/?client={self.SOURCE_APP}"
            logger.info(f"Connecting to XSOverlay at {uri}")
            
            self._websocket = await asyncio.wait_for(
                websockets.connect(uri),
                timeout=5.0
            )
            self._connected = True
            self._reconnect_attempts = 0
            
            logger.info("✅ Connected to XSOverlay")
            
            # Trigger connect callbacks
            for callback in self._on_connect_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    logger.error(f"Error in connect callback: {e}")
            
            # Start listening for messages (XSOverlay can send responses)
            asyncio.create_task(self._listen_loop())
            
            # Subscribe to performance events if enabled
            if self.config.performance_subscription:
                await self._subscribe_to_events()
            
            return True
            
        except ImportError:
            logger.error("websockets library not installed. Run: pip install websockets")
            return False
        except asyncio.TimeoutError:
            logger.warning("XSOverlay connection timed out - is XSOverlay running?")
            self._schedule_reconnect()
            return False
        except ConnectionRefusedError:
            logger.warning("XSOverlay connection refused - is XSOverlay running?")
            self._schedule_reconnect()
            return False
        except Exception as e:
            logger.error(f"Failed to connect to XSOverlay: {e}")
            self._schedule_reconnect()
            return False
            
    async def disconnect(self):
        """Disconnect from XSOverlay"""
        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None
            
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception:
                pass
            self._websocket = None
            
        if self._connected:
            self._connected = False
            logger.info("Disconnected from XSOverlay")
            
            # Trigger disconnect callbacks
            for callback in self._on_disconnect_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    logger.error(f"Error in disconnect callback: {e}")
    
    def _schedule_reconnect(self):
        """Schedule a reconnection attempt"""
        if not self.config.auto_reconnect:
            return
            
        if self._reconnect_attempts >= self.config.max_reconnect_attempts:
            logger.warning(f"Max reconnect attempts ({self.config.max_reconnect_attempts}) reached")
            return
            
        if self._reconnect_task and not self._reconnect_task.done():
            return  # Already scheduled
            
        self._reconnect_attempts += 1
        delay = self.config.reconnect_delay * min(self._reconnect_attempts, 5)
        
        logger.debug(f"Scheduling XSOverlay reconnect in {delay}s (attempt {self._reconnect_attempts})")
        
        async def reconnect():
            await asyncio.sleep(delay)
            await self.connect()
            
        self._reconnect_task = asyncio.create_task(reconnect())
    
    async def _listen_loop(self):
        """Listen for incoming messages from XSOverlay"""
        try:
            while self._connected and self._websocket:
                try:
                    message = await asyncio.wait_for(
                        self._websocket.recv(),
                        timeout=30.0
                    )
                    # Parse and handle XSOverlay messages
                    await self._handle_xso_message(message)
                    
                except asyncio.TimeoutError:
                    # Send a ping to keep connection alive
                    continue
                    
        except Exception as e:
            if self._connected:
                logger.warning(f"XSOverlay connection lost: {e}")
                self._connected = False
                self._websocket = None
                self._performance_subscribed = False
                self._schedule_reconnect()
                
                # Trigger disconnect callbacks
                for callback in self._on_disconnect_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback()
                        else:
                            callback()
                    except Exception as err:
                        logger.error(f"Error in disconnect callback: {err}")
    
# ... (previous code remains similar, I will rewrite the class to include new methods)

    async def request_device_info(self) -> bool:
        """Request current device information (battery levels) from XSOverlay"""
        message = {
            "sender": self.SOURCE_APP,
            "target": "xsoverlay",
            "command": "RequestDeviceInformation"
        }
        return await self._send_message(message)

    async def media_play_pause(self) -> bool:
        """Toggle media playback"""
        return await self._send_message({
            "sender": self.SOURCE_APP,
            "target": "xsoverlay",
            "command": "MediaPlayPause"
        })

    async def media_next(self) -> bool:
        """Skip to next media track"""
        return await self._send_message({
            "sender": self.SOURCE_APP,
            "target": "xsoverlay",
            "command": "MediaNext"
        })

    async def media_previous(self) -> bool:
        """Go to previous media track"""
        return await self._send_message({
            "sender": self.SOURCE_APP,
            "target": "xsoverlay",
            "command": "MediaPrevious"
        })

    async def media_volume_up(self) -> bool:
        """Increase volume"""
        return await self._send_message({
            "sender": self.SOURCE_APP,
            "target": "xsoverlay",
            "command": "MediaVolumeUp"
        })

    async def media_volume_down(self) -> bool:
        """Decrease volume"""
        return await self._send_message({
            "sender": self.SOURCE_APP,
            "target": "xsoverlay",
            "command": "MediaVolumeDown"
        })
        
    async def toggle_layout_mode(self) -> bool:
        """Toggle XSOverlay Layout Mode"""
        return await self._send_message({
            "sender": self.SOURCE_APP,
            "target": "xsoverlay",
            "command": "ToggleLayoutMode"
        })

    async def load_layout(self, layout_name: str) -> bool:
        """Load a specific overlay layout"""
        return await self._send_message({
            "sender": self.SOURCE_APP,
            "target": "xsoverlay",
            "command": "LoadLayout",
            "rawData": layout_name
        })

    async def clear_layout(self) -> bool:
        """Close all open overlays"""
        return await self._send_message({
            "sender": self.SOURCE_APP,
            "target": "xsoverlay",
            "command": "ClearLayout"
        })

    async def _handle_xso_message(self, raw_message: str):
        """Parse and handle incoming XSOverlay messages"""
        try:
            data = json.loads(raw_message)
            
            # Check for performance data response
            if "cpuFrameTime" in data or "gpuFrameTime" in data:
                self._update_performance_data(data)
                return
            
            # Check for theme/settings data
            if "accentColor" in data:
                await self._handle_theme_update(data)
                return

            # Check for device info (battery)
            if "leftControllerBattery" in data or "rightControllerBattery" in data:
                await self._handle_device_info(data)
                return
            
            # Log other messages for debugging
            logger.debug(f"XSOverlay message: {data}")
            
        except json.JSONDecodeError:
            logger.debug(f"Non-JSON XSOverlay message: {raw_message[:100]}")
        except Exception as e:
            logger.warning(f"Error handling XSOverlay message: {e}")

    async def _handle_device_info(self, data: Dict[str, Any]):
        """Handle device info updates (batteries)"""
        # Can be expanded to store state or trigger callbacks
        logger.debug(f"Device Info: {data}")
    
    def _update_performance_data(self, data: Dict[str, Any]):
        """Update performance data from XSOverlay response"""
        try:
            self._performance_data.cpu_frametime = data.get("cpuFrameTime", 0.0)
            self._performance_data.gpu_frametime = data.get("gpuFrameTime", 0.0)
            self._performance_data.target_frametime = data.get("targetFrameTime", 11.11)
            self._performance_data.reprojection_ratio = data.get("reprojectionRatio", 0.0)
            self._performance_data.dropped_frames = data.get("droppedFrames", 0)
            self._performance_data.is_gpu_bound = data.get("isGpuBound", False)
            self._performance_data.is_cpu_bound = data.get("isCpuBound", False)
            
            # Trigger performance callbacks
            for callback in self._on_performance_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(self._performance_data))
                    else:
                        callback(self._performance_data)
                except Exception as e:
                    logger.error(f"Error in performance callback: {e}")
                    
        except Exception as e:
            logger.warning(f"Failed to parse performance data: {e}")
    
    async def _handle_theme_update(self, data: Dict[str, Any]):
        """Handle theme/accent color updates from XSOverlay"""
        try:
            new_color = data.get("accentColor", "")
            
            # XSOverlay may send color as RGB object or hex string
            if isinstance(new_color, dict):
                r = int(new_color.get("r", 0) * 255)
                g = int(new_color.get("g", 0) * 255)
                b = int(new_color.get("b", 0) * 255)
                new_color = f"#{r:02x}{g:02x}{b:02x}"
            elif isinstance(new_color, str) and not new_color.startswith("#"):
                new_color = f"#{new_color}"
            
            if new_color and new_color != self._xso_accent_color:
                old_color = self._xso_accent_color
                self._xso_accent_color = new_color
                logger.info(f"XSOverlay accent color changed: {old_color} -> {new_color}")
                
                # Trigger theme change callbacks
                for callback in self._on_theme_change_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(new_color)
                        else:
                            callback(new_color)
                    except Exception as e:
                        logger.error(f"Error in theme change callback: {e}")
                        
        except Exception as e:
            logger.warning(f"Failed to handle theme update: {e}")
    
    async def send_media_notification(
        self,
        title: str,
        artist: str,
        album: str = "",
        icon_base64: Optional[str] = None,
        duration: float = 5.0
    ) -> bool:
        """
        Send a media player notification.
        
        Args:
            title: Song title
            artist: Artist name
            album: Album name
            icon_base64: Album art (optional)
            duration: Display duration
            
        Returns:
            True if sent successfully
        """
        notification = {
            "messageType": NotificationType.MEDIA_PLAYER,
            "title": title,
            "content": artist,
            "audioPath": album, # XSOverlay uses audioPath field for Album name in Media Player notifications sometimes? 
                               # No, check docs. The docs summary didn't specify MEDIA_PLAYER json structure fully.
                               # But usually it's title/content/icon.
            "timeout": duration,
            "sourceApp": self.SOURCE_APP,
            "opacity": 1.0, 
            "height": 175.0
        }
        
        if album:
             # Some implementations put album in content or strictly use title/content
             notification["content"] = f"{artist}\n<size=80%>{album}</size>"
        
        if icon_base64:
            notification["icon"] = icon_base64
            notification["useBase64Icon"] = True
            
        return await self._send_message(notification)

    async def _subscribe_to_events(self) -> bool:
        """Subscribe to specific data events from XSOverlay"""
        if self._performance_subscribed:
            return True
            
        # Subscribe to Performance, MediaPlayer, and DateAndTime
        topics = ["Performance", "MediaPlayer", "DateAndTime"]
        
        subscribe_msg = {
            "sender": self.SOURCE_APP,
            "target": "xsoverlay",
            "command": "SubscribeToApiEvents",
            "jsonData": json.dumps(topics)
        }
        
        success = await self._send_message(subscribe_msg)
        if success:
            self._performance_subscribed = True
            logger.info(f"Subscribed to XSOverlay events: {', '.join(topics)}")
        return success
    
    async def request_performance_data(self) -> bool:
        """Request current performance data from XSOverlay (one-time)"""
        message = {
            "sender": self.SOURCE_APP,
            "target": "xsoverlay",
            "command": "RequestRuntimePerformance"
        }
        return await self._send_message(message)
    
    async def send_notification(
        self,
        title: str,
        content: str = "",
        duration: Optional[float] = None,
        opacity: Optional[float] = None,
        height: Optional[float] = None,
        icon_base64: Optional[str] = None,
        icon_path: Optional[str] = None,
        audio_path: Optional[str] = None,
        volume: float = 0.7
    ) -> bool:
        """
        Send a toast notification to XSOverlay.
        
        Args:
            title: Notification title (supports Rich Text)
            content: Notification body (supports Rich Text). Empty = smaller notification.
            duration: Display duration in seconds (default: config.default_duration)
            opacity: Transparency 0-1 (default: config.default_opacity)
            height: Notification height when content present (default: config.default_height)
            icon_base64: Base64 encoded icon image
            icon_path: Path to icon file (alternative to base64)
            audio_path: Path to custom sound file
            volume: Sound volume 0-1 (default: 0.7)
            
        Returns:
            True if notification sent successfully
        """
        if not self.config.enabled:
            logger.debug("XSOverlay disabled, notification skipped")
            return False
            
        # If using UDP, we don't need a WebSocket connection
        use_udp = self.config.prefer_udp
        
        if not use_udp and not self._connected:
            logger.debug("Not connected to XSOverlay (WS), attempting connection...")
            connected = await self.connect()
            if not connected:
                return False
        
        # Build notification payload
        notification = {
            "messageType": NotificationType.NOTIFICATION,
            "title": title,
            "content": content,
            "timeout": duration or self.config.default_duration,
            "opacity": opacity or self.config.default_opacity,
            "height": height or self.config.default_height if content else 75.0,
            "sourceApp": self.SOURCE_APP,
            "volume": volume if self.config.sound_enabled else 0.0,
        }
        
        # Add icon if provided
        if icon_base64:
            notification["icon"] = icon_base64
            notification["useBase64Icon"] = True
        elif icon_path:
            try:
                icon_data = await self._load_icon_as_base64(icon_path)
                if icon_data:
                    notification["icon"] = icon_data
                    notification["useBase64Icon"] = True
            except Exception as e:
                logger.warning(f"Failed to load icon: {e}")
        
        # Add audio if provided
        if audio_path:
            notification["audioPath"] = audio_path
        elif self.config.custom_sound_path:
            notification["audioPath"] = self.config.custom_sound_path
            
        return await self._send_message(notification)
    
    async def send_watchlist_alert(
        self,
        username: str,
        tags: List[str],
        user_thumbnail: Optional[str] = None,
        severity: str = "warning",
        bypass_throttle: bool = False
    ) -> bool:
        """
        Send a watchlist alert notification optimized for VR visibility.
        
        Args:
            username: Display name of the user
            tags: List of watchlist tags
            user_thumbnail: Optional base64 encoded user thumbnail
            severity: "info", "warning", "danger" - affects styling
            bypass_throttle: If True, send even when throttled (for critical alerts)
            
        Returns:
            True if notification sent successfully
        """
        import time
        
        # Check throttling (unless bypassed or danger severity)
        if not bypass_throttle and severity != "danger":
            if self.is_throttled:
                now = time.time()
                time_since_last = now - self._last_notification_time
                if time_since_last < self.config.throttled_cooldown:
                    logger.debug(f"Notification throttled (GPU stressed, {time_since_last:.1f}s since last)")
                    return False
        
        # Build alert message
        primary_tag = tags[0] if tags else "Watchlist"
        
        # Use Rich Text formatting for emphasis
        if severity == "danger":
            title = f"<color=red><b>⚠️ WATCHLIST ALERT</b></color>"
            duration = 6.0
        elif severity == "warning":
            title = f"<color=yellow><b>⚠️ WATCHLIST</b></color>"
            duration = 4.0
        else:
            title = f"<color=white><b>👀 WATCHLIST</b></color>"
            duration = 3.0
        
        # When throttled, reduce duration slightly
        if self.is_throttled and severity != "danger":
            duration = min(duration, 2.0)
            
        content = f"<b>{username}</b>\n<color=#888888>[{primary_tag}]</color>"
        
        if len(tags) > 1:
            extra_tags = ", ".join(tags[1:3])
            if len(tags) > 3:
                extra_tags += f" +{len(tags) - 3} more"
            content += f"\n<size=80%>{extra_tags}</size>"
        
        result = await self.send_notification(
            title=title,
            content=content,
            duration=duration,
            opacity=0.95,
            height=150.0,
            icon_base64=user_thumbnail
        )
        
        if result:
            self._last_notification_time = time.time()
        
        return result
    
    async def send_group_request_alert(
        self,
        username: str,
        group_name: str,
        request_type: str = "join",
        user_thumbnail: Optional[str] = None
    ) -> bool:
        """
        Send an alert for group join requests.
        
        Args:
            username: Name of the requesting user
            group_name: Name of the group
            request_type: "join", "invite", etc.
            user_thumbnail: Optional base64 user thumbnail
            
        Returns:
            True if notification sent
        """
        title = f"<color=cyan><b>📥 {request_type.upper()} REQUEST</b></color>"
        content = f"<b>{username}</b>\nwants to join <color=#888888>{group_name}</color>"
        
        return await self.send_notification(
            title=title,
            content=content,
            duration=5.0,
            opacity=0.9,
            height=130.0,
            icon_base64=user_thumbnail
        )
    
    async def send_instance_alert(
        self,
        world_name: str,
        player_count: int,
        event_type: str = "update"
    ) -> bool:
        """
        Send an instance population update notification.
        
        Args:
            world_name: Name of the world
            player_count: Current player count
            event_type: "join", "leave", "update"
            
        Returns:
            True if notification sent
        """
        if event_type == "join":
            title = "<color=green><b>🟢 PLAYER JOINED</b></color>"
        elif event_type == "leave":
            title = "<color=orange><b>🟠 PLAYER LEFT</b></color>"
        else:
            title = "<color=white><b>📊 INSTANCE UPDATE</b></color>"
            
        content = f"{world_name}\n<color=#888888>Players: {player_count}</color>"
        
        return await self.send_notification(
            title=title,
            content=content,
            duration=2.0,
            opacity=0.8,
            height=100.0
        )
    
    async def play_haptics(self, duration_ms: int = 100, intensity: float = 1.0) -> bool:
        """
        Trigger haptic feedback on VR controllers.
        
        Args:
            duration_ms: Duration in milliseconds
            intensity: Intensity 0-1
            
        Returns:
            True if haptics triggered successfully
        """
        if not self.config.haptics_enabled:
            return False
            
        # XSOverlay haptics command
        message = {
            "messageType": 0,  # Command type
            "command": "PlayDeviceHaptics",
            "jsonData": json.dumps({
                "duration": duration_ms / 1000.0,
                "intensity": intensity
            })
        }
        
        return await self._send_message(message)
    
    async def _send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send a raw message to XSOverlay.
        
        Args:
            message: Message dictionary to send
            
        Returns:
            True if sent successfully
        """
        # Checks for UDP eligibility (Notifications only)
        is_notification = message.get("messageType") == NotificationType.NOTIFICATION
        use_udp = self.config.prefer_udp and is_notification
        
        if use_udp:
            return await self._send_udp_message(message)
            
        if not self._websocket or not self._connected:
            return False
            
        async with self._lock:
            try:
                payload = json.dumps(message)
                await self._websocket.send(payload)
                logger.debug(f"Sent to XSOverlay (WS): {message.get('title', message.get('command', 'message'))}")
                return True
            except Exception as e:
                logger.error(f"Failed to send XSOverlay message: {e}")
                self._connected = False
                self._schedule_reconnect()
                return False

    async def _send_udp_message(self, message: Dict[str, Any]) -> bool:
        """Send a message via UDP (fire-and-forget)"""
        try:
            import socket
            
            payload = json.dumps(message).encode('utf-8')
            
            # Create a temporary socket for sending
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(payload, (self.config.host, self.config.udp_port))
            sock.close()
            
            logger.debug(f"Sent to XSOverlay (UDP): {message.get('title')}")
            return True
        except Exception as e:
            logger.error(f"Failed to send XSOverlay UDP message: {e}")
            return False
    
    async def _load_icon_as_base64(self, path: str) -> Optional[str]:
        """Load an image file and convert to base64"""
        try:
            file_path = Path(path)
            if not file_path.exists():
                return None
                
            with open(file_path, "rb") as f:
                data = f.read()
                
            return base64.b64encode(data).decode("utf-8")
        except Exception as e:
            logger.warning(f"Failed to load icon from {path}: {e}")
            return None
    
    async def test_notification(self) -> bool:
        """
        Send a test notification to verify XSOverlay connection.
        
        Returns:
            True if test notification sent successfully
        """
        return await self.send_notification(
            title="<color=cyan><b>🛡️ Group Guardian</b></color>",
            content="XSOverlay integration is working!\nYou'll see watchlist alerts here.",
            duration=5.0,
            opacity=0.95
        )


# Singleton instance
_xsoverlay_service: Optional[XSOverlayService] = None


def get_xsoverlay_service(config: Optional[XSOverlayConfig] = None) -> XSOverlayService:
    """Get or create the singleton XSOverlay service instance"""
    global _xsoverlay_service
    if _xsoverlay_service is None:
        _xsoverlay_service = XSOverlayService(config)
    return _xsoverlay_service


async def connect_xsoverlay() -> bool:
    """Convenience function to connect to XSOverlay"""
    service = get_xsoverlay_service()
    return await service.connect()


async def disconnect_xsoverlay():
    """Convenience function to disconnect from XSOverlay"""
    service = get_xsoverlay_service()
    await service.disconnect()
