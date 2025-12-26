"""
Update Available Dialog
========================
Dialog shown when a new version is available.
"""

import flet as ft
from ui.theme import COLORS
from services.updater import UpdateService


class UpdateDialog(ft.AlertDialog):
    """Dialog for downloading and applying updates."""
    
    def __init__(self, version_tag: str, asset_url: str, release_notes: str = None, on_close: callable = None):
        self.version_tag = version_tag
        self.asset_url = asset_url
        self.release_notes = release_notes or "No release notes available."
        self.on_close_callback = on_close
        
        # Progress bar for download
        self.progress_bar = ft.ProgressBar(
            width=400,
            value=0,
            visible=False,
            color=COLORS["accent_primary"],
            bgcolor=COLORS["surface"],
        )
        
        self.progress_text = ft.Text(
            "",
            size=12,
            color=COLORS["text_secondary"],
            visible=False,
        )
        
        self.download_btn = ft.ElevatedButton(
            "Download Update",
            icon=ft.icons.DOWNLOAD,
            on_click=self._on_download,
            style=ft.ButtonStyle(
                bgcolor=COLORS["accent_primary"],
                color=COLORS["text_primary"],
            ),
        )
        
        self.close_btn = ft.TextButton(
            "Later",
            on_click=self._on_close,
            style=ft.ButtonStyle(color=COLORS["text_secondary"]),
        )
        
        super().__init__(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.icons.SYSTEM_UPDATE, color=COLORS["success"], size=28),
                    ft.Text(
                        "Update Available!",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["success"],
                    ),
                ],
                spacing=10,
            ),
            content=ft.Container(
                width=450,
                content=ft.Column(
                    [
                        ft.Text(
                            f"A new version is available: {version_tag}",
                            size=16,
                            color=COLORS["text_primary"],
                            weight=ft.FontWeight.W_500,
                        ),
                        ft.Container(height=10),
                        ft.Text(
                            "What's New:",
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=COLORS["text_secondary"],
                        ),
                        ft.Container(
                            content=ft.Markdown(
                                self.release_notes[:500] + ("..." if len(self.release_notes) > 500 else ""),
                                selectable=True,
                                extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                            ),
                            bgcolor=COLORS["surface"],
                            border_radius=8,
                            padding=10,
                            max_height=150,
                        ),
                        ft.Container(height=10),
                        self.progress_bar,
                        self.progress_text,
                    ],
                    spacing=5,
                    tight=True,
                ),
            ),
            actions=[
                self.close_btn,
                self.download_btn,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=COLORS["background"],
            shape=ft.RoundedRectangleBorder(radius=16),
        )
    
    def _on_download(self, e):
        """Start downloading the update."""
        self.download_btn.disabled = True
        self.download_btn.text = "Downloading..."
        self.close_btn.disabled = True
        self.progress_bar.visible = True
        self.progress_text.visible = True
        self.progress_text.value = "Starting download..."
        if self.page:
            self.page.update()
        
        # Start download in background
        if self.page:
            self.page.run_task(self._do_download)
    
    async def _do_download(self):
        """Download the update file."""
        try:
            def progress_callback(progress: float):
                self.progress_bar.value = progress
                self.progress_text.value = f"Downloading... {int(progress * 100)}%"
                if self.page:
                    self.page.update()
            
            # Download the update
            new_exe_path = await UpdateService.download_update(
                self.asset_url,
                progress_callback=progress_callback
            )
            
            self.progress_text.value = "Download complete! Applying update..."
            self.progress_bar.value = 1.0
            if self.page:
                self.page.update()
            
            # Apply the update (this will exit the app)
            import asyncio
            await asyncio.sleep(1)  # Small delay for user to see message
            UpdateService.apply_update(new_exe_path)
            
        except Exception as ex:
            self.progress_text.value = f"Download failed: {str(ex)}"
            self.progress_text.color = COLORS["danger"]
            self.download_btn.disabled = False
            self.download_btn.text = "Retry Download"
            self.close_btn.disabled = False
            if self.page:
                self.page.update()
    
    def _on_close(self, e):
        """Close the dialog."""
        self.open = False
        if self.page:
            self.page.update()
        if self.on_close_callback:
            self.on_close_callback()


def show_update_dialog(page: ft.Page, version_tag: str, asset_url: str, release_notes: str = None):
    """Show the update available dialog."""
    dialog = UpdateDialog(version_tag, asset_url, release_notes)
    page.dialog = dialog
    dialog.open = True
    page.update()
    return dialog
