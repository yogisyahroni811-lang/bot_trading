"""
Stats Tab for Sentinel-X GUI.

Displays token usage statistics and trade history.
"""

import customtkinter as ctk
from typing import Dict, Any, Callable
from .base_tab import BaseTab


class StatsTab(BaseTab):
    """Stats tab showing token usage and trade metrics."""
    
    def __init__(
        self,
        parent,
        config_manager,
        refresh_callback: Callable,
        *args,
        **kwargs
    ):
        """
        Initialize stats tab.
        
        Args:
            parent: Parent widget
            config_manager: ConfigManager instance
            refresh_callback: Function to call to refresh stats display
        """
        self.refresh_callback = refresh_callback
        super().__init__(parent, config_manager, *args, **kwargs)
    
    def _init_components(self):
        """Initialize stats UI components."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header with refresh button
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        
        title = ctk.CTkLabel(
            header,
            text="⚡ Token & Trade Statistics",
            font=("Roboto", 24, "bold")
        )
        title.pack(side="left")
        
        refresh_btn = ctk.CTkButton(
            header,
            text="🔄 Refresh",
            command=self.refresh_callback,
            width=100,
            fg_color="#1f538d"
        )
        refresh_btn.pack(side="right")
        
        # Stats display area (scrollable)
        self.stats_textbox = ctk.CTkTextbox(
            self,
            font=("Consolas", 11),
            wrap="word"
        )
        self.stats_textbox.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        
        # Start auto-refresh (5 minutes = 300000 ms)
        self.after(1000, self.auto_refresh)

    def auto_refresh(self):
        """Auto-refresh stats every 5 minutes."""
        if self.winfo_exists():
            self.refresh_callback()
            self.after(300000, self.auto_refresh)
    
    def _load_values(self):
        """Load values from config (not needed for stats display)."""
        pass
    
    def save_config(self):
        """Save configuration (not needed for stats tab)."""
        pass
    
    def update_display(self, stats_text: str):
        """
        Update stats display with formatted text.
        
        Args:
            stats_text: Formatted statistics text to display
        """
        self.stats_textbox.configure(state="normal")
        self.stats_textbox.delete("1.0", "end")
        self.stats_textbox.insert("1.0", stats_text)
        self.stats_textbox.configure(state="disabled")
