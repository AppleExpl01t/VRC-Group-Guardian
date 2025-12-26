import flet as ft
from ..theme import colors, radius, spacing, typography
from ..components.neon_button import NeonButton
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
    print(f"DEBUG: Opening Details Dialog for {user_data.get('displayName')} ({user_id})")
    if not user_id:
        print("DEBUG: No User ID found, aborting dialog.")
        return
    
    # Initial Data (might be partial)
    display_name = user_data.get("displayName") or user_data.get("name", "Unknown")
    thumbnail = user_data.get("local_pfp") or user_data.get("currentAvatarThumbnailImageUrl") or user_data.get("userIcon")
    
    # Database State
    db_entry = db.get_user_data(user_id) if db else None
    current_note = db_entry.get("note", "") if db_entry else ""
    is_watchlisted = db_entry.get("is_watchlisted", False) if db_entry else False
    
    # Controls
    note_field = ft.TextField(
        label="Moderator Note",
        value=current_note,
        multiline=True,
        max_lines=3,
        text_size=typography.size_sm,
        bgcolor=colors.bg_base,
        border_color=colors.glass_border,
    )
    
    watchlist_switch = ft.Switch(
        label="Watchlist (Alert on join)",
        value=is_watchlisted,
        active_color=colors.accent_primary,
    )
    
    bio_text = ft.Text("Loading full profile...", color=colors.text_tertiary, size=typography.size_sm)
    tags_row = ft.Row(wrap=True, spacing=4)
    
    # Save handler
    def save_db_changes(e):
        if not db: return
        
        note = note_field.value.strip()
        wl = watchlist_switch.value
        
        db.set_user_note(user_id, note)
        db.toggle_watchlist(user_id, wl)
        
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
        # Header with Avatar
        ft.Row([
            ft.CircleAvatar(
                foreground_image_src=thumbnail if thumbnail else None,
                content=ft.Text(display_name[:1].upper()) if not thumbnail else None,
                radius=30,
            ),
            ft.Container(width=spacing.sm),
            ft.Column([
                ft.Text(display_name, size=typography.size_lg, weight=ft.FontWeight.BOLD),
                ft.Text(f"ID: {user_id}", size=10, color=colors.text_tertiary, font_family="Consolas", selectable=True),
                tags_row,
            ], spacing=2),
        ]),
        
        ft.Divider(color=colors.glass_border),
        
        # Database Section
        ft.Container(
            content=ft.Column([
                ft.Text("Local Database", size=typography.size_xs, weight=ft.FontWeight.BOLD, color=colors.text_secondary),
                watchlist_switch,
                note_field,
                NeonButton("Save Local Data", icon=ft.Icons.SAVE, on_click=save_db_changes, height=30, variant="secondary", key="save_user_data_btn"),
            ], spacing=spacing.sm),
            bgcolor=colors.bg_base,
            border_radius=radius.md,
            padding=spacing.sm,
            key="user_details_db_panel"
        ),
        
        ft.Container(height=spacing.sm),
        
        # Bio Section
        ft.Text("Biography", size=typography.size_xs, weight=ft.FontWeight.BOLD, color=colors.text_secondary),
        ft.Container(
            content=bio_text,
            bgcolor=colors.bg_base,
            border_radius=radius.md,
            padding=spacing.sm,
            border=ft.border.all(1, colors.glass_border),
            height=80, # Fixed scrollable height
        ),
        
        ft.Container(height=spacing.md),
        
        # Actions
        ft.Row([
            NeonButton("Web Profile", icon=ft.Icons.OPEN_IN_NEW, on_click=open_web_profile, width=150, variant="secondary"),
        ], alignment=ft.MainAxisAlignment.CENTER),
        
    ], tight=True, width=450, scroll=ft.ScrollMode.AUTO)

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
                
                # Update Tags
                tags = full_user.get("tags", [])
                update_tags_ui(tags_row, tags)
                
                # Check cache for better image
                path = await api.cache_user_image(full_user)
                if path:
                    # Not easily updating the avatar in this simple fn setup without ref, 
                    # but typically cached images load from file system next time.
                    pass
                
                dlg.update()
        except Exception as e:
            bio_text.value = f"Error loading profile: {e}"
            dlg.update()
            
    page.run_task(fetch_full_details)

def update_tags_ui(row, tags):
    """Helper to render tags"""
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
