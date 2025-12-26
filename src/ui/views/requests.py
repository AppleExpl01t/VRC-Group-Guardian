
import flet as ft
from ..theme import colors, radius, spacing, typography
from ..components.glass_card import GlassPanel, GlassCard
from ..components.neon_button import IconButton

class RequestsView(ft.Container):
    """
    View for managing group join requests.
    """
    def __init__(self, group=None, api=None, on_navigate=None, on_update_stats=None, **kwargs):
        self.group = group
        self.api = api
        self.on_navigate = on_navigate
        self.on_update_stats = on_update_stats
        self._requests = []
        self._loading = True
        
        # Content list
        self._content_area = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=spacing.sm)
        
        # Header
        header = ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("Join Requests", size=typography.size_2xl, weight=ft.FontWeight.W_700, color=colors.text_primary),
                        ft.Text(f"Pending members for {self.group.get('name') if self.group else 'Unknown'}", color=colors.text_secondary),
                    ],
                    spacing=spacing.xs,
                ),
                ft.Row(
                    controls=[
                        IconButton(
                            icon=ft.Icons.REFRESH_ROUNDED,
                            tooltip="Refresh",
                            on_click=lambda e: self.page.run_task(self._load_data),
                        ),
                    ]
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        content = ft.Column([
            header,
            ft.Container(height=spacing.md),
            self._content_area
        ], expand=True)
        
        super().__init__(
            content=content,
            padding=spacing.lg,
            expand=True,
            **kwargs
        )
        
    def did_mount(self):
        self._update_view()
        self.page.run_task(self._load_data)
        
    async def _load_data(self):
        if not self.api or not self.group:
            self._loading = False
            self._update_view()
            return

        self._loading = True
        self._update_view()
            
        group_id = self.group.get("id")
        self._requests = await self.api.get_group_join_requests(group_id)
        
        # Notify parent app
        if self.on_update_stats:
            self.on_update_stats({"pending_requests": len(self._requests)})
        
        self._loading = False
        self._update_view()
        
    def _update_view(self):
        self._content_area.controls = self._get_content_controls()
        self.update()
        
    def _get_content_controls(self):
        if self._loading:
            return [ft.Container(
                content=ft.ProgressRing(color=colors.accent_primary), 
                alignment=ft.alignment.center,
                expand=True,
                height=200
            )]
            
        if not self._requests:
             return [ft.Container(
                 content=ft.Column([
                     ft.Icon(ft.Icons.INBOX_ROUNDED, size=48, color=colors.text_tertiary),
                     ft.Container(height=spacing.sm),
                     ft.Text("No pending requests", color=colors.text_secondary, size=typography.size_lg),
                     ft.Text("You're all caught up!", color=colors.text_tertiary),
                 ], horizontal_alignment=ft.CrossAxisAlignment.CENTER), 
                 alignment=ft.alignment.center,
                 expand=True,
                 height=300
             )]
             
        items = []
        for req in self._requests:
            items.append(self._build_request_item(req))
            
        return items

    def _build_request_item(self, req):
        user = req.get("user", {})
        user_id = user.get("id")
        user_name = user.get("displayName", "Unknown User")
        
        # Correctly prioritize image sources
        icon = (
            user.get("userIcon") or 
            user.get("profilePicOverride") or 
            user.get("currentAvatarThumbnailImageUrl") or
            user.get("imageUrl")
        )
        
        # Check for Age Verification - Note: This data may not be available in limited API response
        # Will be properly checked when viewing full user details
        
        bio = user.get("bio", "No biography provided.")
        
        bio_text = ft.Text(bio, size=typography.size_sm, color=colors.text_secondary)
        
        # Expansion state tracking using a custom data attribute on the bio container
        bio_container = ft.Container(
            content=ft.Column([
                ft.Divider(color=colors.glass_border, height=1),
                ft.Text("Biography", size=typography.size_xs, color=colors.text_tertiary, weight=ft.FontWeight.BOLD),
                bio_text,
            ], spacing=spacing.xs),
            visible=False, # Hidden by default
            padding=ft.padding.only(top=spacing.sm),
            animate_opacity=200,
        )
        
        avatar_image = ft.Image(src=icon, fit=ft.ImageFit.COVER) if icon else ft.Icon(ft.Icons.PERSON, color=colors.text_secondary)

        # Eager load PFP if page is mounted
        if hasattr(self, "page") and self.page:
            async def load_pfp():
                path = await self.api.cache_user_image(user)
                if path and path != avatar_image.src:
                    avatar_image.src = path
                    avatar_image.update()
            self.page.run_task(load_pfp)

        def toggle_bio(e):
            bio_container.visible = not bio_container.visible
            e.control.icon = ft.Icons.KEYBOARD_ARROW_UP_ROUNDED if bio_container.visible else ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED
            
            # Lazy load bio if not already loaded (and if it's currently placeholder)
            if bio_container.visible and bio_text.value == "No biography provided.":
                bio_text.value = "Loading biography..."
                bio_text.update()
                
                async def fetch_details():
                    await self._fetch_full_user_details(user_id, bio_text, avatar_image)
                    
                self.page.run_task(fetch_details)
                
            self.update()

        # Name row (simple, without age badge since API doesn't provide it)
        name_controls = [
            ft.Text(user_name, weight=ft.FontWeight.BOLD, color=colors.text_primary, size=typography.size_base),
        ]

        async def reject_req():
            await self._handle_action(req, "Reject")
            
        async def accept_req():
            await self._handle_action(req, "Accept")

        return GlassCard(
            content=ft.Column([
                ft.Row([
                    # Avatar
                    ft.Container(
                        content=avatar_image,
                        width=48, height=48, border_radius=24, clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        bgcolor=colors.bg_elevated,
                        on_click=toggle_bio # Clicking avatar also toggles
                    ),
                    
                    # Info (Name + Badges)
                    ft.Container(
                        content=ft.Column([
                            ft.Row(name_controls, spacing=0),
                            ft.Text("Tap to view details", size=typography.size_xs, color=colors.text_tertiary),
                        ], spacing=2, alignment=ft.MainAxisAlignment.CENTER),
                        expand=True,
                        on_click=toggle_bio, # Clicking area toggles
                        padding=ft.padding.only(left=spacing.sm)
                    ),
                    
                    # Actions
                    ft.Row([
                        IconButton(
                            icon=ft.Icons.BLOCK_ROUNDED,
                            icon_color=colors.danger,
                            tooltip="Ban User",
                            on_click=lambda e: self._show_ban_dialog(req)
                        ),
                        ft.Container(width=spacing.xs),
                        IconButton(
                            icon=ft.Icons.CLOSE_ROUNDED,
                            icon_color=colors.warning,
                            tooltip="Reject",
                            on_click=lambda e: self.page.run_task(reject_req)
                        ),
                        ft.Container(width=spacing.xs),
                        IconButton(
                            icon=ft.Icons.CHECK_ROUNDED,
                            icon_color=colors.success,
                            tooltip="Accept",
                            on_click=lambda e: self.page.run_task(accept_req)
                        ),
                    ])
                ], alignment=ft.MainAxisAlignment.START),
                
                # Expandable Bio
                bio_container
            ]),
            padding=spacing.md,
            animate_size=200, # Smooth height animation
        )

    async def _fetch_full_user_details(self, user_id, bio_text_control, avatar_image_control):
        """Fetch full user bio and update UI"""
        user_data = await self.api.get_user(user_id)
        if user_data:
            bio = user_data.get("bio", "").strip() or "User has no biography."
            bio_text_control.value = bio
            bio_text_control.update()
            
            # Cache the image locally for better reliability
            local_path = await self.api.cache_user_image(user_data)
            
            if local_path and local_path != avatar_image_control.src:
                avatar_image_control.src = local_path
                avatar_image_control.update()
        else:
            bio_text_control.value = "Failed to load biography."
            bio_text_control.update()

    def _show_ban_dialog(self, req):
        """Show confirmation dialog for banning a user"""
        user = req.get("user", {})
        user_name = user.get("displayName", "Unknown")
        user_id = user.get("id", "")
        
        def close_dlg(e):
            self.page.close(dlg)
            
        def confirm_ban(e):
            self.page.close(dlg)
            
            async def do_ban():
                await self._confirm_ban_action(req)
                
            self.page.run_task(do_ban)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Ban User?"),
            content=ft.Text(f"Are you sure you want to ban {user_name} ({user_id}) from the group? This cannot be easily undone."),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                ft.TextButton("Ban User", on_click=confirm_ban, style=ft.ButtonStyle(color=colors.danger)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=colors.bg_elevated,
            shape=ft.RoundedRectangleBorder(radius=radius.lg),
        )
        
        self.page.open(dlg)

    async def _confirm_ban_action(self, req):
        """Execute the ban and reject request"""
        group_id = self.group.get("id")
        req_id = req.get("id")
        user = req.get("user", {})
        user_id = user.get("id")
        
        # 1. Ban the user
        ban_success = await self.api.ban_user(group_id, user_id)
        
        if ban_success:
            self.page.open(ft.SnackBar(content=ft.Text("User banned successfully"), bgcolor=colors.success))
            
            # 2. Reject the request (cleanup)
            # Optimistically remove from UI
            self._requests = [r for r in self._requests if r.get("id") != req.get("id")]
            self._update_view()
            
            # Update stats badge
            if self.on_update_stats:
                self.on_update_stats({"pending_requests": len(self._requests)})
            
            # await self.api.handle_join_request(group_id, user_id, "reject")
        else:
            self.page.open(ft.SnackBar(content=ft.Text("Failed to ban user"), bgcolor=colors.danger))

    async def _handle_action(self, req, action):
        group_id = self.group.get("id")
        req_id = req.get("id")
        user = req.get("user", {})
        user_id = user.get("id")
        
        # Optimistic remove from UI
        self._requests = [r for r in self._requests if r.get("id") != req.get("id")]
        self._update_view()
        
        # Update stats badge
        if self.on_update_stats:
            self.on_update_stats({"pending_requests": len(self._requests)})
        
        success = await self.api.handle_join_request(group_id, user_id, action.lower())
        
        if not success:
            # Revert if failed (add back)
            self._requests.append(req)
            self._update_view()
            
            # Show snackbar
            self.page.open(ft.SnackBar(content=ft.Text(f"Failed to {action} request")))
        else:
            msg = f"Accepted {user.get('displayName')}" if action == "Accept" else f"Rejected {user.get('displayName')}"
            self.page.open(ft.SnackBar(content=ft.Text(msg), bgcolor=colors.success_dim if action == "Accept" else colors.danger_dim))

