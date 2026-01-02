"""
Tag Chip Component
==================
A reusable clickable tag chip with emoji and color.
Used in Watchlist and other views for displaying and selecting tags.
"""

import flet as ft
from ..theme import colors, radius, spacing, typography


class TagChip(ft.Container):
    """A clickable tag chip with emoji and color"""
    
    def __init__(
        self,
        tag_name: str,
        emoji: str = "🏷️",
        color: str = colors.accent_primary,
        selected: bool = False,
        on_click=None,
        removable: bool = False,
        on_remove=None,
        **kwargs
    ):
        self.tag_name = tag_name
        self.emoji = emoji
        self.tag_color = color
        self.selected = selected
        self._on_click = on_click
        self.removable = removable
        self._on_remove = on_remove
        
        content = self._build_content()
        
        super().__init__(
            content=content,
            padding=ft.padding.symmetric(horizontal=spacing.sm, vertical=4),
            border_radius=radius.full,
            bgcolor=f"{color}33" if selected else colors.bg_elevated,
            border=ft.border.all(2, color if selected else colors.glass_border),
            on_click=self._handle_click if on_click else None,
            on_hover=self._on_hover if on_click else None,
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            **kwargs
        )
    
    def _build_content(self):
        controls = [
            ft.Text(self.emoji, size=12),
            ft.Text(
                self.tag_name,
                size=typography.size_xs,
                color=colors.text_primary if self.selected else colors.text_secondary,
                weight=ft.FontWeight.W_500 if self.selected else ft.FontWeight.W_400,
            ),
        ]
        
        if self.removable:
            controls.append(
                ft.Container(
                    content=ft.Icon(ft.Icons.CLOSE, size=12, color=colors.text_tertiary),
                    on_click=self._handle_remove,
                    padding=ft.padding.only(left=4),
                )
            )
        
        return ft.Row(controls, spacing=4, tight=True)
    
    def _handle_click(self, e):
        if self._on_click:
            self._on_click(self.tag_name)
    
    def _handle_remove(self, e):
        if self._on_remove:
            e.control.data = self.tag_name  # Pass tag name
            self._on_remove(e)
    
    def _on_hover(self, e):
        if e.data == "true":
            self.bgcolor = f"{self.tag_color}44"
        else:
            self.bgcolor = f"{self.tag_color}33" if self.selected else colors.bg_elevated
        self.update()
    
    def set_selected(self, selected: bool):
        self.selected = selected
        self.bgcolor = f"{self.tag_color}33" if selected else colors.bg_elevated
        self.border = ft.border.all(2, self.tag_color if selected else colors.glass_border)
        self.content = self._build_content()
        self.update()
