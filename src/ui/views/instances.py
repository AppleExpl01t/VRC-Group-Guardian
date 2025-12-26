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
        
        # Get group name for button
        group_name = self.group.get('name', 'Group') if self.group else 'Group'
        
        # Build initial content structure
        header_row = ft.Row([
            ft.Column([
                ft.Text("Active Instances", size=typography.size_2xl, weight=ft.FontWeight.W_700, color=colors.text_primary),
                ft.Text(f"Managing instances for {group_name}", color=colors.text_secondary),
            ]),
            ft.Row([
                NeonButton("Invite Members", icon=ft.Icons.GROUP_ADD_ROUNDED, on_click=lambda e: self._show_group_invite_dialog()),
                NeonButton(f"Open new {group_name} instance", icon=ft.Icons.ADD_BOX_ROUNDED, variant="primary", on_click=lambda e: self._show_new_instance_dialog())
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
        self._instances = await self.api.get_cached_group_instances(group_id)
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
        """Open dialog to create new group instance with world search"""
        group_name = self.group.get('name', 'Group') if self.group else 'Group'
        
        # State for selected world
        selected_world = {"id": None, "name": None, "thumbnail": None}
        
        # Search field
        search_field = ft.TextField(
            label="Search Worlds",
            hint_text="Type to search VRChat worlds...",
            prefix_icon=ft.Icons.SEARCH,
            bgcolor=colors.bg_base,
            border_radius=radius.md,
            border_color=colors.glass_border,
            color=colors.text_primary,
            expand=True,
        )
        
        # OR paste world ID field
        world_id_field = ft.TextField(
            label="Or paste World ID directly",
            hint_text="wrld_xxx or VRChat world URL",
            bgcolor=colors.bg_base,
            border_radius=radius.md,
            border_color=colors.glass_border,
            color=colors.text_primary,
            expand=True,
        )
        
        # Search results container
        search_results = ft.Column(
            controls=[],
            spacing=spacing.xs,
            scroll=ft.ScrollMode.AUTO,
        )
        
        search_results_container = ft.Container(
            content=search_results,
            height=200,
            border=ft.border.all(1, colors.glass_border),
            border_radius=radius.md,
            bgcolor=colors.bg_base,
            padding=spacing.sm,
        )
        
        # Selected world display
        selected_world_display = ft.Container(
            content=ft.Text("No world selected", color=colors.text_tertiary, italic=True),
            padding=spacing.sm,
            visible=True,
        )
        
        # Loading indicator
        loading_indicator = ft.Container(
            content=ft.ProgressRing(color=colors.accent_primary, width=20, height=20),
            visible=False,
            alignment=ft.alignment.center,
        )
        
        def update_selected_display():
            if selected_world["id"]:
                selected_world_display.content = ft.Row([
                    ft.Container(
                        content=ft.Image(
                            src=selected_world["thumbnail"],
                            width=60,
                            height=40,
                            fit=ft.ImageFit.COVER,
                            border_radius=radius.sm,
                        ) if selected_world["thumbnail"] else ft.Icon(ft.Icons.PUBLIC_ROUNDED, size=24),
                        border_radius=radius.sm,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                    ft.Container(width=spacing.sm),
                    ft.Column([
                        ft.Text(selected_world["name"] or "Unknown World", weight=ft.FontWeight.BOLD, color=colors.text_primary, size=typography.size_sm),
                        ft.Text(selected_world["id"], size=typography.size_xs, color=colors.text_tertiary),
                    ], spacing=0, expand=True),
                    ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=colors.success, size=20),
                ], spacing=spacing.sm)
                selected_world_display.bgcolor = colors.success + "22"
                selected_world_display.border = ft.border.all(1, colors.success + "44")
                selected_world_display.border_radius = radius.md
            else:
                selected_world_display.content = ft.Text("No world selected", color=colors.text_tertiary, italic=True)
                selected_world_display.bgcolor = None
                selected_world_display.border = None
            
            if selected_world_display.page:
                selected_world_display.update()
        
        def select_world(world):
            selected_world["id"] = world.get("id")
            selected_world["name"] = world.get("name")
            selected_world["thumbnail"] = world.get("thumbnailImageUrl") or world.get("imageUrl")
            # Also fill in the world ID field
            world_id_field.value = world.get("id", "")
            if world_id_field.page:
                world_id_field.update()
            update_selected_display()
        
        def build_world_result_item(world):
            name = world.get("name", "Unknown World")
            author = world.get("authorName", "Unknown")
            thumbnail = world.get("thumbnailImageUrl") or world.get("imageUrl")
            occupants = world.get("occupants", 0)
            
            return ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Image(
                            src=thumbnail,
                            width=80,
                            height=45,
                            fit=ft.ImageFit.COVER,
                            border_radius=radius.sm,
                        ) if thumbnail else ft.Container(
                            content=ft.Icon(ft.Icons.PUBLIC_ROUNDED, color=colors.text_tertiary),
                            width=80,
                            height=45,
                            bgcolor=colors.bg_elevated,
                            border_radius=radius.sm,
                            alignment=ft.alignment.center,
                        ),
                        border_radius=radius.sm,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                    ft.Column([
                        ft.Text(name, weight=ft.FontWeight.W_500, color=colors.text_primary, size=typography.size_sm, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(f"by {author} • {occupants} online", size=typography.size_xs, color=colors.text_tertiary),
                    ], spacing=0, expand=True),
                ], spacing=spacing.sm),
                padding=spacing.sm,
                border_radius=radius.md,
                bgcolor=colors.bg_elevated,
                border=ft.border.all(1, colors.glass_border),
                on_click=lambda e, w=world: select_world(w),
                ink=True,
            )
        
        async def do_search():
            query = search_field.value.strip() if search_field.value else ""
            if not query or len(query) < 2:
                return
            
            loading_indicator.visible = True
            search_results.controls = []
            if loading_indicator.page:
                loading_indicator.update()
            if search_results.page:
                search_results.update()
            
            try:
                worlds = await self.api.search_worlds(query, n=10)
                loading_indicator.visible = False
                
                if not worlds:
                    search_results.controls = [
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, size=32, color=colors.text_tertiary),
                                ft.Text("No worlds found", color=colors.text_secondary),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            alignment=ft.alignment.center,
                            padding=spacing.lg,
                        )
                    ]
                else:
                    search_results.controls = [build_world_result_item(w) for w in worlds]
                
                if loading_indicator.page:
                    loading_indicator.update()
                if search_results.page:
                    search_results.update()
                    
            except Exception as e:
                print(f"World search error: {e}")
                loading_indicator.visible = False
                search_results.controls = [
                    ft.Text(f"Search error: {str(e)}", color=colors.danger)
                ]
                if loading_indicator.page:
                    loading_indicator.update()
                if search_results.page:
                    search_results.update()
        
        def on_search_submit(e):
            self.page.run_task(do_search)
        
        search_field.on_submit = on_search_submit
        
        # Search button
        search_btn = IconButton(
            icon=ft.Icons.SEARCH_ROUNDED,
            tooltip="Search",
            on_click=lambda e: self.page.run_task(do_search),
        )
        
        # Region dropdown
        region_dd = ft.Dropdown(
            label="Region",
            value="us",
            options=[
                ft.dropdown.Option("us", "US West"),
                ft.dropdown.Option("use", "US East"),
                ft.dropdown.Option("eu", "Europe"),
                ft.dropdown.Option("jp", "Japan"),
            ],
            bgcolor=colors.bg_base,
            border_color=colors.glass_border,
            color=colors.text_primary,
            expand=True
        )

        # Access dropdown
        access_dd = ft.Dropdown(
            label="Access Type",
            value="members",
            options=[
                ft.dropdown.Option("members", "Members Only"),
                ft.dropdown.Option("plus", "Group+"),
                ft.dropdown.Option("public", "Public"),
            ],
            bgcolor=colors.bg_base,
            border_color=colors.glass_border,
            color=colors.text_primary,
            expand=True
        )
        
        queue_chk = ft.Switch(label="Queue Enabled", value=True, active_color=colors.accent_primary)
        age_chk = ft.Switch(label="18+ Age Gate", value=False, active_color=colors.accent_primary)
        name_field = ft.TextField(
            label="Custom Instance Name (VRC+ only)",
            bgcolor=colors.bg_base,
            border_radius=radius.md,
            border_color=colors.glass_border,
            color=colors.text_primary,
        )
        
        def close_dlg(e):
            self.page.close(dlg)
        
        def create_click(e):
            # Get world ID from either selection or direct input
            wid = selected_world["id"] or world_id_field.value.strip() if world_id_field.value else ""
            
            if not wid:
                self.page.open(ft.SnackBar(
                    content=ft.Text("Please search and select a world, or enter a World ID"),
                    bgcolor=colors.danger
                ))
                return
            
            # Extract world ID if a URL is pasted
            if "wrld_" in wid and not wid.startswith("wrld_"):
                import re
                match = re.search(r"(wrld_[a-f0-9\-]+)", wid)
                if match:
                   wid = match.group(1)
            
            self.page.close(dlg)
            
            self.page.run_task(
                self._do_create_instance, 
                world_id=wid,
                region=region_dd.value,
                access=access_dd.value,
                queue=queue_chk.value,
                age_gate=age_chk.value,
                name=name_field.value if name_field.value else None
            )

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.ADD_BOX_ROUNDED, color=colors.accent_primary, size=28),
                ft.Container(width=spacing.sm),
                ft.Text(f"Open new {group_name} instance", weight=ft.FontWeight.W_600),
            ]),
            content=ft.Column([
                ft.Text(f"Create a new group instance for {group_name}", color=colors.text_secondary, size=typography.size_sm),
                ft.Container(height=spacing.md),
                
                # World Search Section
                ft.Text("🌍 Select a World", weight=ft.FontWeight.W_600, color=colors.text_primary),
                ft.Container(height=spacing.xs),
                ft.Row([search_field, search_btn], spacing=spacing.sm),
                ft.Container(height=spacing.xs),
                loading_indicator,
                search_results_container,
                ft.Container(height=spacing.sm),
                
                # Selected world display
                ft.Text("Selected World:", size=typography.size_xs, color=colors.text_tertiary),
                selected_world_display,
                ft.Container(height=spacing.sm),
                
                # Or paste ID
                world_id_field,
                ft.Container(height=spacing.md),
                
                # Instance settings
                ft.Text("⚙️ Instance Settings", weight=ft.FontWeight.W_600, color=colors.text_primary),
                ft.Container(height=spacing.xs),
                ft.Row([region_dd, access_dd], spacing=spacing.md),
                ft.Container(height=spacing.sm),
                ft.Row([queue_chk, age_chk], spacing=spacing.xl),
                ft.Container(height=spacing.sm),
                name_field, 
            ], tight=True, width=550, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                NeonButton("Create Instance", on_click=create_click, variant="primary", icon=ft.Icons.ROCKET_LAUNCH_ROUNDED),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=colors.bg_elevated,
            shape=ft.RoundedRectangleBorder(radius=radius.lg),
        )
        
        self.page.open(dlg)

    async def _do_create_instance(self, world_id, region, access, queue, age_gate, name=None):
        if not self.api: return
        self.page.open(ft.SnackBar(ft.Text("Creating instance..."), bgcolor=colors.bg_elevated))
        
        group_id = self.group.get("id")
        print(f"[DEBUG] Creating instance: world={world_id}, region={region}, access={access}, queue={queue}, age={age_gate}, name={name}, group={group_id}")
        
        try:
            res = await self.api.create_instance(
                world_id=world_id,
                type="group",
                region=region,
                group_id=group_id,
                group_access_type=access,
                queue_enabled=queue,
                age_gate=age_gate,
                name=name
            )
            print(f"[DEBUG] Create instance result: {res}")
            
            if res:
                # Get instance info for display and self-invite
                location = res.get("location") or res.get("id") or ""
                instance_id = res.get("instanceId") or ""
                short_name = res.get("shortName") or ""
                world_name = res.get("world", {}).get("name", "") or res.get("name", "") or "Instance"
                
                # Parse location to get instance ID if needed
                if ":" in location and not instance_id:
                    instance_id = location.split(":", 1)[1]
                
                print(f"[DEBUG] Instance created: location={location}, instanceId={instance_id}, world={world_name}")
                
                # Invalidate instances cache
                self.api.invalidate_instances_cache(group_id)
                
                # Try to send self-invite so user can join
                invite_sent = False
                if instance_id:
                    invite_sent = await self.api.self_invite(world_id, instance_id, short_name)
                    print(f"[DEBUG] Self-invite sent: {invite_sent}")
                
                # Build VRChat launch link
                launch_link = f"vrchat://launch?worldId={world_id}&instanceId={instance_id}" if instance_id else None
                
                # Show success dialog with instance info
                self._show_instance_created_dialog(world_name, location, launch_link, invite_sent)
                
                self._loading = True
                self._update_view()
                await self._load_data()
            else:
                print(f"[DEBUG] API returned None - instance creation failed")
                self.page.open(ft.SnackBar(ft.Text("Failed to create instance (API returned None)"), bgcolor=colors.danger))
        except Exception as e:
            import traceback
            print(f"[DEBUG] Create instance error: {e}")
            traceback.print_exc()
            self.page.open(ft.SnackBar(ft.Text(f"Error: {str(e)}"), bgcolor=colors.danger))
    
    def _show_instance_created_dialog(self, world_name: str, location: str, launch_link: str, invite_sent: bool):
        """Show a dialog with the created instance info"""
        
        def close_dlg(e):
            self.page.close(dlg)
        
        def copy_link(e):
            if launch_link:
                self.page.set_clipboard(launch_link)
                self.page.open(ft.SnackBar(ft.Text("Launch link copied!"), bgcolor=colors.success))
        
        def open_in_vrchat(e):
            if launch_link:
                import webbrowser
                webbrowser.open(launch_link)
                self.page.close(dlg)
        
        invite_status = ft.Row([
            ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=colors.success, size=16),
            ft.Text("Self-invite sent! Check your VRChat invites.", color=colors.success, size=typography.size_sm),
        ]) if invite_sent else ft.Row([
            ft.Icon(ft.Icons.INFO_ROUNDED, color=colors.warning, size=16),
            ft.Text("Open VRChat to join the instance.", color=colors.warning, size=typography.size_sm),
        ])
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=colors.success, size=28),
                ft.Container(width=spacing.sm),
                ft.Text("Instance Created!", weight=ft.FontWeight.W_600),
            ]),
            content=ft.Column([
                ft.Text(world_name, weight=ft.FontWeight.BOLD, color=colors.text_primary, size=typography.size_lg),
                ft.Container(height=spacing.xs),
                ft.Text(f"Location: {location}", size=typography.size_xs, color=colors.text_tertiary, selectable=True),
                ft.Container(height=spacing.md),
                invite_status,
                ft.Container(height=spacing.md),
                ft.Row([
                    NeonButton("Open in VRChat", icon=ft.Icons.OPEN_IN_NEW_ROUNDED, variant="primary", on_click=open_in_vrchat) if launch_link else ft.Container(),
                    ft.TextButton("Copy Link", on_click=copy_link) if launch_link else ft.Container(),
                ], spacing=spacing.sm),
            ], tight=True, width=400),
            actions=[
                ft.TextButton("Close", on_click=close_dlg),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=colors.bg_elevated,
            shape=ft.RoundedRectangleBorder(radius=radius.lg),
        )
        
        self.page.open(dlg)
    
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
            # Invalidate instances cache since we closed one
            self.api.invalidate_instances_cache(self.group.get("id"))
            
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
        
        def close_dlg(e):
            self.page.close(dlg)
        
        def confirm(e):
            self.page.close(dlg)
            self.page.run_task(self._do_invite_online_group_members)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.GROUP_ADD_ROUNDED, color=colors.accent_primary, size=28),
                ft.Container(width=spacing.sm),
                ft.Text("Invite Online Group Members", weight=ft.FontWeight.W_600),
            ]),
            content=ft.Column([
                ft.Text(f"Target Group: {grp_name}", weight=ft.FontWeight.W_600, color=colors.accent_primary),
                ft.Container(height=spacing.md),
                ft.Text("This will scan your ONLINE friends list and invite anyone who is also a member of this group.", size=typography.size_sm, color=colors.text_secondary),
                ft.Container(height=spacing.sm),
                ft.Text("⚠️ Note: This requires you to be in an instance.", color=colors.warning, size=typography.size_sm),
            ], tight=True, width=400),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                NeonButton("Invite Members", on_click=confirm, variant="primary", icon=ft.Icons.SEND_ROUNDED),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=colors.bg_elevated,
            shape=ft.RoundedRectangleBorder(radius=radius.lg),
        )
        
        # Use modern Flet API
        self.page.open(dlg)

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
        
        members = await self.api.get_cached_group_members(grp_id, limit=100)
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
