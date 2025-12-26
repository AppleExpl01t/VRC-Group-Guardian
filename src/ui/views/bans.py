import flet as ft
from ..theme import colors, radius, spacing, typography
from ..components.neon_button import NeonButton, IconButton
from ..components.user_card import UserCard
from ..dialogs.user_details import show_user_details_dialog
from services.database import get_database

class BansView(ft.Container):
    """
    View for managing banned users in a group using Unified UserCard.
    """
    def __init__(self, group=None, api=None, on_navigate=None, **kwargs):
        self.group = group
        self.api = api
        self.on_navigate = on_navigate
        self.db = get_database()
        
        # State
        self._bans = []
        self._all_bans = []
        self._loading = False
        self._search_query = ""
        
        # UI Elements
        self._search_field = None
        self._bans_list = None
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
            bans = await self.api.get_cached_group_bans(group_id)
            if bans:
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
        
        self._search_field = ft.TextField(
            hint_text="Filter banned users...",
            prefix_icon=ft.Icons.SEARCH,
            bgcolor=colors.bg_elevated,
            border_radius=radius.md,
            border_color=colors.glass_border,
            color=colors.text_primary,
            on_submit=self._handle_search,
            on_change=self._handle_search,
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
        
        self._bans_list = ft.ListView(expand=True, spacing=spacing.xs)
        
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
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    padding=spacing.xl,
                )
            ]
            
        items = []
        for ban in self._bans:
            user = ban.get("user", {})
            reason = ban.get("reason", "No reason provided")
            
            def unban(e):
                self._show_unban_confirm(ban)
                
            actions = [NeonButton("Unban", variant="success", height=30, on_click=unban)]

            items.append(
                UserCard(
                    user_data=user,
                    api=self.api,
                    db=self.db,
                    subtitle=f"Reason: {reason}",
                    highlight_color=colors.danger,
                    trailing_controls=actions,
                    on_click=lambda e, u=user: show_user_details_dialog(
                        self.page, u, self.api, self.db, self.group.get("id"), on_update=lambda: self.page.run_task(self._load_all_bans)
                    )
                )
            )
        return items

    def _show_unban_confirm(self, ban):
        user = ban.get("user", {})
        name = user.get("displayName", "Unknown")
        uid = user.get("id")
        
        def confirm(e):
             self.page.close(dlg)
             async def do_unban():
                 success = await self.api.unban_user(self.group.get("id"), uid)
                 if success:
                     self.page.open(ft.SnackBar(content=ft.Text(f"Unbanned {name}"), bgcolor=colors.success))
                     self.api.invalidate_bans_cache(self.group.get("id"))
                     await self._load_all_bans()
                 else:
                     self.page.open(ft.SnackBar(content=ft.Text("Unban failed"), bgcolor=colors.danger))
             self.page.run_task(do_unban)
             
        dlg = ft.AlertDialog(
            title=ft.Text("Unban User?"),
            content=ft.Text(f"Are you sure you want to unban {name}?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.page.close(dlg)),
                ft.TextButton("Unban", style=ft.ButtonStyle(color=colors.success), on_click=confirm),
            ],
            bgcolor=colors.bg_elevated,
        )
        self.page.open(dlg)
        
    def _show_user_search_dialog(self):
        """Show dialog to search VRChat users to ban"""
        search_field = ft.TextField(
            hint_text="Search users to ban...",
            autofocus=True,
            expand=True,
            on_submit=lambda e: self.page.run_task(do_search)
        )
        
        results_list = ft.ListView(expand=True, spacing=spacing.xs)
        loading = ft.ProgressRing(visible=False)
        
        async def do_search():
            query = search_field.value
            if not query: return
            
            loading.visible = True
            results_list.controls.clear()
            dlg.update()
            
            try:
                # Use general user search
                results = await self.api.search_users(query)
                
                controls = []
                for user in results:
                    controls.append(
                       UserCard(
                           user_data=user,
                           api=self.api,
                           compact=True,
                           on_click=lambda e, u=user: show_user_details_dialog(
                               self.page, u, self.api, self.db, self.group.get("id"), 
                               on_update=lambda: self.page.run_task(self._load_all_bans)
                           ) # Clicking opens details which has "Ban" button
                       )
                    )
                
                if not controls:
                    controls.append(ft.Text("No users found", color=colors.text_secondary))
                    
                results_list.controls = controls
                
            except Exception as e:
                results_list.controls = [ft.Text(f"Search failed: {e}", color=colors.danger)]
                
            loading.visible = False
            dlg.update()
            
        dlg = ft.AlertDialog(
            title=ft.Text("Ban New User"),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([search_field, IconButton(ft.Icons.SEARCH, on_click=lambda e: self.page.run_task(do_search))]),
                    loading,
                    ft.Container(content=results_list, height=300),
                ]),
                width=500,
                height=400,
            ),
            actions=[ft.TextButton("Close", on_click=lambda e: self.page.close(dlg))],
            bgcolor=colors.bg_elevated,
        )
        self.page.open(dlg)
