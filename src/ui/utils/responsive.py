"""
Responsive Design Utilities
===========================
Centralized platform detection and responsive helpers for mobile/tablet/desktop
"""

import flet as ft
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DeviceType(Enum):
    """Device type classification based on screen size and platform"""
    MOBILE = "mobile"      # < 600px (phones)
    TABLET = "tablet"      # 600-1024px (tablets)
    DESKTOP = "desktop"    # > 1024px (desktop/laptop)


@dataclass
class ResponsiveConfig:
    """Device-specific configuration for UI elements"""
    
    # Touch targets - minimum sizes for interactive elements
    min_touch_target: int
    icon_size: int
    icon_button_size: int
    button_height: int
    
    # Spacing - padding and margins
    spacing_xs: int
    spacing_sm: int
    spacing_md: int
    spacing_lg: int
    spacing_xl: int
    
    # Typography - font sizes
    font_size_xs: int
    font_size_sm: int
    font_size_base: int
    font_size_lg: int
    font_size_xl: int
    font_size_2xl: int
    
    # Layout - structural settings
    sidebar_visible: bool
    use_bottom_nav: bool
    card_padding: int
    grid_max_extent: int
    dialog_max_width: Optional[int]  # None = 90% of screen
    
    # Components
    avatar_size: int
    avatar_size_compact: int
    group_card_width: Optional[int]  # None = expand
    
    # Effects
    enable_blur: bool  # Disable on low-end mobile for performance
    enable_complex_shadows: bool


# ============================================================================
# Pre-defined configurations for each device type
# ============================================================================

MOBILE_CONFIG = ResponsiveConfig(
    # Touch targets
    min_touch_target=48,
    icon_size=24,
    icon_button_size=44,
    button_height=48,
    
    # Spacing (tighter for mobile)
    spacing_xs=2,
    spacing_sm=4,
    spacing_md=8,
    spacing_lg=12,
    spacing_xl=16,
    
    # Typography (larger for readability)
    font_size_xs=12,
    font_size_sm=14,
    font_size_base=16,
    font_size_lg=18,
    font_size_xl=22,
    font_size_2xl=28,
    
    # Layout
    sidebar_visible=False,
    use_bottom_nav=True,
    card_padding=12,
    grid_max_extent=180,
    dialog_max_width=None,  # Full width dialog
    
    # Components
    avatar_size=48,
    avatar_size_compact=40,
    group_card_width=None,  # Full width cards
    
    # Effects
    enable_blur=False,  # Disable for performance
    enable_complex_shadows=False,
)

TABLET_CONFIG = ResponsiveConfig(
    # Touch targets
    min_touch_target=44,
    icon_size=22,
    icon_button_size=40,
    button_height=44,
    
    # Spacing
    spacing_xs=4,
    spacing_sm=8,
    spacing_md=12,
    spacing_lg=16,
    spacing_xl=24,
    
    # Typography
    font_size_xs=11,
    font_size_sm=13,
    font_size_base=15,
    font_size_lg=18,
    font_size_xl=24,
    font_size_2xl=32,
    
    # Layout
    sidebar_visible=True,  # Collapsed by default
    use_bottom_nav=False,
    card_padding=16,
    grid_max_extent=220,
    dialog_max_width=450,
    
    # Components
    avatar_size=60,
    avatar_size_compact=48,
    group_card_width=260,
    
    # Effects
    enable_blur=True,
    enable_complex_shadows=True,
)

DESKTOP_CONFIG = ResponsiveConfig(
    # Touch targets (can be smaller with mouse)
    min_touch_target=32,
    icon_size=20,
    icon_button_size=36,
    button_height=40,
    
    # Spacing (standard)
    spacing_xs=4,
    spacing_sm=8,
    spacing_md=16,
    spacing_lg=24,
    spacing_xl=32,
    
    # Typography (standard)
    font_size_xs=11,
    font_size_sm=13,
    font_size_base=15,
    font_size_lg=18,
    font_size_xl=24,
    font_size_2xl=32,
    
    # Layout
    sidebar_visible=True,
    use_bottom_nav=False,
    card_padding=24,
    grid_max_extent=260,
    dialog_max_width=500,
    
    # Components
    avatar_size=80,
    avatar_size_compact=60,
    group_card_width=280,
    
    # Effects
    enable_blur=True,
    enable_complex_shadows=True,
)


# ============================================================================
# Detection Functions
# ============================================================================

def is_mobile_platform(page: ft.Page) -> bool:
    """Check if running on mobile platform (Android/iOS)"""
    if not page:
        return False
    return page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]


def is_android(page: ft.Page) -> bool:
    """Check if running on Android"""
    if not page:
        return False
    return page.platform == ft.PagePlatform.ANDROID


def is_ios(page: ft.Page) -> bool:
    """Check if running on iOS"""
    if not page:
        return False
    return page.platform == ft.PagePlatform.IOS


def is_touch_device(page: ft.Page) -> bool:
    """Check if device uses touch input (mobile/tablet)"""
    return is_mobile_platform(page)


def is_desktop(page: ft.Page) -> bool:
    """Check if running on desktop"""
    if not page:
        return True  # Default to desktop
    return page.platform not in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]


def get_screen_width(page: ft.Page) -> int:
    """Get current screen/window width"""
    if not page:
        return 1280  # Default desktop
    
    # On mobile, use page.width (screen width)
    if is_mobile_platform(page):
        return page.width or 400
    
    # On desktop, use window width
    if page.window:
        return page.window.width or 1280
    
    return page.width or 1280


def get_screen_height(page: ft.Page) -> int:
    """Get current screen/window height"""
    if not page:
        return 800
    
    # On mobile, use page.height (screen height)
    if is_mobile_platform(page):
        return page.height or 800
    
    # On desktop, use window height
    if page.window:
        return page.window.height or 800
    
    return page.height or 800


def get_device_type(page: ft.Page) -> DeviceType:
    """
    Determine device type from platform and screen size.
    
    - MOBILE: Android/iOS with width < 600px
    - TABLET: Android/iOS with width >= 600px, OR desktop 600-1024px
    - DESKTOP: Desktop/Web with width > 1024px
    """
    # Platform check first
    if is_mobile_platform(page):
        width = get_screen_width(page)
        if width >= 600:
            return DeviceType.TABLET
        return DeviceType.MOBILE
    
    # Desktop - also check window width for responsive debugging
    width = get_screen_width(page)
    if width < 600:
        return DeviceType.MOBILE
    elif width < 1024:
        return DeviceType.TABLET
    return DeviceType.DESKTOP


def get_config(page: ft.Page) -> ResponsiveConfig:
    """
    Get responsive configuration for current device.
    
    Returns a ResponsiveConfig object with all UI parameters
    appropriate for the current device type.
    """
    device = get_device_type(page)
    if device == DeviceType.MOBILE:
        return MOBILE_CONFIG
    elif device == DeviceType.TABLET:
        return TABLET_CONFIG
    return DESKTOP_CONFIG


# ============================================================================
# Responsive Helpers
# ============================================================================

def responsive_value(page: ft.Page, mobile, tablet=None, desktop=None):
    """
    Return a value based on device type.
    
    Usage:
        padding = responsive_value(page, mobile=8, tablet=12, desktop=16)
        visible = responsive_value(page, mobile=False, desktop=True)
    """
    device = get_device_type(page)
    
    if device == DeviceType.MOBILE:
        return mobile
    elif device == DeviceType.TABLET:
        return tablet if tablet is not None else desktop if desktop is not None else mobile
    else:  # DESKTOP
        return desktop if desktop is not None else tablet if tablet is not None else mobile


def responsive_col(page: ft.Page, mobile_cols: int = 12, tablet_cols: int = None, desktop_cols: int = None) -> dict:
    """
    Generate ResponsiveRow column dictionary based on device.
    
    Usage:
        container = ft.Container(col=responsive_col(page, 12, 6, 4))
    
    Returns:
        dict with xs, sm, md, lg, xl keys for ResponsiveRow
    """
    t = tablet_cols if tablet_cols is not None else mobile_cols
    d = desktop_cols if desktop_cols is not None else t
    
    return {
        "xs": mobile_cols,
        "sm": mobile_cols,
        "md": t,
        "lg": d,
        "xl": d,
    }


def get_dialog_width(page: ft.Page, max_width: int = 500) -> int:
    """
    Get appropriate dialog width for current screen.
    
    On mobile: 90% of screen width
    On tablet/desktop: min(max_width, 90% of screen)
    """
    screen_width = get_screen_width(page)
    
    if is_mobile_platform(page):
        # 90% of screen width, with some minimum
        return max(280, int(screen_width * 0.9))
    
    # Desktop/Tablet: use max_width or 90% of screen, whichever is smaller
    return min(max_width, int(screen_width * 0.9))


def get_grid_extent(page: ft.Page, desktop_extent: int = 260) -> int:
    """
    Get grid max_extent for current device.
    
    Smaller on mobile to fit more items in view with proper sizing.
    """
    config = get_config(page)
    return config.grid_max_extent


def get_button_height(page: ft.Page) -> int:
    """Get appropriate button height for current device"""
    config = get_config(page)
    return config.button_height


def get_icon_size(page: ft.Page) -> int:
    """Get appropriate icon size for current device"""
    config = get_config(page)
    return config.icon_size


def get_avatar_size(page: ft.Page, compact: bool = False) -> int:
    """Get appropriate avatar size for current device"""
    config = get_config(page)
    return config.avatar_size_compact if compact else config.avatar_size


def should_show_sidebar(page: ft.Page) -> bool:
    """Check if sidebar should be visible on current device"""
    config = get_config(page)
    return config.sidebar_visible


def should_use_bottom_nav(page: ft.Page) -> bool:
    """Check if bottom navigation should be used on current device"""
    config = get_config(page)
    return config.use_bottom_nav


def should_enable_blur(page: ft.Page) -> bool:
    """Check if blur effects should be enabled (performance consideration)"""
    config = get_config(page)
    return config.enable_blur


# ============================================================================
# Spacing Helpers
# ============================================================================

class ResponsiveSpacing:
    """
    Responsive spacing values that adapt to device type.
    
    Usage:
        sp = ResponsiveSpacing(page)
        container = ft.Container(padding=sp.md)
    """
    
    def __init__(self, page: ft.Page):
        self._config = get_config(page)
    
    @property
    def xs(self) -> int:
        return self._config.spacing_xs
    
    @property
    def sm(self) -> int:
        return self._config.spacing_sm
    
    @property
    def md(self) -> int:
        return self._config.spacing_md
    
    @property
    def lg(self) -> int:
        return self._config.spacing_lg
    
    @property
    def xl(self) -> int:
        return self._config.spacing_xl


class ResponsiveTypography:
    """
    Responsive font sizes that adapt to device type.
    
    Usage:
        typo = ResponsiveTypography(page)
        text = ft.Text("Hello", size=typo.base)
    """
    
    def __init__(self, page: ft.Page):
        self._config = get_config(page)
    
    @property
    def xs(self) -> int:
        return self._config.font_size_xs
    
    @property
    def sm(self) -> int:
        return self._config.font_size_sm
    
    @property
    def base(self) -> int:
        return self._config.font_size_base
    
    @property
    def lg(self) -> int:
        return self._config.font_size_lg
    
    @property
    def xl(self) -> int:
        return self._config.font_size_xl
    
    @property
    def xxl(self) -> int:
        return self._config.font_size_2xl
