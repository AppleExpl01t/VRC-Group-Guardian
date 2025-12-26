import flet as ft
from ..theme import colors, radius, spacing, typography
from ..components.neon_button import NeonButton, IconButton
from ..components.glass_card import GlassCard

class MembersView(ft.Container):
    """
    View for managing group members.
    """
    def __init__(self, group=None, api=None, on_navigate=None, **kwargs):
        self.group = group
        self.api = api
        self.on_navigate = on_navigate
        self._members = []
        self._all_members = []  # Cache of all members for client-side search
        self._loading = False
        self._search_query = ""
        self._avatar_controls = {} # Map of user_id -> CircleAvatar control
        
        # UI Elements
        self._search_field = None
        self._members_list = None
        self._loading_indicator = None
        
        content = self._build_view()
        
        super().__init__(
            content=content,
            padding=spacing.lg,
            expand=True,
            **kwargs
        )
        
    def did_mount(self):
        self.page.run_task(self._load_all_members)
        self.page.run_task(self._image_worker)
        
    async def _load_all_members(self):
        """Load all members into cache for client-side search"""
        if self._loading:
            return
            
        self._loading = True
        self._all_members = []
        self._update_ui()
        
        group_id = self.group.get("id")
        
        # Load all members
        offset = 0
        limit = 50
        has_more = True
        
        while has_more:
            new_members = await self.api.search_group_members(
                group_id, 
                limit=limit, 
                offset=offset
            )
            
            if len(new_members) < limit:
                has_more = False
            
            # (Removed sync batch caching to prevent rate limiting)

            self._all_members.extend(new_members)
            offset += len(new_members)
            
            # Update UI progressively
            self._apply_filter()
        
        self._loading = False
        self._apply_filter()
        
    def _apply_filter(self):
        """Apply search filter to cached members"""
        if self._search_query:
            query = self._search_query.lower()
            self._members = [
                m for m in self._all_members 
                if query in m.get("user", {}).get("displayName", "").lower()
            ]
        else:
            self._members = self._all_members.copy()
        self._update_ui()
        
    def _update_ui(self):
        if self._members_list:
            self._members_list.controls = self._build_member_items()
            if self._loading:
                self._members_list.controls.append(ft.Container(
                    content=ft.ProgressRing(color=colors.accent_primary),
                    alignment=ft.alignment.center,
                    padding=20
                ))
            if self._members_list.page:
                self._members_list.update()

    def _build_view(self):
        # Header
        header = ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("Members", size=typography.size_2xl, weight=ft.FontWeight.W_700, color=colors.text_primary),
                        ft.Text(f"Manage members of {self.group.get('name')}", color=colors.text_secondary),
                    ],
                    spacing=spacing.xs,
                ),
            ],
        )
        
        # Search Bar
        self._search_field = ft.TextField(
            hint_text="Search members...",
            prefix_icon=ft.Icons.SEARCH,
            bgcolor=colors.bg_elevated,
            border_radius=radius.md,
            border_color=colors.glass_border,
            color=colors.text_primary,
            on_submit=self._handle_search,
            expand=True,
        )
        
        search_row = ft.Row(
            controls=[
                self._search_field,
                IconButton(
                    icon=ft.Icons.SEARCH_ROUNDED, 
                    tooltip="Search",
                    on_click=lambda e: self._handle_search(e)
                )
            ]
        )
        
        # Members List
        self._members_list = ft.ListView(
            expand=True,
            spacing=spacing.xs,
        )
        
        return ft.Column(
            controls=[
                header,
                ft.Container(height=spacing.md),
                search_row,
                ft.Container(height=spacing.sm),
                ft.Container(content=self._members_list, expand=True)
            ],
            expand=True,
        )
        
    def _handle_search(self, e):
        self._search_query = self._search_field.value
        self._apply_filter()

    async def _image_worker(self):
        """Background task to load images sequentially with delay"""
        import asyncio
        while True:
            # Find first member in CURRENT LIST that needs an image
            # This effectively prioritizes the filtered/visible list
            candidate = None
            for m in self._members:
                user = m.get("user", {})
                # Skip if already loaded or currently loading
                if not user.get("local_pfp") and not user.get("_loading_img"):
                    candidate = user
                    break
            
            if candidate:
                candidate["_loading_img"] = True
                try:
                    # 1 Second delay as requested
                    await asyncio.sleep(1)
                    
                    if self.api:
                        path = await self.api.cache_user_image(candidate)
                        if path:
                            candidate["local_pfp"] = path
                            
                            # Update UI if control exists
                            uid = candidate.get("id")
                            if uid in self._avatar_controls:
                                ctl = self._avatar_controls[uid]
                                ctl.foreground_image_src = path
                                ctl.content = None # Remove initials
                                if ctl.page:
                                    ctl.update()
                except Exception as e:
                    print(f"Image worker error: {e}")
            else:
                # Idle if no images needed
                await asyncio.sleep(1)

    def _build_member_items(self):
        self._avatar_controls = {} # Reset control map on rebuild
        
        if not self._members and not self._loading:
            return [ft.Text("No members found", color=colors.text_tertiary, text_align=ft.TextAlign.CENTER)]
            
        items = []
        for member in self._members:
            user = member.get("user", {})
            user_id = user.get("id")
            display_name = user.get("displayName", "Unknown")
            # Use local cached PFP if available, otherwise just use initials (don't fallback to URL to avoid 401s)
            thumbnail = user.get("local_pfp") 
            
            avatar = ft.CircleAvatar(
                foreground_image_src=thumbnail,
                content=ft.Text(display_name[:1].upper()) if not thumbnail else None,
                radius=20,
            )
            self._avatar_controls[user_id] = avatar
            
            item = ft.Container(
                content=ft.Row(
                    controls=[
                        avatar,
                        ft.Text(display_name, color=colors.text_primary, weight=ft.FontWeight.W_500, size=typography.size_base, expand=True),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=colors.text_tertiary, size=16)
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                padding=spacing.sm,
                border_radius=radius.md,
                bgcolor=colors.bg_elevated,
                border=ft.border.all(1, colors.glass_border),
                margin=ft.margin.only(bottom=spacing.xs),
                on_click=lambda e, m=member: self._show_member_details(m),
                ink=True,
            )
            items.append(item)
            
        return items

    def _show_member_details(self, member):
        user = member.get("user", {})
        user_id = user.get("id")
        display_name = user.get("displayName")
        thumbnail = user.get("thumbnailUrl") or user.get("currentAvatarThumbnailImageUrl")
        
        # Create the dialog with a loading state for extra info
        age_badge_container = ft.Container(visible=False)  # Will be populated async
        bio_text = ft.Text("Loading...", color=colors.text_tertiary, size=typography.size_sm)
        
        # Function to close dialog
        def close_dlg(e):
            self.page.close(dlg)
            
        # Action Buttons
        def kick_user(e):
            self.page.close(dlg)
            self.page.open(ft.SnackBar(content=ft.Text(f"Kick functionality not yet implemented for {display_name}")))
            
        def ban_user(e):
            self.page.close(dlg)
            self._show_ban_confirm(member)
            
        def view_profile(e):
            self.page.close(dlg)
            import webbrowser
            webbrowser.open(f"https://vrchat.com/home/user/{user_id}")

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.CircleAvatar(
                    foreground_image_src=thumbnail,
                    content=ft.Text(display_name[:1].upper()) if not thumbnail else None,
                    radius=20,
                    bgcolor=colors.accent_primary,
                ),
                ft.Container(width=spacing.sm),
                ft.Column([
                    ft.Row([
                        ft.Text(display_name, weight=ft.FontWeight.W_600),
                        age_badge_container,  # Age badge will appear here
                    ], spacing=spacing.xs),
                    ft.Text(f"ID: {user_id}", size=typography.size_xs, color=colors.text_tertiary),
                ], spacing=0),
            ]),
            content=ft.Column([
                # Bio section
                ft.Text("Biography", size=typography.size_xs, color=colors.text_tertiary, weight=ft.FontWeight.BOLD),
                bio_text,
                ft.Divider(color=colors.glass_border),
                ft.Container(height=spacing.sm),
                NeonButton("View VRChat Profile", icon=ft.Icons.OPEN_IN_NEW_ROUNDED, variant=NeonButton.VARIANT_SECONDARY, on_click=view_profile),
                ft.Container(height=spacing.xs),
                NeonButton("Kick from Group", icon=ft.Icons.REMOVE_CIRCLE_OUTLINE, variant=NeonButton.VARIANT_WARNING, on_click=kick_user),
                ft.Container(height=spacing.xs),
                NeonButton("Ban from Group", icon=ft.Icons.BLOCK, variant=NeonButton.VARIANT_DANGER, on_click=ban_user),
            ], tight=True, width=400),
            actions=[
                ft.TextButton("Close", on_click=close_dlg)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=colors.bg_elevated,
            shape=ft.RoundedRectangleBorder(radius=radius.lg),
        )
        self.page.open(dlg)
        
        # Async fetch full user details
        async def load_user_details():
            try:
                full_user = await self.api.get_user(user_id)
                if full_user:
                    # Update bio
                    bio = full_user.get("bio", "").strip() or "No biography provided."
                    bio_text.value = bio
                    bio_text.color = colors.text_secondary
                    if bio_text.page:
                        bio_text.update()
                    
                    # Check age verification
                    age_status = full_user.get("ageVerificationStatus", "")
                    is_age_verified = (
                        full_user.get("ageVerified", False) or
                        age_status in ["plus18", "verified", "18+"]
                    )
                    
                    if is_age_verified:
                        age_badge_container.content = ft.Container(
                            content=ft.Text(
                                "18+",
                                size=10,
                                weight=ft.FontWeight.W_700,
                                color=colors.bg_deepest,
                            ),
                            bgcolor=colors.accent_secondary,
                            padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            border_radius=4,
                        )
                        age_badge_container.visible = True
                        if age_badge_container.page:
                            age_badge_container.update()
                else:
                    bio_text.value = "Failed to load user details."
                    if bio_text.page:
                        bio_text.update()

            except Exception as e:
                print(f"Error loading user details: {e}")
                bio_text.value = "Failed to load user details."
                if bio_text.page:
                    bio_text.update()
        
        self.page.run_task(load_user_details)
        
    def _show_ban_confirm(self, member):
        user = member.get("user", {})
        user_id = user.get("id")
        display_name = user.get("displayName")
        
        def close_dlg(e):
            self.page.close(dlg)
            
        def confirm_ban(e):
            self.page.close(dlg)
            async def do_ban():
                success = await self.api.ban_user(self.group.get("id"), user_id)
                if success:
                    self.page.open(ft.SnackBar(content=ft.Text(f"Banned {display_name}"), bgcolor=colors.success))
                    # Reload list
                    await self._load_all_members()
                else:
                    self.page.open(ft.SnackBar(content=ft.Text(f"Failed to ban {display_name}"), bgcolor=colors.danger))
            self.page.run_task(do_ban)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Ban"),
            content=ft.Text(f"Are you sure you want to ban {display_name}? This action cannot be easily undone."),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                ft.TextButton("Ban User", style=ft.ButtonStyle(color=colors.danger), on_click=confirm_ban),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=colors.bg_elevated,
            shape=ft.RoundedRectangleBorder(radius=radius.lg),
        )
        self.page.open(dlg)
