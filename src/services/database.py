"""
Database Service for Group Guardian
===================================
Handles persistence for:
- User Notes & Watchlists
- Join/Leave History
- Avatar History
- Asset/Media Logs
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from utils.paths import get_database_path

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, db_path: str = None):
        # Use centralized path utility for EXE-relative path
        self.db_path = Path(db_path) if db_path else get_database_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database schema"""
        conn = self._get_conn()
        try:
            # Users table (Notes, Watchlist, Sounds)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT,
                    note TEXT,
                    is_watchlisted BOOLEAN DEFAULT 0,
                    sound_path TEXT,
                    last_seen TIMESTAMP
                )
            """)

            # Join Logs (History)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS join_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    username TEXT,
                    is_system BOOLEAN DEFAULT 0,
                    event_kind TEXT,
                    world_id TEXT,
                    instance_id TEXT,
                    location TEXT,
                    leave_timestamp TEXT
                )
            """)

            # Avatar Logs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS avatar_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT,
                    username TEXT,
                    avatar_name TEXT,
                    avatar_id TEXT,
                    perf_rating TEXT
                )
            """)

            # Media/Asset Logs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS media_logs (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    type TEXT,
                    owner_id TEXT,
                    image_url TEXT,
                    meta_json TEXT
                )
            """)
            
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to init database: {e}")
        finally:
            conn.close()

    # --- User Management ---

    def update_user_metadata(self, user_id: str, username: str = None):
        """Update last seen username and timestamp"""
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            if username:
                conn.execute("""
                    INSERT INTO users (user_id, username, last_seen)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                    username = ?, 
                    last_seen = ?
                """, (user_id, username, now, username, now))
            else:
                conn.execute("""
                    INSERT INTO users (user_id, last_seen)
                    VALUES (?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                    last_seen = ?
                """, (user_id, now, now))
            conn.commit()
        finally:
            conn.close()

    def set_user_note(self, user_id: str, note: str):
        conn = self._get_conn()
        try:
            # Ensure user exists first
            self.update_user_metadata(user_id)
            conn.execute("UPDATE users SET note = ? WHERE user_id = ?", (note, user_id))
            conn.commit()
        finally:
            conn.close()

    def toggle_watchlist(self, user_id: str, state: bool):
        conn = self._get_conn()
        try:
            self.update_user_metadata(user_id)
            conn.execute("UPDATE users SET is_watchlisted = ? WHERE user_id = ?", (1 if state else 0, user_id))
            conn.commit()
        finally:
            conn.close()
            
    def get_user_data(self, user_id: str) -> Optional[dict]:
        conn = self._get_conn()
        try:
            cur = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def search_users(self, query: str) -> List[dict]:
        """Search users by name or ID, prioritizes those with notes/watchlist"""
        conn = self._get_conn()
        try:
            q = f"%{query}%"
            # Prioritize matches with notes or watchlist
            cur = conn.execute("""
                SELECT * FROM users 
                WHERE username LIKE ? OR user_id LIKE ? OR note LIKE ?
                ORDER BY is_watchlisted DESC, note IS NOT NULL DESC, last_seen DESC
                LIMIT 50
            """, (q, q, q))
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    # --- History / Logs ---

    def log_join(self, user_id: str, username: str, timestamp: str, location: str = ""):
        conn = self._get_conn()
        try:
            # First ensure user metadata
            self.update_user_metadata(user_id, username)
            
            # Insert log
            conn.execute("""
                INSERT INTO join_logs (timestamp, user_id, username, event_kind, location)
                VALUES (?, ?, ?, 'join', ?)
            """, (timestamp, user_id, username, location))
            conn.commit()
        finally:
            conn.close()

    def log_leave(self, user_id: str, timestamp: str):
        conn = self._get_conn()
        try:
            # Find latest open join for this user
            conn.execute("""
                UPDATE join_logs 
                SET leave_timestamp = ? 
                WHERE id = (
                    SELECT id FROM join_logs 
                    WHERE user_id = ? AND leave_timestamp IS NULL 
                    ORDER BY id DESC LIMIT 1
                )
            """, (timestamp, user_id))
            conn.commit()
        finally:
            conn.close()

    def get_active_users(self) -> List[dict]:
        """Get users who have joined but not left"""
        conn = self._get_conn()
        try:
            cur = conn.execute("""
                SELECT 
                    j.*, 
                    u.note, 
                    u.is_watchlisted, 
                    u.username as known_username 
                FROM join_logs j
                LEFT JOIN users u ON j.user_id = u.user_id
                WHERE j.leave_timestamp IS NULL AND j.is_system = 0
                ORDER BY j.timestamp DESC
            """)
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()
            
    def get_recent_history(self, limit: int = 100) -> List[dict]:
        conn = self._get_conn()
        try:
            cur = conn.execute("""
                SELECT * FROM join_logs 
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    # --- Avatar & Assets ---
    
    def log_avatar(self, user_id: str, username: str, avatar_name: str, timestamp: str):
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO avatar_logs (timestamp, user_id, username, avatar_name)
                VALUES (?, ?, ?, ?)
            """, (timestamp, user_id, username, avatar_name))
            conn.commit()
        finally:
            conn.close()

# Singleton instance
_db_instance = None

def get_database() -> DatabaseService:
    global _db_instance
    if not _db_instance:
        _db_instance = DatabaseService()
    return _db_instance
