"""
LogWatcher Service
===================
Tails VRChat log files in real-time to detect player joins/leaves, instance changes,
and asset events. Features database integration and backfilling.
"""

import os
import time
import re
import glob
import threading
import logging
from typing import Callable, Optional, List, Dict, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class LogWatcher:
    """
    Watches the VRChat log file for real-time events.
    Migrated from FCH-Toolkit logic.
    """
    
    # Regex Patterns
    RE_TIMESTAMP = re.compile(r"^(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})")
    RE_PLAYER_JOIN = re.compile(r"OnPlayerJoined\s+(?:\[[^\]]+\]\s*)?([^\r\n(]+?)\s*\((usr_[a-f0-9\-]{36})\)")
    RE_PLAYER_LEAVE = re.compile(r"OnPlayerLeft\s+([^\r\n(]+?)\s*\((usr_[a-f0-9\-]{36})\)")
    
    # Joining wrld_xxx:instance_yyy
    # Capture wrld_id, instance_tags
    RE_JOINING = re.compile(r"Joining\s+(wrld_[a-f0-9\-]{36}):([^~\s]+)(?:~region\(([^)]+)\))?")
    
    RE_AVATAR_SWITCH = re.compile(r"\[Behaviour\]\s+Switching\s+(.+?)\s+to\s+avatar\s+(.+)")
    
    # Cleaning / Purge
    RE_LEFT_ROOM = re.compile(r"Successfully left room")
    RE_QUIT = re.compile(r"VRCApplication:\s*HandleApplicationQuit")
    
    # Assets / Media (Experimental - based on observed logs)
    # Portal dropped by X
    RE_PORTAL = re.compile(r"\[Behaviour\]\s+User\s+(.+?)\s+dropped\s+portal\s+to\s+(wrld_[a-f0-9\-]{36})")

    def __init__(self):
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []
        
        # log path - Windows only, use fallback for Android
        user_profile = os.environ.get("USERPROFILE", "")
        if user_profile:
            self.log_dir = os.path.join(user_profile, "AppData", "LocalLow", "VRChat", "VRChat")
        else:
            self.log_dir = ""  # Not available on Android
        
        # Memory state
        self.current_log_path: Optional[str] = None
        self.active_players: Dict[str, str] = {} # uid -> name
        self.player_avatars: Dict[str, str] = {} # uid -> avatar_name
        
        # Instance state
        self.current_world_id: Optional[str] = None
        self.current_instance_id: Optional[str] = None
        self.current_group_id: Optional[str] = None
        
        # Backfill state
        self._is_backfilling = False
        
        # Error throttling - prevent log spam
        self._last_db_error_time: float = 0
        self._db_error_logged = False

    def add_listener(self, callback: Callable[[Dict[str, Any]], None]):
        if callback not in self._listeners:
            self._listeners.append(callback)

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._watch_loop, daemon=True, name="LogWatcher")
        self.thread.start()
        logger.info("LogWatcher started")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)

    def _get_latest_log(self) -> Optional[str]:
        # Fast search for output_log_*.txt
        try:
            search = os.path.join(self.log_dir, "output_log_*.txt")
            files = glob.glob(search)
            if not files: return None
            return max(files, key=os.path.getmtime)
        except Exception:
            return None

    def _backfill(self, filepath: str, max_bytes=4*1024*1024) -> int:
        """
        Read the last `max_bytes` of the file to reconstruct state.
        Returns the new file position.
        """
        self._is_backfilling = True
        try:
            size = os.path.getsize(filepath)
            start_pos = max(0, size - max_bytes)
            
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                f.seek(start_pos)
                # Discard first partial line
                if start_pos > 0:
                    f.readline()
                
                # Read all lines
                lines = f.readlines()
                final_pos = f.tell()
                
                # Check for last instance join
                # We only really care about the *last* active session
                # But treating them sequentially works too
                
                # Optimization: Find last "Joining wrld_" index
                last_join_idx = -1
                for i, line in enumerate(lines):
                    if self.RE_JOINING.search(line):
                        last_join_idx = i
                
                start_processing_idx = max(0, last_join_idx)
                
                print(f"[LogWatcher] Backfilling from line {start_processing_idx}...")
                
                for line in lines[start_processing_idx:]:
                    self._process_line(line, is_backfill=True)
                    
                return final_pos
                
        except Exception as e:
            # Throttle error logging
            current_time = time.time()
            if current_time - self._last_db_error_time > 60:
                logger.error(f"Backfill error: {e}")
                self._last_db_error_time = current_time
            return 0
        finally:
            self._is_backfilling = False

    def _watch_loop(self):
        last_inode = -1
        current_pos = 0
        
        while self.running:
            latest = self._get_latest_log()
            if not latest:
                time.sleep(2)
                continue
                
            try:
                stat = os.stat(latest)
                curr_inode = stat.st_ino
                curr_size = stat.st_size
                
                if curr_inode != last_inode:
                    # New file
                    logger.info(f"Log rotation: {os.path.basename(latest)}")
                    self.current_log_path = latest
                    last_inode = curr_inode
                    
                    # Truncate memory for new session logic
                    self.active_players.clear()
                    self.player_avatars.clear()
                    
                    # Backfill
                    current_pos = self._backfill(latest)
                    
                    # Notify UI of reset via "disconnected" then "backfill done"
                    self._emit({"type": "rotation"})
                    
                else:
                    # Same file, check tail in binary mode for safety? 
                    # Python's text mode buffering is okay for this frequency
                    if curr_size < current_pos:
                        # File truncated? (Rare for VRC log, but possible)
                        current_pos = 0 
                    
                    if curr_size > current_pos:
                        with open(latest, "r", encoding="utf-8", errors="replace") as f:
                            f.seek(current_pos)
                            lines = f.readlines()
                            current_pos = f.tell()
                            
                            for line in lines:
                                self._process_line(line, is_backfill=False)
            
            except Exception as e:
                # Throttle error logging - only log once per 60 seconds
                current_time = time.time()
                if current_time - self._last_db_error_time > 60:
                    logger.error(f"Watch loop error: {e}")
                    self._last_db_error_time = current_time
                time.sleep(1)
            
            time.sleep(0.5)

    def _process_line(self, line: str, is_backfill: bool = False):
        line = line.strip()
        if not line: return
        
        # Timestamp extraction is expensive, do lazily if needed?
        # FCH relies on log timestamp.
        # Format: 2023.10.25 15:30:00 ...
        ts_match = self.RE_TIMESTAMP.match(line)
        ts_str = ts_match.group(1) if ts_match else datetime.now().strftime("%Y.%m.%d %H:%M:%S")

        from .database import get_database
        db = get_database()

        # 1. Join
        # OnPlayerJoined Name (usr_...)
        m = self.RE_PLAYER_JOIN.search(line)
        if m:
            name, uid = m.group(1).strip(), m.group(2).strip()
            self.active_players[uid] = name
            
            val_location = f"{self.current_world_id}:{self.current_instance_id}" if self.current_world_id else ""
            
            # DB & Emit
            db.log_join(uid, name, ts_str, val_location)
            
            if not is_backfill:
                self._emit({
                    "type": "player_join", "user_id": uid, "display_name": name, 
                    "timestamp": ts_str
                })
            return

        # 2. Leave
        m = self.RE_PLAYER_LEAVE.search(line)
        if m:
            name, uid = m.group(1).strip(), m.group(2).strip()
            if uid in self.active_players:
                del self.active_players[uid]
            if uid in self.player_avatars:
                del self.player_avatars[uid]
            
            db.log_leave(uid, ts_str)
            
            if not is_backfill:
                self._emit({
                    "type": "player_leave", "user_id": uid, "name": name, 
                    "timestamp": ts_str
                })
            return

        # 3. Avatar
        m = self.RE_AVATAR_SWITCH.search(line)
        if m:
            name, av_name = m.group(1).strip(), m.group(2).strip()
            # Reverse lookup uid
            uid = next((u for u, n in self.active_players.items() if n == name), None)
            
            if uid:
                self.player_avatars[uid] = av_name
                db.log_avatar(uid, name, av_name, ts_str)
                
                if not is_backfill:
                    self._emit({
                        "type": "player_avatar_change", "user_id": uid, 
                        "name": name, "avatar_name": av_name, "timestamp": ts_str
                    })
            return

        # 4. Instance Join
        # Joining wrld_...:instance...
        m = self.RE_JOINING.search(line)
        if m:
            world_id = m.group(1)
            rest = m.group(2) # instance_id...
            # region?
            
            # Parse instance id (before ~)
            instance_id = rest.split("~")[0]
            
            # Find group
            grp_match = re.search(r"~group\((grp_[a-f0-9\-]{36})\)", rest)
            group_id = grp_match.group(1) if grp_match else None
            
            # State Update
            self.current_world_id = world_id
            self.current_instance_id = instance_id
            self.current_group_id = group_id
            
            # Clear players on map change
            self.active_players.clear()
            self.player_avatars.clear()
            
            # DB? 
            # We log system events too?
            db.log_join("system", "System", ts_str, f"{world_id}:{instance_id}")
            
            self._emit({
                "type": "instance_change", "world_id": world_id, 
                "instance_id": instance_id, "group_id": group_id, "timestamp": ts_str
            })
            return

        # 5. Quit/Left
        if self.RE_QUIT.search(line) or self.RE_LEFT_ROOM.search(line):
            self.active_players.clear()
            self.player_avatars.clear()
            
            db.log_join("system", "System", ts_str, "Left Room / Quit")
            
            if not is_backfill:
                self._emit({"type": "disconnected", "timestamp": ts_str})

    def _emit(self, data: Dict[str, Any]):
        for listener in self._listeners:
            try:
                listener(data)
            except: 
                pass

# Singleton
_watcher = None
def get_log_watcher(callback=None) -> LogWatcher:
    global _watcher
    if not _watcher:
        _watcher = LogWatcher()
    if callback:
        _watcher.add_listener(callback)
    return _watcher

