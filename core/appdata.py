"""
User Data Directory Manager for Sentinel-X.

Manages application data location in %APPDATA%\SentinelX\ on Windows.
Handles migration from old exe-based storage to proper app data directory.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Optional


class AppDataManager:
    """Manages user data directory location and migration."""
    
    # Application identifier
    APP_NAME = "SentinelX"
    
    # Subdirectories
    SUBDIRS = [
        "config",      # Configuration files
        "database",    # SQLite databases
        "logs",        # Application logs
        "chroma_db",   # Vector store
        "knowledge",   # RAG knowledge base
        "backups",     # Configuration backups
    ]
    
    def __init__(self):
        """Initialize AppData manager."""
        self.app_data_dir = self._get_app_data_directory()
        self._ensure_directories_exist()
    
    def _get_app_data_directory(self) -> Path:
        r"""
        Get platform-specific application data directory.
        
        Returns:
            Path to %APPDATA%\SentinelX\ on Windows
        """
        if sys.platform == "win32":
            # Windows: %APPDATA%\SentinelX
            appdata = os.getenv("APPDATA")
            if not appdata:
                raise EnvironmentError("APPDATA environment variable not found")
            return Path(appdata) / self.APP_NAME
        else:
            # Fallback for non-Windows (should not happen for this app)
            home = Path.home()
            return home / f".{self.APP_NAME.lower()}"
    
    def _ensure_directories_exist(self):
        """Create application data directories if they don't exist."""
        for subdir in self.SUBDIRS:
            dir_path = self.app_data_dir / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def get_path(self, relative_path: str) -> Path:
        """
        Get full path for a file in application data directory.
        
        Args:
            relative_path: Relative path from app data root (e.g., "config/config.json")
        
        Returns:
            Absolute path in application data directory
        """
        return self.app_data_dir / relative_path
    
    def detect_legacy_files(self) -> dict:
        """
        Detect files in old location (exe directory).
        
        Returns:
            Dictionary of {filename: old_path} for files requiring migration
        """
        legacy_files = {}
        
        # Get executable directory (or current directory if not frozen)
        if getattr(sys, 'frozen', False):
            exe_dir = Path(sys.executable).parent
        else:
            exe_dir = Path.cwd()
        
        # Check for legacy files
        legacy_candidates = [
            "config.json",
            "trade_history.db",
            "chroma_db",  # Directory
            "knowledge",  # Directory
        ]
        
        for candidate in legacy_candidates:
            old_path = exe_dir / candidate
            if old_path.exists():
                legacy_files[candidate] = old_path
        
        return legacy_files
    
    def migrate_legacy_data(self, legacy_files: dict, create_backup: bool = True) -> bool:
        """
        Migrate data from old location to new AppData directory.
        
        Args:
            legacy_files: Dictionary from detect_legacy_files()
            create_backup: Whether to backup before migration
        
        Returns:
            True if migration successful
        """
        logger.info("Starting data migration from exe directory to AppData")
        
        if create_backup:
            self._create_backup(legacy_files)
        
        migrated_count = 0
        
        for filename, old_path in legacy_files.items():
            try:
                # Determine new location
                if filename == "config.json":
                    new_path = self.get_path("config/config.json")
                elif filename == "trade_history.db":
                    new_path = self.get_path("database/trade_history.db")
                elif filename == "chroma_db":
                    new_path = self.get_path("chroma_db")
                elif filename == "knowledge":
                    new_path = self.get_path("knowledge")
                else:
                    continue
                
                # Skip if already exists in new location
                if new_path.exists():
                    logger.info(f"Skipped migration for {filename} (already exists in target)")
                    continue
                
                # Copy file or directory
                if old_path.is_dir():
                    shutil.copytree(old_path, new_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(old_path, new_path)
                
                logger.info(f"Migrated {filename}", extra={"context": {"source": str(source_path), "dest": str(dest_path)}})
                migrated_count += 1
                
            except Exception as e:
                logger.error(f"Failed to migrate {filename}: {e}", extra={"context": {"file": filename, "error": str(e)}})
                return False
        
        logger.info(f"Migration complete: migrated {migrated_count} item(s)")
        return True
    
    def _create_backup(self, legacy_files: dict):
        """Create backup of legacy files before migration."""
        import datetime
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.get_path(f"backups/migration_{timestamp}")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Creating migration backup: {backup_dir}")
        
        for filename, old_path in legacy_files.items():
            try:
                backup_path = backup_dir / filename
                
                if old_path.is_dir():
                    shutil.copytree(old_path, backup_path)
                else:
                    shutil.copy2(old_path, backup_path)
                
                logger.info(f"Backed up {filename}")
            except Exception as e:
                logger.warning(f"Backup failed for {filename}: {e}", extra={"context": {"file": filename, "error": str(e)}})
    
    def should_show_migration_wizard(self) -> bool:
        """
        Check if migration wizard should be shown.
        
        Returns:
            True if legacy files exist and migration not yet done
        """
        legacy_files = self.detect_legacy_files()
        
        # Show wizard if legacy files exist
        if legacy_files:
            # Check if main config already migrated
            new_config = self.get_path("config/config.json")
            if not new_config.exists():
                return True
        
        return False


# Global singleton instance
_app_data_manager: Optional[AppDataManager] = None


def get_app_data_manager() -> AppDataManager:
    """
    Get global AppDataManager instance (singleton).
    
    Returns:
        AppDataManager instance
    """
    global _app_data_manager
    
    if _app_data_manager is None:
        _app_data_manager = AppDataManager()
    
    return _app_data_manager


def get_appdata_path(relative_path: str) -> str:
    """
    Convenience function to get application data path.
    
    Args:
        relative_path: Relative path from app data root
    
    Returns:
        Absolute path as string
    """
    manager = get_app_data_manager()
    return str(manager.get_path(relative_path))


# Example usage in other modules:
# from core.appdata import get_appdata_path
# CONFIG_PATH = get_appdata_path("config/config.json")
# DB_PATH = get_appdata_path("database/trade_history.db")
