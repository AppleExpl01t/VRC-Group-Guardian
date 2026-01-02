"""
Data Folder Setup Dialog
========================
First-launch dialog to let users configure where their data is stored.
"""

import flet as ft
from pathlib import Path
from utils.paths import get_default_data_dir, set_data_folder, is_data_folder_configured
from ui.theme import COLORS


class DataFolderSetupDialog(ft.AlertDialog):
    """Dialog for first-time data folder setup."""
    
    def __init__(self, on_complete: callable = None):
        self.on_complete = on_complete
        self._selected_path = str(get_default_data_dir())
        
        # Path display
        self.path_text = ft.Text(
            self._selected_path,
            size=12,
            color=COLORS["text_secondary"],
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        
        # Browse button
        self.browse_btn = ft.ElevatedButton(
            "Browse...",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self._on_browse,
            style=ft.ButtonStyle(
                bgcolor=COLORS["surface_bright"],
                color=COLORS["text_primary"],
            ),
        )
        
        # File picker reference
        self.file_picker = ft.FilePicker(
            on_result=self._on_folder_picked
        )
        
        super().__init__(
            modal=True,
            title=ft.Text(
                "📂 Choose Data Folder",
                size=20,
                weight=ft.FontWeight.BOLD,
                color=COLORS["accent_primary"],
            ),
            content=ft.Container(
                width=450,
                content=ft.Column(
                    [
                        ft.Text(
                            "Group Guardian needs a folder to store your data, "
                            "including cookies, user database, and cached images.",
                            size=14,
                            color=COLORS["text_primary"],
                        ),
                        ft.Container(height=10),
                        ft.Text(
                            "Data Folder Location:",
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=COLORS["text_secondary"],
                        ),
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Container(
                                        content=self.path_text,
                                        expand=True,
                                        padding=10,
                                        bgcolor=COLORS["surface"],
                                        border_radius=8,
                                        border=ft.border.all(2, COLORS["border"]),
                                    ),
                                    self.browse_btn,
                                ],
                                spacing=10,
                            ),
                            padding=ft.padding.only(top=5),
                        ),
                        ft.Container(height=10),
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=COLORS["text_muted"]),
                                    ft.Text(
                                        "This can be changed later in Settings.",
                                        size=11,
                                        color=COLORS["text_muted"],
                                        italic=True,
                                    ),
                                ],
                                spacing=5,
                            ),
                        ),
                    ],
                    spacing=5,
                    tight=True,
                ),
            ),
            actions=[
                ft.TextButton(
                    "Use Default",
                    on_click=self._on_use_default,
                    style=ft.ButtonStyle(color=COLORS["text_secondary"]),
                ),
                ft.ElevatedButton(
                    "Continue",
                    icon=ft.Icons.CHECK,
                    on_click=self._on_confirm,
                    style=ft.ButtonStyle(
                        bgcolor=COLORS["accent_primary"],
                        color=COLORS["text_primary"],
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=COLORS["background"],
            shape=ft.RoundedRectangleBorder(radius=16),
        )
    
    def _on_browse(self, e):
        """Open folder picker."""
        if self.page:
            # Add file picker to page overlay if not already there
            if self.file_picker not in self.page.overlay:
                self.page.overlay.append(self.file_picker)
                self.page.update()
            
            self.file_picker.get_directory_path(
                dialog_title="Select Data Folder",
                initial_directory=str(Path(self._selected_path).parent),
            )
    
    def _on_folder_picked(self, e: ft.FilePickerResultEvent):
        """Handle folder selection."""
        if e.path:
            self._selected_path = e.path
            self.path_text.value = self._selected_path
            if self.page:
                self.page.update()
    
    def _on_use_default(self, e):
        """Use the default path."""
        self._selected_path = str(get_default_data_dir())
        self._apply_and_close()
    
    def _on_confirm(self, e):
        """Confirm the selected path."""
        self._apply_and_close()
    
    def _apply_and_close(self):
        """Apply the selected path and close dialog."""
        # Save the data folder location
        set_data_folder(self._selected_path)
        
        # Close dialog using modern API
        if self.page:
            self.page.close(self)
        
        # Callback
        if self.on_complete:
            self.on_complete(self._selected_path)


def show_data_folder_setup(page: ft.Page, on_complete: callable = None):
    """
    Show the data folder setup dialog if not configured.
    Returns True if dialog was shown, False if already configured.
    """
    if is_data_folder_configured():
        return False
    
    dialog = DataFolderSetupDialog(on_complete=on_complete)
    page.overlay.append(dialog.file_picker)
    page.open(dialog)  # Use modern Flet API
    return True
