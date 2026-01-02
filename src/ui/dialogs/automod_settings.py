import flet as ft
import logging
from services.database import get_database
from services.watchlist_service import get_watchlist_service
from ui.components.glass_card import GlassCard
from ui.components.neon_button import NeonButton
from ui.theme import colors, spacing, typography
from ui.dialogs.user_details import show_user_details_dialog

logger = logging.getLogger(__name__)

# Trust rank options for dropdown
TRUST_RANK_OPTIONS = [
    (0, "No requirement"),
    (1, "New User (minimum)"),
    (2, "User (minimum)"),
    (3, "Known User (minimum)"),
    (4, "Trusted User (minimum)"),
]

class AutoModSettingsDialog(ft.AlertDialog):
    def __init__(self, page: ft.Page, group_id: str, group_name: str, api=None, on_update=None):
        self.page_ref = page
        self.group_id = group_id
        self.group_name = group_name
        self.api = api  # VRChat API for fetching user profiles
        self.on_update = on_update
        self.db = get_database()
        
        # Load current settings
        self.settings = self.db.get_group_settings(group_id) or {}
        logger.info(f"Loaded automod settings for {group_id}: {self.settings}")
        
        super().__init__(
            modal=True,
            title=ft.Text("Auto-Moderation Settings", size=22, weight=ft.FontWeight.BOLD),
            content_padding=15,
            actions_padding=15,
        )
        self._build_content()
        
    def _build_content(self):
        # Controls - ensure boolean conversion from SQLite int (0/1)
        enabled_val = bool(self.settings.get("automod_enabled", 0))
        age_val = bool(self.settings.get("automod_age_verified_only", 0))
        trust_val = int(self.settings.get("automod_min_trust_rank", 0) or 0)
        days_val = int(self.settings.get("automod_min_account_age_days", 0) or 0)
        
        logger.info(f"Switch values: enabled={enabled_val}, age={age_val}, trust={trust_val}, days={days_val}")
        
        # Main enable switch
        self.sw_enabled = ft.Switch(
            label="Enable Auto-Moderation", 
            value=enabled_val,
            active_color=colors.accent_primary
        )
        
        # === DENY RULES SECTION ===
        
        # Age verification switch
        self.sw_age = ft.Switch(
            label="Require Age Verified (18+)", 
            value=age_val,
            active_color=colors.danger
        )
        
        # Trust rank dropdown
        self.dd_trust = ft.Dropdown(
            label="Minimum Trust Rank",
            value=str(trust_val),
            options=[ft.dropdown.Option(str(v), text=t) for v, t in TRUST_RANK_OPTIONS],
            border_color=colors.glass_border,
            focused_border_color=colors.accent_primary,
            width=250,
        )
        
        # Account age input
        self.tf_account_age = ft.TextField(
            label="Minimum Account Age (days)",
            hint_text="0 = no requirement",
            value=str(days_val) if days_val > 0 else "",
            border_color=colors.glass_border,
            focused_border_color=colors.accent_primary,
            keyboard_type=ft.KeyboardType.NUMBER,
            width=200,
        )
        
        # Blocked keywords
        ex_keywords = ",".join(self.settings.get("automod_exclude_keywords", []))
        self.tf_exclude = ft.TextField(
            label="Block Keywords (comma separated)",
            hint_text="e.g. minor, bot, troll",
            value=ex_keywords,
            border_color=colors.glass_border,
            focused_border_color=colors.danger,
            multiline=True,
            min_lines=2
        )
        
        # === ACCEPT RULES SECTION ===
        
        req_keywords = ",".join(self.settings.get("automod_require_keywords", []))
        self.tf_require = ft.TextField(
            label="Auto-Accept Keywords (comma separated)",
            hint_text="e.g. 18+, furality, password123",
            value=req_keywords,
            border_color=colors.glass_border,
            focused_border_color=colors.success,
            multiline=True,
            min_lines=2
        )
        
        # Logs Section
        logs = self.db.get_automod_logs(self.group_id, limit=50)
        watchlist_svc = get_watchlist_service()
        log_rows = []
        if logs:
            for log in logs:
                action_color = colors.success if log['action'] == 'accept' else colors.danger
                user_id = log.get('user_id', '')
                username = log.get('username', 'Unknown')
                was_accepted = log['action'] == 'accept'
                
                # Check watchlist using centralized service - ensures user is recorded
                is_watchlisted = False
                if user_id:
                    status = watchlist_svc.check_and_record_user(user_id, username)
                    is_watchlisted = status.get("is_watchlisted", False)
                
                # Action button based on the automod action
                if was_accepted:
                    # User was auto-accepted, show Kick button
                    action_btn = ft.IconButton(
                        icon=ft.Icons.PERSON_REMOVE_ROUNDED,
                        icon_size=16,
                        icon_color=colors.danger,
                        tooltip="Kick from group",
                        on_click=lambda e, uid=user_id, uname=username: self._kick_user(uid, uname),
                    )
                else:
                    # User was auto-rejected, show Invite button
                    action_btn = ft.IconButton(
                        icon=ft.Icons.PERSON_ADD_ROUNDED,
                        icon_size=16,
                        icon_color=colors.success,
                        tooltip="Send group invite",
                        on_click=lambda e, uid=user_id, uname=username: self._invite_user(uid, uname),
                    )
                
                # Create clickable log entry with action button
                log_rows.append(
                    ft.Container(
                        content=ft.Row([
                            # Main content (clickable for profile)
                            ft.Container(
                                content=ft.Column([
                                    ft.Row([
                                        ft.Row([
                                            # Watchlist indicator
                                            ft.Icon(ft.Icons.WARNING_ROUNDED, size=12, color=colors.warning, tooltip="On watchlist") if is_watchlisted else ft.Container(width=0),
                                            ft.Icon(ft.Icons.PERSON_ROUNDED, size=14, color=colors.warning if is_watchlisted else colors.accent_primary),
                                            ft.Text(username, weight=ft.FontWeight.BOLD, size=12, color=colors.warning if is_watchlisted else colors.accent_primary),
                                        ], spacing=4),
                                        ft.Container(
                                            content=ft.Text(log['action'].upper(), size=9, color=action_color),
                                            border=ft.border.all(1, action_color),
                                            border_radius=4,
                                            padding=ft.padding.symmetric(horizontal=4, vertical=1)
                                        )
                                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                    ft.Text(log['reason'], size=10, color=ft.Colors.with_opacity(0.7, "white"), max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(log['timestamp'][:16].replace("T", " "), size=9, color=ft.Colors.with_opacity(0.5, "white"))
                                ], spacing=1),
                                expand=True,
                                on_click=lambda e, uid=user_id, uname=username: self._open_user_profile(uid, uname),
                                on_hover=lambda e: self._on_log_hover(e),
                                tooltip=f"Click to view {username}'s profile",
                                animate_scale=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
                            ),
                            # Action button
                            action_btn,
                        ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=ft.padding.only(left=8, right=4, top=6, bottom=6),
                        border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.with_opacity(0.1, "white"))),
                    )
                )
        else:
            log_rows.append(ft.Text("No recent auto-mod actions.", italic=True, size=12, color=ft.Colors.with_opacity(0.5, "white")))
            
        logs_panel = GlassCard(
            content=ft.Column([
                ft.Text("Recent Activity", size=14, weight=ft.FontWeight.BOLD),
                ft.Text("Click user to view profile • Use buttons to undo actions", size=9, color=ft.Colors.with_opacity(0.5, "white")),
                ft.Column(log_rows, scroll=ft.ScrollMode.AUTO, height=140)
            ], spacing=spacing.xs),
            padding=8
        )

        # Build the content layout
        self.content = ft.Container(
            width=520,
            content=ft.Column([
                ft.Text(f"Configure auto-moderation for {self.group_name}", 
                       color=ft.Colors.with_opacity(0.7, "white"), size=typography.size_sm),
                ft.Divider(color=ft.Colors.TRANSPARENT, height=8),
                
                # Main switch
                self.sw_enabled,
                ft.Divider(color=ft.Colors.TRANSPARENT, height=8),
                
                # DENY RULES
                ft.Text("🚫 Auto-Reject Rules", weight=ft.FontWeight.BOLD, color=colors.danger),
                ft.Text("Users matching ANY of these will be rejected:", size=11, 
                       color=ft.Colors.with_opacity(0.6, "white")),
                ft.Container(height=4),
                self.sw_age,
                ft.Row([self.dd_trust, self.tf_account_age], spacing=spacing.md),
                self.tf_exclude,
                ft.Text("Block if bio contains any of these keywords (case insensitive)", 
                       size=10, color=ft.Colors.with_opacity(0.5, "white")),
                
                ft.Divider(color=ft.Colors.TRANSPARENT, height=12),
                
                # ACCEPT RULES  
                ft.Text("✅ Auto-Accept Rules", weight=ft.FontWeight.BOLD, color=colors.success),
                ft.Text("Users matching these (and NOT rejected) will be accepted:", size=11,
                       color=ft.Colors.with_opacity(0.6, "white")),
                ft.Container(height=4),
                self.tf_require,
                ft.Text("Accept if bio contains any of these keywords (case insensitive)", 
                       size=10, color=ft.Colors.with_opacity(0.5, "white")),
                
                ft.Divider(color=ft.Colors.TRANSPARENT, height=12),
                logs_panel
            ], scroll=ft.ScrollMode.AUTO, height=480, spacing=spacing.xs)
        )
        
        self.actions = [
            ft.TextButton("Cancel", on_click=self._close),
            NeonButton("Save Settings", on_click=self._save, width=150)
        ]
        
    def _close(self, e):
        self.page_ref.close(self)
        
    def _save(self, e):
        # Parse values
        req = [x.strip() for x in self.tf_require.value.split(",") if x.strip()]
        ex = [x.strip() for x in self.tf_exclude.value.split(",") if x.strip()]
        
        # Parse trust rank
        try:
            trust_rank = int(self.dd_trust.value or "0")
        except:
            trust_rank = 0
            
        # Parse account age
        try:
            account_age = int(self.tf_account_age.value or "0")
        except:
            account_age = 0
        
        # Log what we're saving
        logger.info(f"Saving automod settings: enabled={self.sw_enabled.value}, age={self.sw_age.value}, " +
                   f"trust={trust_rank}, days={account_age}, req={req}, ex={ex}")
        
        self.db.set_group_automod_settings(
            self.group_id,
            self.group_name,
            self.sw_enabled.value,
            self.sw_age.value,
            req,
            ex,
            trust_rank,
            account_age
        )
        
        # Show confirmation
        self.page_ref.open(ft.SnackBar(
            content=ft.Text("Auto-moderation settings saved!"), 
            bgcolor=colors.success
        ))
        
        if self.on_update:
            self.on_update()
            
        self._close(e)
    
    def _open_user_profile(self, user_id: str, username: str):
        """Open user profile dialog for a user from the logs"""
        if not user_id:
            self.page_ref.open(ft.SnackBar(
                content=ft.Text("User ID not available"),
                bgcolor=colors.warning
            ))
            return
        
        # Construct minimal user data for the dialog
        user_data = {
            "id": user_id,
            "displayName": username,
        }
        
        # Show user details dialog
        show_user_details_dialog(
            self.page_ref,
            user_data,
            self.api,
            self.db,
            group_id=self.group_id
        )
    
    def _on_log_hover(self, e):
        """Handle hover on log entry - scale effect"""
        if e.data == "true":
            e.control.scale = 1.02
        else:
            e.control.scale = 1.0
        e.control.update()
    
    def _invite_user(self, user_id: str, username: str):
        """Send a group invite to a user who was auto-rejected"""
        if not self.api:
            self.page_ref.open(ft.SnackBar(
                content=ft.Text("API not available"),
                bgcolor=colors.danger
            ))
            return
        
        if not user_id:
            self.page_ref.open(ft.SnackBar(
                content=ft.Text("User ID not available"),
                bgcolor=colors.warning
            ))
            return
        
        async def do_invite():
            try:
                # Send group invite
                success = await self.api.invite_user_to_group(self.group_id, user_id)
                
                if success:
                    self.page_ref.open(ft.SnackBar(
                        content=ft.Text(f"✅ Invite sent to {username}"),
                        bgcolor=colors.success
                    ))
                else:
                    self.page_ref.open(ft.SnackBar(
                        content=ft.Text(f"Failed to invite {username}"),
                        bgcolor=colors.danger
                    ))
            except Exception as e:
                logger.error(f"Error inviting user: {e}")
                self.page_ref.open(ft.SnackBar(
                    content=ft.Text(f"Error: {e}"),
                    bgcolor=colors.danger
                ))
        
        self.page_ref.run_task(do_invite)
    
    def _kick_user(self, user_id: str, username: str):
        """Kick a user from the group who was auto-accepted"""
        if not self.api:
            self.page_ref.open(ft.SnackBar(
                content=ft.Text("API not available"),
                bgcolor=colors.danger
            ))
            return
        
        if not user_id:
            self.page_ref.open(ft.SnackBar(
                content=ft.Text("User ID not available"),
                bgcolor=colors.warning
            ))
            return
        
        async def do_kick():
            try:
                # Kick user from group
                success = await self.api.kick_user(self.group_id, user_id)
                
                if success:
                    self.page_ref.open(ft.SnackBar(
                        content=ft.Text(f"✅ Kicked {username} from group"),
                        bgcolor=colors.success
                    ))
                else:
                    self.page_ref.open(ft.SnackBar(
                        content=ft.Text(f"Failed to kick {username}"),
                        bgcolor=colors.danger
                    ))
            except Exception as e:
                logger.error(f"Error kicking user: {e}")
                self.page_ref.open(ft.SnackBar(
                    content=ft.Text(f"Error: {e}"),
                    bgcolor=colors.danger
                ))
        
        self.page_ref.run_task(do_kick)

def show_automod_settings(page: ft.Page, group_id: str, group_name: str, api=None, on_update=None):
    dialog = AutoModSettingsDialog(page, group_id, group_name, api=api, on_update=on_update)
    page.open(dialog)  # Use modern Flet API
