import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from datetime import datetime
from core.config import ConfigManager
from core.license_manager import LicenseManager
from core.logger import get_logger
from gui_components.auth_dialog import show_auth_dialog
from core.user_auth import get_user_auth
from core.prompt_templates import get_prompt_templates
import os
import shutil
import subprocess
import threading

logger = get_logger(__name__)

class SentinelXGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        try:
            logger.info('Starting GUI initialization')
            
            # Check authentication first
            auth = get_user_auth()
            session = auth.get_current_session()
            
            if not session:
                # Show login/register dialog
                logger.info('No active session, showing auth dialog')
                success, user_data = show_auth_dialog(self)
                
                if not success:
                    logger.warning('Authentication failed or cancelled')
                    self.destroy()
                    return
                
                logger.info(f'User authenticated: {user_data["email"]}')
            else:
                logger.info(f'Session active: {session["email"]}')
            
            self.title('Sentinel-X Trading Bot')
            self.geometry('1000x700')
            self.minsize(800, 600)
            
            self.config_manager = ConfigManager()
            self.current_config = self.config_manager.load_config()
            
            self.license_manager = LicenseManager()
            license_status = self.license_manager.get_license_status()
            
            logger.info(f'License status: {license_status}')
            
            # Server state
            self.is_server_running = False
            self.server_process = None
            self.server_status_label = None
            self.ai_status_label = None
            
            # Prompt templates
            self.prompt_templates = get_prompt_templates()
            self.current_prompt_text = None
            
            self._build_ui()
            
            # Start MT5 connection monitoring
            self._update_mt5_status()
            
            if license_status['status'] != 'ACTIVE':
                self.after(1000, self._show_license_warning)
            
            logger.info('GUI initialized successfully')
            
        except Exception as e:
            logger.error(f'GUI init failed: {e}')
            import traceback
            traceback.print_exc()
            raise
    
    def _build_ui(self):
        header = ctk.CTkFrame(self, height=50, fg_color='#1a1a2e')
        header.pack(fill='x', side='top')
        header.pack_propagate(False)
        
        # Left side - Logo
        ctk.CTkLabel(header, text='Sentinel-X', font=('Arial', 20, 'bold')).pack(side='left', padx=20, pady=10)
        
        # Center - User info (if authenticated)
        auth = get_user_auth()
        session = auth.get_current_session()
        if session:
            user_info = ctk.CTkFrame(header, fg_color='transparent')
            user_info.pack(side='left', padx=20)
            
            ctk.CTkLabel(
                user_info,
                text=f"👤 {session['email']}",
                font=('Arial', 11),
                text_color='#aaaaaa'
            ).pack(side='left')
        
        # Right side - License status and Logout
        right_frame = ctk.CTkFrame(header, fg_color='transparent')
        right_frame.pack(side='right', padx=20)
        
        status = self.license_manager.get_license_status()
        status_text = f"License: {status['tier']} ({status['status']})"
        status_color = '#00ff00' if status['status'] == 'ACTIVE' else '#ff0000'
        
        ctk.CTkLabel(right_frame, text=status_text, font=('Arial', 12), text_color=status_color).pack(side='left', padx=10)
        
        # MT5 Connection Status
        self.mt5_status_frame = ctk.CTkFrame(right_frame, fg_color='transparent')
        self.mt5_status_frame.pack(side='left', padx=10)
        
        self.mt5_status_dot = ctk.CTkLabel(
            self.mt5_status_frame,
            text='●',
            font=('Arial', 16),
            text_color='#888888'  # Default abu-abu
        )
        self.mt5_status_dot.pack(side='left')
        
        self.mt5_status_text = ctk.CTkLabel(
            self.mt5_status_frame,
            text='MT5: Not Connected',
            font=('Arial', 11),
            text_color='#888888'
        )
        self.mt5_status_text.pack(side='left', padx=5)
        
        # Logout button
        if session:
            ctk.CTkButton(
                right_frame,
                text='Logout',
                command=self._do_logout,
                fg_color='#dc3545',
                hover_color='#c82333',
                width=80,
                height=28,
                font=('Arial', 11)
            ).pack(side='left', padx=10)
        
        # Navigation tabs
        nav_frame = ctk.CTkFrame(self, height=40, fg_color='#2d2d44')
        nav_frame.pack(fill='x', side='top')
        nav_frame.pack_propagate(False)
        
        self.nav_buttons = {}
        tabs = [
            ('License', self._show_license_tab),
            ('Dashboard', self._show_dashboard_tab),
            ('Token Stats', self._show_stats_tab),
            ('Knowledge', self._show_knowledge_tab),
            ('Prompt', self._show_prompt_tab),
            ('Judge', self._show_judge_tab),
            ('Charts', self._show_charts_tab),
            ('Monitoring', self._show_monitoring_tab)
        ]
        
        for tab_name, command in tabs:
            btn = ctk.CTkButton(
                nav_frame,
                text=tab_name,
                command=command,
                fg_color='transparent',
                text_color='#aaaaaa',
                hover_color='#3d3d5c',
                width=100,
                height=30,
                font=('Arial', 11)
            )
            btn.pack(side='left', padx=5, pady=5)
            self.nav_buttons[tab_name] = btn
        
        self.content = ctk.CTkFrame(self, fg_color='transparent')
        self.content.pack(fill='both', expand=True, padx=20, pady=20)
        
        self._show_license_tab()
    
    def _show_license_tab(self):
        self._clear_content()
        self._highlight_tab('License')
        
        frame = ctk.CTkFrame(self.content)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text='License Management', font=('Arial', 24, 'bold')).pack(pady=30)
        
        status = self.license_manager.get_license_status()
        
        if status['status'] == 'ACTIVE':
            ctk.CTkLabel(frame, text=f"License Active: {status['tier']}", 
                        font=('Arial', 16), text_color='#00ff00').pack(pady=10)
            
            expiry = status.get('expires_text', 'Unknown')
            ctk.CTkLabel(frame, text=f"Expiry: {expiry}", font=('Arial', 14)).pack(pady=5)
            
            features = ', '.join(status.get('features', []))
            ctk.CTkLabel(frame, text=f"Features: {features}", font=('Arial', 12)).pack(pady=5)
            
        else:
            ctk.CTkLabel(frame, text='No license activated', 
                        font=('Arial', 16), text_color='#ffaa00').pack(pady=10)
            
            self.license_entry = ctk.CTkEntry(frame, placeholder_text='Enter license key (SNTL-X-...)', width=400)
            self.license_entry.pack(pady=20)
            
            btn_frame = ctk.CTkFrame(frame, fg_color='transparent')
            btn_frame.pack(pady=10)
            
            ctk.CTkButton(btn_frame, text='Activate License', 
                         command=self._activate_license,
                         fg_color='#007bff', hover_color='#0056b3').pack(side='left', padx=5)
            
            ctk.CTkButton(btn_frame, text='Start Free Trial', 
                         command=self._start_trial,
                         fg_color='#28a745', hover_color='#218838').pack(side='left', padx=5)
        
        info_text = """License Information:
- TRIAL: 7 days, 50 trades, basic features
- PRO: Lifetime, unlimited, advanced features  
- ENTERPRISE: Lifetime, unlimited, all features + support

Hardware-locked: License binds to first device activated"""
        
        text_box = ctk.CTkTextbox(frame, width=600, height=120, font=('Arial', 11))
        text_box.pack(pady=20)
        text_box.insert('1.0', info_text)
        text_box.configure(state='disabled')
    
    def _activate_license(self):
        try:
            key = self.license_entry.get().strip()
            if not key:
                messagebox.showerror('Error', 'Please enter a license key')
                return
            
            success, msg = self.license_manager.activate_license(key)
            
            if success:
                messagebox.showinfo('Success', msg)
                self._show_license_tab()
            else:
                messagebox.showerror('Failed', msg)
                
        except Exception as e:
            logger.error(f'License activation error: {e}')
            messagebox.showerror('Error', f'Activation failed: {e}')
    
    def _start_trial(self):
        try:
            if self.license_manager.activate_trial():
                messagebox.showinfo('Success', '7-day trial activated!')
                self._show_license_tab()
            else:
                messagebox.showerror('Error', 'Failed to activate trial')
        except Exception as e:
            logger.error(f'Trial activation error: {e}')
            messagebox.showerror('Error', f'Trial failed: {e}')
    
    def _show_license_warning(self):
        messagebox.showwarning(
            'License Required',
            'Please activate a license or start a free trial to use all features.'
        )
    
    def _do_logout(self):
        """Handle logout."""
        if messagebox.askyesno('Confirm Logout', 'Are you sure you want to logout?'):
            auth = get_user_auth()
            auth.logout()
            messagebox.showinfo('Logged Out', 'You have been logged out successfully.')
            
            # Restart auth dialog
            self.destroy()
            import sys
            sys.exit(0)  # Will restart on next run
    
    def _clear_content(self):
        """Clear content area."""
        for widget in self.content.winfo_children():
            widget.destroy()
    
    def _highlight_tab(self, active_tab):
        """Highlight active tab button."""
        for tab_name, btn in self.nav_buttons.items():
            if tab_name == active_tab:
                btn.configure(fg_color='#007bff', text_color='white')
            else:
                btn.configure(fg_color='transparent', text_color='#aaaaaa')
    
    def _show_dashboard_tab(self):
        """Show Dashboard tab with full configuration."""
        self._clear_content()
        self._highlight_tab('Dashboard')
        
        # Create scrollable frame for dashboard
        scroll_frame = ctk.CTkScrollableFrame(self.content)
        scroll_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # ===== SERVER CONTROL SECTION =====
        server_frame = ctk.CTkFrame(scroll_frame)
        server_frame.pack(fill='x', pady=10, padx=10)
        
        ctk.CTkLabel(server_frame, text='Server Control', font=('Arial', 18, 'bold')).pack(anchor='w', padx=15, pady=10)
        
        server_row = ctk.CTkFrame(server_frame, fg_color='transparent')
        server_row.pack(fill='x', padx=15, pady=5)
        
        ctk.CTkLabel(server_row, text='Port:', font=('Arial', 12)).pack(side='left', padx=5)
        self.port_entry = ctk.CTkEntry(server_row, width=80, placeholder_text='8000')
        self.port_entry.pack(side='left', padx=5)
        self.port_entry.insert(0, '8000')
        
        self.start_btn = ctk.CTkButton(server_row, text='START', fg_color='#28a745', hover_color='#218838', 
                                       width=80, command=self._start_server)
        self.start_btn.pack(side='left', padx=10)
        
        self.stop_btn = ctk.CTkButton(server_row, text='STOP', fg_color='#dc3545', hover_color='#c82333', 
                                      width=80, command=self._stop_server, state='disabled')
        self.stop_btn.pack(side='left', padx=5)
        
        ctk.CTkLabel(server_row, text='Secret:', font=('Arial', 12)).pack(side='left', padx=(30, 5))
        self.secret_entry = ctk.CTkEntry(server_row, width=150, placeholder_text='Shared Secret', show='*')
        self.secret_entry.pack(side='left', padx=5)
        
        ctk.CTkButton(server_row, text='Test Signal', fg_color='#6c757d', hover_color='#5a6268', 
                     width=100, command=self._test_signal).pack(side='left', padx=10)
        
        # Status indicators
        status_row = ctk.CTkFrame(server_frame, fg_color='transparent')
        status_row.pack(fill='x', padx=15, pady=10)
        
        self.status_dot = ctk.CTkLabel(status_row, text='●', font=('Arial', 20), text_color='#888888')
        self.status_dot.pack(side='left')
        
        self.server_status_label = ctk.CTkLabel(status_row, text='OFFLINE', font=('Arial', 12), text_color='#888888')
        self.server_status_label.pack(side='left', padx=5)
        
        ctk.CTkLabel(status_row, text='|', font=('Arial', 12), text_color='#555555').pack(side='left', padx=10)
        
        self.ai_status_label = ctk.CTkLabel(status_row, text='AI: Disconnected', font=('Arial', 12), text_color='#888888')
        self.ai_status_label.pack(side='left')
        
        # ===== TWO COLUMN LAYOUT =====
        columns_frame = ctk.CTkFrame(scroll_frame, fg_color='transparent')
        columns_frame.pack(fill='x', pady=10)
        columns_frame.grid_columnconfigure(0, weight=1)
        columns_frame.grid_columnconfigure(1, weight=1)
        
        # ===== LEFT COLUMN: AI & API =====
        left_col = ctk.CTkFrame(columns_frame)
        left_col.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
        
        # AI Inference Engine
        ai_frame = ctk.CTkFrame(left_col)
        ai_frame.pack(fill='x', pady=5, padx=5)
        
        ctk.CTkLabel(ai_frame, text='AI Inference Engine', font=('Arial', 16, 'bold')).pack(anchor='w', padx=10, pady=10)
        
        ai_content = ctk.CTkFrame(ai_frame, fg_color='transparent')
        ai_content.pack(fill='x', padx=10, pady=5)
        
        ctk.CTkLabel(ai_content, text='Provider:', font=('Arial', 11)).grid(row=0, column=0, sticky='w', pady=3)
        provider_combo = ctk.CTkComboBox(ai_content, values=['openrouter', 'openai', 'anthropic', 'groq'], width=200)
        provider_combo.grid(row=0, column=1, sticky='ew', padx=5, pady=3)
        provider_combo.set('openrouter')
        
        ctk.CTkLabel(ai_content, text='Model:', font=('Arial', 11)).grid(row=1, column=0, sticky='w', pady=3)
        model_combo = ctk.CTkComboBox(ai_content, values=['nvidia/nemotron-3-nano-30b-a3b:free', 'gpt-4', 'claude-3-opus'], width=200)
        model_combo.grid(row=1, column=1, sticky='ew', padx=5, pady=3)
        model_combo.set('nvidia/nemotron-3-nano-30b-a3b:free')
        
        # Temp, Tokens, Timeout row
        params_row = ctk.CTkFrame(ai_content, fg_color='transparent')
        params_row.grid(row=2, column=0, columnspan=2, sticky='ew', pady=10)
        
        ctk.CTkLabel(params_row, text='Temp:', font=('Arial', 11)).pack(side='left', padx=5)
        temp_entry = ctk.CTkEntry(params_row, width=60, placeholder_text='0.1')
        temp_entry.pack(side='left', padx=5)
        temp_entry.insert(0, '0.1')
        
        ctk.CTkLabel(params_row, text='Tokens:', font=('Arial', 11)).pack(side='left', padx=(15, 5))
        tokens_entry = ctk.CTkEntry(params_row, width=80, placeholder_text='4096')
        tokens_entry.pack(side='left', padx=5)
        tokens_entry.insert(0, '4096')
        
        ctk.CTkLabel(params_row, text='Timeout:', font=('Arial', 11)).pack(side='left', padx=(15, 5))
        timeout_entry = ctk.CTkEntry(params_row, width=60, placeholder_text='20')
        timeout_entry.pack(side='left', padx=5)
        timeout_entry.insert(0, '20')
        
        ctk.CTkLabel(ai_content, text='Base URL:', font=('Arial', 11)).grid(row=3, column=0, sticky='w', pady=3)
        baseurl_entry = ctk.CTkEntry(ai_content, placeholder_text='https://openrouter.ai/api/v1')
        baseurl_entry.grid(row=3, column=1, sticky='ew', padx=5, pady=3)
        baseurl_entry.insert(0, 'https://openrouter.ai/api/v1')
        
        ai_content.grid_columnconfigure(1, weight=1)
        
        # API Credentials
        api_frame = ctk.CTkFrame(left_col)
        api_frame.pack(fill='x', pady=5, padx=5)
        
        ctk.CTkLabel(api_frame, text='API Credentials', font=('Arial', 16, 'bold')).pack(anchor='w', padx=10, pady=10)
        
        api_content = ctk.CTkFrame(api_frame, fg_color='transparent')
        api_content.pack(fill='x', padx=10, pady=5)
        
        providers = [
            ('GROQ:', ''),
            ('OPENAI:', ''),
            ('ANTHROPIC:', ''),
            ('OPENROUTER:', 'sk-or-v1-...'),
            ('QWEN:', ''),
            ('DEEPSEEK:', ''),
            ('GOOGLE:', '')
        ]
        
        for i, (label, placeholder) in enumerate(providers):
            ctk.CTkLabel(api_content, text=label, font=('Arial', 11), width=100).grid(row=i, column=0, sticky='e', pady=3)
            entry = ctk.CTkEntry(api_content, placeholder_text=placeholder, show='*')
            entry.grid(row=i, column=1, sticky='ew', padx=5, pady=3)
            if placeholder:
                entry.insert(0, placeholder)
        
        api_content.grid_columnconfigure(1, weight=1)
        
        # ===== RIGHT COLUMN: RISK & STRATEGY =====
        right_col = ctk.CTkFrame(columns_frame)
        right_col.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
        
        # Risk & Strategy
        risk_frame = ctk.CTkFrame(right_col)
        risk_frame.pack(fill='x', pady=5, padx=5)
        
        ctk.CTkLabel(risk_frame, text='Risk & Strategy', font=('Arial', 16, 'bold')).pack(anchor='w', padx=10, pady=10)
        
        risk_content = ctk.CTkFrame(risk_frame, fg_color='transparent')
        risk_content.pack(fill='x', padx=10, pady=5)
        
        # Timeframes & Max Candles
        row1 = ctk.CTkFrame(risk_content, fg_color='transparent')
        row1.pack(fill='x', pady=5)
        
        ctk.CTkLabel(row1, text='Timeframes (csv):', font=('Arial', 11)).pack(side='left')
        tf_entry = ctk.CTkEntry(row1, placeholder_text='15,30,H1,H4,D1')
        tf_entry.pack(side='left', fill='x', expand=True, padx=5)
        tf_entry.insert(0, '15,30,H1,H4,D1')
        
        ctk.CTkLabel(row1, text='Max Candles:', font=('Arial', 11)).pack(side='left', padx=(10, 5))
        candles_entry = ctk.CTkEntry(row1, width=80, placeholder_text='100')
        candles_entry.pack(side='left')
        candles_entry.insert(0, '100')
        
        # Min Confidence & Max Spread
        row2 = ctk.CTkFrame(risk_content, fg_color='transparent')
        row2.pack(fill='x', pady=5)
        
        ctk.CTkLabel(row2, text='Min Confidence:', font=('Arial', 11)).pack(side='left')
        conf_entry = ctk.CTkEntry(row2, width=80, placeholder_text='0.55')
        conf_entry.pack(side='left', padx=5)
        conf_entry.insert(0, '0.55')
        
        ctk.CTkLabel(row2, text='Max Spread:', font=('Arial', 11)).pack(side='left', padx=(10, 5))
        spread_entry = ctk.CTkEntry(row2, width=80, placeholder_text='5.0')
        spread_entry.pack(side='left')
        spread_entry.insert(0, '5.0')
        
        # Cooldown & Max Hold Bars
        row3 = ctk.CTkFrame(risk_content, fg_color='transparent')
        row3.pack(fill='x', pady=5)
        
        ctk.CTkLabel(row3, text='Cooldown (min):', font=('Arial', 11)).pack(side='left')
        cooldown_entry = ctk.CTkEntry(row3, width=80, placeholder_text='30')
        cooldown_entry.pack(side='left', padx=5)
        cooldown_entry.insert(0, '30')
        
        ctk.CTkLabel(row3, text='Max Hold Bars:', font=('Arial', 11)).pack(side='left', padx=(10, 5))
        hold_entry = ctk.CTkEntry(row3, width=100, placeholder_text='9999999')
        hold_entry.pack(side='left')
        hold_entry.insert(0, '9999999')
        
        # SL/TP Mode
        row4 = ctk.CTkFrame(risk_content, fg_color='transparent')
        row4.pack(fill='x', pady=5)
        
        ctk.CTkLabel(row4, text='SL/TP Mode:', font=('Arial', 11)).pack(side='left')
        sltp_combo = ctk.CTkComboBox(row4, values=['ai', 'fixed', 'atr'], width=120)
        sltp_combo.pack(side='left', padx=5)
        sltp_combo.set('ai')
        
        ctk.CTkLabel(row4, text='Timezone:', font=('Arial', 11)).pack(side='left', padx=(10, 5))
        tz_entry = ctk.CTkEntry(row4, placeholder_text='Asia/Jakarta')
        tz_entry.pack(side='left', fill='x', expand=True, padx=5)
        tz_entry.insert(0, 'Asia/Jakarta')
        
        # Fixed SL/TP & ATR Multipliers
        row5 = ctk.CTkFrame(risk_content, fg_color='transparent')
        row5.pack(fill='x', pady=5)
        
        ctk.CTkLabel(row5, text='Fixed SL/TP:', font=('Arial', 11)).pack(side='left')
        sl_entry = ctk.CTkEntry(row5, width=60, placeholder_text='5.0')
        sl_entry.pack(side='left', padx=5)
        sl_entry.insert(0, '5.0')
        
        tp_entry = ctk.CTkEntry(row5, width=60, placeholder_text='7.0')
        tp_entry.pack(side='left', padx=5)
        tp_entry.insert(0, '7.0')
        
        ctk.CTkLabel(row5, text='ATR Mult:', font=('Arial', 11)).pack(side='left', padx=(15, 5))
        atr1_entry = ctk.CTkEntry(row5, width=50, placeholder_text='1.5')
        atr1_entry.pack(side='left', padx=5)
        atr1_entry.insert(0, '1.5')
        
        atr2_entry = ctk.CTkEntry(row5, width=50, placeholder_text='2.0')
        atr2_entry.pack(side='left', padx=5)
        atr2_entry.insert(0, '2.0')
        
        # Presets
        ctk.CTkLabel(risk_content, text='Presets:', font=('Arial', 11)).pack(anchor='w', pady=(10, 5))
        presets_frame = ctk.CTkFrame(risk_content, fg_color='transparent')
        presets_frame.pack(fill='x')
        
        ctk.CTkButton(presets_frame, text='Safe', fg_color='#ffc107', hover_color='#e0a800', 
                     text_color='black', width=80).pack(side='left', padx=5)
        ctk.CTkButton(presets_frame, text='Aggressive', fg_color='#dc3545', hover_color='#c82333', 
                     width=100).pack(side='left', padx=5)
        ctk.CTkButton(presets_frame, text='Sniper', fg_color='#28a745', hover_color='#218838', 
                     width=80).pack(side='left', padx=5)
        
        # Notifications & Data
        notif_frame = ctk.CTkFrame(right_col)
        notif_frame.pack(fill='x', pady=5, padx=5)
        
        ctk.CTkLabel(notif_frame, text='Notifications & Data', font=('Arial', 16, 'bold')).pack(anchor='w', padx=10, pady=10)
        
        notif_content = ctk.CTkFrame(notif_frame, fg_color='transparent')
        notif_content.pack(fill='x', padx=10, pady=5)
        
        enable_telegram = ctk.CTkCheckBox(notif_content, text='Enable Telegram')
        enable_telegram.pack(anchor='w', pady=5)
        
        ctk.CTkLabel(notif_content, text='Bot Token:', font=('Arial', 11)).pack(anchor='w', pady=(5, 0))
        bot_token_entry = ctk.CTkEntry(notif_content, placeholder_text='Your Telegram Bot Token')
        bot_token_entry.pack(fill='x', pady=3)
        
        ctk.CTkLabel(notif_content, text='Chat ID:', font=('Arial', 11)).pack(anchor='w', pady=(5, 0))
        chat_id_entry = ctk.CTkEntry(notif_content, placeholder_text='Your Telegram Chat ID')
        chat_id_entry.pack(fill='x', pady=3)
        
        # Save Configuration Button
        save_btn = ctk.CTkButton(scroll_frame, text='Save Configuration', 
                                fg_color='#007bff', hover_color='#0056b3',
                                font=('Arial', 14, 'bold'), height=40)
        save_btn.pack(fill='x', padx=10, pady=20)
    
    def _show_stats_tab(self):
        """Show Token Stats tab."""
        self._clear_content()
        self._highlight_tab('Token Stats')
        
        frame = ctk.CTkFrame(self.content)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text='Token Statistics', font=('Arial', 24, 'bold')).pack(pady=30)
        
        stats = [
            ('Total Trades', '0'),
            ('Win Rate', '0%'),
            ('Total PnL', '$0.00'),
            ('Average Win', '$0.00'),
            ('Average Loss', '$0.00'),
            ('Current Streak', '0')
        ]
        
        for label, value in stats:
            row = ctk.CTkFrame(frame, fg_color='transparent')
            row.pack(fill='x', pady=10, padx=50)
            
            ctk.CTkLabel(row, text=label, font=('Arial', 14)).pack(side='left')
            ctk.CTkLabel(row, text=value, font=('Arial', 14, 'bold')).pack(side='right')
    
    def _show_knowledge_tab(self):
        """Show Knowledge Base tab."""
        self._clear_content()
        self._highlight_tab('Knowledge')
        
        frame = ctk.CTkFrame(self.content)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text='Knowledge Base', font=('Arial', 24, 'bold')).pack(pady=30)
        
        ctk.CTkLabel(frame, text='Upload trading strategy files', font=('Arial', 14)).pack(pady=10)
        
        btn_frame = ctk.CTkFrame(frame, fg_color='transparent')
        btn_frame.pack(pady=20)
        
        ctk.CTkButton(
            btn_frame,
            text='Upload File',
            command=self._upload_knowledge_file,
            fg_color='#007bff',
            hover_color='#0056b3',
            width=150
        ).pack(side='left', padx=10)
        
        ctk.CTkButton(
            btn_frame,
            text='Scan Knowledge',
            command=self._scan_knowledge,
            fg_color='#28a745',
            hover_color='#218838',
            width=150
        ).pack(side='left', padx=10)
        
        # File list
        files_frame = ctk.CTkFrame(frame)
        files_frame.pack(fill='both', expand=True, pady=20, padx=50)
        
        ctk.CTkLabel(files_frame, text='Uploaded Files', font=('Arial', 14, 'bold')).pack(anchor='w', pady=10, padx=10)
        
        # Check for files
        kb_dir = 'knowledge/concepts'
        if os.path.exists(kb_dir):
            files = [f for f in os.listdir(kb_dir) if f.endswith(('.txt', '.md'))]
            if files:
                files_list = ctk.CTkTextbox(files_frame, height=150)
                files_list.pack(fill='x', padx=10, pady=5)
                files_list.insert('1.0', '\n'.join(f'  📄 {f}' for f in files))
                files_list.configure(state='disabled')
            else:
                ctk.CTkLabel(files_frame, text='No files uploaded yet. Click "Upload File" to add strategy files.', 
                           font=('Arial', 12), text_color='#888888').pack(pady=30)
        else:
            ctk.CTkLabel(files_frame, text='No files uploaded yet. Click "Upload File" to add strategy files.', 
                       font=('Arial', 12), text_color='#888888').pack(pady=30)
    
    def _show_prompt_tab(self):
        """Show Prompt Template tab."""
        self._clear_content()
        self._highlight_tab('Prompt')
        
        # Main container dengan scroll
        scroll_frame = ctk.CTkScrollableFrame(self.content)
        scroll_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Header
        ctk.CTkLabel(scroll_frame, text='Prompt Templates', font=('Arial', 24, 'bold')).pack(pady=20)
        
        # Template selection
        select_frame = ctk.CTkFrame(scroll_frame)
        select_frame.pack(fill='x', pady=10, padx=10)
        
        ctk.CTkLabel(select_frame, text='Select Template:', font=('Arial', 14, 'bold')).pack(anchor='w', padx=10, pady=10)
        
        templates = self.prompt_templates.list_templates()
        template_names = list(templates.keys())
        
        self.template_combo = ctk.CTkComboBox(
            select_frame, 
            values=[f"{k}: {v}" for k, v in templates.items()],
            width=500,
            command=self._on_template_change
        )
        self.template_combo.pack(padx=10, pady=5)
        self.template_combo.set("default: Default System (Recommended)")
        
        # Template description
        desc_frame = ctk.CTkFrame(select_frame)
        desc_frame.pack(fill='x', padx=10, pady=10)
        
        self.template_desc = ctk.CTkLabel(
            desc_frame,
            text="Default system prompt with complete trading analysis framework including market structure, supply/demand zones, and risk management rules.",
            font=('Arial', 11),
            wraplength=700
        )
        self.template_desc.pack(padx=10, pady=10)
        
        # Prompt display
        ctk.CTkLabel(scroll_frame, text='Current Prompt:', font=('Arial', 14, 'bold')).pack(anchor='w', padx=10, pady=(20, 5))
        
        prompt_frame = ctk.CTkFrame(scroll_frame)
        prompt_frame.pack(fill='both', expand=True, pady=10, padx=10)
        
        self.prompt_textbox = ctk.CTkTextbox(prompt_frame, height=400, font=('Courier', 11))
        self.prompt_textbox.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Load default prompt
        default_prompt = self.prompt_templates.get_prompt("default")
        self.prompt_textbox.insert('1.0', default_prompt)
        
        # Buttons
        btn_frame = ctk.CTkFrame(scroll_frame, fg_color='transparent')
        btn_frame.pack(fill='x', pady=20)
        
        ctk.CTkButton(
            btn_frame,
            text='Use This Template',
            command=self._apply_template,
            fg_color='#28a745',
            hover_color='#218838',
            height=35
        ).pack(side='left', padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text='Reset to Default',
            command=self._reset_prompt,
            fg_color='#6c757d',
            hover_color='#5a6268',
            height=35
        ).pack(side='left', padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text='Save Custom Prompt',
            command=self._save_custom_prompt,
            fg_color='#007bff',
            hover_color='#0056b3',
            height=35
        ).pack(side='left', padx=5)
        
        # Custom additions
        ctk.CTkLabel(scroll_frame, text='Custom Additions (optional):', font=('Arial', 12)).pack(anchor='w', padx=10, pady=(20, 5))
        
        self.custom_additions = ctk.CTkTextbox(scroll_frame, height=100, font=('Arial', 11))
        self.custom_additions.pack(fill='x', pady=5, padx=10)
        self.custom_additions.insert('1.0', 'Add your custom instructions here...')
    
    def _on_template_change(self, selection):
        """Handle template selection change."""
        template_key = selection.split(':')[0]
        
        # Update description
        descriptions = {
            "default": "Default system prompt with complete trading analysis framework including market structure, supply/demand zones, and risk management rules.",
            "scalping": "Specialized for scalping strategies on M5/M15 timeframes with quick entries and tight stops.",
            "swing": "Optimized for swing trading on H4/D1 timeframes with larger targets and longer hold times.",
            "news": "High-risk news trading strategy. Use with caution and strict risk management."
        }
        
        desc = descriptions.get(template_key, "Custom prompt template")
        self.template_desc.configure(text=desc)
        
        # Update prompt text
        prompt = self.prompt_templates.get_prompt(template_key)
        self.prompt_textbox.delete('1.0', 'end')
        self.prompt_textbox.insert('1.0', prompt)
    
    def _apply_template(self):
        """Apply selected template."""
        selection = self.template_combo.get()
        template_key = selection.split(':')[0]
        custom = self.custom_additions.get('1.0', 'end').strip()
        
        if custom and custom != 'Add your custom instructions here...':
            self.prompt_templates.active_template = template_key
            messagebox.showinfo('Success', f'Template "{template_key}" activated with custom additions!')
        else:
            self.prompt_templates.active_template = template_key
            messagebox.showinfo('Success', f'Template "{template_key}" activated!')
    
    def _reset_prompt(self):
        """Reset to default prompt."""
        self.template_combo.set("default: Default System (Recommended)")
        self._on_template_change("default: Default System (Recommended)")
        messagebox.showinfo('Reset', 'Prompt reset to default!')
    
    def _save_custom_prompt(self):
        """Save current prompt as custom template."""
        dialog = ctk.CTkToplevel(self)
        dialog.title('Save Custom Prompt')
        dialog.geometry('400x150')
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text='Enter template name:', font=('Arial', 12)).pack(pady=10)
        
        name_entry = ctk.CTkEntry(dialog, width=300)
        name_entry.pack(pady=10)
        
        def save():
            name = name_entry.get().strip()
            if name:
                prompt_text = self.prompt_textbox.get('1.0', 'end')
                if self.prompt_templates.add_custom_prompt(name, prompt_text):
                    messagebox.showinfo('Success', f'Custom template "{name}" saved!')
                    dialog.destroy()
                    # Refresh tab
                    self._show_prompt_tab()
                else:
                    messagebox.showerror('Error', 'Failed to save template!')
            else:
                messagebox.showwarning('Warning', 'Please enter a name!')
        
        ctk.CTkButton(dialog, text='Save', command=save, fg_color='#28a745').pack(pady=10)
    
    def _show_charts_tab(self):
        """Show Charts tab dengan Matplotlib integration."""
        self._clear_content()
        self._highlight_tab('Charts')
        
        # Create frame untuk ChartTab
        chart_frame = ctk.CTkFrame(self.content)
        chart_frame.pack(fill='both', expand=True)
        
        # Import dan create ChartTab
        from gui_components.chart_tab import ChartTab
        
        def log_callback(msg):
            logger.info(f"Chart: {msg}")
        
        chart_tab = ChartTab(
            chart_frame,
            self.config_manager,
            log_callback
        )
        chart_tab.pack(fill='both', expand=True)
        
        # Auto-refresh saat tab dibuka
        chart_tab.refresh()
    
    def _show_monitoring_tab(self):
        """Show Monitoring tab."""
        self._clear_content()
        self._highlight_tab('Monitoring')
        
        frame = ctk.CTkFrame(self.content)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text='System Monitoring', font=('Arial', 24, 'bold')).pack(pady=30)
        
        # Log area
        log_frame = ctk.CTkFrame(frame)
        log_frame.pack(fill='both', expand=True, pady=20, padx=50)
        
        ctk.CTkLabel(log_frame, text='Activity Log', font=('Arial', 14, 'bold')).pack(pady=10)
        
        log_text = ctk.CTkTextbox(log_frame, width=700, height=300)
        log_text.pack(pady=10, padx=10, fill='both', expand=True)
        log_text.insert('1.0', 'System initialized...\nLicense validated...\nUser logged in...\n')
        log_text.configure(state='disabled')
    
    # ===== SERVER CONTROL METHODS =====
    def _start_server(self):
        """Start the trading server."""
        if self.is_server_running:
            messagebox.showwarning('Warning', 'Server is already running!')
            return
        
        try:
            port = int(self.port_entry.get())
            
            # Update UI
            self.is_server_running = True
            self.start_btn.configure(state='disabled')
            self.stop_btn.configure(state='normal')
            
            # Update status
            self.status_dot.configure(text_color='#00ff00')
            self.server_status_label.configure(text='ONLINE', text_color='#00ff00')
            self.ai_status_label.configure(text='AI: Connected', text_color='#00ff00')
            
            logger.info(f'Server started on port {port}')
            messagebox.showinfo('Success', f'Server started on port {port}!')
            
        except ValueError:
            messagebox.showerror('Error', 'Invalid port number!')
        except Exception as e:
            logger.error(f'Failed to start server: {e}')
            messagebox.showerror('Error', f'Failed to start server: {e}')
    
    def _stop_server(self):
        """Stop the trading server."""
        if not self.is_server_running:
            messagebox.showwarning('Warning', 'Server is not running!')
            return
        
        try:
            # Update UI
            self.is_server_running = False
            self.start_btn.configure(state='normal')
            self.stop_btn.configure(state='disabled')
            
            # Update status
            self.status_dot.configure(text_color='#888888')
            self.server_status_label.configure(text='OFFLINE', text_color='#888888')
            self.ai_status_label.configure(text='AI: Disconnected', text_color='#888888')
            
            logger.info('Server stopped')
            messagebox.showinfo('Success', 'Server stopped!')
            
        except Exception as e:
            logger.error(f'Failed to stop server: {e}')
            messagebox.showerror('Error', f'Failed to stop server: {e}')
    
    def _test_signal(self):
        """Test trading signal."""
        if not self.is_server_running:
            messagebox.showwarning('Server Offline', 'Please start the server first!')
            return
        
        messagebox.showinfo('Test Signal', 'Test signal sent! Check logs for details.')
    
    # ===== KNOWLEDGE BASE METHODS =====
    def _upload_knowledge_file(self):
        """Upload file to knowledge base."""
        file_path = filedialog.askopenfilename(
            title='Select Strategy File',
            filetypes=[
                ('Text files', '*.txt'),
                ('Markdown files', '*.md'),
                ('All files', '*.*')
            ]
        )
        
        if file_path:
            try:
                # Create directory if not exists
                kb_dir = 'knowledge/concepts'
                os.makedirs(kb_dir, exist_ok=True)
                
                # Copy file
                dest_path = os.path.join(kb_dir, os.path.basename(file_path))
                shutil.copy2(file_path, dest_path)
                
                logger.info(f'File uploaded: {os.path.basename(file_path)}')
                messagebox.showinfo('Success', f'File uploaded: {os.path.basename(file_path)}')
                
                # Refresh file list
                self._refresh_knowledge_files()
                
            except Exception as e:
                logger.error(f'Upload failed: {e}')
                messagebox.showerror('Error', f'Upload failed: {e}')
    
    def _scan_knowledge(self):
        """Scan and ingest knowledge base."""
        # Check if server is running
        if not self.is_server_running:
            messagebox.showwarning(
                'Server Offline', 
                'Please start the server from Dashboard first before scanning knowledge!'
            )
            return
        
        try:
            kb_dir = 'knowledge/concepts'
            if not os.path.exists(kb_dir):
                messagebox.showwarning('No Files', 'No knowledge files found. Please upload files first.')
                return
            
            files = [f for f in os.listdir(kb_dir) if f.endswith(('.txt', '.md'))]
            if not files:
                messagebox.showwarning('No Files', 'No .txt or .md files found in knowledge base.')
                return
            
            # Show progress
            progress = ctk.CTkToplevel(self)
            progress.title('Scanning Knowledge')
            progress.geometry('300x100')
            progress.transient(self)
            progress.grab_set()
            
            ctk.CTkLabel(progress, text='Scanning knowledge base...', font=('Arial', 12)).pack(pady=20)
            ctk.CTkProgressBar(progress, mode='indeterminate').pack(pady=10, padx=20, fill='x')
            progress.update()
            
            # Perform scan in background
            def do_scan():
                try:
                    # Import here to avoid circular dependency
                    from core.rag import RAG
                    rag = RAG()
                    result = rag.ingest_knowledge_base(kb_dir)
                    
                    progress.destroy()
                    messagebox.showinfo('Scan Complete', f'Successfully scanned {len(files)} files!\n\n{result}')
                    self._refresh_knowledge_files()
                    
                except Exception as e:
                    progress.destroy()
                    logger.error(f'Scan failed: {e}')
                    messagebox.showerror('Scan Failed', f'Error: {e}')
            
            # Run in thread to keep UI responsive
            thread = threading.Thread(target=do_scan)
            thread.start()
            
        except Exception as e:
            logger.error(f'Scan error: {e}')
            messagebox.showerror('Error', f'Scan failed: {e}')
    
    def _refresh_knowledge_files(self):
        """Refresh the knowledge files list."""
        # This would update the file list display
        # For now, just log it
        kb_dir = 'knowledge/concepts'
        if os.path.exists(kb_dir):
            files = [f for f in os.listdir(kb_dir) if f.endswith(('.txt', '.md'))]
            logger.info(f'Knowledge files: {len(files)} files')
    
    def _show_judge_tab(self):
        """Show The Judge 2.0 - Enhanced dengan Decision History, Gauge, Filter, Collapsible."""
        self._clear_content()
        self._highlight_tab('Judge')
        
        # Main container with scrollbar
        main_container = ctk.CTkFrame(self.content)
        main_container.pack(fill='both', expand=True)
        
        # Create canvas for scrolling
        canvas = tk.Canvas(main_container, bg='#2b2b2b', highlightthickness=0)
        scrollbar = ctk.CTkScrollbar(main_container, command=canvas.yview)
        scroll_frame = ctk.CTkFrame(canvas)
        
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=960)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to scroll
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # ========== HEADER ==========
        header = ctk.CTkFrame(scroll_frame, fg_color='#1a1a2e')
        header.pack(fill='x', pady=10, padx=10)
        
        ctk.CTkLabel(
            header,
            text='⚖️ The Judge 2.0 - Reasoning Engine',
            font=('Arial', 22, 'bold'),
            text_color='#00ff00'
        ).pack(pady=10)
        
        ctk.CTkLabel(
            header,
            text='3-Tier Decision Matrix: Math (30%) + AI Debate (70%)',
            font=('Arial', 12),
            text_color='#888888'
        ).pack(pady=(0, 5))
        
        # ========== CURRENT DECISION PANEL ==========
        current_frame = ctk.CTkFrame(scroll_frame, fg_color='#1a1a2e', border_width=2, border_color='#333333')
        current_frame.pack(fill='x', pady=10, padx=10)
        
        ctk.CTkLabel(
            current_frame,
            text='📊 CURRENT EVALUATION',
            font=('Arial', 14, 'bold'),
            text_color='#00aaff'
        ).pack(pady=10)
        
        # Visual Gauge for Confidence
        gauge_frame = ctk.CTkFrame(current_frame, fg_color='transparent')
        gauge_frame.pack(fill='x', padx=20, pady=5)
        
        self.confidence_gauge_label = ctk.CTkLabel(
            gauge_frame,
            text='Confidence: 0%',
            font=('Arial', 16, 'bold'),
            text_color='#888888'
        )
        self.confidence_gauge_label.pack()
        
        # Custom progress bar canvas
        self.gauge_canvas = tk.Canvas(gauge_frame, height=30, bg='#1a1a2e', highlightthickness=0)
        self.gauge_canvas.pack(fill='x', pady=5)
        
        # Draw initial gauge
        self._draw_confidence_gauge(0)
        
        # Threshold line label
        ctk.CTkLabel(
            gauge_frame,
            text='▲ Threshold: 65% (Entry)',
            font=('Arial', 10),
            text_color='#ffaa00'
        ).pack()
        
        # Final Action Display
        self.final_action_label = ctk.CTkLabel(
            current_frame,
            text='HOLD',
            font=('Arial', 32, 'bold'),
            text_color='#888888'
        )
        self.final_action_label.pack(pady=10)
        
        self.final_reasoning_text = ctk.CTkTextbox(current_frame, height=80, font=('Arial', 10))
        self.final_reasoning_text.pack(fill='x', padx=20, pady=5)
        self.final_reasoning_text.insert('1.0', 'Waiting for market evaluation...')
        self.final_reasoning_text.configure(state='disabled')
        
        # ========== COLLAPSIBLE TIER SECTIONS ==========
        
        # Helper function untuk toggle sections
        def toggle_section(frame, btn, expanded_text, collapsed_text):
            if frame.winfo_viewable():
                frame.pack_forget()
                btn.configure(text=expanded_text)
            else:
                frame.pack(fill='x', pady=5, padx=10, after=btn)
                btn.configure(text=collapsed_text)
        
        # Tier 1 Section
        tier1_header = ctk.CTkFrame(scroll_frame, fg_color='#2d2d44')
        tier1_header.pack(fill='x', pady=5, padx=10)
        
        self.tier1_toggle_btn = ctk.CTkButton(
            tier1_header,
            text='▼ 📊 TIER 1: Mathematical Analysis (30%) - HARD VETO',
            font=('Arial', 12, 'bold'),
            fg_color='transparent',
            hover_color='#3d3d54',
            anchor='w',
            command=lambda: toggle_section(self.tier1_content, self.tier1_toggle_btn,
                                          '▶ 📊 TIER 1: Mathematical Analysis (30%) - HARD VETO',
                                          '▼ 📊 TIER 1: Mathematical Analysis (30%) - HARD VETO')
        )
        self.tier1_toggle_btn.pack(fill='x', padx=5, pady=5)
        
        self.tier1_content = ctk.CTkFrame(tier1_header, fg_color='transparent')
        self.tier1_content.pack(fill='x', padx=10, pady=5)
        
        self.tier1_status = ctk.CTkLabel(self.tier1_content, text='Status: Waiting...', font=('Arial', 11))
        self.tier1_status.pack(anchor='w', pady=2)
        
        self.tier1_trend = ctk.CTkLabel(self.tier1_content, text='Trend: -', font=('Arial', 11))
        self.tier1_trend.pack(anchor='w', pady=2)
        
        self.tier1_veto = ctk.CTkLabel(self.tier1_content, text='Veto: No active veto', 
                                       font=('Arial', 11), text_color='#00ff00')
        self.tier1_veto.pack(anchor='w', pady=2)
        
        # Tier 2 Section
        tier2_header = ctk.CTkFrame(scroll_frame, fg_color='#2d2d44')
        tier2_header.pack(fill='x', pady=5, padx=10)
        
        self.tier2_toggle_btn = ctk.CTkButton(
            tier2_header,
            text='▼ 🧠 TIER 2: RAG Context Retrieval',
            font=('Arial', 12, 'bold'),
            fg_color='transparent',
            hover_color='#3d3d54',
            anchor='w',
            command=lambda: toggle_section(self.tier2_content, self.tier2_toggle_btn,
                                          '▶ 🧠 TIER 2: RAG Context Retrieval',
                                          '▼ 🧠 TIER 2: RAG Context Retrieval')
        )
        self.tier2_toggle_btn.pack(fill='x', padx=5, pady=5)
        
        self.tier2_content = ctk.CTkFrame(tier2_header, fg_color='transparent')
        self.tier2_content.pack(fill='x', padx=10, pady=5)
        
        self.tier2_status = ctk.CTkLabel(self.tier2_content, text='Knowledge Base: Ready', font=('Arial', 11))
        self.tier2_status.pack(anchor='w', pady=2)
        
        # Tier 3 Section
        tier3_header = ctk.CTkFrame(scroll_frame, fg_color='#2d2d44')
        tier3_header.pack(fill='x', pady=5, padx=10)
        
        self.tier3_toggle_btn = ctk.CTkButton(
            tier3_header,
            text='▼ ⚔️ TIER 3: AI Debate (70%) - The Soul',
            font=('Arial', 12, 'bold'),
            fg_color='transparent',
            hover_color='#3d3d54',
            anchor='w',
            command=lambda: toggle_section(self.tier3_content, self.tier3_toggle_btn,
                                          '▶ ⚔️ TIER 3: AI Debate (70%) - The Soul',
                                          '▼ ⚔️ TIER 3: AI Debate (70%) - The Soul')
        )
        self.tier3_toggle_btn.pack(fill='x', padx=5, pady=5)
        
        self.tier3_content = ctk.CTkFrame(tier3_header, fg_color='transparent')
        self.tier3_content.pack(fill='x', padx=10, pady=5)
        
        # Pro Agent
        pro_frame = ctk.CTkFrame(self.tier3_content, fg_color='#1a331a')
        pro_frame.pack(fill='x', pady=5)
        
        ctk.CTkLabel(pro_frame, text='👍 PRO AGENT (The Optimist)', 
                     font=('Arial', 11, 'bold'), text_color='#28a745').pack(anchor='w', padx=10, pady=3)
        
        self.pro_status = ctk.CTkLabel(pro_frame, text='Confidence: 0%', font=('Arial', 10))
        self.pro_status.pack(anchor='w', padx=10, pady=2)
        
        # Con Agent
        con_frame = ctk.CTkFrame(self.tier3_content, fg_color='#331a1a')
        con_frame.pack(fill='x', pady=5)
        
        ctk.CTkLabel(con_frame, text='👎 CON AGENT (Devil\'s Advocate)', 
                     font=('Arial', 11, 'bold'), text_color='#dc3545').pack(anchor='w', padx=10, pady=3)
        
        self.con_status = ctk.CTkLabel(con_frame, text='Confidence: 0%', font=('Arial', 10))
        self.con_status.pack(anchor='w', padx=10, pady=2)
        
        # Debate Winner
        self.debate_winner_label = ctk.CTkLabel(self.tier3_content, text='🏆 Winner: -', 
                                                 font=('Arial', 11, 'bold'), text_color='#ffff00')
        self.debate_winner_label.pack(anchor='w', padx=10, pady=5)
        
        # ========== DECISION HISTORY SECTION ==========
        history_frame = ctk.CTkFrame(scroll_frame, fg_color='#1a1a2e', border_width=2, border_color='#333333')
        history_frame.pack(fill='both', expand=True, pady=10, padx=10)
        
        # History Header
        history_header = ctk.CTkFrame(history_frame, fg_color='#2d2d44')
        history_header.pack(fill='x', pady=10, padx=10)
        
        ctk.CTkLabel(
            history_header,
            text='📜 DECISION HISTORY',
            font=('Arial', 14, 'bold'),
            text_color='#ffaa00'
        ).pack(side='left', padx=10, pady=10)
        
        # Filter Controls
        filter_frame = ctk.CTkFrame(history_header, fg_color='transparent')
        filter_frame.pack(side='right', padx=10, pady=5)
        
        # Symbol Filter
        ctk.CTkLabel(filter_frame, text='Symbol:', font=('Arial', 10)).pack(side='left', padx=5)
        self.history_symbol_filter = ctk.CTkOptionMenu(
            filter_frame,
            values=['All'],
            width=80,
            font=('Arial', 10)
        )
        self.history_symbol_filter.pack(side='left', padx=5)
        
        # Action Filter
        ctk.CTkLabel(filter_frame, text='Action:', font=('Arial', 10)).pack(side='left', padx=5)
        self.history_action_filter = ctk.CTkOptionMenu(
            filter_frame,
            values=['All', 'BUY', 'SELL', 'HOLD'],
            width=80,
            font=('Arial', 10)
        )
        self.history_action_filter.pack(side='left', padx=5)
        
        # Search Box
        ctk.CTkLabel(filter_frame, text='Search:', font=('Arial', 10)).pack(side='left', padx=5)
        self.history_search = ctk.CTkEntry(filter_frame, width=120, placeholder_text='keyword...')
        self.history_search.pack(side='left', padx=5)
        
        # Refresh Button
        ctk.CTkButton(
            filter_frame,
            text='🔄 Refresh',
            font=('Arial', 10),
            width=70,
            height=25,
            command=self._refresh_decision_history
        ).pack(side='left', padx=5)
        
        # Bind filter changes
        self.history_symbol_filter.configure(command=lambda _: self._refresh_decision_history())
        self.history_action_filter.configure(command=lambda _: self._refresh_decision_history())
        self.history_search.bind('<Return>', lambda _: self._refresh_decision_history())
        
        # Statistics Row
        stats_frame = ctk.CTkFrame(history_frame, fg_color='transparent')
        stats_frame.pack(fill='x', padx=10, pady=5)
        
        self.history_stats = ctk.CTkLabel(
            stats_frame,
            text='Total: 0 | Win Rate: 0% | Avg Conf: 0% | PnL: $0.00',
            font=('Arial', 10),
            text_color='#888888'
        )
        self.history_stats.pack(side='left')
        
        # Clear History Button
        ctk.CTkButton(
            stats_frame,
            text='🗑️ Clear',
            font=('Arial', 10),
            width=70,
            height=25,
            fg_color='#dc3545',
            hover_color='#c82333',
            command=self._clear_decision_history
        ).pack(side='right')
        
        # Decision List Container
        self.decision_list_frame = ctk.CTkScrollableFrame(history_frame, height=250)
        self.decision_list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Test Button
        test_frame = ctk.CTkFrame(scroll_frame, fg_color='transparent')
        test_frame.pack(fill='x', pady=10, padx=10)
        
        ctk.CTkButton(
            test_frame,
            text='🧪 Test The Judge',
            command=self._test_judge,
            fg_color='#007bff',
            hover_color='#0056b3',
            font=('Arial', 12, 'bold'),
            height=35
        ).pack(pady=5)
        
        # Load initial data
        self._refresh_decision_history()
        self._update_judge_display()
    
    def _draw_confidence_gauge(self, confidence: float):
        """Draw visual confidence gauge."""
        try:
            canvas = self.gauge_canvas
            canvas.delete('all')
            
            width = canvas.winfo_width() if canvas.winfo_width() > 100 else 900
            height = 30
            
            # Background
            canvas.create_rectangle(0, 5, width, 25, fill='#1a1a2e', outline='#333333')
            
            # Progress bar
            bar_width = width * confidence
            
            # Color based on confidence level
            if confidence >= 0.8:
                color = '#00ff00'  # Green - High
            elif confidence >= 0.65:
                color = '#ffaa00'  # Orange - Medium (threshold)
            elif confidence >= 0.4:
                color = '#ffff00'  # Yellow - Low
            else:
                color = '#ff0000'  # Red - Very low
            
            if bar_width > 0:
                canvas.create_rectangle(0, 5, bar_width, 25, fill=color, outline='')
            
            # Threshold line (65%)
            threshold_x = width * 0.65
            canvas.create_line(threshold_x, 0, threshold_x, 30, fill='#ffaa00', width=2, dash=(4, 2))
            
        except Exception as e:
            logger.error(f"Failed to draw gauge: {e}")
    
    def _refresh_decision_history(self):
        """Refresh decision history list dengan filter."""
        try:
            from core.decision_history import get_decision_history
            
            history = get_decision_history()
            
            # Get filter values
            symbol = self.history_symbol_filter.get()
            action = self.history_action_filter.get()
            search = self.history_search.get().strip()
            
            # Get filtered decisions
            decisions = history.get_decisions(
                symbol=symbol if symbol != 'All' else None,
                action=action if action != 'All' else None,
                search_text=search if search else None,
                limit=50
            )
            
            # Update symbol dropdown options
            symbols = ['All'] + history.get_unique_symbols()
            current_symbol = self.history_symbol_filter.get()
            if current_symbol not in symbols:
                current_symbol = 'All'
            self.history_symbol_filter.configure(values=symbols)
            self.history_symbol_filter.set(current_symbol)
            
            # Update statistics
            stats = history.get_statistics()
            self.history_stats.configure(
                text=f"Total: {stats['total_decisions']} | "
                     f"Win Rate: {stats['win_rate']:.1f}% | "
                     f"Avg Conf: {stats['avg_confidence']:.1f}% | "
                     f"PnL: ${stats['total_pnl']:.2f}"
            )
            
            # Clear existing list
            for widget in self.decision_list_frame.winfo_children():
                widget.destroy()
            
            # Show decisions
            if not decisions:
                ctk.CTkLabel(
                    self.decision_list_frame,
                    text='No decisions yet. Start trading to see history.',
                    font=('Arial', 11),
                    text_color='#666666'
                ).pack(pady=20)
            else:
                for decision in decisions:
                    self._create_decision_card(decision)
        
        except Exception as e:
            logger.error(f"Failed to refresh decision history: {e}")
    
    def _create_decision_card(self, decision):
        """Create a decision card untuk history list."""
        try:
            card = ctk.CTkFrame(self.decision_list_frame, fg_color='#252535')
            card.pack(fill='x', pady=3, padx=5)
            
            # Top row: Time, Symbol, Action
            top_row = ctk.CTkFrame(card, fg_color='transparent')
            top_row.pack(fill='x', padx=10, pady=(5, 2))
            
            time_str = decision.timestamp.strftime('%H:%M:%S')
            ctk.CTkLabel(top_row, text=f"● {time_str}", 
                        font=('Arial', 10), text_color='#666666').pack(side='left')
            
            ctk.CTkLabel(top_row, text=decision.symbol, 
                        font=('Arial', 11, 'bold')).pack(side='left', padx=10)
            
            action_colors = {'BUY': '#00ff00', 'SELL': '#ff0000', 'HOLD': '#888888'}
            action_color = action_colors.get(decision.action, '#888888')
            
            ctk.CTkLabel(top_row, text=decision.action, 
                        font=('Arial', 11, 'bold'), text_color=action_color).pack(side='left')
            
            # Confidence bar
            conf_pct = decision.confidence * 100
            conf_color = '#00ff00' if conf_pct >= 65 else '#ffaa00' if conf_pct >= 40 else '#ff0000'
            ctk.CTkLabel(top_row, text=f"{conf_pct:.0f}%", 
                        font=('Arial', 10), text_color=conf_color).pack(side='right')
            
            # Bottom row: Winner, Reasoning preview
            bottom_row = ctk.CTkFrame(card, fg_color='transparent')
            bottom_row.pack(fill='x', padx=10, pady=(0, 5))
            
            winner_text = f"🏆 {decision.debate_winner}" if decision.debate_winner != '-' else 'No winner'
            ctk.CTkLabel(bottom_row, text=winner_text, 
                        font=('Arial', 9), text_color='#ffff00').pack(side='left')
            
            if decision.executed and decision.pnl is not None:
                pnl_color = '#00ff00' if decision.pnl > 0 else '#ff0000'
                pnl_text = f"${decision.pnl:+.2f}"
                ctk.CTkLabel(bottom_row, text=pnl_text, 
                            font=('Arial', 9, 'bold'), text_color=pnl_color).pack(side='right')
        
        except Exception as e:
            logger.error(f"Failed to create decision card: {e}")
    
    def _clear_decision_history(self):
        """Clear all decision history."""
        try:
            from core.decision_history import get_decision_history
            
            if messagebox.askyesno("Confirm", "Clear all decision history? This cannot be undone."):
                get_decision_history().clear_history()
                self._refresh_decision_history()
                logger.info("Decision history cleared by user")
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
    
    def _test_judge(self):
        """Test The Judge with sample data."""
        import random
        
        # Simulate evaluation
        trend = random.choice(['bullish', 'bearish', 'neutral'])
        strength = random.uniform(0.5, 0.95)
        veto = trend == 'bearish' and strength > 0.8
        
        pro_conf = random.uniform(0.6, 0.9)
        con_conf = random.uniform(0.5, 0.85)
        
        if pro_conf > con_conf + 0.1:
            winner, action = "PRO Agent", "BUY"
        elif con_conf > pro_conf + 0.1:
            winner, action = "CON Agent", "HOLD"
        else:
            winner, action = "NEUTRAL", "HOLD"
        
        if veto:
            action = "HOLD"
            final_conf = pro_conf * 0.3
        else:
            tier1_score = strength * 0.3
            debate_score = max(pro_conf, con_conf) * 0.7
            final_conf = tier1_score + debate_score
        
        # Update display
        self.tier1_status.configure(text=f"Status: Analysis complete")
        self.tier1_trend.configure(text=f"Trend: {trend.upper()} (strength: {strength:.2f})")
        self.tier1_veto.configure(
            text=f"{'⚠️ VETO: Active' if veto else 'Veto: No active veto'}",
            text_color='#ff0000' if veto else '#00ff00'
        )
        
        self.pro_status.configure(text=f"Confidence: {pro_conf:.1%}")
        self.con_status.configure(text=f"Confidence: {con_conf:.1%}")
        self.debate_winner_label.configure(text=f"🏆 Winner: {winner}")
        
        # Update gauge
        self._draw_confidence_gauge(final_conf)
        self.confidence_gauge_label.configure(
            text=f"Confidence: {final_conf:.1%}",
            text_color='#00ff00' if final_conf >= 0.65 else '#ffaa00' if final_conf >= 0.4 else '#ff0000'
        )
        
        # Update action label
        action_colors = {'BUY': '#00ff00', 'SELL': '#ff0000', 'HOLD': '#888888'}
        self.final_action_label.configure(
            text=action,
            text_color=action_colors.get(action, '#888888')
        )
        
        reason = f"Tier 1 (Math): {strength*0.3:.1%} | Tier 3 (Debate): {max(pro_conf, con_conf)*0.7:.1%}"
        self.final_reasoning_text.configure(state='normal')
        self.final_reasoning_text.delete('1.0', 'end')
        self.final_reasoning_text.insert('1.0', reason)
        self.final_reasoning_text.configure(state='disabled')
        
        # Save to history
        try:
            from core.decision_history import DecisionRecord, get_decision_history
            
            decision = DecisionRecord(
                symbol=f"TEST{random.randint(1, 99)}",
                action=action,
                confidence=final_conf,
                tier1_score=strength,
                tier2_context="Test context",
                tier3_pro_conf=pro_conf,
                tier3_con_conf=con_conf,
                debate_winner=winner,
                final_reasoning=reason
            )
            get_decision_history().add_decision(decision)
            self._refresh_decision_history()
        except Exception as e:
            logger.error(f"Failed to save test decision: {e}")
        
        logger.info(f'The Judge test: {action} ({final_conf:.1%} confidence)')
    
    def _update_judge_display(self):
        """Update Judge tab dengan data real-time dari monitor."""
        try:
            from core.judge_monitor import get_judge_monitor
            monitor = get_judge_monitor()
            
            status = monitor.load_status()
            if status and status.get('last_evaluation'):
                eval_data = status['last_evaluation']
                
                # Update Tier 1
                self.tier1_status.configure(text=f"Status: Last eval {eval_data.get('timestamp', 'N/A')[-8:]}")
                self.tier1_trend.configure(text=f"Symbol: {eval_data.get('symbol', '-')} {eval_data.get('timeframe', '')}")
                
                if eval_data.get('veto_active'):
                    self.tier1_veto.configure(text=f"⚠️ VETO: {eval_data.get('veto_reason', 'Active')}", text_color='#ff0000')
                else:
                    self.tier1_veto.configure(text='Veto: No active veto', text_color='#00ff00')
                
                # Update Agents
                pro_conf = eval_data.get('pro_confidence', 0)
                con_conf = eval_data.get('con_confidence', 0)
                self.pro_status.configure(text=f"Confidence: {pro_conf:.1%}")
                self.con_status.configure(text=f"Confidence: {con_conf:.1%}")
                
                # Update Winner
                winner = eval_data.get('debate_winner', '-')
                self.debate_winner_label.configure(text=f"🏆 Winner: {winner}")
                
                # Update Gauge
                conf = eval_data.get('confidence', 0)
                self._draw_confidence_gauge(conf)
                self.confidence_gauge_label.configure(
                    text=f"Confidence: {conf:.1%}",
                    text_color='#00ff00' if conf >= 0.65 else '#ffaa00' if conf >= 0.4 else '#ff0000'
                )
                
                # Update Action
                action = eval_data.get('action', 'HOLD')
                action_colors = {'BUY': '#00ff00', 'STRONG_BUY': '#00ff00',
                                'SELL': '#ff0000', 'STRONG_SELL': '#ff0000', 'HOLD': '#888888'}
                self.final_action_label.configure(
                    text=action,
                    text_color=action_colors.get(action, '#888888')
                )
                
                # Update Reasoning
                reasoning = eval_data.get('reasoning', 'No reasoning')
                tier1_contrib = eval_data.get('tier1_contribution', 0)
                tier3_contrib = eval_data.get('tier3_contribution', 0)
                full_reason = f"{reasoning}\n\nTier 1 (Math): {tier1_contrib:.1%} | Tier 3 (Debate): {tier3_contrib:.1%}"
                
                self.final_reasoning_text.configure(state='normal')
                self.final_reasoning_text.delete('1.0', 'end')
                self.final_reasoning_text.insert('1.0', full_reason)
                self.final_reasoning_text.configure(state='disabled')
                
                # Refresh history occasionally
                if not hasattr(self, '_last_history_refresh') or \
                   (datetime.now() - self._last_history_refresh).seconds > 5:
                    self._refresh_decision_history()
                    self._last_history_refresh = datetime.now()
        
        except Exception as e:
            logger.error(f"Failed to update Judge display: {e}")
        
        # Schedule next update
        if hasattr(self, 'content') and self.winfo_exists():
            self.after(1000, self._update_judge_display)
    
    def _update_mt5_status(self):
        """Update MT5 connection status di header."""
        try:
            # Cek status dari monitor file
            from core.mt5_monitor import get_mt5_monitor
            monitor = get_mt5_monitor()
            status_info = monitor.get_status_info()
            
            status = status_info.get('status', 'disconnected')
            status_text = status_info.get('status_text', 'MT5: Not Connected')
            color = status_info.get('color', '#888888')
            
            # Update UI
            self.mt5_status_dot.configure(text_color=color)
            self.mt5_status_text.configure(text=status_text, text_color=color)
            
        except Exception as e:
            # Jika error, tampilkan sebagai disconnected
            self.mt5_status_dot.configure(text_color='#888888')
            self.mt5_status_text.configure(text='MT5: Not Connected', text_color='#888888')
        
        # Schedule next update (every 2 seconds)
        if hasattr(self, 'content') and self.winfo_exists():
            self.after(2000, self._update_mt5_status)
    
if __name__ == '__main__':
    logger.info('Starting Sentinel-X GUI')
    app = SentinelXGUI()
    logger.info('Entering mainloop')
    app.mainloop()
    logger.info('GUI closed')
