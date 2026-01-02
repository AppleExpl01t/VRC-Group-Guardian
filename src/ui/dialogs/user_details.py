import flet as ft
from ..theme import colors, radius, spacing, typography
from ..components.neon_button import NeonButton
from ..utils.responsive import is_mobile_platform
from services.watchlist_service import get_watchlist_service
import webbrowser

def show_user_details_dialog(page: ft.Page, user_data: dict, api, db, group_id: str = None, on_update=None):
    """
    Shows a comprehensive user details dialog with moderation and database controls.
    
    Args:
        page: Flet page instance
        user_data: User dictionary (from API)
        api: VRChatAPI instance
        db: DatabaseService instance
        group_id: Optional group ID for moderation context (Kick/Ban)
        on_update: Callback function to run after database changes
    """
    
    user_id = user_data.get("id") or user_data.get("userId")
    if not user_id:
        return
    
    # Initial Data (might be partial)
    display_name = user_data.get("displayName") or user_data.get("name", "Unknown")
    
    # Check local_pfp first (cached by UserCard), then API image fields
    # VRChat API returns images in these fields with different availability
    thumbnail = (
        user_data.get("local_pfp") or  # Already cached locally by UserCard
        user_data.get("profilePicOverride") or  # Custom profile pic (most accurate)
        user_data.get("userIcon") or  # User icon
        user_data.get("thumbnailUrl") or  # Member list thumbnail
        user_data.get("currentAvatarThumbnailImageUrl") or  # Avatar thumbnail
        user_data.get("currentAvatarImageUrl") or  # Full avatar image
        user_data.get("imageUrl")  # Generic image field
    )
    
    # User status information
    user_status = user_data.get("status", "offline")
    status_description = user_data.get("statusDescription", "")
    
    # Status color mapping
    status_colors = {
        "active": "#4caf50",  # Green - Online
        "join me": "#2196f3",  # Blue
        "ask me": "#ff9800",  # Orange
        "busy": "#f44336",  # Red
        "offline": "#9e9e9e",  # Gray
    }
    status_color = status_colors.get(user_status.lower(), "#9e9e9e")
    
    # Database State - use centralized watchlist service
    watchlist_svc = get_watchlist_service()
    user_status_data = watchlist_svc.check_and_record_user(user_id, display_name)
    current_note = user_status_data.get("note", "") or ""
    is_watchlisted = user_status_data.get("is_watchlisted", False)
    
    # Controls (use refs for updating)
    # Use ft.Image in a circular container (same approach as UserCard which works correctly)
    avatar_size = 48  # Reduced from 60
    avatar_radius = 24
    
    avatar_image = ft.Image(
        src=thumbnail if thumbnail else "",
        width=avatar_size,
        height=avatar_size,
        fit=ft.ImageFit.COVER,
        border_radius=avatar_radius,  # Make it circular
        opacity=1 if thumbnail else 0,
    )
    
    avatar_fallback = ft.Text(display_name[:1].upper(), size=20, weight=ft.FontWeight.BOLD, color=colors.text_primary)
    
    avatar_container = ft.Container(
        content=avatar_image if thumbnail else avatar_fallback,
        width=avatar_size,
        height=avatar_size,
        border_radius=avatar_radius,
        bgcolor=colors.accent_primary,
        alignment=ft.alignment.center,
    )
    
    status_indicator = ft.Container(
        width=10,  # Reduced from 12
        height=10,
        border_radius=5,
        bgcolor=status_color,
        border=ft.border.all(2, colors.bg_elevated),
    )
    
    status_text = ft.Text(
        status_description if status_description else (f"Status: {user_status.title()}" if user_status != "offline" else "Offline"),
        size=typography.size_xs,
        color=status_color,
        italic=True,
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    
    note_field = ft.TextField(
        label="Moderator Note",
        value=current_note,
        multiline=True,
        max_lines=3,
        text_size=typography.size_xs,  # Reduced from sm
        bgcolor=colors.bg_base,
        border_color=colors.glass_border,
        height=60,  # Explicit compact height
    )
    
    # Handler for immediate watchlist toggle - uses centralized service
    def on_watchlist_change(e):
        # Use watchlist service for centralized management and event publishing
        watchlist_svc.toggle_watchlist(user_id, e.control.value, username=display_name)
        
        # Visual feedback
        msg = "Added to watchlist" if e.control.value else "Removed from watchlist"
        page.snack_bar = ft.SnackBar(content=ft.Text(msg), bgcolor=colors.success if e.control.value else colors.text_tertiary)
        page.snack_bar.open = True
        page.update()
        
        if on_update:
            on_update()

    watchlist_switch = ft.Switch(
        label="Watchlist (Alert on join)",
        label_style=ft.TextStyle(size=typography.size_xs),  # Compact label
        value=is_watchlisted,
        active_color=colors.accent_primary,
        on_change=on_watchlist_change,
        scale=0.8,  # Scale down
    )
    
    bio_text = ft.Text("Loading full profile...", color=colors.text_tertiary, size=typography.size_xs) # Reduced
    tags_row = ft.Row(wrap=True, spacing=2) # Reduced spacing
    
    # Save handler - uses centralized watchlist service
    def save_db_changes(e):
        note = note_field.value.strip()
        wl = watchlist_switch.value
        
        # Use watchlist service for centralized management
        watchlist_svc.set_user_note(user_id, note, username=display_name)
        watchlist_svc.toggle_watchlist(user_id, wl, username=display_name)
        
        page.open(ft.SnackBar(content=ft.Text(f"Saved data for {display_name}"), bgcolor=colors.success))
        
        if on_update:
            on_update()
            
    # Moderation Handlers
    def confirm_ban(e):
        page.close(dlg)
        _show_ban_confirm(page, user_data, group_id, api, on_update)
        
    def confirm_kick(e):
        page.close(dlg)
        _show_kick_confirm(page, user_data, group_id, api, on_update)

    def open_web_profile(e):
        webbrowser.open(f"https://vrchat.com/home/user/{user_id}")

    # Build Content
    content = ft.Column([
        # Header with Avatar and Status
        ft.Row([
            ft.Stack([
                avatar_container,
                ft.Container(
                    content=status_indicator,
                    alignment=ft.alignment.bottom_right,
                    width=avatar_size,
                    height=avatar_size,
                ),
            ], width=avatar_size, height=avatar_size),
            ft.Container(width=spacing.sm),
            ft.Column([
                ft.Text(display_name, size=typography.size_base, weight=ft.FontWeight.BOLD), # Reduced from lg
                ft.Text(f"ID: {user_id}", size=9, color=colors.text_tertiary, font_family="Consolas", selectable=True), # Reduced
                status_text,
                tags_row,
            ], spacing=1, expand=True), # Reduced spacing
        ]),
        
        ft.Divider(color=colors.glass_border, height=spacing.sm),
        
        # Database Section
        ft.Container(
            content=ft.Column([
                ft.Text("Local Database", size=typography.size_xs, weight=ft.FontWeight.BOLD, color=colors.text_secondary),
                watchlist_switch,
                note_field,
                NeonButton("Save Local Data", icon=ft.Icons.SAVE, on_click=save_db_changes, height=28, variant="secondary", key="save_user_data_btn"), # Reduced height
            ], spacing=spacing.xs),
            bgcolor=colors.bg_base,
            border_radius=radius.md,
            padding=spacing.xs, # Reduced padding
            key="user_details_db_panel"
        ),
        
        ft.Container(height=spacing.xs),
        
        # Bio Section
        ft.Text("Biography", size=typography.size_xs, weight=ft.FontWeight.BOLD, color=colors.text_secondary),
        ft.Container(
            content=bio_text,
            bgcolor=colors.bg_base,
            border_radius=radius.md,
            padding=spacing.xs,
            border=ft.border.all(2, colors.glass_border),
            height=60, # Reduced height
        ),
        
        ft.Container(height=spacing.sm),
        
        # Actions
        ft.Row([
            NeonButton("Web Profile", icon=ft.Icons.OPEN_IN_NEW, on_click=open_web_profile, width=120, height=32, variant="secondary"),
        ], alignment=ft.MainAxisAlignment.CENTER),
        
        
    ], tight=True, width=320 if is_mobile_platform(page) else 400, scroll=ft.ScrollMode.AUTO)

    # Group Specific Actions
    if group_id:
        content.controls.append(ft.Container(height=spacing.sm))
        content.controls.append(ft.Divider(color=colors.glass_border))
        content.controls.append(ft.Text("Group Moderation", size=typography.size_xs, weight=ft.FontWeight.BOLD, color=colors.danger))
        content.controls.append(ft.Container(height=spacing.xs))
        content.controls.append(ft.Row([
             NeonButton("Kick Member", icon=ft.Icons.REMOVE_CIRCLE_OUTLINE, variant="warning", on_click=confirm_kick, expand=True),
             ft.Container(width=spacing.xs),
             NeonButton("Ban Member", icon=ft.Icons.BLOCK, variant="danger", on_click=confirm_ban, expand=True),
        ]))

    dlg = ft.AlertDialog(
        content=content,
        bgcolor=colors.bg_elevated,
        shape=ft.RoundedRectangleBorder(radius=radius.lg),
        actions=[ft.TextButton("Close", on_click=lambda e: page.close(dlg))],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    
    page.open(dlg)
    
    # Async Fetch Logic
    async def fetch_full_details():
        try:
            full_user = await api.get_user(user_id)
            if full_user:
                # Update Bio
                bio = full_user.get("bio", "").strip() or "No biography."
                bio_text.value = bio
                bio_text.color = colors.text_primary
                
                # Update Tags (pass full_user for age verification check)
                tags = full_user.get("tags", [])
                update_tags_ui(tags_row, tags, full_user)
                
                # Update status from full profile
                new_status = full_user.get("status", "offline")
                new_status_desc = full_user.get("statusDescription", "")
                new_status_color = status_colors.get(new_status.lower(), "#9e9e9e")
                
                status_indicator.bgcolor = new_status_color
                status_text.value = new_status_desc if new_status_desc else (f"Status: {new_status.title()}" if new_status != "offline" else "Offline")
                status_text.color = new_status_color
                
                # Update avatar image from full profile
                best_img = (
                    full_user.get("profilePicOverride") or
                    full_user.get("userIcon") or
                    full_user.get("currentAvatarThumbnailImageUrl") or
                    full_user.get("currentAvatarImageUrl")
                )
                
                if best_img:
                    # Try to cache the image locally for authenticated access
                    cached_path = await api.cache_user_image(full_user)
                    if cached_path:
                        # Update the ft.Image src and make it visible
                        avatar_image.src = cached_path
                        avatar_image.opacity = 1
                        avatar_container.content = avatar_image
                    else:
                        # Use direct URL if caching failed
                        avatar_image.src = best_img
                        avatar_image.opacity = 1
                        avatar_container.content = avatar_image
                
                dlg.update()
        except Exception as e:
            bio_text.value = f"Error loading profile: {e}"
            bio_text.color = colors.danger
            dlg.update()
            
    page.run_task(fetch_full_details)

def update_tags_ui(row, tags, full_user=None):
    """Helper to render tags including trust ranks and age verification"""
    controls = []
    
    # Known trust tags
    trust_tags = {
        "system_trust_legend": ("Legendary", colors.warning),
        "system_trust_veteran": ("Veteran", colors.warning),
        "system_trust_trusted": ("Trusted", "#a66efa"), # Purple
        "system_trust_known": ("Known", "#ff7b42"), # Orange
        "system_trust_basic": ("User", "#2bcf5c"), # Green
        "system_trust_new": ("New", "#1e88e5"), # Blue
        "system_troll": ("Nuisance", colors.danger),
    }
    
    for tag in tags:
        if tag in trust_tags:
            label, color = trust_tags[tag]
            controls.append(
                ft.Container(
                    content=ft.Text(label, size=10, weight=ft.FontWeight.BOLD, color=colors.bg_deepest),
                    bgcolor=color,
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    border_radius=4,
                )
            )
    
    # Age Verification Badge
    # Check ageVerificationStatus field (from full_user) or tag
    age_is_18_plus = False
    
    if full_user:
        age_status = full_user.get("ageVerificationStatus", "")
        age_verified_flag = full_user.get("ageVerified", False)
        age_is_18_plus = age_verified_flag and (age_status == "18+")
    
    # Also check for system tag as fallback
    if not age_is_18_plus and "system_age_verified" in tags:
        age_is_18_plus = True
    
    if age_is_18_plus:
        controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.SMART_BUTTON, size=8, color=colors.text_primary),
                        ft.Text("18+", size=9, weight=ft.FontWeight.BOLD, color=colors.text_primary),
                    ],
                    spacing=2,
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=colors.bg_elevated_2,  # Consistent style
                padding=ft.padding.symmetric(horizontal=5, vertical=2),
                border_radius=4,
                border=ft.border.all(1, colors.text_tertiary),
                tooltip="Age Verified 18+",
            )
        )
    
    if not controls:
        controls.append(ft.Text("No Trust Rank", size=10, color=colors.text_tertiary))
        
    row.controls = controls

def _show_ban_confirm(page, user, group_id, api, on_update):
    # Reuse existing ban logic pattern
    def do_ban(e):
        page.close(confirm_dlg)
        async def execute():
            success = await api.ban_user(group_id, user.get("id"))
            if success:
                page.open(ft.SnackBar(content=ft.Text(f"Banned {user.get('displayName')}"), bgcolor=colors.success))
                if on_update: on_update()
            else:
                page.open(ft.SnackBar(content=ft.Text("Ban failed"), bgcolor=colors.danger))
        page.run_task(execute)
        
    confirm_dlg = ft.AlertDialog(
        title=ft.Text("Confirm Ban"),
        content=ft.Text(f"Ban {user.get('displayName')} from the group?"),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: page.close(confirm_dlg)),
            ft.TextButton("Ban", style=ft.ButtonStyle(color=colors.danger), on_click=do_ban)
        ],
        bgcolor=colors.bg_elevated,
    )
    page.open(confirm_dlg)

def _show_kick_confirm(page, user, group_id, api, on_update):
    def do_kick(e):
        page.close(confirm_dlg)
        async def execute():
            success = await api.kick_user(group_id, user.get("id"))
            if success:
                page.open(ft.SnackBar(content=ft.Text(f"Kicked {user.get('displayName')}"), bgcolor=colors.success))
                if on_update: on_update()
            else:
                page.open(ft.SnackBar(content=ft.Text("Kick failed"), bgcolor=colors.danger))
        page.run_task(execute)
        
    confirm_dlg = ft.AlertDialog(
        title=ft.Text("Confirm Kick"),
        content=ft.Text(f"Kick {user.get('displayName')} from the group?"),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: page.close(confirm_dlg)),
            ft.TextButton("Kick", style=ft.ButtonStyle(color=colors.warning), on_click=do_kick)
        ],
        bgcolor=colors.bg_elevated,
    )
    page.open(confirm_dlg)
