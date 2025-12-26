"""
VRChat API Client
=================
Handles authentication and API requests with proper rate limiting
"""

import httpx
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from services.debug_logger import get_logger, log_request
from utils.paths import get_cookies_path, get_api_cache_path, get_image_cache_dir

logger = get_logger("api.client")


class VRChatAPI:
    """
    VRChat API Client with VRCX-style request handling:
    
    1. Request Deduplication - Pending GET requests are cached for 10s
    2. Failed Request Cache - 403/404 errors are cached for 15min to avoid retries
    3. Rate Limiter - Token bucket style, X requests per Y interval
    4. Exponential Backoff - Retry with exponential delays on failures
    5. Global 429 Blocking - All requests pause on rate limit
    """
    
    BASE_URL = "https://api.vrchat.cloud/api/1"
    USER_AGENT = "GroupGuardian/1.0.0 (VRChat Moderation Tool)"
    
    # VRCX-style constants
    PENDING_REQUEST_TTL = 10.0  # seconds - merge duplicate GET requests within this window
    FAILED_REQUEST_TTL = 900.0  # 15 minutes - don't retry 403/404 within this window
    RATE_LIMIT_PER_MINUTE = 60  # requests per minute
    MAX_RETRIES = 5
    BASE_BACKOFF_DELAY = 1.0  # seconds
    
    def __init__(self, cookies_path: str = None):
        # Use centralized path utilities for proper EXE-relative paths
        self._cookies_path = Path(cookies_path) if cookies_path else get_cookies_path()
        self._client: Optional[httpx.AsyncClient] = None
        self._last_request_time: Optional[datetime] = None
        self._min_request_interval = 0.1  # 100ms minimum spacing between requests
        self._auth_cookie: Optional[str] = None
        self._two_factor_auth_cookie: Optional[str] = None
        self._current_user: Optional[Dict] = None
        self._requires_2fa: bool = False
        self._2fa_type: Optional[str] = None
        
        # VRCX-style request management
        self._pending_requests: Dict[str, Dict] = {}  # URL -> {"task": Task, "time": datetime}
        self._failed_requests: Dict[str, datetime] = {}  # endpoint -> last_fail_time
        self._rate_limiter_stamps: List[datetime] = []  # timestamps of recent requests
        self._request_lock = asyncio.Lock()
        self._api_blocked = asyncio.Event()
        self._api_blocked.set()  # Not blocked initially
        
        # Caching - use centralized path
        self._cache_file = get_api_cache_path()
        self._cache = self._load_api_cache()
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper headers"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "User-Agent": self.USER_AGENT,
                    "Accept": "application/json",
                },
                timeout=30.0,
                follow_redirects=True,
            )
            # Load saved cookies if they exist
            await self._load_cookies()
        return self._client
    
    async def _load_cookies(self):
        """Load saved auth cookies from file"""
        if self._cookies_path.exists():
            try:
                data = json.loads(self._cookies_path.read_text())
                self._auth_cookie = data.get("auth")
                self._two_factor_auth_cookie = data.get("twoFactorAuth")
                logger.info("Loaded saved session cookies")
            except Exception as e:
                logger.warning(f"Could not load cookies: {e}")
    
    def _load_api_cache(self) -> Dict:
        """Load API cache from disk"""
        if self._cache_file.exists():
            try:
                return json.loads(self._cache_file.read_text())
            except:
                return {}
        return {}

    def _save_api_cache(self):
        """Save API cache to disk"""
        try:
            self._cache_file.write_text(json.dumps(self._cache))
        except Exception as e:
            logger.warning(f"Failed to write cache: {e}")

    async def _save_cookies(self):
        """Save auth cookies to file"""
        try:
            data = {
                "auth": self._auth_cookie,
                "twoFactorAuth": self._two_factor_auth_cookie,
            }
            self._cookies_path.write_text(json.dumps(data))
            logger.info("Saved session cookies")
        except Exception as e:
            logger.warning(f"Could not save cookies: {e}")
    
    def _get_cookies(self) -> Dict[str, str]:
        """Get cookies dict for requests"""
        cookies = {}
        if self._auth_cookie:
            cookies["auth"] = self._auth_cookie
        if self._two_factor_auth_cookie:
            cookies["twoFactorAuth"] = self._two_factor_auth_cookie
        return cookies
    
    def _extract_cookies(self, response: httpx.Response):
        """Extract auth cookies from response"""
        for cookie_name, cookie_value in response.cookies.items():
            if cookie_name == "auth":
                self._auth_cookie = cookie_value
                logger.debug("Got auth cookie")
            elif cookie_name == "twoFactorAuth":
                self._two_factor_auth_cookie = cookie_value
                logger.debug("Got 2FA cookie")
    
    async def _vrcx_rate_limit(self):
        """
        VRCX-style token bucket rate limiter.
        Allows RATE_LIMIT_PER_MINUTE requests per minute with smooth distribution.
        """
        now = datetime.now()
        interval = timedelta(minutes=1)
        
        # Clean old timestamps
        self._rate_limiter_stamps = [
            ts for ts in self._rate_limiter_stamps 
            if now - ts < interval
        ]
        
        # If at limit, wait for oldest to expire
        if len(self._rate_limiter_stamps) >= self.RATE_LIMIT_PER_MINUTE:
            oldest = self._rate_limiter_stamps[0]
            wait_time = (oldest + interval - now).total_seconds()
            if wait_time > 0:
                logger.debug(f"Rate limiter: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
        
        self._rate_limiter_stamps.append(datetime.now())
    
    def _is_failed_request_cached(self, endpoint: str) -> bool:
        """
        VRCX-style: Check if endpoint recently returned 403/404.
        Don't retry for 15 minutes.
        """
        if endpoint in self._failed_requests:
            last_fail = self._failed_requests[endpoint]
            if (datetime.now() - last_fail).total_seconds() < self.FAILED_REQUEST_TTL:
                return True
            # Expired, remove from cache
            del self._failed_requests[endpoint]
        return False
    
    def _cache_failed_request(self, endpoint: str):
        """Mark an endpoint as recently failed (403/404)"""
        self._failed_requests[endpoint] = datetime.now()
    
    async def _execute_with_backoff(self, fn, endpoint: str):
        """
        VRCX-style exponential backoff with retry.
        """
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                return await fn()
            except Exception as e:
                last_error = e
                # Check if it's a retryable error (429)
                if hasattr(e, 'response') and e.response.status_code == 429:
                    delay = self.BASE_BACKOFF_DELAY * (2 ** attempt)
                    logger.warning(f"Backoff: waiting {delay:.1f}s before retry {attempt + 1}/{self.MAX_RETRIES}")
                    await asyncio.sleep(delay)
                else:
                    raise
        raise last_error
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> httpx.Response:
        """
        VRCX-style request handling with:
        1. Request deduplication for GET requests
        2. Failed request caching (skip 403/404 for 15 min)
        3. Token bucket rate limiting
        4. Global 429 blocking
        5. Exponential backoff on failures
        """
        client = await self._get_client()
        
        # Build full URL for deduplication key
        url_key = f"{method}:{endpoint}"
        if "params" in kwargs:
            import urllib.parse
            url_key += "?" + urllib.parse.urlencode(kwargs["params"])
        
        # VRCX Pattern 1: Check failed request cache for GET requests
        if method == "GET" and self._is_failed_request_cached(endpoint):
            logger.debug(f"Skipping recently failed endpoint: {endpoint}")
            # Return a mock 404 response
            raise Exception(f"Endpoint {endpoint} recently failed (cached)")
        
        # VRCX Pattern 2: Request deduplication for GET requests
        if method == "GET" and url_key in self._pending_requests:
            pending = self._pending_requests[url_key]
            if (datetime.now() - pending["time"]).total_seconds() < self.PENDING_REQUEST_TTL:
                logger.debug(f"Merging duplicate request: {endpoint}")
                return await pending["task"]
            else:
                # Expired, remove
                del self._pending_requests[url_key]
        
        # Add cookies
        cookies = self._get_cookies()
        if cookies:
            kwargs["cookies"] = cookies
        
        async def do_request():
            # Wait for global block to clear
            await self._api_blocked.wait()
            
            # Apply rate limiting
            await self._vrcx_rate_limit()
            
            # Also apply minimum spacing
            async with self._request_lock:
                if self._last_request_time:
                    elapsed = (datetime.now() - self._last_request_time).total_seconds()
                    if elapsed < self._min_request_interval:
                        await asyncio.sleep(self._min_request_interval - elapsed)
                self._last_request_time = datetime.now()
            
            response = await client.request(method, endpoint, **kwargs)
            self._extract_cookies(response)
            
            # Handle 429
            if response.status_code == 429:
                if self._api_blocked.is_set():
                    self._api_blocked.clear()
                    retry_after = float(response.headers.get("Retry-After", 10.0))
                    wait_time = retry_after + 1.0
                    logger.error(f"429 RATE LIMITED! Blocking API for {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                    self._api_blocked.set()
                else:
                    await self._api_blocked.wait()
                # Retry by raising
                raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
            
            # Cache 403/404 for GET requests
            if method == "GET" and response.status_code in (403, 404):
                self._cache_failed_request(endpoint)
            
            return response
        
        # For GET requests, store as pending
        if method == "GET":
            task = asyncio.create_task(do_request())
            self._pending_requests[url_key] = {"task": task, "time": datetime.now()}
            try:
                response = await task
            finally:
                # Cleanup
                if url_key in self._pending_requests:
                    del self._pending_requests[url_key]
            return response
        else:
            # Non-GET: just execute with backoff
            for attempt in range(self.MAX_RETRIES):
                try:
                    return await do_request()
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < self.MAX_RETRIES - 1:
                        delay = self.BASE_BACKOFF_DELAY * (2 ** attempt)
                        logger.warning(f"Retry {attempt + 1}/{self.MAX_RETRIES} after {delay:.1f}s")
                        await asyncio.sleep(delay)
                    else:
                        raise
                except httpx.RequestError as e:
                    if attempt < self.MAX_RETRIES - 1:
                        delay = self.BASE_BACKOFF_DELAY * (2 ** attempt)
                        logger.warning(f"Request error, retry {attempt + 1}: {e}")
                        await asyncio.sleep(delay)
                    else:
                        raise

    
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
    
    @property
    def is_authenticated(self) -> bool:
        """Check if currently authenticated"""
        return self._current_user is not None
    
    @property
    def current_user(self) -> Optional[Dict]:
        """Get current user info"""
        return self._current_user
    
    @property
    def requires_2fa(self) -> bool:
        """Check if 2FA is required"""
        return self._requires_2fa
    
    @property
    def two_factor_type(self) -> Optional[str]:
        """Get the type of 2FA required"""
        return self._2fa_type
    
    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
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

    
    # ==================== IMAGE METHODS ====================
    
    async def download_image(self, url: str, save_name: str) -> Optional[str]:
        """
        Download an image from VRChat API (with auth cookies) and save locally.
        
        Args:
            url: The VRChat image URL
            save_name: Unique name for the saved file (no extension)
            
        Returns:
            Local file path to the saved image, or None if failed
        """
        if not url:
            return None
        
        # Use centralized path utility for EXE-relative path
        cache_dir = get_image_cache_dir()
        
        # Determine file extension from URL or default to png
        ext = "png"
        if ".jpg" in url or ".jpeg" in url:
            ext = "jpg"
        elif ".webp" in url:
            ext = "webp"
        
        local_path = cache_dir / f"{save_name}.{ext}"
        
        # Check if already cached
        if local_path.exists():
            return str(local_path.absolute())
        
        try:
            client = await self._get_client()
            await self._vrcx_rate_limit() # Enforce rate limit for images too
            response = await client.get(
                url,
                cookies=self._get_cookies(),
                follow_redirects=True,
            )
            
            if response.status_code == 200:
                local_path.write_bytes(response.content)
                logger.debug(f"Cached image: {save_name}")
                return str(local_path.absolute())
            else:
                logger.warning(f"Failed to download image {url}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            return None
    
    async def cache_group_images(self, group: dict) -> dict:
        """
        Download and cache group icon and banner images.
        
        Args:
            group: Group dict with iconUrl and bannerUrl
            
        Returns:
            Group dict with updated local paths
        """
        group_id = group.get("id", "unknown")
        
        # Cache icon
        icon_url = group.get("iconUrl")
        if icon_url:
            local_icon = await self.download_image(icon_url, f"group_{group_id}_icon")
            if local_icon:
                group["iconUrl"] = local_icon
        
        # Cache banner
        banner_url = group.get("bannerUrl")
        if banner_url:
            local_banner = await self.download_image(banner_url, f"group_{group_id}_banner")
            if local_banner:
                group["bannerUrl"] = local_banner
        
        return group
    
    async def cache_user_image(self, user: dict) -> str:
        """
        Download and cache user profile image.
        Returns the local path or None.
        """
        user_id = user.get("id", "unknown")
        # Try current avatar thumbnail first (usually best for PFP), then userIcon
        img_url = user.get("currentAvatarThumbnailImageUrl") or user.get("userIcon")
        
        if not img_url:
            return None
            
        return await self.download_image(img_url, f"user_{user_id}_pfp")

    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Fetch full user details"""
        try:
            response = await self._request("GET", f"/users/{user_id}")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None

    async def get_friends(self, offline: bool = False, n: int = 100, offset: int = 0) -> List[Dict]:
        """
        Fetch the authenticated user's friends list.
        
        Args:
            offline: If True, return only offline friends. If False, return online/active friends.
            n: Number of friends to return (max 100 per request)
            offset: Offset for pagination
            
        Returns:
            List of friend user objects
        """
        try:
            params = {
                "n": min(n, 100),
                "offset": offset,
                "offline": str(offline).lower(),
            }
            
            response = await self._request(
                "GET",
                "/auth/user/friends",
                params=params,
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch friends: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching friends: {e}")
            return []

    async def get_all_friends(self, on_progress=None) -> List[Dict]:
        """
        Fetch ALL friends (both online and offline) with pagination.
        
        Args:
            on_progress: Optional callback(current, is_online_phase) for progress updates
            
        Returns:
            Complete list of all friends
        """
        all_friends = []
        
        # Get online friends first
        logger.info("Fetching online friends...")
        offset = 0
        while True:
            batch = await self.get_friends(offline=False, n=100, offset=offset)
            if not batch:
                break
            all_friends.extend(batch)
            logger.info(f"Fetched {len(batch)} online friends (total: {len(all_friends)})")
            if on_progress:
                try:
                    on_progress(len(all_friends), True)
                except:
                    pass
            if len(batch) < 100:
                break
            offset += 100
        
        # Get offline friends
        logger.info("Fetching offline friends...")
        offset = 0
        while True:
            batch = await self.get_friends(offline=True, n=100, offset=offset)
            if not batch:
                break
            all_friends.extend(batch)
            logger.info(f"Fetched {len(batch)} offline friends (total: {len(all_friends)})")
            if on_progress:
                try:
                    on_progress(len(all_friends), False)
                except:
                    pass
            if len(batch) < 100:
                break
            offset += 100
        
        logger.info(f"Total: {len(all_friends)} friends fetched")
        return all_friends

    async def search_users(self, query: str, n: int = 20, offset: int = 0) -> List[Dict]:
        """
        Search for VRChat users by displayName.
        
        Args:
            query: The search term to match against displayName
            n: Number of results to return (max 100)
            offset: Offset for pagination
            
        Returns:
            List of user objects matching the search
        """
        if not query or not query.strip():
            return []
            
        try:
            params = {
                "search": query.strip(),
                "n": min(n, 100),
                "offset": offset,
            }
            
            response = await self._request(
                "GET",
                "/users",
                params=params,
            )
            
            if response.status_code == 200:
                users = response.json()
                logger.info(f"Found {len(users)} users for query '{query}'")
                return users
            else:
                logger.warning(f"Failed to search users: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return []

    # ==================== GROUP METHODS ====================
    
    async def get_my_groups(self, force_refresh: bool = False) -> List[Dict]:
        """
        Fetch all groups where the user has moderation permissions.
        Uses aggressive disk caching (1 hour TTL).
        """
        # Ensure we have user ID
        user_id = self._current_user.get("id")
        if not user_id:
            # Try to get user info if missing
            chk = await self.check_session()
            if not chk.get("valid"):
                return []
            user_id = self._current_user.get("id")
            
        # 1. Check Cache
        # 1. Check Cache
        cache_key = f"groups_{user_id}"
        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached:
                timestamp = cached.get("time", 0)
                if (datetime.now().timestamp() - timestamp) < 3600: # 1 hour
                    logger.info("Using cached group list from disk")
                    return cached.get("data", [])
        
        logger.info(f"Fetching groups for {user_id} (API)...")

        try:
            # First get user's group memberships (lite)
            response = await self._request(
                "GET",
                f"/users/{user_id}/groups",
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to get groups: {response.status_code}")
                return []
            
            memberships = response.json()
            
            # Helper for parallel processing
            async def process_membership(membership):
                group_id = membership.get("groupId")
                if not group_id: return None
                
                # Get full group info
                group_info = await self.get_group(group_id)
                if not group_info: return None
                    
                # Check permissions
                my_member = group_info.get("myMember", {})
                permissions = my_member.get("permissions", [])
                mod_perms = ["group-bans-manage", "group-members-manage", "group-instance-moderate", "group-data-manage", "group-audit-view", "*"]
                
                has_mod_perms = any(p in permissions for p in mod_perms)
                is_owner = my_member.get("isOwner", False)
                
                if has_mod_perms or is_owner:
                    # Construct Image URLs if missing
                    icon_url = group_info.get("iconUrl")
                    if not icon_url and group_info.get("iconId"):
                        icon_url = f"https://api.vrchat.cloud/api/1/file/{group_info['iconId']}/image/file"
                    
                    banner_url = group_info.get("bannerUrl")
                    if not banner_url and group_info.get("bannerId"):
                        banner_url = f"https://api.vrchat.cloud/api/1/file/{group_info['bannerId']}/image/file"

                    # Fetch pending requests count (if we have permission)
                    request_count = 0
                    if any(p in permissions for p in ["group-members-manage", "*"]) or is_owner:
                         # We use a safe separate call here
                         try:
                             reqs = await self.get_group_join_requests(group_id)
                             request_count = len(reqs)
                         except:
                             pass

                    group_data = {
                        "id": group_id,
                        "name": group_info.get("name", "Unknown Group"),
                        "shortCode": group_info.get("shortCode", ""),
                        "discriminator": group_info.get("discriminator", ""),
                        "description": group_info.get("description", ""),
                        "iconUrl": icon_url,
                        "bannerUrl": banner_url,
                        "memberCount": group_info.get("memberCount", 0),
                        "onlineMemberCount": group_info.get("onlineMemberCount", 0),
                        "pendingRequestCount": request_count,
                        "isOwner": is_owner,
                        "permissions": permissions,
                        "roles": my_member.get("roleIds", []),
                    }
                    # No image caching, rely on Flet remote URLs
                    return group_data
                return None

            # Run all tasks in parallel
            print(f"Fetching details for {len(memberships)} groups concurrently...")
            tasks = [process_membership(m) for m in memberships]
            results = await asyncio.gather(*tasks)
            
            # Filter and Cache
            mod_groups = [r for r in results if r]
            print(f"Processing complete: {len(mod_groups)} mod groups found")
            
            if mod_groups:
                self._cache[cache_key] = {
                    "time": datetime.now().timestamp(),
                    "data": mod_groups
                }
                self._save_api_cache()
            
            return mod_groups
            
        except Exception as e:
            logger.error(f"Error fetching groups: {e}")
            return []
    
    async def get_group(self, group_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific group.
        
        Args:
            group_id: The group ID
            
        Returns:
            Group info dict or None
        """
        try:
            response = await self._request(
                "GET",
                f"/groups/{group_id}",
                params={"includeRoles": "true"},
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get group {group_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching group: {e}")
            return None
    
    async def get_group_instances(self, group_id: str) -> list:
        """Get active instances for a group"""
        try:
            response = await self._request(
                "GET",
                f"/groups/{group_id}/instances",
            )
            
            if response.status_code == 200:
                return response.json()
            return []
            
        except Exception as e:
            logger.error(f"Error fetching group instances: {e}")
            return []
    
    async def close_group_instance(self, world_id: str, instance_id: str, hard_close: bool = False) -> bool:
        """Close a group instance
        
        Args:
            world_id: The world ID (wrld_xxx)
            instance_id: The instance ID (includes the full location string after the world ID)
            hard_close: If True, forces immediate close
            
        Returns:
            True if successful, False otherwise
        """
        try:
            location = f"{world_id}:{instance_id}"
            logger.info(f"Closing instance: {location}")
            
            params = {}
            if hard_close:
                params["hardClose"] = "true"
            
            response = await self._request(
                "DELETE",
                f"/instances/{location}",
                params=params if params else None,
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"Instance closed successfully: {location}")
                return True
            else:
                logger.warning(f"Failed to close instance: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error closing instance: {e}")
            return False
            
    async def get_group_join_requests(self, group_id: str) -> list:
        """Get pending join requests for a group"""
        try:
            logger.info(f"Fetching join requests for group {group_id}")
            response = await self._request(
                "GET",
                f"/groups/{group_id}/requests",
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Found {len(data)} join requests")
                if data:
                    logger.debug(f"Sample Request Data: {data[0]}")
                return data
            else:
                logger.warning(f"Failed to fetch requests: {response.status_code} - {response.text}")
                return []
            
        except Exception as e:
            logger.error(f"Error fetching join requests: {e}")
            return []
    
    async def get_group_bans(self, group_id: str) -> list:
        """Get banned members for a group"""
        try:
            response = await self._request(
                "GET",
                f"/groups/{group_id}/bans",
            )
            
            if response.status_code == 200:
                return response.json()
            return []
            
        except Exception as e:
            logger.error(f"Error fetching group bans: {e}")
            return []
    
    async def get_group_audit_logs(self, group_id: str, n: int = 50) -> list:
        """Get audit logs for a group"""
        try:
            response = await self._request(
                "GET",
                f"/groups/{group_id}/auditLogs",
                params={"n": n},
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            return []
            
        except Exception as e:
            logger.error(f"Error fetching audit logs: {e}")
            return []

    async def search_group_members(self, group_id: str, query: str = None, limit: int = 50, offset: int = 0) -> list:
        """Search group members"""
        try:
            params = {"n": limit, "offset": offset}
            if query:
                params["query"] = query
                
            response = await self._request(
                "GET",
                f"/groups/{group_id}/members",
                params=params,
            )
            
            if response.status_code == 200:
                return response.json()
            return []
            
        except Exception as e:
            logger.error(f"Error searching group members: {e}")
            return []

    async def get_group_online_members(self, group_id: str, limit: int = 1000) -> List[Dict]:
        """
        Fetch all online members of a group.
        Since the API doesn't support filtering by 'online' directly for groups,
        we fetch members and filter client-side.
        """
        online_members = []
        offset = 0
        batch_size = 100
        
        logger.debug(f"[DEBUG] Fetching online members for group {group_id} (limit={limit})")
        
        try:
            while len(online_members) < limit:
                logger.debug(f"[DEBUG] Fetching batch offset={offset}, size={batch_size}")
                members = await self.search_group_members(group_id, limit=batch_size, offset=offset)
                if not members:
                    logger.debug(f"[DEBUG] No members returned in batch.")
                    break
                    
                batch_online = 0
                for member in members:
                    # The member object contains a 'user' field with details
                    user = member.get("user", {})
                    # Check location/status to determine if online
                    # Note: Group member objects might not always have full location data depending on privacy,
                    # but usually have status/location if the caller has permissions.
                    
                    # Log raw status for debugging first few
                    if offset == 0 and batch_online < 3:
                        logger.debug(f"[DEBUG] Sample User: {user.get('displayName')} | Status: {user.get('status')} | Loc: {user.get('location')}")

                    if user.get("location") and user.get("location") != "offline":
                         online_members.append(user)
                         batch_online += 1
                    elif user.get("status") and user.get("status") != "offline":
                         online_members.append(user)
                         batch_online += 1
                
                logger.debug(f"[DEBUG] Batch found {batch_online} online members. Total so far: {len(online_members)}")
                         
                if len(members) < batch_size:
                    break
                    
                offset += batch_size
                
            logger.info(f"Found {len(online_members)} online members in group {group_id}")
            return online_members
        except Exception as e:
            logger.error(f"Error fetching group online members: {e}")
            return []

    async def handle_join_request(self, group_id: str, user_id: str, action: str = "accept") -> bool:
        """
        Handle a group join request.
        
        Args:
            group_id: The group ID
            user_id: The requesting user ID (usr_...)
            action: 'accept' or 'reject'
            
        Returns:
            True if successful
        """
        try:
            response = await self._request(
                "PUT",
                f"/groups/{group_id}/requests/{user_id}",
                json={"action": action}
            )
            
            if response.status_code == 200:
                logger.info(f"Join request {action}ed for user {user_id}")
                return True
            else:
                logger.error(f"Failed to {action} join request: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error handling join request: {e}")
            return False

    async def ban_user(self, group_id: str, user_id: str) -> bool:
        """Ban a user from the group"""
        try:
            response = await self._request(
                "POST",
                f"/groups/{group_id}/bans",
                json={"userId": user_id}
            )
            
            if response.status_code == 200:
                logger.info(f"Banned user {user_id} from group {group_id}")
                return True
            else:
                logger.error(f"Failed to ban user: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error banning user: {e}")
            return False

    async def unban_user(self, group_id: str, user_id: str) -> bool:
        """Unban a user from the group"""
        try:
            response = await self._request(
                "DELETE",
                f"/groups/{group_id}/bans/{user_id}",
            )
            
            if response.status_code == 200:
                logger.info(f"Unbanned user {user_id} from group {group_id}")
                return True
            else:
                logger.error(f"Failed to unban user: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error unbanning user: {e}")
            return False

    async def invite_user_to_group(self, group_id: str, user_id: str) -> bool:
        """Invite a user to join the group"""
        try:
            response = await self._request(
                "POST",
                f"/groups/{group_id}/invites",
                json={"userId": user_id}
            )
            
            if response.status_code == 200:
                logger.info(f"Invited user {user_id} to group {group_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error inviting user: {e}")
            return False

    async def get_world(self, world_id: str) -> Optional[Dict]:
        """Get world details"""
        try:
             response = await self._request("GET", f"/worlds/{world_id}")
             if response.status_code == 200:
                 return response.json()
             return None
        except Exception as e:
            logger.error(f"Error fetching world: {e}")
            return None

    async def invite_to_instance(self, user_id: str, world_id: str, instance_id: str, world_name: str = None, message_slot: int = None) -> bool:
        """
        Send an instance invite to a user.
        
        Args:
            user_id: The user ID (usr_xxx)
            world_id: The world ID (wrld_xxx)
            instance_id: The instance ID
            world_name: Optional world name (matches VRCX behavior)
            message_slot: Optional message slot index (1-12)
            
        Returns:
            True if successful
        """
        try:
            # Full instance location format
            instance_location = f"{world_id}:{instance_id}"
            
            payload = {
                "instanceId": instance_location,
                "worldId": world_id,
            }
            
            if world_name:
                payload["worldName"] = world_name
                
            if message_slot is not None:
                payload["messageSlot"] = message_slot
            
            response = await self._request(
                "POST",
                f"/invite/{user_id}",
                json=payload
            )
            
            if response.status_code == 200:
                logger.info(f"Sent invite to {user_id} for {instance_location}")
                return True
            else:
                logger.warning(f"Failed to invite {user_id}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending invite to {user_id}: {e}")
            return False

    async def create_instance(self, world_id: str, type: str, region: str, 
                            owner_id: str = None, count: int = 0,
                            group_id: str = None, group_access_type: str = None, 
                            queue_enabled: bool = False, role_ids: list = None,
                            name: str = None) -> Optional[Dict]:
        """
        Create a new instance.
        """
        try:
            payload = {
                "worldId": world_id,
                "type": type,
                "region": region,
            }
            
            if type == "group":
                if not group_id: return None
                # VRChat API expects ownerId to be the group ID for group instances
                payload["ownerId"] = group_id
                # payload["groupId"] = group_id # Some docs say groupId, VRCX uses ownerId. Let's send both or just ownerId.
                # VRCX sets ownerId to groupId. Let's follow VRCX.
                if group_access_type:
                    payload["groupAccessType"] = group_access_type
                if queue_enabled:
                    payload["queueEnabled"] = True
                if role_ids:
                    payload["roleIds"] = role_ids
            
            if name: # Custom instance name (VRC+ only usually)
                payload["name"] = name

            response = await self._request("POST", "/instances", json=payload)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to create instance: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating instance: {e}")
            return None

    async def get_group_roles(self, group_id: str) -> list:
        """Fetch roles for a group"""
        try:
            response = await self._request("GET", f"/groups/{group_id}/roles")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error fetching group roles: {e}")
            return []
