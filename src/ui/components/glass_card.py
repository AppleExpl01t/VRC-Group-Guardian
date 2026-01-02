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
        padding: int = spacing.md,  # Reduced from lg for compact layout
        border_radius_value: int = radius.md,  # Slightly smaller radius
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
        self._base_border = ft.border.all(2, colors.glass_border)  # 2x thicker
        self._hover_border = ft.border.all(2, colors.glass_border_hover)  # 2x thicker
        
        # Create glowing border shadow effect
        self._base_shadow = [
            shadows.card_shadow(),
            ft.BoxShadow(  # Inner glow from border
                spread_radius=0,
                blur_radius=12,
                color="rgba(139, 92, 246, 0.15)",
            ),
        ]
        
        super().__init__(
            content=content,
            padding=padding,
            border_radius=border_radius_value,
            bgcolor=colors.bg_elevated, # Solid opaque background for stability
            border=self._base_border,
            shadow=self._base_shadow,
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
        """Handle hover state with glow effect (no lift/zoom)"""
        if e.data == "true":
            # Hover IN - intensify border glow
            self.border = self._hover_border
            self.shadow = [
                ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=35,
                    color=f"rgba(139, 92, 246, 0.45)",
                    blur_style=ft.ShadowBlurStyle.OUTER,
                ),
                ft.BoxShadow(  # Intense border glow
                    spread_radius=2,
                    blur_radius=18,
                    color=f"rgba(139, 92, 246, 0.25)",
                ),
            ]
        else:
            # Hover OUT
            self.border = self._base_border
            self.shadow = self._base_shadow
        
        self.update()


class GlassPanel(ft.Container):
    """
    A larger glass panel for main content areas.
    Less hover effect, more static appearance.
    
    Args:
        enable_blur: Whether to enable blur effect. Set to False on mobile for performance.
    """
    
    def __init__(
        self,
        content: ft.Control = None,
        padding: int = spacing.md,  # Reduced from lg for compact layout
        border_radius_value: int = radius.md,  # Slightly smaller radius
        width: int = None,
        height: int = None,
        expand: bool = False,
        enable_blur: bool = True,  # Can be disabled for mobile performance
        **kwargs,
    ):
        # Glowing border shadow
        panel_shadow = [
            shadows.card_shadow(),
            ft.BoxShadow(  # Soft border glow
                spread_radius=0,
                blur_radius=15,
                color="rgba(139, 92, 246, 0.12)",
            ),
        ]
        
        super().__init__(
            content=content,
            padding=padding,
            border_radius=border_radius_value,
            bgcolor=colors.bg_glass,
            border=ft.border.all(2, colors.glass_border),  # 2x thicker
            shadow=panel_shadow,
            blur=ft.Blur(15, 15, ft.BlurTileMode.CLAMP) if enable_blur else None,
            width=width,
            height=height,
            expand=expand,
            **kwargs,
        )
