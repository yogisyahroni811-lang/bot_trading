import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from core.user_auth import get_user_auth
from core.logger import get_logger

logger = get_logger(__name__)

class AuthDialog(ctk.CTkToplevel):
    """Login/Register dialog - appears before main application."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.auth = get_user_auth()
        self.result = None
        self.user_data = None
        
        self._setup_window()
        
        # Check if first run (need to register)
        if self.auth.is_first_run():
            self._show_register_form()
        else:
            self._show_login_form()
    
    def _setup_window(self):
        """Setup dialog window."""
        self.title("Sentinel-X - Authentication")
        self.geometry("500x600")
        self.resizable(False, False)
        
        # Center window
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        # Make modal
        self.transient(self.master)
        self.grab_set()
        
        # Header
        self._create_header()
    
    def _create_header(self):
        """Create header section."""
        header = ctk.CTkFrame(self, fg_color='#1a1a2e', corner_radius=0)
        header.pack(fill='x')
        
        ctk.CTkLabel(
            header, 
            text='Sentinel-X', 
            font=('Arial', 24, 'bold'),
            text_color='white'
        ).pack(pady=20)
        
        ctk.CTkLabel(
            header,
            text='AI-Powered Trading Bot',
            font=('Arial', 12),
            text_color='#888888'
        ).pack(pady=(0, 20))
    
    def _show_login_form(self):
        """Show login form for existing users."""
        # Clear any existing content
        for widget in self.winfo_children():
            if widget != self.winfo_children()[0]:  # Keep header
                widget.destroy()
        
        # Form container
        form_frame = ctk.CTkFrame(self, fg_color='transparent')
        form_frame.pack(fill='both', expand=True, padx=40, pady=30)
        
        # Title
        ctk.CTkLabel(
            form_frame,
            text='Login',
            font=('Arial', 20, 'bold')
        ).pack(pady=(0, 30))
        
        # Email
        ctk.CTkLabel(form_frame, text='Email', font=('Arial', 12)).pack(anchor='w')
        self.email_entry = ctk.CTkEntry(form_frame, placeholder_text='your@email.com', width=400)
        self.email_entry.pack(pady=(5, 15))
        
        # Password
        ctk.CTkLabel(form_frame, text='Password', font=('Arial', 12)).pack(anchor='w')
        self.password_entry = ctk.CTkEntry(form_frame, placeholder_text='Your password', 
                                          width=400, show='*')
        self.password_entry.pack(pady=(5, 30))
        
        # Show password checkbox
        self.show_password_var = tk.BooleanVar()
        ctk.CTkCheckBox(
            form_frame,
            text='Show password',
            variable=self.show_password_var,
            command=self._toggle_password_visibility
        ).pack(anchor='w', pady=(0, 20))
        
        # Login button
        ctk.CTkButton(
            form_frame,
            text='Login',
            command=self._do_login,
            fg_color='#007bff',
            hover_color='#0056b3',
            width=400,
            height=40
        ).pack(pady=10)
        
        # Register link
        ctk.CTkLabel(
            form_frame,
            text="Don't have an account? Register with a new license key",
            font=('Arial', 10),
            text_color='#888888'
        ).pack(pady=20)
        
        ctk.CTkButton(
            form_frame,
            text='Register New Account',
            command=self._show_register_form,
            fg_color='transparent',
            border_width=2,
            border_color='#007bff',
            text_color='#007bff',
            width=400,
            height=35
        ).pack()
    
    def _show_register_form(self):
        """Show registration form for new users."""
        # Clear any existing content (except header)
        for widget in self.winfo_children():
            if widget != self.winfo_children()[0]:
                widget.destroy()
        
        # Form container
        form_frame = ctk.CTkFrame(self, fg_color='transparent')
        form_frame.pack(fill='both', expand=True, padx=40, pady=20)
        
        # Title
        ctk.CTkLabel(
            form_frame,
            text='Register New Account',
            font=('Arial', 20, 'bold')
        ).pack(pady=(0, 20))
        
        # Warning for first-time
        if self.auth.is_first_run():
            warning_frame = ctk.CTkFrame(form_frame, fg_color='#2d1b1b', corner_radius=8)
            warning_frame.pack(fill='x', pady=(0, 20))
            
            ctk.CTkLabel(
                warning_frame,
                text='⚠ First Time Setup\nPlease register to activate Sentinel-X',
                font=('Arial', 11),
                text_color='#ffaa00'
            ).pack(pady=10)
        
        # Email
        ctk.CTkLabel(form_frame, text='Email *', font=('Arial', 12)).pack(anchor='w')
        self.reg_email_entry = ctk.CTkEntry(form_frame, placeholder_text='your@email.com', width=400)
        self.reg_email_entry.pack(pady=(5, 10))
        
        # Password
        ctk.CTkLabel(form_frame, text='Password * (min 8 chars)', font=('Arial', 12)).pack(anchor='w')
        self.reg_password_entry = ctk.CTkEntry(form_frame, placeholder_text='Create strong password', 
                                              width=400, show='*')
        self.reg_password_entry.pack(pady=(5, 10))
        
        # Confirm Password
        ctk.CTkLabel(form_frame, text='Confirm Password *', font=('Arial', 12)).pack(anchor='w')
        self.reg_confirm_entry = ctk.CTkEntry(form_frame, placeholder_text='Confirm password', 
                                             width=400, show='*')
        self.reg_confirm_entry.pack(pady=(5, 10))
        
        # Show password checkbox
        self.reg_show_password_var = tk.BooleanVar()
        ctk.CTkCheckBox(
            form_frame,
            text='Show passwords',
            variable=self.reg_show_password_var,
            command=self._toggle_reg_password_visibility
        ).pack(anchor='w', pady=(0, 15))
        
        # License Key
        ctk.CTkLabel(form_frame, text='License Key *', font=('Arial', 12)).pack(anchor='w')
        self.reg_license_entry = ctk.CTkEntry(
            form_frame, 
            placeholder_text='SNTL-X-XXXX-XXXX-XXXX-XXXX', 
            width=400
        )
        self.reg_license_entry.pack(pady=(5, 15))
        
        # License info
        license_info = """License Types:
• TRIAL: Free, 7 days, 50 trades
• PRO: Lifetime, unlimited ($299)
• ENTERPRISE: Lifetime, unlimited ($999)"""
        
        info_label = ctk.CTkLabel(
            form_frame,
            text=license_info,
            font=('Arial', 10),
            text_color='#888888'
        )
        info_label.pack(anchor='w', pady=(0, 20))
        
        # Register button
        ctk.CTkButton(
            form_frame,
            text='Register Account',
            command=self._do_register,
            fg_color='#28a745',
            hover_color='#218838',
            width=400,
            height=40
        ).pack(pady=10)
        
        # Back to login (if not first run)
        if not self.auth.is_first_run():
            ctk.CTkButton(
                form_frame,
                text='Back to Login',
                command=self._show_login_form,
                fg_color='transparent',
                text_color='#007bff'
            ).pack(pady=10)
    
    def _toggle_password_visibility(self):
        """Toggle password visibility in login form."""
        if self.show_password_var.get():
            self.password_entry.configure(show='')
        else:
            self.password_entry.configure(show='*')
    
    def _toggle_reg_password_visibility(self):
        """Toggle password visibility in register form."""
        if self.reg_show_password_var.get():
            self.reg_password_entry.configure(show='')
            self.reg_confirm_entry.configure(show='')
        else:
            self.reg_password_entry.configure(show='*')
            self.reg_confirm_entry.configure(show='*')
    
    def _do_login(self):
        """Process login."""
        email = self.email_entry.get().strip()
        password = self.password_entry.get()
        
        if not email or not password:
            messagebox.showerror('Error', 'Please enter both email and password')
            return
        
        success, msg, user_data = self.auth.login_user(email, password)
        
        if success:
            self.result = 'login'
            self.user_data = user_data
            messagebox.showinfo('Success', msg)
            self.destroy()
        else:
            messagebox.showerror('Login Failed', msg)
    
    def _do_register(self):
        """Process registration."""
        email = self.reg_email_entry.get().strip()
        password = self.reg_password_entry.get()
        confirm = self.reg_confirm_entry.get()
        license_key = self.reg_license_entry.get().strip()
        
        # Validate inputs
        if not all([email, password, confirm, license_key]):
            messagebox.showerror('Error', 'All fields are required')
            return
        
        if password != confirm:
            messagebox.showerror('Error', 'Passwords do not match')
            return
        
        if len(password) < 8:
            messagebox.showerror('Error', 'Password must be at least 8 characters')
            return
        
        # Register
        success, msg = self.auth.register_user(email, password, license_key)
        
        if success:
            self.result = 'register'
            messagebox.showinfo('Success', msg)
            self.destroy()
        else:
            messagebox.showerror('Registration Failed', msg)
    
    def get_result(self):
        """Get authentication result."""
        return self.result, self.user_data


def show_auth_dialog(parent=None):
    """
    Show authentication dialog and return result.
    
    Returns:
        (success: bool, user_data: dict or None)
    """
    dialog = AuthDialog(parent)
    dialog.wait_window()  # Wait for dialog to close
    
    result, user_data = dialog.get_result()
    return result is not None, user_data