"""
Group Selection View - Matching Login Theme
"""

import flet as ft
from ..theme import colors, radius, shadows, spacing, typography
from ..components.animated_background import SimpleGradientBackground


class GroupCard(ft.Container):
    def __init__(self, group: dict, on_select=None, is_active_group: bool = False, expand_card: bool = False, **kwargs):
        self._group = group
        self._on_select = on_select
        self._is_active_group = is_active_group
        self._expand_card = expand_card
        
        # Default width for desktop, or expand for mobile
        card_width = None if expand_card else 280
        
        super().__init__(
            content=self._build(),
            width=card_width,
            expand=expand_card,
            border_radius=radius.lg,
            bgcolor=colors.bg_elevated,
            border=ft.border.all(2, colors.glass_border),
            shadow=shadows.card_shadow(),
            clip_behavior=ft.ClipBehavior.NONE,  # Allow glow effects to render outside bounds
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            on_click=lambda e: on_select(group) if on_select else None,
            on_hover=self._hover,
            **kwargs,
        )
    
    def _build(self):
        g = self._group
        
        # Build icon - use group icon if available, otherwise a placeholder
        icon_url = g.get("iconUrl")
        if icon_url:
            icon_content = ft.Image(
                src=icon_url,
                fit=ft.ImageFit.COVER,
                width=50,
                height=50,
                border_radius=radius.md,
                error_content=ft.Icon(ft.Icons.GROUPS_ROUNDED, size=26, color=colors.text_primary),
            )
        else:
            icon_content = ft.Icon(ft.Icons.GROUPS_ROUNDED, size=26, color=colors.text_primary)
        
        # Build banner - use group banner if available, otherwise a gradient
        banner_url = g.get("bannerUrl")
        if banner_url:
            # Direct image allows transparency to show the card background (bg_elevated)
            banner_image = ft.Image(
                src=banner_url,
                fit=ft.ImageFit.COVER,
                width=280,
                height=80,
            )
        else:
            # No banner - use gradient on dark background
            banner_image = ft.Container(
                height=80,
                width=280,
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_left,
                    end=ft.alignment.bottom_right,
                    colors=["rgba(139,92,246,0.5)", "rgba(6,182,212,0.4)"],
                ),
            )
        
        # Wrap banner in container with rounded TOP corners to match card
        banner_content = ft.Container(
            content=banner_image,
            width=280,
            height=80,
            border_radius=ft.border_radius.only(top_left=radius.lg, top_right=radius.lg),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )
        
        # Notification Badge
        pending_count = g.get("pendingRequestCount", 0)
        badge = None
        if pending_count > 0:
            badge = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_ROUNDED, size=14, color=colors.bg_base),
                        ft.Text(str(pending_count), color=colors.bg_base, size=12, weight=ft.FontWeight.BOLD),
                    ],
                    spacing=2,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                bgcolor=colors.accent_primary,
                border_radius=radius.full,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                right=spacing.sm,
                top=spacing.sm,
                shadow=ft.BoxShadow(blur_radius=8, color=colors.accent_primary, blur_style=ft.ShadowBlurStyle.OUTER),
            )
        
        # Live Badge (Overrides Pending Badge if both present, or stack? Let's stack or prioritize Live)
        live_badge = None
        if self._is_active_group:
            # Shift pending badge down if needed, or just put Live on top/left?
            # Let's put Live in Top Right, move Pending to Top Left? Or stack vertically?
            # User wants "dynamically show the live button". A big green badge/button is good.
            live_badge = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.RADIO_BUTTON_CHECKED, size=14, color=colors.bg_base),
                        ft.Text("LIVE", color=colors.bg_base, size=12, weight=ft.FontWeight.BOLD),
                    ],
                    spacing=2,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                bgcolor=colors.success,
                border_radius=radius.full,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                right=spacing.sm,
                top=spacing.sm if not badge else spacing.xl + 4, # Stack if badge exists
                shadow=ft.BoxShadow(blur_radius=10, color=colors.success, blur_style=ft.ShadowBlurStyle.OUTER),
                animate=ft.Animation(300, ft.AnimationCurve.BOUNCE_OUT),
            )

        return ft.Column([
            ft.Stack([
                banner_content,
                # Icon
                ft.Container(
                    content=ft.Container(
                        content=icon_content,
                        width=54, height=54, border_radius=radius.md,
                        border=ft.border.all(3, colors.bg_elevated), # Blend border
                        bgcolor=colors.bg_elevated, # Match card background
                        # Use dark bg for icons to handle PNG transparency properly
                        alignment=ft.alignment.center,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                    left=spacing.md, bottom=-25,
                ),
                # Badge
                badge if badge else ft.Container(),
                live_badge if live_badge else ft.Container(),
            ], height=80, clip_behavior=ft.ClipBehavior.NONE),
            ft.Container(height=28),
            ft.Container(
                content=ft.Column([
                    ft.Text(g.get("name", "?"), size=typography.size_lg, weight=ft.FontWeight.W_600, color=colors.text_primary, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(f"{g.get('shortCode','')}.{g.get('discriminator','')}", size=typography.size_sm, color=colors.text_tertiary),
                    ft.Container(height=4),
                    ft.Row([
                        ft.Row([ft.Icon(ft.Icons.PEOPLE_ROUNDED, size=14, color=colors.text_secondary), ft.Text(f"{g.get('memberCount',0):,}", size=12, color=colors.text_secondary)], spacing=4),
                        ft.Row([ft.Container(width=8, height=8, border_radius=4, bgcolor=colors.success), ft.Text(f"{g.get('onlineMemberCount',0)} online", size=12, color=colors.success)], spacing=4),
                    ], spacing=spacing.lg),
                    ft.Row([ft.Icon(ft.Icons.STAR_ROUNDED, size=12, color="#fbbf24"), ft.Text("Owner", size=11, color="#fbbf24", weight=ft.FontWeight.W_600)], spacing=4) if g.get("isOwner") else ft.Container(),
                ], spacing=2),
                padding=spacing.md,
            ),
        ], spacing=0)
    
    def _hover(self, e):
        if e.data == "true":
            self.border = ft.border.all(2, colors.accent_primary)
            # Enhanced glow effect on hover - no zoom, just beautiful glow
            self.shadow = [
                ft.BoxShadow(blur_radius=35, color="rgba(139,92,246,0.5)", blur_style=ft.ShadowBlurStyle.OUTER),
                ft.BoxShadow(blur_radius=15, spread_radius=2, color="rgba(139,92,246,0.2)"),
            ]
        else:
            self.border = ft.border.all(2, colors.glass_border)
            self.shadow = shadows.card_shadow()
        self.update()





class GroupSelectionView(ft.View):
    """Group selection - uses same SimpleGradientBackground as Dashboard"""
    
    # VRChat status colors (same as Sidebar)
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
    
    def __init__(self, groups=None, on_group_select=None, on_logout=None, on_refresh=None, on_settings=None, username="User", pfp_path=None, user_data=None, current_group_id=None, supports_live=True, has_live_data=False, **kwargs):
        self._groups = groups or []
        self._on_group_select = on_group_select
        self._on_logout = on_logout
        self._on_refresh = on_refresh
        self._on_settings = on_settings
        self._username = username
        self._pfp_path = pfp_path
        self._user_data = user_data or {}
        self._current_group_id = current_group_id
        self._supports_live = supports_live
        self._has_live_data = has_live_data  # Whether we have active log data
        self._is_mobile = kwargs.pop("is_mobile", False)
        self._loading = None
        self._grid = None
        self._no_groups = None
        self._live_monitor_btn = None  # Reference to live monitor button
        
        # SAME as LoginView - use bg_deepest as bgcolor
        super().__init__(
            route="/groups",
            padding=0,
            bgcolor=colors.bg_deepest,
            **kwargs,
        )
        
        # Build and set controls - AnimatedBackground wraps everything
        self.controls = [self._build_view()]
    
    def _build_view(self):
        """Build the view wrapped in AnimatedBackground like LoginView"""
        from ..utils.responsive import is_mobile_platform
        
        # Use passed flag
        is_mobile = self._is_mobile
        
        # Loading indicator
        self._loading = ft.Container(
            content=ft.Column([
                ft.ProgressRing(width=50, height=50, stroke_width=3, color=colors.accent_primary),
                ft.Container(height=16),
                ft.Text("Loading your groups...", color=colors.text_secondary),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.alignment.center,
            expand=True,
            visible=len(self._groups) == 0,
        )
        
        # Groups grid
        cards = []
        if self._groups:
            cards = [
                GroupCard(
                    g, 
                    on_select=self._on_group_select,
                    is_active_group=(g.get('id') == self._current_group_id),
                    expand_card=is_mobile, # Expand cards on mobile
                    key=f"group_card_{g.get('id')}"
                ) for g in self._groups
            ]
            
        self._grid = ft.Container(
            content=ft.Column([
                ft.Row(controls=cards, wrap=True, spacing=spacing.lg, run_spacing=spacing.lg),
            ], scroll=ft.ScrollMode.AUTO, expand=True),
            expand=True,
            visible=len(self._groups) > 0,
        )
        
        # No groups
        self._no_groups = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.GROUPS_ROUNDED, size=64, color=colors.text_tertiary),
                ft.Container(height=16),
                ft.Text("No Groups Found", size=20, weight=ft.FontWeight.W_600, color=colors.text_secondary),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.alignment.center,
            expand=True,
            visible=False,
        )
        
        # Create Live Monitor button
        self._live_monitor_btn = ft.ElevatedButton(
            "Live Monitor",
            icon=ft.Icons.PLAY_CIRCLE_FILLED_ROUNDED,
            style=ft.ButtonStyle(
                color=colors.bg_base,
                bgcolor=colors.success,
            ),
            on_click=lambda e: self.page.go("/live"),
            key="live_monitor_btn",
            visible=self._supports_live and self._has_live_data,
        )
        
        # Logout button logic
        logout_button = ft.IconButton(
            icon=ft.Icons.LOGOUT_ROUNDED,
            icon_size=20 if is_mobile else 18,
            icon_color=colors.text_tertiary,
            tooltip="Logout",
            key="logout_btn",
            on_click=lambda e: self._on_logout() if self._on_logout else None,
        )
        
        # Avatar logic
        avatar_url = (
            self._pfp_path or
            self._user_data.get("local_pfp") or 
            self._user_data.get("profilePicOverride") or 
            self._user_data.get("userIcon") or 
            self._user_data.get("currentAvatarThumbnailImageUrl") or
            self._user_data.get("currentAvatarImageUrl") or
            self._user_data.get("imageUrl") or
            self._user_data.get("thumbnailUrl")
        )
        
        avatar_content = ft.Image(src=avatar_url, fit=ft.ImageFit.COVER) if avatar_url else ft.Text(self._username[0].upper() if self._username else "?", size=14, weight=ft.FontWeight.W_600, color=colors.text_primary)
        avatar_widget = ft.Container(
            content=avatar_content,
            width=36, height=36, border_radius=18,
            bgcolor=None if avatar_url else colors.accent_primary,
            alignment=ft.alignment.center,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )

        if is_mobile:
            # === MOBILE LAYOUT ===
            # Header with Avatar, Title, Settings, Logout
            mobile_header = ft.Container(
                content=ft.Row([
                    avatar_widget,
                    ft.Column([
                        ft.Text("Select Group", size=typography.size_lg, weight=ft.FontWeight.W_700, color=colors.text_primary),
                        ft.Text(self._username, size=typography.size_xs, color=colors.text_secondary),
                    ], spacing=0, expand=True),
                    self._live_monitor_btn,
                    ft.IconButton(ft.Icons.SETTINGS_ROUNDED, icon_color=colors.text_secondary, on_click=self._on_settings),
                    logout_button,
                ], spacing=spacing.sm),
                padding=ft.padding.symmetric(horizontal=spacing.md, vertical=spacing.sm),
                bgcolor=colors.bg_base,
                border=ft.border.only(bottom=ft.BorderSide(1, colors.glass_border)),
            )
            
            content = ft.Column([
                mobile_header,
                ft.Container(
                    content=ft.Stack([self._loading, self._grid, self._no_groups]),
                    expand=True,
                    padding=ft.padding.all(spacing.md),
                ),
            ], spacing=0, expand=True)
            
        else:
            # === DESKTOP LAYOUT ===
            # Original Sidebar Panel + Main Content
            
            # Header (Desktop)
            header = ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Text("Select a Group", size=typography.size_2xl, weight=ft.FontWeight.W_700, color=colors.text_primary),
                        ft.Text("Choose a group to moderate", size=typography.size_base, color=colors.text_secondary),
                    ], spacing=2),
                    ft.Container(expand=True),
                    self._live_monitor_btn,
                    ft.IconButton(
                        icon=ft.Icons.REFRESH_ROUNDED,
                        tooltip="Refresh Groups",
                        icon_color=colors.text_secondary,
                        on_click=self._on_refresh,
                        disabled=self._on_refresh is None,
                        key="refresh_groups_btn"
                    ),
                ], spacing=spacing.md),
                padding=ft.padding.all(spacing.xl),
            )

            # Sidebar Panel Construction (Reusing existing logic roughly)
            # VRChat status colors
            user_status = self._user_data.get("status", "offline")
            status_color = self.STATUS_COLORS.get(user_status.lower() if user_status else "offline", self.STATUS_COLORS["offline"])
            status_label = self.STATUS_LABELS.get(user_status.lower() if user_status else "offline", "Offline")
            
            # Logo
            import os
            icon_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.jpg"))
            logo_img = ft.Image(src=icon_path, width=36, height=36, fit=ft.ImageFit.COVER) if os.path.exists(icon_path) else ft.Icon(ft.Icons.SHIELD_ROUNDED, size=28, color=colors.accent_primary)
            logo_widget = ft.Container(content=logo_img, width=40, height=40, border_radius=radius.md, clip_behavior=ft.ClipBehavior.ANTI_ALIAS, alignment=ft.alignment.center)
            
            # User Section
            user_section = ft.Container(
                content=ft.Row([
                    avatar_widget,
                    ft.Column([
                        ft.Text(self._username, size=typography.size_sm, weight=ft.FontWeight.W_500, color=colors.text_primary),
                        ft.Row([
                            ft.Container(width=8, height=8, border_radius=4, bgcolor=status_color),
                            ft.Text(status_label, size=typography.size_xs, color=colors.text_tertiary),
                        ], spacing=4),
                    ], spacing=0, expand=True),
                    logout_button,
                ], spacing=spacing.sm, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=ft.padding.only(top=spacing.md),
                border=ft.border.only(top=ft.BorderSide(2, colors.glass_border)),
            )

            settings_btn = ft.Container(
                content=ft.Row([ft.Icon(ft.Icons.SETTINGS_ROUNDED, size=20, color=colors.text_secondary), ft.Text("Settings", size=typography.size_base, color=colors.text_secondary)], spacing=spacing.md),
                padding=ft.padding.symmetric(horizontal=spacing.md, vertical=spacing.sm),
                border_radius=radius.md,
                on_click=self._on_settings,
                on_hover=lambda e: self._hover_settings(e),
            )

            user_panel = ft.Container(
                content=ft.Column([
                    ft.Container(content=ft.Row([logo_widget, ft.Text("Group Guardian", size=typography.size_lg, weight=ft.FontWeight.W_600, color=colors.text_primary)], spacing=spacing.md), padding=ft.padding.only(bottom=spacing.lg)),
                    ft.Container(expand=True),
                    settings_btn,
                    user_section,
                ], spacing=0, expand=True),
                width=200,  # Reduced from 240 to match main Sidebar
                bgcolor=colors.bg_base,
                border=ft.border.only(right=ft.BorderSide(2, colors.glass_border)),
                padding=spacing.md,
            )
            
            content = ft.Row([
                user_panel,
                ft.Container(
                    content=ft.Stack([
                        ft.Column([
                            header,
                            ft.Container(
                                content=ft.Stack([self._loading, self._grid, self._no_groups]),
                                expand=True,
                                padding=ft.padding.symmetric(horizontal=spacing.xl),
                            ),
                        ], expand=True),
                    ]),
                    expand=True,
                ),
            ], spacing=0, expand=True)
            
        # Wrap in background
        return SimpleGradientBackground(
            content=ft.Container(
                content=content,
                expand=True,
            ),
        )
    
    def set_groups(self, groups):
        self._groups = groups
        self._loading.visible = False
        
        if groups is not None:
             # Just Group Cards
            cards = []
            
            if groups:
                cards.extend([
                    GroupCard(
                        g, 
                        on_select=self._on_group_select,
                        is_active_group=(g.get('id') == self._current_group_id),
                        key=f"group_card_{g.get('id')}"
                    ) for g in groups
                ])
            
            self._grid.content.controls[0].controls = cards
            self._grid.visible = True
            
            # Hide "No Groups" if we have cards
            self._no_groups.visible = len(groups) == 0
        else:
             # This case (groups is None) shouldn't happen with current logic but for safety
            self._grid.visible = False
            self._no_groups.visible = True
        
        if self.page:
            self.page.update()

    def set_loading(self, loading: bool):
        """Set loading state"""
        self._loading.visible = loading
        
        # If loading, hide grid/no_groups. If not loading, restore visibility based on state
        if loading:
            self._grid.visible = False
            self._no_groups.visible = False
        else:
            self._grid.visible = len(self._groups) > 0
            self._no_groups.visible = len(self._groups) == 0
            
        if self.page:
            self.page.update()

    def set_current_group_id(self, group_id: str):
        """Update active group ID and refresh cards"""
        if self._current_group_id != group_id:
            self._current_group_id = group_id
            # Refresh cards
            self.set_groups(self._groups)
    
    def set_has_live_data(self, has_live_data: bool):
        """
        Update live data availability.
        Shows/hides the Live Monitor button based on whether we have active log data.
        """
        self._has_live_data = has_live_data
        if self._live_monitor_btn:
            self._live_monitor_btn.visible = self._supports_live and has_live_data
            if self.page:
                try:
                    self._live_monitor_btn.update()
                except:
                    pass

    def _hover_settings(self, e):
        """Handle hover on settings button"""
        if e.data == "true":
            e.control.bgcolor = colors.bg_elevated
            e.control.content.controls[0].color = colors.text_primary
            e.control.content.controls[1].color = colors.text_primary
        else:
            e.control.bgcolor = None
            e.control.content.controls[0].color = colors.text_secondary
            e.control.content.controls[1].color = colors.text_secondary
        e.control.update()
