import flet as ft
from ..theme import colors, radius, spacing, typography
from ..components.neon_button import NeonButton, IconButton
from ..components.glass_card import GlassCard

class BansView(ft.Container):
    """
    View for managing banned users in a group.
    """
    def __init__(self, group=None, api=None, on_navigate=None, **kwargs):
        self.group = group
        self.api = api
        self.on_navigate = on_navigate
        self._bans = []
        self._all_bans = []  # Cache of all bans for client-side search
        self._loading = False
        self._search_query = ""
        
        # UI Elements
        self._search_field = None
        self._bans_list = None
        self._loading_indicator = None
        self._count_text = None
        
        content = self._build_view()
        
        super().__init__(
            content=content,
            padding=spacing.lg,
            expand=True,
            **kwargs
        )
        
    def did_mount(self):
        self.page.run_task(self._load_all_bans)
        
    async def _load_all_bans(self):
        """Load all banned users into cache for client-side search"""
        if self._loading:
            return
            
        self._loading = True
        self._all_bans = []
        self._update_ui()
        
        group_id = self.group.get("id")
        
        try:
            # Fetch all bans - uses pagination if available
            bans = await self.api.get_group_bans(group_id)
            
            if bans:
                # Cache images for banned users
                for ban in bans:
                    user = ban.get("user", {})
                    if user:
                        try:
                            path = await self.api.cache_user_image(user)
                            if path:
                                user["local_pfp"] = path
                        except Exception as e:
                            print(f"Failed to cache ban image: {e}")

                self._all_bans = bans
            
        except Exception as e:
            print(f"Error loading bans: {e}")
            
        self._loading = False
        self._apply_filter()
        
    def _apply_filter(self):
        """Apply search filter to cached bans"""
        if self._search_query:
            query = self._search_query.lower()
            self._bans = [
                b for b in self._all_bans 
                if query in (b.get("user", {}).get("displayName") or "").lower() or
                   query in (b.get("userId") or "").lower()
            ]
        else:
            self._bans = self._all_bans.copy()
        self._update_ui()
        
    def _update_ui(self):
        if self._bans_list:
            self._bans_list.controls = self._build_ban_items()
            if self._loading:
                self._bans_list.controls.append(ft.Container(
                    content=ft.ProgressRing(color=colors.accent_primary),
                    alignment=ft.alignment.center,
                    padding=20
                ))
            self._bans_list.update()
            
        # Update count
        if self._count_text:
            total = len(self._all_bans)
            showing = len(self._bans)
            if self._search_query:
                self._count_text.value = f"Showing {showing} of {total} banned users"
            else:
                self._count_text.value = f"{total} banned user{'s' if total != 1 else ''}"
            self._count_text.update()

    def _build_view(self):
        # Header
        self._count_text = ft.Text("Loading...", color=colors.text_secondary, size=typography.size_sm)
        
        header = ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("Banned Users", size=typography.size_2xl, weight=ft.FontWeight.W_700, color=colors.text_primary),
                        ft.Text(f"Manage banned users of {self.group.get('name')}", color=colors.text_secondary),
                    ],
                    spacing=spacing.xs,
                ),
                ft.Container(expand=True),
                NeonButton(
                    "Ban by Search",
                    icon=ft.Icons.PERSON_SEARCH_ROUNDED,
                    variant=NeonButton.VARIANT_DANGER,
                    on_click=lambda e: self._show_user_search_dialog(),
                ),
                ft.Container(width=spacing.sm),
                self._count_text,
            ],
        )
        
        # Search Bar (for filtering existing bans)
        self._search_field = ft.TextField(
            hint_text="Filter banned users...",
            prefix_icon=ft.Icons.SEARCH,
            bgcolor=colors.bg_elevated,
            border_radius=radius.md,
            border_color=colors.glass_border,
            color=colors.text_primary,
            on_submit=self._handle_search,
            on_change=self._handle_search,  # Live search
            expand=True,
        )
        
        search_row = ft.Row(
            controls=[
                self._search_field,
                IconButton(
                    icon=ft.Icons.REFRESH_ROUNDED, 
                    tooltip="Refresh",
                    on_click=lambda e: self.page.run_task(self._load_all_bans)
                )
            ]
        )
        
        # Bans List
        self._bans_list = ft.ListView(
            expand=True,
            spacing=spacing.xs,
            on_scroll_interval=0,
        )
        
        return ft.Column(
            controls=[
                header,
                ft.Container(height=spacing.md),
                search_row,
                ft.Container(height=spacing.sm),
                ft.Container(content=self._bans_list, expand=True)
            ],
            expand=True,
        )
        
    def _handle_search(self, e):
        self._search_query = self._search_field.value or ""
        self._apply_filter()

    def _build_ban_items(self):
        if not self._bans and not self._loading:
            return [
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, size=48, color=colors.success),
                            ft.Container(height=spacing.sm),
                            ft.Text("No banned users", color=colors.text_secondary, size=typography.size_base),
                            ft.Text("All users are welcome in this group!", color=colors.text_tertiary, size=typography.size_sm),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    padding=spacing.xl,
                )
            ]
            
        items = []
        for ban in self._bans:
            # Handle both nested user object and flat structure
            user = ban.get("user", {})
            user_id = user.get("id") or ban.get("userId", "Unknown")
            display_name = user.get("displayName", ban.get("displayName", "Unknown User"))
            # Use local cached PFP if available
            thumbnail = user.get("local_pfp") or user.get("thumbnailUrl") or user.get("currentAvatarThumbnailImageUrl") or ban.get("thumbnailUrl")
            banned_at = ban.get("createdAt", ban.get("bannedAt", ""))
            
            avatar = ft.CircleAvatar(
                foreground_image_src=thumbnail,
                content=ft.Text(display_name[:1].upper()) if not thumbnail else None,
                radius=20,
                bgcolor=colors.accent_primary,  # Purple like members tab
            )
            
            # Format ban date
            ban_info = ""
            if banned_at:
                try:
                    from datetime import datetime
                    if 'T' in banned_at:
                        dt = datetime.fromisoformat(banned_at.replace('Z', '+00:00'))
                        ban_info = f"Banned {dt.strftime('%b %d, %Y')}"
                except:
                    ban_info = f"Banned: {banned_at[:10]}"
            
            item = ft.Container(
                content=ft.Row(
                    controls=[
                        avatar,
                        ft.Column(
                            controls=[
                                ft.Text(display_name, color=colors.text_primary, weight=ft.FontWeight.W_500, size=typography.size_base),
                                ft.Text(ban_info or f"ID: {user_id[:20]}...", color=colors.text_tertiary, size=typography.size_xs),
                            ],
                            spacing=0,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Icon(ft.Icons.BLOCK_ROUNDED, color=colors.danger, size=16),
                            bgcolor=colors.danger + "22",
                            border_radius=radius.sm,
                            padding=4,
                        ),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=colors.text_tertiary, size=16)
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                padding=spacing.sm,
                border_radius=radius.md,
                bgcolor=colors.bg_elevated,
                border=ft.border.all(1, "rgba(239, 68, 68, 0.4)"),  # Warm red at 40% opacity
                margin=ft.margin.only(bottom=spacing.xs),
                on_click=lambda e, b=ban: self._show_ban_details(b),
                ink=True,
            )
            items.append(item)
            
        return items

    def _show_ban_details(self, ban):
        """Show moderation options for a banned user"""
        user = ban.get("user", {})
        user_id = user.get("id") or ban.get("userId", "Unknown")
        display_name = user.get("displayName", ban.get("displayName", "Unknown User"))
        thumbnail = user.get("thumbnailUrl") or user.get("currentAvatarThumbnailImageUrl")
        banned_at = ban.get("createdAt", ban.get("bannedAt", ""))
        
        # Function to close dialog
        def close_dlg(e):
            self.page.close(dlg)
            
        # Action Buttons
        def unban_user(e):
            self.page.close(dlg)
            self._confirm_unban(ban, invite_after=False)
            
        def unban_and_invite(e):
            self.page.close(dlg)
            self._confirm_unban(ban, invite_after=True)
            
        def view_profile(e):
            self.page.close(dlg)
            # Open VRChat profile in browser
            import webbrowser
            webbrowser.open(f"https://vrchat.com/home/user/{user_id}")

        # Build ban info
        ban_info_text = ""
        if banned_at:
            try:
                from datetime import datetime
                if 'T' in banned_at:
                    dt = datetime.fromisoformat(banned_at.replace('Z', '+00:00'))
                    ban_info_text = f"Banned on {dt.strftime('%B %d, %Y at %I:%M %p')}"
            except:
                ban_info_text = f"Banned: {banned_at}"

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.CircleAvatar(
                        foreground_image_src=thumbnail,
                        content=ft.Text(display_name[:1].upper()) if not thumbnail else None,
                        radius=20,
                    ),
                    ft.Container(width=spacing.sm),
                    ft.Column(
                        controls=[
                            ft.Text(display_name, weight=ft.FontWeight.W_600),
                            ft.Text(f"ID: {user_id}", size=typography.size_xs, color=colors.text_tertiary),
                        ],
                        spacing=0,
                    ),
                ],
            ),
            content=ft.Column([
                # Ban status badge
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.BLOCK_ROUNDED, color=colors.danger, size=16),
                            ft.Text("BANNED", color=colors.danger, weight=ft.FontWeight.W_600, size=typography.size_sm),
                        ],
                        spacing=spacing.xs,
                    ),
                    bgcolor=colors.danger + "22",
                    border_radius=radius.md,
                    padding=ft.padding.symmetric(horizontal=spacing.md, vertical=spacing.xs),
                ),
                
                ft.Container(height=spacing.xs),
                ft.Text(ban_info_text, color=colors.text_secondary, size=typography.size_sm) if ban_info_text else ft.Container(),
                
                ft.Divider(color=colors.glass_border, height=spacing.lg),
                
                ft.Text("Moderation Actions", weight=ft.FontWeight.W_600, color=colors.text_primary),
                ft.Container(height=spacing.xs),
                
                NeonButton(
                    "Unban User", 
                    icon=ft.Icons.REMOVE_CIRCLE_OUTLINE_ROUNDED, 
                    variant=NeonButton.VARIANT_SUCCESS, 
                    on_click=unban_user,
                    width=350,
                ),
                ft.Container(height=spacing.xs),
                NeonButton(
                    "Unban & Invite to Group", 
                    icon=ft.Icons.PERSON_ADD_ROUNDED, 
                    variant=NeonButton.VARIANT_PRIMARY, 
                    on_click=unban_and_invite,
                    width=350,
                ),
                ft.Container(height=spacing.xs),
                NeonButton(
                    "View VRChat Profile", 
                    icon=ft.Icons.OPEN_IN_NEW_ROUNDED, 
                    variant=NeonButton.VARIANT_SECONDARY, 
                    on_click=view_profile,
                    width=350,
                ),
            ], tight=True, width=350),
            actions=[
                ft.TextButton("Close", on_click=close_dlg)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=colors.bg_elevated,
            shape=ft.RoundedRectangleBorder(radius=radius.lg),
        )
        self.page.open(dlg)
        
    def _confirm_unban(self, ban, invite_after=False):
        """Show confirmation dialog for unbanning"""
        user = ban.get("user", {})
        user_id = user.get("id") or ban.get("userId", "Unknown")
        display_name = user.get("displayName", ban.get("displayName", "Unknown User"))
        
        def close_dlg(e):
            self.page.close(dlg)
            
        def confirm_action(e):
            self.page.close(dlg)
            self.page.run_task(lambda: self._do_unban(ban, invite_after))
            
        action_text = "unban and invite" if invite_after else "unban"
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Confirm {'Unban & Invite' if invite_after else 'Unban'}"),
            content=ft.Text(f"Are you sure you want to {action_text} {display_name}?"),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                ft.TextButton(
                    "Confirm", 
                    style=ft.ButtonStyle(color=colors.success), 
                    on_click=confirm_action
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=colors.bg_elevated,
            shape=ft.RoundedRectangleBorder(radius=radius.lg),
        )
        self.page.open(dlg)
        
    async def _do_unban(self, ban, invite_after=False):
        """Execute the unban action"""
        user = ban.get("user", {})
        user_id = user.get("id") or ban.get("userId")
        display_name = user.get("displayName", ban.get("displayName", "Unknown User"))
        group_id = self.group.get("id")
        
        try:
            # Unban the user
            success = await self.api.unban_user(group_id, user_id)
            
            if success:
                self.page.open(ft.SnackBar(
                    content=ft.Text(f"Successfully unbanned {display_name}"), 
                    bgcolor=colors.success
                ))
                
                # Invite if requested
                if invite_after:
                    invite_success = await self.api.invite_user_to_group(group_id, user_id)
                    if invite_success:
                        self.page.open(ft.SnackBar(
                            content=ft.Text(f"Invite sent to {display_name}"), 
                            bgcolor=colors.success
                        ))
                    else:
                        self.page.open(ft.SnackBar(
                            content=ft.Text(f"Unbanned but failed to invite {display_name}"), 
                            bgcolor=colors.warning
                        ))
                
                # Reload bans list
                await self._load_all_bans()
            else:
                self.page.open(ft.SnackBar(
                    content=ft.Text(f"Failed to unban {display_name}"), 
                    bgcolor=colors.danger
                ))
                
        except Exception as e:
            print(f"Error unbanning user: {e}")
            self.page.open(ft.SnackBar(
                content=ft.Text(f"Error: {str(e)}"), 
                bgcolor=colors.danger
            ))

    def _show_user_search_dialog(self):
        """Show dialog to search for users to ban"""
        search_field = ft.TextField(
            hint_text="Enter username to search...",
            prefix_icon=ft.Icons.SEARCH,
            bgcolor=colors.bg_base,
            border_radius=radius.md,
            border_color=colors.glass_border,
            color=colors.text_primary,
            expand=True,
            autofocus=True,
        )
        
        results_container = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Text("Enter a username and press Search", color=colors.text_tertiary, italic=True),
                    alignment=ft.alignment.center,
                    height=100,
                )
            ],
            spacing=spacing.sm,
            scroll=ft.ScrollMode.AUTO,
        )
        
        loading_indicator = ft.Container(
            content=ft.ProgressRing(color=colors.accent_primary, width=24, height=24),
            visible=False,
            alignment=ft.alignment.center,
        )
        
        def close_dlg(e):
            self.page.close(dlg)
            
        async def do_search():
            query = search_field.value
            if not query or not query.strip():
                return
                
            # Show loading
            loading_indicator.visible = True
            results_container.controls = []
            dlg.update()
            
            try:
                users = await self.api.search_users(query.strip())
                loading_indicator.visible = False
                
                if not users:
                    results_container.controls = [
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, size=32, color=colors.text_tertiary),
                                ft.Text("No users found", color=colors.text_secondary),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            alignment=ft.alignment.center,
                            height=100,
                        )
                    ]
                else:
                    # Cache images for search results
                    for user in users:
                        try:
                            path = await self.api.cache_user_image(user)
                            if path:
                                user["local_pfp"] = path
                        except Exception:
                            pass

                    results_container.controls = [
                        self._build_search_result_item(user, dlg) for user in users
                    ]
                    
                dlg.update()
                
            except Exception as e:
                loading_indicator.visible = False
                results_container.controls = [
                    ft.Text(f"Error: {str(e)}", color=colors.danger)
                ]
                dlg.update()
        
        def on_search(e):
            self.page.run_task(do_search)
        
        search_field.on_submit = on_search

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.PERSON_SEARCH_ROUNDED, color=colors.danger, size=28),
                ft.Container(width=spacing.sm),
                ft.Text("Search & Ban User", weight=ft.FontWeight.W_600),
            ]),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        search_field,
                        NeonButton(
                            "Search",
                            icon=ft.Icons.SEARCH,
                            variant=NeonButton.VARIANT_PRIMARY,
                            on_click=on_search,
                        ),
                    ], spacing=spacing.sm),
                    ft.Container(height=spacing.sm),
                    loading_indicator,
                    ft.Container(
                        content=results_container,
                        height=350,
                        border=ft.border.all(1, colors.glass_border),
                        border_radius=radius.md,
                        padding=spacing.sm,
                        bgcolor=colors.bg_base,
                    ),
                ], spacing=spacing.sm),
                width=550,
            ),
            actions=[
                ft.TextButton("Close", on_click=close_dlg),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=colors.bg_elevated,
            shape=ft.RoundedRectangleBorder(radius=radius.lg),
        )
        self.page.open(dlg)
    
    def _build_search_result_item(self, user: dict, parent_dlg) -> ft.Control:
        """Build a single search result item with profile and ban button"""
        user_id = user.get("id", "")
        display_name = user.get("displayName", "Unknown")
        bio = user.get("bio", "No bio available")
        thumbnail = user.get("local_pfp") or user.get("currentAvatarThumbnailImageUrl") or user.get("userIcon")
        status = user.get("status", "offline")
        
        # Status color
        status_colors = {
            "join me": "#42caff",
            "active": "#10b981",
            "online": "#10b981",
            "ask me": "#f59e0b",
            "busy": "#ef4444",
            "offline": "#64748b",
        }
        status_color = status_colors.get(status.lower() if status else "offline", "#64748b")
        
        # Truncate bio
        bio_display = (bio[:150] + "...") if bio and len(bio) > 150 else (bio or "No bio")
        
        # Bio container (expandable)
        bio_expanded = ft.Ref[ft.Container]()
        
        def toggle_bio(e):
            if bio_expanded.current:
                bio_expanded.current.visible = not bio_expanded.current.visible
                bio_expanded.current.update()
        
        def ban_user(e):
            self.page.close(parent_dlg)
            self._confirm_search_ban(user)

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    # Avatar
                    ft.Container(
                        content=ft.Image(
                            src=thumbnail,
                            width=48,
                            height=48,
                            fit=ft.ImageFit.COVER,
                            border_radius=24,
                        ) if thumbnail else ft.CircleAvatar(
                            content=ft.Text(display_name[:1].upper()),
                            radius=24,
                            bgcolor=colors.accent_primary,
                        ),
                        width=48,
                        height=48,
                        border_radius=24,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                    # Info
                    ft.Column([
                        ft.Row([
                            ft.Text(display_name, weight=ft.FontWeight.BOLD, color=colors.text_primary, size=typography.size_base),
                            ft.Container(
                                width=8,
                                height=8,
                                border_radius=4,
                                bgcolor=status_color,
                            ),
                        ], spacing=spacing.xs),
                        ft.Text(f"ID: {user_id[:25]}...", size=typography.size_xs, color=colors.text_tertiary),
                    ], expand=True, spacing=0),
                    # Ban button
                    NeonButton(
                        "Ban",
                        icon=ft.Icons.BLOCK_ROUNDED,
                        variant=NeonButton.VARIANT_DANGER,
                        on_click=ban_user,
                    ),
                ], spacing=spacing.md),
                # Bio section
                ft.Container(
                    ref=bio_expanded,
                    content=ft.Column([
                        ft.Divider(color=colors.glass_border, height=1),
                        ft.Text("Bio:", size=typography.size_xs, color=colors.text_tertiary, weight=ft.FontWeight.BOLD),
                        ft.Text(bio_display, size=typography.size_sm, color=colors.text_secondary),
                    ], spacing=2),
                    visible=True,
                    padding=ft.padding.only(top=spacing.sm),
                ),
            ], spacing=spacing.xs),
            padding=spacing.md,
            bgcolor=colors.bg_elevated,
            border_radius=radius.md,
            border=ft.border.all(1, colors.glass_border),
            on_click=toggle_bio,
        )
    
    def _confirm_search_ban(self, user: dict):
        """Show confirmation dialog for banning a searched user"""
        user_id = user.get("id", "")
        display_name = user.get("displayName", "Unknown")
        thumbnail = user.get("currentAvatarThumbnailImageUrl") or user.get("userIcon")
        bio = user.get("bio", "No bio")
        
        def close_dlg(e):
            self.page.close(dlg)
            
        def confirm_ban(e):
            self.page.close(dlg)
            self.page.run_task(lambda: self._execute_search_ban(user))

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.WARNING_ROUNDED, color=colors.danger, size=28),
                ft.Container(width=spacing.sm),
                ft.Text("Confirm Ban", weight=ft.FontWeight.W_600),
            ]),
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Image(
                            src=thumbnail,
                            width=64,
                            height=64,
                            fit=ft.ImageFit.COVER,
                            border_radius=32,
                        ) if thumbnail else ft.CircleAvatar(
                            content=ft.Text(display_name[:1].upper()),
                            radius=32,
                            bgcolor=colors.accent_primary,
                        ),
                        width=64,
                        height=64,
                        border_radius=32,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                    ft.Container(width=spacing.md),
                    ft.Column([
                        ft.Text(display_name, weight=ft.FontWeight.BOLD, size=typography.size_lg, color=colors.text_primary),
                        ft.Text(f"ID: {user_id}", size=typography.size_xs, color=colors.text_tertiary),
                    ], expand=True, spacing=0),
                ]),
                ft.Container(height=spacing.md),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Bio:", size=typography.size_xs, color=colors.text_tertiary, weight=ft.FontWeight.BOLD),
                        ft.Text(bio[:200] + ("..." if len(bio) > 200 else ""), size=typography.size_sm, color=colors.text_secondary),
                    ], spacing=2),
                    padding=spacing.md,
                    bgcolor=colors.bg_base,
                    border_radius=radius.md,
                ),
                ft.Container(height=spacing.md),
                ft.Text(
                    f"Are you sure you want to ban {display_name} from {self.group.get('name')}?",
                    color=colors.text_primary,
                ),
                ft.Text(
                    "⚠️ This action cannot be easily undone.",
                    color=colors.warning,
                    size=typography.size_sm,
                ),
            ], tight=True, width=400),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                NeonButton(
                    "Ban User",
                    icon=ft.Icons.BLOCK_ROUNDED,
                    variant=NeonButton.VARIANT_DANGER,
                    on_click=confirm_ban,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=colors.bg_elevated,
            shape=ft.RoundedRectangleBorder(radius=radius.lg),
        )
        self.page.open(dlg)
    
    async def _execute_search_ban(self, user: dict):
        """Execute the ban on a searched user"""
        user_id = user.get("id", "")
        display_name = user.get("displayName", "Unknown")
        group_id = self.group.get("id")
        
        try:
            success = await self.api.ban_user(group_id, user_id)
            
            if success:
                self.page.open(ft.SnackBar(
                    content=ft.Text(f"✓ Banned {display_name}"),
                    bgcolor=colors.success,
                ))
                # Refresh bans list
                await self._load_all_bans()
            else:
                self.page.open(ft.SnackBar(
                    content=ft.Text(f"Failed to ban {display_name}"),
                    bgcolor=colors.danger,
                ))
        except Exception as e:
            print(f"Error banning user: {e}")
            self.page.open(ft.SnackBar(
                content=ft.Text(f"Error: {str(e)}"),
                bgcolor=colors.danger,
            ))
