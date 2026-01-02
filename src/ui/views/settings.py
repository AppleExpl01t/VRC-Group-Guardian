"""
Settings View
=============
Application configuration and personalization
"""

import flet as ft
from ..theme import colors, radius, spacing, typography, shadows
from ..components.glass_card import GlassCard, GlassPanel
from ..components.neon_button import NeonButton
from services.updater import UpdateService
from services.watchlist_alerts import get_alert_service
from services.notification_service import get_notification_service

class SettingsView(ft.Container):
    """
    Settings view with organized categories:
    - UI Theme (Customization)
    - General (Placeholder)
    - Account (Placeholder)
    """
    
    def __init__(self, api=None, on_navigate=None, on_theme_change=None, **kwargs):
        self.api = api
        self.on_navigate = on_navigate
        self.on_theme_change = on_theme_change  # Callback for when theme color changes
        self._theme_settings_control = None
        self._custom_color_field = None
        
        # File Picker for custom sounds
        self._file_picker = ft.FilePicker(on_result=self._handle_file_picker_result)
        
        # Developer Profile Data
        self._dev_profile_data = None
        self._dev_card_ref = ft.Ref()
        
        content = self._build_view()
        
        super().__init__(
            content=content,
            expand=True,
            padding=spacing.lg,
            **kwargs,
        )

    def did_mount(self):
        """Fetch developer profile on mount"""
        # Register file picker
        self.page.overlay.append(self._file_picker)
        self.page.update()
        
        if self.api:
            self.page.run_task(self._fetch_dev_profile)

    async def _fetch_dev_profile(self):
        """Fetch AppleExpl01t's profile"""
        if not self.api: return
        
        dev_id = "usr_ef7c23be-3c3c-40b4-a01c-82f59b2a8229"
        try:
            user = await self.api.get_user(dev_id)
            if user:
                # Cache images
                pfp = await self.api.cache_user_image(user)
                # Helper to cache banner (re-using download_image directly if no helper exists)
                banner_url = user.get("profileBannerUrl") or user.get("currentAvatarImageUrl")
                local_banner = None
                if banner_url:
                     local_banner = await self.api.download_image(banner_url, f"dev_{dev_id}_banner")
                
                self._dev_profile_data = {
                    "name": user.get("displayName"),
                    "status": user.get("statusDescription") or user.get("status"),
                    "pfp": pfp,
                    "banner": local_banner,
                    "rank": user.get("tags", [])
                }
                self._update_dev_card()
        except Exception as e:
            print(f"Failed to fetch dev profile: {e}")

    def _update_dev_card(self):
        """Update the developer card with fetched data"""
        if self._dev_card_ref.current and self._dev_profile_data:
            # Rebuild the card content with real data
            new_content = self._build_dev_profile_content()
            self._dev_card_ref.current.content = new_content
            self._dev_card_ref.current.update()

    def _build_view(self) -> ft.Control:
        """Build settings layout - Organized Tabbed Version"""
        
        # Header
        header = ft.Column(
            controls=[
                ft.Text(
                    "Settings",
                    size=typography.size_xl,
                    weight=ft.FontWeight.W_700,
                    color=colors.text_primary,
                ),
                ft.Text(
                    "Customize your experience and preferences",
                    size=typography.size_sm,
                    color=colors.text_secondary,
                ),
            ],
            spacing=0,
        )
        
        # Initialize sections
        self._theme_settings_control = self._build_theme_settings()
        
        # Create Tabs
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            indicator_color=colors.accent_primary,
            label_color=colors.accent_primary,
            unselected_label_color=colors.text_secondary,
            divider_color=colors.glass_border,
            tabs=[
                ft.Tab(
                    text="General",
                    icon=ft.Icons.SETTINGS_SUGGEST_ROUNDED,
                    content=ft.Container(
                        content=ft.ListView(
                            controls=[
                                ft.Container(height=spacing.sm),
                                self._theme_settings_control,
                                ft.Container(height=spacing.md),
                                self._build_update_section(),
                                ft.Container(height=spacing.md),
                                self._build_credits_section(),
                                ft.Container(height=spacing.lg),
                            ],
                            padding=ft.padding.only(right=10),
                        ),
                        padding=spacing.sm
                    )
                ),
                ft.Tab(
                    text="Notifications",
                    icon=ft.Icons.NOTIFICATIONS_ROUNDED,
                    content=ft.Container(
                        content=ft.ListView(
                            controls=[
                                ft.Container(height=spacing.sm),
                                self._build_notification_section(),
                                ft.Container(height=spacing.lg),
                            ],
                            padding=ft.padding.only(right=10),
                        ),
                        padding=spacing.sm
                    )
                ),
                ft.Tab(
                    text="Integrations",
                    icon=ft.Icons.EXTENSION_ROUNDED,
                    content=ft.Container(
                        content=ft.ListView(
                            controls=[
                                ft.Container(height=spacing.sm),
                                self._build_xsoverlay_section(),
                                ft.Container(height=spacing.lg),
                            ],
                            padding=ft.padding.only(right=10),
                        ),
                        padding=spacing.sm
                    )
                ),
                ft.Tab(
                    text="System",
                    icon=ft.Icons.STORAGE_ROUNDED,
                    content=ft.Container(
                        content=ft.ListView(
                            controls=[
                                ft.Container(height=spacing.sm),
                                self._build_database_section(),
                                ft.Container(height=spacing.lg),
                            ],
                            padding=ft.padding.only(right=10),
                        ),
                        padding=spacing.sm
                    )
                )
            ],
            expand=True,
        )
        
        return ft.Column(
            controls=[
                header,
                ft.Container(height=spacing.sm),
                self.tabs,
            ],
            spacing=0,
            expand=True,
        )
    
    # ... (Theme Settings Code - kept primarily as is, just referenced) ...
    def _build_theme_settings(self) -> ft.Control:
         # (Collapsed for brevity, assuming standard implementation or I'll copy the existing block if I can't partial replace)
         # Actually, I should probably keep the existing method by NOT replacing it if I can avoid it.
         # But `replace_file_content` replaces a block.
         # I will paste the _build_theme_settings from the previous `view_file`.
         
        # Quick Colors (Tokens)
        accent_colors = ["#8b5cf6", "#06b6d4", "#3b82f6", "#ec4899", "#10b981", "#f59e0b", "#ef4444"]
        
        color_row = ft.Row(
            controls=[
                ft.Container(
                    width=32, height=32, border_radius=radius.full, bgcolor=color,
                    border=ft.border.all(2, colors.text_primary if color == colors.accent_primary else "transparent"),
                    on_click=lambda e, c=color: self._handle_color_change(c),
                    animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT), tooltip=color
                ) for color in accent_colors
            ], spacing=spacing.md,
        )
        
        self._custom_color_field = ft.TextField(
             label="Custom Hex Color", value=colors.accent_primary,
             text_style=ft.TextStyle(size=typography.size_base),
             border_color=colors.glass_border, focused_border_color=colors.accent_primary,
             text_size=typography.size_base, width=200, height=45, dense=True, content_padding=10,
             on_submit=lambda e: self._handle_color_change(e.control.value),
        )

        custom_color_row = ft.Row(
            controls=[
                ft.Container(width=45, height=45, bgcolor=colors.accent_primary, border_radius=radius.md, border=ft.border.all(2, colors.glass_border)),
                self._custom_color_field,
                NeonButton(text="Apply", on_click=lambda e: self._handle_color_change(self._custom_color_field.value), variant="primary", height=45)
            ], spacing=spacing.md, vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        return GlassPanel(
            content=ft.Column(
                controls=[
                    ft.Row(controls=[ft.Icon(ft.Icons.PALETTE_ROUNDED, color=colors.accent_primary), ft.Text("UI Theme", size=typography.size_lg, weight=ft.FontWeight.W_600, color=colors.text_primary)], spacing=spacing.sm),
                    ft.Divider(color=colors.glass_border, height=spacing.xl),
                    ft.Text("Quick Colors", weight=ft.FontWeight.W_500, color=colors.text_primary),
                    ft.Container(height=spacing.xs),
                    color_row,
                    ft.Container(height=spacing.lg),
                    ft.Text("Custom Color", weight=ft.FontWeight.W_500, color=colors.text_primary),
                    ft.Container(height=spacing.xs),
                    custom_color_row,
                    ft.Divider(color=colors.glass_border, height=spacing.xl),
                    ft.Row(controls=[ft.Container(expand=True), NeonButton(text="Reset to Default", icon=ft.Icons.RESTORE_ROUNDED, on_click=self._handle_reset_theme, variant="secondary")])
                ],
            ),
        )

    def _build_notification_section(self) -> ft.Control:
        """Build Notification Settings Section"""
        try:
            notif_service = get_notification_service()
            config = notif_service.config
            
            # Volume slider
            self._volume_slider = ft.Slider(
                value=config.master_volume,
                min=0,
                max=1,
                divisions=20,
                label="{value:.0%}",
                active_color=colors.accent_primary,
                inactive_color=colors.bg_glass,
                on_change=self._handle_volume_change,
            )
            
            self._volume_label = ft.Text(
                f"{int(config.master_volume * 100)}%",
                size=typography.size_sm,
                color=colors.text_primary,
                weight=ft.FontWeight.W_500,
            )
            
            # Event toggles
            def create_toggle(label: str, description: str, value: bool, on_change):
                return ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text(label, weight=ft.FontWeight.W_500, color=colors.text_primary),
                                ft.Text(description, size=typography.size_xs, color=colors.text_tertiary),
                            ],
                            spacing=2,
                        ),
                        ft.Container(expand=True),
                        ft.Switch(
                            value=value,
                            active_color=colors.accent_primary,
                            on_change=on_change,
                            scale=0.85,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            
            self._watchlist_toggle = create_toggle(
                "Watchlist Alerts", 
                "Play sound when watchlisted user joins",
                config.watchlist_alerts_enabled,
                lambda e: self._handle_notif_toggle("watchlist", e.control.value)
            )
            
            self._automod_toggle = create_toggle(
                "Auto-Mod Actions",
                "Play sound when auto-mod accepts/rejects request",
                config.automod_alerts_enabled,
                lambda e: self._handle_notif_toggle("automod", e.control.value)
            )
            
            self._joinreq_toggle = create_toggle(
                "New Join Requests",
                "Play sound when new group join requests arrive",
                config.join_request_alerts_enabled,
                lambda e: self._handle_notif_toggle("joinreq", e.control.value)
            )
            
            self._player_join_toggle = create_toggle(
                "Player Joins",
                "Play sound when players join your instance (can be noisy)",
                config.player_join_alerts_enabled,
                lambda e: self._handle_notif_toggle("player_join", e.control.value)
            )
            
            self._update_toggle = create_toggle(
                "App Updates",
                "Play sound when updates are available",
                config.update_alerts_enabled,
                lambda e: self._handle_notif_toggle("update", e.control.value)
            )
            
            # Sound file picker
            available_sounds = notif_service.get_available_sounds()
            current_sound = config.custom_sound_path 
            
            # Ensure dropdown value is valid
            dropdown_value = "Default"
            if current_sound and str(current_sound) in available_sounds:
                 dropdown_value = str(current_sound)
            
            self._sound_dropdown = ft.Dropdown(
                value=dropdown_value,
                options=self._get_sound_options(available_sounds),
                on_change=self._handle_sound_change,
                border_color=colors.glass_border,
                focused_border_color=colors.accent_primary,
                bgcolor=colors.bg_elevated,
                width=250,
                content_padding=10,
            )
            
            # Test button
            self._test_sound_button = NeonButton(
                text="Test",
                icon=ft.Icons.VOLUME_UP_ROUNDED,
                on_click=self._handle_test_sound,
                variant="secondary",
                height=40,
                width=100
            )

            # Import button
            self._import_sound_button = NeonButton(
                text="Import",
                icon=ft.Icons.UPLOAD_FILE_ROUNDED,
                on_click=lambda _: self._file_picker.pick_files(
                    allow_multiple=False,
                    allowed_extensions=["mp3", "wav", "ogg"],
                    dialog_title="Select Notification Sound"
                ),
                variant="secondary",
                height=40,
                width=120
            )
            
            return GlassPanel(
                content=ft.Column(
                    controls=[
                        # Header
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_ROUNDED, color=colors.accent_primary),
                                ft.Text("Notification Sounds", size=typography.size_lg, weight=ft.FontWeight.W_600, color=colors.text_primary),
                            ],
                            spacing=spacing.sm,
                        ),
                        ft.Divider(color=colors.glass_border, height=spacing.md),
                        
                        # Volume control
                        ft.Text("Master Volume", weight=ft.FontWeight.W_500, color=colors.text_primary),
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.VOLUME_DOWN_ROUNDED, color=colors.text_secondary, size=18),
                                ft.Container(content=self._volume_slider, expand=True),
                                ft.Icon(ft.Icons.VOLUME_UP_ROUNDED, color=colors.text_secondary, size=18),
                                self._volume_label,
                            ],
                            spacing=spacing.sm,
                        ),
                        ft.Container(height=spacing.sm),
                        
                        # Event toggles
                        ft.Text("Notification Events", weight=ft.FontWeight.W_500, color=colors.text_primary),
                        ft.Container(height=spacing.xs),
                        self._watchlist_toggle,
                        self._automod_toggle,
                        self._joinreq_toggle,
                        self._player_join_toggle,
                        self._update_toggle,
                        ft.Container(height=spacing.md),
                        
                        # Sound selection
                        ft.Text("Notification Sound", weight=ft.FontWeight.W_500, color=colors.text_primary),
                        ft.Container(height=spacing.xs),
                        ft.Row(
                            controls=[
                                self._sound_dropdown,
                                ft.Container(width=spacing.sm),
                                self._test_sound_button,
                                ft.Container(width=spacing.xs),
                                self._import_sound_button,
                            ],
                        ),
                        ft.Container(height=spacing.xs),
                        ft.Text(
                            "💡 Place custom .mp3/.wav/.ogg files in the app folder or assets folder",
                            size=typography.size_xs,
                            color=colors.text_tertiary,
                            italic=True,
                        ),
                    ],
                ),
            )
        except Exception as e:
            print(f"Error building notification section: {e}")
            import traceback
            traceback.print_exc()
            return GlassPanel(content=ft.Text(f"Error loading notification settings: {e}", color=colors.danger))

    def _get_sound_options(self, sounds):
        """Generate dropdown options with nice labels"""
        opts = [ft.dropdown.Option("Default", "Default Sound")]
        for s in sounds:
            filename = s.replace("\\", "/").split("/")[-1]
            if filename == "Group_Guardian_Notif_sound.mp3":
                continue # Skip main default file (covered by 'Default Sound')
            elif filename == "Group_Guardian_Notif_Sound_No_Voice.mp3":
                opts.append(ft.dropdown.Option(s, "Default (No Voice)"))
            else:
                opts.append(ft.dropdown.Option(s, filename))
        return opts

    def _handle_volume_change(self, e):
        """Handle volume slider change"""
        notif_service = get_notification_service()
        volume = e.control.value
        notif_service.set_volume(volume)
        self._volume_label.value = f"{int(volume * 100)}%"
        self._volume_label.update()

    def _handle_notif_toggle(self, event_type: str, enabled: bool):
        """Handle notification event toggle"""
        notif_service = get_notification_service()
        config = notif_service.config
        
        if event_type == "watchlist":
            config.watchlist_alerts_enabled = enabled
        elif event_type == "automod":
            config.automod_alerts_enabled = enabled
        elif event_type == "joinreq":
            config.join_request_alerts_enabled = enabled
        elif event_type == "player_join":
            config.player_join_alerts_enabled = enabled
        elif event_type == "update":
            config.update_alerts_enabled = enabled
        
        notif_service.save_config()
        
        status = "enabled" if enabled else "disabled"
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(f"Notification {status}"),
            bgcolor=colors.success if enabled else colors.text_tertiary
        )
        self.page.snack_bar.open = True
        self.page.update()

    def _handle_sound_change(self, e):
        """Handle sound file selection change"""
        notif_service = get_notification_service()
        
        if e.control.value == "Default":
            notif_service.set_custom_sound(None)
        else:
            notif_service.set_custom_sound(e.control.value)
        
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text("Notification sound updated"),
            bgcolor=colors.success
        )
        self.page.snack_bar.open = True
        self.page.update()

    def _handle_test_sound(self, e):
        """Play test notification sound"""
        notif_service = get_notification_service()
        success = notif_service.play_test()
        
        if success:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("🔔 Test notification played!"),
                bgcolor=colors.success
            )
        else:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("⚠️ Could not play sound - check if pygame is installed"),
                bgcolor=colors.warning
            )
        self.page.snack_bar.open = True
        self.page.update()

    def _handle_file_picker_result(self, e: ft.FilePickerResultEvent):
        """Handle custom sound file selection"""
        if not e.files or not e.files[0].path:
            return

        import shutil
        import os
        from pathlib import Path

        file_path = Path(e.files[0].path)
        assets_dir = Path(os.getcwd()) / "assets"
        assets_dir.mkdir(exist_ok=True)
        
        target_path = assets_dir / file_path.name
        
        try:
            # Copy file to assets
            shutil.copy2(file_path, target_path)
            
            # Update service
            notif_service = get_notification_service()
            notif_service.set_custom_sound(str(target_path))
            
            # Refresh dropdown options
            available_sounds = notif_service.get_available_sounds()
            
            self._sound_dropdown.options = self._get_sound_options(available_sounds)
            self._sound_dropdown.value = str(target_path)
            self._sound_dropdown.update()
            
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Imported and set: {file_path.name}"),
                bgcolor=colors.success
            )
            self.page.snack_bar.open = True
            self.page.update()
            
        except Exception as ex:
            print(f"Error importing sound: {ex}")
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Failed to import sound: {ex}"),
                bgcolor=colors.danger
            )
            self.page.snack_bar.open = True
            self.page.update()

    def _build_xsoverlay_section(self) -> ft.Control:
        """Build XSOverlay Integration Settings Section"""
        
        alert_service = get_alert_service()
        xso_status = alert_service.get_xsoverlay_status() if alert_service else {}
        
        # Status indicator
        is_connected = xso_status.get("connected", False)
        is_enabled = xso_status.get("enabled", True)
        
        status_color = colors.success if is_connected else colors.text_tertiary
        status_text = "Connected" if is_connected else "Not Connected"
        
        self._xso_status_indicator = ft.Row(
            controls=[
                ft.Container(
                    width=10, height=10, 
                    border_radius=radius.full, 
                    bgcolor=status_color,
                    animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
                ),
                ft.Text(status_text, size=typography.size_sm, color=status_color),
            ],
            spacing=spacing.sm,
        )
        
        # Enable XSOverlay switch
        self._xso_enable_switch = ft.Switch(
            value=is_enabled,
            active_color=colors.accent_primary,
            on_change=self._handle_xso_toggle,
        )
        
        # VRC Fallback switch
        vrc_fallback = xso_status.get("vrc_fallback", True)
        self._xso_fallback_switch = ft.Switch(
            value=vrc_fallback,
            active_color=colors.accent_secondary,
            on_change=self._handle_xso_fallback_toggle,
        )
        
        # Connect button
        self._xso_connect_button = NeonButton(
            text="Connect" if not is_connected else "Reconnect",
            icon=ft.Icons.LINK_ROUNDED if not is_connected else ft.Icons.REFRESH_ROUNDED,
            on_click=self._handle_xso_connect,
            variant="primary",
            height=40,
        )
        
        # Test button
        self._xso_test_button = NeonButton(
            text="Send Test",
            icon=ft.Icons.NOTIFICATIONS_ACTIVE_ROUNDED,
            on_click=self._handle_xso_test,
            variant="secondary",
            height=40,
        )
        
        return GlassPanel(
            content=ft.Column(
                controls=[
                    # Header
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.HEADSET_ROUNDED, color=colors.accent_secondary),
                            ft.Text("XSOverlay Integration", size=typography.size_lg, weight=ft.FontWeight.W_600, color=colors.text_primary),
                            ft.Container(expand=True),
                            self._xso_status_indicator,
                        ],
                        spacing=spacing.sm,
                    ),
                    ft.Divider(color=colors.glass_border, height=spacing.md),
                    
                    # Description
                    ft.Text(
                        "Receive watchlist alerts directly in VR through XSOverlay notifications.",
                        size=typography.size_sm,
                        color=colors.text_secondary,
                    ),
                    ft.Container(height=spacing.sm),
                    
                    # Enable toggle
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text("Enable XSOverlay Alerts", weight=ft.FontWeight.W_500, color=colors.text_primary),
                                    ft.Text("Send notifications to XSOverlay when available", size=typography.size_xs, color=colors.text_tertiary),
                                ],
                                spacing=2,
                            ),
                            ft.Container(expand=True),
                            self._xso_enable_switch,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(height=spacing.sm),
                    
                    # VRC Fallback toggle
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text("VRChat Invite Fallback", weight=ft.FontWeight.W_500, color=colors.text_primary),
                                    ft.Text("Fall back to in-game invites if XSOverlay unavailable", size=typography.size_xs, color=colors.text_tertiary),
                                ],
                                spacing=2,
                            ),
                            ft.Container(expand=True),
                            self._xso_fallback_switch,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(height=spacing.sm),
                    
                    # Performance throttling toggle
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text("Performance Throttling", weight=ft.FontWeight.W_500, color=colors.text_primary),
                                    ft.Text("Reduce notification frequency when GPU is stressed", size=typography.size_xs, color=colors.text_tertiary),
                                ],
                                spacing=2,
                            ),
                            ft.Container(expand=True),
                            ft.Switch(
                                value=True,  # Enabled by default
                                active_color=colors.accent_secondary,
                                on_change=self._handle_xso_throttle_toggle,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(height=spacing.sm),
                    
                    # Theme sync toggle
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text("Theme Sync", weight=ft.FontWeight.W_500, color=colors.text_primary),
                                    ft.Text("Match app accent color to XSOverlay theme", size=typography.size_xs, color=colors.text_tertiary),
                                ],
                                spacing=2,
                            ),
                            ft.Container(expand=True),
                            ft.Switch(
                                value=True,  # Enabled by default
                                active_color=colors.accent_primary,
                                on_change=self._handle_xso_theme_sync_toggle,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(height=spacing.md),
                    
                    # Buttons row
                    ft.Row(
                        controls=[
                            self._xso_connect_button,
                            self._xso_test_button,
                        ],
                        spacing=spacing.md,
                    ),
                    
                    # Info text
                    ft.Container(height=spacing.sm),
                    ft.Text(
                        "💡 Make sure XSOverlay is running before connecting. Port: 42070",
                        size=typography.size_xs,
                        color=colors.text_tertiary,
                        italic=True,
                    ),
                ],
            ),
        )
    
    async def _handle_xso_toggle(self, e):
        """Toggle XSOverlay enabled state"""
        alert_service = get_alert_service()
        if alert_service:
            alert_service.xsoverlay_enabled = e.control.value
            status = "enabled" if e.control.value else "disabled"
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"XSOverlay alerts {status}"),
                bgcolor=colors.success if e.control.value else colors.text_tertiary
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    async def _handle_xso_fallback_toggle(self, e):
        """Toggle VRC invite fallback"""
        alert_service = get_alert_service()
        if alert_service:
            alert_service.vrc_invite_fallback = e.control.value
            status = "enabled" if e.control.value else "disabled"
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"VRChat invite fallback {status}"),
                bgcolor=colors.bg_elevated
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    async def _handle_xso_connect(self, e):
        """Connect to XSOverlay"""
        self._xso_connect_button.set_loading(True)
        self._xso_connect_button.update()
        
        error_msg = None
        try:
            alert_service = get_alert_service()
            if not alert_service:
                error_msg = "Alert service not initialized"
            else:
                connected = await alert_service.connect_xsoverlay()
                
                if connected:
                    # Update status
                    self._xso_status_indicator.controls[0].bgcolor = colors.success
                    self._xso_status_indicator.controls[1].value = "Connected"
                    self._xso_status_indicator.controls[1].color = colors.success
                    self._xso_connect_button.text = "Reconnect"
                    self._xso_connect_button.icon = ft.Icons.REFRESH_ROUNDED
                    
                    self.page.snack_bar = ft.SnackBar(
                        content=ft.Text("✅ Connected to XSOverlay!"),
                        bgcolor=colors.success
                    )
                else:
                    error_msg = "Connection refused - Make sure XSOverlay is running (port 42070)"
        except ConnectionRefusedError:
            error_msg = "Connection refused - XSOverlay is not running"
        except TimeoutError:
            error_msg = "Connection timed out - XSOverlay may be busy or not responding"
        except Exception as ex:
            error_msg = f"Connection error: {str(ex)}"
        
        if error_msg:
            self._xso_status_indicator.controls[0].bgcolor = colors.danger
            self._xso_status_indicator.controls[1].value = "Failed"
            self._xso_status_indicator.controls[1].color = colors.danger
            
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"❌ {error_msg}"),
                bgcolor=colors.danger,
                duration=5000  # Show longer for errors
            )
        
        self._xso_status_indicator.update()
        self.page.snack_bar.open = True
        self.page.update()
        
        self._xso_connect_button.set_loading(False)
        self._xso_connect_button.update()
    
    async def _handle_xso_test(self, e):
        """Send test notification to XSOverlay"""
        self._xso_test_button.set_loading(True)
        self._xso_test_button.update()
        
        error_msg = None
        try:
            alert_service = get_alert_service()
            if not alert_service:
                error_msg = "Alert service not initialized"
            else:
                # Check if connected first
                status = alert_service.get_xsoverlay_status()
                if not status.get("connected", False):
                    error_msg = "Not connected to XSOverlay - Click 'Connect' first"
                else:
                    success = await alert_service.test_xsoverlay()
                    
                    if success:
                        self.page.snack_bar = ft.SnackBar(
                            content=ft.Text("✅ Test notification sent! Check your VR headset"),
                            bgcolor=colors.success
                        )
                    else:
                        error_msg = "Failed to send notification - WebSocket may have disconnected"
        except Exception as ex:
            error_msg = f"Test failed: {str(ex)}"
        
        if error_msg:
             self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"❌ {error_msg}"),
                bgcolor=colors.danger
            )
        
        self.page.snack_bar.open = True
        self.page.update()
        
        self._xso_test_button.set_loading(False)
        self._xso_test_button.update()

    def _handle_xso_throttle_toggle(self, e):
        """Toggle performance throttling"""
        alert_service = get_alert_service()
        if alert_service:
            # We don't have a direct setting for this in config yet, but would go here
            pass

    def _handle_xso_theme_sync_toggle(self, e):
        """Toggle theme sync"""
        # Future implementation
        pass

    def _build_database_section(self) -> ft.Control:
        """Build Database Management Section"""
        return GlassPanel(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.STORAGE_ROUNDED, color=colors.accent_primary),
                            ft.Text("Database Management", size=typography.size_lg, weight=ft.FontWeight.W_600, color=colors.text_primary),
                        ],
                        spacing=spacing.sm,
                    ),
                    ft.Divider(color=colors.glass_border, height=spacing.md),
                    ft.Text(
                        "View and verify system records integrity.",
                        size=typography.size_sm,
                        color=colors.text_secondary,
                    ),
                    ft.Container(height=spacing.sm),
                    NeonButton(
                        text="Open Database Inspector",
                        icon=ft.Icons.OPEN_IN_NEW_ROUNDED,
                        on_click=lambda _: self.on_navigate("/database") if self.on_navigate else None,
                        variant="secondary",
                        width=250
                    )
                ]
            )
        )
    
    async def _handle_xso_throttle_toggle(self, e):
        """Toggle performance throttling"""
        from services.xsoverlay import get_xsoverlay_service
        xso = get_xsoverlay_service()
        if xso:
            xso.config.performance_throttle_enabled = e.control.value
            status = "enabled" if e.control.value else "disabled"
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Performance throttling {status}"),
                bgcolor=colors.bg_elevated
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    async def _handle_xso_theme_sync_toggle(self, e):
        """Toggle theme synchronization with XSOverlay"""
        from services.xsoverlay import get_xsoverlay_service
        xso = get_xsoverlay_service()
        if xso:
            xso.config.theme_sync_enabled = e.control.value
            
            if e.control.value:
                # Register theme change callback
                def on_theme_change(color: str):
                    if self.on_theme_change:
                        self.on_theme_change(color)
                xso.on_theme_change(on_theme_change)
                
                # Apply current XSOverlay color if available
                if xso.accent_color:
                    if self.on_theme_change:
                        self.on_theme_change(xso.accent_color)
                        
            status = "enabled" if e.control.value else "disabled"
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Theme sync {status}"),
                bgcolor=colors.bg_elevated
            )
            self.page.snack_bar.open = True
            self.page.update()

    def _build_update_section(self) -> ft.Control:
        """Build Update Checker Section"""
        
        self._update_status_text = ft.Text(f"Current Version: v{UpdateService.CURRENT_VERSION}", color=colors.text_secondary, size=typography.size_sm)
        self._update_button = NeonButton(
            text="Check for Updates", 
            icon=ft.Icons.UPDATE, 
            on_click=self._handle_check_update,
            variant="secondary",
            height=40
        )
        
        self._update_progress = ft.ProgressBar(width=None, value=0, color=colors.accent_primary, bgcolor=colors.bg_deep, visible=False)
        
        return GlassPanel(
            content=ft.Column(
                controls=[
                    ft.Row(controls=[ft.Icon(ft.Icons.SYSTEM_UPDATE_ALT, color=colors.accent_secondary), ft.Text("Application Updates", size=typography.size_lg, weight=ft.FontWeight.W_600, color=colors.text_primary)], spacing=spacing.sm),
                    ft.Divider(color=colors.glass_border, height=spacing.md),
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    self._update_status_text,
                                    ft.Text("Auto-updates for portable exe", size=typography.size_xs, color=colors.text_tertiary)
                                ],
                                spacing=2
                            ),
                            ft.Container(expand=True),
                            self._update_button
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    ft.Container(height=5),
                    self._update_progress
                ]
            )
        )

    async def _handle_check_update(self, e):
        """Handle update check"""
        self._update_button.set_loading(True)
        self._update_button.update()
        
        try:
             # Now returns asset_url instead of html_url
             is_new, tag, asset_url, body = await UpdateService.check_for_updates()
             
             if is_new:
                 self._update_status_text.value = f"New Version Available: {tag}"
                 self._update_status_text.color = colors.success
                 
                 # Prepare for download
                 self._update_button.text = "Install Now"
                 self._update_button.icon = ft.Icons.DOWNLOAD_ROUNDED
                 self._update_button.set_loading(False)
                 
                 # Define download callback with the captured asset_url
                 async def do_update(ev):
                     await self._handle_download_update(asset_url)
                     
                 self._update_button._on_click = do_update 
                 self._update_button.start_icon_shimmer()
                 
             else:
                 self._update_status_text.value = f"You are up to date (v{UpdateService.CURRENT_VERSION})"
                 self._update_button.text = "Check for Updates"
                 self._update_button.set_loading(False)
                 
        except Exception as ex:
             print(f"Update check error: {ex}")
             self._update_button.set_loading(False)
             
        self._update_status_text.update()
        self._update_button.update()
        
    async def _handle_download_update(self, asset_url):
        """Download and install update"""
        print(f"Starting update download from {asset_url}")
        self._update_button.set_loading(True)
        self._update_progress.visible = True
        self._update_progress.value = None 
        self._update_progress.update()
        
        try:
             # Progress callback
             def on_progress(p):
                 self._update_progress.value = p
                 self._update_progress.update()

             # Download directly using the url we found earlier
             path = await UpdateService.download_update(asset_url, on_progress)
             
             # Apply
             self._update_status_text.value = "Restarting to apply update..."
             self._update_status_text.update()
             
             import asyncio
             await asyncio.sleep(1)
             
             UpdateService.apply_update(path)
             
        except Exception as e:
            print(f"Update failed: {e}")
            self._update_button.set_loading(False)
            self._update_progress.visible = False
            self._update_progress.update()
            
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Update failed: {e}"), bgcolor=colors.danger)
            self.page.snack_bar.open = True
            self.page.update()

    def _build_credits_section(self) -> ft.Control:
        """Build the Developer Credits section"""
        return GlassPanel(
            ref=self._dev_card_ref,
            content=self._build_dev_profile_content()
        )

    def _build_dev_profile_content(self) -> ft.Control:
        """Internal builder for dev profile content"""
        
        # Default/Fallback Data
        name = self._dev_profile_data.get("name") if self._dev_profile_data else "AppleExpl01t"
        status = self._dev_profile_data.get("status") if self._dev_profile_data else "Developer"
        pfp_src = self._dev_profile_data.get("pfp") if self._dev_profile_data else ""
        banner_src = self._dev_profile_data.get("banner") if self._dev_profile_data else ""
        
        # Banner Image (with fallback gradient)
        banner = ft.Container(
            content=ft.Image(src=banner_src, fit=ft.ImageFit.COVER, opacity=0.6) if banner_src else None,
            height=120,
            bgcolor=colors.accent_primary if not banner_src else None,
            border_radius=ft.border_radius.only(top_left=radius.lg, top_right=radius.lg),
            gradient=ft.LinearGradient(colors=[colors.accent_primary, colors.bg_deepest]) if not banner_src else None
        )

        # Profile Picture (Centered circles)
        pfp = ft.Container(
            content=ft.Image(src=pfp_src, fit=ft.ImageFit.COVER) if pfp_src else ft.Icon(ft.Icons.PERSON, size=40),
            width=80, height=80,
            border_radius=radius.full,
            border=ft.border.all(3, colors.bg_deepest),
            bgcolor=colors.bg_elevated,
            alignment=ft.alignment.center,
            shadow=shadows.glow_purple(blur=10)
        )
        
        # Speech Bubble
        bubble = ft.Container(
            content=ft.Text(f"\"{status}\"", size=12, italic=True, color=colors.text_primary),
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            bgcolor=colors.bg_elevated,
            border_radius=radius.md,
            border=ft.border.all(2, colors.accent_secondary),
        )
        
        # Use Stack for PFP overlapping Banner
        # Banner is at top. PFP is centered and "low on top", meaning overlapping the bottom edge of banner.
        
        # Ensure banner stretches in Stack
        banner.left = 0
        banner.right = 0
        banner.top = 0
        
        profile_stack = ft.Stack(
            controls=[
                banner,
                ft.Container(
                    content=pfp,
                    alignment=ft.alignment.top_center,
                    top=80, # Banner (120) - Half PFP (40) = 80
                    left=0, right=0,
                ),
            ],
            height=160,
            clip_behavior=ft.ClipBehavior.NONE, 
        )

        # Info Section
        info_col = ft.Column(
            controls=[
                ft.Container(height=10),
                bubble if status else ft.Container(),
                ft.Container(height=10),
                ft.Text(name, size=typography.size_xl, weight=ft.FontWeight.BOLD, color=colors.accent_primary),
                ft.Text("Lead Developer", size=typography.size_sm, color=colors.text_tertiary),
                ft.Container(height=spacing.md),
                
                # Discord Link
                NeonButton(
                    text="Support & Bug Reports",
                    icon=ft.Icons.DISCORD,
                    on_click=lambda e: self.page.launch_url("https://discord.gg/eDKC5yEQJN"),
                    variant="primary",
                    width=250
                ),
                ft.Container(height=spacing.lg),
                
                # References
                ft.Text("Special Thanks & References", weight=ft.FontWeight.BOLD),
                ft.Row(
                    controls=[
                        ft.TextButton("vrcx-team", on_click=lambda e: self.page.launch_url("https://github.com/vrcx-team/VRCX")),
                        ft.Text("|", disabled=True),
                        ft.TextButton("Lumi-VRC", on_click=lambda e: self.page.launch_url("https://github.com/Lumi-VRC/FCH-Toolkit-App")),
                        ft.Text("|", disabled=True),
                        ft.TextButton("ComfyChloe", on_click=lambda e: self.page.launch_url("https://github.com/ComfyChloe/API-Automation-Tools")),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    wrap=True,
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=spacing.xs
        )

        return ft.Container(
            content=ft.Column([
                profile_stack,
                ft.Container(content=info_col, padding=spacing.lg)
            ], spacing=0)
        )

    def _handle_color_change(self, color: str):
        # ... (Same as before) ...
        # Basic validation for Hex codes
        if not color.startswith("#"):
            color = "#" + color
        
        # Simple length check (supports #RGB and #RRGGBB)
        if len(color) not in [4, 7]:
            if self.page:
                self.page.snack_bar = ft.SnackBar(content=ft.Text("Invalid Hex Code"), bgcolor=colors.danger)
                self.page.snack_bar.open = True
                self.page.update()
            return
        
        # Update core color
        colors.accent_primary = color
        
        # Update Flet page theme (affects some built-in controls)
        if self.page:
            self.page.theme = ft.Theme(color_scheme_seed=color)
            self.page.update()
        
        # Notify main app to refresh sidebar and other theme-aware components
        if self.on_theme_change:
            self.on_theme_change(color)
        
        # Rebuild settings panel
        if self._theme_settings_control:
             new_content = self._build_theme_settings()
             self.content.controls[2] = new_content
             self.content.update()
             
             self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Theme updated to {color}"), bgcolor=colors.bg_elevated)
             self.page.snack_bar.open = True
             self.page.update()

    def _handle_reset_theme(self, e):
        """Handle reset theme"""
        self._handle_color_change("#8b5cf6") # Default purple

    def _build_section_placeholder(self, title: str, subtitle: str) -> ft.Control:
        return GlassPanel(
            content=ft.Column(
                controls=[
                    ft.Row(controls=[ft.Icon(ft.Icons.SETTINGS_APPLICATIONS_ROUNDED, color=colors.text_secondary), ft.Text(title, size=typography.size_lg, weight=ft.FontWeight.W_600, color=colors.text_secondary)], spacing=spacing.sm),
                    ft.Text(subtitle, size=typography.size_sm, color=colors.text_tertiary),
                ]
            ),
            opacity=0.7
        )
