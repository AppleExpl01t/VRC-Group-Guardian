
import flet as ft
from ui.theme import colors, spacing, radius, typography
from ui.components.title_bar import TitleBar
from ui.components.glass_card import GlassCard
from ui.components.status_badge import StatusBadge
from services.database import get_database
from utils.crypto import get_integrity_service
import asyncio

class DatabaseView(ft.Container):
    """
    Database Viewer & Integrity Check Dashboard
    Allows viewing of raw database records with cryptographic integrity verification.
    """
    
    def __init__(self, api, on_navigate):
        super().__init__()
        self.api = api
        self.on_navigate = on_navigate
        self.expand = True
        self.padding = spacing.lg
        
        self.current_table = "Users"
        self.search_query = ""
        self.page_size = 50
        self.current_page = 0
        
        # Stats
        self.integrity_stats = {
            "verified": 0,
            "tampered": 0,
            "total": 0
        }
        
        self.content = self._build_ui()
        
    def did_mount(self):
        # Initial data load - run sequentially to avoid conflicts
        self.page.run_task(self._init_data)

    async def _init_data(self):
        try:
            await self._refresh_stats()
            await self._load_table_data()
        except Exception as e:
            print(f"Error initializing database view: {e}")
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Error loading data: {e}"), bgcolor=colors.danger)
            self.page.snack_bar.open = True
            self.page.update()
        
    def _build_ui(self):
        return ft.Column(
            controls=[
                self._build_header(),
                ft.Container(height=spacing.md),
                self._build_stats_row(),
                ft.Container(height=spacing.md),
                self._build_controls(),
                ft.Container(height=spacing.sm),
                self._build_data_grid_container(),
            ],
            expand=True,
            spacing=0
        )
        
    def _build_header(self):
        return ft.Row(
            controls=[
                ft.IconButton(
                    ft.Icons.ARROW_BACK_ROUNDED,
                    icon_color=colors.text_primary,
                    icon_size=24,
                    tooltip="Back to Settings",
                    on_click=lambda _: self.on_navigate("/settings") if self.on_navigate else None
                ),
                ft.Icon(ft.Icons.STORAGE_ROUNDED, size=32, color=colors.accent_primary),
                ft.Column(
                    controls=[
                        ft.Text("Database Inspector", size=24, weight="bold", color=colors.text_primary),
                        ft.Text("View and verify system records", size=14, color=colors.text_secondary),
                    ],
                    spacing=0
                ),
                ft.Container(expand=True),
                # Global Integrity Badge
                self._build_integrity_badge()
            ]
        )
        
    def _build_integrity_badge(self):
        self.integrity_badge_icon = ft.Icon(ft.Icons.SHIELD_ROUNDED, color=colors.success)
        self.integrity_badge_text = ft.Text("System Integrity Verified", color=colors.success, weight="bold")
        
        return GlassCard(
            content=ft.Row(
                controls=[
                    self.integrity_badge_icon,
                    self.integrity_badge_text
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=10,
            width=250
        )

    def _build_stats_row(self):
        self.stat_verified = self._build_mini_stat("Verified", "0", colors.success)
        self.stat_tampered = self._build_mini_stat("Tampered", "0", colors.danger)
        self.stat_total = self._build_mini_stat("Total Records", "0", colors.text_primary)
        
        return ft.Row(
            controls=[
                self.stat_total,
                self.stat_verified,
                self.stat_tampered,
                ft.Container(expand=True),
                ft.ElevatedButton(
                    "Run Forensic Audit",
                    icon=ft.Icons.SECURITY_UPDATE_GOOD_ROUNDED,
                    style=ft.ButtonStyle(
                        color=colors.bg_deepest,
                        bgcolor=colors.accent_primary,
                        shape=ft.RoundedRectangleBorder(radius=radius.md)
                    ),
                    on_click=self._run_audit
                )
            ],
            spacing=spacing.md
        )
        
    def _build_mini_stat(self, label, value, color):
        return GlassCard(
            content=ft.Column(
                controls=[
                    ft.Text(label, size=12, color=colors.text_tertiary),
                    ft.Text(value, size=20, weight="bold", color=color)
                ],
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            width=140,
            padding=10
        )

    def _build_controls(self):
        self.table_selector = ft.Dropdown(
            options=[
                ft.dropdown.Option("Users"),
                ft.dropdown.Option("Join Logs"),
                ft.dropdown.Option("Auto-Mod Logs"),
            ],
            value="Users",
            width=200,
            border_color=colors.glass_border,
            color=colors.text_primary,
            text_size=14,
            on_change=self._on_table_changed
        )
        
        self.search_field = ft.TextField(
            hint_text="Search ID or Username...",
            width=300,
            height=40,
            text_size=14,
            content_padding=10,
            border_radius=radius.md,
            bgcolor=colors.bg_elevated,
            border_color=colors.glass_border,
            on_submit=self._on_search
        )
        
        return ft.Row(
            controls=[
                self.table_selector,
                self.search_field,
                ft.IconButton(ft.Icons.SEARCH_ROUNDED, on_click=self._on_search),
                ft.Container(expand=True),
                ft.IconButton(ft.Icons.REFRESH_ROUNDED, on_click=self._on_refresh)
            ]
        )

    def _build_data_grid_container(self):
        self.data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Username")),
                ft.DataColumn(ft.Text("Data")),
                ft.DataColumn(ft.Text("Integrity")),
            ],
            rows=[],
            heading_row_color=colors.bg_elevated,
            border=ft.border.all(1, colors.glass_border),
            border_radius=radius.md,
            column_spacing=20,
        )
        
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row([self.data_table], scroll=ft.ScrollMode.ALWAYS, expand=True)
                ],
                expand=True,
                scroll=ft.ScrollMode.HIDDEN
            ),
            bgcolor=colors.bg_base,
            border_radius=radius.md,
            border=ft.border.all(1, colors.glass_border),
            expand=True
        )

    async def _on_table_changed(self, e):
        self.current_table = self.table_selector.value
        self.current_page = 0
        await self._load_table_data()

    async def _on_search(self, e):
        self.search_query = self.search_field.value
        self.current_page = 0
        await self._load_table_data()

    async def _on_refresh(self, e):
        await self._refresh_stats()
        await self._load_table_data()

    async def _refresh_stats(self):
        # Run integrity report in background
        report = await asyncio.to_thread(get_database().get_integrity_report)
        
        self.stat_total.content.controls[1].value = str(report["total_records"])
        self.stat_verified.content.controls[1].value = str(report["verified_records"])
        self.stat_tampered.content.controls[1].value = str(report["tampered_records"])
        
        if report["tampered_records"] > 0:
            self.stat_tampered.bgcolor = colors.danger_bg
            self.integrity_badge_icon.name = ft.Icons.GPP_BAD_ROUNDED
            self.integrity_badge_icon.color = colors.danger
            self.integrity_badge_text.value = "Integrity Compromised"
            self.integrity_badge_text.color = colors.danger
        else:
            self.stat_tampered.bgcolor = colors.bg_elevated
            self.integrity_badge_icon.name = ft.Icons.SHIELD_ROUNDED
            self.integrity_badge_icon.color = colors.success
            self.integrity_badge_text.value = "System Integrity Verified"
            self.integrity_badge_text.color = colors.success
            
        self.update()

    async def _load_table_data(self):
        db = get_database()
        rows = []
        columns = []
        
        data = []
        
        # Determine columns and fetch data based on table type
        if self.current_table == "Users":
            columns = [
                ft.DataColumn(ft.Text("User ID")),
                ft.DataColumn(ft.Text("Username")),
                ft.DataColumn(ft.Text("Sightings")),
                ft.DataColumn(ft.Text("First Seen")),
                ft.DataColumn(ft.Text("Status")),
            ]
            
            if self.search_query:
                data = await asyncio.to_thread(db.search_users, self.search_query, 100)
            else:
                data = await asyncio.to_thread(db.get_all_users, 100, 0)
                
            for item in data:
                hash_val = item.get("integrity_hash")
                is_valid = item.get("integrity_valid", False)
                
                if not hash_val:
                    status_icon = ft.Icon(ft.Icons.HELP_OUTLINE, color=colors.text_secondary, size=16)
                    status_text = ft.Text("Unverifyable", color=colors.text_secondary, size=12)
                elif is_valid:
                    status_icon = ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=colors.success, size=16)
                    status_text = ft.Text("Valid", color=colors.success, size=12)
                else:
                    status_icon = ft.Icon(ft.Icons.BROKEN_IMAGE_ROUNDED, color=colors.danger, size=16)
                    status_text = ft.Text("Tampered", color=colors.danger, size=12)

                rows.append(ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(item['user_id'], size=12, font_family="monospace")),
                        ft.DataCell(ft.Text(item.get('current_username', 'Unknown'))),
                        ft.DataCell(ft.Text(str(item.get('sightings_count', 0)))),
                        ft.DataCell(ft.Text(item.get('first_seen', '').split('T')[0])),
                        ft.DataCell(ft.Row([status_icon, status_text])),
                    ],
                ))

        elif self.current_table == "Join Logs":
            columns = [
                ft.DataColumn(ft.Text("Time")),
                ft.DataColumn(ft.Text("User")),
                ft.DataColumn(ft.Text("Event")),
                ft.DataColumn(ft.Text("Location")),
                ft.DataColumn(ft.Text("Status")),
            ]
            # DB service doesn't have a generic "get logs" exposed nicely yet with search,
            # using get_recent_history but ideally we'd add a robust log search.
            # For now, just show recent history.
            data = await asyncio.to_thread(db.get_recent_history, 100)
             
            for item in data:
                hash_val = item.get("integrity_hash")
                
                if not hash_val:
                    status_icon = ft.Icon(ft.Icons.HELP_OUTLINE, color=colors.text_secondary, size=16)
                    status_text = ft.Text("Unverifyable", color=colors.text_secondary, size=12)
                else:
                    is_valid = get_integrity_service().verify_hash(
                        item,
                        ["timestamp", "user_id", "event_kind", "location"],
                        hash_val
                    )
                    
                    if is_valid:
                        status_icon = ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=colors.success, size=16)
                        status_text = ft.Text("Valid", color=colors.success, size=12)
                    else:
                        status_icon = ft.Icon(ft.Icons.BROKEN_IMAGE_ROUNDED, color=colors.danger, size=16)
                        status_text = ft.Text("Tampered", color=colors.danger, size=12)

                rows.append(ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(item.get('timestamp', '').replace('T', ' ')[:19], size=12)),
                        ft.DataCell(ft.Text(item.get('username', 'Unknown'))),
                        ft.DataCell(ft.Text(item.get('event_kind', 'join'))),
                        ft.DataCell(ft.Text(item.get('location', ''))),
                        ft.DataCell(ft.Row([status_icon, status_text])),
                    ]
                ))

        elif self.current_table == "Auto-Mod Logs":
             columns = [
                ft.DataColumn(ft.Text("Time")),
                ft.DataColumn(ft.Text("User")),
                ft.DataColumn(ft.Text("Action")),
                ft.DataColumn(ft.Text("Reason")),
                ft.DataColumn(ft.Text("Status")),
            ]
             # We need a group ID to fetch these... default to current? 
             # Or fetch all? 'get_automod_logs' requires group_id. 
             # For a global view, we might need a new DB method. 
             # I'll just skip this for now or show empty message.
             rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text("Select a group in Dashboard to view specific logs")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text(""))]))
        
        self.data_table.columns = columns
        self.data_table.rows = rows
        self.update()

    async def _run_audit(self, e):
        e.control.text = "Scanning..."
        e.control.disabled = True
        self.update()
        
        await self._refresh_stats()
        
        e.control.text = "Audit Complete"
        e.control.disabled = False
        await asyncio.sleep(2)
        e.control.text = "Run Forensic Audit"
        self.update()
