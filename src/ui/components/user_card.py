import flet as ft
from ..theme import colors, radius, spacing, typography
from ..components.neon_button import IconButton
from services.event_bus import get_event_bus
from services.watchlist_service import get_watchlist_service

class UserCard(ft.Container):
    """
    A unified user card component for displaying user summaries across the app.
    Handles avatar caching, badges, and consistent styling.
    """
    def __init__(
        self, 
        user_data: dict, 
        api, 
        db=None, 
        on_click=None, 
        on_avatar_click=None,
        trailing_controls: list = None,
        subtitle: str = None,
        highlight_color: str = None,
        compact: bool = False,
        **kwargs
    ):
        if "key" not in kwargs and user_data:
             id_val = user_data.get("id") or user_data.get("userId")
             if id_val:
                 kwargs["key"] = f"user_card_{id_val}"
        super().__init__(**kwargs)
        self.user_data = user_data
        self.api = api # VRChatAPI instance
        self.db = db   # DatabaseService instance
        self.on_click_handler = on_click
        self.on_avatar_click = on_avatar_click or on_click
        self.trailing_controls = trailing_controls or []
        self.subtitle = subtitle
        self.highlight_color = highlight_color
        self.compact = compact
        
        # State
        self._is_watchlisted = False
        self._note = None
        self._avatar_image = None
        
        # Initialize
        self._fetch_db_status()
        self.content = self._build_content()
        self._apply_styling()
        
    def did_mount(self):
        # Trigger lazy image load
        if self.page:
            self.page.run_task(self._load_avatar)
            
        # Subscribe to updates
        get_event_bus().subscribe("user_updated", self._on_user_updated)

    def will_unmount(self):
        get_event_bus().unsubscribe("user_updated", self._on_user_updated)

    def _on_user_updated(self, data):
        """Handle user update event"""
        target_id = data.get("user_id")
        my_id = self.user_data.get("id") or self.user_data.get("userId")
        
        if target_id and target_id == my_id:
            self._fetch_db_status()
            # Re-apply styling based on new status
            self._apply_styling()
            # Re-build content if needed (e.g. badges changed)
            self.content = self._build_content()
            self.update()
            
    def _fetch_db_status(self):
        """Check watchlist service for watchlist/note status and ensure user is recorded"""
        user_id = self.user_data.get("id") or self.user_data.get("userId")
        if not user_id:
            return
        
        # Get display name for recording
        username = self.user_data.get("displayName") or self.user_data.get("name", "Unknown")
        
        # Use centralized watchlist service - this ensures user is recorded and checked
        try:
            watchlist_svc = get_watchlist_service()
            status = watchlist_svc.check_and_record_user(user_id, username)
            self._is_watchlisted = status.get("is_watchlisted", False)
            self._note = status.get("note")
        except Exception:
            # Fallback to direct DB access if service fails
            if self.db:
                try:
                    entry = self.db.get_user_data(user_id)
                    if entry:
                        self._is_watchlisted = entry.get("is_watchlisted", False)
                        self._note = entry.get("note")
                except Exception:
                    pass

    def _apply_styling(self):
        self.padding = spacing.sm if self.compact else spacing.md
        self.border_radius = radius.md
        self.bgcolor = colors.bg_elevated
        
        # Determine Border
        if self.highlight_color:
            self.border = ft.border.all(2, self.highlight_color)
            self.bgcolor = colors.bg_elevated_2 # Slightly lighter for highlighted
        elif self._is_watchlisted:
            self.border = ft.border.all(2, colors.accent_primary)
            self.bgcolor = colors.bg_elevated_2
        elif self._note:
            self.border = ft.border.all(2, colors.success)
        else:
            self.border = ft.border.all(2, colors.glass_border)
        
        # Ensure entire card is clickable with proper ink effect
        self.ink = True
        self.ink_color = "rgba(139, 92, 246, 0.15)"  # Subtle purple ripple
        self.on_click = self._handle_card_click
        self.on_hover = self._handle_hover
        
        # Add animation for hover effects
        self.animate = ft.Animation(200, ft.AnimationCurve.EASE_OUT)
    
    def _handle_card_click(self, e):
        """Handle click on entire card - logs and forwards to handler"""
        user_id = self.user_data.get("id") or self.user_data.get("userId")
        print(f"[UserCard] Click registered on card for user: {user_id}")
        if self.on_click_handler:
            self.on_click_handler(e)
    
    def _handle_hover(self, e):
        """Handle hover with glow effect"""
        if e.data == "true":
            # Hover IN - add glow
            self.shadow = [
                ft.BoxShadow(blur_radius=20, color="rgba(139, 92, 246, 0.3)", blur_style=ft.ShadowBlurStyle.OUTER),
            ]
        else:
            # Hover OUT
            self.shadow = None
        self.update()

    def _build_content(self):
        user_id = self.user_data.get("id") or self.user_data.get("userId")
        display_name = self.user_data.get("displayName") or self.user_data.get("name", "Unknown")
        # Only use local cached image to avoid Flet loading issues with VRChat CDNs (which result in black circles)
        thumbnail = self.user_data.get("local_pfp")

        # Avatar - reduced sizes for compact layout
        size = 48 if self.compact else 64  # Reduced from 60/80
        radius_val = size / 2
        
        self._avatar_image = ft.Image(
            src=thumbnail if thumbnail else "",
            width=size,
            height=size,
            fit=ft.ImageFit.COVER,
            border_radius=radius_val,
            opacity=1 if thumbnail else 0,
            animate_opacity=300,
        )
        
        # Avatar container - NO on_click here, parent container handles all clicks
        avatar_container = ft.Container(
            content=self._avatar_image,
            width=size,
            height=size,
            border_radius=radius_val,
            bgcolor=colors.bg_base, # Placeholder color
        )
        
        if not thumbnail:
            # Add initial fallback if no image yet
            avatar_container.content = ft.CircleAvatar(
                content=ft.Text(display_name[:1].upper(), size=16 if self.compact else 20),  # Reduced from 20/24
                radius=radius_val,
                bgcolor=colors.accent_primary if self._is_watchlisted else colors.bg_base,
            )

        # Name & Badges
        badges = []
        
        # Local DB badges (watchlist/notes)
        if self._is_watchlisted:
            badges.append(ft.Icon(ft.Icons.VISIBILITY, size=14, color=colors.accent_primary, tooltip="Watchlisted"))
        if self._note:
            badges.append(ft.Icon(ft.Icons.NOTE, size=14, color=colors.success, tooltip="Has Note"))
        
        # VRChat Trust Ranks
        tags = self.user_data.get("tags") or []
        trust_badges = {
            "system_trust_legend": ("⭐", "#FFD700", "Legendary User"),  # Gold
            "system_trust_veteran": ("🏆", "#FFD700", "Veteran User"),  # Gold
            "system_trust_trusted": ("✓", "#a66efa", "Trusted User"),   # Purple
            "system_trust_known": ("◆", "#ff7b42", "Known User"),       # Orange
            "system_trust_basic": ("●", "#2bcf5c", "User"),             # Green
            "system_trust_new": ("○", "#1e88e5", "New User"),           # Blue
            "system_troll": ("⚠", colors.danger, "Nuisance User"),      # Red
        }
        
        for tag, (symbol, color, tooltip) in trust_badges.items():
            if tag in tags:
                if tag in ["system_trust_legend", "system_trust_veteran"]:
                    badges.append(ft.Icon(ft.Icons.VERIFIED, size=14, color=color, tooltip=tooltip))
                elif tag == "system_troll":
                    badges.append(ft.Container(
                        content=ft.Text(symbol, size=10, color=colors.bg_deepest, weight=ft.FontWeight.BOLD),
                        bgcolor=color,
                        padding=ft.padding.symmetric(horizontal=3, vertical=1),
                        border_radius=4,
                        tooltip=tooltip,
                    ))
                else:
                    badges.append(ft.Container(
                        content=ft.Text(symbol, size=10, color=colors.bg_deepest, weight=ft.FontWeight.BOLD),
                        bgcolor=color,
                        padding=ft.padding.symmetric(horizontal=3, vertical=1),
                        border_radius=4,
                        tooltip=tooltip,
                    ))
                break  # Only show highest trust rank
        
        # Age Verification Status (18+)
        age_status = self.user_data.get("ageVerificationStatus")
        is_age_verified = self.user_data.get("ageVerified", False)

        if (is_age_verified and age_status == "18+") or "system_age_verified" in tags:
            badges.append(ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.SMART_BUTTON, size=8, color=colors.text_primary), # Placeholder icon, 'SMART_BUTTON' looks a bit like a card/badge
                        ft.Text("18+", size=9, color=colors.text_primary, weight=ft.FontWeight.BOLD),
                    ],
                    spacing=2,
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=colors.bg_elevated_2, # Use a subtle background
                padding=ft.padding.symmetric(horizontal=4, vertical=1),
                border_radius=4,
                border=ft.border.all(1, colors.text_tertiary), # Add a subtle border
                tooltip="Age Verified 18+",
            ))
        
        # Platform Icons (VR/Desktop/Mobile)
        last_platform = self.user_data.get("last_platform", "")
        platform_icons = {
            "standalonewindows": (ft.Icons.COMPUTER, "Desktop"),
            "android": (ft.Icons.PHONE_ANDROID, "Mobile/Quest"),
            "ios": (ft.Icons.PHONE_IPHONE, "iOS"),
        }
        if last_platform and last_platform.lower() in platform_icons:
            icon, tooltip = platform_icons[last_platform.lower()]
            badges.append(ft.Icon(icon, size=12, color=colors.text_tertiary, tooltip=tooltip))
        
        # Check for VR headset indicators in tags
        if any("system_world_access" in t for t in tags if t):
            # This user can access VR worlds, likely has VR
            pass  # Could add VR badge if needed

        
        # Layout Construction (Vertical/Grid Style)
        
        content_controls = []
        
        # 1. Avatar (Centered, larger)
        content_controls.append(
            ft.Container(
                content=avatar_container,
                alignment=ft.alignment.center,
                padding=ft.padding.only(bottom=spacing.xs)
            )
        )
        
        # 2. Name & Badges (Centered)
        content_controls.append(
            ft.Row(
                controls=[
                    ft.Text(
                        display_name,
                        weight=ft.FontWeight.W_600,
                        size=typography.size_base,
                        color=colors.text_primary,
                        no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    *badges
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                wrap=True, # Allow wrapping if name+badges are too long
                spacing=4,
            )
        )

        
        # 3. Subtitle / Status (Centered)
        # Re-using logic from before but centering
        status_row_controls = []
        if self.subtitle:
             status_row_controls.append(ft.Text(self.subtitle, size=typography.size_xs, color=colors.text_tertiary, text_align=ft.TextAlign.CENTER))
        else:
            # Default ID or status
            status = self.user_data.get("status")
            if status:
                 # Status color dot
                 status_colors = {
                    "active": colors.success, "online": colors.success,
                    "join me": "#42caff", "ask me": "#f59e0b",
                    "busy": colors.danger, "offline": colors.text_tertiary
                 }
                 col = status_colors.get(str(status).lower(), colors.text_tertiary)
                 status_row_controls.append(ft.Container(width=6, height=6, border_radius=3, bgcolor=col))
                 status_row_controls.append(ft.Text(status.title(), size=typography.size_xs, color=colors.text_tertiary))
            else:
                 status_row_controls.append(ft.Text(user_id[:20]+"..." if user_id else "", size=8, color=colors.text_tertiary, font_family="Consolas"))
        
        if status_row_controls:
            content_controls.append(
                ft.Row(
                    status_row_controls, 
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4
                )
            )
            
        # 4. Trailing Controls (Actions) - Moved to bottom footer
        if self.trailing_controls:
            content_controls.append(ft.Container(height=spacing.xs)) # Spacer
            content_controls.append(
                ft.Row(
                    self.trailing_controls,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=spacing.md
                )
            )

        return ft.Column(
            controls=content_controls,
            spacing=2,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    async def _load_avatar(self):
        """Securely load/cache the avatar image, fetching full profile if needed"""
        if not self.api:
            return
            
        try:
            # Check if we need to fetch full profile (if missing image URLs)
            # Include all possible image fields that VRChat API might return
            img_keys = ["profilePicOverride", "userIcon", "iconUrl", "thumbnailUrl", 
                       "currentAvatarThumbnailImageUrl", "currentAvatarImageUrl", "imageUrl"]
            has_img_url = any(self.user_data.get(k) for k in img_keys)
            
            user_id = self.user_data.get("id") or self.user_data.get("userId")

            if not has_img_url and user_id:
                # Fetch full profile to get image URLs
                full_profile = await self.api.get_user(user_id)
                if full_profile:
                    self.user_data.update(full_profile)
                    
            # Check if we already have it locally (maybe from a previous fetch or DB)
            if self.user_data.get("local_pfp"):
                src = self.user_data["local_pfp"]
                if isinstance(self.content.controls[0].content, ft.Image):
                     self.content.controls[0].content.src = src
                     self.content.controls[0].content.opacity = 1
                     if self.content.controls[0].content.page:
                        self.content.controls[0].content.update()
                # If it was a CircleAvatar (placeholder), we need to swap it
                elif hasattr(self.content.controls[0], "content") and isinstance(self.content.controls[0].content, ft.CircleAvatar):
                     self.content.controls[0].content = self._avatar_image
                     self._avatar_image.src = src
                     self._avatar_image.opacity = 1
                     if self.content.controls[0].page:
                        self.content.controls[0].update()
                return

            # Fetch (cache_user_image handles picking the best URL)
            path = await self.api.cache_user_image(self.user_data)
            
            if path:
                self.user_data["local_pfp"] = path
                # Update UI
                if isinstance(self.content.controls[0].content, ft.Image):
                    img = self.content.controls[0].content
                    img.src = path
                    img.opacity = 1
                else:
                    # Switch CircleAvatar to Image if formerly text
                    self.content.controls[0].content = self._avatar_image
                    self._avatar_image.src = path
                    self._avatar_image.opacity = 1
                
                if self.page:
                    self.update()
                    
        except Exception as e:
            print(f"Avatar load failed for user {self.user_data.get('id') or self.user_data.get('userId')}: {e}")
