"""
Status Badge Component
======================
Glowing status indicators for various states
"""

import flet as ft
from ..theme import colors, radius, spacing, typography


class StatusBadge(ft.Container):
    """
    A glowing status badge for displaying states.
    Features:
    - Multiple variants (success, warning, danger, info, etc.)
    - Optional icon
    - Subtle glow effect
    - Pill shape
    """
    
    VARIANT_SUCCESS = "success"
    VARIANT_WARNING = "warning"
    VARIANT_DANGER = "danger"
    VARIANT_INFO = "info"
    VARIANT_NEUTRAL = "neutral"
    VARIANT_PURPLE = "purple"
    
    def __init__(
        self,
        text: str,
        variant: str = VARIANT_NEUTRAL,
        icon: str = None,
        small: bool = False,
        **kwargs,
    ):
        self._variant = variant
        self._colors = self._get_variant_colors()
        
        # Build content
        controls = []
        
        if icon:
            controls.append(
                ft.Icon(
                    name=icon,
                    size=12 if small else 14,
                    color=self._colors["text"],
                )
            )
        
        controls.append(
            ft.Text(
                text.upper(),
                size=typography.size_xs if small else typography.size_sm,
                weight=ft.FontWeight.W_600,
                color=self._colors["text"],
            )
        )
        
        super().__init__(
            content=ft.Row(
                controls=controls,
                spacing=spacing.xs,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(
                horizontal=spacing.sm if small else spacing.md,
                vertical=spacing.xs,
            ),
            border_radius=radius.full,
            bgcolor=self._colors["bg"],
            border=ft.border.all(2, self._colors["border"]),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=10,
                color=self._colors["glow"],
            ),
            **kwargs,
        )
    
    def _get_variant_colors(self) -> dict:
        """Get colors based on variant"""
        variants = {
            self.VARIANT_SUCCESS: {
                "bg": "rgba(16, 185, 129, 0.15)",
                "text": "#34d399",
                "border": "rgba(16, 185, 129, 0.3)",
                "glow": "rgba(16, 185, 129, 0.2)",
            },
            self.VARIANT_WARNING: {
                "bg": "rgba(245, 158, 11, 0.15)",
                "text": "#fbbf24",
                "border": "rgba(245, 158, 11, 0.3)",
                "glow": "rgba(245, 158, 11, 0.2)",
            },
            self.VARIANT_DANGER: {
                "bg": "rgba(239, 68, 68, 0.15)",
                "text": "#f87171",
                "border": "rgba(239, 68, 68, 0.3)",
                "glow": "rgba(239, 68, 68, 0.2)",
            },
            self.VARIANT_INFO: {
                "bg": "rgba(6, 182, 212, 0.15)",
                "text": "#22d3ee",
                "border": "rgba(6, 182, 212, 0.3)",
                "glow": "rgba(6, 182, 212, 0.2)",
            },
            self.VARIANT_NEUTRAL: {
                "bg": "rgba(148, 163, 184, 0.15)",
                "text": "#94a3b8",
                "border": "rgba(148, 163, 184, 0.3)",
                "glow": "rgba(148, 163, 184, 0.1)",
            },
            self.VARIANT_PURPLE: {
                "bg": "rgba(139, 92, 246, 0.15)",
                "text": "#a78bfa",
                "border": "rgba(139, 92, 246, 0.3)",
                "glow": "rgba(139, 92, 246, 0.2)",
            },
        }
        return variants.get(self._variant, variants[self.VARIANT_NEUTRAL])


class PulseDot(ft.Container):
    """
    A pulsing status dot indicator.
    """
    
    def __init__(
        self,
        color: str = colors.success,
        size: int = 8,
        pulse: bool = True,
        **kwargs,
    ):
        # Inner dot
        inner = ft.Container(
            width=size,
            height=size,
            border_radius=size // 2,
            bgcolor=color,
        )
        
        # Outer pulsing ring (if enabled)
        if pulse:
            content = ft.Stack(
                controls=[
                    ft.Container(
                        width=size + 6,
                        height=size + 6,
                        border_radius=(size + 6) // 2,
                        bgcolor=color.replace(")", ", 0.3)").replace("rgb", "rgba") if "rgb" in color else f"rgba(16, 185, 129, 0.3)",
                        animate_opacity=ft.Animation(1000, ft.AnimationCurve.EASE_IN_OUT),
                    ),
                    ft.Container(
                        content=inner,
                        alignment=ft.alignment.center,
                    ),
                ],
                width=size + 6,
                height=size + 6,
            )
        else:
            content = inner
        
        super().__init__(
            content=content,
            **kwargs,
        )
