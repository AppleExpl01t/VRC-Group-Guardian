import httpx
import webbrowser
import logging
from packaging import version

logger = logging.getLogger(__name__)

from datetime import datetime

class UpdateService:
    GITHUB_REPO = "AppleExpl01t/VRC-Group-Guardian"
    CURRENT_VERSION = "1.0.0" 
    CURRENT_BUILD_TIMESTAMP = 0 # Injected during build (Unix Config)
    
    @staticmethod
    async def check_for_updates():
        """
        Check GitHub releases for a new version using TIMESTAMP.
        Returns (is_available, version_tag, asset_url, release_notes)
        """
        try:
            # 1. Get Latest Release
            url = f"https://api.github.com/repos/{UpdateService.GITHUB_REPO}/releases/latest"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                
            if response.status_code != 200:
                return False, None, None, None
                
            data = response.json()
            latest_tag = data.get("tag_name", "")
            body = data.get("body")
            published_at_str = data.get("published_at") # ISO 8601
            
            # Find .exe asset
            assets = data.get("assets", [])
            asset_url = None
            for asset in assets:
                if asset["name"].lower().endswith(".exe"):
                    asset_url = asset["browser_download_url"]
                    break
            
            if not asset_url or not published_at_str:
                return False, None, None, None

            # 2. Compare Timestamps
            # Parse GitHub time (e.g. 2025-12-25T20:00:00Z)
            # Simple manual parsing or use dateutil if available. 
            # Trying standard concise parsing:
            try:
                # Handle 'Z' manually if python < 3.11 for fromisoformat
                if published_at_str.endswith('Z'):
                    published_at_str = published_at_str[:-1] + '+00:00'
                remote_time = datetime.fromisoformat(published_at_str).timestamp()
            except Exception as e:
                logger.error(f"Time parsing failed: {e}")
                return False, None, None, None

            local_time = float(UpdateService.CURRENT_BUILD_TIMESTAMP)
            
            logger.info(f"Checking Update: Local Time={local_time} vs Remote Time={remote_time}")

            # Buffer: Remote must be at least 60 seconds newer than local build to avoid race conditions
            if remote_time > (local_time + 60):
                return True, latest_tag, asset_url, body
                    
            return False, None, None, None
            
        except Exception as e:
            logger.error(f"Update check failed: {e}")
            return False, None, None, None

    @staticmethod
    async def _get_commit_sha_from_tag(tag_name: str) -> str:
        """Resolves a tag name to a commit SHA"""
        try:
            # First, check if it's a ref
            url = f"https://api.github.com/repos/{UpdateService.GITHUB_REPO}/git/ref/tags/{tag_name}"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
            
            if response.status_code == 200:
                data = response.json()
                obj = data.get("object", {})
                sha = obj.get("sha")
                type = obj.get("type")
                
                if type == "commit":
                    return sha
                elif type == "tag":
                    # Annotated tag, fetch the tag object to get the commit
                    tag_url = obj.get("url")
                    async with client.get(tag_url, timeout=5.0) as tag_res:
                        if tag_res.status_code == 200:
                            return tag_res.json().get("object", {}).get("sha")
                            
            # If ref lookup failed, maybe the tag parsing was off by 'v'? Try simple fetch?
            # Actually, sometimes releases 'tag_name' might just be the name, but the ref is 'refs/tags/v...'
            # Let's try listing tags if the direct ref fails? No, too heavy.
            # Assume strict mapping for now or fallbacks.
            return None
        except Exception as e:
            logger.error(f"SHA Resolution error: {e}")
            return None

    @staticmethod
    def open_release_page(url):
        if url:
            webbrowser.open(url)

    @staticmethod
    async def download_update(download_url: str, progress_callback=None):
        """
        Download the update to a temporary file in the current directory.
        """
        import os
        import sys
        
        try:
            # Determine download path
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.getcwd() # In dev mode
            
            target_path = os.path.join(base_dir, "GroupGuardian_new.exe")
            
            logger.info(f"Downloading update to {target_path}...")
            
            async with httpx.AsyncClient(follow_redirects=True) as client:
                async with client.stream("GET", download_url) as response:
                    response.raise_for_status()
                    total = int(response.headers.get("Content-Length", 0))
                    
                    with open(target_path, "wb") as f:
                        current = 0
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)
                            current += len(chunk)
                            if progress_callback and total > 0:
                                progress_callback(current / total)
                                
            return target_path
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise e

    @staticmethod
    def apply_update(new_exe_path: str):
        """
        Launch the new executable with instructions to replace the old one.
        """
        import os
        import sys
        import subprocess
        
        if getattr(sys, 'frozen', False):
            current_exe = sys.executable
        else:
            logger.warning("Auto-update not supported in dev mode.")
            return

        # Launch the NEW exe, telling it to delete THIS exe
        # Argument: --perform-update "Path\To\Old.exe"
        logger.info(f"Launching new version for swap: {new_exe_path}")
        subprocess.Popen([new_exe_path, "--perform-update", current_exe])
        sys.exit(0)

    @staticmethod
    def handle_update_process():
        """
        Called at startup to check if we are the 'updater' process.
        Returns TRUE if we handled an update and should exit.
        """
        import sys
        import os
        import time
        import shutil
        import subprocess

        if "--perform-update" in sys.argv:
            try:
                # We are the NEW process (running as .new usually)
                old_exe_path = sys.argv[sys.argv.index("--perform-update") + 1]
                
                # 1. Wait for old process to exit
                time.sleep(2) 
                
                # 2. Delete the old executable
                if os.path.exists(old_exe_path):
                    try:
                        os.remove(old_exe_path)
                    except Exception as e:
                        # If deletion fails, we can't really proceed with a clean swap
                        # But we are already running the new version...
                        print(f"Failed to delete old exe: {e}")
                
                # 3. Copy OURSELVES to the original name (GroupGuardian.exe)
                # We are currently running as GroupGuardian_new.exe
                current_running_path = sys.executable
                
                # Check if we are already named correctly (unlikely in this flow)
                if os.path.abspath(current_running_path) == os.path.abspath(old_exe_path):
                    return False # Nothing to do?
                
                shutil.copy2(current_running_path, old_exe_path)
                
                # 4. Launch the restored 'GroupGuardian.exe'
                subprocess.Popen([old_exe_path])
                
                # 5. Exit this temporary process containing the update logic
                # The OS will clean up this temp file eventually or we leave it 
                # (Optional: launch a cleanup script for the .new file? Hard to self-delete.)
                sys.exit(0)
                
            except Exception as e:
                print(f"Update error: {e}")
                # If update failed, maybe just continue running as the new version?
                # or exiting? Let's continue running so the user at least has the app.
                return False
        
        return False

    @staticmethod
    async def get_latest_asset_url(tag):
        """Helper to find the .exe asset url for a specific tag"""
        try:
            url = f"https://api.github.com/repos/{UpdateService.GITHUB_REPO}/releases/tags/v{tag}"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                if response.status_code == 200:
                    assets = response.json().get("assets", [])
                    for asset in assets:
                         if asset["name"].endswith(".exe"):
                             return asset["browser_download_url"]
            return None
        except:
             return None
