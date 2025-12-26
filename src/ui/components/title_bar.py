"""
Custom Title Bar Component
===========================
Themed window controls for frameless window with version display
"""

import flet as ft
from ..theme import colors, spacing, typography, radius
from services.updater import UpdateService


class TitleBar(ft.Container):
    """Custom title bar with themed window controls and version indicator"""
    
    def __init__(
        self,
        title: str = "Group Guardian",
        icon_path: str = None,
        **kwargs,
    ):
        self._title = title
        self._icon_path = icon_path
        
        # Update state
        self._update_available = False
        self._update_version = None
        self._update_url = None
        self._release_notes = None
        
        # Version text - will pulse red when update available
        self._version_text = ft.Text(
            f"v{UpdateService.CURRENT_VERSION}",
            size=10,
            color=colors.text_tertiary,
            weight=ft.FontWeight.W_400,
        )
        
        # Version container (clickable when update available)
        self._version_container = ft.Container(
            content=self._version_text,
            padding=ft.padding.symmetric(horizontal=8, vertical=2),
            border_radius=radius.sm,
            on_click=self._on_version_click,
            tooltip="Click to check for updates",
        )
        
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
        
        # App title with version
        title_section = ft.Container(
            content=ft.Row(
                [
                    ft.Text(
                        self._title,
                        size=typography.size_sm,
                        weight=ft.FontWeight.W_500,
                        color=colors.text_secondary,
                    ),
                    self._version_container,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
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
    
    def set_update_available(self, version: str, url: str, notes: str = None):
        """Mark that an update is available - triggers pulsing red version"""
        self._update_available = True
        self._update_version = version
        self._update_url = url
        self._release_notes = notes
        
        # Update version text with pulsing red style
        self._version_text.value = f"v{UpdateService.CURRENT_VERSION} → {version}"
        self._version_text.color = colors.danger
        self._version_text.weight = ft.FontWeight.BOLD
        
        # Add pulsing border and background
        self._version_container.bgcolor = ft.colors.with_opacity(0.15, colors.danger)
        self._version_container.border = ft.border.all(1, colors.danger)
        self._version_container.tooltip = f"Update available! Click to download {version}"
        
        # Start pulsing animation
        self._version_container.animate_opacity = ft.Animation(800, ft.AnimationCurve.EASE_IN_OUT)
        
        if self.page:
            try:
                self.page.update()
                # Start pulse loop
                self.page.run_task(self._pulse_loop)
            except:
                pass
    
    async def _pulse_loop(self):
        """Animate pulsing effect for update indicator"""
        import asyncio
        while self._update_available and self.page:
            self._version_container.opacity = 0.6
            self._version_container.update()
            await asyncio.sleep(0.8)
            if not self._update_available:
                break
            self._version_container.opacity = 1.0
            self._version_container.update()
            await asyncio.sleep(0.8)
    
    def _on_version_click(self, e):
        """Handle click on version - show update dialog if available"""
        if self._update_available and self.page:
            from ui.dialogs.update_dialog import show_update_dialog
            show_update_dialog(
                self.page,
                self._update_version,
                self._update_url,
                self._release_notes
            )
        else:
            # Check for updates manually
            if self.page:
                self.page.run_task(self._check_updates)
    
    async def _check_updates(self):
        """Manually check for updates"""
        self._version_text.value = "Checking..."
        if self.page:
            self.page.update()
        
        is_available, version, url, notes = await UpdateService.check_for_updates()
        
        if is_available:
            self.set_update_available(version, url, notes)
        else:
            self._version_text.value = f"v{UpdateService.CURRENT_VERSION} ✓"
            self._version_text.color = colors.success
            if self.page:
                self.page.update()
                
            # Reset after 3 seconds
            import asyncio
            await asyncio.sleep(3)
            self._version_text.value = f"v{UpdateService.CURRENT_VERSION}"
            self._version_text.color = colors.text_tertiary
            if self.page:
                self.page.update()
    
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
