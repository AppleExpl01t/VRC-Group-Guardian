"""
Reusable Confirmation Dialog Component
======================================
A standardized dialog for confirmation actions to reduce code duplication.
"""

import flet as ft
from ..theme import colors, radius, spacing, typography
from ..components.neon_button import NeonButton


def show_confirm_dialog(
    page: ft.Page,
    title: str,
    message: str,
    on_confirm,
    confirm_text: str = "Confirm",
    cancel_text: str = "Cancel",
    variant: str = "danger",
    icon: str = None,
    details_content: ft.Control = None,
    warning_text: str = None,
):
    """
    Show a standardized confirmation dialog.
    
    Args:
        page: The Flet page to open the dialog on
        title: Dialog title
        message: Main message/description
        on_confirm: Async or sync callback when user confirms (no args)
        confirm_text: Text for confirm button (default: "Confirm")
        cancel_text: Text for cancel button (default: "Cancel")
        variant: Button variant - "danger", "primary", "secondary" (default: "danger")
        icon: Optional icon for the title (ft.Icons.* value)
        details_content: Optional additional content to show (e.g., user info card)
        warning_text: Optional warning message to show (with ⚠️ icon)
    """
    
    def close_dlg(e):
        page.close(dlg)
    
    def do_confirm(e):
        page.close(dlg)
        # Handle both sync and async callbacks
        result = on_confirm()
        if hasattr(result, '__await__'):
            page.run_task(lambda: result)
    
    # Determine icon and color based on variant
    icon_color = colors.danger if variant == "danger" else colors.accent_primary
    default_icon = ft.Icons.WARNING_ROUNDED if variant == "danger" else ft.Icons.INFO_ROUNDED
    title_icon = icon or default_icon
    
    # Build content column
    content_controls = [
        ft.Text(message, color=colors.text_primary, size=typography.size_base),
    ]
    
    if details_content:
        content_controls.extend([
            ft.Container(height=spacing.sm),
            details_content,
        ])
    
    if warning_text:
        content_controls.extend([
            ft.Container(height=spacing.md),
            ft.Text(f"⚠️ {warning_text}", color=colors.warning, size=typography.size_sm),
        ])
    
    # Map variant to NeonButton variant
    button_variant = {
        "danger": NeonButton.VARIANT_DANGER,
        "primary": NeonButton.VARIANT_PRIMARY,
        "secondary": NeonButton.VARIANT_SECONDARY,
    }.get(variant, NeonButton.VARIANT_DANGER)
    
    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon(title_icon, color=icon_color, size=28),
            ft.Container(width=spacing.sm),
            ft.Text(title, weight=ft.FontWeight.W_600),
        ]),
        content=ft.Column(content_controls, tight=True, width=400),
        actions=[
            ft.TextButton(cancel_text, on_click=close_dlg),
            NeonButton(
                text=confirm_text,
                variant=button_variant,
                on_click=do_confirm,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=colors.bg_elevated,
        shape=ft.RoundedRectangleBorder(radius=radius.lg),
    )
    
    page.open(dlg)
    return dlg


def show_loading_dialog(page: ft.Page, message: str = "Loading..."):
    """
    Show a non-dismissable loading dialog.
    
    Returns the dialog so it can be closed later with page.close(dlg).
    """
    dlg = ft.AlertDialog(
        modal=True,
        content=ft.Row([
            ft.ProgressRing(width=20, height=20, stroke_width=2, color=colors.accent_primary),
            ft.Container(width=spacing.md),
            ft.Text(message, color=colors.text_primary),
        ], alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=colors.bg_elevated,
        shape=ft.RoundedRectangleBorder(radius=radius.lg),
    )
    
    page.open(dlg)
    return dlg
