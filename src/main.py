"""
Group Guardian - Main Application Entry
=======================================
VRChat Group Moderation Automation Tool
"""

import sys
import os
import traceback

# --- DEBUG ALL THE THINGS ---
print("--- PYTHON STARTUP DEBUG ---")
print(f"CWD: {os.getcwd()}")
try:
    print(f"__file__: {__file__}")
    print(f"Dirname: {os.path.dirname(os.path.abspath(__file__))}")
except NameError:
    print("__file__ not defined")

print(f"sys.path before: {sys.path}")

# Ensure we are in the right place
if getattr(sys, 'frozen', False):
    app_dir = sys._MEIPASS
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))

if app_dir not in sys.path:
    print(f"Adding {app_dir} to sys.path")
    sys.path.insert(0, app_dir)

print(f"sys.path after: {sys.path}")

print("Directory listing of app_dir:")
try:
    for item in os.listdir(app_dir):
        print(f" - {item}")
        if os.path.isdir(os.path.join(app_dir, item)):
             print(f"   (DIR) Contents of {item}: {os.listdir(os.path.join(app_dir, item))}")
except Exception as e:
    print(f"Error listing dir: {e}")

print("Attempting imports...")
try:
    import api
    print(f"Import api successful: {api}")
    import api.mock_client
    print(f"Import api.mock_client successful")
except Exception as e:
    print(f"IMPORT DEBUG FAILED: {e}")
    traceback.print_exc()
print("--- END DEBUG ---")
# ----------------------------

# Standard imports
import json
import base64
from pathlib import Path
import flet as ft

# Application imports
from api.mock_client import MockVRChatAPI  # Demo Mode
from ui.theme import setup_theme, colors, spacing
from ui.components.sidebar import Sidebar
from ui.components.animated_background import SimpleGradientBackground
from ui.views.login import LoginView
from ui.views.welcome import WelcomeView
from ui.views.group_selection import GroupSelectionView
from ui.views.dashboard import DashboardView
from ui.views.instances import InstancesView
from api.client import VRChatAPI
from ui.views.requests import RequestsView
from ui.views.members import MembersView
from ui.views.bans import BansView
from ui.components.title_bar import TitleBar
from ui.views.settings import SettingsView
from ui.views.live_instance import LiveInstanceView
from ui.views.history import HistoryView
from services.log_watcher import get_log_watcher
from services.config import ConfigService
from services.updater import UpdateService


class GroupGuardianApp:
    """Main application class"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self._current_route = "/login"
        self._is_authenticated = False
        self._username = ""
        self._current_user = {}  # Store full user object
        self._login_view = None
        self._welcome_view = None
        self._group_selection_view = None
        
        # Current selected group
        self._current_group = None
        self._groups = []
        self._pending_requests_count = 0
        self._sidebar = None
        
        # Loading state lock to prevent concurrent fetches
        self._loading_groups_lock = False
        
        # Persistent Views
        self._live_view = None
        
        # VRChat API client
        self._api = VRChatAPI()
        
        # Setup theme
        setup_theme(page)
        
        # Window configuration - frameless for custom title bar
        page.window.width = 1280
        page.window.height = 800
        page.window.min_width = 1024
        page.window.min_height = 600
        page.window.center()
        page.title = "Group Guardian"
        page.window.frameless = True  # Frameless window for custom title bar
        
        # Set window icon (still used in taskbar)
        import os
        self._icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "icon.png"))
        if os.path.exists(self._icon_path):
            page.window.icon = self._icon_path
        
        # Route handling
        page.on_route_change = self._on_route_change
        
        # Show splash immediately to hide login during auto-auth
        self._show_splash()
        
        # Determine platform capabilities
        # Live Monitor relies on local log files, so disable on mobile
        self._supports_live = page.platform not in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
        
        # Start Log Watcher for global state (group detection) if supported
        self._watcher = None
        if self._supports_live:
            try:
                self._watcher = get_log_watcher(self._handle_global_log_event)
                self._watcher.start()
            except Exception as e:
                print(f"Failed to start LogWatcher: {e}")
                self._supports_live = False # Fallback if start fails
        
        # Check for existing session in background
        self.page.run_task(self._check_existing_session)
    
    async def _check_existing_session(self):
        """Check if we have a valid saved session"""
        print("Checking for existing session...")
        # Add slight delay to let splash render if it was just added
        import asyncio
        await asyncio.sleep(0.1)
        
        try:
            result = await self._api.check_session()
            
            if result.get("valid"):
                user = result.get("user", {})
                self._username = user.get("displayName", "User")
                self._current_user = user
                self._is_authenticated = True
                print(f"Session valid! Logged in as: {self._username}")
                # Show welcome screen -> group selection
                self._show_welcome(user)
            else:
                print("No valid session, trying stored credentials...")
                saved_user, saved_pass = self._load_credentials()
                if saved_user and saved_pass:
                    print(f"Found stored credentials for {saved_user}, attempting login...")
                    result = await self._do_login_sequence(saved_user, saved_pass)
                    if result.get("success"):
                        return

                print("No valid session or credentials")
                self._show_login()
        except Exception as e:
            print(f"Session check error: {e}")
            self._show_login()
    
    def _create_view_with_titlebar(self, content: ft.Control, keep_view_ref=None) -> ft.View:
        """Create a view with custom title bar
        
        Args:
            content: The content control or View to wrap
            keep_view_ref: If content is a View, we need to manually update its page reference
        """
        # If content is already a View, extract its controls
        if isinstance(content, ft.View):
            inner_controls = content.controls if content.controls else []
            # Wrap the inner controls
            inner_content = ft.Container(
                content=ft.Column(controls=inner_controls, expand=True, spacing=0),
                expand=True,
                bgcolor=content.bgcolor,
            )
        else:
            inner_content = ft.Container(content=content, expand=True)
        
        # Determine route
        route = "/"
        if isinstance(content, ft.View) and content.route:
            route = content.route
            
        return ft.View(
            route,
            controls=[
                ft.Column(
                    controls=[
                        TitleBar(title="Group Guardian", icon_path=self._icon_path),
                        inner_content,
                    ],
                    spacing=0,
                    expand=True,
                )
            ],
            padding=0,
            bgcolor=colors.bg_deepest,
        )

    def _show_splash(self):
        """Show splash screen while checking session"""
        self.page.views.clear()
        
        content = ft.Column(
            controls=[
                ft.Icon(ft.Icons.SHIELD_ROUNDED, size=80, color=colors.accent_primary),
                ft.Container(height=spacing.md),
                ft.Text("Group Guardian", size=32, weight=ft.FontWeight.BOLD, color=colors.text_primary),
                ft.Container(height=spacing.xl),
                ft.ProgressRing(color=colors.accent_primary, width=24, height=24),
                ft.Container(height=spacing.sm),
                ft.Text("Initializing...", size=typography.size_sm, color=colors.text_tertiary)
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        )
        
        # Use simple gradient background
        background = SimpleGradientBackground(content=ft.Container(content=content, alignment=ft.alignment.center))
        
        view = self._create_view_with_titlebar(background)
        self.page.views.append(view)
        self.page.update()
    
    def _show_login(self):
        """Show login view"""
        self.page.views.clear()
        
        # Check for stored credentials for autofill
        saved_user, saved_pass = self._load_credentials()
        
        self._login_view = LoginView(
            on_login=self._handle_login,
            on_login_success=self._handle_login_success,
            on_2fa_verify=self._handle_2fa_verify,
            on_demo_login=self._start_demo_mode,
            initial_username=saved_user or "",
            initial_password=saved_pass or "",
            initial_remember=bool(saved_user),
        )
        
        # Wrap with title bar
        view = self._create_view_with_titlebar(self._login_view)
        self.page.views.append(view)
        self.page.update()
        
        # Manually set page reference since we extracted controls from the View
        self._login_view.page = self.page
    
    async def _do_login_sequence(self, username, password) -> dict:
        """Execute login logic, returns result dict"""
        result = await self._api.login(username, password)
        
        if result.get("success"):
            if result.get("requires_2fa"):
                # if we are doing silent login from startup, we must show UI now
                if not self._login_view:
                     self._show_login()
                
                tfa_type = result.get("2fa_type", "emailOtp")
                print(f"2FA required: {tfa_type}")
                if self._login_view:
                    self._login_view.show_2fa_required(tfa_type)
            else:
                user = result.get("user", {})
                self._username = user.get("displayName", username)
                self._current_user = user
                self._handle_login_success()
        
        return result

    def _handle_login(self, username: str, password: str, remember_me: bool = False):
        """Handle login attempt with real VRChat API"""
        self._username = username
        print(f"Login attempt: {username}, Remember: {remember_me}")
        
        if remember_me:
            self._save_credentials(username, password)
        else:
            self._clear_credentials()
        
        async def do_login():
            result = await self._do_login_sequence(username, password)
            
            if not result.get("success"):
                error = result.get("error", "Login failed")
                print(f"Login failed: {error}")
                if self._login_view:
                    self._login_view.show_login_error(error)

        self.page.run_task(do_login)

    def _save_credentials(self, username, password):
        """Save credentials to local file (simple encoding)"""
        try:
            data = f"{username}:{password}".encode("utf-8")
            b64_data = base64.b64encode(data).decode("utf-8")
            with open("storage.json", "w") as f:
                json.dump({"auth": b64_data}, f)
        except Exception as e:
            print(f"Failed to save credentials: {e}")

    def _load_credentials(self):
        """Load stored credentials"""
        try:
            if not os.path.exists("storage.json"):
                return None, None
            with open("storage.json", "r") as f:
                data = json.load(f)
            
            if "auth" in data:
                decoded = base64.b64decode(data["auth"]).decode("utf-8")
                if ":" in decoded:
                    return decoded.split(":", 1)
            return None, None
        except Exception as e:
            print(f"Failed to load credentials: {e}")
            return None, None
            
    def _clear_credentials(self):
        """Clear stored credentials"""
        if os.path.exists("storage.json"):
            try:
                os.remove("storage.json")
            except: 
                pass
    
    def _handle_2fa_verify(self, code: str):
        """Handle 2FA code verification"""
        print(f"Verifying 2FA code: {code}")
        
        async def do_verify():
            result = await self._api.verify_2fa(code)
            
            if result.get("success"):
                user = result.get("user", {})
                self._username = user.get("displayName", self._username)
                self._current_user = user
                print(f"2FA verified! Logged in as: {self._username}")
                self._handle_login_success()
            else:
                error = result.get("error", "Invalid code")
                print(f"2FA verification failed: {error}")
                if self._login_view:
                    self._login_view.show_2fa_error(error)
        
        self.page.run_task(do_verify)
    
    def _handle_login_success(self):
        """Handle successful login - go to welcome screen"""
        self._is_authenticated = True
        if self._current_user:
            self._show_welcome(self._current_user)
        else:
            # Fallback if no user object (shouldn't happen)
            self.page.go("/groups")
    
    def _show_welcome(self, user: dict):
        """Show cinematic welcome screen"""
        self.page.views.clear()
        self._welcome_view = WelcomeView(user)
        view = self._create_view_with_titlebar(self._welcome_view)
        self.page.views.append(view)
        self.page.update()
        
        # Manually set page reference since we extracted controls from the View
        self._welcome_view.page = self.page
        
        # Manually trigger the animation since did_mount won't be called on extracted controls
        if hasattr(self._welcome_view, 'did_mount'):
            self._welcome_view.did_mount()
        
        # Start loading groups and specific user assets
        self.page.run_task(self._load_data_and_transition)
        
    async def _load_data_and_transition(self):
        """Load data in background while showing welcome animation"""
        import asyncio
        
        # Start user asset loading (PFP)
        self.page.run_task(self._load_user_assets)
        
        # Load groups and WAIT so we can decide navigation
        await self._load_groups(force_refresh=True)
        
        # Strict wait for cinematic feel
        await asyncio.sleep(3.5)
        
        print(f"Transitioning... Found {len(self._groups)} groups")
        
        # Auto-select if only 1 group
        if len(self._groups) == 1:
            print("Single group detected, skipping selection.")
            self._handle_group_select(self._groups[0])
        else:
            print("Transitioning to group selection...")
            self._show_group_selection()
        
    async def _load_user_assets(self):
        """Securely load user PFP"""
        if not self._current_user:
            return
            
        # Download authenticated image
        pfp_path = await self._api.cache_user_image(self._current_user)
        
        # Update view if we are still on welcome screen
        if pfp_path and self._welcome_view:
            self._welcome_view.set_avatar_image(pfp_path)
            
        if pfp_path:
            self._current_user["local_pfp"] = pfp_path

    async def _start_demo_mode(self, e=None):
        """Start demo mode with mock API"""
        print("Starting Demo Mode...")
        self._api = MockVRChatAPI()
        
        # Verify mock login
        try:
             await self._api.login()
             self._current_user = self._api.current_user
             self._is_authenticated = True
             self._groups = [] # Reset groups
             
             # Cache (fake) user image
             # Note: _show_welcome will trigger _load_data_and_transition which calls _load_user_assets properly
             
             # Navigate to welcome
             self._show_welcome(self._current_user)
             
        except Exception as ex:
            print(f"Demo failed: {ex}")
            import traceback
            traceback.print_exc()
            
    
    def _show_group_selection(self):
        """Show group selection view"""
        self.page.views.clear()
        self._group_selection_view = GroupSelectionView(
            groups=self._groups,  # Use currently known groups
            on_group_select=self._handle_group_select,
            on_logout=self._handle_logout,
            on_refresh=self._handle_refresh_groups,
            on_settings=lambda e: self.page.go("/settings"),
            username=self._username,
            pfp_path=self._current_user.get("local_pfp"),
            user_data=self._current_user,
            current_group_id=self._watcher.current_group_id if(self._watcher and self._supports_live) else None,
            supports_live=self._supports_live,
        )
        view = self._create_view_with_titlebar(self._group_selection_view)
        self.page.views.append(view)
        self.page.update()
        
        # Manually set page reference since we extracted controls from the View
        self._group_selection_view.page = self.page
        
        # Fetch groups async if empty
        if not self._groups:
             print("Groups empty or not loaded, triggering fetch...")
             self.page.run_task(lambda: self._load_groups(force_refresh=True))
    
    async def _handle_refresh_groups(self, e=None):
        """Force refresh groups"""
        await self._load_groups(force_refresh=True)
            
    async def _load_groups(self, force_refresh: bool = False):
        """Load user's groups with mod permissions"""
        if self._loading_groups_lock:
            print("Group load already in progress...")
            return

        self._loading_groups_lock = True
        try:
            if self._groups and not force_refresh:
                print("Using cached groups")
                if self._group_selection_view:
                     self._group_selection_view.set_groups(self._groups)
                return

            print("Loading groups...")
            if self._group_selection_view:
                self._group_selection_view.set_loading(True)
            
            # Add visual delay for feedback on manual refresh
            if force_refresh:
                import asyncio
                await asyncio.sleep(0.8)
                
            groups = await self._api.get_my_groups(force_refresh=force_refresh)
            print(f"Found {len(groups)} groups with mod permissions")
            
            # Cache group images locally (VRChat URLs require auth cookies)
            import asyncio
            for group in groups:
                # Download images with auth and replace URLs with local paths
                await self._api.cache_group_images(group)
            
            self._groups = groups
            
            if self._group_selection_view:
                self._group_selection_view.set_groups(groups)
                self._group_selection_view.set_loading(False)
                
        except Exception as e:
            print(f"Error loading groups: {e}")
            if self._group_selection_view:
                 self._group_selection_view.set_loading(False)
        finally:
            self._loading_groups_lock = False
    
    def _handle_group_select(self, group: dict):
        """Handle group selection"""
        self._current_group = group
        print(f"Selected group: {group.get('name')} ({group.get('id')})")
        
        # Update window title
        self.page.title = f"Group Guardian - {group.get('name')}"
        
        # Navigate to dashboard for this group
        self.page.go("/dashboard")
    
    def _handle_logout(self):
        """Handle logout"""
        async def do_logout():
            await self._api.logout()
            
            # Reset to real API client (exits Demo Mode)
            self._api = VRChatAPI()
            
            self._is_authenticated = False
            self._current_group = None
            self._groups = []
            self._username = ""
            self._welcome_view = None # Clear stale view reference
            self._live_view = None # Clear stale live view reference
            print("Logged out")
            self.page.go("/login")
        
        self.page.run_task(do_logout)
    
    def _on_route_change(self, e: ft.RouteChangeEvent):
        """Handle route changes"""
        route = e.route
        
        if route == "/login" or not self._is_authenticated:
            self._show_login()
            return
        
        if route == "/welcome":
             if self._current_user:
                 self._show_welcome(self._current_user)
             return

        if route == "/groups":
            self._show_group_selection()
            return
        
        if route == "/live":
            # Allow live view without group selection, but use main view layout
             self.page.views.clear()
             self.page.views.append(self._build_main_view(route))
             self.page.update()
             return

        if route == "/settings":
            # Allow settings without group selection
            self.page.views.clear()
            self.page.views.append(self._build_main_view(route))
            self.page.update()
            return

        if not self._current_group:
            # No group selected, go to group selection
            self.page.go("/groups")
            return
        
        # Build main app layout for selected group
        self.page.views.clear()
        self.page.views.append(self._build_main_view(route))
        self.page.update()
    
    def _build_main_view(self, route: str) -> ft.View:
        """Build main app view with sidebar and content"""
        
        # Sidebar with group name and user data
        
        # Determine nav items based on route context
        custom_nav = None
        if route == "/live":
            custom_nav = [
                 {"icon": ft.Icons.PLAY_CIRCLE_ROUNDED, "label": "Live", "route": "/live"},
            ]
            # When in /live, we usually want to go back to group selection easily
            
        self._sidebar = Sidebar(
            on_navigate=self._navigate,
            on_logout=self._handle_logout,
            current_route=route,
            user_name=self._username or "User",
            user_data=self._current_user,  # Pass full user data for avatar and status
            badge_counts={"/requests": self._pending_requests_count},
            nav_items=custom_nav
        )
        
        # Content area
        content = self._get_content_for_route(route)
        
        # Group header bar (Only if group selected)
        if self._current_group:
            group_header = ft.Container(
                content=ft.Row(
                    controls=[
                        # Group icon
                        ft.Container(
                            content=ft.Image(
                                src=self._current_group.get("iconUrl", ""),
                                fit=ft.ImageFit.COVER,
                                width=32,
                                height=32,
                                border_radius=radius.sm,
                            ) if self._current_group.get("iconUrl") else ft.Icon(
                                ft.Icons.GROUPS_ROUNDED,
                                size=24,
                                color=colors.accent_primary,
                            ),
                            width=40,
                            height=40,
                            border_radius=radius.sm,
                            bgcolor=colors.bg_elevated,
                            alignment=ft.alignment.center,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    self._current_group.get("name", "Group"),
                                    size=typography.size_base,
                                    weight=ft.FontWeight.W_600,
                                    color=colors.text_primary,
                                ),
                                ft.Text(
                                    f"{self._current_group.get('memberCount', 0):,} members",
                                    size=typography.size_xs,
                                    color=colors.text_tertiary,
                                ),
                            ],
                            spacing=0,
                        ),
                        ft.Container(expand=True),
                        ft.TextButton(
                            "Back to group selection",
                            style=ft.ButtonStyle(color=colors.accent_secondary),
                            on_click=lambda e: self.page.go("/groups"),
                        ),
                    ],
                    spacing=spacing.md,
                ),
                padding=ft.padding.symmetric(horizontal=spacing.lg, vertical=spacing.sm),
                bgcolor=colors.bg_base,
                border=ft.border.only(bottom=ft.BorderSide(1, colors.glass_border)),
            )
        else:
             # Minimal header for non-group views (like Live when accessed from root)
             group_header = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.SHIELD_ROUNDED, color=colors.accent_primary),
                        ft.Text("Group Guardian", weight=ft.FontWeight.BOLD, color=colors.text_primary),
                        ft.Container(expand=True),
                        ft.TextButton(
                            "Back to group selection",
                            style=ft.ButtonStyle(color=colors.accent_secondary),
                            on_click=lambda e: self.page.go("/groups"),
                        ),
                    ]
                ),
                padding=ft.padding.symmetric(horizontal=spacing.lg, vertical=spacing.sm),
                bgcolor=colors.bg_base,
                border=ft.border.only(bottom=ft.BorderSide(1, colors.glass_border)),
             )
        
        # Main content with header
        content_column = ft.Column(
            controls=[
                group_header,
                ft.Container(
                    content=SimpleGradientBackground(content=content),
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )
        
        # Main layout
        main_row = ft.Row(
            controls=[
                self._sidebar,
                content_column,
            ],
            spacing=0,
            expand=True,
        )
        
        # Wrap everything with title bar
        full_layout = ft.Column(
            controls=[
                TitleBar(title="Group Guardian", icon_path=self._icon_path),
                ft.Container(content=main_row, expand=True),
            ],
            spacing=0,
            expand=True,
        )
        
        return ft.View(
            route=route,
            padding=0,
            bgcolor=colors.bg_deepest,
            controls=[full_layout],
        )
    
    def _navigate(self, route: str):
        """Navigate to a route"""
        self.page.go(route)
        
    def _handle_stats_update(self, stats: dict):
        """Handle stats updates from views"""
        if "pending_requests" in stats:
            self._pending_requests_count = stats["pending_requests"]
            if self._sidebar:
                self._sidebar.set_badge("/requests", self._pending_requests_count)
    
    def _get_content_for_route(self, route: str) -> ft.Control:
        """Get content control for a route"""
        
        if route == "/live":
            if not self._supports_live:
                return ft.Container(content=ft.Text("Live Monitor not supported on this device", color=colors.text_secondary), alignment=ft.alignment.center)

            if not self._live_view:
                self._live_view = LiveInstanceView(
                    api=self._api,
                    on_navigate=self._navigate
                )
            return self._live_view

        if route == "/dashboard":
            return DashboardView(
                group=self._current_group,
                api=self._api,
                on_navigate=self._navigate,
                on_update_stats=self._handle_stats_update
            )
        
        elif route == "/instances":
            return InstancesView(
                group=self._current_group,
                api=self._api,
                on_navigate=self._navigate
            )
        
        elif route == "/requests":
            return RequestsView(
                group=self._current_group,
                api=self._api,
                on_navigate=self._navigate,
                on_update_stats=self._handle_stats_update
            )
        
        elif route == "/members":
            return MembersView(
                group=self._current_group,
                api=self._api,
                on_navigate=self._navigate
            )
        
        elif route == "/bans":
            return BansView(
                group=self._current_group,
                api=self._api,
                on_navigate=self._navigate
            )
        
        elif route == "/history":
             return HistoryView(
                 api=self._api,
                 on_navigate=self._navigate
             )
        
        elif route == "/logs":
            return self._placeholder_view("Audit Logs", "View moderation activity history")
        
        elif route == "/settings":
            return SettingsView(on_navigate=self._navigate, api=self._api)
        
        else:
            return DashboardView()
    
    def _handle_global_log_event(self, event: dict):
        """Handle global log events (e.g. for group detection)"""
        if not self._supports_live:
             return
             
        if event.get("type") == "instance_change":
            group_id = event.get("group_id")
            
            # If we are on the group selection screen, update it
            if self._group_selection_view and self._current_route == "/groups":
                 # We must run UI updates on the main thread
                 # Flet's page.run_task might be needed if called from thread
                 # But modifying the view state and calling update() usually works if thread-safe
                 # Or just rebuild the view logic?
                 # GroupSelectionView has set_current_group_id
                 self._group_selection_view.set_current_group_id(group_id)

    def _placeholder_view(self, title: str, subtitle: str) -> ft.Control:
        """Create a placeholder view for unimplemented routes"""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        title,
                        size=32,
                        weight=ft.FontWeight.W_700,
                        color=colors.text_primary,
                    ),
                    ft.Text(
                        subtitle,
                        size=16,
                        color=colors.text_secondary,
                    ),
                    ft.Container(height=spacing.xl),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Icon(
                                    ft.Icons.CONSTRUCTION_ROUNDED,
                                    size=64,
                                    color=colors.text_tertiary,
                                ),
                                ft.Container(height=spacing.md),
                                ft.Text(
                                    "Coming Soon",
                                    size=24,
                                    weight=ft.FontWeight.W_600,
                                    color=colors.text_tertiary,
                                ),
                                ft.Text(
                                    "This feature is under development",
                                    size=14,
                                    color=colors.text_tertiary,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        alignment=ft.alignment.center,
                        expand=True,
                    ),
                ],
                expand=True,
            ),
            expand=True,
            padding=spacing.lg,
        )


# Need to import these for the group header
from ui.theme import radius, typography




def main(page: ft.Page):
    """Application entry point"""
    # Handle auto-update process if flags are present
    UpdateService.handle_update_process()
    
    try:
        GroupGuardianApp(page)
    except Exception as e:
        page.clean()
        page.add(
            ft.Column([
                ft.Text("Critical Error during startup:", size=20, weight="bold", color="red"),
                ft.Text(str(e), color="yellow"),
                ft.Text(traceback.format_exc(), size=10, font_family="monospace"),
            ], scroll="auto")
        )
        page.update()


if __name__ == "__main__":
    ft.app(target=main)
