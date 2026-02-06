"""
Knowledge Tab for Sentinel-X GUI.

Manages RAG knowledge base files (upload/view/delete).
"""

import customtkinter as ctk
from typing import Dict, Any, Callable
from .base_tab import BaseTab


class KnowledgeTab(BaseTab):
    """Knowledge base management tab."""
    
    def __init__(
        self,
        parent,
        config_manager,
        refresh_files_callback: Callable,
        upload_file_callback: Callable,
        delete_file_callback: Callable,
        scan_knowledge_callback: Callable,
        *args,
        **kwargs
    ):
        """
        Initialize knowledge tab.
        
        Args:
            parent: Parent widget
            config_manager: ConfigManager instance
            refresh_files_callback: Function to refresh file list
            upload_file_callback: Function to upload new file
            delete_file_callback: Function to delete selected file
            scan_knowledge_callback: Function to scan/ingest knowledge base
        """
        self.refresh_files_callback = refresh_files_callback
        self.upload_file_callback = upload_file_callback
        self.delete_file_callback = delete_file_callback
        self.scan_knowledge_callback = scan_knowledge_callback
        
        super().__init__(parent, config_manager, *args, **kwargs)
    
    def _init_components(self):
        """Initialize knowledge tab UI components."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        title = ctk.CTkLabel(
            header,
            text="📚 Knowledge Base Manager",
            font=("Roboto", 24, "bold")
        )
        title.pack(side="left")
        
        # Action buttons
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        
        upload_btn = ctk.CTkButton(
            actions,
            text="📤 Upload File",
            command=self.upload_file_callback,
            fg_color="#28a745",
            width=150
        )
        upload_btn.pack(side="left", padx=5)
        
        scan_btn = ctk.CTkButton(
            actions,
            text="🔍 Scan Knowledge Base",
            command=self.scan_knowledge_callback,
            fg_color="purple",
            width=200
        )
        scan_btn.pack(side="left", padx=5)
        
        refresh_btn = ctk.CTkButton(
            actions,
            text="🔄 Refresh",
            command=self.refresh_files_callback,
            width=120
        )
        refresh_btn.pack(side="left", padx=5)
        
        delete_btn = ctk.CTkButton(
            actions,
            text="🗑️ Delete Selected",
            command=self.delete_file_callback,
            fg_color="#dc3545",
            width=150
        )
        delete_btn.pack(side="right", padx=5)
        
        # File list (scrollable)
        self.file_list_frame = ctk.CTkScrollableFrame(self)
        self.file_list_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.file_list_frame.grid_columnconfigure(0, weight=1)
        
        # Placeholder label
        self.placeholder_label = ctk.CTkLabel(
            self.file_list_frame,
            text="No files loaded. Click 'Refresh' to load knowledge base files.",
            text_color="gray"
        )
        self.placeholder_label.grid(row=0, column=0, pady=50)
    
    def _load_values(self):
        """Load values from config (not needed for knowledge tab)."""
        pass
    
    def save_config(self):
        """Save configuration (not needed for knowledge tab)."""
        pass
    
    def update_file_list(self, files: list):
        """
        Update the file list display.
        
        Args:
            files: List of dictionaries with file info (name, size, date, etc.)
        """
        # Clear existing widgets
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        
        if not files:
            self.placeholder_label = ctk.CTkLabel(
                self.file_list_frame,
                text="No files in knowledge base.",
                text_color="gray"
            )
            self.placeholder_label.grid(row=0, column=0, pady=50)
            return
        
        # Create file list items
        for idx, file_info in enumerate(files):
            file_frame = ctk.CTkFrame(self.file_list_frame, fg_color="#15151A")
            file_frame.grid(row=idx, column=0, sticky="ew", pady=2, padx=5)
            file_frame.grid_columnconfigure(1, weight=1)
            
            # Checkbox for selection
            checkbox = ctk.CTkCheckBox(file_frame, text="")
            checkbox.grid(row=0, column=0, padx=10, pady=10)
            
            # File name
            name_label = ctk.CTkLabel(
                file_frame,
                text=file_info.get('name', 'Unknown'),
                font=("Roboto", 12, "bold"),
                anchor="w"
            )
            name_label.grid(row=0, column=1, sticky="w", padx=10)
            
            # File size
            size_label = ctk.CTkLabel(
                file_frame,
                text=file_info.get('size', '0 KB'),
                text_color="gray",
                anchor="e"
            )
            size_label.grid(row=0, column=2, padx=10)
            
            # Store checkbox reference
            if not hasattr(self, 'file_checkboxes'):
                self.file_checkboxes = []
            self.file_checkboxes.append((checkbox, file_info))
    
    def get_selected_files(self) -> list:
        """
        Get list of selected file names.
        
        Returns:
            List of selected file names
        """
        if not hasattr(self, 'file_checkboxes'):
            return []
        
        selected = []
        for checkbox, file_info in self.file_checkboxes:
            if checkbox.get():
                selected.append(file_info.get('name'))
        
        return selected
