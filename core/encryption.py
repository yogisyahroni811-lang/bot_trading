"""
Enhanced Encryption Module with Windows DPAPI Support.

Upgrades from Fernet-based encryption to Windows Data Protection API (DPAPI)
for machine+user specific encryption. Includes automatic migration from legacy format.
"""

import json
import base64
import platform
from typing import Dict, Any, Optional

# Logger import (conditional to avoid circular dependency)
try:
    from .logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    # Fallback during initialization
    import logging
    logger = logging.getLogger(__name__)


# Check if we're on Windows
IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    try:
        # Windows DPAPI via cryptography library
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        import win32crypt  # pywin32 for DPAPI
        DPAPI_AVAILABLE = True
    except ImportError:
        DPAPI_AVAILABLE = False
        logger.warning("DPAPI not available - falling back to Fernet", extra={"context": {"platform": platform.system()}})
else:
    DPAPI_AVAILABLE = False

# Fallback to Fernet for non-Windows or if DPAPI unavailable
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import hashlib


class DPAPIEncryptor:
    """Windows DPAPI-based encryption for API keys."""
    
    MAGIC_HEADER = b"DPAPI_V1:"  # Marker for DPAPI-encrypted data
    
    def __init__(self):
        """Initialize DPAPI encryptor."""
        if not IS_WINDOWS or not DPAPI_AVAILABLE:
            raise RuntimeError("DPAPI only available on Windows with pywin32 installed")
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt data using Windows DPAPI.
        
        Args:
            plaintext: Data to encrypt
        
        Returns:
            Base64-encoded encrypted data with header
        """
        try:
            # Convert to bytes
            plaintext_bytes = plaintext.encode('utf-8')
            
            # Encrypt using DPAPI (machine+user specific)
            encrypted_bytes = win32crypt.CryptProtectData(
                plaintext_bytes,
                u"SentinelX API Key",  # Description
                None,  # Optional entropy (we don't use it)
                None,  # Reserved
                None,  # Prompt struct
                0  # Flags (0 = default, user-specific)
            )
            
            # Add magic header + base64 encode
            marked_data = self.MAGIC_HEADER + encrypted_bytes
            return base64.b64encode(marked_data).decode('ascii')
            
        except Exception as e:
            raise RuntimeError(f"DPAPI encryption failed: {e}")
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt DPAPI-encrypted data.
        
        Args:
            ciphertext: Base64-encoded encrypted data
        
        Returns:
            Decrypted plaintext
        """
        try:
            # Decode base64
            marked_data = base64.b64decode(ciphertext.encode('ascii'))
            
            # Verify magic header
            if not marked_data.startswith(self.MAGIC_HEADER):
                raise ValueError("Invalid DPAPI data (missing header)")
            
            # Remove header
            encrypted_bytes = marked_data[len(self.MAGIC_HEADER):]
            
            # Decrypt using DPAPI
            decrypted_bytes = win32crypt.CryptUnprotectData(
                encrypted_bytes,
                None,  # Optional entropy
                None,  # Reserved
                None,  # Prompt struct
                0  # Flags
            )[1]  # Returns (description, decrypted_data)
            
            return decrypted_bytes.decode('utf-8')
            
        except Exception as e:
            raise RuntimeError(f"DPAPI decryption failed: {e}")
    
    def is_dpapi_encrypted(self, data: str) -> bool:
        """Check if data is DPAPI-encrypted (has magic header)."""
        try:
            decoded = base64.b64decode(data.encode('ascii'))
            return decoded.startswith(self.MAGIC_HEADER)
        except Exception:
            return False


class FernetEncryptor:
    """Legacy Fernet-based encryption (fallback for non-Windows)."""
    
    ENCRYPTED_KEYS = ["api_keys"]
    
    def __init__(self):
        """Initialize Fernet encryptor with machine-derived key."""
        salt = self._get_salt()
        key = self._derive_encryption_key(salt)
        self.fernet = Fernet(key)
    
    @staticmethod
    def _get_machine_id() -> str:
        """Get machine-specific identifier."""
        import subprocess
        
        machine_uuid = ""
        
        if platform.system() == "Windows":
            try:
                cmd = "wmic csproduct get uuid"
                output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL)
                machine_uuid = output.decode().split('\n')[1].strip()
            except Exception:
                pass
        elif platform.system() == "Linux":
            try:
                with open('/etc/machine-id', 'r') as f:
                    machine_uuid = f.read().strip()
            except Exception:
                try:
                    with open('/var/lib/dbus/machine-id', 'r') as f:
                        machine_uuid = f.read().strip()
                except Exception:
                    pass
        
        if not machine_uuid:
            machine_uuid = platform.node()
        
        combined = f"{machine_uuid}-{platform.node()}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    @staticmethod
    def _get_salt() -> bytes:
        """Get or create encryption salt."""
        import os
        from pathlib import Path
        
        # Try to use AppData path
        try:
            from .appdata import get_appdata_path
            salt_file = Path(get_appdata_path("config/.salt"))
        except Exception:
            salt_file = Path(".salt")
        
        if salt_file.exists():
            with open(salt_file, 'rb') as f:
                return f.read()
        else:
            salt = os.urandom(16)
            salt_file.parent.mkdir(parents=True, exist_ok=True)
            with open(salt_file, 'wb') as f:
                f.write(salt)
            return salt
    
    @staticmethod
    def _derive_encryption_key(salt: bytes) -> bytes:
        """Derive encryption key using PBKDF2."""
        machine_id = FernetEncryptor._get_machine_id()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = kdf.derive(machine_id.encode())
        return base64.urlsafe_b64encode(key)
    
    def encrypt_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive config sections."""
        encrypted_config = config.copy()
        
        for section in self.ENCRYPTED_KEYS:
            if section in encrypted_config:
                plaintext = json.dumps(encrypted_config[section])
                ciphertext = self.fernet.encrypt(plaintext.encode())
                
                encrypted_config[section] = {
                    "_encrypted": True,
                    "data": ciphertext.decode('utf-8')
                }
        
        return encrypted_config
    
    def decrypt_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt config sections."""
        decrypted_config = config.copy()
        
        for section in self.ENCRYPTED_KEYS:
            if section in decrypted_config and isinstance(decrypted_config[section], dict):
                if decrypted_config[section].get("_encrypted"):
                    try:
                        ciphertext = decrypted_config[section]["data"].encode('utf-8')
                        plaintext = self.fernet.decrypt(ciphertext).decode('utf-8')
                        decrypted_config[section] = json.loads(plaintext)
                    except Exception as e:
                        logger.error(f"Decryption failed for {section}: {e}", extra={"context": {"section": section, "error": str(e)}})
                        decrypted_config[section] = {}
        
        return decrypted_config
    
    def is_encrypted(self, config: Dict[str, Any]) -> bool:
        """Check if config has encrypted sections."""
        for section in self.ENCRYPTED_KEYS:
            if section in config and isinstance(config[section], dict):
                if config[section].get("_encrypted"):
                    return True
        return False


class ConfigEncryptor:
    """
    Unified config encryptor with DPAPI support and migration.
    
    - Windows + DPAPI available: Use DPAPI
    - Otherwise: Use Fernet (machine-specific)
    - Auto-migrate from Fernet to DPAPI on Windows
    """
    
    ENCRYPTED_KEYS = ["api_keys"]
    
    def __init__(self):
        """Initialize encryptor (DPAPI if available, else Fernet)."""
        self.use_dpapi = IS_WINDOWS and DPAPI_AVAILABLE
        
        if self.use_dpapi:
            self.dpapi = DPAPIEncryptor()
            logger.info("Using Windows DPAPI encryption")
        else:
            self.fernet_enc = FernetEncryptor()
            logger.info("Using Fernet encryption (fallback)")
    
    def encrypt_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt sensitive config sections.
        
        Args:
            config: Configuration dictionary
        
        Returns:
            Config with encrypted sections
        """
        if self.use_dpapi:
            return self._encrypt_with_dpapi(config)
        else:
            return self.fernet_enc.encrypt_config(config)
    
    def decrypt_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt config sections (auto-detects format).
        
        Args:
            config: Configuration dictionary
        
        Returns:
            Config with decrypted sections
        """
        # Detect encryption format
        if self._is_dpapi_encrypted(config):
            return self._decrypt_with_dpapi(config)
        elif self._is_fernet_encrypted(config):
            if self.use_dpapi:
                # Migrate from Fernet to DPAPI
                logger.info("Migrating from Fernet to DPAPI...")
                return self._migrate_to_dpapi(config)
            else:
                return self.fernet_enc.decrypt_config(config)
        else:
            # Not encrypted
            return config
    
    def is_encrypted(self, config: Dict[str, Any]) -> bool:
        """Check if config is encrypted."""
        return self._is_dpapi_encrypted(config) or self._is_fernet_encrypted(config)
    
    # === DPAPI Methods ===
    
    def _encrypt_with_dpapi(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt config using DPAPI."""
        encrypted_config = config.copy()
        
        for section in self.ENCRYPTED_KEYS:
            if section in encrypted_config:
                plaintext = json.dumps(encrypted_config[section])
                ciphertext = self.dpapi.encrypt(plaintext)
                
                encrypted_config[section] = {
                    "_encrypted": "dpapi_v1",
                    "data": ciphertext
                }
        
        return encrypted_config
    
    def _decrypt_with_dpapi(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt DPAPI-encrypted config."""
        decrypted_config = config.copy()
        
        for section in self.ENCRYPTED_KEYS:
            if section in decrypted_config and isinstance(decrypted_config[section], dict):
                if decrypted_config[section].get("_encrypted") == "dpapi_v1":
                    try:
                        ciphertext = decrypted_config[section]["data"]
                        plaintext = self.dpapi.decrypt(ciphertext)
                        decrypted_config[section] = json.loads(plaintext)
                    except Exception as e:
                        logger.error(f"DPAPI decryption failed for {section}: {e}", extra={"context": {"section": section, "error": str(e)}})
                        decrypted_config[section] = {}
        
        return decrypted_config
    
    def _is_dpapi_encrypted(self, config: Dict[str, Any]) -> bool:
        """Check if config uses DPAPI encryption."""
        for section in self.ENCRYPTED_KEYS:
            if section in config and isinstance(config[section], dict):
                if config[section].get("_encrypted") == "dpapi_v1":
                    return True
        return False
    
    # === Fernet Methods ===
    
    def _is_fernet_encrypted(self, config: Dict[str, Any]) -> bool:
        """Check if config uses Fernet encryption."""
        for section in self.ENCRYPTED_KEYS:
            if section in config and isinstance(config[section], dict):
                if config[section].get("_encrypted") is True:
                    return True
        return False
    
    def _migrate_to_dpapi(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate config from Fernet to DPAPI."""
        # Decrypt with Fernet
        decrypted = self.fernet_enc.decrypt_config(config)
        
        # Re-encrypt with DPAPI
        migrated = self._encrypt_with_dpapi(decrypted)
        
        logger.info("Migration to DPAPI complete")
        return migrated


# Global singleton
_encryptor: Optional[ConfigEncryptor] = None


def get_encryptor() -> ConfigEncryptor:
    """Get global encryptor instance (singleton)."""
    global _encryptor
    
    if _encryptor is None:
        _encryptor = ConfigEncryptor()
    
    return _encryptor
