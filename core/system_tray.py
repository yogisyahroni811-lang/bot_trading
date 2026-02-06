"""
System Tray Integration for Sentinel-X.

Provides system tray icon with menu, minimize-to-tray functionality,
and balloon notifications for trade decisions.
"""

import sys
import threading
from pathlib import Path
from typing import Optional, Callable
from core.logger import get_logger

logger = get_logger(__name__)


class SystemTrayManager:
    """Manages system tray icon and interactions."""
    
    def __init__(self, root_window, icon_path: Optional[Path] = None):
        """
        Initialize system tray manager.
        
        Args:
            root_window: The main CTk window instance
            icon_path: Optional path to tray icon (.ico file)
        """
        self.root = root_window
        self.icon_path = icon_path
        self.tray_icon = None
        self.menu = None
        self.thread = None
        
        # Callbacks (set by main app)
        self.on_show_window: Optional[Callable] = None
        self.on_start_server: Optional[Callable] = None
        self.on_stop_server: Optional[Callable] = None
        self.on_exit_app: Optional[Callable] = None
        
        # State
        self.server_running = False
        
        self._setup_tray()
    
    def _setup_tray(self):
        """Setup system tray icon and menu."""
        try:
            # Import pystray for system tray (Windows-compatible)
            from PIL import Image
            import pystray
            
            # Load icon or create default
            if self.icon_path and self.icon_path.exists():
                icon_image = Image.open(self.icon_path)
            else:
                # Create simple default icon (32x32 green/red indicator)
                icon_image = self._create_default_icon()
            
            # Create menu
            self.menu = pystray.Menu(
                pystray.MenuItem(
                    "Show Sentinel-X",
                    self._menu_show_window,
                    default=True  # Double-click action
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Start Server",
                    self._menu_start_server,
                    enabled=lambda item: not self.server_running
                ),
                pystray.MenuItem(
                    "Stop Server",
                    self._menu_stop_server,
                    enabled=lambda item: self.server_running
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Exit",
                    self._menu_exit
                )
            )
            
            # Create tray icon
            self.tray_icon = pystray.Icon(
                "SentinelX",
                icon_image,
                "Sentinel-X Trading Bot",
                self.menu
            )
            
            logger.info("System tray initialized successfully")
            
        except ImportError:
            logger.warning("pystray not installed - system tray disabled")
            logger.info("Install with: pip install pystray pillow")
        except Exception as e:
            logger.error(f"Failed to setup system tray: {e}", extra={"context": {"error": str(e)}})
    
    def _create_default_icon(self):
        """Create a simple default icon (32x32 green circle)."""
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (32, 32), color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        d.ellipse((4, 4, 28, 28), fill=(0, 200, 100))
        return img
    
    def start(self):
        """Run system tray icon in a separate thread."""
        if not self.tray_icon:
            return
            
        def _run():
            try:
                self.tray_icon.run()
            except Exception as e:
                logger.error(f"System tray crashed: {e}")
            
        self.thread = threading.Thread(target=_run, daemon=True)
        self.thread.start()
        logger.info("System tray started in background")
    
    def cleanup(self):
        """Stop tray icon."""
        if self.tray_icon:
            self.tray_icon.stop()
            logger.info("System tray stopped")
    
    # --- Menu Actions ---
    
    def _menu_show_window(self, icon, item):
        """Show the main window."""
        if self.on_show_window:
            self.root.after(0, self.on_show_window)
    
    def _menu_start_server(self, icon, item):
        """Start the server."""
        if self.on_start_server:
            # Execute in main thread context if possible, but callback handles it
            self.root.after(0, self.on_start_server)
    
    def _menu_stop_server(self, icon, item):
        """Stop the server."""
        if self.on_stop_server:
            self.root.after(0, self.on_stop_server)
            
    def _menu_exit(self, icon, item):
        """Exit the application."""
        if self.on_exit_app:
            self.root.after(0, self.on_exit_app)
        else:
            self.cleanup()
            sys.exit(0)
    
    def notify(self, title: str, message: str):
        """Show a balloon notification."""
        if self.tray_icon:
            try:
                self.tray_icon.notify(message, title)
            except Exception as e:
                logger.error(f"Notification error: {e}")

    def update_server_status(self, is_running: bool):
        """Update server status for menu enablement."""
        self.server_running = is_running
        # pystray menus are often static, checking self.server_running in the lambda works
        # but might need GUI interaction to refresh state visualization
