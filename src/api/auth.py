"""
Authentication Mixin
=====================
Handles login, 2FA, session management, and logout.
"""

from typing import Dict, Any, Optional
from services.debug_logger import get_logger

logger = get_logger("api.auth")


class AuthMixin:
    """
    Mixin providing authentication functionality:
    - Login with username/password
    - 2FA verification (email OTP and TOTP)
    - Session checking
    - Logout
    - Pipeline token retrieval
    """
    
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Attempt to login with username and password.
        
        Returns:
            dict with keys:
            - success: bool
            - requires_2fa: bool
            - 2fa_type: "emailOtp" | "totp" | None
            - user: dict (if no 2FA required)
            - error: str (if failed)
        """
        import base64
        
        # Create Basic Auth header
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        try:
            response = await self._request(
                "GET",
                "/auth/user",
                headers={"Authorization": f"Basic {encoded}"},
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if 2FA is required
                if "requiresTwoFactorAuth" in data and data["requiresTwoFactorAuth"]:
                    tfa_types = data.get("requiresTwoFactorAuth", [])
                    self._requires_2fa = True
                    
                    # Prefer emailOtp if available
                    if "emailOtp" in tfa_types:
                        self._2fa_type = "emailOtp"
                    elif "totp" in tfa_types:
                        self._2fa_type = "totp"
                    else:
                        self._2fa_type = tfa_types[0] if tfa_types else "totp"
                    
                    logger.info(f"2FA required: {self._2fa_type}")
                    
                    return {
                        "success": True,
                        "requires_2fa": True,
                        "2fa_type": self._2fa_type,
                    }
                else:
                    # Login successful, no 2FA
                    self._current_user = data
                    self._requires_2fa = False
                    await self._save_cookies()
                    
                    logger.info(f"Logged in as: {data.get('displayName')}")
                    
                    return {
                        "success": True,
                        "requires_2fa": False,
                        "user": data,
                    }
            
            elif response.status_code == 401:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error", {}).get("message", "Invalid credentials")
                logger.warning(f"Login failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                }
            
            else:
                logger.error(f"Login error: {response.status_code}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                }
                
        except Exception as e:
            logger.error(f"Login exception: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    async def verify_2fa(self, code: str) -> Dict[str, Any]:
        """
        Verify 2FA code (email OTP or TOTP).
        
        Args:
            code: The 6-digit code
            
        Returns:
            dict with keys:
            - success: bool
            - user: dict (if successful)
            - error: str (if failed)
        """
        if not self._2fa_type:
            return {"success": False, "error": "No 2FA type set"}
        
        # Determine endpoint based on 2FA type
        if self._2fa_type == "emailOtp":
            endpoint = "/auth/twofactorauth/emailotp/verify"
        elif self._2fa_type == "totp":
            endpoint = "/auth/twofactorauth/totp/verify"
        else:
            endpoint = f"/auth/twofactorauth/{self._2fa_type}/verify"
        
        try:
            response = await self._request(
                "POST",
                endpoint,
                json={"code": code},
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("verified", False):
                    # 2FA successful, now get user info
                    await self._save_cookies()
                    
                    # Fetch current user
                    user_response = await self._request("GET", "/auth/user")
                    if user_response.status_code == 200:
                        self._current_user = user_response.json()
                        logger.info(f"2FA verified. Logged in as: {self._current_user.get('displayName')}")
                        
                        return {
                            "success": True,
                            "user": self._current_user,
                        }
                    else:
                        return {
                            "success": True,
                            "user": data,
                        }
                else:
                    return {
                        "success": False,
                        "error": "Code not verified",
                    }
            
            elif response.status_code == 400:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error", {}).get("message", "Invalid code")
                return {
                    "success": False,
                    "error": error_msg,
                }
            
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                }
                
        except Exception as e:
            logger.error(f"2FA verification error: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    async def check_session(self) -> Dict[str, Any]:
        """
        Check if we have a valid session from saved cookies.
        
        Returns:
            dict with keys:
            - valid: bool
            - user: dict (if valid)
        """
        if not self._auth_cookie:
            await self._load_cookies()
        
        if not self._auth_cookie:
            return {"valid": False}
        
        try:
            response = await self._request("GET", "/auth/user")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if still needs 2FA
                if "requiresTwoFactorAuth" in data:
                    return {"valid": False, "requires_2fa": True}
                
                self._current_user = data
                logger.info(f"Session valid for: {data.get('displayName')}")
                
                return {
                    "valid": True,
                    "user": data,
                }
            else:
                return {"valid": False}
                
        except Exception as e:
            logger.error(f"Session check error: {e}")
            return {"valid": False}
    
    async def logout(self):
        """
        Logout from the current in-memory session.
        
        NOTE: We intentionally do NOT delete the cookies.json file.
        This allows the auth cookie (and 2FA state) to persist, so the user
        doesn't have to re-enter 2FA every time they restart the app
        or 'logout' to switch accounts (unless they manually delete the file).
        """
        try:
             # Optionally call remote logout if you want to invalidate the cookie server-side
             # await self._request("PUT", "/logout")
             pass
        except:
            pass
        
        # Clear in-memory state only
        self._auth_cookie = None
        self._two_factor_auth_cookie = None
        self._current_user = None
        
        # Do NOT delete the file
        # if self._cookies_path.exists():
        #     self._cookies_path.unlink()
        
        logger.info("Logged out")
    
    async def get_pipeline_token(self) -> Optional[str]:
        """
        Get authentication token for WebSocket pipeline.
        Used to connect to wss://pipeline.vrchat.cloud
        
        Returns:
            Auth token string, or None if failed
        """
        try:
            response = await self._request("GET", "/auth")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return data.get("token")
                    
            logger.warning(f"Failed to get pipeline token: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting pipeline token: {e}")
            return None
    
    async def get_my_location(self) -> Optional[Dict[str, str]]:
        """
        Get the current user's location from the VRChat API.
        
        Uses the same approach as VRCX - fetches /auth/user and extracts
        the presence.world and presence.instance fields.
        
        Returns:
            Dict with 'world_id' and 'instance_id' if in an instance,
            None if offline or not in a valid instance
        """
        try:
            response = await self._request("GET", "/auth/user")
            
            if response.status_code == 200:
                data = response.json()
                presence = data.get("presence", {})
                
                world = presence.get("world", "")
                instance = presence.get("instance", "")
                
                # Check if in a real instance (not offline, private, etc.)
                if world and instance and world.startswith("wrld_"):
                    logger.info(f"Current location: {world}:{instance}")
                    return {
                        "world_id": world,
                        "instance_id": instance,
                        "location": f"{world}:{instance}",
                    }
                else:
                    logger.debug(f"Not in a valid instance. World: {world}, Instance: {instance}")
                    return None
            else:
                logger.warning(f"Failed to get location: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting location: {e}")
            return None
