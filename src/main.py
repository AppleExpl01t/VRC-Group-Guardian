"""
Group Guardian - Main Application Entry
=======================================
VRChat Group Moderation Automation Tool
"""

import sys
import os
import traceback

# --- INITIALIZE DEBUG LOGGING FIRST ---
from services.debug_logger import init_logging, get_logger

# Initialize logging before anything else
init_logging()
logger = get_logger("main")

logger.info("Application starting...")
logger.debug(f"CWD: {os.getcwd()}")
try:
    logger.debug(f"__file__: {__file__}")
    logger.debug(f"Dirname: {os.path.dirname(os.path.abspath(__file__))}")
except NameError:
    logger.debug("__file__ not defined")

logger.debug(f"sys.path before: {sys.path}")

# Ensure we are in the right place
if getattr(sys, 'frozen', False):
    app_dir = sys._MEIPASS
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))

if app_dir not in sys.path:
    logger.debug(f"Adding {app_dir} to sys.path")
    sys.path.insert(0, app_dir)

logger.debug(f"sys.path after: {sys.path}")

logger.info("Attempting module imports...")
try:
    import api
    logger.debug(f"Import api successful: {api}")
    import api.mock_client
    logger.debug(f"Import api.mock_client successful")
except Exception as e:
    logger.error(f"IMPORT FAILED: {e}")
    import traceback
    traceback.print_exc()
logger.info("Core imports complete")
# --- END LOGGING INIT ---

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
from ui.views.watchlist import WatchlistView
from services.log_watcher import get_log_watcher
from services.watchlist_alerts import get_alert_service
from services.updater import UpdateService
from services.websocket_pipeline import get_pipeline, get_event_handler
from services.instance_context import get_instance_context, InstanceContextState
from services import focus_debugger as fd
from ui.dialogs.data_folder_setup import show_data_folder_setup
from utils.paths import is_data_folder_configured
from services.debug_controller import DebugController

# Initialize focus debugger early
fd.init_focus_debugger()
fd.log_info("Main app starting - focus debugger active")


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
        self._sidebar_collapsed = False # Persistent sidebar state
        
        # Loading state lock to prevent concurrent fetches
        self._loading_groups_lock = False
        
        # Persistent Views
        self._live_view = None
        
        # VRChat API client
        self._api = VRChatAPI()
        
        # WebSocket pipeline for real-time updates (friend status, notifications, etc.)
        self._pipeline = get_pipeline()
        self._pipeline_connected = False
        
        # Update State
        self._update_available = False
        self._update_info = None  # (version, url, notes)

        # Agentic Debug Interface - Re-enabled for focus debugging
        self._debug_controller = DebugController(self)
        self._debug_controller.start_listener()

        
        # Setup theme
        setup_theme(page)
        
        # Import responsive utilities for platform detection
        from ui.utils.responsive import is_mobile_platform, is_touch_device, get_config
        
        # Store responsive config for use throughout app
        self._is_mobile = is_mobile_platform(page)
        self._responsive_config = get_config(page)
        
        # Window configuration - conditional on platform
        # Desktop: custom frameless window with minimum sizes
        # Mobile: use default system chrome and full screen
        page.title = "Group Guardian"
        
        import os
        self._icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "icon.png"))
        
        if not self._is_mobile:
            # Desktop configuration
            page.window.width = 1280
            page.window.height = 800
            page.window.min_width = 1024
            page.window.min_height = 600
            page.window.center()
            page.window.frameless = True  # Custom title bar for desktop
            
            # Set window icon (used in taskbar)
            if os.path.exists(self._icon_path):
                page.window.icon = self._icon_path
        else:
            # Mobile configuration
            # Use system chrome, no minimum sizes (they break mobile)
            logger.info(f"Running on mobile platform: {page.platform}")
        
        # Route handling
        page.on_route_change = self._on_route_change
        
        # Responsive layout - auto-collapse sidebar on narrow windows (desktop only)
        if not self._is_mobile:
            page.on_resized = self._on_window_resized
        
        # Show splash immediately to hide login during auto-auth
        self._show_splash()
        
        # Determine platform capabilities
        # Live Monitor relies on local log files, so disable on mobile
        self._supports_live = not self._is_mobile
        
        # Move LogWatcher start to async task to prevent init blocking
        self.page.run_task(self._init_services)
        
        # Check if data folder needs to be configured (first launch)
        logger.info("Checking data folder configuration...")
        if not is_data_folder_configured():
            logger.info("Data folder not configured, showing setup...")
            # Show setup dialog - will call _on_data_folder_configured when done
            show_data_folder_setup(page, on_complete=self._on_data_folder_configured)
        else:
            # Already configured, proceed with startup steps
            self.page.run_task(self._check_for_updates)
            self.page.run_task(self._check_existing_session)
            logger.debug("Startup tasks scheduled.")
    
    async def _init_services(self):
        """Initialize background services asynchronously"""
        import asyncio
        
        self._watcher = None
        self._alert_service = None
        self._instance_context = None
        
        if self._supports_live:
            try:
                logger.info("Starting LogWatcher (Async)...")
                # get_log_watcher might allow thread start, which is fast.
                self._watcher = get_log_watcher(self._handle_global_log_event)
                self._watcher.start()
                logger.info("LogWatcher started (Async).")
                
                # Initialize alert service (will set API client after login)
                self._alert_service = get_alert_service()
                logger.info("WatchlistAlertService initialized.")
                
                # Initialize instance context service for moderation context awareness
                self._instance_context = get_instance_context()
                self._instance_context.attach_log_watcher(self._watcher)
                self._instance_context.add_listener(self._on_instance_context_change)
                logger.info("InstanceContextService initialized and attached to LogWatcher.")
                
                # Start background alert processing loop
                self.page.run_task(self._process_alerts_loop)
                
            except Exception as e:
                logger.error(f"Failed to start LogWatcher: {e}")
                self._supports_live = False
    
    async def _process_alerts_loop(self):
        """Background loop to process pending watchlist alerts"""
        import asyncio
        while True:
            try:
                if self._alert_service and self._alert_service.enabled:
                    await self._alert_service.process_pending_alerts()
            except Exception as e:
                logger.debug(f"Alert processing error: {e}")
            await asyncio.sleep(1.0)  # Check for new alerts every second
    
    def _handle_global_log_event(self, event: dict):
        """
        Handle log watcher events globally.
        
        This method:
        1. Passes events to WatchlistAlertService for alert processing
        2. Updates GroupSelectionView on instance changes
        
        Note: LiveInstanceView handles its own events via direct LogWatcher registration.
        """
        if not self._supports_live:
            return
            
        # Pass to alert service for watchlist notifications
        if self._alert_service:
            self._alert_service.on_event(event)
        
        # Handle instance changes for group selection view
        if event.get("type") == "instance_change":
            group_id = event.get("group_id")
            
            # If we are on the group selection screen, update it
            if self._group_selection_view and self._current_route == "/groups":
                self._group_selection_view.set_current_group_id(group_id)

    def _on_data_folder_configured(self, path: str):
        """Called when user completes data folder setup."""
        logger.info(f"Data folder configured: {path}")
        # Now proceed with startup steps
        self.page.run_task(self._check_for_updates)
        self.page.run_task(self._check_existing_session)
    
    def _on_instance_context_change(self, context):
        """
        Handle instance context changes from the InstanceContextService.
        
        This is called when:
        - User enters/leaves an instance
        - Instance is matched/unmatched against group instances
        - Periodic refresh updates the context
        
        Use this to show/hide features based on moderation context.
        """
        from services.instance_context import InstanceContextState
        
        state = context.state
        instance = context.current_instance
        group = context.matching_group
        
        # Determine if we have live data (in any instance)
        has_live_data = state != InstanceContextState.OFFLINE
        
        # Update GroupSelectionView live button visibility if on that screen
        if self._group_selection_view and self._current_route == "/groups":
            self._group_selection_view.set_has_live_data(has_live_data)
        
        if state == InstanceContextState.IN_GROUP_INSTANCE:
            logger.info(f"🎯 Moderation context: IN GROUP INSTANCE")
            logger.info(f"   Group: {group.get('name') if group else 'Unknown'}")
            logger.info(f"   World: {instance.world_id if instance else 'Unknown'}")
            logger.info(f"   Features available: {context.available_features}")
        elif state == InstanceContextState.IN_UNTRACKED:
            logger.info(f"📍 Moderation context: IN UNTRACKED INSTANCE")
            logger.info(f"   Location: {instance.location if instance else 'Unknown'}")
        else:
            logger.info(f"📴 Moderation context: OFFLINE")
    
    async def _check_existing_session(self):
        """Check if we have a valid saved session"""
        logger.info("Checking for existing session...")
        # Add slight delay to let splash render if it was just added
        import asyncio
        await asyncio.sleep(0.1)
        
        try:
            logger.info("Before api.check_session()...")
            result = await self._api.check_session()
            logger.info(f"After api.check_session(). Result: {result}")
            
            if result.get("valid"):
                user = result.get("user", {})
                self._username = user.get("displayName", "User")
                self._current_user = user
                logger.info(f"Session valid! Logged in as: {self._username}")
                # Use common login success handler to set up all services
                self._handle_login_success()
            else:
                logger.info("No valid session, trying stored credentials...")
                saved_user, saved_pass = self._load_credentials()
                if saved_user and saved_pass:
                    logger.info(f"Found stored credentials for {saved_user}, attempting login...")
                    result = await self._do_login_sequence(saved_user, saved_pass)
                    if result.get("success"):
                        return

                logger.info("No valid session or credentials")
                self._show_login()
        except Exception as e:
            logger.error(f"Session check error: {e}")
            import traceback
            traceback.print_exc()
            self._show_login()
            
    async def _check_for_updates(self):
        """Check for updates in background"""
        try:
            is_available, version, url, notes = await UpdateService.check_for_updates()
            if is_available:
                logger.info(f"Update available: {version}")
                self._update_available = True
                self._update_info = (version, url, notes)
                
                # Update current view's title bar if possible
                if self.page.views:
                    try:
                        current_view = self.page.views[-1]
                        # Structure: View -> [Column] -> [TitleBar, Container]
                        if current_view.controls and isinstance(current_view.controls[0], ft.Column):
                            root_col = current_view.controls[0]
                            if root_col.controls and isinstance(root_col.controls[0], TitleBar):
                                title_bar = root_col.controls[0]
                                title_bar.set_update_available(version, url, notes)
                    except Exception as e:
                        logger.debug(f"Could not update title bar live: {e}")
                
                # Title bar update already calls its own update internally
        except Exception as e:
            logger.error(f"Update check failed: {e}")
    
    def _create_view_with_titlebar(self, content: ft.Control, keep_view_ref=None) -> ft.View:
        """Create a view with custom title bar (desktop only, mobile uses system chrome)"""
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
        
        # On mobile, skip the title bar (use system chrome)
        if self._is_mobile:
            return ft.View(
                route,
                controls=[inner_content],
                padding=0,
                bgcolor=colors.bg_deepest,
            )
            
        # Desktop: Create TitleBar with update info if available
        title_bar = TitleBar(title="Group Guardian", icon_path=self._icon_path)
        if self._update_available and self._update_info:
            version, url, notes = self._update_info
            title_bar.set_update_available(version, url, notes)
            
        return ft.View(
            route,
            controls=[
                ft.Column(
                    controls=[
                        title_bar,
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
        try:
             self.page.update()
        except:
             pass
    
    def _show_login(self):
        """Show login view"""
        fd.log_view_rebuild("LoginView", "_show_login called")
        self.page.views.clear()
        
        # Check for stored credentials for autofill
        saved_user, saved_pass = self._load_credentials()
        fd.log_info(f"_show_login: Creating LoginView (has_saved_creds={bool(saved_user)})")
        
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
        fd.log_page_update("_show_login", "After appending view")
        self.page.update()
        
        # Manually set page reference since we extracted controls from the View
        self._login_view.page = self.page
        fd.log_info("_show_login: Calling did_mount()")
        self._login_view.did_mount()
        fd.log_info("_show_login: Complete")
    
    async def _do_login_sequence(self, username, password) -> dict:
        """Execute login logic, returns result dict"""
        result = await self._api.login(username, password)
        
        if result.get("success"):
            if result.get("requires_2fa"):
                # if we are doing silent login from startup, we must show UI now
                if not self._login_view:
                     self._show_login()
                
                tfa_type = result.get("2fa_type", "emailOtp")
                logger.info(f"2FA required: {tfa_type}")
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
        logger.debug(f"Login attempt: {username}, Remember: {remember_me}")
        
        if remember_me:
            self._save_credentials(username, password)
        else:
            self._clear_credentials()
        
        async def do_login():
            try:
                result = await self._do_login_sequence(username, password)
                
                if not result.get("success"):
                    error = result.get("error", "Login failed")
                    logger.warning(f"Login failed: {error}")
                    if self._login_view:
                        self._login_view.show_login_error(error)
            except Exception as e:
                logger.error(f"Unexpected login error: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                if self._login_view:
                    self._login_view.show_login_error(f"An unexpected error occurred: {str(e)}")

        self.page.run_task(do_login)

    def _save_credentials(self, username, password):
        """Save credentials to local file (simple encoding)"""
        try:
            data = f"{username}:{password}".encode("utf-8")
            b64_data = base64.b64encode(data).decode("utf-8")
            with open("storage.json", "w") as f:
                json.dump({"auth": b64_data}, f)
        except Exception as e:
            logger.warning(f"Failed to save credentials: {e}")

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
            logger.warning(f"Failed to load credentials: {e}")
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
        logger.debug(f"Verifying 2FA code: {code[:2]}***")
        
        async def do_verify():
            result = await self._api.verify_2fa(code)
            
            if result.get("success"):
                user = result.get("user", {})
                self._username = user.get("displayName", self._username)
                self._current_user = user
                logger.info(f"2FA verified! Logged in as: {self._username}")
                self._handle_login_success()
            else:
                error = result.get("error", "Invalid code")
                logger.warning(f"2FA verification failed: {error}")
                if self._login_view:
                    self._login_view.show_2fa_error(error)
        
        self.page.run_task(do_verify)
    
    def _handle_login_success(self):
        """Handle successful login - go to welcome screen"""
        self._is_authenticated = True
        
        # Start WebSocket pipeline for real-time updates
        self.page.run_task(self._connect_pipeline)
        
        # Connect alert service to authenticated API
        if self._alert_service:
            self._alert_service.set_api(self._api)
            logger.info("WatchlistAlertService connected to API")
        
        # Connect instance context service to authenticated API and start it
        if self._instance_context:
            self._instance_context.set_api(self._api)
            self.page.run_task(self._instance_context.start)
            logger.info("InstanceContextService connected to API and started")
        
        if self._current_user:
            self._show_welcome(self._current_user)
        else:
            # Fallback if no user object (shouldn't happen)
            self.page.go("/groups")
    
    async def _connect_pipeline(self):
        """Connect to VRChat's real-time WebSocket pipeline"""
        try:
            token = await self._api.get_pipeline_token()
            if token:
                # Initialize event handler for default behaviors
                get_event_handler()
                
                # Add custom listeners for our app
                self._pipeline.add_listener("notification", self._on_pipeline_notification)
                self._pipeline.add_listener("group-member-updated", self._on_group_member_updated)
                
                await self._pipeline.connect(token)
                self._pipeline_connected = True
                logger.info("WebSocket pipeline connected - real-time updates enabled")
            else:
                logger.warning("Could not get pipeline token - using polling mode")
        except Exception as e:
            logger.error(f"Failed to connect pipeline: {e}")
    
    def _on_pipeline_notification(self, data: dict):
        """Handle real-time notifications from pipeline"""
        noty_type = data.get("type", "")
        logger.info(f"Real-time notification: {noty_type}")
        
        # Refresh pending requests if it's a group invite request
        if noty_type in ["group.invite", "requestInvite", "groupQueueRequest"]:
            if self._current_group:
                self.page.run_task(self._refresh_pending_requests_silently)
    
    def _on_group_member_updated(self, data: dict):
        """Handle real-time group member updates from pipeline"""
        member = data.get("member", {})
        group_id = member.get("groupId", "")
        
        # If it's for our current group, refresh data
        if self._current_group and group_id == self._current_group.get("id"):
            logger.info(f"Group member updated in current group")
            # Could trigger specific view refreshes here
    
    async def _refresh_pending_requests_silently(self):
        """Silently refresh pending request count without UI disruption"""
        if self._current_group:
            try:
                requests = await self._api.get_group_join_requests(
                    self._current_group["id"],
                    n=1  # Just need count
                )
                # Update sidebar badge if needed
                if self._sidebar:
                    self._sidebar.update_pending_count(len(requests))
            except:
                pass  # Silent fail
    
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
        
        logger.info(f"Transitioning... Found {len(self._groups)} groups")
        
        # Auto-select if only 1 group
        if len(self._groups) == 1:
            logger.debug("Single group detected, skipping selection.")
            self._handle_group_select(self._groups[0])
        else:
            logger.debug("Transitioning to group selection...")
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
        logger.info("Starting Demo Mode...")
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
            logger.error(f"Demo failed: {ex}")
            import traceback
            logger.exception("Demo mode exception")
            
    
    def _show_group_selection(self):
        """Show group selection view"""
        self.page.views.clear()
        
        # Check if we have active live log data
        has_live_data = False
        if self._instance_context:
            has_live_data = self._instance_context.has_live_data()
        
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
            has_live_data=has_live_data,
            is_mobile=self._is_mobile,
        )
        view = self._create_view_with_titlebar(self._group_selection_view)
        self.page.views.append(view)
        self.page.update()
        
        # Manually set page reference since we extracted controls from the View
        self._group_selection_view.page = self.page
        
        if not self._groups:
             logger.debug("Groups empty or not loaded, triggering fetch...")
             self.page.run_task(self._load_groups, force_refresh=True)
    
    async def _handle_refresh_groups(self, e=None):
        """Force refresh groups"""
        await self._load_groups(force_refresh=True)
            
    async def _load_groups(self, force_refresh: bool = False):
        """Load user's groups with mod permissions"""
        if self._loading_groups_lock:
            logger.debug("Group load already in progress...")
            return

        self._loading_groups_lock = True
        try:
            if self._groups and not force_refresh:
                logger.debug("Using cached groups")
                if self._group_selection_view:
                     self._group_selection_view.set_groups(self._groups)
                return

            logger.info("Loading groups...")
            if self._group_selection_view:
                self._group_selection_view.set_loading(True)
            
            # Add visual delay for feedback on manual refresh
            if force_refresh:
                import asyncio
                await asyncio.sleep(0.8)
                
            groups = await self._api.get_my_groups(force_refresh=force_refresh)
            logger.info(f"Found {len(groups)} groups with mod permissions")
            
            # Cache group images locally (VRChat URLs require auth cookies)
            import asyncio
            for group in groups:
                # Download images with auth and replace URLs with local paths
                await self._api.cache_group_images(group)
            
            self._groups = groups
            
            # Update instance context service with the groups list
            if self._instance_context:
                self._instance_context.set_groups(groups)
                # Trigger a refresh of group instances to match against current location
                self.page.run_task(self._instance_context.refresh_group_instances)
            
            if self._group_selection_view:
                self._group_selection_view.set_groups(groups)
                self._group_selection_view.set_loading(False)
                
        except Exception as e:
            logger.error(f"Error loading groups: {e}")
            if self._group_selection_view:
                 self._group_selection_view.set_loading(False)
        finally:
            self._loading_groups_lock = False
    
    def _handle_group_select(self, group: dict):
        """Handle group selection"""
        self._current_group = group
        logger.info(f"Selected group: {group.get('name')} ({group.get('id')})")
        
        # Update window title
        self.page.title = f"Group Guardian - {group.get('name')}"
        
        # Navigate to dashboard for this group
        self.page.go("/dashboard")
    
    def _handle_logout(self):
        """Handle logout"""
        # Prevent multiple logout calls
        if getattr(self, '_logout_in_progress', False):
            return
        self._logout_in_progress = True
        
        async def do_logout():
            try:
                await self._api.logout()
                
                # Clear all entity caches to prevent stale data on re-login
                self._api.clear_all_caches()
                
                # Reset to real API client (exits Demo Mode)
                self._api = VRChatAPI()
                
                self._is_authenticated = False
                self._current_group = None
                self._groups = []
                self._username = ""
                self._current_user = {}  # Clear user object to ensure fresh state
                self._welcome_view = None # Clear stale view reference
                self._live_view = None # Clear stale live view reference
                
                # Disconnect alert service from old API
                if self._alert_service:
                    self._alert_service.set_api(None)
                
                # Stop and disconnect instance context service
                if self._instance_context:
                    await self._instance_context.stop()
                    self._instance_context.set_api(None)
                    self._instance_context.set_groups([])
                    
                logger.info("Logged out")
                self.page.go("/login")
            finally:
                self._logout_in_progress = False
        
        self.page.run_task(do_logout)
    
    def _on_window_resized(self, e):
        """Handle window resize for responsive layout"""
        if not self.page or not self._sidebar:
            return
        
        # Get current window width
        width = self.page.window.width or 1280
        
        # Collapse sidebar on narrow windows (< 1100px)
        # Expand on wider windows (> 1200px)
        # Update persistent state so it survives navigation
        if width < 1100:
            self._sidebar.set_collapsed(True)
            self._sidebar_collapsed = True
        elif width > 1200:
            self._sidebar.set_collapsed(False)
            self._sidebar_collapsed = False
    
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
            # Check if we have live data before allowing access to live view
            has_live_data = self._instance_context.has_live_data() if self._instance_context else False
            if not self._supports_live or not has_live_data:
                # No live data available, redirect to groups
                logger.info("Attempted to access /live without live log data - redirecting to /groups")
                self.page.go("/groups")
                return
            
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
        """Build main app view with sidebar (desktop) or bottom nav (mobile)"""
        
        # Content area
        content = self._get_content_for_route(route)
        
        # Check if running on mobile
        if self._is_mobile:
            return self._build_mobile_main_view(route, content)
        else:
            return self._build_desktop_main_view(route, content)
    
    def _build_mobile_main_view(self, route: str, content: ft.Control) -> ft.View:
        """Build mobile-optimized main view with bottom navigation"""
        from ui.components.bottom_nav import BottomNavBar
        
        # Mobile header - simplified
        mobile_header = ft.Container(
            content=ft.Row(
                controls=[
                    # Group icon or app icon
                    ft.Container(
                        content=ft.Image(
                            src=self._current_group.get("iconUrl", "") if self._current_group and self._current_group.get("iconUrl") else self._icon_path,
                            fit=ft.ImageFit.COVER,
                            width=32,
                            height=32,
                            border_radius=radius.sm,
                        ),
                        width=36,
                        height=36,
                        border_radius=radius.sm,
                        bgcolor=colors.bg_elevated,
                        alignment=ft.alignment.center,
                    ),
                    ft.Container(width=spacing.sm),
                    # Group/App name
                    ft.Text(
                        self._current_group.get("name", "Group Guardian") if self._current_group else "Group Guardian",
                        size=typography.size_lg,
                        weight=ft.FontWeight.W_600,
                        color=colors.text_primary,
                        expand=True,
                        no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    # Back button
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK_ROUNDED,
                        icon_color=colors.text_secondary,
                        icon_size=24,
                        tooltip="Back to Groups",
                        on_click=lambda e: self.page.go("/groups"),
                    ),
                ],
            ),
            padding=ft.padding.symmetric(horizontal=spacing.md, vertical=spacing.sm),
            bgcolor=colors.bg_base,
            border=ft.border.only(bottom=ft.BorderSide(1, colors.glass_border)),
        )
        
        # Bottom navigation
        bottom_nav = BottomNavBar(
            on_navigate=self._navigate,
            current_route=route,
            badge_counts={"/requests": self._pending_requests_count},
        )
        
        # Main layout: Header + Content + Bottom Nav
        full_layout = ft.Column(
            controls=[
                mobile_header,
                ft.Container(
                    content=SimpleGradientBackground(content=content),
                    expand=True,
                ),
                bottom_nav,
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
    
    def _build_desktop_main_view(self, route: str, content: ft.Control) -> ft.View:
        """Build desktop main view with sidebar navigation"""
        
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
            on_toggle=self._handle_sidebar_toggle,
            current_route=route,
            collapsed=self._sidebar_collapsed,
            user_name=self._username or "User",
            user_data=self._current_user,  # Pass full user data for avatar and status
            badge_counts={"/requests": self._pending_requests_count},
            nav_items=custom_nav
        )
        
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
    
    def _handle_theme_change(self, new_color: str):
        """Handle theme color change from settings - refresh sidebar immediately"""
        if self._sidebar:
            self._sidebar.refresh_theme()
            
    def _handle_sidebar_toggle(self, collapsed: bool):
        """Handle sidebar toggle from UI"""
        self._sidebar_collapsed = collapsed
    
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
                on_update_stats=self._handle_stats_update,
                is_mobile=self._is_mobile
            )
        
        elif route == "/instances":
            return InstancesView(
                group=self._current_group,
                api=self._api,
                on_navigate=self._navigate,
                is_mobile=self._is_mobile
            )
        
        elif route == "/requests":
            return RequestsView(
                group=self._current_group,
                api=self._api,
                on_navigate=self._navigate,
                on_update_stats=self._handle_stats_update,
                is_mobile=self._is_mobile
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
        
        elif route == "/watchlist":
            return WatchlistView(
                api=self._api,
                on_navigate=self._navigate
            )
        
        elif route == "/logs":
            return self._placeholder_view("Audit Logs", "View moderation activity history")
        
        elif route == "/settings":
            return SettingsView(on_navigate=self._navigate, api=self._api, on_theme_change=self._handle_theme_change)
        
        else:
            return DashboardView()

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
    try:
        UpdateService.handle_update_process()
    except Exception as e:
        logger.error(f"Update service init error: {e}")
    
    try:
        GroupGuardianApp(page)
    except Exception as e:
        import traceback
        logger.critical(f"Critical error during startup: {e}")
        logger.exception("Startup exception")
        page.clean()
        page.add(
            ft.Column([
                ft.Text("Critical Error during startup:", size=20, weight="bold", color="red"),
                ft.Text(str(e), color="yellow"),
                ft.Text(traceback.format_exc(), size=10, font_family="monospace"),
            ], scroll="auto")
        )
        page.update()


if __name__ == "__main__" or __name__ == "main":
    logger.info(f"Starting app with __name__='{__name__}'")
    ft.app(target=main)
