"""
Group Guardian - Design Token System
=====================================
AAA-quality cyberpunk glassmorphism theme
"""

import flet as ft
from dataclasses import dataclass


@dataclass
class Colors:
    """Color palette - Cyberpunk Glassmorphism"""
    
    # Background layers (darkest to lightest)
    bg_deepest: str = "#0a0a0f"      # Almost black with blue tint
    bg_deep: str = "#0d0d15"          # Deep space
    bg_base: str = "#12121a"          # Base background
    bg_elevated: str = "#1a1a25"      # Elevated surfaces
    bg_elevated_2: str = "#222230"    # Slightly lighter elevated (hover/highlight)
    bg_glass: str = "rgba(30, 30, 45, 0.6)"  # Glass panels
    
    # Primary accent colors
    accent_primary: str = "#8b5cf6"   # Vibrant purple
    accent_secondary: str = "#06b6d4"  # Electric cyan
    accent_tertiary: str = "#3b82f6"   # Royal blue
    accent_pink: str = "#ec4899"       # Hot pink
    
    # Semantic colors
    success: str = "#10b981"           # Emerald green
    success_dim: str = "#059669"
    warning: str = "#f59e0b"           # Amber
    warning_dim: str = "#d97706"
    danger: str = "#ef4444"            # Red
    danger_dim: str = "#dc2626"
    danger_bg: str = "rgba(239, 68, 68, 0.1)"  # Light red background for hover
    info: str = "#06b6d4"              # Cyan
    
    # Text hierarchy
    text_primary: str = "#f8fafc"      # Almost white
    text_secondary: str = "#94a3b8"    # Muted gray-blue
    text_tertiary: str = "#64748b"     # Even more muted
    text_disabled: str = "#475569"     # Disabled state
    
    # Glass & borders
    glass_border: str = "rgba(255, 255, 255, 0.08)"
    glass_border_hover: str = "rgba(139, 92, 246, 0.3)"
    
    # Gradients (as CSS strings for backgrounds)
    @staticmethod
    def gradient_space() -> ft.LinearGradient:
        return ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=["#0a0a1a", "#1a0a2e", "#0a1a2e"],
        )
    
    @staticmethod
    def gradient_card() -> ft.LinearGradient:
        return ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=["rgba(40, 30, 70, 0.4)", "rgba(20, 40, 60, 0.4)"],
        )
    
    @staticmethod
    def gradient_button_primary() -> ft.LinearGradient:
        return ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=["#8b5cf6", "#6366f1"],
        )
    
    @staticmethod
    def gradient_button_success() -> ft.LinearGradient:
        return ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=["#10b981", "#059669"],
        )
    
    @staticmethod
    def gradient_button_danger() -> ft.LinearGradient:
        return ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=["#ef4444", "#dc2626"],
        )


@dataclass
class Spacing:
    """Spacing system - 8px grid"""
    
    xs: int = 4
    sm: int = 8
    md: int = 16
    lg: int = 24
    xl: int = 32
    xxl: int = 48
    xxxl: int = 64


@dataclass
class Radius:
    """Border radius values"""
    
    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24
    full: int = 9999


@dataclass
class Shadows:
    """Shadow definitions"""
    
    @staticmethod
    def glow_purple(blur: int = 20, opacity: float = 0.4) -> ft.BoxShadow:
        return ft.BoxShadow(
            spread_radius=0,
            blur_radius=blur,
            color=f"rgba(139, 92, 246, {opacity})",
        )
    
    @staticmethod
    def glow_cyan(blur: int = 20, opacity: float = 0.4) -> ft.BoxShadow:
        return ft.BoxShadow(
            spread_radius=0,
            blur_radius=blur,
            color=f"rgba(6, 182, 212, {opacity})",
        )
    
    @staticmethod
    def glow_success(blur: int = 15, opacity: float = 0.5) -> ft.BoxShadow:
        return ft.BoxShadow(
            spread_radius=0,
            blur_radius=blur,
            color=f"rgba(16, 185, 129, {opacity})",
        )
    
    @staticmethod
    def glow_danger(blur: int = 15, opacity: float = 0.5) -> ft.BoxShadow:
        return ft.BoxShadow(
            spread_radius=0,
            blur_radius=blur,
            color=f"rgba(239, 68, 68, {opacity})",
        )
    
    @staticmethod
    def glow_warning(blur: int = 15, opacity: float = 0.5) -> ft.BoxShadow:
        return ft.BoxShadow(
            spread_radius=0,
            blur_radius=blur,
            color=f"rgba(245, 158, 11, {opacity})",
        )
    
    @staticmethod
    def card_shadow() -> ft.BoxShadow:
        return ft.BoxShadow(
            spread_radius=0,
            blur_radius=32,
            color="rgba(0, 0, 0, 0.4)",
            offset=ft.Offset(0, 8),
        )


@dataclass
class Typography:
    """Typography settings"""
    
    font_family: str = "Inter"
    font_family_display: str = "Outfit"
    font_family_mono: str = "JetBrains Mono"
    
    # Font sizes
    size_xs: int = 11
    size_sm: int = 13
    size_base: int = 15
    size_lg: int = 18
    size_xl: int = 24
    size_2xl: int = 32
    size_3xl: int = 48


# Create singleton instances
colors = Colors()
spacing = Spacing()
radius = Radius()
shadows = Shadows()
typography = Typography()


def setup_theme(page: ft.Page) -> None:
    """Apply the Group Guardian theme to a page"""
    
    # Dark mode
    page.theme_mode = ft.ThemeMode.DARK
    
    # Custom theme - use color_scheme_seed for simplicity
    page.theme = ft.Theme(
        color_scheme_seed=colors.accent_primary,
    )
    
    # Background
    page.bgcolor = colors.bg_deepest
    
    # Window settings
    page.window.title_bar_hidden = False
    page.window.title_bar_buttons_hidden = False
    
    # Padding
    page.padding = 0
    
    # Scroll behavior
    page.scroll = None


def create_text(
    value: str,
    size: int = typography.size_base,
    color: str = colors.text_primary,
    weight: ft.FontWeight = ft.FontWeight.W_400,
    font_family: str = None,
) -> ft.Text:
    """Create a themed text widget"""
    return ft.Text(
        value=value,
        size=size,
        color=color,
        weight=weight,
        font_family=font_family or typography.font_family,
    )

# Legacy / Dict-style access for new components
COLORS = {
    "background": colors.bg_deepest,
    "surface": colors.bg_elevated,
    "surface_bright": colors.bg_glass,
    "border": colors.glass_border,
    "accent_primary": colors.accent_primary,
    "text_primary": colors.text_primary,
    "text_secondary": colors.text_secondary,
    "text_muted": colors.text_tertiary,
    "success": colors.success,
    "danger": colors.danger,
    "warning": colors.warning,
    "info": colors.info,
}
