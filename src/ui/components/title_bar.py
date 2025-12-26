"""
Custom Title Bar Component
===========================
Themed window controls for frameless window
"""

import flet as ft
from ..theme import colors, spacing, typography, radius


class TitleBar(ft.Container):
    """Custom title bar with themed window controls"""
    
    def __init__(
        self,
        title: str = "Group Guardian",
        icon_path: str = None,
        **kwargs,
    ):
        self._title = title
        self._icon_path = icon_path
        
        content = self._build_title_bar()
        
        super().__init__(
            content=content,
            height=40,
            bgcolor=colors.bg_deepest,
            padding=ft.padding.symmetric(horizontal=spacing.sm),
            **kwargs,
        )
    
    def _build_title_bar(self) -> ft.Control:
        """Build the title bar content"""
        
        # App title only (left side) - also acts as drag area
        title_section = ft.Container(
            content=ft.Text(
                self._title,
                size=typography.size_sm,
                weight=ft.FontWeight.W_500,
                color=colors.text_secondary,
            ),
            expand=True,
        )
        
        # Window controls (right side)
        window_controls = ft.Row(
            controls=[
                # Minimize
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.REMOVE_ROUNDED,
                        size=16,
                        color=colors.text_secondary,
                    ),
                    width=40,
                    height=30,
                    alignment=ft.alignment.center,
                    border_radius=radius.sm,
                    on_click=self._minimize_window,
                    on_hover=self._on_button_hover,
                    data="normal",
                ),
                # Maximize/Restore
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.CROP_SQUARE_ROUNDED,
                        size=14,
                        color=colors.text_secondary,
                    ),
                    width=40,
                    height=30,
                    alignment=ft.alignment.center,
                    border_radius=radius.sm,
                    on_click=self._maximize_window,
                    on_hover=self._on_button_hover,
                    data="normal",
                ),
                # Close
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.CLOSE_ROUNDED,
                        size=16,
                        color=colors.text_secondary,
                    ),
                    width=40,
                    height=30,
                    alignment=ft.alignment.center,
                    border_radius=radius.sm,
                    on_click=self._close_window,
                    on_hover=self._on_close_hover,
                    data="close",
                ),
            ],
            spacing=0,
        )
        
        return ft.WindowDragArea(
            content=ft.Row(
                controls=[
                    title_section,
                    window_controls,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
        )
    
    def _minimize_window(self, e):
        """Minimize the window"""
        self.page.window.minimized = True
        self.page.update()
    
    def _maximize_window(self, e):
        """Toggle maximize/restore"""
        self.page.window.maximized = not self.page.window.maximized
        self.page.update()
    
    def _close_window(self, e):
        """Close the window"""
        self.page.window.close()
    
    def _on_button_hover(self, e):
        """Handle hover on normal buttons"""
        if e.data == "true":
            e.control.bgcolor = colors.bg_elevated
        else:
            e.control.bgcolor = None
        e.control.update()
    
    def _on_close_hover(self, e):
        """Handle hover on close button"""
        if e.data == "true":
            e.control.bgcolor = colors.danger
            e.control.content.color = colors.text_primary
        else:
            e.control.bgcolor = None
            e.control.content.color = colors.text_secondary
        e.control.update()
