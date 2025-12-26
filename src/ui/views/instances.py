import asyncio
from datetime import datetime
import flet as ft
from ..theme import colors, radius, spacing, typography
from ..components.glass_card import GlassPanel
from ..components.neon_button import NeonButton, IconButton

class InstancesView(ft.Container):
    def __init__(self, group=None, api=None, on_navigate=None, **kwargs):
        self.group = group
        self.api = api
        self.on_navigate = on_navigate
        self._instances = []
        self._loading = True
        
        # Main content area for the list
        self._content_area = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Build initial content structure
        header_row = ft.Row([
            ft.Column([
                ft.Text("Active Instances", size=typography.size_2xl, weight=ft.FontWeight.W_700, color=colors.text_primary),
                ft.Text(f"Managing instances for {self.group.get('name') if self.group else 'Unknown'}", color=colors.text_secondary),
            ]),
            ft.Row([
                NeonButton("Invite Members", icon=ft.Icons.GROUP_ADD_ROUNDED, on_click=lambda e: self._show_group_invite_dialog()),
                NeonButton("New Instance", icon=ft.Icons.ADD_BOX_ROUNDED, variant="primary", on_click=lambda e: self._show_new_instance_dialog())
            ], spacing=spacing.md)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        content = ft.Column([
            header_row,
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
            
        group_id = self.group.get("id")
        self._instances = await self.api.get_group_instances(group_id)
        self._loading = False
        self._update_view()
        
    def _update_view(self):
        """Update the content area with current state"""
        self._content_area.controls = self._get_content_controls()
        self.update()
        
    def _get_content_controls(self):
        """Get the list of controls for the content area"""
        if self._loading:
            return [ft.Container(
                content=ft.ProgressRing(color=colors.accent_primary), 
                alignment=ft.alignment.center,
                expand=True,
                height=200
            )]
            
        if not self._instances:
             return [ft.Container(
                 content=ft.Column([
                     ft.Icon(ft.Icons.PUBLIC_OFF_ROUNDED, size=48, color=colors.text_tertiary),
                     ft.Container(height=spacing.sm),
                     ft.Text("No active instances found", color=colors.text_secondary, size=typography.size_lg),
                     ft.Text("Group instances will appear here when members create them", color=colors.text_tertiary, size=typography.size_sm),
                 ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=spacing.xs),
                 alignment=ft.alignment.center,
                 expand=True,
                 height=200
             )]
             
        rows = []
        for inst in self._instances:
            # Parse instance
            world = inst.get("world", {})
            name = world.get("name", "Unknown World")
            count = inst.get("memberCount", 0)
            
            # Extract Region if present
            location = inst.get("location", "")
            region = "US"
            if "~region(" in location:
                region = location.split("~region(")[-1].split(")")[0].upper()
            
            # Parse world_id and instance_id from location
            # Format: wrld_xxx:instance_id~region(xx)
            world_id = ""
            instance_id = ""
            if ":" in location:
                parts = location.split(":", 1)
                world_id = parts[0]
                instance_id = parts[1] if len(parts) > 1 else ""
                
            row = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.PUBLIC_ROUNDED, color=colors.text_secondary),
                    ft.Column([
                        ft.Text(name, color=colors.text_primary, weight=ft.FontWeight.BOLD),
                        # Hide raw location, show simplified info
                        ft.Text(f"Region: {region} • {count} active", color=colors.text_tertiary, size=12),
                    ], expand=True, spacing=2),
                    ft.Container(
                        content=ft.Text(region, size=10, color=colors.text_tertiary),
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        border=ft.border.all(1, colors.glass_border),
                        border_radius=4,
                    ),
                    ft.Text(f"{count} users", color=colors.accent_secondary, weight=ft.FontWeight.BOLD),
                    ft.IconButton(
                        ft.Icons.CLOSE_ROUNDED, 
                        tooltip="Close Instance", 
                        icon_color=colors.danger, 
                        on_click=lambda e, loc=location, n=name, wid=world_id, iid=instance_id: self._show_close_confirmation(loc, n, wid, iid)
                    ),
                ], spacing=spacing.sm),
                padding=spacing.md,
                border=ft.border.all(1, colors.glass_border),
                bgcolor=colors.bg_elevated,
                border_radius=radius.md,
                margin=ft.margin.only(bottom=spacing.sm),
            )
            rows.append(row)
            
        return rows
    
    def _show_new_instance_dialog(self):
        """Open dialog to create new group instance"""
        # We need a field for World ID but labelled carefully
        world_field = ft.TextField(
            label="World Link or Source (Hidden)", 
            hint_text="Paste World URL or ID here",
            expand=True
        )
        
        region_dd = ft.Dropdown(
            label="Region",
            value="us",
            options=[
                ft.dropdown.Option("us", "US West"),
                ft.dropdown.Option("use", "US East"),
                ft.dropdown.Option("eu", "Europe"),
                ft.dropdown.Option("jp", "Japan"),
            ],
            expand=True
        )

        access_dd = ft.Dropdown(
            label="Access",
            value="members",
            options=[
                ft.dropdown.Option("members", "Members Only"),
                ft.dropdown.Option("plus", "Group+"),
                ft.dropdown.Option("public", "Public"),
            ],
            expand=True
        )
        
        queue_chk = ft.Switch(label="Queue Enabled", value=True)
        age_chk = ft.Switch(label="Age Gate", value=False)
        name_field = ft.TextField(label="Custom Instance Name (VRC+)")
        
        def create_click(e):
            val = world_field.value.strip()
            if not val: return
            
            # Extract world ID if a URL is pasted
            wid = val
            if "wrld_" in val:
                # simple extraction: find wrld_... until end or non-valid char
                import re
                match = re.search(r"(wrld_[a-f0-9\-]+)", val)
                if match:
                   wid = match.group(1)
            
            self.page.close_dialog()
            self.page.run_task(self._do_create_instance, 
                               world_id=wid,
                               region=region_dd.value,
                               access=access_dd.value,
                               queue=queue_chk.value,
                               age_gate=age_chk.value,
                               name=name_field.value if name_field.value else None)

        dlg = ft.AlertDialog(
            title=ft.Text("New Group Instance"),
            content=ft.Column([
                ft.Text(f"For Group: {self.group.get('name')}", color=colors.accent_primary),
                world_field,
                ft.Row([region_dd, access_dd], spacing=10),
                ft.Row([queue_chk, age_chk], spacing=20),
                name_field, 
            ], tight=True, width=500),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.page.close_dialog()),
                NeonButton("Create", on_click=create_click, variant="primary"),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    async def _do_create_instance(self, world_id, region, access, queue, age_gate, name=None):
        if not self.api: return
        self.page.open(ft.SnackBar(ft.Text("Creating instance..."), bgcolor=colors.bg_elevated))
        
        print(f"[DEBUG] Creating instance: world={world_id}, region={region}, access={access}, queue={queue}, age={age_gate}, name={name}")
        
        try:
            res = await self.api.create_instance(
                world_id=world_id,
                type="group",
                region=region,
                group_id=self.group.get("id"),
                group_access_type=access,
                queue_enabled=queue,
                name=name
            )
            print(f"[DEBUG] Create instance result: {res}")
            
            if res:
                 self.page.open(ft.SnackBar(ft.Text(f"Instance Created Successfully"), bgcolor=colors.success))
                 self._loading = True
                 self._update_view()
                 await self._load_data()
            else:
                 self.page.open(ft.SnackBar(ft.Text("Failed to create instance (API returned None)"), bgcolor=colors.danger))
        except Exception as e:
            print(f"[DEBUG] Create instance error: {e}")
            self.page.open(ft.SnackBar(ft.Text(f"Error: {str(e)}"), bgcolor=colors.danger))
    
    def _show_close_confirmation(self, location: str, world_name: str, world_id: str, instance_id: str):
        """Show confirmation dialog before closing an instance"""
        
        def close_dlg(e):
            self.page.close(dlg)
        
        def confirm_close(e):
            self.page.close(dlg)
            self.page.run_task(lambda: self._close_instance(world_id, instance_id, world_name))
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.WARNING_ROUNDED, color=colors.danger, size=28),
                ft.Container(width=spacing.sm),
                ft.Text("Close Instance?", weight=ft.FontWeight.W_600),
            ]),
            content=ft.Column([
                ft.Text(
                    f"Are you sure you want to close this instance?",
                    color=colors.text_primary,
                    size=typography.size_base,
                ),
                ft.Container(height=spacing.sm),
                ft.Container(
                    content=ft.Column([
                        ft.Text(world_name, weight=ft.FontWeight.BOLD, color=colors.text_primary),
                        # Hidden ID/Location
                        ft.Text("Public Group Instance", color=colors.text_tertiary, size=12),
                    ], spacing=2),
                    padding=spacing.md,
                    bgcolor=colors.bg_base,
                    border_radius=radius.md,
                ),
                ft.Container(height=spacing.md),
                ft.Text(
                    "⚠️ All users in this instance will be disconnected.",
                    color=colors.warning,
                    size=typography.size_sm,
                ),
            ], tight=True, width=400),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                NeonButton(
                    text="Close Instance",
                    icon=ft.Icons.CLOSE_ROUNDED,
                    variant=NeonButton.VARIANT_DANGER,
                    on_click=confirm_close,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=colors.bg_elevated,
            shape=ft.RoundedRectangleBorder(radius=radius.lg),
        )
        self.page.open(dlg)
    
    async def _close_instance(self, world_id: str, instance_id: str, world_name: str):
        """Close the instance via API"""
        if not self.api:
            return
        
        # Show loading snackbar
        self.page.open(ft.SnackBar(
            content=ft.Row([
                ft.ProgressRing(width=16, height=16, stroke_width=2, color=colors.text_primary),
                ft.Container(width=spacing.sm),
                ft.Text(f"Closing {world_name}..."),
            ]),
            bgcolor=colors.bg_elevated,
        ))
        
        success = await self.api.close_group_instance(world_id, instance_id)
        
        if success:
            self.page.open(ft.SnackBar(
                content=ft.Text(f"✓ Instance closed: {world_name}"),
                bgcolor=colors.success,
            ))
            # Refresh the list
            self._loading = True
            self._update_view()
            await self._load_data()
        else:
            self.page.open(ft.SnackBar(
                content=ft.Text(f"✗ Failed to close instance"),
                bgcolor=colors.danger,
            ))


    def _show_group_invite_dialog(self):
        """Show dialog for group invites"""
        grp_name = self.group.get("name") if self.group else "Unknown Group"
        
        def confirm(e):
            self.page.close_dialog()
            self.page.run_task(self._do_invite_online_group_members)

        dlg = ft.AlertDialog(
            title=ft.Text("Invite Online Group Members"),
            content=ft.Column([
                ft.Text(f"Target Group: {grp_name}", weight=ft.FontWeight.W_600),
                ft.Container(height=10),
                ft.Text("This will scan your ONLINE friends list and invite anyone who is also a member of this group.", size=typography.size_sm),
                ft.Text("Note: This requires you to be in an instance.", color=colors.warning, size=typography.size_xs),
            ], tight=True, width=400),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.page.close_dialog()),
                NeonButton("Invite", on_click=confirm, variant="primary"),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=colors.bg_elevated,
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    async def _do_invite_online_group_members(self):
        """Invite friends in group logic"""
        if not self.api or not self.group: return
        grp_id = self.group.get("id")
        
        # 0. Check Location
        loc = await self.api.get_my_location()
        if not loc:
            self.page.open(ft.SnackBar(ft.Text("You must be in an instance to send invites."), bgcolor=colors.danger))
            return

        # 1. Fetch Friends
        self.page.open(ft.SnackBar(ft.Text("Fetching friends..."), bgcolor=colors.bg_elevated))
        friends = await self.api.get_all_friends()
        if not friends: 
            self.page.open(ft.SnackBar(ft.Text("No online friends found."), bgcolor=colors.warning))
            return
        
        # 2. Filter by group (fetch first 100 members for now as optimization)
        # Ideally we loop friends and check membership, but that's N requests.
        self.page.open(ft.SnackBar(ft.Text("Filtering group members..."), bgcolor=colors.bg_elevated))
        
        members = await self.api.search_group_members(grp_id, limit=100)
        member_ids = {m['user']['id'] for m in members}
             
        targets = [f for f in friends if f['id'] in member_ids]
        
        if not targets:
            self.page.open(ft.SnackBar(ft.Text("No online friends found in this group (checked recent members)."), bgcolor=colors.warning))
            return
            
        # 3. Send Invites
        count = 0
        self.page.open(ft.SnackBar(ft.Text(f"Inviting {len(targets)} members..."), bgcolor=colors.accent_primary))
        for f in targets:
            await self.api.invite_to_instance(f['id'], loc['world_id'], loc['instance_id'])
            count += 1
            await asyncio.sleep(1.2) # Rate limit
            
        self.page.open(ft.SnackBar(ft.Text(f"Sent {count} invites successfully."), bgcolor=colors.success))
