"""
Login View
==========
Beautiful animated login screen with glassmorphism
Animated transition from login → 2FA
"""

import flet as ft
import asyncio
from ..theme import colors, radius, shadows, spacing, typography
from ..components.glass_card import GlassCard
from ..components.neon_button import NeonButton
from ..components.animated_background import SimpleGradientBackground
from services.debug_logger import get_logger
from services import focus_debugger as fd

logger = get_logger("login_view")


class LoginView(ft.View):
    """
    Stunning login screen with:
    - Animated space background
    - Floating glassmorphism login card
    - Animated transition to 2FA
    - Neon glow effects
    """
    
    def __init__(
        self,
        on_login = None,
        on_login_success = None,
        on_2fa_verify = None,
        on_demo_login = None,
        initial_username: str = "",
        initial_password: str = "",
        initial_remember: bool = False,
        **kwargs,
    ):
        self._initial_username = initial_username
        self._initial_password = initial_password
        self._initial_remember = initial_remember
        self._on_login = on_login
        self._on_login_success = on_login_success
        self._on_2fa_verify = on_2fa_verify
        self.on_demo_login = on_demo_login
        self._is_loading = False
        self._is_transitioning = False
        self._2fa_type = "emailOtp"
        
        # UI components
        self._username_field = None
        self._password_field = None
        self.controls = []
        self._login_button = None
        self._error_text = None
        self._twofa_fields = []
        self._twofa_instruction = None
        
        # Card containers for animation
        self._login_card = None
        self._twofa_card = None
        
        # Remember me checkbox
        self._remember_checkbox = None
        
        super().__init__(
            route="/login",
            padding=0,
            bgcolor=colors.bg_deepest,
            **kwargs,
        )
        
        self.controls = [self._build_view()]
    
    def _build_view(self) -> ft.Control:
        """Build the complete login view with both cards"""
        
        # Build login card
        self._login_card = self._build_login_card()
        
        # Build 2FA card (hidden initially)
        self._twofa_card = self._build_2fa_card()
        
        # Main container that will hold either login or 2FA card
        self._card_container = ft.Container(
            content=self._login_card,
            alignment=ft.alignment.center,
            animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
        )
        
        # Footer
        footer = ft.Text(
            "✦ Secure VRChat Authentication",
            size=typography.size_sm,
            color=colors.text_tertiary,
        )
        
        # Center content
        centered_content = ft.Column(
            controls=[
                ft.Container(expand=True),
                self._card_container,
                ft.Container(height=spacing.lg),
                footer,
                ft.Container(height=spacing.xl),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
        
        # Use SimpleGradientBackground to match the rest of the UI
        return SimpleGradientBackground(
            content=ft.Container(
                content=centered_content,
                expand=True,
            ),
        )
    
    def _build_login_card(self) -> ft.Container:
        """Build the login form card"""
        fd.log_info("LoginView: Building login card")
        
        # Username field - REMOVED key and focus handlers to fix focus bug
        self._username_field = ft.TextField(
            label="Username or Email",
            value=self._initial_username,
            prefix_icon=ft.Icons.PERSON_ROUNDED,
            border_radius=radius.md,
            bgcolor=colors.bg_elevated,
            border_color=colors.accent_secondary,
            focused_border_color=colors.accent_primary,
            label_style=ft.TextStyle(color=colors.text_secondary),
            text_style=ft.TextStyle(color=colors.text_primary),
            cursor_color=colors.accent_secondary,
            on_submit=lambda e: self._password_field.focus(),
            on_change=self._on_username_change,
            height=48,
            # NOTE: key removed - Flet bug causes focus loss with key property
        )
        
        # Password field - REMOVED key and focus handlers to fix focus bug
        self._password_field = ft.TextField(
            label="Password",
            value=self._initial_password,
            prefix_icon=ft.Icons.LOCK_ROUNDED,
            password=True,
            can_reveal_password=True,
            border_radius=radius.md,
            bgcolor=colors.bg_elevated,
            border_color=colors.accent_secondary,
            focused_border_color=colors.accent_primary,
            label_style=ft.TextStyle(color=colors.text_secondary),
            text_style=ft.TextStyle(color=colors.text_primary),
            cursor_color=colors.accent_secondary,
            on_submit=lambda e: self._handle_login(None),
            on_change=self._on_password_change,
            height=48,
            # NOTE: key removed - Flet bug causes focus loss with key property
        )
        
        # Error text
        self._error_text = ft.Text(
            "",
            size=typography.size_sm,
            color=colors.danger,
            visible=False,
            text_align=ft.TextAlign.CENTER,
        )
        
        # Login button
        self._login_button = NeonButton(
            text="Sign In",
            icon=ft.Icons.LOGIN_ROUNDED,
            variant=NeonButton.VARIANT_PRIMARY,
            on_click=self._handle_login,
            expand=True,
            height=48,
            key="login_submit"
        )
        
        # Remember me
        self._remember_checkbox = ft.Checkbox(
            label="Save credentials",
            value=self._initial_remember,
            fill_color={
                ft.ControlState.SELECTED: colors.accent_primary,
                ft.ControlState.DEFAULT: colors.bg_elevated,
            },
            check_color=colors.text_primary,
            label_style=ft.TextStyle(
                color=colors.text_secondary,
                size=typography.size_sm,
            ),
        )
        
        # Logo section
        logo = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.SHIELD_ROUNDED,
                        size=48,
                        color=colors.accent_primary,
                    ),
                    width=80,
                    height=80,
                    border_radius=radius.xl,
                    bgcolor="rgba(139, 92, 246, 0.15)",
                    alignment=ft.alignment.center,
                    shadow=shadows.glow_purple(blur=30, opacity=0.3),
                ),
                ft.Container(height=spacing.md),
                ft.Text(
                    "Group Guardian",
                    size=typography.size_2xl,
                    weight=ft.FontWeight.W_700,
                    color=colors.text_primary,
                ),
                ft.Text(
                    "VRChat Group Moderation",
                    size=typography.size_base,
                    color=colors.text_secondary,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=spacing.xs,
        )
        
        # Form layout
        form = ft.Column(
            controls=[
                self._username_field,
                ft.Container(height=spacing.sm), # Spacing
                self._password_field,
                ft.Container(height=spacing.sm), # Spacing
                self._error_text,
                ft.Container(height=spacing.sm),
                self._login_button,
                ft.Container(height=spacing.sm),
                ft.Row(
                    controls=[self._remember_checkbox],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(height=spacing.sm),
                ft.TextButton(
                    "Try Demo Mode",
                    icon=ft.Icons.PREVIEW_ROUNDED,
                    style=ft.ButtonStyle(color=colors.accent_primary),
                    on_click=self.on_demo_login,
                    disabled=self.on_demo_login is None,
                    key="login_demo"
                ),
            ],
            spacing=0, # Using containers for explicit spacing control
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        
        # Card content - use Container with max_width for responsive sizing
        card_content = ft.Container(
            content=ft.Column(
                controls=[logo, ft.Container(height=spacing.xl), form],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=340,  # Desktop width
            padding=ft.padding.symmetric(horizontal=spacing.md),
        )
        
        return ft.Container(
            content=GlassCard(
                content=card_content,
                padding=spacing.xl,
                border_radius_value=radius.xl,
                hover_enabled=False,
                height=560, # Explicit height to prevent clipping
            ),
            opacity=1,
            scale=1,
            offset=ft.Offset(0, 0),
            animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
            animate_scale=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
            animate_offset=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
        )
    
    def _build_2fa_card(self) -> ft.Container:
        """Build the 2FA verification card"""
        
        # Create 6 digit input boxes
        # Use slightly smaller size for better mobile fit (6 x 45px + spacing = ~300px)
        self._twofa_fields = []
        for i in range(6):
            field = ft.TextField(
                width=45,  # Reduced from 50 for mobile fit
                height=55,  # Reduced from 60
                text_align=ft.TextAlign.CENTER,
                max_length=1,
                border_radius=radius.md,
                bgcolor=colors.bg_elevated,
                border_color=colors.glass_border,
                focused_border_color=colors.accent_primary,
                text_style=ft.TextStyle(
                    color=colors.text_primary,
                    size=24,  # Reduced from 28
                    weight=ft.FontWeight.W_700,
                ),
                cursor_color=colors.accent_primary,
                keyboard_type=ft.KeyboardType.NUMBER,  # Mobile numeric keyboard
                on_change=lambda e, idx=i: self._on_2fa_digit_change(e, idx),
            )
            self._twofa_fields.append(field)
        
        digit_row = ft.Row(
            controls=self._twofa_fields,
            spacing=spacing.sm,
            alignment=ft.MainAxisAlignment.CENTER,
        )
        
        # 2FA icon with glow
        tfa_icon = ft.Container(
            content=ft.Icon(
                ft.Icons.SECURITY_ROUNDED,
                size=48,
                color=colors.accent_secondary,
            ),
            width=90,
            height=90,
            border_radius=radius.xl,
            bgcolor="rgba(6, 182, 212, 0.15)",
            alignment=ft.alignment.center,
            shadow=shadows.glow_cyan(blur=30, opacity=0.4),
        )
        
        # Instruction text (will be updated based on 2FA type)
        self._twofa_instruction = ft.Text(
            "Check your email for a verification code",
            size=typography.size_base,
            color=colors.text_secondary,
            text_align=ft.TextAlign.CENTER,
        )
        
        # 2FA error text
        self._twofa_error = ft.Text(
            "",
            size=typography.size_sm,
            color=colors.danger,
            visible=False,
            text_align=ft.TextAlign.CENTER,
        )
        
        # Back button
        back_btn = ft.TextButton(
            "← Back to Login",
            style=ft.ButtonStyle(color=colors.text_secondary),
            on_click=self._back_to_login,
        )
        
        # Card content - responsive width
        card_content = ft.Container(
            content=ft.Column(
                controls=[
                    tfa_icon,
                    ft.Container(height=spacing.lg),
                    ft.Text(
                        "Two-Factor Authentication",
                        size=typography.size_xl,
                        weight=ft.FontWeight.W_700,
                        color=colors.text_primary,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=spacing.xs),
                    self._twofa_instruction,
                    ft.Container(height=spacing.xl),
                    digit_row,
                    ft.Container(height=spacing.sm),
                    self._twofa_error,
                    ft.Container(height=spacing.lg),
                    ft.Text(
                        "Enter the 6-digit code sent to you",
                        size=typography.size_sm,
                        color=colors.text_tertiary,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=spacing.md),
                    back_btn,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=360,  # Slightly reduced for mobile fit
            padding=ft.padding.symmetric(horizontal=spacing.sm),
        )
        
        return ft.Container(
            content=GlassCard(
                content=card_content,
                padding=spacing.xl,
                border_radius_value=radius.xl,
                hover_enabled=False,
                height=450,
            ),
            opacity=1,
            scale=1,
            offset=ft.Offset(0, 0),
            animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
            animate_scale=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
            animate_offset=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
        )
    
    def _on_2fa_digit_change(self, e: ft.ControlEvent, idx: int):
        """Handle 2FA digit input with auto-advance"""
        value = e.control.value
        
        if value and len(value) >= 1:
            # Move to next field
            if idx < 5:
                self._twofa_fields[idx + 1].focus()
            else:
                # All 6 digits entered
                code = "".join(f.value or "" for f in self._twofa_fields)
                if len(code) == 6:
                    self._handle_2fa_verify(code)
        
        if self.page:
            self.page.update()
    
    def _handle_login(self, e):
        """Handle login button click"""
        username = self._username_field.value
        password = self._password_field.value
        
        if not username or not password:
            self._show_error("Please enter username and password")
            return
        
        self._set_loading(True)
        
        if self._on_login:
            self._on_login(username, password, self._remember_checkbox.value)
    
    def _handle_2fa_verify(self, code: str):
        """Handle 2FA code submission"""
        self._twofa_error.visible = False
        
        if self._on_2fa_verify:
            # Disable fields during verification
            for field in self._twofa_fields:
                field.disabled = True
            if self.page:
                self.page.update()
            
            self._on_2fa_verify(code)
        elif self._on_login_success:
            self._on_login_success()
    

    
    def _back_to_login(self, e):
        """Go back to login form using asyncio for transition"""
        if self._is_transitioning:
            return
        self._is_transitioning = True
        
        # Swap content
        self._card_container.opacity = 0
        if self.page:
            self.page.update()
        
        async def swap():
            await asyncio.sleep(0.3)
            self._card_container.content = self._login_card
            self._card_container.opacity = 1
            
            # Clear 2FA fields
            for field in self._twofa_fields:
                field.value = ""
                field.disabled = False
            self._twofa_error.visible = False
            
            if self.page:
                self.page.update()
            
            self._is_transitioning = False
                
        if self.page:
            self.page.run_task(swap)
        else:
            self._is_transitioning = False

    def _set_loading(self, loading: bool):
        """Set loading state"""
        self._is_loading = loading
        if hasattr(self._login_button, 'set_loading'):
            self._login_button.set_loading(loading)
        self._username_field.disabled = loading
        self._password_field.disabled = loading
        if self.page:
            self.page.update()
    
    def did_mount(self):
        """Called when view is added to page"""
        # Set initial focus safely
        try:
            if not self._initial_username:
                self._username_field.focus()
            else:
                self._password_field.focus()
        except:
            pass

    def _on_username_change(self, e):
        """Handle username field change with focus debugging"""
        fd.log_text_change("username", "<prev>", e.control.value)
        fd.log_info(f"  _on_username_change: value length = {len(e.control.value)}")
        self._clear_error_safe()
    
    def _on_password_change(self, e):
        """Handle password field change with focus debugging"""
        fd.log_text_change("password", "<prev>", f"[{len(e.control.value)} chars]")
        fd.log_info(f"  _on_password_change: value length = {len(e.control.value)}")
        self._clear_error_safe()
    
    def _clear_error_safe(self):
        """
        Clear error state WITHOUT calling any update().
        This is the safe version that won't cause focus loss.
        """
        if self._error_text.visible:
            fd.log_info("  _clear_error_safe: Error was visible, hiding it")
            self._error_text.visible = False
            self._username_field.border_color = colors.accent_secondary
            self._password_field.border_color = colors.accent_secondary
            # DO NOT CALL UPDATE - let Flet handle it naturally
            # The old code called update() here which may cause focus issues
        else:
            fd.log_info("  _clear_error_safe: Error already hidden, no action")

    def _clear_error(self):
        """Clear error state - INSTRUMENTED VERSION"""
        fd.log_warning("_clear_error() CALLED - checking if this causes focus loss")
        if self._error_text.visible:
            fd.log_info("  Error is visible, clearing...")
            self._error_text.visible = False
            self._username_field.border_color = colors.accent_secondary
            self._password_field.border_color = colors.accent_secondary
            
            # DANGEROUS: These update() calls may cause focus loss
            fd.log_warning("  About to call _error_text.update()")
            self._error_text.update()
            fd.log_warning("  About to call _username_field.update()")
            self._username_field.update()
            fd.log_warning("  About to call _password_field.update()")
            self._password_field.update()
            fd.log_info("  All updates complete")
        else:
            fd.log_info("  Error already hidden, skipping")

    def _show_error(self, message: str):
        """Show error on login form"""
        self._error_text.value = message
        self._error_text.visible = True
        
        if not self._username_field.value:
            self._username_field.border_color = colors.danger
        if not self._password_field.value:
            self._password_field.border_color = colors.danger
        
        if self.page:
            self.page.update()
    
    # ==================== PUBLIC METHODS ====================
    
    def show_login_error(self, message: str):
        """Show error message on login form"""
        self._set_loading(False)
        self._show_error(message)
    
    def show_2fa_required(self, tfa_type: str = "emailOtp"):
        """
        Animate from login form to 2FA form.
        This creates a beautiful transition!
        """
        if self._is_transitioning:
            return
        self._is_transitioning = True
            
        self._2fa_type = tfa_type
        # No need to import logger again, usage of global logger is fine or re-fetch if needed
        logger.debug(f"Transitioning to 2FA screen (type: {tfa_type})")
        
        # Update instruction based on 2FA type
        if tfa_type == "emailOtp":
            self._twofa_instruction.value = "Check your email for a verification code"
        elif tfa_type == "totp":
            self._twofa_instruction.value = "Enter the code from your authenticator app"
        else:
            self._twofa_instruction.value = "Enter your verification code"
        
        self._set_loading(False)
        
        # Swap content with fade
        self._card_container.opacity = 0 # Fade out login
        if self.page:
            self.page.update()
        
        async def swap_to_2fa():
            await asyncio.sleep(0.3)
            self._card_container.content = self._twofa_card
            self._card_container.opacity = 1 # Fade in 2FA
            if self.page:
                self.page.update()
            
            # Focus first 2FA field after a short delay
            await asyncio.sleep(0.5)
            if self._twofa_fields:
                self._twofa_fields[0].focus()
            if self.page:
                self.page.update()
                
            self._is_transitioning = False
        
        if self.page:
            self.page.run_task(swap_to_2fa)
        else:
            self._is_transitioning = False
    
    def show_2fa_error(self, message: str):
        """Show error on 2FA form"""
        # Re-enable fields
        for field in self._twofa_fields:
            field.disabled = False
            field.value = ""
        
        self._twofa_error.value = message
        self._twofa_error.visible = True
        
        # Focus first field
        if self._twofa_fields:
            self._twofa_fields[0].focus()
        
        if self.page:
            self.page.update()
