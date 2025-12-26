import flet as ft
from ..theme import colors, radius, spacing, typography
from ..components.neon_button import IconButton

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
            
    def _fetch_db_status(self):
        """Check local DB for watchlist/note status"""
        if not self.db:
            return
            
        user_id = self.user_data.get("id") or self.user_data.get("userId")
        if not user_id:
            return
            
        # We can optimistically check the db if it's passed
        # Assuming db.get_user_data(uid) is synchronous (sqlite usually is in this app)
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
            self.border = ft.border.all(1, self.highlight_color)
            self.bgcolor = colors.bg_elevated_2 # Slightly lighter for highlighted
        elif self._is_watchlisted:
            self.border = ft.border.all(1, colors.accent_primary)
            self.bgcolor = colors.bg_elevated_2
        elif self._note:
            self.border = ft.border.all(1, colors.success)
        else:
            self.border = ft.border.all(1, colors.glass_border)
            
        self.ink = True
        self.on_click = self.on_click_handler

    def _build_content(self):
        user_id = self.user_data.get("id") or self.user_data.get("userId")
        display_name = self.user_data.get("displayName") or self.user_data.get("name", "Unknown")
        thumbnail = self.user_data.get("local_pfp") or \
                    self.user_data.get("thumbnailUrl") or \
                    self.user_data.get("currentAvatarThumbnailImageUrl") or \
                    self.user_data.get("currentAvatarImageUrl") or \
                    self.user_data.get("userIcon") or \
                    self.user_data.get("profilePicOverride") or \
                    self.user_data.get("imageUrl")

        # Avatar
        self._avatar_image = ft.Image(
            src=thumbnail if thumbnail else "",
            width=32 if self.compact else 40,
            height=32 if self.compact else 40,
            fit=ft.ImageFit.COVER,
            border_radius=16 if self.compact else 20,
            opacity=1 if thumbnail else 0,
            animate_opacity=300,
        )
        
        avatar_container = ft.Container(
            content=self._avatar_image,
            width=32 if self.compact else 40,
            height=32 if self.compact else 40,
            border_radius=16 if self.compact else 20,
            bgcolor=colors.bg_base, # Placeholder color
            on_click=self.on_avatar_click if self.on_avatar_click else self.on_click_handler,
        )
        
        if not thumbnail:
            # Add initial fallback if no image yet
            avatar_container.content = ft.CircleAvatar(
                content=ft.Text(display_name[:1].upper(), size=12 if self.compact else 14),
                radius=16 if self.compact else 20,
                bgcolor=colors.accent_primary if self._is_watchlisted else colors.bg_base,
            )

        # Name & Badges
        badges = []
        if self._is_watchlisted:
            badges.append(ft.Icon(ft.Icons.VISIBILITY, size=14, color=colors.accent_primary, tooltip="Watchlisted"))
        if self._note:
            badges.append(ft.Icon(ft.Icons.NOTE, size=14, color=colors.success, tooltip="Has Note"))
            
        # 18+ Check (if data availability)
        # Note: API responses vary, verify path: tags often contain 'system_trust_veteran' etc.
        tags = self.user_data.get("tags") or []
        if "system_trust_legend" in tags: # Veteran/Legendary
             badges.append(ft.Icon(ft.Icons.VERIFIED, size=14, color=colors.warning, tooltip="Trusted User"))
        
        name_row = ft.Row(
            controls=[
                ft.Text(
                    display_name,
                    weight=ft.FontWeight.W_600,
                    size=typography.size_base,
                    color=colors.text_primary,
                    no_wrap=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    expand=True
                ),
                *badges
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        # Subtitle
        sub_controls = []
        if self.subtitle:
            sub_controls.append(ft.Text(self.subtitle, size=typography.size_xs, color=colors.text_tertiary))
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
                 sub_controls.append(ft.Container(width=6, height=6, border_radius=3, bgcolor=col))
                 sub_controls.append(ft.Text(status.title(), size=typography.size_xs, color=colors.text_tertiary))
            else:
                 sub_controls.append(ft.Text(user_id[:20]+"..." if user_id else "", size=8, color=colors.text_tertiary, font_family="Consolas"))

        text_column = ft.Column(
            controls=[
                name_row,
                ft.Row(sub_controls, spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            ],
            spacing=2,
            alignment=ft.MainAxisAlignment.CENTER,
            expand=True,
        )
        
        # Text container just ensures padding/layout, let parent handle click
        # Explicitly attaching handler to ensure it works even if parent ink consumes it or vice versa
        text_container = ft.Container(
            content=text_column,
            expand=True,
            padding=ft.padding.only(left=spacing.xs),
            on_click=self.on_click_handler
        )

        row_controls = [
            avatar_container,
            text_container,
        ]
        
        if self.trailing_controls:
            row_controls.extend(self.trailing_controls)
        else:
            row_controls.append(ft.Icon(ft.Icons.CHEVRON_RIGHT, color=colors.text_tertiary, size=16))

        return ft.Row(
            controls=row_controls,
            spacing=spacing.sm,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    async def _load_avatar(self):
        """Securely load/cache the avatar image"""
        if not self.api:
            return
            
        try:
            # Check if we already have it
            if self.user_data.get("local_pfp"):
                src = self.user_data["local_pfp"]
                if isinstance(self.content.controls[0].content, ft.Image):
                     self.content.controls[0].content.src = src
                     self.content.controls[0].content.opacity = 1
                     self.content.controls[0].content.update()
                return

            # Fetch
            path = await self.api.cache_user_image(self.user_data)
            if path:
                self.user_data["local_pfp"] = path
                # Update UI
                if isinstance(self.content.controls[0].content, ft.Image):
                    img = self.content.controls[0].content
                    img.src = path
                    img.opacity = 1
                    img.update()
                else:
                    # Switch CircleAvatar to Image if formerly text
                    self.content.controls[0].content = self._avatar_image
                    self._avatar_image.src = path
                    self._avatar_image.opacity = 1
                    self.content.controls[0].update()
                    
        except Exception as e:
            # print(f"Avatar load failed: {e}")
            pass
