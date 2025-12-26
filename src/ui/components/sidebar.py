"""
Sidebar Navigation Component
============================
Collapsible navigation with glowing active states
"""

import flet as ft
from ..theme import colors, radius, shadows, spacing, typography


class NavItem(ft.Container):
    """A single navigation item with icon and label"""
    
    def __init__(
        self,
        icon: str,
        label: str,
        route: str,
        badge_count: int = 0,
        is_active: bool = False,
        on_click = None,
        collapsed: bool = False,
        **kwargs,
    ):
        self._icon = icon
        self._label = label
        self._route = route
        self._badge_count = badge_count
        self._is_active = is_active
        self._on_click = on_click
        self._collapsed = collapsed
        
        content = self._build_content()
        
        super().__init__(
            content=content,
            padding=ft.padding.symmetric(horizontal=spacing.md, vertical=spacing.sm),
            border_radius=radius.md,
            bgcolor=colors.accent_primary if is_active else ft.Colors.TRANSPARENT,
            shadow=shadows.glow_purple(blur=15, opacity=0.3) if is_active else None,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            on_click=self._handle_click,
            on_hover=self._on_hover,
            **kwargs,
        )
    
    def _build_content(self) -> ft.Control:
        """Build nav item content"""
        icon_widget = ft.Icon(
            name=self._icon,
            size=20,
            color=colors.text_primary if self._is_active else colors.text_secondary,
        )
        
        if self._collapsed:
            return icon_widget
        
        controls = [
            icon_widget,
            ft.Text(
                self._label,
                size=typography.size_base,
                weight=ft.FontWeight.W_500 if self._is_active else ft.FontWeight.W_400,
                color=colors.text_primary if self._is_active else colors.text_secondary,
                expand=True,
            ),
        ]
        
        # Add badge if count > 0
        if self._badge_count > 0:
            controls.append(
                ft.Container(
                    content=ft.Text(
                        str(self._badge_count) if self._badge_count < 100 else "99+",
                        size=11,
                        weight=ft.FontWeight.W_600,
                        color=colors.text_primary,
                    ),
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    border_radius=radius.full,
                    bgcolor=colors.danger,
                )
            )
        
        return ft.Row(
            controls=controls,
            spacing=spacing.md,
        )
    
    def _handle_click(self, e):
        """Handle click"""
        if self._on_click:
            self._on_click(self._route)
    
    def _on_hover(self, e: ft.ControlEvent):
        """Handle hover state"""
        if self._is_active:
            return
        
        # When collapsed, self.content is just an Icon, not a Row
        if self._collapsed:
            if e.data == "true":
                self.bgcolor = colors.bg_elevated
                self.content.color = colors.text_primary
            else:
                self.bgcolor = ft.Colors.TRANSPARENT
                self.content.color = colors.text_secondary
            self.update()
            return
            
        if e.data == "true":
            self.bgcolor = colors.bg_elevated
            self.content.controls[0].color = colors.text_primary
            if len(self.content.controls) > 1:
                self.content.controls[1].color = colors.text_primary
        else:
            self.bgcolor = ft.Colors.TRANSPARENT
            self.content.controls[0].color = colors.text_secondary
            if len(self.content.controls) > 1:
                self.content.controls[1].color = colors.text_secondary
        self.update()
    
    def set_active(self, active: bool):
        """Update active state"""
        self._is_active = active
        self.bgcolor = colors.accent_primary if active else ft.Colors.TRANSPARENT
        self.shadow = shadows.glow_purple(blur=15, opacity=0.3) if active else None
        self.content = self._build_content()
        self.update()


class Sidebar(ft.Container):
    """
    Main sidebar navigation component.
    Features:
    - Logo at top
    - Navigation items with icons
    - Badge counts for notifications
    - User profile at bottom with VRChat status
    - Collapsible mode
    """
    
    # VRChat status colors
    STATUS_COLORS = {
        "join me": "#42caff",     # Light blue
        "active": "#10b981",       # Green
        "online": "#10b981",       # Green (alias)
        "ask me": "#f59e0b",       # Orange
        "busy": "#ef4444",         # Red
        "offline": "#64748b",      # Gray
    }
    
    STATUS_LABELS = {
        "join me": "Join Me",
        "active": "Online",
        "online": "Online",
        "ask me": "Ask Me",
        "busy": "Do Not Disturb",
        "offline": "Offline",
    }
    
    def __init__(
        self,
        on_navigate = None,
        on_logout = None,  # Logout callback
        current_route: str = "/dashboard",
        collapsed: bool = False,
        user_name: str = "User",
        user_data: dict = None,  # Full user data with status and avatar
        badge_counts: dict = None,
        nav_items: list = None, # Custom navigation items
        **kwargs,
    ):
        self._on_navigate = on_navigate
        self._on_logout = on_logout
        self._current_route = current_route
        self._collapsed = collapsed
        self._user_name = user_name
        self._user_data = user_data or {}
        self._badge_counts = badge_counts or {}
        self._nav_items = {}
        self._custom_nav_items = nav_items
        
        content = self._build_sidebar()
        
        super().__init__(
            content=content,
            width=64 if collapsed else 240,
            bgcolor=colors.bg_base,
            border=ft.border.only(right=ft.BorderSide(1, colors.glass_border)),
            padding=spacing.md,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            **kwargs,
        )
    
    def _get_status_color(self, status: str) -> str:
        """Get color for VRChat status"""
        return self.STATUS_COLORS.get(status.lower() if status else "offline", self.STATUS_COLORS["offline"])
    
    def _get_status_label(self, status: str) -> str:
        """Get display label for VRChat status"""
        return self.STATUS_LABELS.get(status.lower() if status else "offline", "Offline")
    
    def _build_sidebar(self) -> ft.Control:
        """Build sidebar layout"""
        
        # Logo section - use actual app icon
        import os
        icon_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "icon.jpg"))
        
        if os.path.exists(icon_path):
            logo_widget = ft.Container(
                content=ft.Image(
                    src=icon_path,
                    fit=ft.ImageFit.COVER,
                    width=36,
                    height=36,
                ),
                width=40,
                height=40,
                border_radius=radius.md,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            )
        else:
            logo_widget = ft.Container(
                content=ft.Icon(
                    ft.Icons.SHIELD_ROUNDED,
                    size=28,
                    color=colors.accent_primary,
                ),
                width=40,
                height=40,
                border_radius=radius.md,
                bgcolor=f"rgba(139, 92, 246, 0.15)",
                alignment=ft.alignment.center,
            )
        
        logo_section = ft.Container(
            content=ft.Row(
                controls=[
                    logo_widget,
                    ft.Text(
                        "Group Guardian",
                        size=typography.size_lg,
                        weight=ft.FontWeight.W_600,
                        color=colors.text_primary,
                    ) if not self._collapsed else ft.Container(),
                ],
                spacing=spacing.md,
            ),
            padding=ft.padding.only(bottom=spacing.lg),
        )
        
        # Navigation items
        if self._custom_nav_items is not None:
             nav_items_data = self._custom_nav_items
        else:
            nav_items_data = [
                {"icon": ft.Icons.DASHBOARD_ROUNDED, "label": "Dashboard", "route": "/dashboard"},
                {"icon": ft.Icons.PUBLIC_ROUNDED, "label": "Instances", "route": "/instances"},
                {"icon": ft.Icons.INBOX_ROUNDED, "label": "Requests", "route": "/requests"},
                {"icon": ft.Icons.PEOPLE_ROUNDED, "label": "Members", "route": "/members"},
                {"icon": ft.Icons.BLOCK_ROUNDED, "label": "Bans", "route": "/bans"},
                {"icon": ft.Icons.HISTORY_ROUNDED, "label": "History", "route": "/history"},
                {"icon": ft.Icons.VISIBILITY_ROUNDED, "label": "Watchlist", "route": "/watchlist"},
            ]
        
        nav_controls = []
        for item in nav_items_data:
            # Check for initial badge count override
            route = item["route"]
            badge_cnt = item.get("badge", 0)
            if route in self._badge_counts:
                badge_cnt = self._badge_counts[route]
            
            nav_item = NavItem(
                icon=item["icon"],
                label=item["label"],
                route=route,
                badge_count=badge_cnt,
                is_active=self._current_route == route,
                on_click=self._handle_nav_click,
                collapsed=self._collapsed,
            )
            self._nav_items[item["route"]] = nav_item
            nav_controls.append(nav_item)
        
        nav_section = ft.Column(
            controls=nav_controls,
            spacing=spacing.xs,
            expand=True,
        )
        
        # Settings at bottom
        settings_item = NavItem(
            icon=ft.Icons.SETTINGS_ROUNDED,
            label="Settings",
            route="/settings",
            is_active=self._current_route == "/settings",
            on_click=self._handle_nav_click,
            collapsed=self._collapsed,
        )
        self._nav_items["/settings"] = settings_item
        
        # User profile section
        # Get user avatar URL (local path or remote URL)
        avatar_url = self._user_data.get("local_pfp") or self._user_data.get("currentAvatarThumbnailImageUrl") or self._user_data.get("userIcon")
        
        # Get VRChat status
        user_status = self._user_data.get("status", "offline")
        status_color = self._get_status_color(user_status)
        status_label = self._get_status_label(user_status)
        
        # Avatar widget - use image if available, otherwise initial
        if avatar_url:
            avatar_widget = ft.Container(
                content=ft.Image(
                    src=avatar_url,
                    fit=ft.ImageFit.COVER,
                    width=36,
                    height=36,
                    border_radius=18,
                ),
                width=36,
                height=36,
                border_radius=18,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            )
        else:
            avatar_widget = ft.Container(
                content=ft.Text(
                    self._user_name[0].upper() if self._user_name else "?",
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=colors.text_primary,
                ),
                width=36,
                height=36,
                border_radius=18,
                bgcolor=colors.accent_primary,
                alignment=ft.alignment.center,
            )
        
        # Logout button
        logout_button = ft.IconButton(
            icon=ft.Icons.LOGOUT_ROUNDED,
            icon_size=18,
            icon_color=colors.text_tertiary,
            tooltip="Logout",
            on_click=self._handle_logout,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.HOVERED: colors.danger_bg,
                },
                color={
                    ft.ControlState.HOVERED: colors.danger,
                },
            ),
        )
        
        user_section = ft.Container(
            content=ft.Row(
                controls=[
                    avatar_widget,
                    ft.Column(
                        controls=[
                            ft.Text(
                                self._user_name,
                                size=typography.size_sm,
                                weight=ft.FontWeight.W_500,
                                color=colors.text_primary,
                            ),
                            ft.Row(
                                controls=[
                                    ft.Container(
                                        width=8,
                                        height=8,
                                        border_radius=4,
                                        bgcolor=status_color,
                                    ),
                                    ft.Text(
                                        status_label,
                                        size=typography.size_xs,
                                        color=colors.text_tertiary,
                                    ),
                                ],
                                spacing=4,
                            ),
                        ],
                        spacing=0,
                        expand=True,
                    ) if not self._collapsed else ft.Container(),
                    logout_button if not self._collapsed else ft.Container(),
                ],
                spacing=spacing.sm,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.padding.only(top=spacing.md),
            border=ft.border.only(top=ft.BorderSide(1, colors.glass_border)),
        )
        
        return ft.Column(
            controls=[
                logo_section,
                nav_section,
                settings_item,
                user_section,
            ],
            spacing=0,
            expand=True,
        )
    
    def _handle_nav_click(self, route: str):
        """Handle navigation click"""
        # Update active states
        for r, item in self._nav_items.items():
            item.set_active(r == route)
        
        self._current_route = route
        
        if self._on_navigate:
            self._on_navigate(route)
    
    def _handle_logout(self, e):
        """Handle logout button click"""
        if self._on_logout:
            self._on_logout()
    
    def set_badge(self, route: str, count: int):
        """Update badge count for a nav item"""
        if route in self._nav_items:
            self._nav_items[route]._badge_count = count
            self._nav_items[route].content = self._nav_items[route]._build_content()
            self._nav_items[route].update()
    
    def toggle_collapsed(self):
        """Toggle collapsed state"""
        self._collapsed = not self._collapsed
        self.width = 64 if self._collapsed else 240
        self.content = self._build_sidebar()
        self.update()
