"""
Dashboard View
==============
Main dashboard with stats, instances, and activity
"""

import flet as ft
from ..theme import colors, radius, spacing, typography
from ..components.glass_card import GlassCard, GlassPanel
from ..components.stat_card import StatCard
from ..components.status_badge import StatusBadge
from ..components.neon_button import NeonButton, IconButton
from services.database import get_database
from services.watchlist_service import get_watchlist_service


class DashboardView(ft.Container):
    """
    Main dashboard view with:
    - Stats overview cards
    - Active instances panel
    - Pending requests preview
    - Activity timeline
    """
    
    def __init__(self, group=None, api=None, on_navigate=None, on_update_stats=None, **kwargs):
        self.group = group
        self.api = api
        self.on_navigate = on_navigate
        self.on_update_stats = on_update_stats
        self.db = get_database()
        
        # State
        self._instances = []
        self._requests = []
        self._logs = []
        self._bans = []
        self._automod_logs = []
        self._base_stats = {"active_instances": 0, "pending_requests": 0, "bans_today": 0}
        self._is_mobile = kwargs.pop("is_mobile", False)
        
        # UI References
        self._stats_row = None
        self._instances_panel = None
        self._activity_panel = None
        self._automod_column = None
        
        content = self._build_view()
        
        super().__init__(
            content=content,
            expand=True,
            padding=spacing.lg,
            **kwargs,
        )

    def did_mount(self):
        """Load data when view is mounted"""
        if self.api and self.group:
            self.page.run_task(self._load_data)

    async def _load_data(self):
        """Fetch dashboard data"""
        if not self.api or not self.group:
            return
            
        group_id = self.group.get("id")
        
        # Fetch all data concurrently (using cached getters for efficiency)
        import asyncio
        results = await asyncio.gather(
            self.api.get_cached_group_instances(group_id),
            self.api.get_cached_join_requests(group_id),
            self.api.get_group_audit_logs(group_id, n=10),  # Logs don't need caching (always fresh)
            self.api.get_cached_group_bans(group_id),
        )
        
        self._instances = results[0] or []
        self._requests = results[1] or []
        self._logs = results[2] or []
        self._bans = results[3] or []
        
        # Fetch automod logs from local database
        self._automod_logs = self.db.get_automod_logs(group_id, limit=8) or []
        
        # Update Stats
        # Calculate bans today (naively check if created_at is today, tricky with string dates)
        # For now, just show total or mocked 'today' delta
        
        
        self._base_stats["active_instances"] = len(self._instances)
        self._base_stats["pending_requests"] = len(self._requests)
        self._base_stats["bans_today"] = 0 # Todo: parse logs for bans today
        
        # Notify parent app
        if self.on_update_stats:
            self.on_update_stats(self._base_stats)
        
        # Update UI
        self._update_ui()
        
    def _update_ui(self):
        """Update UI elements with new data"""
        if self._stats_row:
            self._stats_row.controls = self._build_stats_controls()
            self._stats_row.update()
            
        if self._instances_column:
            # Rebuild instance rows
            self._instances_column.controls = self._build_instance_rows()
            self._instances_column.update()
            
        if self._activity_column:
            self._activity_column.controls = self._build_activity_rows()
            self._activity_column.update()
        
        if self._automod_column:
            self._automod_column.controls = self._build_automod_rows()
            self._automod_column.update()

    def _build_stats_controls(self):
        return [
            StatCard(
                icon=ft.Icons.PUBLIC_ROUNDED,
                value=str(self._base_stats["active_instances"]),
                label="Active Instances",
                subtitle="Live status",
                icon_color=colors.accent_secondary,
                col={"xs": 12, "md": 4},
            ),
            StatCard(
                icon=ft.Icons.INBOX_ROUNDED,
                value=str(self._base_stats["pending_requests"]),
                label="Pending Requests",
                trend="neutral", # Todo
                trend_value="",
                icon_color=colors.accent_primary,
                col={"xs": 12, "md": 4},
            ),
            StatCard(
                icon=ft.Icons.BLOCK_ROUNDED,
                value=str(self._base_stats["bans_today"]),
                label="Bans Today",
                subtitle="Last 24h",
                icon_color=colors.danger,
                col={"xs": 12, "md": 4},
            ),
        ]
    
    def _build_view(self) -> ft.Control:
        """Build dashboard layout - compact version"""
        
        # Header - more compact
        header = ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text(
                            "Dashboard",
                            size=typography.size_xl,  # Reduced from 2xl
                            weight=ft.FontWeight.W_700,
                            color=colors.text_primary,
                        ),
                        ft.Text(
                            "Welcome back! Here's what's happening.",
                            size=typography.size_sm,  # Reduced from base
                            color=colors.text_secondary,
                        ),
                    ],
                    spacing=0,  # Reduced from xs
                ),
                ft.Row(
                    controls=[
                        IconButton(
                            icon=ft.Icons.REFRESH_ROUNDED,
                            tooltip="Refresh data",
                            on_click=lambda e: self.page.run_task(self._load_data),
                            key="dashboard_refresh",
                        ),
                    ],
                    spacing=spacing.xs,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        
        # Stats row - Responsive
        self._stats_row = ft.ResponsiveRow(
            controls=self._build_stats_controls(),
            spacing=spacing.sm,
        )
        
        # Active Instances panel
        instances_panel = self._build_instances_panel()
        
        # Activity timeline
        activity_panel = self._build_activity_panel()
        
        # Auto-Mod Activity panel
        automod_panel = self._build_automod_panel()
        
        # Tetris-style grid layout:
        # ┌─────────────────┬─────────────┐
        # │                 │  Activity   │
        # │   Instances     ├─────────────┤
        # │    (expand)     │  Auto-Mod   │
        # └─────────────────┴─────────────┘
        
        # Right column: Activity + AutoMod stacked
        right_column = ft.Column(
            controls=[
                ft.Container(
                    content=activity_panel,
                    expand=1,  # Take 1 part of available space
                ),
                ft.Container(
                    content=automod_panel,
                    expand=1,  # Take 1 part of available space  
                ),
            ],
            spacing=spacing.sm,
            expand=True,
        )
        
        # Main content grid - Tetris layout
        main_grid = ft.ResponsiveRow(
            controls=[
                # Left: Instances panel (larger, takes 6/12 on large screens)
                ft.Container(
                    content=instances_panel,
                    col={"xs": 12, "md": 6},
                    expand=True,
                ),
                # Right: Stacked Activity + AutoMod (takes 6/12 on large screens)
                ft.Container(
                    content=right_column,
                    col={"xs": 12, "md": 6},
                    expand=True,
                ),
            ],
            spacing=spacing.sm,
            expand=True,
        )
        
        return ft.Column(
            controls=[
                header,
                ft.Container(height=spacing.sm),
                self._stats_row,
                ft.Container(height=spacing.sm),
                ft.Container(
                    content=main_grid,
                    expand=True,  # Fill all remaining vertical space
                ),
            ],
            spacing=0,
            expand=True,
        )
    
    def _build_instances_panel(self) -> ft.Control:
        """Build active instances panel"""
        is_mobile = self._is_mobile
        
        self._instances_column = ft.Column(
            controls=self._build_instance_rows(),
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        
        return GlassPanel(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                "Active Instances",
                                size=typography.size_lg,
                                weight=ft.FontWeight.W_600,
                                color=colors.text_primary,
                            ),
                            ft.Container(expand=True),
                            ft.TextButton(
                                "View All →",
                                style=ft.ButtonStyle(color=colors.accent_primary),
                                on_click=lambda e: self.on_navigate("/instances") if self.on_navigate else None,
                                key="dashboard_view_instances",
                            ),
                        ],
                    ),
                    ft.Container(height=spacing.sm),
                    self._instances_column,
                ],
                expand=True,
            ),
            expand=True,
            enable_blur=not is_mobile,
        )
        
    def _build_instance_rows(self):
        if not self._instances:
             return [ft.Container(
                 content=ft.Text("No active instances", color=colors.text_tertiary),
                 padding=20, alignment=ft.alignment.center
             )]
             
        rows = []
        for inst in self._instances:
            world = inst.get("world", {})
            name = world.get("name", "Unknown World")
            count = inst.get("memberCount", 0)
            region = inst.get("location", "").split("~region(")[-1].split(")")[0] if "region(" in inst.get("location", "") else "US"
            
            row = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.PUBLIC_ROUNDED, size=20, color=colors.text_secondary),
                        ft.Text(name, size=typography.size_base, color=colors.text_primary, expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(f"{count} users", size=typography.size_sm, color=colors.text_secondary),
                        ft.Container(
                            content=ft.Text(region.upper(), size=10, color=colors.text_tertiary),
                            padding=ft.padding.symmetric(horizontal=4),
                            border=ft.border.all(2, colors.glass_border),
                            border_radius=4,
                        )
                    ],
                    spacing=spacing.md,
                ),
                padding=ft.padding.symmetric(vertical=spacing.sm),
                border=ft.border.only(bottom=ft.BorderSide(2, colors.glass_border)),
            )
            rows.append(row)
        return rows
    
    def _build_activity_panel(self) -> ft.Control:
        """Build activity timeline panel"""
        is_mobile = self._is_mobile
        
        self._activity_column = ft.Column(
            controls=self._build_activity_rows(),
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        
        return GlassPanel(
            content=ft.Column(
                controls=[
                    ft.Text("Activity Timeline", size=typography.size_lg, weight=ft.FontWeight.W_600, color=colors.text_primary),
                    ft.Container(height=spacing.sm),
                    self._activity_column,
                ],
                expand=True,
            ),
            expand=True,
            enable_blur=not is_mobile,
        )

    def _build_activity_rows(self):
        if not self._logs:
             return [ft.Container(content=ft.Text("No recent activity", color=colors.text_tertiary), padding=20, alignment=ft.alignment.center)]
             
        rows = []
        for log in self._logs:
            # Parse log
            event_type = log.get("type", "unknown")
            created_at = log.get("created_at", "") # VRChat usually sends timestamp format
            # Simple time formatting (slice for now)
            time_str = created_at[11:16] if len(created_at) > 16 else "" 
            
            actor = log.get("actorDisplayName", "System")
            desc = log.get("description", event_type)
            
            color = colors.accent_secondary
            if "ban" in event_type.lower(): color = colors.danger
            if "join" in event_type.lower(): color = colors.success
            
            row = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Container(width=8, height=8, border_radius=4, bgcolor=color),
                        ft.Column(
                            controls=[
                                ft.Text(time_str, size=typography.size_xs, color=colors.text_tertiary),
                                ft.Text(f"{actor}: {desc}", size=typography.size_sm, color=colors.text_secondary, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                            spacing=0,
                            expand=True,
                        ),
                    ],
                    spacing=spacing.sm,
                ),
                padding=ft.padding.symmetric(vertical=spacing.sm),
            )
            rows.append(row)
        return rows

    def _build_automod_panel(self) -> ft.Control:
        """Build auto-mod activity panel"""
        is_mobile = self._is_mobile
        
        self._automod_column = ft.Column(
            controls=self._build_automod_rows(),
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        
        return GlassPanel(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.SMART_TOY_ROUNDED, size=20, color=colors.accent_primary),
                            ft.Text(
                                "Auto-Mod Activity",
                                size=typography.size_lg,
                                weight=ft.FontWeight.W_600,
                                color=colors.text_primary,
                            ),
                            ft.Container(expand=True),
                            ft.TextButton(
                                "Settings →",
                                style=ft.ButtonStyle(color=colors.accent_primary),
                                on_click=lambda e: self.on_navigate("/settings") if self.on_navigate else None,
                                key="dashboard_automod_settings",
                            ),
                        ],
                    ),
                    ft.Container(height=spacing.sm),
                    self._automod_column,
                ],
                expand=True,
            ),
            expand=True,
            enable_blur=not is_mobile,
        )

    def _build_automod_rows(self):
        """Build rows for automod activity log"""
        if not self._automod_logs:
            return [ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.SMART_TOY_ROUNDED, size=32, color=colors.text_tertiary, opacity=0.5),
                        ft.Text("No auto-mod activity yet", color=colors.text_tertiary, size=typography.size_sm),
                        ft.Text("Auto-mod will appear here when enabled", color=colors.text_tertiary, size=typography.size_xs),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=spacing.xs,
                ),
                padding=20,
                alignment=ft.alignment.center,
                expand=True,
            )]

        from ..dialogs.user_details import show_user_details_dialog
        
        watchlist_svc = get_watchlist_service()
        rows = []
        for log in self._automod_logs:
            action = log.get("action", "unknown")
            reason = log.get("reason", "")
            user_id = log.get("user_id", "")
            username = log.get("username", "Unknown User")  # Fixed: DB uses 'username' not 'user_name'
            timestamp = log.get("timestamp", "")
            
            # Check watchlist using centralized service - ensures user is recorded
            is_watchlisted = False
            if user_id:
                status = watchlist_svc.check_and_record_user(user_id, username)
                is_watchlisted = status.get("is_watchlisted", False)
            
            # Format timestamp
            time_str = ""
            if timestamp:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    time_str = dt.strftime("%m/%d %H:%M")
                except:
                    time_str = timestamp[:16] if len(timestamp) > 16 else timestamp

            
            # Action styling
            was_accepted = action == "accept"
            if was_accepted:
                action_color = colors.success
                action_icon = ft.Icons.CHECK_CIRCLE_ROUNDED
                action_text = "Accepted"
            elif action == "reject":
                action_color = colors.danger
                action_icon = ft.Icons.CANCEL_ROUNDED
                action_text = "Rejected"
            else:
                action_color = colors.warning
                action_icon = ft.Icons.HELP_ROUNDED
                action_text = action.title() if action else "Unknown"
            
            # Create action button based on what automod did
            if was_accepted:
                # User was auto-accepted, show Kick button
                action_btn = ft.IconButton(
                    icon=ft.Icons.PERSON_REMOVE_ROUNDED,
                    icon_size=16,
                    icon_color=colors.danger,
                    tooltip="Kick from group",
                    on_click=lambda e, uid=user_id, uname=username: self._kick_user(uid, uname),
                )
            else:
                # User was auto-rejected, show Invite button
                action_btn = ft.IconButton(
                    icon=ft.Icons.PERSON_ADD_ROUNDED,
                    icon_size=16,
                    icon_color=colors.success,
                    tooltip="Send group invite",
                    on_click=lambda e, uid=user_id, uname=username: self._invite_user(uid, uname),
                )
            
            # Clickable user info section
            user_section = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(action_icon, size=18, color=action_color),
                        ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        # Watchlist indicator
                                        ft.Icon(
                                            ft.Icons.WARNING_ROUNDED,
                                            size=14,
                                            color=colors.warning,
                                            tooltip="User is on watchlist",
                                        ) if is_watchlisted else ft.Container(width=0),
                                        ft.Text(
                                            username,
                                            size=typography.size_sm,
                                            color=colors.warning if is_watchlisted else colors.accent_primary,
                                            weight=ft.FontWeight.W_600 if is_watchlisted else ft.FontWeight.W_500,
                                        ),
                                        ft.Container(
                                            content=ft.Text(
                                                action_text,
                                                size=typography.size_xs,
                                                color=action_color,
                                            ),
                                            padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                            bgcolor=f"{action_color}20",
                                            border_radius=radius.sm,
                                        ),
                                    ],
                                    spacing=spacing.xs,
                                ),
                                ft.Text(
                                    reason or "No reason specified",
                                    size=typography.size_xs,
                                    color=colors.text_tertiary,
                                    no_wrap=True,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    spacing=spacing.sm,
                    expand=True,
                ),
                expand=True,
                on_click=lambda e, uid=user_id, uname=username: self._open_user_profile(uid, uname),
                on_hover=lambda e: self._on_row_hover(e),
                tooltip=f"Click to view {username}'s profile",
                animate_scale=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            )
            
            row = ft.Container(
                content=ft.Row(
                    controls=[
                        user_section,
                        ft.Text(
                            time_str,
                            size=typography.size_xs,
                            color=colors.text_tertiary,
                        ),
                        action_btn,
                    ],
                    spacing=spacing.xs,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.padding.symmetric(vertical=spacing.xs, horizontal=spacing.xs),
                border=ft.border.only(bottom=ft.BorderSide(1, colors.glass_border)),
            )
            rows.append(row)
        
        return rows
    
    def _open_user_profile(self, user_id: str, username: str):
        """Open user profile dialog for a user from the automod logs"""
        if not user_id:
            self.page.open(ft.SnackBar(
                content=ft.Text("User ID not available"),
                bgcolor=colors.warning
            ))
            return
        
        from ..dialogs.user_details import show_user_details_dialog
        
        # Construct minimal user data for the dialog
        user_data = {
            "id": user_id,
            "displayName": username,
        }
        
        group_id = self.group.get("id") if self.group else None
        
        # Show user details dialog
        show_user_details_dialog(
            self.page,
            user_data,
            self.api,
            self.db,
            group_id=group_id
        )
    
    def _on_row_hover(self, e):
        """Handle hover on automod row - scale effect"""
        if e.data == "true":
            e.control.scale = 1.02
        else:
            e.control.scale = 1.0
        e.control.update()
    
    def _invite_user(self, user_id: str, username: str):
        """Send a group invite to a user who was auto-rejected"""
        if not self.api:
            self.page.open(ft.SnackBar(
                content=ft.Text("API not available"),
                bgcolor=colors.danger
            ))
            return
        
        if not user_id:
            self.page.open(ft.SnackBar(
                content=ft.Text("User ID not available"),
                bgcolor=colors.warning
            ))
            return
        
        group_id = self.group.get("id") if self.group else None
        if not group_id:
            return
        
        async def do_invite():
            try:
                success = await self.api.invite_user_to_group(group_id, user_id)
                
                if success:
                    self.page.open(ft.SnackBar(
                        content=ft.Text(f"✅ Invite sent to {username}"),
                        bgcolor=colors.success
                    ))
                else:
                    self.page.open(ft.SnackBar(
                        content=ft.Text(f"Failed to invite {username}"),
                        bgcolor=colors.danger
                    ))
            except Exception as e:
                self.page.open(ft.SnackBar(
                    content=ft.Text(f"Error: {e}"),
                    bgcolor=colors.danger
                ))
        
        self.page.run_task(do_invite)
    
    def _kick_user(self, user_id: str, username: str):
        """Kick a user from the group who was auto-accepted"""
        if not self.api:
            self.page.open(ft.SnackBar(
                content=ft.Text("API not available"),
                bgcolor=colors.danger
            ))
            return
        
        if not user_id:
            self.page.open(ft.SnackBar(
                content=ft.Text("User ID not available"),
                bgcolor=colors.warning
            ))
            return
        
        group_id = self.group.get("id") if self.group else None
        if not group_id:
            return
        
        async def do_kick():
            try:
                success = await self.api.kick_user(group_id, user_id)
                
                if success:
                    self.page.open(ft.SnackBar(
                        content=ft.Text(f"✅ Kicked {username} from group"),
                        bgcolor=colors.success
                    ))
                else:
                    self.page.open(ft.SnackBar(
                        content=ft.Text(f"Failed to kick {username}"),
                        bgcolor=colors.danger
                    ))
            except Exception as e:
                self.page.open(ft.SnackBar(
                    content=ft.Text(f"Error: {e}"),
                    bgcolor=colors.danger
                ))
        
        self.page.run_task(do_kick)

