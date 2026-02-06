"""
Global Exception Handler and Crash Reporter for Sentinel-X.

Captures unhandled exceptions, logs crash dumps, and shows user-friendly error dialogs.
"""

import sys
import traceback
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional
import threading
from tkinter import messagebox
from core.notifications import send_telegram_alert_sync
from core.logger import get_logger

logger = get_logger(__name__)


class CrashHandler:
    """Handles unhandled exceptions and crash reporting."""
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize crash handler.
        
        Args:
            log_dir: Directory to store crash logs (defaults to AppData/logs)
        """
        if log_dir is None:
            from .appdata import get_appdata_path
            self.log_dir = Path(get_appdata_path("logs"))
        else:
            self.log_dir = log_dir
        
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Store original exception hook
        self.original_excepthook = sys.excepthook
    
    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """
        Custom exception handler that logs crash and shows dialog.
        
        Args:
            exc_type: Exception class
            exc_value: Exception instance
            exc_traceback: Traceback object
        """
        # Skip keyboard interrupt (user-initiated)
        if issubclass(exc_type, KeyboardInterrupt):
            self.original_excepthook(exc_type, exc_value, exc_traceback)
            return
        
        # Generate crash dump
        crash_info = self._generate_crash_dump(exc_type, exc_value, exc_traceback)
        
        # Write to log file
        log_file = self._write_crash_log(crash_info)
        
        # Print to console (for debugging)
        print("\n" + "=" * 60)
        print("FATAL ERROR - APPLICATION CRASHED")
        print("=" * 60)
        print(crash_info)
        print(f"\nCrash log saved to: {log_file}")
        print("=" * 60)
        
        # Show user-friendly dialog (GUI-safe)
        self._show_error_dialog(crash_info, log_file)
        
        # Try to send Telegram alert
        try:
            send_telegram_alert_sync(f"🚨 **FATAL CRASH DETECTED**\n\n```\n{exc_type.__name__}: {exc_value}\n```\nSee logs for details.")
        except:
            pass
        
        # Call original hook (for proper cleanup)
        self.original_excepthook(exc_type, exc_value, exc_traceback)
    
    def _generate_crash_dump(self, exc_type, exc_value, exc_traceback) -> str:
        """Generate comprehensive crash dump information."""
        lines = []
        
        lines.append("=" * 60)
        lines.append("SENTINEL-X CRASH REPORT")
        lines.append("=" * 60)
        lines.append("")
        
        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"Time: {timestamp}")
        lines.append("")
        
        # System information
        lines.append("System Information:")
        lines.append(f"  OS: {platform.system()} {platform.release()}")
        lines.append(f"  Python: {platform.python_version()}")
        lines.append(f"  Architecture: {platform.machine()}")
        lines.append(f"  Thread: {threading.current_thread().name}")
        lines.append("")
        
        # Exception information
        lines.append("Exception:")
        lines.append(f"  Type: {exc_type.__name__}")
        lines.append(f"  Message: {exc_value}")
        lines.append("")
        
        # Full traceback
        lines.append("Traceback (most recent call last):")
        tb_lines = traceback.format_tb(exc_traceback)
        for line in tb_lines:
            lines.append(line.rstrip())
        
        lines.append("")
        lines.append(f"{exc_type.__name__}: {exc_value}")
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _write_crash_log(self, crash_info: str) -> Path:
        """Write crash dump to log file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"crash_{timestamp}.log"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(crash_info)
        
        return log_file
    
    def _show_error_dialog(self, crash_info: str, log_file: Path):
        """Show user-friendly error dialog (GUI-safe)."""
        try:
            # Only import GUI if available (avoid crashes during GUI init)
            import customtkinter as ctk
            from tkinter import messagebox
            
            # Extract error summary (first 300 chars)
            error_summary = crash_info[:300] + "..." if len(crash_info) > 300 else crash_info
            
            # Create error message
            message = (
                "Sentinel-X encountered a fatal error and needs to close.\n\n"
                f"Crash log saved to:\n{log_file}\n\n"
                "Please report this issue with the log file attached."
            )
            
            # Show messagebox (thread-safe)
            messagebox.showerror(
                "Application Error",
                message,
                icon='error'
            )
            
        except Exception as e:
            # Fallback if GUI unavailable
            logger.error(f"Failed to show crash dialog: {e}", extra={"context": {"error": str(e)}})
    
    def install(self):
        """Install crash handler as global exception hook."""
        sys.excepthook = self.handle_exception
        logger.info("Global exception handler installed")
    
    def uninstall(self):
        """Restore original exception hook."""
        sys.excepthook = self.original_excepthook
        logger.info("Exception handler restored to default")


# Global singleton instance
_crash_handler: Optional[CrashHandler] = None


def install_crash_handler(log_dir: Optional[Path] = None):
    """
    Install global crash handler (call once at app startup).
    
    Args:
        log_dir: Optional custom log directory
    """
    global _crash_handler
    
    if _crash_handler is None:
        _crash_handler = CrashHandler(log_dir)
        _crash_handler.install()
    else:
        logger.warning("Crash handler already installed")


def uninstall_crash_handler():
    """Uninstall crash handler (call at app shutdown if needed)."""
    global _crash_handler
    
    if _crash_handler is not None:
        _crash_handler.uninstall()
        _crash_handler = None


# Example usage in main app:
# from core.crash_handler import install_crash_handler
# install_crash_handler()  # Call before any other code
