"""
License Key Management System for Sentinel-X
Supports LIFETIME PRO licenses with strict hardware-locking
"""

import hashlib
import json
import secrets
import time
import os
from typing import Dict, Optional, Tuple
from core.encryption import get_encryptor
import platform
import subprocess

class LicenseManager:
    """Manages license generation, validation, and enforcement."""
    
    KEY_PREFIX = "SNTL-X"
    LICENSE_FILE = "config/license.enc"
    TRIAL_DAYS = 7
    LIFETIME_FLAG = 2147483647  # Max int (year 2038)
    
    TIERS = {
        "TRIAL": {
            "name": "Trial", 
            "features": ["basic", "demo_only"], 
            "max_trades": 50,
            "days": TRIAL_DAYS
        },
        "PRO": {
            "name": "Professional", 
            "features": ["basic", "advanced", "unlimited"], 
            "max_trades": 0,
            "days": LIFETIME_FLAG
        },
        "ENTERPRISE": {
            "name": "Enterprise", 
            "features": ["all", "white_label", "support"], 
            "max_trades": 0,
            "days": LIFETIME_FLAG
        }
    }
    
    def __init__(self):
        self.encryptor = get_encryptor()
        self.hardware_id = self._generate_hardware_id()
        
    def _generate_hardware_id(self) -> str:
        """Generate unique hardware fingerprint."""
        if platform.system() == "Windows":
            try:
                cmd = "wmic csproduct get uuid"
                output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL)
                machine_uuid = output.decode().split('\n')[1].strip()
            except:
                machine_uuid = ""
        else:
            machine_uuid = platform.node()
        
        if not machine_uuid:
            machine_uuid = platform.node()
        
        system_data = f"{machine_uuid}-{platform.node()}-{platform.processor()}-{platform.system()}"
        return hashlib.sha256(system_data.encode()).hexdigest()
    
    def generate_license_key(self, tier: str = "PRO") -> str:
        """Generate a license key."""
        random_part = secrets.token_hex(8).upper()
        return f"{self.KEY_PREFIX}-{random_part[:4]}-{random_part[4:8]}-{random_part[8:12]}-{random_part[12:16]}"
    
    def create_license_data(self, license_key: str, tier: str = "TRIAL", days: int = None) -> Dict:
        """Create complete license data with metadata."""
        tier_info = self.TIERS.get(tier, self.TIERS["TRIAL"])
        issued_at = int(time.time())
        
        if days is not None:
            expires_at = issued_at + (days * 86400)
        elif tier in ["PRO", "ENTERPRISE"]:
            expires_at = self.LIFETIME_FLAG
        else:
            expires_at = issued_at + (tier_info["days"] * 86400)
        
        license_data = {
            "key": license_key,
            "tier": tier,
            "hardware_id": self._get_hardware_id_for_tier(tier),
            "issued_at": issued_at,
            "expires_at": expires_at,
            "features": tier_info["features"],
            "max_trades": tier_info["max_trades"],
            "signature": ""
        }
        
        signature_data = f"{license_key}{tier}{license_data['hardware_id']}{expires_at}"
        license_data["signature"] = hashlib.sha256(signature_data.encode()).hexdigest()
        
        return license_data
    
    def _get_hardware_id_for_tier(self, tier: str) -> str:
        """Get hardware_id based on tier. TRIAL can be generic, others are strict."""
        if tier == "TRIAL":
            return f"TRIAL_MODE-{self.hardware_id[:16]}"
        return self.hardware_id
    
    def validate_license(self, license_data: Dict) -> Tuple[bool, str]:
        """Validate license integrity, expiry, and hardware-lock."""
        if not license_data:
            return False, "No license data"
        
        current_time = int(time.time())
        expires_at = license_data.get("expires_at", 0)
        
        if expires_at != self.LIFETIME_FLAG and current_time > expires_at:
            return False, "License expired"
        
        signature_data = f"{license_data['key']}{license_data['tier']}{license_data['hardware_id']}{expires_at}"
        expected_signature = hashlib.sha256(signature_data.encode()).hexdigest()
        
        if license_data.get("signature") != expected_signature:
            return False, "License corrupted (signature invalid)"
        
        tier = license_data.get("tier")
        
        if tier not in self.TIERS:
            return False, f"Invalid license tier: {tier}"
        
        # STRICT HARDWARE LOCKING: Every tier except TRIAL
        expected_hw_id = self._get_hardware_id_for_tier(tier)
        
        if tier == "TRIAL":
            # TRIAL: Can run on 1 device, but GENERIC ID (allows 1 reinstall)
            if not license_data.get("hardware_id", "").startswith("TRIAL_MODE-"):
                return False, "Trial license corrupted"
        elif tier in ["PRO", "ENTERPRISE"]:
            # PRO/ENTERPRISE: STRICT machine lock
            stored_hw_id = license_data.get("hardware_id")
            if stored_hw_id != expected_hw_id:
                return False, f"License not valid for this machine. Hardware ID mismatch.\nExpected: {expected_hw_id[:16]}...\nGot: {stored_hw_id[:16] if stored_hw_id else 'None'}"
        
        return True, "Valid"
    
    def is_lifetime(self, license_data: Dict) -> bool:
        """Check if license is lifetime."""
        return license_data.get("expires_at") == self.LIFETIME_FLAG
    
    def save_license(self, license_data: Dict) -> bool:
        """Save license to encrypted file."""
        try:
            os.makedirs("config", exist_ok=True)
            
            encrypted_config = self.encryptor.encrypt_config({"license": license_data})
            final_config = encrypted_config
            
            with open(self.LICENSE_FILE, 'w') as f:
                json.dump(final_config, f, indent=2)
            
            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False
    
    def load_license(self) -> Optional[Dict]:
        """Load license from encrypted file."""
        try:
            if not os.path.exists(self.LICENSE_FILE):
                return None
            
            with open(self.LICENSE_FILE, 'r') as f:
                encrypted_config = json.load(f)
            
            config = self.encryptor.decrypt_config(encrypted_config)
            return config.get("license")
        except Exception as e:
            import traceback
            traceback.print_exc()
            return None
            
            with open(self.LICENSE_FILE, 'r') as f:
                encrypted = json.load(f)
            
            if "_encrypted" in encrypted and encrypted["_encrypted"]:
                config = self.encryptor.decrypt_config(encrypted)
                return config.get("license")
            return encrypted.get("license")
        except Exception:
            return None
    
    def get_license_status(self) -> Dict:
        """Get current license status."""
        license_data = self.load_license()
        
        if not license_data:
            return {
                "status": "NOT_ACTIVATED",
                "message": "No license activated",
                "tier": "NONE",
                "days_remaining": 0,
                "expires_text": "Not activated"
            }
        
        is_valid, message = self.validate_license(license_data)
        
        if not is_valid:
            return {
                "status": "INVALID",
                "message": message,
                "tier": license_data.get("tier", "UNKNOWN"),
                "days_remaining": 0,
                "expires_text": "Invalid"
            }
        
        tier = license_data.get("tier", "UNKNOWN")
        expires_at = license_data.get("expires_at", 0)
        
        is_lifetime = self.is_lifetime(license_data)
        
        if is_lifetime:
            days_remaining = -1
            expires_text = "Lifetime"
        else:
            current_time = int(time.time())
            days_remaining = max(0, (expires_at - current_time) // 86400)
            expires_text = f"{days_remaining} days"
        
        return {
            "status": "ACTIVE",
            "message": message,
            "tier": tier,
            "days_remaining": days_remaining,
            "expires_text": expires_text,
            "is_lifetime": is_lifetime,
            "features": license_data.get("features", []),
            "max_trades": license_data.get("max_trades", 0),
            "hardware_id": license_data.get("hardware_id", "")
        }
        
        is_valid, message = self.validate_license(license_data)
        
        if not is_valid:
            return {
                "status": "INVALID",
                "message": message,
                "tier": license_data.get("tier", "UNKNOWN"),
                "days_remaining": 0
            }
        
        tier = license_data.get("tier", "UNKNOWN")
        expires_at = license_data.get("expires_at", 0)
        
        if self.is_lifetime(license_data):
            days_remaining = -1  # Lifetime flag
            expires_text = "Lifetime"
        else:
            current_time = int(time.time())
            days_remaining = (expires_at - current_time) // 86400
            days_remaining = max(0, days_remaining)
            expires_text = f"{days_remaining} days"
        
        return {
            "status": "ACTIVE",
            "message": message,
            "tier": tier,
            "days_remaining": days_remaining,
            "expires_text": expires_text,
            "features": license_data.get("features", []),
            "max_trades": license_data.get("max_trades", 0),
            "hardware_id": license_data.get("hardware_id", "")
        }
    
    def activate_trial(self) -> bool:
        """Activate trial license."""
        license_key = self.generate_license_key("TRIAL")
        license_data = self.create_license_data(license_key, "TRIAL")
        return self.save_license(license_data)
    
    def activate_license(self, license_key: str, tier: str = "PRO") -> Tuple[bool, str]:
        """Activate a purchased license key."""
        if not license_key.startswith(self.KEY_PREFIX + "-"):
            return False, "Invalid license key format"
        
        license_data = self.create_license_data(license_key, tier)
        
        if self.save_license(license_data):
            tier_name = self.TIERS.get(tier, {}).get("name", tier)
            return True, f"{tier_name} license activated successfully"
        else:
            return False, "Failed to save license"
    
    def deactivate_license(self) -> bool:
        """Deactivate license (remove from device)."""
        try:
            if os.path.exists(self.LICENSE_FILE):
                os.remove(self.LICENSE_FILE)
                return True
            return False
        except Exception:
            return False
    
    def migrate_to_hardware_id(self, tier: str) -> bool:
        """Migrate trial to hardware-locked license."""
        license_data = self.load_license()
        
        if not license_data or license_data.get("tier") != "TRIAL":
            return False
        
        license_data["tier"] = tier
        license_data["hardware_id"] = self.hardware_id
        license_data["expires_at"] = self.LIFETIME_FLAG
        
        signature_data = f"{license_data['key']}{tier}{self.hardware_id}{license_data['expires_at']}"
        license_data["signature"] = hashlib.sha256(signature_data.encode()).hexdigest()
        
        return self.save_license(license_data)
