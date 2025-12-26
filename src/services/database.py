"""
Database Service for Group Guardian
===================================
Handles persistence for:
- User Profiles (sightings, known names, notes, watchlist)
- Join/Leave History
- Avatar History
- Asset/Media Logs

All data comes from VRChat logs - NO API calls.
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
            # Enhanced Users table - comprehensive user profiles
            # Primary key is user_id (never changes)
            # Searchable by username
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    current_username TEXT,
                    known_usernames TEXT DEFAULT '[]',
                    note TEXT,
                    is_watchlisted BOOLEAN DEFAULT 0,
                    is_favorite BOOLEAN DEFAULT 0,
                    sightings_count INTEGER DEFAULT 0,
                    first_seen TEXT,
                    last_seen TEXT,
                    total_time_together INTEGER DEFAULT 0,
                    custom_sound_path TEXT,
                    custom_color TEXT,
                    tags TEXT DEFAULT '[]'
                )
            """)
            
            # Create index for fast username search
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_username 
                ON users(current_username)
            """)

            # Join Logs (History) - tracks individual sessions
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
                    leave_timestamp TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Create index for user_id lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_join_logs_user 
                ON join_logs(user_id)
            """)

            # Avatar Logs - track avatar changes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS avatar_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT,
                    username TEXT,
                    avatar_name TEXT,
                    avatar_id TEXT,
                    perf_rating TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # Media/Asset Logs (for future use)
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
            
            # Custom Tags table - stores tag definitions with colors/descriptions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS custom_tags (
                    name TEXT PRIMARY KEY,
                    emoji TEXT DEFAULT '🏷️',
                    color TEXT DEFAULT '#808080',
                    description TEXT,
                    is_default BOOLEAN DEFAULT 0,
                    created_at TEXT
                )
            """)
            
            # Seed default tags if table is empty
            self._seed_default_tags(conn)
            
            # Migration: Add new columns if upgrading from old schema
            self._migrate_schema(conn)

            
            conn.commit()
            logger.info(f"Database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to init database: {e}")
        finally:
            conn.close()
    
    def _seed_default_tags(self, conn):
        """Seed default watchlist tags if not already present"""
        from datetime import datetime
        now = datetime.now().isoformat()
        
        default_tags = [
            ("Crasher", "🚨", "#FF4444", "Known to crash sessions", 1),
            ("Predator", "⚠️", "#FF0000", "Dangerous individual", 1),
            ("Zoophile", "🚫", "#880000", "Known zoophile", 1),
            ("Suspicious", "👀", "#FF9800", "Suspicious behavior", 1),
            ("Bad Vibes", "💀", "#9C27B0", "Generally unpleasant", 1),
            ("VIP", "⭐", "#FFD700", "Very important person", 1),
            ("Friend", "💚", "#4CAF50", "Trusted friend", 1),
            ("Mute Evader", "🔇", "#607D8B", "Uses alts to evade mutes", 1),
            ("Bot/Alt", "🤖", "#795548", "Bot or alternate account", 1),
            ("Harassment", "📛", "#E91E63", "Known harasser", 1),
            ("Ripper", "🏴‍☠️", "#673AB7", "Rips avatars/worlds", 1),
            ("Leaker", "💧", "#03A9F4", "Leaks private content", 1),
        ]
        
        for name, emoji, color, desc, is_default in default_tags:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO custom_tags (name, emoji, color, description, is_default, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (name, emoji, color, desc, is_default, now))
            except Exception as e:
                logger.debug(f"Tag {name} already exists or error: {e}")
    
    def _migrate_schema(self, conn):
        """Add new columns to existing tables if they don't exist"""
        # Check existing columns
        cursor = conn.execute("PRAGMA table_info(users)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        
        new_columns = [
            ("known_usernames", "TEXT DEFAULT '[]'"),
            ("sightings_count", "INTEGER DEFAULT 0"),
            ("first_seen", "TEXT"),
            ("is_favorite", "BOOLEAN DEFAULT 0"),
            ("total_time_together", "INTEGER DEFAULT 0"),
            ("custom_sound_path", "TEXT"),
            ("custom_color", "TEXT"),
            ("tags", "TEXT DEFAULT '[]'"),
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in existing_cols:
                try:
                    conn.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                    logger.info(f"Added column: {col_name}")
                except:
                    pass  # Column might already exist
        
        # Rename username to current_username if needed
        if "username" in existing_cols and "current_username" not in existing_cols:
            try:
                conn.execute("ALTER TABLE users RENAME COLUMN username TO current_username")
                logger.info("Renamed username to current_username")
            except:
                pass


    # --- User Profile Management ---

    def record_user_sighting(self, user_id: str, username: str) -> dict:
        """
        Record a user sighting from VRChat logs.
        - Creates user if new
        - Updates current username
        - Adds to known usernames if different
        - Increments sightings count
        - Updates first/last seen
        
        Returns the updated user profile.
        """
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            
            # Check if user exists
            cursor = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing user
                known_names = json.loads(existing['known_usernames'] or '[]')
                current_name = existing['current_username']
                
                # Add old name to known names if username changed
                if current_name and current_name != username and current_name not in known_names:
                    known_names.append(current_name)
                
                # Also add new name if not already tracking it
                if username and username not in known_names and username != current_name:
                    # This handles the case where we see them with a new name
                    pass  # New name becomes current, old becomes known
                
                conn.execute("""
                    UPDATE users SET
                        current_username = ?,
                        known_usernames = ?,
                        sightings_count = sightings_count + 1,
                        last_seen = ?
                    WHERE user_id = ?
                """, (username, json.dumps(known_names), now, user_id))
            else:
                # Create new user
                conn.execute("""
                    INSERT INTO users (
                        user_id, current_username, known_usernames,
                        sightings_count, first_seen, last_seen
                    ) VALUES (?, ?, '[]', 1, ?, ?)
                """, (user_id, username, now, now))
            
            conn.commit()
            return self.get_user_profile(user_id)
        finally:
            conn.close()

    def get_user_profile(self, user_id: str) -> Optional[dict]:
        """Get full user profile by ID"""
        conn = self._get_conn()
        try:
            cursor = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                profile = dict(row)
                # Parse JSON fields
                profile['known_usernames'] = json.loads(profile.get('known_usernames') or '[]')
                profile['tags'] = json.loads(profile.get('tags') or '[]')
                return profile
            return None
        finally:
            conn.close()

    def search_users(self, query: str, limit: int = 50) -> List[dict]:
        """
        Search users by username (current or known) or user ID.
        Prioritizes watchlisted users and those with notes.
        """
        conn = self._get_conn()
        try:
            q = f"%{query}%"
            cursor = conn.execute("""
                SELECT * FROM users 
                WHERE current_username LIKE ? 
                   OR user_id LIKE ? 
                   OR known_usernames LIKE ?
                   OR note LIKE ?
                ORDER BY 
                    is_watchlisted DESC,
                    is_favorite DESC,
                    sightings_count DESC,
                    last_seen DESC
                LIMIT ?
            """, (q, q, q, q, limit))
            
            results = []
            for row in cursor.fetchall():
                profile = dict(row)
                profile['known_usernames'] = json.loads(profile.get('known_usernames') or '[]')
                profile['tags'] = json.loads(profile.get('tags') or '[]')
                results.append(profile)
            return results
        finally:
            conn.close()

    def get_all_users(self, limit: int = 500, offset: int = 0) -> List[dict]:
        """Get all users sorted by last seen"""
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                SELECT * FROM users 
                ORDER BY last_seen DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            results = []
            for row in cursor.fetchall():
                profile = dict(row)
                profile['known_usernames'] = json.loads(profile.get('known_usernames') or '[]')
                profile['tags'] = json.loads(profile.get('tags') or '[]')
                results.append(profile)
            return results
        finally:
            conn.close()

    def get_user_count(self) -> int:
        """Get total number of tracked users"""
        conn = self._get_conn()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM users")
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def set_user_note(self, user_id: str, note: str):
        """Set or update a user's note"""
        conn = self._get_conn()
        try:
            conn.execute("UPDATE users SET note = ? WHERE user_id = ?", (note, user_id))
            conn.commit()
        finally:
            conn.close()

    def toggle_watchlist(self, user_id: str, state: bool):
        """Toggle watchlist status for a user"""
        conn = self._get_conn()
        try:
            conn.execute("UPDATE users SET is_watchlisted = ? WHERE user_id = ?", (1 if state else 0, user_id))
            conn.commit()
        finally:
            conn.close()

    def toggle_favorite(self, user_id: str, state: bool):
        """Toggle favorite status for a user"""
        conn = self._get_conn()
        try:
            conn.execute("UPDATE users SET is_favorite = ? WHERE user_id = ?", (1 if state else 0, user_id))
            conn.commit()
        finally:
            conn.close()

    def add_user_tag(self, user_id: str, tag: str):
        """Add a tag to a user"""
        conn = self._get_conn()
        try:
            cursor = conn.execute("SELECT tags FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                tags = json.loads(row['tags'] or '[]')
                if tag not in tags:
                    tags.append(tag)
                    conn.execute("UPDATE users SET tags = ? WHERE user_id = ?", (json.dumps(tags), user_id))
                    conn.commit()
        finally:
            conn.close()

    def remove_user_tag(self, user_id: str, tag: str):
        """Remove a tag from a user"""
        conn = self._get_conn()
        try:
            cursor = conn.execute("SELECT tags FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                tags = json.loads(row['tags'] or '[]')
                if tag in tags:
                    tags.remove(tag)
                    conn.execute("UPDATE users SET tags = ? WHERE user_id = ?", (json.dumps(tags), user_id))
                    conn.commit()
        finally:
            conn.close()

    def get_watchlisted_users(self) -> List[dict]:
        """Get all watchlisted users"""
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                SELECT * FROM users WHERE is_watchlisted = 1
                ORDER BY last_seen DESC
            """)
            results = []
            for row in cursor.fetchall():
                profile = dict(row)
                profile['known_usernames'] = json.loads(profile.get('known_usernames') or '[]')
                profile['tags'] = json.loads(profile.get('tags') or '[]')
                results.append(profile)
            return results
        finally:
            conn.close()

    def get_favorite_users(self) -> List[dict]:
        """Get all favorite users"""
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                SELECT * FROM users WHERE is_favorite = 1
                ORDER BY last_seen DESC
            """)
            results = []
            for row in cursor.fetchall():
                profile = dict(row)
                profile['known_usernames'] = json.loads(profile.get('known_usernames') or '[]')
                profile['tags'] = json.loads(profile.get('tags') or '[]')
                results.append(profile)
            return results
        finally:
            conn.close()

    def get_users_by_tag(self, tag: str) -> List[dict]:
        """Get all users with a specific tag"""
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                SELECT * FROM users WHERE tags LIKE ?
                ORDER BY last_seen DESC
            """, (f'%"{tag}"%',))
            results = []
            for row in cursor.fetchall():
                profile = dict(row)
                profile['known_usernames'] = json.loads(profile.get('known_usernames') or '[]')
                profile['tags'] = json.loads(profile.get('tags') or '[]')
                results.append(profile)
            return results
        finally:
            conn.close()

    def get_user_data(self, user_id: str) -> Optional[dict]:
        """Legacy method - use get_user_profile instead"""
        return self.get_user_profile(user_id)

    # --- History / Logs ---

    def log_join(self, user_id: str, username: str, timestamp: str, location: str = ""):
        """Log a join event (for history tracking)"""
        conn = self._get_conn()
        try:
            # Insert log entry
            conn.execute("""
                INSERT INTO join_logs (timestamp, user_id, username, event_kind, location)
                VALUES (?, ?, ?, 'join', ?)
            """, (timestamp, user_id, username, location))
            conn.commit()
        finally:
            conn.close()

    def log_leave(self, user_id: str, timestamp: str):
        """Log a leave event by updating the most recent join"""
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
        """Get users who have joined but not left (current instance)"""
        conn = self._get_conn()
        try:
            cur = conn.execute("""
                SELECT 
                    j.*, 
                    u.note, 
                    u.is_watchlisted,
                    u.is_favorite,
                    u.sightings_count,
                    u.known_usernames,
                    u.current_username as known_username 
                FROM join_logs j
                LEFT JOIN users u ON j.user_id = u.user_id
                WHERE j.leave_timestamp IS NULL AND j.is_system = 0
                ORDER BY j.timestamp DESC
            """)
            results = []
            for row in cur.fetchall():
                profile = dict(row)
                profile['known_usernames'] = json.loads(profile.get('known_usernames') or '[]')
                results.append(profile)
            return results
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
