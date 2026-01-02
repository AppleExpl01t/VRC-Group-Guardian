"""
Neon Button Component
=====================
Gradient buttons with glow effects and hover animations
"""

import flet as ft
from ..theme import colors, radius, shadows, spacing, typography, get_contrast_text_color, hex_to_rgb


class NeonButton(ft.Container):
    """
    A premium neon-glow button with gradient background.
    Features:
    - Gradient background
    - Glow shadow
    - Hover scale and glow intensification
    - Loading state with spinner
    - Disabled state
    """
    
    VARIANT_PRIMARY = "primary"
    VARIANT_SUCCESS = "success"
    VARIANT_DANGER = "danger"
    VARIANT_WARNING = "warning"
    VARIANT_SECONDARY = "secondary"
    
    def __init__(
        self,
        text: str,
        on_click = None,
        variant: str = VARIANT_PRIMARY,
        icon: str = None,
        width: int = None,
        height: int = 36,  # Reduced from 44
        disabled: bool = False,
        loading: bool = False,
        expand: bool = False,
        **kwargs,
    ):
        self._text = text
        self._on_click = on_click
        self._variant = variant
        self._icon = icon
        self._disabled = disabled
        self._loading = loading
        self._original_gradient = self._get_gradient()
        self._original_shadow = self._get_shadow()
        
        # Build content
        button_content = self._build_content()
        
        super().__init__(
            content=button_content,
            padding=ft.padding.symmetric(horizontal=spacing.lg, vertical=2),  # Reduced vertical padding
            border_radius=radius.md,
            gradient=self._original_gradient if not disabled else None,
            bgcolor=colors.text_disabled if disabled else None,
            shadow=self._original_shadow if not disabled else None,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            on_click=self._handle_click if not disabled else None,
            on_hover=self._on_hover if not disabled else None,
            width=width,
            height=height,
            expand=expand,
            opacity=0.5 if disabled else 1.0,
            **kwargs,
        )
    
    def _build_content(self) -> ft.Control:
        """Build button content (icon + text or loading spinner)"""
        
        # Determine text color based on contrast
        text_color = colors.text_primary
        if self._variant == self.VARIANT_PRIMARY:
            text_color = get_contrast_text_color(colors.accent_primary)
            
        if self._loading:
            return ft.Row(
                controls=[
                    ft.ProgressRing(
                        width=16,
                        height=16,
                        stroke_width=2,
                        color=text_color,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        
        controls = []
        
        if self._icon:
            controls.append(
                ft.Icon(
                    name=self._icon,
                    size=18,
                    color=text_color,
                )
            )
        
        controls.append(
            ft.Text(
                self._text,
                size=typography.size_base,
                weight=ft.FontWeight.W_600,
                color=text_color,
            )
        )
        
        return ft.Row(
            controls=controls,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=spacing.sm,
        )
    
    def _get_gradient(self) -> ft.LinearGradient:
        """Get gradient based on variant"""
        gradients = {
            self.VARIANT_PRIMARY: colors.gradient_button_primary(), # Now dynamic
            self.VARIANT_SUCCESS: colors.gradient_button_success(),
            self.VARIANT_DANGER: colors.gradient_button_danger(),
            self.VARIANT_WARNING: ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=[colors.warning, colors.warning_dim],
            ),
            self.VARIANT_SECONDARY: ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=[colors.bg_elevated, colors.bg_deep],
            ),
        }
        return gradients.get(self._variant, gradients[self.VARIANT_PRIMARY])
    
    def _get_shadow(self) -> ft.BoxShadow:
        """Get glow shadow based on variant"""
        
        # Dynamic primary shadow
        primary_shadow = None
        try:
            r, g, b = hex_to_rgb(colors.accent_primary)
            primary_shadow = ft.BoxShadow(
                blur_radius=20,
                spread_radius=0,
                color=f"rgba({r}, {g}, {b}, 0.4)",
                blur_style=ft.ShadowBlurStyle.OUTER,
            )
        except:
             primary_shadow = shadows.glow_purple()

        shadow_map = {
            self.VARIANT_PRIMARY: primary_shadow,
            self.VARIANT_SUCCESS: shadows.glow_success(),
            self.VARIANT_DANGER: shadows.glow_danger(),
            self.VARIANT_WARNING: shadows.glow_warning(),
            self.VARIANT_SECONDARY: None,
        }
        return shadow_map.get(self._variant)
    
    def _on_hover(self, e: ft.ControlEvent):
        """Handle hover state - intensify glow (no zoom)"""
        if self._disabled:
            return
            
        if e.data == "true":
            # Hover IN - intensify glow only (no scale)
            if self._original_shadow:
                self.shadow = [
                    ft.BoxShadow(
                        spread_radius=3,
                        blur_radius=35,
                        color=self._original_shadow.color.replace("0.4", "0.6") if self._original_shadow.color else None,
                        blur_style=ft.ShadowBlurStyle.OUTER,
                    ),
                ]
        else:
            # Hover OUT
            self.shadow = self._original_shadow
        
        self.update()
    
    def _handle_click(self, e):
        """Handle click with ripple-like feedback"""
        if self._on_click and not self._disabled and not self._loading:
            try:
                import asyncio
                import inspect
                if inspect.iscoroutinefunction(self._on_click):
                    # Async handler - wrap in async function for run_task
                    if self.page:
                        async def run_async():
                            await self._on_click(e)
                        self.page.run_task(run_async)
                else:
                    self._on_click(e)
            except Exception as ex:
                print(f"Error in NeonButton click: {ex}")
                import traceback
                traceback.print_exc()
    
    def set_loading(self, loading: bool):
        """Set loading state"""
        self._loading = loading
        self.content = self._build_content()
        self.on_click = None if loading else self._handle_click
        self.on_hover = None if loading else self._on_hover
        self.update()

    @property
    def text(self):
        return self._text
    
    @text.setter
    def text(self, value):
        self._text = value
        self.content = self._build_content()

    @property
    def variant(self):
        return self._variant

    @variant.setter
    def variant(self, value):
        self._variant = value
        self._original_gradient = self._get_gradient()
        self._original_shadow = self._get_shadow()
        if not self._disabled:
            self.gradient = self._original_gradient
            self.shadow = self._original_shadow

    def set_disabled(self, disabled: bool):
        self._disabled = disabled
        # Update styling
        self.opacity = 0.5 if disabled else 1.0
        self.gradient = None if disabled else self._original_gradient
        self.shadow = None if disabled else self._original_shadow
        self.bgcolor = colors.text_disabled if disabled else None
        self.on_click = None if disabled else self._handle_click
        self.on_hover = None if disabled else self._on_hover




class IconButton(ft.Container):
    """
    A circular icon button with hover effect
    """
    
    def __init__(
        self,
        icon: str,
        on_click = None,
        size: int = 36,  # Reduced from 40
        icon_size: int = 20,
        icon_color: str = colors.text_secondary,
        tooltip: str = None,
        **kwargs,
    ):
        self._icon = icon
        self._default_icon_color = icon_color
        
        super().__init__(
            content=ft.Icon(
                name=icon,
                size=icon_size,
                color=icon_color,
            ),
            width=size,
            height=size,
            border_radius=size // 2,
            bgcolor=ft.Colors.TRANSPARENT,
            alignment=ft.alignment.center,
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            on_click=on_click,
            on_hover=self._on_hover,
            tooltip=tooltip,
            **kwargs,
        )
    
    def _on_hover(self, e: ft.ControlEvent):
        """Handle hover state"""
        if e.data == "true":
            self.bgcolor = colors.bg_elevated
            self.content.color = colors.text_primary
        else:
            self.bgcolor = ft.Colors.TRANSPARENT
            self.content.color = self._default_icon_color
        self.update()
