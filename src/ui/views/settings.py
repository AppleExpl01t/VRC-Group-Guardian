"""
Settings View
=============
Application configuration and personalization
"""

import flet as ft
from ..theme import colors, radius, spacing, typography, shadows
from ..components.glass_card import GlassCard, GlassPanel
from ..components.neon_button import NeonButton

class SettingsView(ft.Container):
    """
    Settings view with organized categories:
    - UI Theme (Customization)
    - General (Placeholder)
    - Account (Placeholder)
    """
    
    def __init__(self, api=None, on_navigate=None, **kwargs):
        self.api = api
        self.on_navigate = on_navigate
        self._theme_settings_control = None
        self._custom_color_field = None
        
        # Developer Profile Data
        self._dev_profile_data = None
        self._dev_card_ref = ft.Ref()
        
        content = self._build_view()
        
        super().__init__(
            content=content,
            expand=True,
            padding=spacing.lg,
            **kwargs,
        )

    def did_mount(self):
        """Fetch developer profile on mount"""
        if self.api:
            self.page.run_task(self._fetch_dev_profile)

    async def _fetch_dev_profile(self):
        """Fetch AppleExpl01t's profile"""
        if not self.api: return
        
        dev_id = "usr_ef7c23be-3c3c-40b4-a01c-82f59b2a8229"
        try:
            user = await self.api.get_user(dev_id)
            if user:
                # Cache images
                pfp = await self.api.cache_user_image(user)
                # Helper to cache banner (re-using download_image directly if no helper exists)
                banner_url = user.get("profileBannerUrl") or user.get("currentAvatarImageUrl")
                local_banner = None
                if banner_url:
                     local_banner = await self.api.download_image(banner_url, f"dev_{dev_id}_banner")
                
                self._dev_profile_data = {
                    "name": user.get("displayName"),
                    "status": user.get("statusDescription") or user.get("status"),
                    "pfp": pfp,
                    "banner": local_banner,
                    "rank": user.get("tags", [])
                }
                self._update_dev_card()
        except Exception as e:
            print(f"Failed to fetch dev profile: {e}")

    def _update_dev_card(self):
        """Update the developer card with fetched data"""
        if self._dev_card_ref.current and self._dev_profile_data:
            # Rebuild the card content with real data
            new_content = self._build_dev_profile_content()
            self._dev_card_ref.current.content = new_content
            self._dev_card_ref.current.update()

    def _build_view(self) -> ft.Control:
        """Build settings layout"""
        
        # ... (Existing Header and Theme Settings) ...
        # Header
        header = ft.Column(
            controls=[
                ft.Text(
                    "Settings",
                    size=typography.size_2xl,
                    weight=ft.FontWeight.W_700,
                    color=colors.text_primary,
                ),
                ft.Text(
                    "Customize your experience and preferences",
                    size=typography.size_base,
                    color=colors.text_secondary,
                ),
            ],
            spacing=spacing.xs,
        )
        
        self._theme_settings_control = self._build_theme_settings()
        
        # Credits Section
        credits_section = self._build_credits_section()
        
        content_column = ft.Column(
            controls=[
                header,
                ft.Container(height=spacing.lg),
                self._theme_settings_control,
                ft.Container(height=spacing.xl),
                credits_section,
                ft.Container(height=spacing.lg),
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        
        return content_column
    
    # ... (Theme Settings Code - kept primarily as is, just referenced) ...
    def _build_theme_settings(self) -> ft.Control:
         # (Collapsed for brevity, assuming standard implementation or I'll copy the existing block if I can't partial replace)
         # Actually, I should probably keep the existing method by NOT replacing it if I can avoid it.
         # But `replace_file_content` replaces a block.
         # I will paste the _build_theme_settings from the previous `view_file`.
         
        # Quick Colors (Tokens)
        accent_colors = ["#8b5cf6", "#06b6d4", "#3b82f6", "#ec4899", "#10b981", "#f59e0b", "#ef4444"]
        
        color_row = ft.Row(
            controls=[
                ft.Container(
                    width=32, height=32, border_radius=radius.full, bgcolor=color,
                    border=ft.border.all(2, colors.text_primary if color == colors.accent_primary else "transparent"),
                    on_click=lambda e, c=color: self._handle_color_change(c),
                    animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT), tooltip=color
                ) for color in accent_colors
            ], spacing=spacing.md,
        )
        
        self._custom_color_field = ft.TextField(
             label="Custom Hex Color", value=colors.accent_primary,
             text_style=ft.TextStyle(size=typography.size_base),
             border_color=colors.glass_border, focused_border_color=colors.accent_primary,
             text_size=typography.size_base, width=200, height=45, dense=True, content_padding=10,
             on_submit=lambda e: self._handle_color_change(e.control.value),
        )

        custom_color_row = ft.Row(
            controls=[
                ft.Container(width=45, height=45, bgcolor=colors.accent_primary, border_radius=radius.md, border=ft.border.all(1, colors.glass_border)),
                self._custom_color_field,
                NeonButton(text="Apply", on_click=lambda e: self._handle_color_change(self._custom_color_field.value), variant="primary", height=45)
            ], spacing=spacing.md, vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        return GlassPanel(
            content=ft.Column(
                controls=[
                    ft.Row(controls=[ft.Icon(ft.Icons.PALETTE_ROUNDED, color=colors.accent_primary), ft.Text("UI Theme", size=typography.size_lg, weight=ft.FontWeight.W_600, color=colors.text_primary)], spacing=spacing.sm),
                    ft.Divider(color=colors.glass_border, height=spacing.xl),
                    ft.Text("Quick Colors", weight=ft.FontWeight.W_500, color=colors.text_primary),
                    ft.Container(height=spacing.xs),
                    color_row,
                    ft.Container(height=spacing.lg),
                    ft.Text("Custom Color", weight=ft.FontWeight.W_500, color=colors.text_primary),
                    ft.Container(height=spacing.xs),
                    custom_color_row,
                    ft.Divider(color=colors.glass_border, height=spacing.xl),
                    ft.Row(controls=[ft.Container(expand=True), NeonButton(text="Reset to Default", icon=ft.Icons.RESTORE_ROUNDED, on_click=self._handle_reset_theme, variant="secondary")])
                ],
            ),
        )

    def _build_credits_section(self) -> ft.Control:
        """Build the Developer Credits section"""
        return GlassPanel(
            ref=self._dev_card_ref,
            content=self._build_dev_profile_content()
        )

    def _build_dev_profile_content(self) -> ft.Control:
        """Internal builder for dev profile content"""
        
        # Default/Fallback Data
        name = self._dev_profile_data.get("name") if self._dev_profile_data else "AppleExpl01t"
        status = self._dev_profile_data.get("status") if self._dev_profile_data else "Developer"
        pfp_src = self._dev_profile_data.get("pfp") if self._dev_profile_data else ""
        banner_src = self._dev_profile_data.get("banner") if self._dev_profile_data else ""
        
        # Banner Image (with fallback gradient)
        banner = ft.Container(
            content=ft.Image(src=banner_src, fit=ft.ImageFit.COVER, opacity=0.6) if banner_src else None,
            height=120,
            bgcolor=colors.primary if not banner_src else None,
            border_radius=ft.border_radius.only(top_left=radius.lg, top_right=radius.lg),
            gradient=ft.LinearGradient(colors=[colors.accent_primary, colors.bg_deepest]) if not banner_src else None
        )

        # Profile Picture (Centered circles)
        pfp = ft.Container(
            content=ft.Image(src=pfp_src, fit=ft.ImageFit.COVER) if pfp_src else ft.Icon(ft.Icons.PERSON, size=40),
            width=80, height=80,
            border_radius=radius.full,
            border=ft.border.all(3, colors.bg_deepest),
            bgcolor=colors.bg_elevated,
            alignment=ft.alignment.center,
            shadow=shadows.glow_purple(blur=10)
        )
        
        # Speech Bubble
        bubble = ft.Container(
            content=ft.Text(f"\"{status}\"", size=12, italic=True, color=colors.text_primary),
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            bgcolor=colors.bg_elevated,
            border_radius=radius.md,
            border=ft.border.all(1, colors.accent_secondary),
            # Position this absolute relative to something? 
            # Flet Stack positioning:
            right=-10, top=0
        )
        
        # Use Stack for PFP overlapping Banner
        # Banner is at top. PFP is centered and "low on top", meaning overlapping the bottom edge of banner.
        
        profile_stack = ft.Stack(
            controls=[
                banner,
                ft.Container(
                    content=pfp,
                    alignment=ft.alignment.bottom_center,
                    bottom=-40, # Half height of PFP
                    left=0, right=0,
                ),
                # Status Bubble (Right of PFP)
                ft.Container(
                    content=bubble,
                    bottom=-30,
                    right=40, # Adjust specific to layout
                    opacity=0.9
                ) if status else ft.Container()
            ],
            height=160, # 120 banner + 40 overlap space
        )

        # Info Section
        info_col = ft.Column(
            controls=[
                ft.Container(height=45), # Spacer for PFP overlap
                ft.Text(name, size=typography.size_xl, weight=ft.FontWeight.BOLD, color=colors.accent_primary),
                ft.Text("Lead Developer", size=typography.size_sm, color=colors.text_tertiary),
                ft.Container(height=spacing.md),
                
                # Discord Link
                NeonButton(
                    text="Join our Discord Community",
                    icon=ft.Icons.DISCORD,
                    on_click=lambda e: self.page.launch_url("https://discord.gg/eDKC5yEQJN"),
                    variant="primary",
                    width=250
                ),
                ft.Container(height=spacing.lg),
                
                # References
                ft.Text("Special Thanks & References", weight=ft.FontWeight.BOLD),
                ft.Row(
                    controls=[
                        ft.TextButton("VRCX", on_click=lambda e: self.page.launch_url("https://github.com/vrcx-team/VRCX")),
                        ft.Text("|", disabled=True),
                        ft.TextButton("FCH-Toolkit", on_click=lambda e: self.page.launch_url("https://github.com/FCH-Toolkit/FCH-Toolkit")),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=spacing.xs
        )

        return ft.Container(
            content=ft.Column([
                profile_stack,
                ft.Container(content=info_col, padding=spacing.lg)
            ], spacing=0)
        )

    def _handle_color_change(self, color: str):
        # ... (Same as before) ...
        # Basic validation for Hex codes
        if not color.startswith("#"):
            color = "#" + color
        
        # Simple length check (supports #RGB and #RRGGBB)
        if len(color) not in [4, 7]:
            if self.page:
                self.page.snack_bar = ft.SnackBar(content=ft.Text("Invalid Hex Code"), bgcolor=colors.danger)
                self.page.snack_bar.open = True
                self.page.update()
            return
        
        # Update core color
        colors.accent_primary = color
        
        # Update Flet page theme (affects some built-in controls)
        if self.page:
            self.page.theme = ft.Theme(color_scheme_seed=color)
            self.page.update()
        
        # Rebuild
        if self._theme_settings_control:
             new_content = self._build_theme_settings()
             self.content.controls[2] = new_content
             self.content.update()
             
             self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Theme updated to {color}"), bgcolor=colors.bg_elevated)
             self.page.snack_bar.open = True
             self.page.update()

    def _handle_reset_theme(self, e):
        """Handle reset theme"""
        self._handle_color_change("#8b5cf6") # Default purple

    def _build_section_placeholder(self, title: str, subtitle: str) -> ft.Control:
        return GlassPanel(
            content=ft.Column(
                controls=[
                    ft.Row(controls=[ft.Icon(ft.Icons.SETTINGS_APPLICATIONS_ROUNDED, color=colors.text_secondary), ft.Text(title, size=typography.size_lg, weight=ft.FontWeight.W_600, color=colors.text_secondary)], spacing=spacing.sm),
                    ft.Text(subtitle, size=typography.size_sm, color=colors.text_tertiary),
                ]
            ),
            opacity=0.7
        )
