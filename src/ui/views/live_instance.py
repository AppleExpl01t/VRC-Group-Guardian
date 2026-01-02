"""
Live Instance View
==================
Real-time monitoring of the current VRChat instance via local log files.
Features local watchlist management and note-taking.
"""

import asyncio
import logging
from datetime import datetime
import flet as ft
from ..theme import colors, radius, spacing, typography
from ..components.glass_card import GlassCard, GlassPanel
from ..components.neon_button import NeonButton
from ..components.user_card import UserCard
from services.log_watcher import get_log_watcher
from services.database import get_database
from services.watchlist_service import get_watchlist_service
from services.notification_service import get_notification_service

logger = logging.getLogger(__name__)

class LiveInstanceView(ft.Container):
    """
    Live view showing current instance players and events with Watchlist integration.
    """
    
    def __init__(self, api=None, on_navigate=None, **kwargs):
        self.api = api # Optional API access for fetching user details
        self.on_navigate = on_navigate
        self._watcher = get_log_watcher(self._handle_log_event)
        self._db = get_database()
        
        # State
        self._players = {} # user_id -> displayName
        self._avatars = {} # user_id -> avatar_name
        self._joins = [] # List of strings/controls
        self._leaves = [] # List of strings/controls
        self._watchlist_cache = {} # user_id -> dict
        
        self._current_world = "Unknown World"
        self._current_instance = "NotInInstance"
        
        # UI Refs
        self._player_list = None
        self._join_list = None
        self._leave_list = None
        self._header_text = None
        self._header_subtext = None
        self._invite_progress_container = None
        self._is_inviting = False # Flag for cancellation
        
        content = self._build_view()
        
        super().__init__(
            content=content,
            expand=True,
            padding=spacing.lg,
            **kwargs,
        )

    def did_mount(self):
        """Start watcher when view mounts"""
        if not self._watcher.running:
            self._watcher.start()
        
        self._refresh_watchlist_cache()
            
        # Hydrate initial state from watcher (if it was already running)
        self._players = self._watcher.active_players.copy()
        
        # Hydrate avatars if available on watcher
        if hasattr(self._watcher, 'player_avatars'):
            self._avatars = self._watcher.player_avatars.copy()
        
        self._current_world = self._watcher.current_world_id or "Unknown World"
        self._current_instance = self._watcher.current_instance_id or "No Instance"
        
        self._update_player_list()
        self._update_header()

    def _refresh_watchlist_cache(self):
        """Load active user metadata from centralized watchlist service"""
        watchlist_svc = get_watchlist_service()
        watchlist_svc.refresh_cache()
        
        # Also cache active users' data for quick local reference
        active = self._db.get_active_users()
        for u in active:
            uid = u["user_id"]
            if u.get("note") or u.get("is_watchlisted"):
                self._watchlist_cache[uid] = {
                    "note": u.get("note"),
                    "is_watchlisted": u.get("is_watchlisted"),
                }

    def _handle_log_event(self, event):
        """Handle event from LogWatcher"""
        evt_type = event.get("type")
        ts = datetime.now().strftime("%H:%M:%S")
        notif_service = get_notification_service()
        
        if evt_type == "player_join":
            uid = event["user_id"]
            name = event["display_name"]
            self._players[uid] = name
            
            # Check watchlist using centralized service - ensures user is recorded
            watchlist_svc = get_watchlist_service()
            status = watchlist_svc.check_and_record_user(uid, name)
            self._watchlist_cache[uid] = status
            
            if status.get("is_watchlisted"):
                self._add_watchlist_event(f"WATCHLIST: {name} joined", colors.accent_primary, ts)
                # Play watchlist alert sound (higher priority)
                notif_service.notify_watchlist_alert(name)
            else:
                # Play regular player join sound
                notif_service.notify_player_join(name)
            
            self._add_join(name, ts)
            self._update_player_list()
            
        elif evt_type == "player_leave":
            uid = event["user_id"]
            name = event.get("display_name") or event.get("name") or "Unknown"
            
            if uid in self._players:
                del self._players[uid]
            if uid in self._avatars:
                del self._avatars[uid]
            
            # Play player leave sound
            notif_service.notify_player_leave(name)
            
            self._add_leave(name, ts)
            self._update_player_list()
        
        elif evt_type == "player_avatar_change":
            uid = event["user_id"]
            avatar = event["avatar_name"]
            self._avatars[uid] = avatar
            self._update_player_list()
            
        elif evt_type == "instance_change":
            self._players.clear()
            self._avatars.clear()
            self._joins.clear()
            self._leaves.clear()
            self._current_world = event.get("world_id", "Unknown")
            self._current_instance = event.get("instance_id", "Unknown")
            
            self._add_watchlist_event(f"Joined {self._current_world}", colors.success, ts)
            self._update_player_list()
            self._update_header()

        elif evt_type == "rotation":
             # Trigger refresh or clear
             self.did_mount()

        elif evt_type == "disconnected":
            self._players.clear()
            self._avatars.clear()
            self._current_instance = "Disconnected"
            self._add_watchlist_event("Disconnected", colors.warning, ts)
            self._update_player_list()
            self._update_header()

    def _add_join(self, name: str, ts: str):
        """Add to join list"""
        entry = self._create_log_row(name, "Joined", colors.success, ts)
        self._joins.insert(0, entry)
        if len(self._joins) > 20: self._joins.pop()
        if self._join_list:
            self._join_list.controls = self._joins[:]
            self._join_list.update()

    def _add_leave(self, name: str, ts: str):
        """Add to leave list"""
        entry = self._create_log_row(name, "Left", colors.danger, ts)
        self._leaves.insert(0, entry)
        if len(self._leaves) > 20: self._leaves.pop()
        if self._leave_list:
            self._leave_list.controls = self._leaves[:]
            self._leave_list.update()
            
    def _add_watchlist_event(self, msg: str, color: str, ts: str):
        """Add critical event to the join log with highlighting"""
        entry = ft.Container(
            content=ft.Row([
                ft.Text(ts, size=10, color=colors.text_tertiary),
                ft.Icon(ft.Icons.WARNING_ROUNDED, size=12, color=color),
                ft.Text(msg, weight=ft.FontWeight.BOLD, color=color, expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
            ], spacing=spacing.xs),
            padding=ft.padding.all(4),
            bgcolor=colors.with_opacity(color, 0.1),
            border_radius=radius.sm,
            border=ft.border.left(2, color)
        )
        # Add to joins list so it's visible in the main log stream
        self._joins.insert(0, entry)
        if len(self._joins) > 50: self._joins.pop()
        if self._join_list:
            self._join_list.controls = self._joins[:]
            self._join_list.update()

    def _update_player_list(self):
        """Rebuild player list UI using Unified UserCard"""
        if not self._player_list:
            return
            
        items = []
        for uid, name in self._players.items():
            # Construct ephemeral user object
            user_data = {
                "id": uid,
                "displayName": name,
            }
            
            # Check for avatar (from log watcher)
            avatar_name = self._avatars.get(uid)
            
            items.append(
                UserCard(
                    user_data=user_data,
                    api=self.api,
                    db=self._db,
                    compact=True,
                    subtitle=avatar_name if avatar_name else None,
                    on_click=lambda e, u=user_data: self._open_details(u),
                )
            )
            
        if not items:
            items.append(ft.Container(content=ft.Text("No active players", color=colors.text_secondary, italic=True), padding=10))
            
        self._player_list.controls = items
        self._player_list.update()

    def _open_details(self, user_data):
        """Open unified details dialog"""
        from ..dialogs.user_details import show_user_details_dialog
        
        # We might need to refresh the list if they update a note/watchlist legacy
        def on_update():
            # Refresh local cache from DB
            self._refresh_watchlist_cache()
            # Rebuild UI to show new icons
            self._update_player_list()
            
        show_user_details_dialog(
            self.page,
            user_data,
            self.api,
            self._db,
            on_update=on_update
        )

    def _update_header(self):
        """Update header info"""
        if self._header_text:
            self._header_text.value = f"Live Monitor"
            sub = f"{self._current_world}"
            if self._current_instance != "NotInInstance":
                sub += f" #{self._current_instance}"
            self._header_subtext.value = sub
            self._header_text.update()
            self._header_subtext.update()

    def _build_view(self) -> ft.Control:
        """Build UI layout mimicking DashboardView"""
        
        self._header_text = ft.Text(
            "Live Monitor",
            size=typography.size_xl,  # Reduced from 2xl
            weight=ft.FontWeight.W_700,
            color=colors.text_primary,
        )
        self._header_subtext = ft.Text(
            "Waiting for instance connection...",
            size=typography.size_sm,  # Reduced from base
            color=colors.text_secondary,
        )
        
        header = ft.Row(
            controls=[
                ft.Column(
                    controls=[self._header_text, self._header_subtext],
                    spacing=0,  # Reduced from xs
                ),
                ft.Row([
                    NeonButton(
                        "Invite Online Members",
                        icon=ft.Icons.GROUP_ADD_ROUNDED,
                        variant=NeonButton.VARIANT_PRIMARY,
                        on_click=lambda e: self._show_invite_all_dialog(),
                    ),
                    ft.Icon(ft.Icons.WAVES, color=colors.success, size=30, animate_opacity=300),
                ], spacing=spacing.md),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        
        # Columns
        self._player_list = ft.GridView(
            max_extent=180,
            child_aspect_ratio=0.85,
            spacing=spacing.xs,
            run_spacing=spacing.xs,
            expand=True,
            padding=spacing.xs,
        )
        self._join_list = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO)
        self._leave_list = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO)
        
        # Instance Invite Progress Container
        self._invite_progress_container = ft.Container(
            animate_opacity=300,
            animate_size=300,
        )
        
        # Main Grid Layout
        # Row 1: Active Players (Center focus)
        # Row 2: Recent Joins | Recent Leaves
        
        player_panel = GlassPanel(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.PEOPLE, color=colors.accent_secondary),
                    ft.Text("Active Players", size=typography.size_lg, weight=ft.FontWeight.W_600),
                ]),
                ft.Divider(color=colors.glass_border),
                ft.Container(content=self._player_list, expand=True)
            ]),
            expand=True,
            height=300, # Fixed height for main list
        )
        
        join_panel = GlassPanel(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.LOGIN_ROUNDED, color=colors.success, size=16),
                    ft.Text("Recent Joins", weight=ft.FontWeight.W_600),
                ]),
                ft.Divider(color=colors.glass_border),
                ft.Container(content=self._join_list, expand=True)
            ]),
            expand=True
        )
        
        leave_panel = GlassPanel(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.LOGOUT_ROUNDED, color=colors.danger, size=16),
                    ft.Text("Recent Leaves", weight=ft.FontWeight.W_600),
                ]),
                ft.Divider(color=colors.glass_border),
                ft.Container(content=self._leave_list, expand=True)
            ]),
            expand=True
        )
        
        return ft.Column(
            controls=[
                header,
                ft.Container(height=spacing.md),
                ft.Container(height=spacing.lg),
                self._invite_progress_container,
                player_panel,
                ft.Container(height=spacing.md),
                ft.Row(
                    controls=[
                        ft.Container(content=join_panel, expand=1, height=200),
                        ft.Container(content=leave_panel, expand=1, height=200),
                    ],
                    spacing=spacing.md
                )
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO
        )

    def _show_invite_all_dialog(self):
        """Show confirmation dialog before inviting all friends"""
        # Will fetch location from API when confirming
        def close_dlg(e):
            self.page.close(dlg)
            
        def confirm_invite(e):
            self.page.close(dlg)
            self.page.run_task(self._do_invite_all_friends)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.GROUP_ADD_ROUNDED, color=colors.accent_primary, size=28),
                ft.Container(width=spacing.sm),
                ft.Text("Invite All Online Friends?", weight=ft.FontWeight.W_600),
            ]),
            content=ft.Column([
                ft.Text(
                    "This will fetch your current location and invite all ONLINE friends to your instance.",
                    color=colors.text_secondary,
                ),
                ft.Container(height=spacing.sm),
                ft.Text(
                    "📍 Your current location will be fetched from the VRChat API.",
                    color=colors.text_tertiary,
                    size=typography.size_sm,
                ),
                ft.Container(height=spacing.sm),
                ft.Text(
                    "⚠️ Only friends who are online (not offline) will be invited.",
                    color=colors.warning,
                    size=typography.size_sm,
                ),
            ], tight=True, width=400),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                NeonButton(
                    text="Invite Online Friends",
                    icon=ft.Icons.SEND_ROUNDED,
                    variant=NeonButton.VARIANT_PRIMARY,
                    on_click=confirm_invite,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=colors.bg_elevated,
            shape=ft.RoundedRectangleBorder(radius=radius.lg),
        )
        self.page.open(dlg)

    async def _do_invite_all_friends(self):
        """Execute the invite all friends operation with UI progress"""
        if not self.api:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("API not available"), bgcolor=colors.danger)
            self.page.snack_bar.open = True
            self.page.update()
            return
            
        if self._is_inviting:
            return

        self._is_inviting = True
        
        # UI Elements
        progress_bar = ft.ProgressBar(value=0, color=colors.accent_primary, bgcolor=colors.bg_glass)
        status_text = ft.Text("Initializing...", color=colors.text_secondary, size=typography.size_sm)
        log_col = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        log_container = ft.Container(
            content=log_col,
            height=150,
            bgcolor=colors.bg_glass,
            border_radius=radius.md,
            padding=spacing.xs,
            border=ft.border.all(2, colors.glass_border)
        )
        
        cancel_btn = NeonButton("Cancel", variant="danger", height=36)
        
        def handle_cancel(e=None):
            self._is_inviting = False
            status_text.value = "Cancelling..."
            cancel_btn.set_disabled(True)
            cancel_btn.update()
            status_text.update()
            
        def close_card(e=None):
            self._invite_progress_container.content = None
            self._invite_progress_container.padding = 0
            self._invite_progress_container.update()

        cancel_btn.on_click = handle_cancel

        # Build Card
        card = GlassCard(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.SEND_ROUNDED, color=colors.accent_primary),
                    ft.Text(
                        "Inviting Online Friends", 
                        size=typography.size_lg, 
                        weight=ft.FontWeight.W_600,
                        expand=True,
                        no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS
                    ),
                    cancel_btn
                ], spacing=spacing.md, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(height=spacing.xs),
                progress_bar,
                status_text,
                ft.Container(height=spacing.xs),
                ft.Text("Invite Log:", weight=ft.FontWeight.W_500),
                log_container,
            ]),
            padding=spacing.lg
        )
        
        self._invite_progress_container.content = card
        self._invite_progress_container.padding = ft.padding.only(bottom=spacing.md)
        self._invite_progress_container.update()
        
        try:
            logger.debug("Starting invite process...")
            # 1. Get Location
            status_text.value = "Fetching current location..."
            progress_bar.type = ft.ProgressRing
            status_text.update()
            
            location = await self.api.get_my_location()
            logger.debug(f"Location result: {location}")
            
            if not self._is_inviting: return # Check cancel
            
            if not location:
                # Fallback to log watcher
                if self._watcher.current_world_id and self._watcher.current_instance_id:
                    location = {
                        "world_id": self._watcher.current_world_id,
                        "instance_id": self._watcher.current_instance_id,
                    }
                    logger.debug(f"Using fallback location from watcher: {location}")
                else:
                    logger.debug("Could not determine location.")
                    status_text.value = "Error: Could not determine location (must be in an instance)."
                    status_text.color = colors.danger
                    cancel_btn.text = "Close"
                    cancel_btn.on_click = close_card
                    cancel_btn.set_disabled(False)
                    cancel_btn.variant = "secondary"
                    self._invite_progress_container.update()
                    self._is_inviting = False
                    return

            world_id = location["world_id"]
            instance_id = location["instance_id"]
            
            # Fetch world name for invite payload (VRCX style)
            world_name = None
            try:
                world_info = await self.api.get_world(world_id)
                if world_info:
                    world_name = world_info.get("name")
                    logger.debug(f"Fetched world name: {world_name}")
            except Exception as e:
                logger.debug(f"Failed to fetch world info: {e}")
                pass

            # 2. Get Members to Invite
            group_id = getattr(self._watcher, 'current_group_id', None)
            logger.debug(f"Current group ID from watcher: {group_id}")
            
            if group_id:
                status_text.value = f"Fetching online members for group {group_id}..."
                status_text.update()
                logger.debug(f"Calling get_group_online_members for {group_id}")
                members_to_invite = await self.api.get_group_online_members(group_id)
                target_type = "members"
            else:
                status_text.value = f"No active group detected. Fetching online friends..."
                status_text.update()
                logger.debug("Calling get_all_friends")
                friends = await self.api.get_all_friends()
                members_to_invite = [f for f in friends if f.get("location") != "offline"]
                target_type = "friends"
            
            logger.debug(f"Found {len(members_to_invite) if members_to_invite else 0} online {target_type} to invite")

            if not self._is_inviting: return

            if not members_to_invite:
                status_text.value = f"No online {target_type} found to invite."
                logger.debug("No members to invite. Aborting.")
                cancel_btn.text = "Close"
                cancel_btn.on_click = close_card
                cancel_btn.set_disabled(False)
                status_text.update()
                cancel_btn.update()
                self._is_inviting = False
                return

            total = len(members_to_invite)
            status_text.value = f"Starting invites for {total} online {target_type}..."
            status_text.update()
            
            # 3. Iterate
            success_count = 0
            
            for i, member in enumerate(members_to_invite):
                if not self._is_inviting:
                    logger.debug("Invite process cancelled by user.")
                    break
                    
                member_id = member.get("id") 
                member_name = member.get("displayName", "Unknown")
                
                logger.debug(f"Inviting {member_name} ({member_id})...")
                
                # Log Item
                try:
                    # invite_to_instance works for both friends and group members (using user_id)
                    result = await self.api.invite_to_instance(
                        member_id, 
                        world_id, 
                        instance_id,
                        world_name=world_name
                    )
                    is_success = bool(result)
                    logger.debug(f"Invite result for {member_name}: {'Success' if is_success else 'Failed'}")
                except Exception as e:
                    logger.debug(f"Invite error for {member_name}: {e}")
                    is_success = False

                if is_success:
                    success_count += 1
                    icon = ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=colors.success, size=16)
                    status_str = "Sent"
                else:
                    icon = ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, color=colors.danger, size=16)
                    status_str = "Failed"

                # Add to log (at top)
                log_row = ft.Row([
                    ft.Text(f"{datetime.now().strftime('%H:%M:%S')}", size=10, color=colors.text_tertiary),
                    icon,
                    ft.Text(member_name, expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(status_str, size=12, color=colors.text_secondary)
                ], spacing=spacing.xs)
                
                log_col.controls.insert(0, log_row)
                if len(log_col.controls) > 50: log_col.controls.pop()
                log_col.update()
                
                # Update Progress
                progress = (i + 1) / total
                progress_bar.value = progress
                status_text.value = f"Inviting... {i+1}/{total} ({success_count} sent)"
                progress_bar.update()
                status_text.update()
                
                # Rate limit
                if i < total - 1:
                    await asyncio.sleep(1.5)
            
            # Done
            if self._is_inviting:
                self._show_invite_summary("Invites Sent Successfully", success_count, is_error=False)
                logger.info(f"Invite process completed. Sent: {success_count}/{total}")
            else:
                self._show_invite_summary("Invite Process Cancelled", success_count, is_error=True)
                
        except Exception as e:
            logger.error(f"Critical invite error: {e}")
            self._show_invite_summary(f"Error: {str(e)[:50]}", success_count if 'success_count' in locals() else 0, is_error=True)
            
        finally:
            self._is_inviting = False

    def _show_invite_summary(self, status: str, count: int, is_error: bool = False):
        """Show a small summary card after invite process finishes"""
        
        def close_summary(e):
            self._invite_progress_container.content = None
            self._invite_progress_container.padding = 0
            self._invite_progress_container.update()

        icon = ft.Icons.CHECK_CIRCLE_ROUNDED if not is_error else ft.Icons.WARNING_ROUNDED
        color = colors.success if not is_error else colors.warning
        
        summary_card = GlassCard(
            content=ft.Row([
                ft.Icon(icon, color=color, size=24),
                ft.Column([
                    ft.Text(status, weight=ft.FontWeight.W_600, color=colors.text_primary),
                    ft.Text(f"Invites sent: {count}", size=typography.size_sm, color=colors.text_secondary),
                ], spacing=2, expand=True),
                ft.IconButton(
                    icon=ft.Icons.CLOSE_ROUNDED,
                    icon_color=colors.text_secondary,
                    tooltip="Dismiss",
                    on_click=close_summary
                )
            ], alignment=ft.MainAxisAlignment.START),
            padding=spacing.md,
            height=80, # Fixed smaller height
        )
        
        self._invite_progress_container.content = summary_card
        self._invite_progress_container.padding = ft.padding.only(bottom=spacing.md)
        self._invite_progress_container.update()
