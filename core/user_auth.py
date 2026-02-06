"""
User Authentication System for Sentinel-X
Handles login, registration, and session management
"""

import hashlib
import json
import os
import secrets
import time
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from core.encryption import get_encryptor
from core.license_manager import LicenseManager

class UserAuth:
    """Manages user authentication and registration."""
    
    USERS_FILE = "config/users.enc"
    SESSION_FILE = "config/session.enc"
    SESSION_DURATION_HOURS = 24
    
    def __init__(self):
        self.encryptor = get_encryptor()
        self.license_manager = LicenseManager()
    
    def _hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """Hash password with salt using PBKDF2."""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # PBKDF2 with SHA256
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )
        
        return key.hex(), salt
    
    def _verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """Verify password against stored hash."""
        computed_hash, _ = self._hash_password(password, salt)
        return computed_hash == stored_hash
    
    def _load_users(self) -> Dict:
        """Load users from encrypted storage."""
        try:
            if not os.path.exists(self.USERS_FILE):
                return {}
            
            with open(self.USERS_FILE, 'r') as f:
                encrypted_config = json.load(f)
            
            config = self.encryptor.decrypt_config(encrypted_config)
            return config.get("users", {})
        except Exception as e:
            print(f"Failed to load users: {e}")
            return {}
    
    def _save_users(self, users: Dict) -> bool:
        """Save users to encrypted storage."""
        try:
            os.makedirs("config", exist_ok=True)
            
            config = {"users": users}
            encrypted_config = self.encryptor.encrypt_config(config)
            
            with open(self.USERS_FILE, 'w') as f:
                json.dump(encrypted_config, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Failed to save users: {e}")
            return False
    
    def is_first_run(self) -> bool:
        """Check if this is first time (no users registered)."""
        users = self._load_users()
        return len(users) == 0
    
    def register_user(self, email: str, password: str, license_key: str) -> Tuple[bool, str]:
        """
        Register new user with license validation.
        
        Returns:
            (success: bool, message: str)
        """
        # Validate inputs
        if not email or '@' not in email:
            return False, "Invalid email address"
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        
        if not license_key.startswith("SNTL-X-"):
            return False, "Invalid license key format"
        
        # Check if email already registered
        users = self._load_users()
        if email in users:
            return False, "Email already registered. Please login instead."
        
        # Validate license
        try:
            license_manager = LicenseManager()
            # Activate license first
            success, msg = license_manager.activate_license(license_key)
            
            if not success:
                return False, f"Invalid license: {msg}"
            
            # Get license status
            license_status = license_manager.get_license_status()
            if license_status["status"] != "ACTIVE":
                return False, "License activation failed"
            
        except Exception as e:
            return False, f"License validation error: {e}"
        
        # Hash password
        password_hash, salt = self._hash_password(password)
        
        # Create user record
        user_id = secrets.token_hex(8)
        user_data = {
            "user_id": user_id,
            "email": email.lower(),
            "password_hash": password_hash,
            "salt": salt,
            "license_key": license_key,
            "license_tier": license_status["tier"],
            "registered_at": int(time.time()),
            "last_login": None,
            "login_count": 0,
            "is_active": True
        }
        
        # Save user
        users[email.lower()] = user_data
        if not self._save_users(users):
            return False, "Failed to save user data"
        
        # Create session
        self._create_session(user_id, email)
        
        return True, f"Registration successful! Welcome to Sentinel-X {license_status['tier']}"
    
    def login_user(self, email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Login existing user.
        
        Returns:
            (success: bool, message: str, user_data: dict or None)
        """
        if not email or not password:
            return False, "Please enter email and password", None
        
        # Load user
        users = self._load_users()
        user = users.get(email.lower())
        
        if not user:
            return False, "Email not found. Please register first.", None
        
        if not user.get("is_active", True):
            return False, "Account deactivated. Contact support.", None
        
        # Verify password
        stored_hash = user["password_hash"]
        salt = user["salt"]
        
        if not self._verify_password(password, stored_hash, salt):
            return False, "Incorrect password", None
        
        # Update last login
        user["last_login"] = int(time.time())
        user["login_count"] = user.get("login_count", 0) + 1
        users[email.lower()] = user
        self._save_users(users)
        
        # Create session
        self._create_session(user["user_id"], email)
        
        # Return user info (without sensitive data)
        safe_user = {
            "user_id": user["user_id"],
            "email": user["email"],
            "license_tier": user["license_tier"],
            "registered_at": user["registered_at"]
        }
        
        return True, "Login successful!", safe_user
    
    def _create_session(self, user_id: str, email: str):
        """Create login session."""
        try:
            session = {
                "user_id": user_id,
                "email": email,
                "created_at": int(time.time()),
                "expires_at": int(time.time()) + (self.SESSION_DURATION_HOURS * 3600),
                "is_active": True
            }
            
            config = {"session": session}
            encrypted_config = self.encryptor.encrypt_config(config)
            
            with open(self.SESSION_FILE, 'w') as f:
                json.dump(encrypted_config, f)
                
        except Exception as e:
            print(f"Failed to create session: {e}")
    
    def get_current_session(self) -> Optional[Dict]:
        """Get current active session."""
        try:
            if not os.path.exists(self.SESSION_FILE):
                return None
            
            with open(self.SESSION_FILE, 'r') as f:
                encrypted_config = json.load(f)
            
            config = self.encryptor.decrypt_config(encrypted_config)
            session = config.get("session")
            
            if not session:
                return None
            
            # Check if expired
            if session.get("expires_at", 0) < int(time.time()):
                return None
            
            return session if session.get("is_active") else None
            
        except Exception as e:
            print(f"Failed to get session: {e}")
            return None
    
    def logout(self):
        """Logout current user."""
        try:
            if os.path.exists(self.SESSION_FILE):
                os.remove(self.SESSION_FILE)
            return True
        except Exception as e:
            print(f"Logout error: {e}")
            return False
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user data by email."""
        users = self._load_users()
        return users.get(email.lower())
    
    def change_password(self, email: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Change user password."""
        if len(new_password) < 8:
            return False, "New password must be at least 8 characters"
        
        # Verify old password
        success, msg, user = self.login_user(email, old_password)
        if not success:
            return False, "Current password is incorrect"
        
        # Load users
        users = self._load_users()
        user_data = users.get(email.lower())
        
        if not user_data:
            return False, "User not found"
        
        # Update password
        new_hash, new_salt = self._hash_password(new_password)
        user_data["password_hash"] = new_hash
        user_data["salt"] = new_salt
        
        users[email.lower()] = user_data
        if self._save_users(users):
            return True, "Password changed successfully"
        else:
            return False, "Failed to save new password"


# Singleton instance
_user_auth_instance = None

def get_user_auth() -> UserAuth:
    """Get global UserAuth instance (singleton)."""
    global _user_auth_instance
    if _user_auth_instance is None:
        _user_auth_instance = UserAuth()
    return _user_auth_instance