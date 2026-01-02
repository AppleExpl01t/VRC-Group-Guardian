# Codebase Optimization Action Plan

**Created:** 2025-12-26  
**Status:** In Progress  
**Priority Legend:** 🔴 High | 🟡 Medium | 🟢 Low

---

## Overview

This document outlines the remaining optimization tasks identified during the codebase audit. These are larger refactors that require careful planning and testing.

---

## 1. Split Large API Client File

**Priority:** 🟡 Medium  
**Estimated Effort:** 4-6 hours  
**Risk Level:** Medium (requires careful import management)

### Current State
`src/api/client.py` is 2019 lines (~78KB) containing:
- Authentication logic (login, 2FA, session management)
- Rate limiting (token bucket, backoff)
- Request handling (deduplication, error caching)
- Image caching
- Group management (CRUD, members, bans, instances)
- User management (search, friends)
- Invite management
- WebSocket token handling

### Proposed Structure
```
src/api/
├── __init__.py          # Export main VRChatAPI class
├── client.py            # Main API client (orchestrator, ~200 lines)
├── auth.py              # Authentication module (~150 lines)
│   ├── login()
│   ├── verify_2fa()
│   ├── check_session()
│   ├── logout()
│   └── Cookie management
├── request_handler.py   # Request handling (~200 lines)
│   ├── _request()
│   ├── _vrcx_rate_limit()
│   ├── _is_failed_request_cached()
│   ├── _execute_with_backoff()
│   └── Pending request deduplication
├── groups.py            # Group operations (~400 lines)
│   ├── get_my_groups()
│   ├── get_group()
│   ├── get_group_instances()
│   ├── get_group_join_requests()
│   ├── get_group_bans()
│   ├── get_group_members()
│   ├── handle_join_request()
│   ├── ban_user() / unban_user() / kick_user()
│   └── create_instance() / close_instance()
├── users.py             # User operations (~200 lines)
│   ├── get_user()
│   ├── search_users()
│   ├── get_friends()
│   ├── get_all_friends()
│   └── invite_to_instance()
├── images.py            # Image caching (~100 lines)
│   ├── download_image()
│   ├── cache_user_image()
│   └── cache_group_images()
├── worlds.py            # World operations (~100 lines)
│   ├── get_world()
│   ├── search_worlds()
│   └── get_cached_world()
└── cache.py             # Cache methods (~150 lines)
    ├── get_cached_*() methods
    └── invalidate_*() methods
```

### Implementation Steps

1. **Create module files** (30 min)
   - Create empty module files with proper imports
   - Define `__all__` exports

2. **Extract auth.py** (1 hour)
   - Move login, verify_2fa, check_session, logout
   - Move cookie management (_load_cookies, _save_cookies, _get_cookies)
   - Create AuthMixin class or standalone functions

3. **Extract request_handler.py** (1 hour)
   - Move _request method and all rate limiting logic
   - This is the trickiest part - needs careful dependency handling

4. **Extract groups.py** (1 hour)
   - Move all group-related methods
   - Create GroupsMixin or standalone async functions

5. **Extract users.py** (45 min)
   - Move user/friend methods

6. **Extract images.py** (30 min)
   - Move image caching methods

7. **Extract worlds.py** (30 min)
   - Move world search/fetch methods

8. **Extract cache.py** (30 min)
   - Move all get_cached_* and invalidate_* methods

9. **Update client.py** (30 min)
   - Compose mixins or call module functions
   - Update imports

10. **Testing** (1 hour)
    - Test all API operations
    - Test demo mode
    - Test error handling

### Dependencies
- None (can be done independently)

### Rollback Plan
- Keep original client.py as client_backup.py until fully tested

---

## 2. Migrate API Client to Centralized CacheManager

**Priority:** 🟢 Low  
**Estimated Effort:** 3-4 hours  
**Risk Level:** High (could affect cached data behavior)

### Current State
`VRChatAPI` has its own simple file-based cache:
```python
self._cache = self._load_api_cache()  # Dict from JSON file
self._cache_file = get_api_cache_path()
```

`CacheManager` in `services/cache_manager.py` has:
- TTL-based expiration
- LRU eviction
- In-memory + optional disk persistence
- Entity-specific merge functions
- Background cleanup task

### Proposed Changes

1. **Remove duplicate cache from VRChatAPI**
   - Remove `_cache`, `_cache_file`, `_load_api_cache()`, `_save_api_cache()`

2. **Use CacheManager for all cached entities**
   ```python
   from services.cache_manager import get_cache
   cache = get_cache()
   
   # Instead of:
   if group_id in self._cache:
       return self._cache[group_id]
   
   # Use:
   return cache.get("group", group_id)
   ```

3. **Update all get_cached_* methods**
   - Use `cache.get()` and `cache.set()`
   - Leverage TTL configuration in CacheManager

4. **Configure TTLs appropriately**
   - Groups: 1 hour
   - Users: 5 minutes
   - Instances: 1 minute
   - Join requests: 2 minutes
   - Bans: 5 minutes

### Implementation Steps

1. **Audit current cache usage** (30 min)
   - List all places `self._cache` is used
   - Document expected TTLs

2. **Update VRChatAPI.__init__** (15 min)
   - Remove cache initialization
   - Get CacheManager instance

3. **Update get_cached_* methods** (2 hours)
   - Convert each method to use CacheManager
   - Test individually

4. **Update invalidate_* methods** (30 min)
   - Use `cache.invalidate()` instead of dict deletion

5. **Remove old cache code** (15 min)
   - Delete _cache, _cache_file, _load_api_cache, _save_api_cache

6. **Testing** (1 hour)
   - Test cache persistence across restarts
   - Test TTL expiration
   - Test invalidation

### Dependencies
- Consider doing after "Split API Client" for easier refactoring

### Risks
- Cached data format might differ
- TTL behavior changes could affect UX
- Need to handle migration of existing cached data

---

## 3. Create SearchableListMixin

**Priority:** 🟢 Low  
**Estimated Effort:** 2-3 hours  
**Risk Level:** Low (additive change)

### Current State
Multiple views have similar search/filter patterns:
- `members.py`: `_apply_filter()` + `_handle_search()`
- `bans.py`: `_apply_filter()` + `_handle_search()`
- `watchlist.py`: Search + tag filtering

### Proposed Mixin
```python
# src/ui/mixins/searchable_list.py

class SearchableListMixin:
    """Mixin providing search/filter functionality for list views"""
    
    def __init__(self):
        self._search_query = ""
        self._all_items = []
        self._filtered_items = []
        self._search_field = None
        
    def _setup_search(self, placeholder="Search...", debounce_ms=300):
        """Create and return a search field widget"""
        ...
    
    def _apply_filter(self, items, query):
        """Override in subclass to customize filtering logic"""
        ...
    
    def _handle_search(self, query):
        """Handle search input and trigger filter"""
        ...
    
    def _refresh_list(self):
        """Re-render the filtered list"""
        ...
```

### Implementation Steps

1. **Create mixin file** (30 min)
   - Implement `SearchableListMixin` class
   - Add search debouncing

2. **Test with MembersView** (45 min)
   - Refactor MembersView to use mixin
   - Verify functionality

3. **Apply to BansView** (30 min)
   - Refactor BansView

4. **Apply to WatchlistView** (45 min)
   - Refactor WatchlistView (more complex due to tag filtering)

5. **Testing** (30 min)
   - Test all three views
   - Test edge cases (empty results, special characters)

### Dependencies
- None

---

## 4. Convert Remaining Print Statements in main.py

**Priority:** 🟢 Low  
**Estimated Effort:** 1 hour  
**Risk Level:** Very Low

### Current State
`main.py` has ~35 `print()` statements used for debugging/logging.

### Categories

| Category | Count | Action |
|----------|-------|--------|
| Session/Login flow | 12 | Convert to `logger.info/debug` |
| Group loading | 8 | Convert to `logger.info/debug` |
| Navigation | 5 | Convert to `logger.debug` |
| Service init | 5 | Convert to `logger.info` |
| Errors | 5 | Convert to `logger.error` |

### Implementation Steps

1. **Ensure logger is imported** (already done in main.py)

2. **Convert by category**
   - Session flow → `logger.debug` (sensitive info)
   - Group loading → `logger.info` 
   - Navigation → `logger.debug`
   - Service init → `logger.info`
   - Errors → `logger.error`

3. **Test** (15 min)
   - Verify log output
   - Check log file rotation

### Dependencies
- None

---

## 5. Refactor Dialog Patterns to Use ConfirmDialog

**Priority:** 🟡 Medium  
**Estimated Effort:** 2 hours  
**Risk Level:** Low

### Current State
Created `src/ui/dialogs/confirm_dialog.py` but views still use handcrafted dialogs.

### Dialogs to Refactor

| Location | Dialog | Complexity |
|----------|--------|-----------|
| `requests.py` | `_show_ban_dialog()` | Simple |
| `bans.py` | `_show_unban_confirm()` | Simple |
| `instances.py` | `_show_close_confirmation()` | Medium (has details) |
| `watchlist.py` | `_confirm_remove()` | Simple |

### Implementation Steps

1. **Refactor requests.py** (20 min)
   - Replace `_show_ban_dialog()` with `show_confirm_dialog()`

2. **Refactor bans.py** (20 min)
   - Replace `_show_unban_confirm()` with `show_confirm_dialog()`

3. **Refactor instances.py** (30 min)
   - Replace `_show_close_confirmation()` - needs `details_content` parameter

4. **Refactor watchlist.py** (20 min)
   - Replace `_confirm_remove()` with `show_confirm_dialog()`

5. **Testing** (30 min)
   - Test all dialog flows
   - Verify callbacks work correctly

### Dependencies
- None (ConfirmDialog already created)

---

## Priority Matrix

| Task | Impact | Effort | Priority |
|------|--------|--------|----------|
| Refactor Dialogs to ConfirmDialog | Medium | Low | 🟡 Do Next |
| Convert Print Statements | Low | Low | 🟢 Easy Win |
| Create SearchableListMixin | Medium | Medium | 🟢 Nice to Have |
| Split API Client | High | High | 🟡 When Time Allows |
| Migrate to CacheManager | Medium | High | 🟢 Future Sprint |

---

## Recommended Execution Order

1. **Refactor Dialogs** - Uses already-created component
2. **Convert Print Statements** - Quick cleanup
3. **Create SearchableListMixin** - Reduces future duplication
4. **Split API Client** - Major refactor, do when stable
5. **Migrate to CacheManager** - Do after API Client split

---

## Tracking

- [x] Refactor Dialog Patterns ✅ (2025-12-26)
- [x] Convert Print Statements ✅ (2025-12-26)  
- [x] Create SearchableListMixin ✅ (2025-12-26)
- [x] Split API Client ✅ (2025-12-27)
- [x] Migrate to CacheManager ✅ (2025-12-27)

## Session Summary (2025-12-27) - API Client Refactor

### Completed
1. **Split API Client into Modular Mixins**
   - Created `src/api/base.py` - BaseAPI with shared state, HTTP client management
   - Created `src/api/request_handler.py` - RequestMixin with VRCX-style rate limiting
   - Created `src/api/auth.py` - AuthMixin for login, 2FA, session management
   - Created `src/api/images.py` - ImagesMixin for image caching
   - Created `src/api/users.py` - UsersMixin for user operations
   - Created `src/api/groups.py` - GroupsMixin for group operations
   - Created `src/api/invites.py` - InvitesMixin for invite/notification operations
   - Created `src/api/worlds.py` - WorldsMixin for world operations
   - Created `src/api/cache.py` - CacheMixin for cached fetch methods

2. **Migrated to Centralized CacheManager**
   - Removed old `self._cache` dict from VRChatAPI
   - Removed `_load_api_cache()` and `_save_api_cache()` methods
   - Updated `get_my_groups()` to use CacheManager for caching
   - All cached fetch methods now use the centralized CacheManager
   - Added `invalidate_my_groups_cache()` method

3. **New API Structure**
   ```
   src/api/
   ├── __init__.py          # Package exports (VRChatAPI, MockVRChatAPI)
   ├── client.py            # Main VRChatAPI composed from mixins (~75 lines)
   ├── base.py              # BaseAPI: HTTP client, cookies, shared state
   ├── request_handler.py   # RequestMixin: rate limiting, deduplication
   ├── auth.py              # AuthMixin: login, 2FA, session, location
   ├── images.py            # ImagesMixin: image download/caching
   ├── users.py             # UsersMixin: get_user, friends, search
   ├── groups.py            # GroupsMixin: groups, members, bans, instances
   ├── invites.py           # InvitesMixin: invites, self-invite, alerts
   ├── worlds.py            # WorldsMixin: worlds, search, create instance
   ├── cache.py             # CacheMixin: cached fetch + invalidation
   └── mock_client.py       # MockVRChatAPI (unchanged)
   ```

4. **Benefits**
   - Total: 10 modules, ~88KB vs 1 file at 78KB
   - Each module is focused on a single domain
   - Easy to test and maintain
   - No breaking changes - VRChatAPI interface unchanged
   - main.py imports work exactly as before

5. **Testing**
   - Verified all 28+ expected methods exist on VRChatAPI
   - Application starts and connects to VRChat API successfully
   - WebSocket pipeline connects properly

---

## Session Summary (2025-12-26)

### Completed
1. **Refactored Dialogs to ConfirmDialog**
   - `requests.py` - `_show_ban_dialog()` now uses `show_confirm_dialog()`
   - `bans.py` - `_show_unban_confirm()` now uses `show_confirm_dialog()`
   - `instances.py` - `_show_close_confirmation()` now uses `show_confirm_dialog()` with `details_content`

2. **Converted Print Statements in main.py**
   - Converted ~25 `print()` statements to proper `logger.*` calls
   - Also fixed a print statement in `login.py`

3. **Created SearchableListMixin**
   - Created `src/ui/mixins/searchable_list.py`
   - Created `src/ui/mixins/__init__.py`
   - Applied mixin to `MembersView` (refactored to use mixin)
   - Applied mixin to `BansView` (refactored to use mixin)
   - Applied mixin to `WatchlistView` (refactored to use mixin, added custom filter logic)

4. **Fixed ADI Navigation**
   - Fixed `debug_controller.py` to call `page.update()` after `page.go()`

5. **Added Keys for ADI Testing**
   - Added keys to buttons in `requests.py` and `bans.py` for ADI testing

