"""
Glassmorphism Card Component
============================
Frosted glass effect panel with subtle glow
"""

import flet as ft
from ..theme import colors, radius, shadows, spacing


class GlassCard(ft.Container):
    """
    A premium glassmorphism card with frosted glass effect.
    Features:
    - Translucent background with blur
    - Subtle border glow
    - Hover animation with lift effect
    """
    
    def __init__(
        self,
        content: ft.Control = None,
        padding: int = spacing.lg,
        border_radius_value: int = radius.lg,
        hover_enabled: bool = True,
        glow_color: str = colors.accent_primary,
        on_click = None,
        width: int = None,
        height: int = None,
        expand: bool = False,
        **kwargs,
    ):
        self._hover_enabled = hover_enabled
        self._glow_color = glow_color
        self._base_border = ft.border.all(1, colors.glass_border)
        self._hover_border = ft.border.all(1, colors.glass_border_hover)
        
        super().__init__(
            content=content,
            padding=padding,
            border_radius=border_radius_value,
            bgcolor=colors.bg_elevated, # Solid opaque background for stability
            border=self._base_border,
            shadow=shadows.card_shadow(),
            # blur=ft.Blur(20, 20, ft.BlurTileMode.CLAMP), # Removed to fix rendering artifacts
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            on_click=on_click,
            on_hover=self._on_hover if hover_enabled else None,
            width=width,
            height=height,
            expand=expand,
            **kwargs,
        )
    
    def _on_hover(self, e: ft.ControlEvent):
        """Handle hover state with lift and glow effect"""
        if e.data == "true":
            # Hover IN
            self.border = self._hover_border
            self.shadow = ft.BoxShadow(
                spread_radius=0,
                blur_radius=25,
                color=f"rgba(139, 92, 246, 0.3)",
                offset=ft.Offset(0, 12),
            )
            self.offset = ft.Offset(0, -0.01)  # Slight lift
        else:
            # Hover OUT
            self.border = self._base_border
            self.shadow = shadows.card_shadow()
            self.offset = ft.Offset(0, 0)
        
        self.update()


class GlassPanel(ft.Container):
    """
    A larger glass panel for main content areas.
    Less hover effect, more static appearance.
    """
    
    def __init__(
        self,
        content: ft.Control = None,
        padding: int = spacing.lg,
        border_radius_value: int = radius.lg,
        width: int = None,
        height: int = None,
        expand: bool = False,
        **kwargs,
    ):
        super().__init__(
            content=content,
            padding=padding,
            border_radius=border_radius_value,
            bgcolor=colors.bg_glass,
            border=ft.border.all(1, colors.glass_border),
            shadow=shadows.card_shadow(),
            blur=ft.Blur(15, 15, ft.BlurTileMode.CLAMP),
            width=width,
            height=height,
            expand=expand,
            **kwargs,
        )
