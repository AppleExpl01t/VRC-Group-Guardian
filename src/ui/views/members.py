import flet as ft
import logging
from ..theme import colors, radius, spacing, typography
from ..components.neon_button import NeonButton, IconButton
from ..components.glass_card import GlassCard
from ..components.user_card import UserCard
from ..dialogs.user_details import show_user_details_dialog
from ..mixins import SearchableListMixin
from services.database import get_database

logger = logging.getLogger(__name__)

class MembersView(ft.Container, SearchableListMixin):
    """
    View for managing group members using unified UserCard components.
    """
    def __init__(self, group=None, api=None, on_navigate=None, **kwargs):
        self.group = group
        self.api = api
        self.on_navigate = on_navigate
        self._members_list = None
        self._loading = False
        
        # Initialize mixin
        self._setup_search_mixin()
        
        self.db = get_database()
        
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
        self._set_items([]) # Clear items via mixin
        self._render_list()
        
        group_id = self.group.get("id")
        
        # Load all members
        all_loaded = []
        
        # Load all members
        offset = 0
        limit = 50
        has_more = True
        
        while has_more:
            try:
                new_members = await self.api.get_cached_group_members(
                    group_id, 
                    limit=limit, 
                    offset=offset
                )
                
                if new_members is None:
                    # API error handled inside get_cached_group_members generally, but just in case
                    has_more = False
                    continue

                if len(new_members) < limit:
                    has_more = False
                    
                all_loaded.extend(new_members)
                offset += len(new_members)
                
                # Update UI progressively
                self._set_items(all_loaded)
            except Exception as e:
                import traceback
                logger.error(f"Error loading members: {e}")
                traceback.print_exc()
                has_more = False
                self.page.open(ft.SnackBar(ft.Text(f"Failed to load all members: {e}"), bgcolor=colors.danger))
        
        self._loading = False
        self._set_items(all_loaded)
        
    def _render_list(self):
        """Render the filtered list (called by mixin)"""
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
        # Header - more compact
        header = ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("Members", size=typography.size_xl, weight=ft.FontWeight.W_700, color=colors.text_primary),  # Reduced from 2xl
                        ft.Text(f"Manage members of {self.group.get('name')}", color=colors.text_secondary, size=typography.size_sm), # Reduced from default
                    ],
                    spacing=0,  # Reduced from xs
                ),
            ],
        )
        
        search_field = self._create_search_field(
            placeholder="Search members...",
            expand=False,
            # key="members_search" # Removed to fix focus loss bug
        )
        
        # Members list - tighter grid
        self._members_list = ft.GridView(
            max_extent=220,  # Reduced from 240
            child_aspect_ratio=1.35,  # Adjusted ratio
            spacing=spacing.sm,  # Reduced from md
            run_spacing=spacing.sm,  # Reduced from md
            expand=True,
        )
        
        return ft.Column([
            header,
            ft.Container(height=spacing.sm),  # Reduced from md
            search_field,
            ft.Container(height=spacing.xs),
            ft.Container(content=self._members_list, expand=True)
        ], expand=True)
        
        # Note: SearchableListMixin update logic needs to be careful not to rebuild the entire view continuously.
        # However, since we are only calling self._members_list.update() in _render_list, 
        # the text field (search_field) should NOT lose focus unless the parent itself re-renders.
        # Reducing spacing between search and content.
        


    def _build_member_items(self):
        # Use _filtered_items from mixin
        if self._loading and not self._filtered_items:
             return [ft.Container(
                 content=ft.ProgressRing(color=colors.accent_primary),
                 alignment=ft.alignment.center,
                 height=100
             )]

        if not self._filtered_items:
            return [ft.Text("No members found", color=colors.text_tertiary, text_align=ft.TextAlign.CENTER)]
            
        items = []
        for member in self._filtered_items:
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
        show_user_details_dialog(
            self.page, 
            user, 
            self.api, 
            self.db, 
            group_id=self.group.get("id"),
            on_update=lambda: self.page.run_task(self._load_all_members) # Refresh list if action taken
        )
