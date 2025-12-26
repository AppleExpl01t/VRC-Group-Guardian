# Dashboard & Menu Implementation Plan

## Phase 1: API Client Expansion
The `src/api/client.py` needs methods to fetch data required for the dashboard and menus.
- [ ] `get_group_instances(group_id)` - Fetch active instances.
- [ ] `get_group_join_requests(group_id)` - Fetch pending join requests.
- [ ] `get_group_audit_logs(group_id)` - Fetch recent activity.
- [ ] `get_group_bans(group_id)` - Fetch banned users.
- [ ] `get_group_members(group_id)` - Fetch/search members.

## Phase 2: Dashboard View (`/dashboard`)
Update `src/ui/views/dashboard.py` to use real data.
- [ ] Pass `current_group` to `DashboardView`.
- [ ] Implement `load_data()` method to fetch instances, requests, and logs.
- [ ] Wire up "Refresh" button.
- [ ] Replace dummy stats with real counts.
- [ ] Connect "View All" buttons to navigation.

## Phase 3: Menu Views
Create new views for sidebar navigation items.

### 3.1 Instances View (`/instances`)
- [ ] Create `src/ui/views/instances.py`.
- [ ] List active group instances with details (Region, Member count).
- [ ] Implement "Close Instance" functionality (warns user).

### 3.2 Join Requests View (`/requests`)
- [ ] Create `src/ui/views/requests.py`.
- [ ] List pending requests with user bio, avatar, and tags.
- [ ] Implement "Accept" and "Reject" actions.
- [ ] Implement "Auto-Screening" visual indicators (e.g. matched keywords).

### 3.3 Members View (`/members`)
- [ ] Create `src/ui/views/members.py`.
- [ ] Searchable member list.
- [ ] Role management (Assign/Revoke roles).
- [ ] Kick/Ban dialogs.

### 3.4 Bans View (`/bans`)
- [ ] Create `src/ui/views/bans.py`.
- [ ] List banned users.
- [ ] Unban functionality.
- [ ] Add new ban dialog.

### 3.5 Logs View (`/logs`)
- [ ] Create `src/ui/views/logs.py`.
- [ ] Display audit logs with filtering by type key.

### 3.6 Settings View (`/settings`)
- [ ] Create `src/ui/views/settings.py`.
- [ ] Configure automation intervals.
- [ ] Manage local blacklists (keywords, groups).
- [ ] Save/Load configuration to `config.json`.
