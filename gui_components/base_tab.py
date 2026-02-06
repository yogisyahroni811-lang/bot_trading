"""
Abstract base class for GUI tabs in Sentinel-X.

Provides shared utilities and layout helpers for all tab implementations.
"""

import customtkinter as ctk
from abc import ABC, abstractmethod
from typing import Optional


class BaseTab(ctk.CTkFrame, ABC):
    """
    Abstract base class for all GUI tabs.
    
    Subclasses must implement:
    - _init_components(): Create tab UI elements
    - _load_values(): Load values from config
    - save_config(): Save tab configuration
    """
    
    def __init__(self, parent, config_manager, *args, **kwargs):
        """
        Initialize base tab.
        
        Args:
            parent: Parent widget
            config_manager: ConfigManager instance for loading/saving config
        """
        super().__init__(parent, *args, **kwargs)
        self.config_manager = config_manager
        self.config = config_manager.load_config()
        
        # Initialize UI
        self._init_components()
        
        # Load values from config
        self._load_values()
    
    @abstractmethod
    def _init_components(self):
        """Initialize tab-specific UI components. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _load_values(self):
        """Load values from config into UI widgets. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def save_config(self):
        """Save tab configuration. Must be implemented by subclasses."""
        pass
    
    def create_label_input_pair(
        self,
        parent: ctk.CTkFrame,
        label_text: str,
        default_value: str = "",
        show: Optional[str] = None,
        row: int = 0
    ) -> ctk.CTkEntry:
        """
        Helper: Create a label + input field pair.
        
        Args:
            parent: Parent frame
            label_text: Label text
            default_value: Default input value
            show: Character to show for password fields (e.g., '*')
            row: Grid row number
            
        Returns:
            CTkEntry widget
        """
        label = ctk.CTkLabel(parent, text=label_text, anchor="w")
        label.grid(row=row, column=0, padx=10, pady=5, sticky="w")
        
        entry = ctk.CTkEntry(parent, show=show)
        entry.insert(0, default_value)
        entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
        
        return entry
    
    def create_section_header(
        self,
        parent: ctk.CTkFrame,
        title: str,
        row: int = 0
    ) -> ctk.CTkLabel:
        """
        Helper: Create a section header label.
        
        Args:
            parent: Parent frame
            title: Header title
            row: Grid row number
            
        Returns:
            CTkLabel widget
        """
        header = ctk.CTkLabel(
            parent,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        header.grid(row=row, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")
        return header
