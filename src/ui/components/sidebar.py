"""
Sidebar Navigation Component
============================
Premium collapsible navigation with smooth animations
Features:
- Elegant collapse/expand transitions
- Smooth opacity fades for labels
- Premium easing curves
"""

import flet as ft
from ..theme import colors, radius, shadows, spacing, typography

# Animation constants
COLLAPSE_DURATION = 350  # Main collapse animation duration (ms)
LABEL_FADE_DURATION = 250  # Label fade in/out duration


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
        
        # Create icon widget
        self._icon_widget = ft.Icon(
            name=self._icon,
            size=20,
            color=colors.text_primary if self._is_active else colors.text_secondary,
        )
        
        # Create label text widget with opacity animation
        self._label_widget = ft.Text(
            self._label,
            size=typography.size_base,
            weight=ft.FontWeight.W_500 if self._is_active else ft.FontWeight.W_400,
            color=colors.text_primary if self._is_active else colors.text_secondary,
            opacity=0.0 if collapsed else 1.0,
            animate_opacity=ft.Animation(LABEL_FADE_DURATION, ft.AnimationCurve.EASE_IN_OUT),
            no_wrap=True,
        )
        
        # Label container - always visible, opacity controlled
        self._label_container = ft.Container(
            content=self._label_widget,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            animate=ft.Animation(COLLAPSE_DURATION, ft.AnimationCurve.EASE_IN_OUT_CUBIC_EMPHASIZED),
        )
        
        # Badge container
        self._badge_container = self._build_badge()
        
        content = self._build_content()
        
        super().__init__(
            content=content,
            padding=ft.padding.symmetric(vertical=spacing.sm, horizontal=spacing.sm),
            border_radius=radius.md,
            bgcolor=colors.accent_primary if is_active else ft.Colors.TRANSPARENT,
            shadow=shadows.glow_purple(blur=15, opacity=0.3) if is_active else None,
            animate=ft.Animation(COLLAPSE_DURATION, ft.AnimationCurve.EASE_IN_OUT_CUBIC_EMPHASIZED),
            on_click=self._handle_click,
            on_hover=self._on_hover,
            **kwargs,
        )
    
    def _build_badge(self) -> ft.Container:
        """Build badge with animation support"""
        if self._badge_count <= 0:
            return ft.Container(width=0, height=0, visible=False)
        
        return ft.Container(
            content=ft.Text(
                str(self._badge_count) if self._badge_count < 100 else "99+",
                size=11,
                weight=ft.FontWeight.W_600,
                color=colors.text_primary,
            ),
            padding=ft.padding.symmetric(horizontal=6, vertical=2),
            border_radius=radius.full,
            bgcolor=colors.danger,
            opacity=0.0 if self._collapsed else 1.0,
            animate_opacity=ft.Animation(LABEL_FADE_DURATION, ft.AnimationCurve.EASE_IN_OUT),
        )
    
    def _build_content(self) -> ft.Control:
        """Build nav item content"""
        # Use CENTER alignment when collapsed for centered icons
        self._content_row = ft.Row(
            controls=[
                ft.Container(
                    content=self._icon_widget,
                    width=24,
                    alignment=ft.alignment.center,
                ),
                self._label_container,
                self._badge_container,
            ],
            spacing=spacing.sm,
            alignment=ft.MainAxisAlignment.CENTER if self._collapsed else ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return self._content_row
    
    def _handle_click(self, e):
        """Handle click"""
        if self._on_click:
            self._on_click(self._route)
    
    def _on_hover(self, e: ft.ControlEvent):
        """Handle hover state"""
        if self._is_active:
            return
        
        if e.data == "true":
            self.bgcolor = colors.bg_elevated
            self._icon_widget.color = colors.text_primary
            self._label_widget.color = colors.text_primary
        else:
            self.bgcolor = ft.Colors.TRANSPARENT
            self._icon_widget.color = colors.text_secondary
            self._label_widget.color = colors.text_secondary
        self.update()
    
    def set_active(self, active: bool):
        """Update active state"""
        self._is_active = active
        self.bgcolor = colors.accent_primary if active else ft.Colors.TRANSPARENT
        self.shadow = shadows.glow_purple(blur=15, opacity=0.3) if active else None
        
        # Update icon and label colors
        self._icon_widget.color = colors.text_primary if active else colors.text_secondary
        self._label_widget.weight = ft.FontWeight.W_500 if active else ft.FontWeight.W_400
        self._label_widget.color = colors.text_primary if active else colors.text_secondary
        
        self.update()
    
    def set_collapsed(self, collapsed: bool):
        """Animate collapse/expand state"""
        self._collapsed = collapsed
        
        # Animate label - only use opacity, don't toggle visible
        self._label_widget.opacity = 0.0 if collapsed else 1.0
        
        # Animate badge - only use opacity
        if self._badge_count > 0:
            self._badge_container.opacity = 0.0 if collapsed else 1.0
        
        # Update row alignment for centering when collapsed
        if hasattr(self, '_content_row') and self._content_row:
            self._content_row.alignment = ft.MainAxisAlignment.CENTER if collapsed else ft.MainAxisAlignment.START
        
        self.update()


class Sidebar(ft.Container):
    """
    Main sidebar navigation component with smooth animations.
    
    Features:
    - Elegant collapse/expand transitions
    - Logo with animated title fade
    - Navigation items with smooth transitions
    - User profile with fluid opacity changes
    """
    
    # VRChat status colors
    STATUS_COLORS = {
        "join me": "#42caff",
        "active": "#10b981",
        "online": "#10b981",
        "ask me": "#f59e0b",
        "busy": "#ef4444",
        "offline": "#64748b",
    }
    
    STATUS_LABELS = {
        "join me": "Join Me",
        "active": "Online",
        "online": "Online",
        "ask me": "Ask Me",
        "busy": "Do Not Disturb",
        "offline": "Offline",
    }
    
    EXPANDED_WIDTH = 200  # Reduced from 240
    COLLAPSED_WIDTH = 56  # Reduced from 72
    
    def __init__(
        self,
        on_navigate = None,
        on_logout = None,
        on_toggle = None,
        current_route: str = "/dashboard",
        collapsed: bool = False,
        user_name: str = "User",
        user_data: dict = None,
        badge_counts: dict = None,
        nav_items: list = None,
        **kwargs,
    ):
        self._on_navigate = on_navigate
        self._on_logout = on_logout
        self._on_toggle = on_toggle
        self._current_route = current_route
        self._collapsed = collapsed
        self._user_name = user_name
        self._user_data = user_data or {}
        self._badge_counts = badge_counts or {}
        self._nav_items = {}
        self._custom_nav_items = nav_items
        
        # Store references for animation
        self._logo_title = None
        self._logo_row = None
        self._user_details = None
        self._user_row = None
        self._logout_button = None
        self._toggle_button = None
        
        content = self._build_sidebar()
        
        super().__init__(
            content=content,
            width=self.COLLAPSED_WIDTH if collapsed else self.EXPANDED_WIDTH,
            bgcolor=colors.bg_base,
            border=ft.border.only(right=ft.BorderSide(2, colors.glass_border)),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=10,
                color="rgba(139, 92, 246, 0.08)",
                offset=ft.Offset(2, 0),
            ),
            padding=spacing.sm if collapsed else spacing.md,
            animate=ft.Animation(COLLAPSE_DURATION, ft.AnimationCurve.EASE_IN_OUT_CUBIC_EMPHASIZED),
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
        
        # Logo section
        import os
        icon_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "icon.jpg"))
        
        if os.path.exists(icon_path):
            logo_icon = ft.Container(
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
            logo_icon = ft.Container(
                content=ft.Icon(
                    ft.Icons.SHIELD_ROUNDED,
                    size=28,
                    color=colors.accent_primary,
                ),
                width=40,
                height=40,
                border_radius=radius.md,
                bgcolor="rgba(139, 92, 246, 0.15)",
                alignment=ft.alignment.center,
            )
        
        # Animated logo title
        self._logo_title = ft.Container(
            content=ft.Text(
                "Group Guardian",
                size=typography.size_lg,
                weight=ft.FontWeight.W_600,
                color=colors.text_primary,
                no_wrap=True,
                opacity=0.0 if self._collapsed else 1.0,
                animate_opacity=ft.Animation(LABEL_FADE_DURATION, ft.AnimationCurve.EASE_IN_OUT),
            ),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
        
        # Store reference to logo row for alignment changes
        self._logo_row = ft.Row(
            controls=[logo_icon, self._logo_title],
            spacing=spacing.md,
            alignment=ft.MainAxisAlignment.CENTER if self._collapsed else ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        
        logo_section = ft.Container(
            content=self._logo_row,
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
            self._nav_items[route] = nav_item
            nav_controls.append(nav_item)
        
        nav_section = ft.Column(
            controls=nav_controls,
            spacing=spacing.xs,
            expand=True,
        )
        
        # Settings item
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
        avatar_url = (
            self._user_data.get("local_pfp") or 
            self._user_data.get("profilePicOverride") or 
            self._user_data.get("userIcon") or 
            self._user_data.get("currentAvatarThumbnailImageUrl") or
            self._user_data.get("currentAvatarImageUrl") or
            self._user_data.get("imageUrl") or
            self._user_data.get("thumbnailUrl")
        )
        
        user_status = self._user_data.get("status", "offline")
        status_color = self._get_status_color(user_status)
        status_label = self._get_status_label(user_status)
        
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
        
        # User details with animation
        self._user_details = ft.Container(
            content=ft.Column(
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
            ),
            opacity=0.0 if self._collapsed else 1.0,
            animate_opacity=ft.Animation(LABEL_FADE_DURATION, ft.AnimationCurve.EASE_IN_OUT),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
        
        # Logout button
        self._logout_button = ft.Container(
            content=ft.IconButton(
                icon=ft.Icons.LOGOUT_ROUNDED,
                icon_size=18,
                icon_color=colors.text_tertiary,
                tooltip="Logout",
                on_click=self._handle_logout,
                style=ft.ButtonStyle(
                    bgcolor={ft.ControlState.HOVERED: colors.danger_bg},
                    color={ft.ControlState.HOVERED: colors.danger},
                ),
            ),
            opacity=0.0 if self._collapsed else 1.0,
            animate_opacity=ft.Animation(LABEL_FADE_DURATION, ft.AnimationCurve.EASE_IN_OUT),
        )
        
        # Store reference to user row for alignment changes
        self._user_row = ft.Row(
            controls=[
                avatar_widget,
                self._user_details,
                self._logout_button,
            ],
            spacing=spacing.sm,
            alignment=ft.MainAxisAlignment.CENTER if self._collapsed else ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        
        user_section = ft.Container(
            content=self._user_row,
            padding=ft.padding.only(top=spacing.md),
            border=ft.border.only(top=ft.BorderSide(2, colors.glass_border)),
        )

        # Toggle button
        self._toggle_button = ft.IconButton(
            icon=ft.Icons.KEYBOARD_DOUBLE_ARROW_RIGHT_ROUNDED if self._collapsed else ft.Icons.KEYBOARD_DOUBLE_ARROW_LEFT_ROUNDED,
            icon_size=18,
            icon_color=colors.text_secondary,
            tooltip="Expand" if self._collapsed else "Collapse",
            on_click=lambda e: self.toggle_collapsed(),
        )
        
        toggle_section = ft.Container(
            content=self._toggle_button,
            padding=ft.padding.only(top=spacing.xs),
            alignment=ft.alignment.center,
        )
        
        return ft.Column(
            controls=[
                logo_section,
                nav_section,
                settings_item,
                user_section,
                toggle_section,
            ],
            spacing=0,
            expand=True,
        )
    
    def _handle_nav_click(self, route: str):
        """Handle navigation click"""
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
            nav_item = self._nav_items[route]
            nav_item._badge_count = count
            nav_item._badge_container = nav_item._build_badge()
            nav_item.content = nav_item._build_content()
            nav_item.update()
    
    def toggle_collapsed(self):
        """Toggle collapsed state with smooth animations"""
        self._collapsed = not self._collapsed
        
        # Animate sidebar width
        self.width = self.COLLAPSED_WIDTH if self._collapsed else self.EXPANDED_WIDTH
        self.padding = spacing.sm if self._collapsed else spacing.md
        
        # Animate logo - opacity and centering
        if self._logo_title and self._logo_title.content:
            self._logo_title.content.opacity = 0.0 if self._collapsed else 1.0
            self._logo_title.update()
        if self._logo_row:
            self._logo_row.alignment = ft.MainAxisAlignment.CENTER if self._collapsed else ft.MainAxisAlignment.START
            self._logo_row.update()
        
        # Animate nav items
        for route, nav_item in self._nav_items.items():
            nav_item.set_collapsed(self._collapsed)
        
        # Animate user details - only opacity
        if self._user_details:
            self._user_details.opacity = 0.0 if self._collapsed else 1.0
            self._user_details.update()
        
        # Animate logout button - only opacity
        if self._logout_button:
            self._logout_button.opacity = 0.0 if self._collapsed else 1.0
            self._logout_button.update()
        
        # Center user row when collapsed
        if self._user_row:
            self._user_row.alignment = ft.MainAxisAlignment.CENTER if self._collapsed else ft.MainAxisAlignment.START
            self._user_row.update()
        
        # Update toggle button icon
        if self._toggle_button:
            self._toggle_button.icon = (
                ft.Icons.KEYBOARD_DOUBLE_ARROW_RIGHT_ROUNDED 
                if self._collapsed 
                else ft.Icons.KEYBOARD_DOUBLE_ARROW_LEFT_ROUNDED
            )
            self._toggle_button.tooltip = "Expand" if self._collapsed else "Collapse"
            self._toggle_button.update()
        
        self.update()
        
        if self._on_toggle:
            self._on_toggle(self._collapsed)
    
    def set_collapsed(self, collapsed: bool):
        """Set collapsed state (used for responsive layout)"""
        if self._collapsed != collapsed:
            self._collapsed = collapsed
            
            self.width = self.COLLAPSED_WIDTH if self._collapsed else self.EXPANDED_WIDTH
            self.padding = spacing.sm if self._collapsed else spacing.md
            
            if self._logo_title and self._logo_title.content:
                self._logo_title.content.opacity = 0.0 if self._collapsed else 1.0
                self._logo_title.update()
            if self._logo_row:
                self._logo_row.alignment = ft.MainAxisAlignment.CENTER if self._collapsed else ft.MainAxisAlignment.START
                self._logo_row.update()
            
            for route, nav_item in self._nav_items.items():
                nav_item.set_collapsed(self._collapsed)
            
            if self._user_details:
                self._user_details.opacity = 0.0 if self._collapsed else 1.0
                self._user_details.update()
            
            if self._logout_button:
                self._logout_button.opacity = 0.0 if self._collapsed else 1.0
                self._logout_button.update()
            
            if self._user_row:
                self._user_row.alignment = ft.MainAxisAlignment.CENTER if self._collapsed else ft.MainAxisAlignment.START
                self._user_row.update()
            
            if self._toggle_button:
                self._toggle_button.icon = (
                    ft.Icons.KEYBOARD_DOUBLE_ARROW_RIGHT_ROUNDED 
                    if self._collapsed 
                    else ft.Icons.KEYBOARD_DOUBLE_ARROW_LEFT_ROUNDED
                )
                self._toggle_button.tooltip = "Expand" if self._collapsed else "Collapse"
                self._toggle_button.update()
            
            self.update()
    
    def refresh_theme(self):
        """Refresh theme-dependent colors"""
        for route, nav_item in self._nav_items.items():
            if nav_item._is_active:
                nav_item.bgcolor = colors.accent_primary
                from .neon_button import hex_to_rgb
                try:
                    r, g, b = hex_to_rgb(colors.accent_primary)
                    nav_item.shadow = ft.BoxShadow(
                        blur_radius=15,
                        spread_radius=0,
                        color=f"rgba({r}, {g}, {b}, 0.3)",
                        blur_style=ft.ShadowBlurStyle.OUTER,
                    )
                except:
                    nav_item.shadow = shadows.glow_purple(blur=15, opacity=0.3)
                nav_item.update()
        
        self.update()
