# API Optimization Implementation Summary

## Overview

This document summarizes the VRCX-style API data loading optimizations implemented in Group Guardian to reduce API rate limiting, quicken loading times, and improve overall efficiency.

## Key Components

### 1. Centralized Cache Manager (`services/cache_manager.py`)

A new centralized in-memory caching system inspired by VRCX's store architecture:

#### Cache Classes:
- **`EntityCache[T]`** - Generic cache for any entity type with:
  - TTL-based expiration (configurable per cache)
  - LRU eviction when max entries exceeded
  - Optional merge function for updating cached data
  
- **`CacheManager`** - Global singleton managing all entity caches:
  - `users` - User profiles (5 min TTL)
  - `groups` - Group details (10 min TTL)
  - `instances` - Group instances (1 min TTL - dynamic data)
  - `worlds` - World details (1 hour TTL - rarely changes)
  - `group_members` - Member lists (2 min TTL)
  - `join_requests` - Join requests (1 min TTL)
  - `group_bans` - Ban lists (2 min TTL)

### 2. Cached Getter Methods (`api/client.py`)

New VRCX-style cached getter methods added to `VRChatAPI`:

| Method | Description |
|--------|-------------|
| `get_cached_user()` | Returns cached user or fetches from API |
| `get_cached_group()` | Returns cached group or fetches from API |
| `get_cached_group_instances()` | Returns cached instances (1 min TTL) |
| `get_cached_join_requests()` | Returns cached join requests |
| `get_cached_group_bans()` | Returns cached ban list |
| `get_cached_group_members()` | Returns cached member list |
| `get_cached_world()` | Returns cached world (1 hour TTL) |

### 3. Cache Invalidation Methods

Methods to invalidate cached data after mutations:

| Method | Use Case |
|--------|----------|
| `invalidate_join_requests_cache()` | After accepting/rejecting requests |
| `invalidate_bans_cache()` | After banning/unbanning users |
| `invalidate_members_cache()` | After member changes |
| `invalidate_instances_cache()` | After creating/closing instances |
| `invalidate_group_cache()` | Invalidates all caches for a group |
| `clear_all_caches()` | On logout |

## Views Updated

### Dashboard (`views/dashboard.py`)
- Uses `get_cached_group_instances()`, `get_cached_join_requests()`, `get_cached_group_bans()`

### Requests (`views/requests.py`)
- Uses `get_cached_join_requests()`
- Invalidates cache after accepting/rejecting/banning

### Bans (`views/bans.py`)
- Uses `get_cached_group_bans()`
- Invalidates cache after ban/unban operations

### Instances (`views/instances.py`)
- Uses `get_cached_group_instances()` and `get_cached_group_members()`
- Invalidates cache after creating/closing instances

### Members (`views/members.py`)
- Uses `get_cached_group_members()` and `get_cached_user()`
- Invalidates cache after banning members

## Benefits

1. **Reduced API Calls** - Repeated requests within TTL window are served from cache
2. **Faster UI** - Cached data loads instantly
3. **Rate Limit Protection** - Fewer API calls = less 429 errors
4. **Consistent Data** - Invalidation ensures fresh data after mutations
5. **Memory Efficient** - LRU eviction prevents unbounded growth
