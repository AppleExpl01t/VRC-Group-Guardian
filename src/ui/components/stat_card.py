"""
Stat Card Component
===================
Dashboard statistic cards with animated counters
"""

import flet as ft
from ..theme import colors, radius, shadows, spacing, typography
from .glass_card import GlassCard


class StatCard(GlassCard):
    """
    A dashboard statistic card with icon, value, and label.
    Features:
    - Large animated number display
    - Icon with color accent
    - Subtitle/trend indicator
    - Click to navigate
    """
    
    def __init__(
        self,
        icon: str,
        value: str | int,
        label: str,
        subtitle: str = None,
        icon_color: str = colors.accent_primary,
        trend: str = None,  # "up" | "down" | None
        trend_value: str = None,  # e.g., "+5"
        on_click = None,
        **kwargs,
    ):
        self._icon = icon
        self._value = str(value)
        self._label = label
        self._subtitle = subtitle
        self._icon_color = icon_color
        self._trend = trend
        self._trend_value = trend_value
        
        content = self._build_content()
        
        super().__init__(
            content=content,
            on_click=on_click,
            hover_enabled=on_click is not None,
            **kwargs,
        )
    
    def _build_content(self) -> ft.Control:
        """Build the card content layout"""
        
        # Icon with glow background
        icon_container = ft.Container(
            content=ft.Icon(
                name=self._icon,
                size=24,
                color=self._icon_color,
            ),
            width=48,
            height=48,
            border_radius=radius.md,
            bgcolor=f"rgba({self._hex_to_rgb(self._icon_color)}, 0.15)",
            alignment=ft.alignment.center,
        )
        
        # Value (large number)
        value_text = ft.Text(
            self._value,
            size=36,
            weight=ft.FontWeight.W_700,
            color=colors.text_primary,
        )
        
        # Label
        label_text = ft.Text(
            self._label,
            size=typography.size_sm,
            color=colors.text_secondary,
        )
        
        # Main row with icon and stats
        main_content = ft.Row(
            controls=[
                icon_container,
                ft.Column(
                    controls=[
                        value_text,
                        label_text,
                    ],
                    spacing=0,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            spacing=spacing.md,
        )
        
        # Build subtitle/trend row if exists
        if self._subtitle or self._trend:
            trend_controls = []
            
            if self._trend and self._trend_value:
                trend_color = colors.success if self._trend == "up" else colors.danger
                trend_icon = ft.Icons.TRENDING_UP if self._trend == "up" else ft.Icons.TRENDING_DOWN
                
                trend_controls.append(
                    ft.Row(
                        controls=[
                            ft.Icon(trend_icon, size=14, color=trend_color),
                            ft.Text(
                                self._trend_value,
                                size=typography.size_xs,
                                color=trend_color,
                                weight=ft.FontWeight.W_500,
                            ),
                        ],
                        spacing=2,
                    )
                )
            
            if self._subtitle:
                trend_controls.append(
                    ft.Text(
                        self._subtitle,
                        size=typography.size_xs,
                        color=colors.text_tertiary,
                    )
                )
            
            subtitle_row = ft.Row(
                controls=trend_controls,
                spacing=spacing.sm,
            )
            
            return ft.Column(
                controls=[
                    main_content,
                    ft.Container(height=spacing.sm),
                    ft.Divider(height=1, color=colors.glass_border),
                    ft.Container(height=spacing.sm),
                    subtitle_row,
                ],
                spacing=0,
            )
        
        return main_content
    
    def _hex_to_rgb(self, hex_color: str) -> str:
        """Convert hex color to RGB values string"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return f"{r}, {g}, {b}"
        return "139, 92, 246"  # Default to purple
    
    def update_value(self, new_value: str | int):
        """Update the stat value with animation hint"""
        self._value = str(new_value)
        # Rebuild content
        self.content = self._build_content()
        self.update()
