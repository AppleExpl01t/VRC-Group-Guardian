"""
Watchlist Management View
=========================
Manage watchlisted users, tags, and alert settings.
"""

import flet as ft
from datetime import datetime
from typing import Optional, List, Dict
from ..theme import colors, radius, spacing, typography, shadows
from ..components.glass_card import GlassCard, GlassPanel
from ..components.neon_button import NeonButton, IconButton
from ..components.user_card import UserCard
from ..dialogs.user_details import show_user_details_dialog
from services.database import get_database
from services.watchlist_alerts import get_alert_service, DEFAULT_TAGS


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
            border=ft.border.all(1, color if selected else colors.glass_border),
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
        self.border = ft.border.all(1, self.tag_color if selected else colors.glass_border)
        self.content = self._build_content()
        self.update()





class WatchlistView(ft.Container):
    """
    Main watchlist management view.
    Features:
    - View all watchlisted users
    - Add/edit/remove users
    - Manage tags
    - Configure alert settings
    """
    
    def __init__(self, api=None, on_navigate=None, **kwargs):
        self.api = api
        self.on_navigate = on_navigate
        self._db = get_database()
        self._alert_service = get_alert_service()
        
        # State
        self._users = []
        self._search_query = ""
        self._selected_tag_filter = None
        
        # Tag info lookup
        self._tag_info = {t["name"]: t for t in DEFAULT_TAGS}
        
        # UI Refs
        self._user_list = None
        self._stats_row = None
        self._search_field = None
        
        content = self._build_view()
        
        super().__init__(
            content=content,
            expand=True,
            padding=spacing.lg,
            **kwargs
        )
    
    def did_mount(self):
        """Load watchlist data on mount"""
        self._load_watchlist()
    
    def _load_watchlist(self):
        """Load all watchlisted users from database"""
        self._users = self._db.get_watchlisted_users()
        self._update_stats()
        self._render_user_list()
    
    def _update_stats(self):
        """Update statistics display"""
        if not self._stats_row:
            return
        
        # Count users by tag
        tag_counts = {}
        for user in self._users:
            tags = user.get("tags", [])
            if isinstance(tags, str):
                import json
                try:
                    tags = json.loads(tags)
                except:
                    tags = []
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Get top 3 tags
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        stats = []
        
        # Total count
        stats.append(self._build_stat_card(
            icon=ft.Icons.VISIBILITY_ROUNDED,
            value=str(len(self._users)),
            label="Monitored",
            color=colors.accent_primary
        ))
        
        # Top tag stats
        for tag_name, count in top_tags:
            info = self._tag_info.get(tag_name, {"emoji": "🏷️", "color": colors.accent_secondary})
            stats.append(self._build_stat_card(
                icon=None,
                emoji=info.get("emoji", "🏷️"),
                value=str(count),
                label=tag_name,
                color=info.get("color", colors.accent_secondary)
            ))
        
        # Alert status
        alert_enabled = self._alert_service.enabled if self._alert_service else False
        stats.append(self._build_stat_card(
            icon=ft.Icons.NOTIFICATIONS_ACTIVE_ROUNDED if alert_enabled else ft.Icons.NOTIFICATIONS_OFF_ROUNDED,
            value="ON" if alert_enabled else "OFF",
            label="Alerts",
            color=colors.success if alert_enabled else colors.text_tertiary
        ))
        
        self._stats_row.controls = stats
        self._stats_row.update()
    
    def _build_stat_card(self, icon=None, emoji=None, value="0", label="", color=colors.accent_primary):
        """Build a small stat card"""
        icon_widget = None
        if emoji:
            icon_widget = ft.Text(emoji, size=20)
        elif icon:
            icon_widget = ft.Icon(icon, size=20, color=color)
        
        return GlassCard(
            content=ft.Column([
                icon_widget if icon_widget else ft.Container(),
                ft.Text(value, size=typography.size_xl, weight=ft.FontWeight.W_700, color=color),
                ft.Text(label, size=typography.size_xs, color=colors.text_secondary),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
            padding=spacing.md,
            width=120,
            height=100,
        )
    
    def _render_user_list(self):
        """Render the user list with current filters"""
        if not self._user_list:
            return
        
        # Apply search filter
        filtered = self._users
        if self._search_query:
            query = self._search_query.lower()
            filtered = [u for u in filtered if 
                        query in u.get("username", "").lower() or 
                        query in u.get("user_id", "").lower()]
        
        # Apply tag filter
        if self._selected_tag_filter:
            def has_tag(user):
                tags = user.get("tags", [])
                if isinstance(tags, str):
                    import json
                    try:
                        tags = json.loads(tags)
                    except:
                        tags = []
                return self._selected_tag_filter in tags
            filtered = [u for u in filtered if has_tag(u)]
        
        if not filtered:
            self._user_list.controls = [
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.PERSON_OFF_ROUNDED, size=48, color=colors.text_tertiary),
                        ft.Text(
                            "No watchlisted users" if not self._search_query else "No users match your search",
                            color=colors.text_secondary,
                            size=typography.size_base,
                        ),
                        NeonButton(
                            "Add First User",
                            icon=ft.Icons.PERSON_ADD_ROUNDED,
                            variant=NeonButton.VARIANT_PRIMARY,
                            on_click=lambda e: self._show_add_dialog(),
                        ) if not self._search_query else ft.Container(),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=spacing.md),
                    alignment=ft.alignment.center,
                    expand=True,
                    padding=spacing.xxl,
                )
            ]
        else:
            cards = []
            for user in filtered:
                uid = user.get("user_id", "")
                username = user.get("current_username") or user.get("username", "Unknown")
                sightings = user.get("sightings_count", 0)
                last_seen = user.get("last_seen", "Never")
                
                # Construct data for UserCard
                user_data = {
                    "id": uid,
                    "displayName": username,
                    "name": username,
                    "tags": user.get("tags", []),
                    "note": user.get("note")
                    # Fallback icon/image logic is handled by UserCard via API if available
                }
                
                # Actions
                actions = [
                    IconButton(
                        icon=ft.Icons.EDIT_ROUNDED,
                        tooltip="Edit Watchlist Entry",
                        on_click=lambda e, u=uid: self._show_edit_dialog(u) # Keep legacy edit dialog for now
                    ),
                    ft.Container(width=spacing.xs),
                    IconButton(
                        icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                        icon_color=colors.danger,
                        tooltip="Remove from Watchlist",
                        on_click=lambda e, u=uid, n=username: self._confirm_remove(u, n)
                    )
                ]
                
                cards.append(
                    UserCard(
                        user_data=user_data,
                        api=self.api,
                        db=self._db,
                        subtitle=f"Seen: {last_seen} • Sightings: {sightings}",
                        trailing_controls=actions,
                        on_click=lambda e, u=user_data: show_user_details_dialog(
                            self.page, u, self.api, self._db, on_update=lambda: self.page.run_task(self._load_watchlist)
                        )
                    )
                )
            self._user_list.controls = cards
        
        self._user_list.update()
    
    def _handle_search(self, e):
        """Handle search input"""
        self._search_query = e.control.value
        self._render_user_list()
    
    def _handle_tag_filter(self, tag_name: str):
        """Handle tag filter selection"""
        if self._selected_tag_filter == tag_name:
            self._selected_tag_filter = None  # Toggle off
        else:
            self._selected_tag_filter = tag_name
        self._render_user_list()
    
    def _show_add_dialog(self):
        """Show dialog to add a user to the watchlist"""
        # Search field for VRChat user lookup
        search_field = ft.TextField(
            label="Search VRChat User",
            hint_text="Enter username to search...",
            border_color=colors.glass_border,
            focused_border_color=colors.accent_primary,
            suffix=ft.IconButton(
                icon=ft.Icons.SEARCH,
                on_click=lambda e: search_user(e),
            ),
            on_submit=lambda e: search_user(e),
        )
        
        search_results_col = ft.Column(spacing=4, visible=False)
        selected_user = {"id": None, "name": None}
        
        username_field = ft.TextField(
            label="Display Name",
            hint_text="Enter the user's display name",
            border_color=colors.glass_border,
            focused_border_color=colors.accent_primary,
        )
        
        user_id_field = ft.TextField(
            label="User ID",
            hint_text="usr_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            border_color=colors.glass_border,
            focused_border_color=colors.accent_primary,
        )
        
        async def do_search(query):
            """Search VRChat API for users"""
            if not self.api or not query:
                return
            try:
                results = await self.api.search_users(query, n=5)
                search_results_col.controls.clear()
                if results:
                    for user in results:
                        uid = user.get("id", "")
                        uname = user.get("displayName", "Unknown")
                        search_results_col.controls.append(
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.PERSON, size=16, color=colors.text_secondary),
                                    ft.Text(uname, expand=True, color=colors.text_primary),
                                    ft.Text(uid[:20] + "...", size=10, color=colors.text_tertiary),
                                ], spacing=8),
                                padding=spacing.sm,
                                bgcolor=colors.bg_elevated,
                                border_radius=radius.sm,
                                on_click=lambda e, u=uid, n=uname: select_user(u, n),
                                on_hover=lambda e: setattr(e.control, 'bgcolor', colors.bg_glass if e.data == 'true' else colors.bg_elevated) or e.control.update(),
                            )
                        )
                    search_results_col.visible = True
                else:
                    search_results_col.controls.append(
                        ft.Text("No users found", color=colors.text_tertiary, italic=True)
                    )
                    search_results_col.visible = True
                search_results_col.update()
            except Exception as ex:
                print(f"Search error: {ex}")
        
        def search_user(e):
            query = search_field.value.strip()
            if query and self.page:
                self.page.run_task(do_search, query)
        
        def select_user(uid, uname):
            selected_user["id"] = uid
            selected_user["name"] = uname
            user_id_field.value = uid
            username_field.value = uname
            search_results_col.visible = False
            user_id_field.update()
            username_field.update()
            search_results_col.update()
        
        note_field = ft.TextField(
            label="Note (optional)",
            hint_text="Add notes about this user...",
            multiline=True,
            max_lines=3,
            border_color=colors.glass_border,
            focused_border_color=colors.accent_primary,
        )
        
        # Tag selection
        selected_tags = []
        
        def toggle_tag(tag_name):
            if tag_name in selected_tags:
                selected_tags.remove(tag_name)
            else:
                selected_tags.append(tag_name)
            # Rebuild chips only if mounted
            rebuild_tag_chips()
        
        def rebuild_tag_chips():
            """Rebuild tag chips - only update if mounted"""
            new_controls = [
                TagChip(
                    tag_name=t["name"],
                    emoji=t["emoji"],
                    color=t["color"],
                    selected=t["name"] in selected_tags,
                    on_click=toggle_tag,
                ) for t in DEFAULT_TAGS
            ]
            tag_chips_row.controls = new_controls
            # Only call update if the control is mounted to a page
            if tag_chips_row.page:
                tag_chips_row.update()
        
        # Build initial tag chips (no update needed yet)
        tag_chips_row = ft.Row(
            controls=[
                TagChip(
                    tag_name=t["name"],
                    emoji=t["emoji"],
                    color=t["color"],
                    selected=False,
                    on_click=toggle_tag,
                ) for t in DEFAULT_TAGS
            ],
            wrap=True, 
            spacing=4
        )
        
        def save_user(e):
            username = username_field.value.strip()
            user_id = user_id_field.value.strip()
            note = note_field.value.strip()
            
            if not username or not user_id:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("Please enter both username and user ID"),
                    bgcolor=colors.warning
                )
                self.page.snack_bar.open = True
                self.page.update()
                return
            
            # Validate user ID format
            if not user_id.startswith("usr_"):
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("User ID must start with 'usr_'"),
                    bgcolor=colors.warning
                )
                self.page.snack_bar.open = True
                self.page.update()
                return
            
            # Add to database
            self._db.record_user_sighting(user_id, username)
            self._db.toggle_watchlist(user_id, True)
            if note:
                self._db.set_user_note(user_id, note)
            for tag in selected_tags:
                self._db.add_user_tag(user_id, tag)
            
            self.page.close(dlg)
            self._load_watchlist()
            
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Added {username} to watchlist"),
                bgcolor=colors.success
            )
            self.page.snack_bar.open = True
            self.page.update()
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.PERSON_ADD_ROUNDED, color=colors.accent_primary),
                ft.Text("Add to Watchlist", weight=ft.FontWeight.W_600),
            ], spacing=spacing.sm),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Search VRChat:", weight=ft.FontWeight.W_500, color=colors.text_secondary, size=typography.size_sm),
                    search_field,
                    search_results_col,
                    ft.Divider(color=colors.glass_border),
                    ft.Text("Or enter manually:", weight=ft.FontWeight.W_500, color=colors.text_secondary, size=typography.size_sm),
                    username_field,
                    user_id_field,
                    ft.Container(height=spacing.sm),
                    ft.Text("Tags:", weight=ft.FontWeight.W_500, color=colors.text_secondary),
                    tag_chips_row,
                    ft.Container(height=spacing.sm),
                    note_field,
                ], tight=True, scroll=ft.ScrollMode.AUTO),
                width=480,
                height=500,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.page.close(dlg)),
                NeonButton("Add to Watchlist", icon=ft.Icons.ADD, variant="primary", on_click=save_user),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=colors.bg_elevated,
            shape=ft.RoundedRectangleBorder(radius=radius.lg),
        )
        
        self.page.open(dlg)
    
    def _show_edit_dialog(self, user_id: str):
        """Show dialog to edit a watchlisted user"""
        user = self._db.get_user_profile(user_id)
        if not user:
            return
        
        username = user.get("username", "Unknown")
        current_tags = user.get("tags", [])
        if isinstance(current_tags, str):
            import json
            try:
                current_tags = json.loads(current_tags)
            except:
                current_tags = []
        
        note_field = ft.TextField(
            label="Note",
            value=user.get("note", ""),
            multiline=True,
            max_lines=4,
            border_color=colors.glass_border,
            focused_border_color=colors.accent_primary,
        )
        
        # Tag selection
        selected_tags = list(current_tags)
        
        def toggle_tag(tag_name):
            if tag_name in selected_tags:
                selected_tags.remove(tag_name)
            else:
                selected_tags.append(tag_name)
            rebuild_tag_chips()
        
        def rebuild_tag_chips():
            """Rebuild tag chips - only update if mounted"""
            new_controls = [
                TagChip(
                    tag_name=t["name"],
                    emoji=t["emoji"],
                    color=t["color"],
                    selected=t["name"] in selected_tags,
                    on_click=toggle_tag,
                ) for t in DEFAULT_TAGS
            ]
            tag_chips_row.controls = new_controls
            if tag_chips_row.page:
                tag_chips_row.update()
        
        # Build initial tag chips with current selection
        tag_chips_row = ft.Row(
            controls=[
                TagChip(
                    tag_name=t["name"],
                    emoji=t["emoji"],
                    color=t["color"],
                    selected=t["name"] in selected_tags,
                    on_click=toggle_tag,
                ) for t in DEFAULT_TAGS
            ],
            wrap=True,
            spacing=4
        )
        
        def save_changes(e):
            note = note_field.value.strip()
            
            # Update note
            self._db.set_user_note(user_id, note)
            
            # Update tags - remove old, add new
            for old_tag in current_tags:
                if old_tag not in selected_tags:
                    self._db.remove_user_tag(user_id, old_tag)
            for new_tag in selected_tags:
                if new_tag not in current_tags:
                    self._db.add_user_tag(user_id, new_tag)
            
            self.page.close(dlg)
            self._load_watchlist()
            
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Updated {username}"),
                bgcolor=colors.success
            )
            self.page.snack_bar.open = True
            self.page.update()
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.EDIT_ROUNDED, color=colors.accent_primary),
                ft.Column([
                    ft.Text(f"Edit: {username}", weight=ft.FontWeight.W_600),
                    ft.Text(user_id, size=10, color=colors.text_tertiary, font_family="Consolas"),
                ], spacing=0, expand=True),
            ], spacing=spacing.sm),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Tags:", weight=ft.FontWeight.W_500, color=colors.text_secondary),
                    tag_chips_row,
                    ft.Container(height=spacing.md),
                    note_field,
                ], tight=True),
                width=450,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.page.close(dlg)),
                NeonButton("Save Changes", icon=ft.Icons.SAVE, variant="primary", on_click=save_changes),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=colors.bg_elevated,
            shape=ft.RoundedRectangleBorder(radius=radius.lg),
        )
        
        self.page.open(dlg)
    
    def _confirm_remove(self, user_id: str, username: str):
        """Show confirmation before removing from watchlist"""
        def do_remove(e):
            self._db.toggle_watchlist(user_id, False)
            self.page.close(dlg)
            self._load_watchlist()
            
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Removed {username} from watchlist"),
                bgcolor=colors.success
            )
            self.page.snack_bar.open = True
            self.page.update()
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.WARNING_ROUNDED, color=colors.warning),
                ft.Text("Remove from Watchlist?", weight=ft.FontWeight.W_600),
            ], spacing=spacing.sm),
            content=ft.Text(
                f"Are you sure you want to remove {username} from your watchlist?\n\n"
                "Their notes and tags will be preserved in case you add them back later.",
                color=colors.text_secondary,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.page.close(dlg)),
                NeonButton("Remove", icon=ft.Icons.DELETE, variant="danger", on_click=do_remove),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=colors.bg_elevated,
            shape=ft.RoundedRectangleBorder(radius=radius.lg),
        )
        
        self.page.open(dlg)
    
    def _toggle_alerts(self, e):
        """Toggle alert service enabled state"""
        if self._alert_service:
            # Use the switch value directly
            self._alert_service.enabled = e.control.value
            self._update_stats()
            
            status = "enabled" if self._alert_service.enabled else "disabled"
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"In-game alerts {status}"),
                bgcolor=colors.success if self._alert_service.enabled else colors.text_tertiary
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    def _send_test_alert(self, e):
        """Send a test alert notification"""
        
        async def do_test():
            if not self._alert_service:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("Alert service not available"),
                    bgcolor=colors.warning
                )
                self.page.snack_bar.open = True
                self.page.update()
                return
            
            if not self._alert_service.api:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("Not logged in - cannot send test alert"),
                    bgcolor=colors.warning
                )
                self.page.snack_bar.open = True
                self.page.update()
                return
            
            # If no current instance, try to fetch from API
            current_instance = self._alert_service.get_current_instance()
            
            if not current_instance:
                try:
                    location = await self.api.get_my_location()
                    if location:
                        self._alert_service.update_instance(
                            location.get("world_id", ""),
                            location.get("instance_id", "")
                        )
                except Exception as ex:
                    pass
            
            # Check again after trying to fetch
            current_instance = self._alert_service.get_current_instance()
            if not current_instance:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("You must be in a VRChat instance to test alerts"),
                    bgcolor=colors.warning
                )
                self.page.snack_bar.open = True
                self.page.update()
                return
            
            # Send test alert
            success = await self._alert_service.send_alert(
                username="Test User",
                user_id="usr_test",
                tags=["Test"]
            )
            
            if success:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("✅ Test alert sent! Check your VRChat notifications."),
                    bgcolor=colors.success
                )
            else:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("❌ Failed to send test alert. Check console for details."),
                    bgcolor=colors.danger
                )
            self.page.snack_bar.open = True
            self.page.update()
        
        if self.page:
            self.page.run_task(do_test)
    
    def _build_view(self):
        """Build the main view layout"""
        
        # Header
        header = ft.Row([
            ft.Column([
                ft.Text(
                    "Watchlist Management",
                    size=typography.size_2xl,
                    weight=ft.FontWeight.W_700,
                    color=colors.text_primary,
                ),
                ft.Text(
                    "Monitor users and receive in-game alerts",
                    size=typography.size_base,
                    color=colors.text_secondary,
                ),
            ], spacing=spacing.xs),
            ft.Row([
                NeonButton(
                    "Add User",
                    icon=ft.Icons.PERSON_ADD_ROUNDED,
                    variant=NeonButton.VARIANT_PRIMARY,
                    on_click=lambda e: self._show_add_dialog(),
                ),
            ], spacing=spacing.md),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        
        # Stats row
        self._stats_row = ft.Row(spacing=spacing.md, scroll=ft.ScrollMode.AUTO)
        
        # Search and filter bar
        self._search_field = ft.TextField(
            prefix_icon=ft.Icons.SEARCH,
            hint_text="Search by username or ID...",
            border_color=colors.glass_border,
            focused_border_color=colors.accent_primary,
            on_change=self._handle_search,
            expand=True,
        )
        
        filter_row = ft.Row([
            self._search_field,
            ft.Container(width=spacing.md),
            ft.PopupMenuButton(
                icon=ft.Icons.FILTER_LIST_ROUNDED,
                tooltip="Filter by tag",
                items=[
                    ft.PopupMenuItem(
                        text="All Users",
                        on_click=lambda e: self._clear_filter(),
                    ),
                    ft.PopupMenuItem(),  # Divider
                ] + [
                    ft.PopupMenuItem(
                        text=f"{t['emoji']} {t['name']}",
                        on_click=lambda e, tn=t["name"]: self._handle_tag_filter(tn),
                    ) for t in DEFAULT_TAGS
                ],
            ),
        ])
        
        # User list
        self._user_list = ft.Column(
            spacing=spacing.sm,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        
        # Alert settings panel
        self._alert_switch = ft.Switch(
            value=self._alert_service.enabled if self._alert_service else False,
            active_color=colors.success,
            on_change=self._toggle_alerts,
        )
        
        alert_panel = GlassPanel(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_ROUNDED, color=colors.accent_secondary, size=20),
                    ft.Text("Alert Settings", weight=ft.FontWeight.W_600, expand=True),
                    self._alert_switch,
                ]),
                ft.Text(
                    "When enabled, you'll receive in-game invite notifications when watchlisted users join your instance.",
                    size=typography.size_sm,
                    color=colors.text_tertiary,
                ),
                ft.Container(height=spacing.sm),
                NeonButton(
                    "Send Test Alert",
                    icon=ft.Icons.SEND_ROUNDED,
                    variant=NeonButton.VARIANT_SECONDARY,
                    on_click=self._send_test_alert,
                    height=36,
                ),
            ], spacing=spacing.sm),
        )
        
        # Main layout
        return ft.Column([
            header,
            ft.Container(height=spacing.md),
            self._stats_row,
            ft.Container(height=spacing.md),
            filter_row,
            ft.Container(height=spacing.md),
            ft.Row([
                ft.Container(
                    content=self._user_list,
                    expand=2,
                ),
                ft.Container(width=spacing.md),
                ft.Column([
                    alert_panel,
                    ft.Container(height=spacing.md),
                    GlassPanel(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.LABEL_ROUNDED, color=colors.accent_primary, size=18),
                                ft.Text("Available Tags", weight=ft.FontWeight.W_600),
                            ], spacing=spacing.sm),
                            ft.Divider(color=colors.glass_border),
                            ft.Column([
                                ft.Row([
                                    ft.Text(t["emoji"], size=16),
                                    ft.Text(t["name"], weight=ft.FontWeight.W_500, color=colors.text_primary, expand=True),
                                ], spacing=spacing.sm)
                                for t in DEFAULT_TAGS
                            ], spacing=spacing.xs, scroll=ft.ScrollMode.AUTO),
                        ], spacing=spacing.sm),
                        expand=True,
                    ),
                ], expand=1, spacing=0),
            ], expand=True, vertical_alignment=ft.CrossAxisAlignment.START),
        ], expand=True)
    
    def _clear_filter(self):
        """Clear tag filter"""
        self._selected_tag_filter = None
        self._render_user_list()
