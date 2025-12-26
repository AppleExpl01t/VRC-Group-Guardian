import flet as ft
from ..theme import colors, radius, spacing, typography
from ..components.neon_button import IconButton
from ..components.user_card import UserCard
from ..dialogs.user_details import show_user_details_dialog
from services.database import get_database

class RequestsView(ft.Container):
    """
    View for managing group join requests using Unified UserCard.
    """
    def __init__(self, group=None, api=None, on_navigate=None, on_update_stats=None, **kwargs):
        self.group = group
        self.api = api
        self.on_navigate = on_navigate
        self.on_update_stats = on_update_stats
        self._requests = []
        self._loading = True
        self.db = get_database()
        
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
            
        try:
            group_id = self.group.get("id")
            self._requests = await self.api.get_cached_join_requests(group_id)
            
            # Notify parent app
            if self.on_update_stats:
                self.on_update_stats({"pending_requests": len(self._requests)})
        except Exception as e:
            print(f"Error loading requests: {e}")
            import traceback
            traceback.print_exc()
        finally:
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
        
        async def reject_req(e):
            await self._handle_action(req, "Reject")
            
        async def accept_req(e):
            await self._handle_action(req, "Accept")
            
        def show_ban(e):
             # Reuse dialog service's ban logic if possible, or simple confirmation here
             from ..dialogs.user_details import show_user_details_dialog
             # Open details with ban active? Custom ban dialog is simpler for strict "Request" context
             self._show_ban_dialog(req)

        # Actions
        actions = [
            IconButton(
                icon=ft.Icons.BLOCK_ROUNDED,
                icon_color=colors.danger,
                tooltip="Ban User",
                on_click=show_ban
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
        ]

        return UserCard(
            user_data=user,
            api=self.api,
            db=self.db,
            trailing_controls=actions,
            on_click=lambda e: show_user_details_dialog(
                self.page, 
                user, 
                self.api, 
                self.db, 
                group_id=self.group.get("id")
            )
        )

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
        )
        self.page.open(dlg)

    async def _confirm_ban_action(self, req):
        """Execute the ban and reject request"""
        group_id = self.group.get("id")
        user = req.get("user", {})
        user_id = user.get("id")
        
        # 1. Ban the user
        ban_success = await self.api.ban_user(group_id, user_id)
        
        if ban_success:
            # Invalidate caches since we modified data
            self.api.invalidate_join_requests_cache(group_id)
            self.api.invalidate_bans_cache(group_id)
            
            self.page.open(ft.SnackBar(content=ft.Text("User banned successfully"), bgcolor=colors.success))
            
            # 2. Reject the request (cleanup)
            self._requests = [r for r in self._requests if r.get("id") != req.get("id")]
            self._update_view()
            
            if self.on_update_stats:
                self.on_update_stats({"pending_requests": len(self._requests)})
        else:
            self.page.open(ft.SnackBar(content=ft.Text("Failed to ban user"), bgcolor=colors.danger))

    async def _handle_action(self, req, action):
        group_id = self.group.get("id")
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
            # Invalidate cache since we modified data
            self.api.invalidate_join_requests_cache(group_id)
            if action == "Accept":
                self.api.invalidate_members_cache(group_id)  # New member added
            
            msg = f"Accepted {user.get('displayName')}" if action == "Accept" else f"Rejected {user.get('displayName')}"
            self.page.open(ft.SnackBar(content=ft.Text(msg), bgcolor=colors.success_dim if action == "Accept" else colors.danger_dim))


