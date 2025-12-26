import flet as ft
from ..theme import colors, radius, spacing, typography
from ..components.neon_button import NeonButton, IconButton
from ..components.glass_card import GlassCard
from ..components.user_card import UserCard
from ..dialogs.user_details import show_user_details_dialog
from services.database import get_database

class MembersView(ft.Container):
    """
    View for managing group members using unified UserCard components.
    """
    def __init__(self, group=None, api=None, on_navigate=None, **kwargs):
        self.group = group
        self.api = api
        self.on_navigate = on_navigate
        self._members = []
        self._all_members = []
        self._loading = False
        self._search_query = ""
        self.db = get_database()
        
        # UI Elements
        self._search_field = None
        self._members_list = None
        
        content = self._build_view()
        
        super().__init__(
            content=content,
            padding=spacing.lg,
            expand=True,
            **kwargs
        )
        
    def did_mount(self):
        self.page.run_task(self._load_all_members)
        
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
            new_members = await self.api.get_cached_group_members(
                group_id, 
                limit=limit, 
                offset=offset
            )
            
            if len(new_members) < limit:
                has_more = False
                
            self._all_members.extend(new_members)
            offset += len(new_members)
            
            # Update UI progressively
            self._apply_filter()
        
        self._loading = False
        self._apply_filter()
        
    def _apply_filter(self):
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
        
        search_row = ft.Row([
            self._search_field,
            IconButton(ft.Icons.SEARCH_ROUNDED, on_click=lambda e: self._handle_search(e))
        ])
        
        self._members_list = ft.ListView(
            expand=True,
            spacing=spacing.xs,
        )
        
        return ft.Column([
            header,
            ft.Container(height=spacing.md),
            search_row,
            ft.Container(height=spacing.sm),
            ft.Container(content=self._members_list, expand=True)
        ], expand=True)
        
    def _handle_search(self, e):
        self._search_query = self._search_field.value
        self._apply_filter()

    def _build_member_items(self):
        if not self._members and not self._loading:
            return [ft.Text("No members found", color=colors.text_tertiary, text_align=ft.TextAlign.CENTER)]
            
        items = []
        for member in self._members:
            user = member.get("user", {})
            
            card = UserCard(
                user_data=user,
                api=self.api,
                db=self.db,
                subtitle=member.get("managerNotes") or "Member",
                on_click=lambda e, u=user: self._open_details(u),
            )
            items.append(card)
            
        return items

    def _open_details(self, user):
        print(f"DEBUG: MembersView._open_details called for user {user.get('displayName')}")
        show_user_details_dialog(
            self.page, 
            user, 
            self.api, 
            self.db, 
            group_id=self.group.get("id"),
            on_update=lambda: self.page.run_task(self._load_all_members) # Refresh list if action taken
        )
