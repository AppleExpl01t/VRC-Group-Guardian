import asyncio
import flet as ft
import logging
from ..theme import colors, radius, spacing, typography
from ..components.neon_button import IconButton
from ..components.user_card import UserCard
from ..dialogs.user_details import show_user_details_dialog
from ..dialogs.confirm_dialog import show_confirm_dialog
from ..dialogs.automod_settings import show_automod_settings
from services.database import get_database
from services.automod import get_automod_service
from services.notification_service import get_notification_service

logger = logging.getLogger(__name__)

class RequestsView(ft.Container):
    """
    View for managing group join requests using Unified UserCard.
    Features auto-refresh when auto-mod is enabled.
    """
    def __init__(self, group=None, api=None, on_navigate=None, on_update_stats=None, **kwargs):
        self.group = group
        self.api = api
        self.on_navigate = on_navigate
        self.on_update_stats = on_update_stats
        # Extract is_mobile to prevent sending to super().__init__
        self._is_mobile = kwargs.pop("is_mobile", False)
        self._requests = []
        self._loading = True
        self.db = get_database()
        
        # Auto-refresh state
        self._automod_enabled = False
        self._polling_active = False
        self._polling_task = None
        self._poll_interval_seconds = 30  # Check every 30 seconds when automod is enabled
        self._prev_request_count = 0  # Track previous count for new request notifications
        
        # Content list - using GridView with responsive extent
        self._content_area = ft.GridView(
            max_extent=170 if self._is_mobile else 220,
            child_aspect_ratio=0.95,
            spacing=spacing.sm,
            run_spacing=spacing.sm,
            expand=True,
        )
        
        # Countdown timer text for auto-refresh
        self._countdown_text = ft.Text("", size=10, color=colors.text_tertiary)
        
        # Auto-mod status indicator row
        self._status_row = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.AUTO_MODE_ROUNDED, size=14, color=colors.accent_secondary),
                ft.Text("Auto-Mod:", size=10, color=colors.text_tertiary),
                ft.Text("Off", size=10, color=colors.text_tertiary, ref=ft.Ref[ft.Text]()),
                ft.Container(width=spacing.sm),
                ft.Icon(ft.Icons.REFRESH_ROUNDED, size=12, color=colors.text_tertiary),
                self._countdown_text,
            ], spacing=4),
            padding=ft.padding.symmetric(horizontal=spacing.md, vertical=spacing.xs),
            visible=False,  # Will be made visible when automod is enabled
        )
        self._status_text = None  # Will be set after building
        
        # Header - more compact
        header = ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("Join Requests", size=typography.size_xl, weight=ft.FontWeight.W_700, color=colors.text_primary),
                        ft.Text(f"Pending members for {self.group.get('name') if self.group else 'Unknown'}", color=colors.text_secondary, size=typography.size_sm),
                    ],
                    spacing=0,
                ),
                ft.Row(
                    controls=[
                        IconButton(
                            icon=ft.Icons.SETTINGS_SUGGEST_ROUNDED,
                            tooltip="Auto-Mod Settings",
                            on_click=self._open_automod_settings,
                        ),
                        ft.Container(width=spacing.xs),
                        IconButton(
                            icon=ft.Icons.REFRESH_ROUNDED,
                            tooltip="Refresh",
                            on_click=lambda e: self.page.run_task(self._load_data, force_refresh=True),
                        ),
                    ]
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        content = ft.Column([
            header,
            self._status_row,
            ft.Container(height=spacing.sm),
            self._content_area
        ], expand=True)
        
        super().__init__(
            content=content,
            padding=spacing.md,
            expand=True,
            **kwargs
        )
    
    def _open_automod_settings(self, e):
        """Open automod settings dialog"""
        show_automod_settings(
            self.page, 
            self.group.get("id"), 
            self.group.get("name"),
            api=self.api,
            on_update=self._on_automod_settings_changed
        )
    
    def _on_automod_settings_changed(self):
        """Called when automod settings are saved"""
        # Reload settings and refresh
        self._check_automod_status()
        self.page.run_task(self._load_data, force_refresh=True)
        
    def did_mount(self):
        # Always sync requests when page loads (regardless of automod status)
        self._update_view()
        
        # Force refresh data on mount
        self.page.run_task(self._load_data, force_refresh=True)
        
        # Check automod status and start polling if enabled
        # This will reset the countdown timer
        self._check_automod_status()
        
    def will_unmount(self):
        """Clean up polling task when view is unmounted"""
        self._stop_polling()
    
    def _check_automod_status(self):
        """Check if automod is enabled for this group and update UI accordingly"""
        if self.group:
            group_id = self.group.get("id")
            settings = self.db.get_group_settings(group_id)
            self._automod_enabled = bool(settings.get("automod_enabled", 0)) if settings else False
            
            # Update status row
            self._status_row.visible = self._automod_enabled
            
            # Update status text within the row
            if self._status_row.content and hasattr(self._status_row.content, 'controls'):
                for ctrl in self._status_row.content.controls:
                    if isinstance(ctrl, ft.Text) and ctrl != self._countdown_text:
                        if "Auto-Mod:" in str(ctrl.value):
                            continue
                        # This is the status text
                        ctrl.value = "Active" if self._automod_enabled else "Off"
                        ctrl.color = colors.success if self._automod_enabled else colors.text_tertiary
            
            # Start/stop polling based on automod status
            if self._automod_enabled:
                self._start_polling()
            else:
                self._stop_polling()
            
            if self._status_row.page:
                try:
                    self._status_row.update()
                except:
                    pass
    
    def _start_polling(self, reset_timer: bool = True):
        """Start background polling for auto-refresh. If reset_timer is True, restarts the countdown."""
        if self._polling_active and not reset_timer:
            return
        
        # Stop existing polling to reset the timer
        if self._polling_active:
            self._polling_active = False
            self._polling_task = None
        
        # Start fresh
        self._polling_active = True
        self._update_countdown_display(f"Next sync: {self._poll_interval_seconds}s")
        self._polling_task = self.page.run_task(self._poll_with_countdown)
        logger.info(f"Started requests auto-refresh (every {self._poll_interval_seconds}s)")
    
    def _stop_polling(self):
        """Stop background polling"""
        self._polling_active = False
        if self._polling_task:
            logger.info("Stopped requests auto-refresh")
            self._polling_task = None
    
    def _update_countdown_display(self, text: str):
        """Update the countdown text display"""
        self._countdown_text.value = text
        if self._countdown_text.page:
            try:
                self._countdown_text.update()
            except:
                pass
    
    async def _poll_with_countdown(self):
        """
        Unified polling task that handles countdown and auto-refresh.
        Only runs when automod is enabled.
        """
        while self._polling_active:
            try:
                # Countdown phase
                countdown = self._poll_interval_seconds
                
                while countdown > 0 and self._polling_active:
                    self._update_countdown_display(f"Next sync: {countdown}s")
                    await asyncio.sleep(1)
                    countdown -= 1
                
                if not self._polling_active:
                    break
                
                # Refresh phase
                self._update_countdown_display("⟳ Syncing...")
                logger.debug("Auto-refreshing join requests...")
                
                if self.api and self.group:
                    group_id = self.group.get("id")
                    
                    # Fetch fresh requests
                    self._requests = await self.api.get_group_join_requests(group_id)
                    
                    if not self._polling_active or not self.page:
                        break
                    
                    # Run automod on new requests
                    automod = get_automod_service()
                    processed_ids = await automod.process_join_requests(self.api, group_id, self._requests)
                    
                    if processed_ids:
                        # Remove processed from view
                        self._requests = [
                            r for r in self._requests 
                            if r.get("userId") not in processed_ids 
                            and r.get("user", {}).get("id") not in processed_ids
                        ]
                        
                        # Show notification
                        if self.page:
                            self.page.open(ft.SnackBar(
                                content=ft.Text(f"Auto-Mod processed {len(processed_ids)} request(s)"),
                                bgcolor=colors.accent_primary
                            ))
                    
                    # Update view
                    self._loading = False
                    self._update_view()
                    
                    # Update stats
                    if self.on_update_stats:
                        self.on_update_stats({"pending_requests": len(self._requests)})
                    
                    self._update_countdown_display(f"✓ Synced")
                    await asyncio.sleep(2)  # Show synced message briefly
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error during requests polling: {e}")
                self._update_countdown_display("!")
                await asyncio.sleep(5)
        
    async def _load_data(self, force_refresh: bool = False):
        if not self.api or not self.group:
            self._loading = False
            self._update_view()
            return

        self._loading = True
        self._update_view()
            
        try:
            group_id = self.group.get("id")
            self._requests = await self.api.get_cached_join_requests(group_id, force_refresh=force_refresh)
            
            # Run Auto-Mod
            automod = get_automod_service()
            processed_ids = await automod.process_join_requests(self.api, group_id, self._requests)
            
            if processed_ids:
                # Remove processed from view (check both userId and nested user.id)
                self._requests = [
                    r for r in self._requests 
                    if r.get("userId") not in processed_ids 
                    and r.get("user", {}).get("id") not in processed_ids
                ]
                
                # Invalidate cache since we auto-processed items
                self.api.invalidate_join_requests_cache(group_id)
                
                if self.page:
                    self.page.open(ft.SnackBar(
                        content=ft.Text(f"Auto-Moderation processed {len(processed_ids)} requests."), 
                        bgcolor=colors.accent_primary
                    ))

            # Check if there are new requests since last load (for notifications)
            current_count = len(self._requests)
            if current_count > self._prev_request_count and self._prev_request_count > 0:
                # New requests arrived - play notification
                notif_service = get_notification_service()
                notif_service.notify_join_request()
            self._prev_request_count = current_count

            # Notify parent app
            if self.on_update_stats:
                self.on_update_stats({"pending_requests": len(self._requests)})
        except Exception as e:
            logger.error(f"Error loading requests: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._loading = False
            self._update_view()
        
    def _update_view(self):
        self._content_area.controls = self._get_content_controls()
        if self.page:
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
        
        async def reject_req():
            await self._handle_action(req, "Reject")
            
        async def accept_req():
            await self._handle_action(req, "Accept")
            
        def show_ban(e):
             self._show_ban_dialog(req)

        # Actions - add keys for ADI testing
        user_id = user.get("id", "unknown")
        actions = [
            IconButton(
                icon=ft.Icons.BLOCK_ROUNDED,
                icon_color=colors.danger,
                tooltip="Ban User",
                on_click=show_ban,
                key=f"btn_ban_{user_id}"
            ),
            ft.Container(width=spacing.xs),
            IconButton(
                icon=ft.Icons.CLOSE_ROUNDED,
                icon_color=colors.warning,
                tooltip="Reject",
                on_click=lambda e: self.page.run_task(reject_req),
                key=f"btn_reject_{user_id}"
            ),
            ft.Container(width=spacing.xs),
            IconButton(
                icon=ft.Icons.CHECK_ROUNDED,
                icon_color=colors.success,
                tooltip="Accept",
                on_click=lambda e: self.page.run_task(accept_req),
                key=f"btn_accept_{user_id}"
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
        
        def do_ban():
            self.page.run_task(lambda: self._confirm_ban_action(req))
        
        show_confirm_dialog(
            self.page,
            title="Ban User?",
            message=f"Are you sure you want to ban {user_name} ({user_id}) from the group?",
            on_confirm=do_ban,
            confirm_text="Ban User",
            variant="danger",
            icon=ft.Icons.BLOCK_ROUNDED,
            warning_text="This action cannot be easily undone.",
        )

    async def _confirm_ban_action(self, req):
        """Execute the ban and reject request"""
        group_id = self.group.get("id")
        user = req.get("user", {})
        user_id = user.get("id")
        
        try:
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
        except Exception as e:
            logger.error(f"Error banning user: {e}")
            import traceback
            traceback.print_exc()
            self.page.open(ft.SnackBar(content=ft.Text(f"Error: {e}"), bgcolor=colors.danger))

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
        
        try:
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
        except Exception as e:
            # Revert if failed (add back)
            self._requests.append(req)
            self._update_view()
            
            logger.error(f"Error handling request: {e}")
            import traceback
            traceback.print_exc()
            self.page.open(ft.SnackBar(content=ft.Text(f"Error: {e}"), bgcolor=colors.danger))
