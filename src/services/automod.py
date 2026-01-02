"""
Auto-Moderation Service
=======================
Handles automatic acceptance/rejection of group join requests based on criteria.

Criteria available:
- Bio keywords (requires fetching full user profile) - uses WHOLE WORD matching
- Trust rank (from user tags)
- Age verification status
- Account age (when account was created)
- Profile picture (has custom image or not)
"""

import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from services.debug_logger import get_logger
from services.database import get_database
from services.notification_service import get_notification_service

logger = get_logger("services.automod")

# Trust rank tags in order from lowest to highest
TRUST_RANKS = [
    ("system_trust_basic", "New User", 1),
    ("system_trust_known", "User", 2),
    ("system_trust_trusted", "Known User", 3),
    ("system_trust_veteran", "Trusted User", 4),
    ("system_trust_legend", "Legendary User", 5),  # Very rare
]

def get_trust_rank(tags: List[str]) -> Tuple[str, str, int]:
    """
    Get the user's trust rank from their tags.
    Returns (tag, display_name, level) where level is 0-5.
    """
    for tag, name, level in reversed(TRUST_RANKS):  # Start from highest
        if tag in tags:
            return (tag, name, level)
    return ("visitor", "Visitor", 0)

def is_age_verified(user: Dict) -> bool:
    """Check if user is age verified (18+)"""
    # Check multiple possible fields
    tags = user.get("tags", [])
    
    # Check tags for age verification
    if "system_age_verified" in tags:
        return True
    
    # Check ageVerificationStatus field (from full user fetch)
    age_status = user.get("ageVerificationStatus", "")
    if age_status in ["verified", "verified_18"]:
        return True
    
    # Check 'ageVerified' boolean (VRCX style)
    if user.get("ageVerified", False):
        return True
        
    return False

def get_account_age_days(user: Dict) -> Optional[int]:
    """Get account age in days from date_joined field"""
    date_joined = user.get("date_joined")
    if not date_joined:
        return None
    
    try:
        # Parse ISO format date
        if "T" in date_joined:
            created = datetime.fromisoformat(date_joined.replace("Z", "+00:00"))
        else:
            created = datetime.strptime(date_joined, "%Y-%m-%d")
        
        now = datetime.now(created.tzinfo) if created.tzinfo else datetime.now()
        return (now - created).days
    except Exception as e:
        logger.debug(f"Could not parse date_joined: {date_joined} - {e}")
        return None


def keyword_matches_text(keyword: str, text: str) -> bool:
    """
    Check if a keyword matches in the text using WHOLE WORD matching.
    
    This prevents 'her' from matching 'here', 'there', 'whether', etc.
    Uses regex word boundaries (\b) for accurate matching.
    
    Args:
        keyword: The keyword to search for (case insensitive)
        text: The text to search in (should already be lowercase)
        
    Returns:
        True if keyword matches as a whole word, False otherwise
    """
    keyword = keyword.lower().strip()
    if not keyword:
        return False
    
    # Escape special regex characters in the keyword
    escaped_keyword = re.escape(keyword)
    
    # Use word boundaries for whole-word matching
    # \b matches word boundaries (start/end of word)
    pattern = r'\b' + escaped_keyword + r'\b'
    
    return bool(re.search(pattern, text, re.IGNORECASE))


class AutoModService:
    def __init__(self):
        self.db = get_database()

    async def process_join_requests(self, api, group_id: str, requests: List[Dict]) -> List[str]:
        """
        Process a list of join requests against auto-mod rules.
        
        Args:
            api: The VRChat API client instance (must have GroupsMixin)
            group_id: Group ID
            requests: List of join request objects
            
        Returns:
            List of user IDs that were processed (accepted or rejected)
        """
        settings = self.db.get_group_settings(group_id)
        if not settings or not settings.get("automod_enabled"):
            logger.debug(f"Auto-mod disabled for group {group_id}")
            return []
            
        processed_user_ids = []
        
        # Get settings
        require_keywords = settings.get("automod_require_keywords", [])
        exclude_keywords = settings.get("automod_exclude_keywords", [])
        age_verified_only = bool(settings.get("automod_age_verified_only", 0))
        min_trust_rank = settings.get("automod_min_trust_rank", 0)  # 0 = no requirement
        min_account_age_days = settings.get("automod_min_account_age_days", 0)  # 0 = no requirement
        
        logger.info(f"Running Auto-Mod for group {group_id} ({len(requests)} requests)")
        logger.info(f"Settings: age_verified={age_verified_only}, min_trust={min_trust_rank}, " +
                   f"min_account_days={min_account_age_days}, req_keywords={require_keywords}, ex_keywords={exclude_keywords}")
        
        for req in requests:
            try:
                user = req.get("user", {})
                user_id = req.get("userId") or user.get("id")
                if not user_id:
                    continue
                    
                display_name = user.get("displayName", "Unknown")
                
                # The join request has limited user data - we need to fetch full profile for bio
                # Only fetch if we need bio keywords or account age
                full_user = None
                if require_keywords or exclude_keywords or min_account_age_days > 0:
                    logger.debug(f"Fetching full profile for {display_name} ({user_id})...")
                    full_user = await api.get_user(user_id)
                    if full_user:
                        # Merge full user data
                        user = {**user, **full_user}
                
                # Extract fields
                bio = user.get("bio", "") or ""
                status_desc = user.get("statusDescription", "") or ""
                tags = user.get("tags", [])
                
                # Combined text to search for keywords
                search_text = (bio + " " + status_desc).lower()
                
                # Get trust rank
                trust_tag, trust_name, trust_level = get_trust_rank(tags)
                
                # Get age verification
                verified_18 = is_age_verified(user)
                
                # Get account age
                account_age = get_account_age_days(user)
                
                logger.debug(f"User {display_name}: trust={trust_name}({trust_level}), " +
                           f"age_verified={verified_18}, account_days={account_age}, bio_len={len(bio)}")
                
                # ===== DENY CHECKS =====
                action = None
                reason = ""
                
                # 1. Age Verification Check (DENY if required but not verified)
                if age_verified_only and not verified_18:
                    action = "reject"
                    reason = "Not age verified (18+ required)"
                
                # 2. Trust Rank Check (DENY if below minimum)
                if not action and min_trust_rank > 0 and trust_level < min_trust_rank:
                    action = "reject"
                    reason = f"Trust rank too low: {trust_name} (minimum level {min_trust_rank} required)"
                
                # 3. Account Age Check (DENY if too new)
                if not action and min_account_age_days > 0:
                    if account_age is None:
                        # If we can't determine age, skip this check (don't deny)
                        logger.debug(f"Could not determine account age for {display_name}")
                    elif account_age < min_account_age_days:
                        action = "reject"
                        reason = f"Account too new: {account_age} days (minimum {min_account_age_days} required)"
                
                # 4. Blocked Keywords (DENY if bio contains any) - WHOLE WORD MATCHING
                # Check for deny keywords first
                matched_deny_keyword = None
                if not action and exclude_keywords:
                    for keyword in exclude_keywords:
                        if keyword_matches_text(keyword, search_text):
                            matched_deny_keyword = keyword
                            break
                
                # 5. Required Keywords (ACCEPT if bio contains any) - WHOLE WORD MATCHING
                # Check for accept keywords
                matched_accept_keyword = None
                if require_keywords:
                    for keyword in require_keywords:
                        if keyword_matches_text(keyword, search_text):
                            matched_accept_keyword = keyword
                            break
                
                # === CONFLICT RESOLUTION: Deny always wins ===
                # If both deny and accept keywords match, DENY takes priority
                if matched_deny_keyword:
                    action = "reject"
                    if matched_accept_keyword:
                        reason = f"Bio contains blocked keyword: '{matched_deny_keyword}' (overrides match for '{matched_accept_keyword}')"
                        logger.info(f"Keyword conflict for {display_name}: deny '{matched_deny_keyword}' wins over accept '{matched_accept_keyword}'")
                    else:
                        reason = f"Bio contains blocked keyword: '{matched_deny_keyword}'"
                elif not action and matched_accept_keyword:
                    action = "accept"
                    reason = f"Bio matches required keyword: '{matched_accept_keyword}'"
                
                # Execute action if any
                if action:
                    logger.info(f"Auto-Mod: {action.upper()} {display_name} - {reason}")
                    
                    # Call API
                    success = await api.handle_join_request(group_id, user_id, action)
                    
                    if success:
                        # Log to DB
                        self.db.log_automod_action(group_id, user_id, display_name, action, reason)
                        processed_user_ids.append(user_id)
                        logger.info(f"Auto-Mod action completed: {action} for {display_name}")
                        
                        # Play notification sound
                        notif_service = get_notification_service()
                        notif_service.notify_automod_action(accepted=(action == "accept"))
                    else:
                        logger.error(f"Auto-Mod action FAILED: {action} for {display_name}")
                else:
                    logger.debug(f"No auto-mod action for {display_name} - requires manual review")
                        
            except Exception as e:
                logger.error(f"Error auto-processing request for user: {e}")
                import traceback
                traceback.print_exc()
                
        return processed_user_ids


_automod_service = None
def get_automod_service():
    global _automod_service
    if not _automod_service:
        _automod_service = AutoModService()
    return _automod_service
