# Android Compatibility & Mobile UX Enhancement Plan

**Created:** 2025-12-30  
**Status:** In Progress  
**Goal:** AAA Top-Tier Mobile Experience Without Compromising Desktop

---

## Executive Summary

This document provides an **exhaustive audit** of the Group Guardian application for Android/mobile compatibility and outlines a comprehensive plan to optimize the app for mobile devices while maintaining the premium PC experience.

The application is built with **Flet** (Python Flutter wrapper), which natively supports cross-platform deployment including Android, iOS, and web. However, the current UI was designed primarily for desktop and requires significant optimizations for mobile.

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Critical Mobile Issues](#2-critical-mobile-issues)
3. [Component-by-Component Audit](#3-component-by-component-audit)
4. [Platform Detection Strategy](#4-platform-detection-strategy)
5. [Responsive Layout System](#5-responsive-layout-system)
6. [Touch Optimization](#6-touch-optimization)
7. [Performance Optimizations](#7-performance-optimizations)
8. [Mobile-First Feature Adaptations](#8-mobile-first-feature-adaptations)
9. [Implementation Roadmap](#9-implementation-roadmap)
10. [AAA Mobile UX Principles](#10-aaa-mobile-ux-principles)

---

## 1. Current State Analysis

### ✅ What's Already Good

| Aspect                    | Status     | Notes                                                        |
| ------------------------- | ---------- | ------------------------------------------------------------ |
| **Platform Detection**    | ✅ Good    | `page.platform` is checked for Android/iOS in `main.py:164`  |
| **Flet Framework**        | ✅ Good    | Natively supports Android deployment                         |
| **ResponsiveRow Usage**   | ⚠️ Partial | Used in `dashboard.py` but not consistently across all views |
| **Touch Events**          | ⚠️ Partial | `on_click` handlers exist but touch targets are too small    |
| **Live Monitor Disabled** | ✅ Good    | Correctly disabled on mobile (no log file access)            |

### ❌ What Needs Work

| Aspect                   | Status      | Impact                                             |
| ------------------------ | ----------- | -------------------------------------------------- |
| **Fixed Widths**         | ❌ Critical | Many components use `width=280`, `width=340`, etc. |
| **Sidebar Navigation**   | ❌ Critical | Desktop-style sidebar doesn't work on mobile       |
| **Window Configuration** | ❌ Critical | `window.min_width=1024` breaks mobile              |
| **Touch Targets**        | ❌ Major    | Icons are 20px, should be minimum 48px on mobile   |
| **Font Sizes**           | ⚠️ Minor    | Typography sizes (11-15px) too small for mobile    |
| **Dialogs**              | ⚠️ Major    | Fixed width dialogs (400-550px) don't fit mobile   |
| **GroupCard**            | ❌ Major    | Fixed 280px width, needs fluid layout              |
| **UserCard**             | ⚠️ Major    | Fixed 80px avatar size, layout issues              |
| **Text Overflow**        | ⚠️ Minor    | Many texts cut off on small screens                |
| **Scroll Areas**         | ⚠️ Minor    | Horizontal scrolling may be needed in some areas   |

---

## 2. Critical Mobile Issues

### 2.1 Window Configuration Blocks Mobile

**File:** `main.py:139-142`

```python
page.window.width = 1280
page.window.height = 800
page.window.min_width = 1024  # ❌ BLOCKS MOBILE
page.window.min_height = 600
```

**Fix:** These window settings should be conditional on platform:

```python
if page.platform not in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]:
    page.window.width = 1280
    page.window.height = 800
    page.window.min_width = 1024
    page.window.min_height = 600
    page.window.frameless = True
```

### 2.2 Sidebar Component Incompatible with Mobile

**File:** `ui/components/sidebar.py`

The sidebar uses:

- Fixed width: `EXPANDED_WIDTH = 240`, `COLLAPSED_WIDTH = 72`
- Desktop collapse animation
- Hover effects (no hover on touch devices)

**Mobile Solution:** Replace sidebar with bottom navigation bar or hamburger + drawer pattern.

### 2.3 Fixed-Width Components

| Component        | Fixed Width              | Mobile Issue           |
| ---------------- | ------------------------ | ---------------------- |
| `GroupCard`      | 280px                    | Won't fit 320px screen |
| `LoginView` card | 340px                    | Slightly too wide      |
| `2FA View` card  | 380px                    | Won't fit mobile       |
| `GlassCard`      | Variable but often fixed | Needs `expand=True`    |
| Dialogs          | 400-550px                | Way too wide           |

---

## 3. Component-by-Component Audit

### 3.1 Core Components

#### `sidebar.py` - 🔴 Critical Rework Required

| Issue  | Current            | Mobile Fix                        |
| ------ | ------------------ | --------------------------------- |
| Layout | Fixed left sidebar | Bottom nav bar OR drawer          |
| Width  | 72-240px fixed     | Full screen drawer or bottom tabs |
| Touch  | Hover effects      | Remove hover, use tap             |
| Items  | Icon + label row   | Icon-only tabs OR full drawer     |

**Recommendation:** Create `MobileNavigation` component with bottom tab bar for primary navigation.

#### `user_card.py` - 🟡 Moderate Changes

| Issue        | Current         | Mobile Fix                 |
| ------------ | --------------- | -------------------------- |
| Avatar       | 60-80px fixed   | 48-56px on mobile          |
| Layout       | Vertical column | Same, but tighter spacing  |
| Touch target | Entire card     | Good, keep this            |
| Actions      | Small icons     | Larger 44px+ touch targets |

#### `glass_card.py` - 🟢 Minor Changes

| Issue   | Current             | Mobile Fix                              |
| ------- | ------------------- | --------------------------------------- |
| Width   | Often fixed         | Use `expand=True` by default            |
| Padding | `spacing.lg` (24px) | Reduce to `spacing.md` (16px) on mobile |
| Blur    | `ft.Blur(15, 15)`   | Consider disabling on low-end devices   |

#### `title_bar.py` - 🟡 Platform Conditional

| Issue      | Current      | Mobile Fix                         |
| ---------- | ------------ | ---------------------------------- |
| Visibility | Always shown | Hide on mobile (use system chrome) |
| Drag area  | Window drag  | Not applicable on mobile           |

### 3.2 Views

#### `login.py` - 🟡 Moderate Changes

| Issue         | Current         | Mobile Fix                       |
| ------------- | --------------- | -------------------------------- |
| Card width    | 340px, 380px    | Use `max_width` with `expand`    |
| Input heights | 48px            | Good for mobile                  |
| 2FA inputs    | 50px width each | 40-45px on mobile                |
| Keyboard      | Not handled     | Add `keyboard_type`, `autofocus` |

#### `group_selection.py` - 🔴 Major Rework

| Issue       | Current            | Mobile Fix                    |
| ----------- | ------------------ | ----------------------------- |
| Layout      | Side panel + grid  | Full-width vertical on mobile |
| Group cards | 280px fixed        | Full-width or 2-column grid   |
| User panel  | 240px left sidebar | Move to header or bottom      |

#### `dashboard.py` - 🟡 Moderate Changes

| Issue         | Current         | Mobile Fix                 |
| ------------- | --------------- | -------------------------- |
| Stats row     | 3-column grid   | Stack vertically on mobile |
| Bottom panels | 8:4 split       | Full width stacked         |
| ResponsiveRow | ✅ Already used | Good foundation            |

#### `instances.py` - 🟡 Moderate Changes

| Issue   | Current                | Mobile Fix              |
| ------- | ---------------------- | ----------------------- |
| Header  | Horizontal row         | Stack on mobile         |
| Buttons | "Invite Members", etc. | Icon-only or stacked    |
| Dialog  | 550px width            | 90% screen width        |
| List    | Horizontal rows        | Good, but simplify info |

#### `requests.py`, `bans.py`, `members.py` - 🟡 Moderate Changes

| Issue    | Current          | Mobile Fix                  |
| -------- | ---------------- | --------------------------- |
| GridView | `max_extent=260` | Reduce to 160-180 on mobile |
| UserCard | See above        | See above                   |

#### `settings.py` - 🟢 Minor Changes

| Issue    | Current    | Mobile Fix |
| -------- | ---------- | ---------- |
| Layout   | Column     | Good       |
| Sections | Full width | Good       |

#### `watchlist.py` - 🟡 Moderate Changes

| Issue       | Current          | Mobile Fix                |
| ----------- | ---------------- | ------------------------- |
| Tags filter | Horizontal chips | Wrap or horizontal scroll |
| List        | GridView         | Reduce extent             |

---

## 4. Platform Detection Strategy

### Create Responsive Utility Module

**File:** `ui/utils/responsive.py` (NEW)

```python
"""
Responsive Design Utilities
===========================
Centralized platform detection and responsive helpers
"""

import flet as ft
from dataclasses import dataclass
from enum import Enum

class DeviceType(Enum):
    MOBILE = "mobile"      # < 600px
    TABLET = "tablet"      # 600-1024px
    DESKTOP = "desktop"    # > 1024px

@dataclass
class ResponsiveConfig:
    """Device-specific configuration"""

    # Touch targets
    min_touch_target: int
    icon_size: int
    button_height: int

    # Spacing
    spacing_sm: int
    spacing_md: int
    spacing_lg: int

    # Typography
    font_size_base: int
    font_size_sm: int
    font_size_lg: int

    # Layout
    sidebar_visible: bool
    use_bottom_nav: bool
    card_padding: int
    grid_max_extent: int
    avatar_size: int

# Pre-defined configurations
MOBILE_CONFIG = ResponsiveConfig(
    min_touch_target=48,
    icon_size=24,
    button_height=48,
    spacing_sm=8,
    spacing_md=12,
    spacing_lg=16,
    font_size_base=16,
    font_size_sm=14,
    font_size_lg=20,
    sidebar_visible=False,
    use_bottom_nav=True,
    card_padding=12,
    grid_max_extent=180,
    avatar_size=48,
)

TABLET_CONFIG = ResponsiveConfig(
    min_touch_target=44,
    icon_size=22,
    button_height=44,
    spacing_sm=8,
    spacing_md=14,
    spacing_lg=20,
    font_size_base=15,
    font_size_sm=13,
    font_size_lg=18,
    sidebar_visible=True,  # Collapsed by default
    use_bottom_nav=False,
    card_padding=16,
    grid_max_extent=220,
    avatar_size=60,
)

DESKTOP_CONFIG = ResponsiveConfig(
    min_touch_target=32,
    icon_size=20,
    button_height=40,
    spacing_sm=8,
    spacing_md=16,
    spacing_lg=24,
    font_size_base=15,
    font_size_sm=13,
    font_size_lg=18,
    sidebar_visible=True,
    use_bottom_nav=False,
    card_padding=24,
    grid_max_extent=260,
    avatar_size=80,
)


def get_device_type(page: ft.Page) -> DeviceType:
    """Determine device type from platform and window size"""
    # Platform check first
    if page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]:
        width = page.width or 400
        if width >= 600:
            return DeviceType.TABLET
        return DeviceType.MOBILE

    # Desktop - also check window width
    width = page.window.width if page.window else page.width or 1280
    if width < 600:
        return DeviceType.MOBILE
    elif width < 1024:
        return DeviceType.TABLET
    return DeviceType.DESKTOP


def get_config(page: ft.Page) -> ResponsiveConfig:
    """Get responsive configuration for current device"""
    device = get_device_type(page)
    if device == DeviceType.MOBILE:
        return MOBILE_CONFIG
    elif device == DeviceType.TABLET:
        return TABLET_CONFIG
    return DESKTOP_CONFIG


def is_mobile(page: ft.Page) -> bool:
    """Quick check if running on mobile"""
    return page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]


def is_touch_device(page: ft.Page) -> bool:
    """Check if device uses touch (mobile/tablet)"""
    return page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
```

---

## 5. Responsive Layout System

### 5.1 Update Theme with Responsive Values

**File:** `ui/theme.py` - Add responsive spacing:

```python
@dataclass
class Spacing:
    """Spacing system - 8px grid with mobile variants"""

    # Desktop values (current)
    xs: int = 4
    sm: int = 8
    md: int = 16
    lg: int = 24
    xl: int = 32
    xxl: int = 48

    # Mobile overrides (smaller)
    @staticmethod
    def mobile():
        return {
            "xs": 2,
            "sm": 4,
            "md": 8,
            "lg": 12,
            "xl": 16,
            "xxl": 24,
        }
```

### 5.2 Adaptive Layout Wrapper

Create a wrapper component that automatically adjusts layouts:

```python
# ui/components/adaptive_layout.py

class AdaptiveLayout(ft.Container):
    """
    Layout wrapper that adapts based on screen size.
    - Desktop: Row layout with sidebar
    - Mobile: Column layout with bottom nav
    """

    def __init__(
        self,
        navigation: ft.Control,
        content: ft.Control,
        page: ft.Page,
        **kwargs
    ):
        self.page = page
        self.navigation = navigation
        self.main_content = content

        super().__init__(
            content=self._build_layout(),
            expand=True,
            **kwargs
        )

        # Listen for resize
        page.on_resized = self._on_resize

    def _build_layout(self):
        if is_mobile(self.page):
            return self._mobile_layout()
        return self._desktop_layout()

    def _mobile_layout(self):
        # Content on top, bottom nav bar
        return ft.Column([
            ft.Container(content=self.main_content, expand=True),
            self._build_bottom_nav(),
        ], spacing=0, expand=True)

    def _desktop_layout(self):
        # Sidebar + content
        return ft.Row([
            self.navigation,
            ft.Container(content=self.main_content, expand=True),
        ], spacing=0, expand=True)
```

---

## 6. Touch Optimization

### 6.1 Minimum Touch Targets

Google Material Design specifies **48x48dp** minimum touch targets. Current issues:

| Component      | Current Size | Required | Fix                       |
| -------------- | ------------ | -------- | ------------------------- |
| Nav icons      | 20px         | 48px     | Wrap in larger container  |
| IconButton     | 24px         | 48px     | Increase icon button size |
| Action buttons | Variable     | 48px     | Set minimum heights       |
| Dropdown items | ~36px        | 48px     | Increase item height      |

### 6.2 Remove Hover-Dependent UX

Hover effects don't work on touch devices. Replace with:

| Hover Effect          | Touch Replacement               |
| --------------------- | ------------------------------- |
| Glow on hover         | Tap highlight (ink ripple)      |
| Color change on hover | Selected state indicator        |
| Tooltip on hover      | Long-press tooltip OR info icon |
| Expand on hover       | Tap to expand                   |

### 6.3 Gesture Support

Add swipe gestures for common actions:

```python
# Swipe actions on cards
ft.GestureDetector(
    on_horizontal_drag_end=handle_swipe,
    content=user_card,
)

# Swipe right: Accept
# Swipe left: Reject
# Long press: Details
```

---

## 7. Performance Optimizations

### 7.1 Reduce Visual Effects on Mobile

```python
class GlassPanel(ft.Container):
    def __init__(self, ..., page: ft.Page = None):
        # Disable blur on mobile (GPU intensive)
        use_blur = not is_mobile(page) if page else True

        super().__init__(
            blur=ft.Blur(15, 15) if use_blur else None,
            ...
        )
```

### 7.2 Lazy Loading

Implement proper lazy loading for lists:

```python
# Use ft.ListView with lazy loading
list_view = ft.ListView(
    controls=[],
    first_item_prototype=True,  # Virtual scrolling
    padding=spacing.md,
)
```

### 7.3 Image Optimization

```python
# Reduce image sizes on mobile
avatar_size = 48 if is_mobile(page) else 80

# Use lower resolution thumbnails
thumbnail_url = user.get("thumbnailUrl")  # Lower res
full_url = user.get("currentAvatarImageUrl")  # Higher res

image_url = thumbnail_url if is_mobile(page) else full_url
```

---

## 8. Mobile-First Feature Adaptations

### 8.1 Features to Disable on Mobile

| Feature            | Reason             | Alternative                       |
| ------------------ | ------------------ | --------------------------------- |
| Live Monitor       | No log file access | "Not available on mobile" message |
| Custom Title Bar   | Uses system chrome | Hide component                    |
| Window Drag        | Not applicable     | N/A                               |
| Keyboard shortcuts | No keyboard        | Touch gestures                    |

### 8.2 Mobile-Enhanced Features

| Feature         | Enhancement                             |
| --------------- | --------------------------------------- |
| Pull-to-refresh | Add gesture to refresh data             |
| Swipe actions   | Swipe cards for quick actions           |
| Haptic feedback | Add `page.haptic_feedback()` on actions |
| Back button     | Handle Android back button              |
| Share           | Add share button for instance links     |

### 8.3 Bottom Navigation Bar

Create mobile navigation component:

```python
# ui/components/bottom_nav.py

class BottomNavBar(ft.Container):
    """
    Mobile bottom navigation bar with 5 main destinations.
    Icons only with labels, larger touch targets.
    """

    NAV_ITEMS = [
        {"icon": ft.Icons.DASHBOARD_ROUNDED, "label": "Home", "route": "/dashboard"},
        {"icon": ft.Icons.PUBLIC_ROUNDED, "label": "Instances", "route": "/instances"},
        {"icon": ft.Icons.INBOX_ROUNDED, "label": "Requests", "route": "/requests"},
        {"icon": ft.Icons.PEOPLE_ROUNDED, "label": "Members", "route": "/members"},
        {"icon": ft.Icons.SETTINGS_ROUNDED, "label": "Settings", "route": "/settings"},
    ]

    def __init__(self, on_navigate, current_route, badge_counts=None):
        self.on_navigate = on_navigate
        self.current_route = current_route
        self.badge_counts = badge_counts or {}

        super().__init__(
            content=self._build(),
            height=64,
            bgcolor=colors.bg_base,
            border=ft.border.only(top=ft.BorderSide(1, colors.glass_border)),
            padding=0,
        )

    def _build(self):
        items = []
        for nav in self.NAV_ITEMS:
            is_active = self.current_route == nav["route"]
            badge = self.badge_counts.get(nav["route"], 0)

            item = ft.Container(
                content=ft.Column([
                    ft.Stack([
                        ft.Icon(
                            nav["icon"],
                            size=24,
                            color=colors.accent_primary if is_active else colors.text_secondary,
                        ),
                        # Badge
                        ft.Container(
                            content=ft.Text(str(badge), size=10, color=colors.bg_base),
                            bgcolor=colors.danger,
                            border_radius=8,
                            padding=ft.padding.symmetric(horizontal=4, vertical=1),
                            right=0,
                            top=0,
                            visible=badge > 0,
                        ) if badge > 0 else ft.Container(),
                    ]),
                    ft.Text(
                        nav["label"],
                        size=11,
                        color=colors.accent_primary if is_active else colors.text_secondary,
                        weight=ft.FontWeight.W_500 if is_active else ft.FontWeight.W_400,
                    ),
                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                expand=True,
                alignment=ft.alignment.center,
                on_click=lambda e, r=nav["route"]: self.on_navigate(r),
                ink=True,
                ink_color="rgba(139, 92, 246, 0.15)",
                height=64,
            )
            items.append(item)

        return ft.Row(items, spacing=0, expand=True)
```

---

## 9. Implementation Roadmap

### Phase 1: Foundation (Day 1-2) 🔴 Critical

- [ ] Create `ui/utils/responsive.py` module
- [ ] Add platform detection to `main.py`
- [ ] Make window config conditional on platform
- [x] Update theme with responsive values

### Phase 2: Core Components (Day 3-4) 🔴 Critical

- [x] Create `BottomNavBar` component
- [x] Update `Sidebar` with mobile detection (hide on mobile)
- [x] Create `AdaptiveLayout` wrapper
- [x] Update `GlassCard` to disable blur on mobile

### Phase 3: Views Adaptation (Day 5-7) 🟡 Major

- [x] Update `LoginView` for fluid widths
- [x] Update `GroupSelectionView` for mobile layout
- [x] Update `DashboardView` to stack on mobile
- [x] Update `InstancesView` header for mobile
- [x] Update all dialogs for mobile widths

### Phase 4: Touch Optimization (Day 8-9) 🟡 Major

- [ ] Increase all touch targets to 48px minimum
- [ ] Remove hover-dependent UX
- [ ] Add swipe gestures to cards
- [ ] Add pull-to-refresh

### Phase 5: Performance (Day 10) 🟢 Important

- [ ] Disable blur effects on mobile
- [ ] Reduce image sizes
- [ ] Implement lazy loading
- [ ] Test on real Android device

### Phase 6: Polish (Day 11-12) 🟢 Nice to Have

- [ ] Add haptic feedback
- [ ] Handle Android back button
- [ ] Add share functionality
- [ ] Final UX testing

---

## 10. AAA Mobile UX Principles

### Design Philosophy

To achieve **"next level AAA TOP TIER"** mobile experience:

1. **Butter-Smooth Animations**

   - 60fps animations using Flet's animation capabilities
   - Spring-based curves for natural feel
   - Minimal animation duration (200-300ms)

2. **Premium Visual Effects (Adapted)**

   - Keep neon glows (use shadows instead of blur)
   - Maintain dark theme
   - Use gradient backgrounds (less GPU intensive than blur)

3. **Intuitive Gestures**

   - Single tap for primary action
   - Swipe for quick actions
   - Long press for context menu
   - Pull to refresh

4. **Contextual Actions**

   - Floating action buttons for primary actions
   - Bottom sheet dialogs instead of modal dialogs
   - Contextual toolbars that appear on selection

5. **Information Hierarchy**

   - Show only essential info on cards
   - "Tap for more" pattern for details
   - Progressive disclosure

6. **Thumb-Friendly Layout**

   - Primary actions in thumb zone (bottom half)
   - Navigation at bottom
   - Critical actions within easy reach

7. **Visual Feedback**
   - Ink ripple on all tappable elements
   - Loading skeletons instead of spinners
   - Success/error animations

### Example: Mobile Request Card

```python
class MobileRequestCard(ft.Container):
    """Optimized request card for mobile - swipe to accept/reject"""

    def __init__(self, request, api, on_action):
        user = request.get("user", {})

        # Simplified content for mobile
        content = ft.Row([
            # Avatar
            ft.Container(
                content=ft.Image(user.get("thumbnailUrl"), width=48, height=48, border_radius=24),
                width=48, height=48,
            ),
            # Name only (no status, badges on tap)
            ft.Column([
                ft.Text(user.get("displayName"), weight=ft.FontWeight.W_600, size=16),
                ft.Text("Tap for details", size=12, color=colors.text_tertiary),
            ], spacing=2, expand=True),
            # Quick action hint
            ft.Icon(ft.Icons.SWIPE_ROUNDED, color=colors.text_tertiary, size=20),
        ], spacing=12)

        # Swipe gesture
        gesture = ft.GestureDetector(
            on_horizontal_drag_end=self._handle_swipe,
            content=content,
        )

        super().__init__(
            content=gesture,
            padding=12,
            bgcolor=colors.bg_elevated,
            border_radius=12,
            height=72,  # Fixed height for list performance
            ink=True,
            on_click=self._show_details,
        )

    def _handle_swipe(self, e):
        if e.velocity_x > 0:  # Swipe right
            self._accept()
        elif e.velocity_x < 0:  # Swipe left
            self._reject()
```

---

## File Change Summary

### New Files to Create

| File                               | Purpose                                |
| ---------------------------------- | -------------------------------------- |
| `ui/utils/responsive.py`           | Platform detection & responsive config |
| `ui/utils/__init__.py`             | Package init                           |
| `ui/components/bottom_nav.py`      | Mobile bottom navigation               |
| `ui/components/adaptive_layout.py` | Adaptive layout wrapper                |
| `ui/components/mobile_card.py`     | Mobile-optimized card variants         |

### Files to Modify

| File                          | Changes                                               |
| ----------------------------- | ----------------------------------------------------- |
| `main.py`                     | Platform-conditional window config, mobile navigation |
| `ui/theme.py`                 | Add responsive spacing/typography getters             |
| `ui/components/sidebar.py`    | Add mobile detection (hide on mobile)                 |
| `ui/components/glass_card.py` | Disable blur on mobile                                |
| `ui/components/user_card.py`  | Responsive sizes, larger touch targets                |
| `ui/views/login.py`           | Fluid card widths                                     |
| `ui/views/group_selection.py` | Mobile layout                                         |
| `ui/views/dashboard.py`       | Mobile stacking                                       |
| `ui/views/instances.py`       | Mobile header, dialog widths                          |
| `ui/views/requests.py`        | Mobile card variant                                   |
| `ui/views/bans.py`            | Mobile card variant                                   |
| `ui/views/members.py`         | Mobile card variant                                   |
| `ui/views/watchlist.py`       | Mobile layout                                         |
| All dialogs                   | Mobile-friendly widths                                |

---

## Testing Checklist

### Android Emulator

- [ ] Test on 320dp width (small phone)
- [ ] Test on 360dp width (standard phone)
- [ ] Test on 400dp width (large phone)
- [ ] Test on 600dp width (tablet portrait)
- [ ] Test on 800dp width (tablet landscape)

### Real Device Testing

- [ ] Touch responsiveness
- [ ] Scroll performance
- [ ] Animation smoothness
- [ ] Memory usage
- [ ] Battery impact
- [ ] Screen rotation
- [ ] Keyboard interaction
- [ ] Back button behavior

### UX Validation

- [ ] All touch targets ≥ 48dp
- [ ] Text readable without zooming
- [ ] No horizontal scrolling on main content
- [ ] Critical actions in thumb zone
- [ ] Consistent navigation pattern
- [ ] Visual feedback on all interactions

---

_This document will be updated as implementation progresses._
