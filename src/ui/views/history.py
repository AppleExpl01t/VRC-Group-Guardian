import flet as ft
from datetime import datetime
from ..theme import colors, radius, spacing, typography
from ..components.user_card import UserCard
from ..dialogs.user_details import show_user_details_dialog
from services.database import get_database

class HistoryView(ft.Container):
    """
    History / Database View
    =======================
    View and search persistent user history, join logs, and logs.
    Features ported from FCH-Toolkit DB.
    """
    def __init__(self, api=None, on_navigate=None, **kwargs):
        self.api = api
        self.on_navigate = on_navigate
        self._db = get_database()
        
        # State
        self._active_tab = "joins"
        self._logs = []
        
        # Controls
        self._content_area = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=spacing.sm)
        self._tabs = None
        
        content = self._build_view()
        
        super().__init__(
            content=content,
            expand=True,
            padding=spacing.lg,
            **kwargs,
        )

    def did_mount(self):
        self._load_tab_content()

    def _build_view(self):
        self._tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="Recent Joins",
                    icon=ft.Icons.HISTORY,
                ),
                ft.Tab(
                    text="User Database",
                    icon=ft.Icons.PERSON_SEARCH,
                ),
            ],
            on_change=self._on_tab_change,
        )
        
        return ft.Column([
            ft.Text("History & Database", size=typography.size_2xl, weight="bold", color=colors.text_primary),
            self._tabs,
            ft.Divider(color=colors.glass_border),
            self._content_area,
        ], expand=True)

    def _on_tab_change(self, e):
        idx = e.control.selected_index
        if idx == 0:
            self._active_tab = "joins"
        else:
            self._active_tab = "users"
        self._load_tab_content()

    def _load_tab_content(self):
        self._content_area.controls.clear()
        
        if self._active_tab == "joins":
            self._render_joins_tab()
        else:
            self._render_users_tab()
            
        self._content_area.update()

    def _render_joins_tab(self):
        logs = self._db.get_recent_history(limit=50)
        
        if not logs:
            self._content_area.controls.append(
                ft.Text("No history logs found.", italic=True, color=colors.text_secondary)
            )
            return

        items = []
        for log in logs:
            uname = log.get("username", "Unknown")
            uid = log.get("user_id", "")
            ts = log.get("timestamp", "")
            loc = log.get("location", "")
            
            user_data = {"id": uid, "displayName": uname}
            
            # Subtitle with timestamp and location
            sub = f"{ts} • {loc}" if loc else ts
            
            items.append(
                UserCard(
                    user_data=user_data,
                    api=self.api,
                    db=self._db,
                    subtitle=sub,
                    on_click=lambda e, u=user_data: show_user_details_dialog(
                        self.page, u, self.api, self._db
                    )
                )
            )
        
        self._content_area.controls = items

    def _render_users_tab(self):
        # We need a search box for users because there could be thousands
        search_field = ft.TextField(
             prefix_icon=ft.Icons.SEARCH,
             hint_text="Search local user database...",
             on_submit=self._do_search_users,
             border_radius=radius.md,
             bgcolor=colors.bg_elevated
        )
        
        self._user_list_col = ft.Column(scroll="auto", expand=True, spacing=spacing.sm)
        
        self._content_area.controls = [
            search_field,
            ft.Container(height=spacing.sm),
            self._user_list_col
        ]

    def _do_search_users(self, e):
        val = e.control.value
        users = self._db.search_users(val)
        
        if not users:
            self._user_list_col.controls = [
                ft.Text("No users found", italic=True, color=colors.text_secondary)
            ]
        else:
            items = []
            for u in users:
                uname = u.get("username", "Unknown")
                uid = u.get("user_id", "")
                note = u.get("note") or ""
                
                # Construct user data from DB record 
                # DB keys might differ slightly, standardized here
                user_data = {
                    "id": uid, 
                    "displayName": uname,
                }
                
                items.append(
                    UserCard(
                        user_data=user_data,
                        api=self.api,
                        db=self._db,
                        subtitle=note if note else None,
                        on_click=lambda e, u=user_data: self._show_details_and_refresh(u)
                    )
                )
            self._user_list_col.controls = items
        self._user_list_col.update()

    def _show_details_and_refresh(self, user_data):
        """Show details and refresh list on close to reflect note changes"""
        def on_update():
            # Ideally we'd remember the search query. For now, we can just clear or keep basic.
            pass
            
        show_user_details_dialog(
            self.page, 
            user_data, 
            self.api, 
            self._db,
            on_update=on_update
        )
