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
from services.event_bus import get_event_bus
from utils.crypto import get_integrity_service

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
                    custom_sound_path TEXT,
                    custom_color TEXT,
                    tags TEXT DEFAULT '[]',
                    integrity_hash TEXT
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
                    location TEXT,
                    leave_timestamp TEXT,
                    integrity_hash TEXT,
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
            
            # Group Settings table - per-group configuration (e.g., auto-close non-age-verified instances)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS group_settings (
                    group_id TEXT PRIMARY KEY,
                    group_name TEXT,
                    auto_close_non_age_verified BOOLEAN DEFAULT 0,
                    automod_enabled BOOLEAN DEFAULT 0,
                    automod_age_verified_only BOOLEAN DEFAULT 0,
                    automod_require_keywords TEXT DEFAULT '[]',
                    automod_exclude_keywords TEXT DEFAULT '[]',
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # Auto-Mod Logs - track automatic approvals/rejections
            conn.execute("""
                CREATE TABLE IF NOT EXISTS automod_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    username TEXT,
                    action TEXT,
                    reason TEXT
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
        from services.watchlist_alerts import DEFAULT_TAGS
        now = datetime.now().isoformat()
        
        # Use centralized tag definitions from watchlist_alerts
        for tag in DEFAULT_TAGS:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO custom_tags (name, emoji, color, description, is_default, created_at)
                    VALUES (?, ?, ?, ?, 1, ?)
                """, (tag["name"], tag["emoji"], tag["color"], tag.get("description", ""), now))
            except Exception as e:
                logger.debug(f"Tag {tag['name']} already exists or error: {e}")
    
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
            ("custom_color", "TEXT"),
            ("tags", "TEXT DEFAULT '[]'"),
            ("integrity_hash", "TEXT"),
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

        # Group Settings table migrations
        cursor = conn.execute("PRAGMA table_info(group_settings)")
        existing_group_cols = {row[1] for row in cursor.fetchall()}
        
        new_group_columns = [
            ("automod_enabled", "BOOLEAN DEFAULT 0"),
            ("automod_age_verified_only", "BOOLEAN DEFAULT 0"),
            ("automod_require_keywords", "TEXT DEFAULT '[]'"),
            ("automod_exclude_keywords", "TEXT DEFAULT '[]'"),
            ("automod_min_trust_rank", "INTEGER DEFAULT 0"),
            ("automod_min_account_age_days", "INTEGER DEFAULT 0"),
        ]
        
        for col_name, col_type in new_group_columns:
            if col_name not in existing_group_cols:
                try:
                    conn.execute(f"ALTER TABLE group_settings ADD COLUMN {col_name} {col_type}")
                    logger.info(f"Added column to group_settings: {col_name}")
                except:
                    pass

        # Ensure automod_logs table exists (double check for existing databases)
        # This handles cases where _init_db might have skipped it in earlier versions
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS automod_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    username TEXT,
                    action TEXT,
                    reason TEXT
                )
            """)
        except Exception as e:
            logger.debug(f"Failed to ensure automod_logs table in migrate: {e}")



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
                
                # Calculate hash for update
                new_sightings = existing['sightings_count'] + 1
                first_seen = existing['first_seen']
                
                integrity = get_integrity_service().generate_hash({
                    "user_id": user_id,
                    "sightings_count": new_sightings,
                    "first_seen": first_seen
                }, ["user_id", "sightings_count", "first_seen"])
                
                conn.execute("""
                    UPDATE users SET
                        current_username = ?,
                        known_usernames = ?,
                        sightings_count = sightings_count + 1,
                        last_seen = ?,
                        integrity_hash = ?
                    WHERE user_id = ?
                """, (username, json.dumps(known_names), now, integrity, user_id))
            else:
                # Create new user
                # Calculate initial hash
                integrity = get_integrity_service().generate_hash({
                    "user_id": user_id,
                    "sightings_count": 1,
                    "first_seen": now
                }, ["user_id", "sightings_count", "first_seen"])
                
                conn.execute("""
                    INSERT INTO users (
                        user_id, current_username, known_usernames,
                        sightings_count, first_seen, last_seen, integrity_hash
                    ) VALUES (?, ?, '[]', 1, ?, ?, ?)
                """, (user_id, username, now, now, integrity))
            
            conn.commit()
            
            # Emit update
            get_event_bus().emit("user_updated", {"user_id": user_id})
            
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
                # Check integrity
                is_valid = get_integrity_service().verify_hash(
                    profile, 
                    ["user_id", "sightings_count", "first_seen"], 
                    profile.get("integrity_hash")
                )
                profile['integrity_valid'] = is_valid
                
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
                
                # Check Integrity
                try:
                    profile['integrity_valid'] = get_integrity_service().verify_hash(
                        profile, 
                        ["user_id", "sightings_count", "first_seen"], 
                        profile.get("integrity_hash")
                    )
                except:
                    profile['integrity_valid'] = False
                    
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
                
                # Check Integrity
                try:
                    profile['integrity_valid'] = get_integrity_service().verify_hash(
                        profile, 
                        ["user_id", "sightings_count", "first_seen"], 
                        profile.get("integrity_hash")
                    )
                except:
                    profile['integrity_valid'] = False

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
            get_event_bus().emit("user_updated", {"user_id": user_id})
        finally:
            conn.close()

    def toggle_watchlist(self, user_id: str, state: bool):
        """Toggle watchlist status for a user"""
        conn = self._get_conn()
        try:
            conn.execute("UPDATE users SET is_watchlisted = ? WHERE user_id = ?", (1 if state else 0, user_id))
            conn.commit()
            get_event_bus().emit("user_updated", {"user_id": user_id})
            get_event_bus().emit("watchlist_updated", {"user_id": user_id, "state": state})
        finally:
            conn.close()

    def toggle_favorite(self, user_id: str, state: bool):
        """Toggle favorite status for a user"""
        conn = self._get_conn()
        try:
            conn.execute("UPDATE users SET is_favorite = ? WHERE user_id = ?", (1 if state else 0, user_id))
            conn.commit()
            get_event_bus().emit("user_updated", {"user_id": user_id})
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
                    get_event_bus().emit("user_updated", {"user_id": user_id})
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
                    get_event_bus().emit("user_updated", {"user_id": user_id})
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
            # Calculate hash
            integrity = get_integrity_service().generate_hash({
                "timestamp": timestamp,
                "user_id": user_id,
                "event_kind": "join",
                "location": location
            }, ["timestamp", "user_id", "event_kind", "location"])
            
            conn.execute("""
                INSERT INTO join_logs (timestamp, user_id, username, event_kind, location, integrity_hash)
                VALUES (?, ?, ?, 'join', ?, ?)
            """, (timestamp, user_id, username, location, integrity))
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

    
    def get_group_settings(self, group_id: str) -> Optional[dict]:
        """Get settings for a specific group"""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM group_settings WHERE group_id = ?", 
                (group_id,)
            )
            row = cursor.fetchone()
            if row:
                data = dict(row)
                # Parse JSON fields
                data['automod_require_keywords'] = json.loads(data.get('automod_require_keywords') or '[]')
                data['automod_exclude_keywords'] = json.loads(data.get('automod_exclude_keywords') or '[]')
                return data
            return None
        finally:
            conn.close()
    
    def set_group_auto_close_non_age_verified(self, group_id: str, group_name: str, enabled: bool):
        """Set whether to auto-close non-age-verified instances for a group"""
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            # Upsert - insert or update
            conn.execute("""
                INSERT INTO group_settings (group_id, group_name, auto_close_non_age_verified, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(group_id) DO UPDATE SET
                    group_name = excluded.group_name,
                    auto_close_non_age_verified = excluded.auto_close_non_age_verified,
                    updated_at = excluded.updated_at
            """, (group_id, group_name, 1 if enabled else 0, now, now))
            conn.commit()
            logger.info(f"Set auto_close_non_age_verified={enabled} for group {group_name} ({group_id})")
            get_event_bus().emit("group_settings_updated", {
                "group_id": group_id, 
                "auto_close_non_age_verified": enabled
            })
        finally:
            conn.close()
    
    def get_groups_with_auto_close_enabled(self) -> List[str]:
        """Get list of group IDs that have auto-close non-age-verified enabled"""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT group_id FROM group_settings WHERE auto_close_non_age_verified = 1"
            )
            return [row['group_id'] for row in cursor.fetchall()]
        finally:
            conn.close()

    def set_group_automod_settings(self, group_id: str, group_name: str, enabled: bool, 
                                 age_verified_only: bool, require_keywords: list, exclude_keywords: list,
                                 min_trust_rank: int = 0, min_account_age_days: int = 0):
        """Update auto-moderation settings for a group"""
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            require_json = json.dumps(require_keywords)
            exclude_json = json.dumps(exclude_keywords)
            
            conn.execute("""
                INSERT INTO group_settings (
                    group_id, group_name, 
                    automod_enabled, automod_age_verified_only, 
                    automod_require_keywords, automod_exclude_keywords,
                    automod_min_trust_rank, automod_min_account_age_days,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(group_id) DO UPDATE SET
                    group_name = excluded.group_name,
                    automod_enabled = excluded.automod_enabled,
                    automod_age_verified_only = excluded.automod_age_verified_only,
                    automod_require_keywords = excluded.automod_require_keywords,
                    automod_exclude_keywords = excluded.automod_exclude_keywords,
                    automod_min_trust_rank = excluded.automod_min_trust_rank,
                    automod_min_account_age_days = excluded.automod_min_account_age_days,
                    updated_at = excluded.updated_at
            """, (
                group_id, group_name, 
                1 if enabled else 0, 1 if age_verified_only else 0,
                require_json, exclude_json,
                min_trust_rank, min_account_age_days,
                now, now
            ))
            conn.commit()
            
            logger.info(f"Saved automod settings for {group_name}: enabled={enabled}, age={age_verified_only}, trust={min_trust_rank}, days={min_account_age_days}")
            
            get_event_bus().emit("group_settings_updated", {
                "group_id": group_id,
                "automod_enabled": enabled
            })
        finally:
            conn.close()

    def log_automod_action(self, group_id: str, user_id: str, username: str, action: str, reason: str):
        """Log an auto-moderation action"""
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            # Calculate hash
            integrity = get_integrity_service().generate_hash({
                "timestamp": now,
                "group_id": group_id,
                "user_id": user_id,
                "action": action,
                "reason": reason
            }, ["timestamp", "group_id", "user_id", "action", "reason"])

            conn.execute("""
                INSERT INTO automod_logs (timestamp, group_id, user_id, username, action, reason, integrity_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (now, group_id, user_id, username, action, reason, integrity))
            conn.commit()
        finally:
            conn.close()
            
    def get_automod_logs(self, group_id: str, limit: int = 50) -> List[dict]:
        """Get auto-moderation logs for a group"""
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                SELECT * FROM automod_logs 
                WHERE group_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (group_id, limit))
            results = []
            for row in cursor.fetchall():
                log = dict(row)
                is_valid = get_integrity_service().verify_hash(
                    log, 
                    ["timestamp", "group_id", "user_id", "action", "reason"], 
                    log.get("integrity_hash")
                )
                log['integrity_valid'] = is_valid
                results.append(log)
            return results
        finally:
            conn.close()

    def get_integrity_report(self) -> dict:
        """Scan entire database and report integrity stats"""
        conn = self._get_conn()
        stats = {
            "total_records": 0,
            "verified_records": 0,
            "tampered_records": 0,
            "unsigned_records": 0,
            "details": {}
        }
        
        try:
            # Check Users
            cursor = conn.execute("SELECT * FROM users")
            users = cursor.fetchall()
            stats["total_records"] += len(users)
            stats["details"]["users"] = {"total": len(users), "tampered": 0}
            
            for row in users:
                data = dict(row)
                if not data.get("integrity_hash"):
                    stats["unsigned_records"] += 1
                    continue
                    
                is_valid = get_integrity_service().verify_hash(
                    data, 
                    ["user_id", "sightings_count", "first_seen"], 
                    data.get("integrity_hash")
                )
                
                if is_valid:
                    stats["verified_records"] += 1
                else:
                    stats["tampered_records"] += 1
                    stats["details"]["users"]["tampered"] += 1

            # Check Join Logs
            cursor = conn.execute("SELECT * FROM join_logs")
            logs = cursor.fetchall()
            stats["total_records"] += len(logs)
            stats["details"]["join_logs"] = {"total": len(logs), "tampered": 0}

            for row in logs:
                data = dict(row)
                if not data.get("integrity_hash"):
                    stats["unsigned_records"] += 1
                    continue

                # event_kind/location logic needs to match log_join
                # Note: log_join sets event_kind='join'. 
                # Currently we only hash 'join' events fully.
                # If event_kind is missing, default to join? No, DB has it.
                
                is_valid = get_integrity_service().verify_hash(
                    data,
                    ["timestamp", "user_id", "event_kind", "location"],
                    data.get("integrity_hash")
                )

                if is_valid:
                    stats["verified_records"] += 1
                else:
                    stats["tampered_records"] += 1
                    stats["details"]["join_logs"]["tampered"] += 1
            
            return stats

        finally:
            conn.close()

# Singleton instance
_db_instance = None

def get_database() -> DatabaseService:
    global _db_instance
    if not _db_instance:
        _db_instance = DatabaseService()
    return _db_instance
