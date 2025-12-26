"""
History / Database View
=======================
View and search persistent user history, join logs, and logs.
Features ported from FCH-Toolkit DB.
"""

import flet as ft
from datetime import datetime
from ..theme import colors, radius, spacing, typography
from ..components.glass_card import GlassCard
from ..components.neon_button import NeonButton
from services.database import get_database

class HistoryView(ft.Container):
    def __init__(self, api=None, on_navigate=None, **kwargs):
        self.api = api
        self.on_navigate = on_navigate
        self._db = get_database()
        
        # State
        self._active_tab = "joins"
        self._logs = []
        
        # Controls
        self._content_area = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
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
            
            # Format nicely
            items.append(
                ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(uname, weight="bold", color=colors.text_primary),
                            ft.Text(ts, size=10, color=colors.text_tertiary),
                        ], expand=True),
                        ft.Column([
                             ft.Text(loc, size=10, color=colors.text_secondary, no_wrap=True),
                             ft.Text(uid, size=8, color=colors.text_tertiary, font_family="Consolas"),
                        ], alignment="end"),
                    ]),
                    padding=spacing.sm,
                    bgcolor=colors.bg_glass,
                    border_radius=radius.sm,
                    border=ft.border.only(bottom=ft.BorderSide(1, colors.glass_border))
                )
            )
        
        self._content_area.controls = items

    def _render_users_tab(self):
        # We need a search box for users because there could be thousands
        search_field = ft.TextField(
             prefix_icon=ft.Icons.SEARCH,
             hint_text="Search local user database...",
             on_submit=self._do_search_users
        )
        
        self._user_list_col = ft.Column(scroll="auto", expand=True)
        
        self._content_area.controls = [
            ft.Row([search_field], alignment="center"),
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
                wl = u.get("is_watchlisted")
                
                # Check for note/watchlist markers
                icons = []
                if wl: icons.append(ft.Icon(ft.Icons.VISIBILITY, size=14, color=colors.accent_primary))
                if note: icons.append(ft.Icon(ft.Icons.NOTE, size=14, color=colors.text_secondary))
                
                items.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Row([
                                    ft.Text(uname, weight="bold", color=colors.text_primary),
                                    *icons
                                ], spacing=4),
                                ft.Text(uid, size=10, color=colors.text_tertiary, font_family="Consolas"),
                            ], expand=True),
                            ft.Text(note[:50] + "..." if len(note) > 50 else note, size=11, color=colors.text_secondary, italic=True)
                        ]),
                        padding=spacing.sm,
                        bgcolor=colors.bg_glass,
                        border_radius=radius.sm,
                        border=ft.border.only(bottom=ft.BorderSide(1, colors.glass_border))
                    )
                )
            self._user_list_col.controls = items
        self._user_list_col.update()
