"""
Request Handler Mixin
======================
VRCX-style request handling with rate limiting, deduplication, and backoff.
"""

import httpx
import asyncio
from datetime import datetime, timedelta
from services.debug_logger import get_logger, log_request

logger = get_logger("api.request")


class RequestMixin:
    """
    Mixin providing VRCX-style request handling:
    
    1. Request Deduplication - Pending GET requests are cached for 10s
    2. Failed Request Cache - 403/404 errors are cached for 15min to avoid retries
    3. Rate Limiter - Token bucket style, X requests per Y interval
    4. Exponential Backoff - Retry with exponential delays on failures
    5. Global 429 Blocking - All requests pause on rate limit
    """
    
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
            # VRCX-style exponential backoff with retry
            last_error = None
            
            for attempt in range(self.MAX_RETRIES):
                try:
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
                        
                        # Raise to trigger retry loop
                        raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
                    
                    # Cache 403/404 for GET requests
                    if method == "GET" and response.status_code in (403, 404):
                        self._cache_failed_request(endpoint)
                    
                    return response
                    
                except httpx.HTTPStatusError as e:
                    last_error = e
                    # If it was a 429, we already slept above, but we need to verify we can retry
                    if e.response.status_code == 429:
                        if attempt < self.MAX_RETRIES - 1:
                            # Continue to next attempt
                            continue
                    
                    # For other status errors, just raise (unless we want to retry 500s?)
                    # Current logic only retries 429s for status errors
                    raise
                    
                except httpx.RequestError as e:
                    last_error = e
                    if attempt < self.MAX_RETRIES - 1:
                        delay = self.BASE_BACKOFF_DELAY * (2 ** attempt)
                        logger.warning(f"Request error, retry {attempt + 1}/{self.MAX_RETRIES}: {e}")
                        await asyncio.sleep(delay)
                    else:
                        raise
            
            if last_error:
                raise last_error
        
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
            # Non-GET: just execute
            return await do_request()
