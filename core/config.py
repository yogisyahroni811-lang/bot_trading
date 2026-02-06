import json
import os
from typing import Dict, Any
from .encryption import get_encryptor
from .appdata import get_appdata_path
from .logger import get_logger

logger = get_logger(__name__)

CONFIG_PATH = get_appdata_path("config/config.json")

DEFAULT_CONFIG = {
    "server": {
        "port": 8000,
        "shared_secret": "SentinelX-Secret-Key"
    },
    "llm": {
        "provider": "groq",
        "model": "mixtral-8x7b-32768",
        "base_url": "",
        "temperature": 0.1,
        "max_tokens": 4096,
        "timeout": 20
    },
    "api_keys": {
        "gemini": "",
        "groq": "",
        "openai": "",
        "anthropic": "",
        "openrouter": ""
    },
    "logging": {
        "level": "INFO",
        "console_output": True,
        "max_file_size_mb": 10
    },
    "trading": {
        "timeframes": ["H1", "H4"],
        "candles_limit": 100,
        "min_conf": 0.6,
        "max_spread": 30.0,
        "cooldown_minutes": 15,
        "max_hold_bars": 99999,
        "sl_tp_mode": "ai",
        "fixed_sl": 5.0,
        "fixed_tp": 7.0,
        "atr_sl_multiplier": 1.5,
        "atr_tp_multiplier": 2.0,
        "timezone": "Asia/Jakarta",
        "block_ranges": "19:00-20:00",
        "strategy_mode": "SAFE"  # Custom Mode state
    },
    "ai_prompt": {
        "mode": "template",  # check "template" or "custom"
        "template_name": "standard",
        "custom_prompt": "Analyze the market structure..."
    },
    "payload": {
        "data_mode": "compact",
        "tail_n": 5,
        "tail_tf": "H1"
    },
    "notifications": {
        "telegram_enabled": False,
        "bot_token": "",
        "chat_id": ""
    }
}

class ConfigManager:
    """
    Configuration manager with built-in encryption for sensitive data.
    
    API keys are automatically encrypted when saved and decrypted when loaded.
    Encryption uses machine-specific keys to prevent config portability.
    """
    
    @staticmethod
    def load_config() -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Automatically decrypts API keys if they are encrypted.
        Creates default config if file doesn't exist.
        
        Returns:
            Configuration dictionary with decrypted sensitive data
        """
        if not os.path.exists(CONFIG_PATH):
            ConfigManager.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
        
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            # Decrypt sensitive sections if encrypted
            encryptor = get_encryptor()
            if encryptor.is_encrypted(config):
                config = encryptor.decrypt_config(config)
            
            return config
            
        except Exception as e:
            logger.error(f"Error loading config: {e}. Using defaults.", extra={"context": {"error": str(e)}})
            return DEFAULT_CONFIG

    @staticmethod
    def save_config(config: Dict[str, Any], encrypt: bool = True):
        """
        Save configuration to file.
        
        Args:
            config: Configuration dictionary
            encrypt: If True, encrypt sensitive sections (default: True)
        """
        try:
            # Encrypt sensitive sections before saving
            if encrypt:
                encryptor = get_encryptor()
                config_to_save = encryptor.encrypt_config(config)
            else:
                config_to_save = config
            
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config_to_save, f, indent=4)
                
        except Exception as e:
            logger.error(f"Error saving config: {e}", extra={"context": {"error": str(e)}})
    
    @staticmethod
    def get_api_key(provider: str) -> str:
        """
        Safely get API key for a specific provider.
        
        Args:
            provider: Provider name (e.g., 'openai', 'groq')
            
        Returns:
            API key string (empty if not found)
        """
        config = ConfigManager.load_config()
        return config.get('api_keys', {}).get(provider, '')
    
    @staticmethod
    def set_api_key(provider: str, key: str):
        """
        Set API key for a specific provider and save (encrypted).
        
        Args:
            provider: Provider name
            key: API key value
        """
        config = ConfigManager.load_config()
        if 'api_keys' not in config:
            config['api_keys'] = {}
        
        config['api_keys'][provider] = key
        ConfigManager.save_config(config, encrypt=True)
