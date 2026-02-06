"""
License Management Tab for Sentinel-X GUI
"""

import customtkinter as ctk
from tkinter import messagebox
from core.license_manager import LicenseManager
from core.logger import get_logger

logger = get_logger(__name__)


class LicenseTab(ctk.CTkFrame):
    """License activation and management tab."""
    
    def __init__(self, parent, config_manager):
        super().__init__(parent, fg_color="transparent")
        
        self.config_manager = config_manager
        self.license_manager = LicenseManager()
        
        self._init_layout()
        self._load_license_status()
    
    def _init_layout(self):
        """Initialize UI components."""
        self.header_frame = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=10)
        self.header_frame.pack(fill="x", pady=(0, 20), padx=20)
        
        ctk.CTkLabel(
            self.header_frame,
            text="License Management",
            font=("Roboto", 24, "bold"),
            text_color="white"
        ).pack(pady=15)
        
        self.status_card = ctk.CTkFrame(self, fg_color="#2e2e2e", corner_radius=10)
        self.status_card.pack(fill="x", padx=20, pady=(0, 20))
        
        self.status_label = ctk.CTkLabel(
            self.status_card,
            text="License Status: Checking...",
            font=("Roboto", 16, "bold"),
            text_color="white"
        )
        self.status_label.pack(pady=15, padx=20, anchor="w")
        
        self.details_label = ctk.CTkLabel(
            self.status_card,
            text="",
            font=("Roboto", 13),
            text_color="#b0b0b0"
        )
        self.details_label.pack(pady=(0, 15), padx=20, anchor="w")
        
        self.activation_frame = ctk.CTkFrame(self, fg_color="#2e2e2e", corner_radius=10)
        
        ctk.CTkLabel(
            self.activation_frame,
            text="Activate License",
            font=("Roboto", 16, "bold"),
            text_color="white"
        ).pack(pady=(15, 10), padx=20, anchor="w")
        
        self.license_entry = ctk.CTkEntry(
            self.activation_frame,
            placeholder_text="SNTL-X-XXXX-XXXX-XXXX-XXXX",
            width=500,
            height=40,
            font=("Roboto", 13)
        )
        self.license_entry.pack(pady=(0, 10), padx=20, anchor="w")
        
        button_frame = ctk.CTkFrame(self.activation_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=10)
        
        self.activate_btn = ctk.CTkButton(
            button_frame,
            text="Activate",
            command=self._activate_license,
            width=150,
            height=35,
            fg_color="#007bff",
            hover_color="#0056b3"
        )
        self.activate_btn.pack(side="left", padx=(0, 10))
        
        self.trial_btn = ctk.CTkButton(
            button_frame,
            text="Start Free Trial",
            command=self._start_trial,
            width=150,
            height=35,
            fg_color="#28a745",
            hover_color="#218838"
        )
        self.trial_btn.pack(side="left")
        
        self.info_frame = ctk.CTkFrame(self, fg_color="#2e2e2e", corner_radius=10)
        self.info_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        ctk.CTkLabel(
            self.info_frame,
            text="License Information",
            font=("Roboto", 16, "bold"),
            text_color="white"
        ).pack(pady=(15, 10), padx=20, anchor="w")
        
        features_text = """TRIAL Tier: Basic trading features | 50 trades limit | 7 days duration
PRO Tier: All trial features | Unlimited trades | 1 year duration | Advanced strategies
ENTERPRISE Tier: All PRO features | White label option | Premium support"""
        
        self.features_textbox = ctk.CTkTextbox(
            self.info_frame,
            width=700,
            height=120,
            font=("Roboto", 12),
            text_color="#b0b0b0",
            fg_color="#1e1e1e",
            corner_radius=5
        )
        self.features_textbox.pack(pady=10, padx=20)
        self.features_textbox.insert("1.0", features_text)
        self.features_textbox.configure(state="disabled")
    
    def _load_license_status(self):
        """Load and display current license status."""
        status = self.license_manager.get_license_status()
        
        if status["status"] == "ACTIVE":
            is_lifetime = status.get("days_remaining", 0) == -1
            days_text = status.get("expires_text", "Lifetime") if is_lifetime else f"Days: {status['days_remaining']}"
            
            self.status_label.configure(
                text=f"✓ License: {status['tier']} (ACTIVE)",
                text_color="#28a745"
            )
            
            details = f"{days_text} | Features: {', '.join(status['features'])}"
            if status['max_trades'] > 0:
                details += f" | Trades: {status['max_trades']}"
            
            self.details_label.configure(text=details)
            self.activation_frame.pack_forget()
            
        else:
            self.status_label.configure(
                text=f"✗ License: {status['message']}",
                text_color="#dc3545"
            )
            self.details_label.configure(text="Please activate license or start trial")
            self.activation_frame.pack(fill="x", padx=20, pady=(0, 20))
            
            license_data = self.license_manager.load_license()
            if license_data and license_data.get("tier") == "TRIAL":
                self.trial_btn.pack_forget()
    
    def _activate_license(self):
        """Handle license activation."""
        license_key = self.license_entry.get().strip()
        
        if not license_key:
            messagebox.showerror("Error", "Enter license key")
            return
        
        self.activate_btn.configure(text="Activating...", state="disabled")
        
        try:
            success, message = self.license_manager.activate_license(license_key)
            
            if success:
                messagebox.showinfo("Success", message)
                self.license_entry.delete(0, "end")
                self._load_license_status()
            else:
                messagebox.showerror("Failed", message)
        finally:
            self.activate_btn.configure(text="Activate", state="normal")
    
    def _start_trial(self):
        """Start free trial."""
        if not messagebox.askyesno("Trial", "Start 7-day trial? One-time only."):
            return
        
        try:
            if self.license_manager.activate_trial():
                messagebox.showinfo("Activated", "7-day trial active! 50 trade limit.")
                self._load_license_status()
            else:
                messagebox.showerror("Error", "Failed to activate trial")
        except Exception as e:
            logger.error(f"Trial activation error: {e}")
            messagebox.showerror("Error", f"Trial failed: {e}")
