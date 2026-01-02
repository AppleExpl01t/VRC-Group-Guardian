import flet as ft
from ..theme import colors, radius, spacing, typography
from ..components.neon_button import NeonButton, IconButton
from ..components.user_card import UserCard
from ..dialogs.user_details import show_user_details_dialog
from ..dialogs.confirm_dialog import show_confirm_dialog
from ..mixins import SearchableListMixin
from services.database import get_database

class BansView(ft.Container, SearchableListMixin):
    """
    View for managing banned users in a group using Unified UserCard.
    """
    def __init__(self, group=None, api=None, on_navigate=None, **kwargs):
        self.group = group
        self.api = api
        self.on_navigate = on_navigate
        self.db = get_database()
        
        self._loading = False
        
        # Initialize mixin
        self._setup_search_mixin()
        
        # UI Elements
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
        self._set_items([])
        self._render_list()
        
        group_id = self.group.get("id")
        
        try:
            bans = await self.api.get_cached_group_bans(group_id)
            if bans:
                self._set_items(bans)
        except Exception as e:
            print(f"Error loading bans: {e}")
            
        self._loading = False
        self._render_list()
        
    def _render_list(self):
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
            stats = self._get_search_stats()
            total = stats['total']
            showing = stats['filtered']
            if self._search_query:
                self._count_text.value = f"Showing {showing} of {total} banned users"
            else:
                self._count_text.value = f"{total} banned user{'s' if total != 1 else ''}"
            self._count_text.update()

    def _build_view(self):
        self._count_text = ft.Text("Loading...", color=colors.text_secondary, size=typography.size_xs) # Reduced from sm
        
        # Header - more compact
        header = ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("Banned Users", size=typography.size_xl, weight=ft.FontWeight.W_700, color=colors.text_primary),  # Reduced from 2xl
                        ft.Text(f"Manage banned users of {self.group.get('name')}", color=colors.text_secondary, size=typography.size_sm), # Reduced from default
                    ],
                    spacing=0,  # Reduced from xs
                ),
                ft.Container(expand=True),
                NeonButton(
                    "Ban by Search",
                    icon=ft.Icons.PERSON_SEARCH_ROUNDED,
                    variant=NeonButton.VARIANT_DANGER,
                    height=36,  # Smaller button
                    on_click=lambda e: self._show_user_search_dialog(),
                ),
                ft.Container(width=spacing.sm),
                self._count_text,
            ],
        )
        
        search_field = self._create_search_field(
            placeholder="Filter banned users...",
            expand=True,
            key="bans_search"
        )
        
        search_row = ft.Row(
            controls=[
                search_field,
                IconButton(
                    icon=ft.Icons.REFRESH_ROUNDED, 
                    tooltip="Refresh",
                    on_click=lambda e: self.page.run_task(self._load_all_bans)
                )
            ]
        )
        
        # Bans list - tighter grid
        self._bans_list = ft.GridView(
            max_extent=220,  # Reduced from 240
            child_aspect_ratio=1.05,  # Slightly taller ratio
            spacing=spacing.sm,  # Reduced from md
            run_spacing=spacing.sm,  # Reduced from md
            expand=True,
        )
        
        return ft.Column(
            controls=[
                header,
                ft.Container(height=spacing.sm),  # Reduced from md
                search_row,
                ft.Container(height=spacing.sm),  # Reduced from sm
                ft.Container(content=self._bans_list, expand=True)
            ],
            expand=True,
        )
        


    def _build_ban_items(self):
        if not self._filtered_items and not self._loading:
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
        for ban in self._filtered_items:
            user = ban.get("user", {})
            reason = ban.get("reason", "No reason provided")
            
            def unban(e):
                self._show_unban_confirm(ban)
            
            user_id = user.get("id", "unknown")
            actions = [NeonButton("Unban", variant="success", height=30, on_click=unban, key=f"btn_unban_{user_id}")]

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
        
        def do_unban():
            async def unban_action():
                success = await self.api.unban_user(self.group.get("id"), uid)
                if success:
                    self.page.open(ft.SnackBar(content=ft.Text(f"Unbanned {name}"), bgcolor=colors.success))
                    self.api.invalidate_bans_cache(self.group.get("id"))
                    await self._load_all_bans()
                else:
                    self.page.open(ft.SnackBar(content=ft.Text("Unban failed"), bgcolor=colors.danger))
            self.page.run_task(unban_action)
        
        show_confirm_dialog(
            self.page,
            title="Unban User?",
            message=f"Are you sure you want to unban {name}?",
            on_confirm=do_unban,
            confirm_text="Unban",
            variant="primary",
            icon=ft.Icons.PERSON_ADD_ROUNDED,
        )
        
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
