"""
Mobile Bottom Navigation Bar Component
=======================================
Premium bottom navigation for mobile devices with:
- 5 main destinations
- Large touch targets (48px+)
- Notification badges
- Smooth animations
- Active state indicator
"""

import flet as ft
from ..theme import colors, radius, spacing, typography


class BottomNavItem(ft.Container):
    """Individual bottom navigation item with icon, label, and optional badge"""
    
    def __init__(
        self,
        icon: str,
        label: str,
        route: str,
        is_active: bool = False,
        badge_count: int = 0,
        on_click=None,
        **kwargs
    ):
        self._icon = icon
        self._label = label
        self._route = route
        self._is_active = is_active
        self._badge_count = badge_count
        self._on_click = on_click
        
        # Create icon widget
        self._icon_widget = ft.Icon(
            name=icon,
            size=24,
            color=colors.accent_primary if is_active else colors.text_secondary,
        )
        
        # Create label widget
        self._label_widget = ft.Text(
            label,
            size=11,
            weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.W_400,
            color=colors.accent_primary if is_active else colors.text_secondary,
            text_align=ft.TextAlign.CENTER,
        )
        
        # Create badge widget
        self._badge_widget = self._build_badge()
        
        # Build content
        content = ft.Column(
            controls=[
                ft.Stack(
                    controls=[
                        ft.Container(
                            content=self._icon_widget,
                            alignment=ft.alignment.center,
                        ),
                        self._badge_widget,
                    ],
                    width=48,
                    height=28,
                ),
                self._label_widget,
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        
        super().__init__(
            content=content,
            expand=True,
            alignment=ft.alignment.center,
            height=64,
            on_click=self._handle_click,
            ink=True,
            ink_color="rgba(139, 92, 246, 0.15)",
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            **kwargs
        )
    
    def _build_badge(self) -> ft.Container:
        """Build notification badge"""
        if self._badge_count <= 0:
            return ft.Container(width=0, height=0, visible=False)
        
        badge_text = str(self._badge_count) if self._badge_count < 100 else "99+"
        
        return ft.Container(
            content=ft.Text(
                badge_text,
                size=9,
                weight=ft.FontWeight.W_700,
                color=colors.text_primary,
            ),
            bgcolor=colors.danger,
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=5, vertical=2),
            right=2,
            top=0,
            animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        )
    
    def _handle_click(self, e):
        """Handle tap on nav item"""
        if self._on_click:
            self._on_click(self._route)
    
    def set_active(self, active: bool):
        """Update active state"""
        self._is_active = active
        self._icon_widget.color = colors.accent_primary if active else colors.text_secondary
        self._label_widget.color = colors.accent_primary if active else colors.text_secondary
        self._label_widget.weight = ft.FontWeight.W_600 if active else ft.FontWeight.W_400
        self.update()
    
    def set_badge(self, count: int):
        """Update badge count"""
        self._badge_count = count
        if count > 0:
            badge_text = str(count) if count < 100 else "99+"
            self._badge_widget.content.value = badge_text
            self._badge_widget.visible = True
        else:
            self._badge_widget.visible = False
        self.update()


class BottomNavBar(ft.Container):
    """
    Mobile bottom navigation bar component.
    
    Features:
    - 5 main navigation destinations
    - Large 48px+ touch targets
    - Notification badges
    - Active state with color indicator
    - Safe area handling
    
    Usage:
        nav = BottomNavBar(
            on_navigate=handle_nav,
            current_route="/dashboard",
            badge_counts={"/requests": 5}
        )
    """
    
    # Default navigation items
    DEFAULT_NAV_ITEMS = [
        {"icon": ft.Icons.DASHBOARD_ROUNDED, "label": "Home", "route": "/dashboard"},
        {"icon": ft.Icons.PUBLIC_ROUNDED, "label": "Instances", "route": "/instances"},
        {"icon": ft.Icons.INBOX_ROUNDED, "label": "Requests", "route": "/requests"},
        {"icon": ft.Icons.PEOPLE_ROUNDED, "label": "Members", "route": "/members"},
        {"icon": ft.Icons.SETTINGS_ROUNDED, "label": "More", "route": "/settings"},
    ]
    
    def __init__(
        self,
        on_navigate=None,
        current_route: str = "/dashboard",
        badge_counts: dict = None,
        nav_items: list = None,
        **kwargs
    ):
        self._on_navigate = on_navigate
        self._current_route = current_route
        self._badge_counts = badge_counts or {}
        self._nav_items_data = nav_items or self.DEFAULT_NAV_ITEMS
        self._nav_items = {}
        
        content = self._build_content()
        
        super().__init__(
            content=content,
            height=64,
            bgcolor=colors.bg_base,
            border=ft.border.only(top=ft.BorderSide(1, colors.glass_border)),
            padding=0,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=8,
                color="rgba(0, 0, 0, 0.3)",
                offset=ft.Offset(0, -2),
            ),
            **kwargs
        )
    
    def _build_content(self) -> ft.Control:
        """Build the navigation bar content"""
        items = []
        
        for nav_data in self._nav_items_data:
            route = nav_data["route"]
            badge_count = self._badge_counts.get(route, 0)
            
            nav_item = BottomNavItem(
                icon=nav_data["icon"],
                label=nav_data["label"],
                route=route,
                is_active=self._current_route == route,
                badge_count=badge_count,
                on_click=self._handle_nav_click,
            )
            
            self._nav_items[route] = nav_item
            items.append(nav_item)
        
        return ft.Row(
            controls=items,
            spacing=0,
            expand=True,
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
        )
    
    def _handle_nav_click(self, route: str):
        """Handle navigation item click"""
        # Update active states
        for r, item in self._nav_items.items():
            item.set_active(r == route)
        
        self._current_route = route
        
        # Trigger navigation callback
        if self._on_navigate:
            self._on_navigate(route)
    
    def set_active_route(self, route: str):
        """Update active route"""
        self._current_route = route
        for r, item in self._nav_items.items():
            item.set_active(r == route)
    
    def set_badge(self, route: str, count: int):
        """Update badge count for a specific route"""
        self._badge_counts[route] = count
        if route in self._nav_items:
            self._nav_items[route].set_badge(count)
    
    def update_badges(self, badge_counts: dict):
        """Update multiple badge counts"""
        for route, count in badge_counts.items():
            self.set_badge(route, count)


class MobileMoreSheet(ft.BottomSheet):
    """
    Bottom sheet for additional navigation options (More menu).
    
    Shows secondary navigation items that don't fit in bottom nav:
    - Bans
    - History
    - Watchlist
    - Logout
    """
    
    SECONDARY_ITEMS = [
        {"icon": ft.Icons.BLOCK_ROUNDED, "label": "Bans", "route": "/bans"},
        {"icon": ft.Icons.HISTORY_ROUNDED, "label": "History", "route": "/history"},
        {"icon": ft.Icons.VISIBILITY_ROUNDED, "label": "Watchlist", "route": "/watchlist"},
    ]
    
    def __init__(
        self,
        on_navigate=None,
        on_logout=None,
        current_route: str = "",
        **kwargs
    ):
        self._on_navigate = on_navigate
        self._on_logout = on_logout
        self._current_route = current_route
        
        content = self._build_content()
        
        super().__init__(
            content=content,
            show_drag_handle=True,
            enable_drag=True,
            **kwargs
        )
    
    def _build_content(self) -> ft.Control:
        """Build the sheet content"""
        items = []
        
        for nav_data in self.SECONDARY_ITEMS:
            is_active = self._current_route == nav_data["route"]
            
            item = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            nav_data["icon"],
                            size=24,
                            color=colors.accent_primary if is_active else colors.text_secondary,
                        ),
                        ft.Container(width=spacing.md),
                        ft.Text(
                            nav_data["label"],
                            size=16,
                            weight=ft.FontWeight.W_500 if is_active else ft.FontWeight.W_400,
                            color=colors.text_primary if is_active else colors.text_secondary,
                        ),
                    ],
                ),
                padding=ft.padding.symmetric(horizontal=24, vertical=16),
                on_click=lambda e, r=nav_data["route"]: self._handle_nav(r),
                ink=True,
                border_radius=radius.md,
            )
            items.append(item)
        
        # Divider
        items.append(ft.Divider(height=1, color=colors.glass_border))
        
        # Logout button
        logout_item = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.LOGOUT_ROUNDED, size=24, color=colors.danger),
                    ft.Container(width=spacing.md),
                    ft.Text("Logout", size=16, color=colors.danger),
                ],
            ),
            padding=ft.padding.symmetric(horizontal=24, vertical=16),
            on_click=self._handle_logout,
            ink=True,
            border_radius=radius.md,
        )
        items.append(logout_item)
        
        return ft.Container(
            content=ft.Column(
                controls=items,
                spacing=spacing.xs,
            ),
            padding=ft.padding.only(top=spacing.sm, bottom=spacing.lg),
            bgcolor=colors.bg_elevated,
            border_radius=ft.border_radius.only(top_left=radius.xl, top_right=radius.xl),
        )
    
    def _handle_nav(self, route: str):
        """Handle navigation from sheet"""
        self.open = False
        self.update()
        if self._on_navigate:
            self._on_navigate(route)
    
    def _handle_logout(self, e):
        """Handle logout"""
        self.open = False
        self.update()
        if self._on_logout:
            self._on_logout()
