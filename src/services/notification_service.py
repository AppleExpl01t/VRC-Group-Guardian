"""
Notification Service
====================
Centralized notification system for Group Guardian.
Handles in-app sound notifications with configurable volume and custom sounds.

Features:
- Play notification sounds for various events
- User-configurable notification sounds
- Volume control
- Event-specific notification settings
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import json
import threading

logger = logging.getLogger(__name__)

# Try importing pygame for audio playback
_pygame_available = False
_pygame_mixer = None

def _init_pygame():
    """Initialize pygame mixer for audio playback"""
    global _pygame_available, _pygame_mixer
    if _pygame_mixer is not None:
        return _pygame_available
    
    try:
        import pygame
        pygame.mixer.init()
        _pygame_mixer = pygame.mixer
        _pygame_available = True
        logger.info("Pygame mixer initialized for notifications")
    except ImportError:
        logger.warning("Pygame not installed - notifications will be silent. Install with: pip install pygame")
        _pygame_available = False
    except Exception as e:
        logger.warning(f"Failed to initialize pygame mixer: {e}")
        _pygame_available = False
    
    return _pygame_available


@dataclass
class NotificationConfig:
    """Configuration for the notification system"""
    # Master volume (0.0 to 1.0)
    master_volume: float = 0.7
    
    # Enable/disable notification categories
    watchlist_alerts_enabled: bool = True
    automod_alerts_enabled: bool = True
    join_request_alerts_enabled: bool = True
    player_join_alerts_enabled: bool = False  # Disabled by default (could be noisy)
    player_leave_alerts_enabled: bool = False  # Disabled by default
    update_alerts_enabled: bool = True
    
    # Custom sound file path (None = use default)
    custom_sound_path: Optional[str] = None
    
    # Default sound file name
    default_sound_filename: str = "Group_Guardian_Notif_sound.mp3"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "master_volume": self.master_volume,
            "watchlist_alerts_enabled": self.watchlist_alerts_enabled,
            "automod_alerts_enabled": self.automod_alerts_enabled,
            "join_request_alerts_enabled": self.join_request_alerts_enabled,
            "player_join_alerts_enabled": self.player_join_alerts_enabled,
            "player_leave_alerts_enabled": self.player_leave_alerts_enabled,
            "update_alerts_enabled": self.update_alerts_enabled,
            "custom_sound_path": self.custom_sound_path,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotificationConfig':
        return cls(
            master_volume=data.get("master_volume", 0.7),
            watchlist_alerts_enabled=data.get("watchlist_alerts_enabled", True),
            automod_alerts_enabled=data.get("automod_alerts_enabled", True),
            join_request_alerts_enabled=data.get("join_request_alerts_enabled", True),
            player_join_alerts_enabled=data.get("player_join_alerts_enabled", False),
            player_leave_alerts_enabled=data.get("player_leave_alerts_enabled", False),
            update_alerts_enabled=data.get("update_alerts_enabled", True),
            custom_sound_path=data.get("custom_sound_path"),
        )


class NotificationService:
    """
    Centralized notification service for Group Guardian.
    
    Plays sound notifications for various events in the app.
    """
    
    # Notification event types
    EVENT_WATCHLIST_ALERT = "watchlist_alert"
    EVENT_AUTOMOD_ACCEPT = "automod_accept"
    EVENT_AUTOMOD_REJECT = "automod_reject"
    EVENT_JOIN_REQUEST = "join_request"
    EVENT_PLAYER_JOIN = "player_join"
    EVENT_PLAYER_LEAVE = "player_leave"
    EVENT_UPDATE_AVAILABLE = "update_available"
    EVENT_GENERIC = "generic"
    
    def __init__(self):
        self.config = NotificationConfig()
        self._config_path = self._get_config_path()
        self._sound_cache: Dict[str, Any] = {}  # Cache loaded sounds
        self._lock = threading.Lock()
        
        # Load saved configuration
        self._load_config()
        
        # Initialize audio system
        _init_pygame()
        
        # Pre-load default sound
        self._preload_sounds()
    
    def _get_config_path(self) -> Path:
        """Get path to notification config file"""
        from utils.paths import get_data_dir
        return get_data_dir() / "notification_config.json"
    
    def _get_default_sound_path(self) -> Optional[Path]:
        """Get path to default notification sound"""
        # Check multiple locations
        possible_paths = [
            # Root folder (where user placed it)
            Path(__file__).parent.parent.parent.parent / self.config.default_sound_filename,
            # Assets folder
            # Development path (src/services/../../assets)
            Path(__file__).parent.parent.parent.parent / "assets" / self.config.default_sound_filename,
            # Relative to exe/cwd
            Path(os.getcwd()) / self.config.default_sound_filename,
            Path(os.getcwd()) / "assets" / self.config.default_sound_filename,
        ]
        
        # Add frozen path (PyInstaller)
        if getattr(sys, 'frozen', False):
             possible_paths.insert(0, Path(sys._MEIPASS) / "assets" / self.config.default_sound_filename)
        
        for path in possible_paths:
            if path.exists():
                logger.debug(f"Found default sound at: {path}")
                return path
        
        logger.warning(f"Default notification sound not found. Checked: {[str(p) for p in possible_paths]}")
        return None
    
    def _get_sound_path(self) -> Optional[Path]:
        """Get the current sound file path (custom or default)"""
        if self.config.custom_sound_path:
            custom_path = Path(self.config.custom_sound_path)
            if custom_path.exists():
                return custom_path
            logger.warning(f"Custom sound not found: {custom_path}")
        
        return self._get_default_sound_path()
    
    def _load_config(self):
        """Load configuration from disk"""
        try:
            if self._config_path.exists():
                with open(self._config_path, "r") as f:
                    data = json.load(f)
                    self.config = NotificationConfig.from_dict(data)
                    logger.debug("Notification config loaded")
        except Exception as e:
            logger.error(f"Failed to load notification config: {e}")
    
    def save_config(self):
        """Save configuration to disk"""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, "w") as f:
                json.dump(self.config.to_dict(), f, indent=2)
            logger.debug("Notification config saved")
        except Exception as e:
            logger.error(f"Failed to save notification config: {e}")
    
    def _preload_sounds(self):
        """Pre-load sounds for faster playback"""
        if not _pygame_available:
            return
        
        sound_path = self._get_sound_path()
        if sound_path:
            try:
                sound = _pygame_mixer.Sound(str(sound_path))
                self._sound_cache["default"] = sound
                logger.debug(f"Pre-loaded notification sound: {sound_path}")
            except Exception as e:
                logger.error(f"Failed to pre-load sound: {e}")
    
    def _is_event_enabled(self, event_type: str) -> bool:
        """Check if notifications are enabled for an event type"""
        if event_type == self.EVENT_WATCHLIST_ALERT:
            return self.config.watchlist_alerts_enabled
        elif event_type in (self.EVENT_AUTOMOD_ACCEPT, self.EVENT_AUTOMOD_REJECT):
            return self.config.automod_alerts_enabled
        elif event_type == self.EVENT_JOIN_REQUEST:
            return self.config.join_request_alerts_enabled
        elif event_type == self.EVENT_PLAYER_JOIN:
            return self.config.player_join_alerts_enabled
        elif event_type == self.EVENT_PLAYER_LEAVE:
            return self.config.player_leave_alerts_enabled
        elif event_type == self.EVENT_UPDATE_AVAILABLE:
            return self.config.update_alerts_enabled
        else:
            return True  # Generic events always play
    
    def play(self, event_type: str = EVENT_GENERIC, volume_multiplier: float = 1.0) -> bool:
        """
        Play a notification sound.
        
        Args:
            event_type: Type of notification event
            volume_multiplier: Additional volume adjustment (0.0 to 1.0)
            
        Returns:
            True if sound was played, False otherwise
        """
        # Check if this event type is enabled
        if not self._is_event_enabled(event_type):
            logger.debug(f"Notification disabled for event: {event_type}")
            return False
        
        if not _pygame_available:
            logger.debug("Audio not available - skipping notification sound")
            return False
        
        with self._lock:
            try:
                # Get or load sound
                sound = self._sound_cache.get("default")
                if not sound:
                    sound_path = self._get_sound_path()
                    if not sound_path:
                        return False
                    sound = _pygame_mixer.Sound(str(sound_path))
                    self._sound_cache["default"] = sound
                
                # Calculate final volume
                final_volume = self.config.master_volume * volume_multiplier
                final_volume = max(0.0, min(1.0, final_volume))  # Clamp to 0-1
                
                # Set volume and play
                sound.set_volume(final_volume)
                sound.play()
                
                logger.debug(f"Notification played: {event_type} (volume: {final_volume:.2f})")
                return True
                
            except Exception as e:
                logger.error(f"Failed to play notification: {e}")
                return False
    
    def play_test(self) -> bool:
        """Play a test notification at current volume"""
        return self.play(self.EVENT_GENERIC, volume_multiplier=1.0)
    
    def set_volume(self, volume: float):
        """Set master volume (0.0 to 1.0)"""
        self.config.master_volume = max(0.0, min(1.0, volume))
        self.save_config()
    
    def set_custom_sound(self, path: Optional[str]):
        """Set a custom notification sound file"""
        self.config.custom_sound_path = path
        
        # Clear cache to force reload
        self._sound_cache.clear()
        
        # Pre-load new sound
        self._preload_sounds()
        
        self.save_config()
    
    def get_available_sounds(self) -> list:
        """Get list of available sound files in the assets folder"""
        sounds = []
        
        # Check assets folder
        assets_dir = Path(__file__).parent.parent.parent.parent / "assets"
        if assets_dir.exists():
            for ext in ["*.mp3", "*.wav", "*.ogg"]:
                sounds.extend(assets_dir.glob(ext))
        
        # Check root folder
        root_dir = Path(__file__).parent.parent.parent.parent
        for ext in ["*.mp3", "*.wav", "*.ogg"]:
            sounds.extend(root_dir.glob(ext))
        
        # Return unique paths as strings
        return list(set(str(s) for s in sounds))
    
    def notify_watchlist_alert(self, username: str):
        """Notify about a watchlisted user joining"""
        return self.play(self.EVENT_WATCHLIST_ALERT)
    
    def notify_automod_action(self, accepted: bool):
        """Notify about an auto-mod action"""
        event = self.EVENT_AUTOMOD_ACCEPT if accepted else self.EVENT_AUTOMOD_REJECT
        return self.play(event)
    
    def notify_join_request(self):
        """Notify about new join request(s)"""
        return self.play(self.EVENT_JOIN_REQUEST)
    
    def notify_player_join(self, username: str):
        """Notify about a player joining the instance"""
        return self.play(self.EVENT_PLAYER_JOIN, volume_multiplier=0.5)  # Quieter for frequent events
    
    def notify_player_leave(self, username: str):
        """Notify about a player leaving the instance"""
        return self.play(self.EVENT_PLAYER_LEAVE, volume_multiplier=0.3)  # Even quieter
    
    def notify_update_available(self):
        """Notify about an available update"""
        return self.play(self.EVENT_UPDATE_AVAILABLE)


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get or create the singleton notification service"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
