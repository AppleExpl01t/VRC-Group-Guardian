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
        
        # State
        self._instances = []
        self._requests = []
        self._logs = []
        self._bans = []
        self._base_stats = {"active_instances": 0, "pending_requests": 0, "bans_today": 0}
        
        # UI References
        self._stats_row = None
        self._instances_panel = None
        self._activity_panel = None
        
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
        
        # Fetch all data concurrently
        import asyncio
        results = await asyncio.gather(
            self.api.get_group_instances(group_id),
            self.api.get_group_join_requests(group_id),
            self.api.get_group_audit_logs(group_id, n=10),
            self.api.get_group_bans(group_id), # Check bans to count today's
        )
        
        self._instances = results[0] or []
        self._requests = results[1] or []
        self._logs = results[2] or []
        self._bans = results[3] or []
        
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

    def _build_stats_controls(self):
        return [
            StatCard(
                icon=ft.Icons.PUBLIC_ROUNDED,
                value=str(self._base_stats["active_instances"]),
                label="Active Instances",
                subtitle="Live status",
                icon_color=colors.accent_secondary,
                expand=True,
            ),
            StatCard(
                icon=ft.Icons.INBOX_ROUNDED,
                value=str(self._base_stats["pending_requests"]),
                label="Pending Requests",
                trend="neutral", # Todo
                trend_value="",
                icon_color=colors.accent_primary,
                expand=True,
            ),
            StatCard(
                icon=ft.Icons.BLOCK_ROUNDED,
                value=str(self._base_stats["bans_today"]),
                label="Bans Today",
                subtitle="Last 24h",
                icon_color=colors.danger,
                expand=True,
            ),
        ]
    
    def _build_view(self) -> ft.Control:
        """Build dashboard layout"""
        
        # Header
        header = ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text(
                            "Dashboard",
                            size=typography.size_2xl,
                            weight=ft.FontWeight.W_700,
                            color=colors.text_primary,
                        ),
                        ft.Text(
                            "Welcome back! Here's what's happening.",
                            size=typography.size_base,
                            color=colors.text_secondary,
                        ),
                    ],
                    spacing=spacing.xs,
                ),
                ft.Row(
                    controls=[
                        IconButton(
                            icon=ft.Icons.REFRESH_ROUNDED,
                            tooltip="Refresh data",
                            on_click=lambda e: self.page.run_task(self._load_data),
                        ),
                        IconButton(
                            icon=ft.Icons.NOTIFICATIONS_ROUNDED,
                            tooltip="Notifications",
                        ),
                    ],
                    spacing=spacing.xs,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        
        # Stats row
        self._stats_row = ft.Row(
            controls=self._build_stats_controls(),
            spacing=spacing.md,
        )
        
        # Active Instances panel
        instances_panel = self._build_instances_panel()
        
        # Activity timeline
        activity_panel = self._build_activity_panel()
        
        # Bottom row with instances and activity
        bottom_row = ft.Row(
            controls=[
                ft.Container(
                    content=instances_panel,
                    expand=2,
                ),
                ft.Container(
                    content=activity_panel,
                    expand=1,
                ),
            ],
            spacing=spacing.md,
            expand=True,
        )
        
        return ft.Column(
            controls=[
                header,
                ft.Container(height=spacing.lg),
                self._stats_row,
                ft.Container(height=spacing.lg),
                bottom_row,
            ],
            spacing=0,
            expand=True,
        )
    
    def _build_instances_panel(self) -> ft.Control:
        """Build active instances panel"""
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
                                on_click=lambda e: self.on_navigate("/instances") if self.on_navigate else None
                            ),
                        ],
                    ),
                    ft.Container(height=spacing.sm),
                    self._instances_column,
                ],
                expand=True,
            ),
            expand=True,
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
                            border=ft.border.all(1, colors.glass_border),
                            border_radius=4,
                        )
                    ],
                    spacing=spacing.md,
                ),
                padding=ft.padding.symmetric(vertical=spacing.sm),
                border=ft.border.only(bottom=ft.BorderSide(1, colors.glass_border)),
            )
            rows.append(row)
        return rows
    
    def _build_activity_panel(self) -> ft.Control:
        """Build activity timeline panel"""
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
