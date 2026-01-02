
import os
import json
import hmac
import hashlib
import base64
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class IntegrityService:
    """
    Handles cryptographic signing and verification of database records
    to detect external tampering.
    """
    
    def __init__(self, key_path: str = "integrity.key"):
        self.key_path = key_path
        self._secret_key = self._load_or_generate_key()
        
    def _load_or_generate_key(self) -> bytes:
        """Load the secret key from disk or generate a new one if missing."""
        if os.path.exists(self.key_path):
            try:
                with open(self.key_path, "rb") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to load integrity key: {e}")
                
        # Generate new key
        logger.info("Generating new integrity security key...")
        new_key = os.urandom(32)  # 256-bit key
        try:
            with open(self.key_path, "wb") as f:
                f.write(new_key)
        except Exception as e:
            logger.error(f"Failed to save integrity key: {e}")
            
        return new_key

    def _serialize_fields(self, data: Dict[str, Any], fields: List[str]) -> bytes:
        """
        Concatenate specific fields into a byte string for signing.
        Order matters!
        """
        parts = []
        for field in fields:
            value = data.get(field)
            # Normalize inputs to string
            if value is None:
                s_val = ""
            elif isinstance(value, (int, float, bool)):
                s_val = str(value)
            else:
                s_val = str(value)
            parts.append(s_val.encode('utf-8'))
        
        return b"|".join(parts)

    def generate_hash(self, data: Dict[str, Any], fields: List[str]) -> str:
        """
        Generate an HMAC-SHA256 signature for the specified fields.
        Returns a base64 encoded string.
        """
        if not self._secret_key:
            return ""
            
        payload = self._serialize_fields(data, fields)
        signature = hmac.new(self._secret_key, payload, hashlib.sha256).digest()
        return base64.b64encode(signature).decode('utf-8')

    def verify_hash(self, data: Dict[str, Any], fields: List[str], stored_hash: str) -> bool:
        """
        Verify if the stored hash matches the current data.
        Returns True if authentic, False if tampered.
        """
        if not stored_hash:
            return False
            
        calculated = self.generate_hash(data, fields)
        # Constant time comparison to prevent timing attacks (overkill here but good practice)
        return hmac.compare_digest(calculated, stored_hash)

class SecureStorage:
    """
    Securely store credentials using the OS keyring (Credential Locker).
    """
    SERVICE_NAME = "GroupGuardianApp"

    @staticmethod
    def save_credentials(username: str, password: str):
        try:
            import keyring
            # Store password in OS Keychain
            keyring.set_password(SecureStorage.SERVICE_NAME, username, password)
            # We also need to remember WHICH user is logged in
            # We'll stick to a simple file for the "last logged in user" part, but not the pass
            with open("last_user", "w") as f:
                f.write(username)
            return True
        except Exception as e:
            logger.error(f"Failed to save to keyring: {e}")
            return False

    @staticmethod
    def get_credentials() -> tuple[Optional[str], Optional[str]]:
        try:
            import keyring
            if not os.path.exists("last_user"):
                return None, None
                
            with open("last_user", "r") as f:
                username = f.read().strip()
            
            if not username:
                return None, None
                
            password = keyring.get_password(SecureStorage.SERVICE_NAME, username)
            return username, password
        except Exception as e:
            logger.error(f"Failed to retrieve from keyring: {e}")
            return None, None

    @staticmethod
    def clear_credentials():
        try:
            import keyring
            if os.path.exists("last_user"):
                with open("last_user", "r") as f:
                    username = f.read().strip()
                if username:
                    try:
                        keyring.delete_password(SecureStorage.SERVICE_NAME, username)
                    except:
                        pass # Password might not exist
                os.remove("last_user")
        except Exception as e:
            logger.error(f"Failed to clear credentials: {e}")

# Singleton instance
_integrity_instance = None

def get_integrity_service() -> IntegrityService:
    global _integrity_instance
    if not _integrity_instance:
        _integrity_instance = IntegrityService()
    return _integrity_instance
