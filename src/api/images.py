"""
Images Mixin
=============
Image downloading and local caching functionality.
"""

from typing import Optional
from services.debug_logger import get_logger
from utils.paths import get_image_cache_dir

logger = get_logger("api.images")


class ImagesMixin:
    """
    Mixin providing image caching functionality:
    - Download images from VRChat API
    - Cache images locally
    - Cache user profile images
    - Cache group icons and banners
    """
    
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
            # Removed self._vrcx_rate_limit() to avoid throttling image downloads
            
            # Use browser headers for images to avoid Cloudflare/CDN blocks
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8"
            }
            
            response = await client.get(
                url,
                cookies=self._get_cookies(),
                headers=headers,
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
        
        Priority order for profile images:
        1. profilePicOverride - User's custom profile picture (most accurate)
        2. userIcon - User-set icon
        3. currentAvatarThumbnailImageUrl - Current avatar thumbnail
        4. currentAvatarImageUrl - Full avatar image
        """
        user_id = user.get("id", "unknown")
        
        # Priority order for profile images
        img_url = (
            user.get("profilePicOverride") or  # Custom profile pic (primary)
            user.get("userIcon") or  # User icon
            user.get("currentAvatarThumbnailImageUrl") or  # Avatar thumbnail
            user.get("currentAvatarImageUrl") or  # Full avatar
            user.get("imageUrl") or  # General image URL
            user.get("thumbnailUrl")  # General thumbnail URL
        )
        
        if not img_url:
            return None
            
        return await self.download_image(img_url, f"user_{user_id}_pfp")

