"""
Welcome View
============
Cinematic welcome screen to mask loading time.
Features user's PFP and a premium reveal animation.
"""

import flet as ft
import asyncio
from ..theme import colors, radius, shadows, spacing, typography
from ..components.animated_background import SimpleGradientBackground

class WelcomeView(ft.View):
    def __init__(self, user: dict, **kwargs):
        self._user = user
        self._display_name = user.get("displayName", "User")
        # Start with None or existing URL, but we'll update it securely
        self._pfp_src = user.get("currentAvatarThumbnailImageUrl") or user.get("userIcon")
        
        super().__init__(
            route="/welcome",
            padding=0,
            bgcolor=colors.bg_deepest,
            **kwargs,
        )
        
        # Refs for animation
        self._avatar_container = None
        self._text_column = None
        self._status_text = None
        self._progress = None
        
        self.controls = [self._build_view()]
        
    def _build_view(self) -> ft.Control:
        # 1. User Avatar with Glow
        # Initial state: hidden or placeholder
        avatar_content = ft.Image(
            src=self._pfp_src if self._pfp_src else "",
            src_base64=None,
            fit=ft.ImageFit.COVER,
            width=180,
            height=180,
            border_radius=90,
            error_content=ft.Icon(ft.Icons.PERSON_ROUNDED, size=80, color=colors.text_secondary),
            opacity=1 if self._pfp_src else 0 
        )
        
        if not self._pfp_src:
            avatar_content = ft.Icon(ft.Icons.PERSON_ROUNDED, size=80, color=colors.text_secondary)

        self._avatar_container = ft.Container(
            content=avatar_content,
            width=180,
            height=180,
            border_radius=90,
            border=ft.border.all(4, colors.bg_base),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=50,
                color=colors.accent_primary,
                offset=ft.Offset(0, 0),
                blur_style=ft.ShadowBlurStyle.NORMAL,
            ),
            animate_scale=ft.Animation(1000, ft.AnimationCurve.ELASTIC_OUT),
            scale=0.1, # Start small
            opacity=0,
            animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_OUT),
            bgcolor=colors.bg_elevated, # Background for transparency/loading
            alignment=ft.alignment.center,
        )
        
        # 2. Welcome Text
        self._text_column = ft.Column(
            controls=[
                ft.Text(
                    f"Welcome back,",
                    size=typography.size_lg,
                    color=colors.text_secondary,
                    text_align=ft.TextAlign.CENTER,
                    font_family="Outfit",
                ),
                ft.Text(
                    self._display_name,
                    size=42,
                    weight=ft.FontWeight.W_800,
                    color=colors.text_primary,
                    text_align=ft.TextAlign.CENTER,
                    font_family="Outfit", 
                ),
            ],
            spacing=spacing.xs,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            animate_opacity=ft.Animation(800, ft.AnimationCurve.EASE_OUT),
            animate_offset=ft.Animation(800, ft.AnimationCurve.EASE_OUT),
            opacity=0,
            offset=ft.Offset(0, 0.2), # Start slightly lower
        )
        
        # 3. Status & Progress
        self._status_text = ft.Text(
            "Establishing secure connection...",
            size=typography.size_sm,
            color=colors.text_tertiary,
            animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_IN),
            opacity=0,
            font_family="Outfit",
        )
        
        self._progress = ft.ProgressBar(
            width=200,
            color=colors.accent_primary,
            bgcolor=colors.bg_elevated,
            height=2,
            border_radius=radius.full,
            opacity=0,
            animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_IN),
        )

        content = ft.Column(
            controls=[
                self._avatar_container,
                ft.Container(height=spacing.xl),
                self._text_column,
                ft.Container(height=spacing.xxl),
                self._status_text,
                ft.Container(height=spacing.sm),
                self._progress,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        # Use SimpleGradientBackground to match Group/Dashboard views
        return SimpleGradientBackground(
            content=ft.Container(
                content=content,
                alignment=ft.alignment.center,
                expand=True,
            )
        )

    def set_avatar_image(self, path: str):
        """Update the avatar image path (e.g. after local cache)"""
        if not path:
            return
            
        print(f"Setting welcome avatar to: {path}")
        # Create new image control
        new_image = ft.Image(
            src=path,
            fit=ft.ImageFit.COVER,
            width=180,
            height=180,
            border_radius=90,
            error_content=ft.Icon(ft.Icons.PERSON_ROUNDED, size=80, color=colors.text_secondary),
        )
        
        self._avatar_container.content = new_image
        self._avatar_container.update()

    def did_mount(self):
        """Start animations when view is mounted"""
        self.page.run_task(self._animate_sequence)

    async def _animate_sequence(self):
        await asyncio.sleep(0.1)
        
        # 1. Pop avatar in
        self._avatar_container.opacity = 1
        self._avatar_container.scale = 1.0
        self._avatar_container.update()
        
        await asyncio.sleep(0.4)
        
        # 2. Fade in text and slide up
        self._text_column.opacity = 1
        self._text_column.offset = ft.Offset(0, 0)
        self._text_column.update()
        
        await asyncio.sleep(0.6)
        
        # 3. Show loading status
        self._status_text.opacity = 1
        self._progress.opacity = 1
        self._status_text.update()
        self._progress.update()
