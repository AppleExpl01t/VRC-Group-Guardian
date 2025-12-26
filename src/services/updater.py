import httpx
import webbrowser
import logging
from packaging import version

logger = logging.getLogger(__name__)

class UpdateService:
    GITHUB_REPO = "AppleExpl01t/VRC-Group-Guardian"
    CURRENT_VERSION = "1.0.0" 
    CURRENT_COMMIT_SHA = "9d583336de02cf799fef25809dd966899816cffa7" # Updated automatically during build
    
    @staticmethod
    async def check_for_updates():
        """
        Check GitHub releases for a new version using COMMIT SHA.
        Returns (is_available, version_tag, asset_url, release_notes)
        """
        try:
            # 1. Get Latest Release
            url = f"https://api.github.com/repos/{UpdateService.GITHUB_REPO}/releases/latest"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                
            if response.status_code != 200:
                logger.error(f"Failed to fetch release: {response.status_code}")
                return False, None, None, None
                
            data = response.json()
            latest_tag = data.get("tag_name", "")
            body = data.get("body")
            
            # Find .exe asset
            assets = data.get("assets", [])
            asset_url = None
            for asset in assets:
                if asset["name"].lower().endswith(".exe"):
                    asset_url = asset["browser_download_url"]
                    break
            
            if not asset_url:
                return False, None, None, None

            # 2. Get Commit SHA for this Tag
            remote_sha = await UpdateService._get_commit_sha_from_tag(latest_tag)
            
            if not remote_sha:
                logger.warning(f"Could not resolve SHA for tag {latest_tag}")
                return False, None, None, None

            logger.info(f"Checking Update: Local SHA={UpdateService.CURRENT_COMMIT_SHA[:7]} vs Remote SHA={remote_sha[:7]}")

            # 3. Compare SHAs
            if remote_sha != UpdateService.CURRENT_COMMIT_SHA:
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
        Create a batch script to swap the executable and restart.
        """
        import os
        import sys
        import subprocess
        
        if getattr(sys, 'frozen', False):
            current_exe = sys.executable
        else:
            # In dev mode, we can't really "restart" the exe, so just mock it
            logger.warning("Auto-update not supported in dev mode. Just pretending.")
            return

        base_dir = os.path.dirname(current_exe)
        exe_name = os.path.basename(current_exe)
        bat_path = os.path.join(base_dir, "update.bat")
        
        # Script content: Wait, Delete Old, Rename New, Start New, Delete Self
        script = f"""
@echo off
timeout /t 2 /nobreak > NUL
del "{exe_name}"
move "{os.path.basename(new_exe_path)}" "{exe_name}"
start "" "{exe_name}"
del "%~f0"
"""
        with open(bat_path, "w") as f:
            f.write(script)
            
        # Launch the script and exit
        logger.info(f"Launching update script: {bat_path}")
        subprocess.Popen([bat_path], shell=True)
        sys.exit(0)

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
