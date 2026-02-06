"""
Dashboard Tab for Sentinel-X GUI.
Refactored for Premium UI/UX with clear grouping, spacing, and hierarchy.
"""

import customtkinter as ctk
import tkinter as tk
from typing import Dict, Any, Callable
from .base_tab import BaseTab
from .widgets import IntSpinbox

# --- CONFIGURATION ---
CARD_COLOR = "#2b2b2b"  # Generic dark card background
HEADER_FONT = ("Roboto", 16, "bold")
LABEL_FONT = ("Roboto", 12)
ACCENT_COLOR = "#1f6aa5"  # Standard CTk Blue, can be tweaked

PROVIDER_MODELS = {
    "groq": ["llama-3.1-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
    "openai": ["gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
    "openrouter": ["meta-llama/llama-3-70b-instruct", "anthropic/claude-3-opus"],
    "anthropic": ["claude-3-opus-20240229", "claude-3-sonnet-20240229"],
    "deepseek": ["deepseek-chat", "deepseek-coder"],
    "qwen": ["qwen-max", "qwen-plus", "qwen-turbo"],
    "google": ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"]
}

class DashboardTab(BaseTab):
    """Premium Dashboard tab with card-based layout."""
    
    def __init__(
        self,
        parent,
        config_manager,
        start_server_callback: Callable,
        stop_server_callback: Callable,
        log_callback: Callable,
        scan_knowledge_callback: Callable,
        open_knowledge_manager_callback: Callable,
        *args,
        **kwargs
    ):
        self.start_server_callback = start_server_callback
        self.stop_server_callback = stop_server_callback
        self.log_callback = log_callback
        self.scan_knowledge_callback = scan_knowledge_callback
        self.open_knowledge_manager_callback = open_knowledge_manager_callback
        
        super().__init__(parent, config_manager, *args, **kwargs)
    
    def _init_components(self):
        """Initialize dashboard UI components with Scrollable Layout."""
        # Main Scrollable Container to prevent overcrowding
        self.main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll.pack(fill="both", expand=True)
        
        # 1. Header & Server Status Card
        self._create_header_card()
        
        # 2. Main Config Area (2 columns: AI Settings vs Trading Settings)
        self.content_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        self.content_frame.pack(fill="x", padx=10, pady=10)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=1)
        
        # Left Column: AI Configuration
        self.left_col = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        self._create_ai_provider_card()
        self._create_api_keys_card()
        
        # Right Column: Trading Configuration
        self.right_col = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.right_col.grid(row=0, column=1, sticky="nsew")
        
        self._create_trading_config_card()
        self._create_payload_card()

        # 3. Prompt Strategy (Full Width)
        self._create_prompt_card()
        
        # 4. Logs (Fixed height at bottom)
        self._create_log_card()

    def _create_card(self, parent, title: str) -> ctk.CTkFrame:
        """Helper to create a standard styled card with title."""
        card = ctk.CTkFrame(parent, fg_color=CARD_COLOR, corner_radius=10)
        card.pack(fill="x", pady=(0, 15))
        
        # Title Header
        title_lbl = ctk.CTkLabel(card, text=title, font=HEADER_FONT, text_color="#e0e0e0")
        title_lbl.pack(anchor="w", padx=15, pady=(12, 5))
        
        # Divider
        # ctk.CTkFrame(card, height=2, fg_color="#404040").pack(fill="x", padx=15, pady=(0, 10))
        
        return card

    def _create_header_card(self):
        """Header with Server Controls."""
        card = self._create_card(self.main_scroll, "Server Control")
        
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=15, pady=(0, 15))
        
        # Grid layout for control row
        content.grid_columnconfigure(1, weight=1) # Spacer
        
        # Left: Controls
        ctrl_frame = ctk.CTkFrame(content, fg_color="transparent")
        ctrl_frame.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(ctrl_frame, text="Port:", font=LABEL_FONT).grid(row=0, column=0, padx=5, sticky="e")
        self.entry_port = ctk.CTkEntry(ctrl_frame, width=70)
        self.entry_port.grid(row=0, column=1, padx=5)
        
        self.btn_start = ctk.CTkButton(
            ctrl_frame, text="START", command=self.start_server_callback, 
            width=100, height=32, fg_color="#2e7d32", hover_color="#1b5e20", font=("Roboto", 13, "bold")
        )
        self.btn_start.grid(row=0, column=2, padx=10)
        
        self.btn_stop = ctk.CTkButton(
            ctrl_frame, text="STOP", command=self.stop_server_callback, 
            width=100, height=32, fg_color="#c62828", hover_color="#b71c1c", state="disabled", font=("Roboto", 13, "bold")
        )
        self.btn_stop.grid(row=0, column=3, padx=5)
        
        # Shared Secret (Visual only if needed, usually hidden)
        ctk.CTkLabel(ctrl_frame, text="Secret:", font=LABEL_FONT).grid(row=0, column=4, padx=(20, 5))
        self.entry_secret = ctk.CTkEntry(ctrl_frame, width=180, show="*")
        self.entry_secret.grid(row=0, column=5, padx=5)

        # Right: Status
        status_frame = ctk.CTkFrame(content, fg_color="transparent")
        status_frame.pack(side="right")
        
        self.lbl_ai_dot = ctk.CTkLabel(status_frame, text="●", text_color="#7f8c8d", font=("Roboto", 24))
        self.lbl_ai_dot.pack(side="left", padx=5)
        
        self.lbl_status = ctk.CTkLabel(status_frame, text="OFFLINE", text_color="#7f8c8d", font=("Roboto", 14, "bold"))
        self.lbl_status.pack(side="left", padx=2)

        # AI Status Separator & Label
        ctk.CTkLabel(status_frame, text="|", text_color="#555").pack(side="left", padx=10)
        
        self.lbl_ai_text = ctk.CTkLabel(status_frame, text="AI: Disconnected", text_color="#7f8c8d", font=("Roboto", 12))
        self.lbl_ai_text.pack(side="left", padx=5)
        
        # Test Signal Button (moved to separate row in cleaner way or small icon)
        self.btn_test = ctk.CTkButton(
            ctrl_frame, text="Test Signal", command=self.run_test_signal,
            width=90, height=24, fg_color="#455a64", font=("Roboto", 11)
        )
        self.btn_test.grid(row=0, column=6, padx=20)

    def _create_ai_provider_card(self):
        """AI Provider Settings."""
        card = self._create_card(self.left_col, "AI Inference Engine")
        
        # Form Layout
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=15, pady=(0, 15))
        grid.grid_columnconfigure(1, weight=1)
        
        # Provider
        ctk.CTkLabel(grid, text="Provider:", font=LABEL_FONT, text_color="gray").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.combo_provider = ctk.CTkComboBox(grid, values=list(PROVIDER_MODELS.keys()), command=self.on_provider_change, height=30)
        self.combo_provider.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        # Model
        ctk.CTkLabel(grid, text="Model:", font=LABEL_FONT, text_color="gray").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.entry_model = ctk.CTkComboBox(grid, values=[], height=30)
        self.entry_model.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        # Advanced Params (Grouped)
        p_frame = ctk.CTkFrame(grid, fg_color="transparent")
        p_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        # Temp / Tokens / Timeout
        ctk.CTkLabel(p_frame, text="Temp:", font=LABEL_FONT).pack(side="left", padx=5)
        self.entry_temp = ctk.CTkEntry(p_frame, width=50)
        self.entry_temp.pack(side="left", padx=2)
        
        ctk.CTkLabel(p_frame, text="Tokens:", font=LABEL_FONT).pack(side="left", padx=(15, 5))
        self.entry_max_tokens = ctk.CTkEntry(p_frame, width=60)
        self.entry_max_tokens.pack(side="left", padx=2)
        
        ctk.CTkLabel(p_frame, text="Timeout:", font=LABEL_FONT).pack(side="left", padx=(15, 5))
        self.entry_timeout = ctk.CTkEntry(p_frame, width=50)
        self.entry_timeout.pack(side="left", padx=2)

        # Base URL (Optional)
        ctk.CTkLabel(grid, text="Base URL:", font=LABEL_FONT, text_color="gray").grid(row=3, column=0, sticky="e", padx=5, pady=(10, 5))
        self.entry_base_url = ctk.CTkEntry(grid, placeholder_text="Default")
        self.entry_base_url.grid(row=3, column=1, sticky="ew", padx=5, pady=(10, 5))

    def _create_api_keys_card(self):
        """API Keys Management."""
        card = self._create_card(self.left_col, "API Credentials")
        
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=15, pady=(0, 15))
        grid.grid_columnconfigure(1, weight=1)
        
        keys = [
            ("GROQ", "entry_key_groq", False),
            ("OPENAI", "entry_key_openai", False),
            ("ANTHROPIC", "entry_key_anthropic", False),
            ("OPENROUTER", "entry_key_openrouter", False),
            ("QWEN", "entry_key_qwen", True), # show placeholder
            ("DEEPSEEK", "entry_key_deepseek", False),
            ("GOOGLE", "entry_key_google", False)
        ]
        
        for i, (label, attr_name, has_placeholder) in enumerate(keys):
            ctk.CTkLabel(grid, text=f"{label}:", font=("Roboto", 11, "bold"), text_color="#bdc3c7").grid(row=i, column=0, sticky="e", padx=5, pady=4)
            ent = ctk.CTkEntry(grid, show="*" if not has_placeholder else "", height=28)
            if has_placeholder:
                ent.configure(placeholder_text="Auto-detect ~/.qwen")
            ent.grid(row=i, column=1, sticky="ew", padx=5, pady=4)
            setattr(self, attr_name, ent)
            
        self.btn_save_config = ctk.CTkButton(
            card, text="Save Configuration", command=self.save_config,
            height=36, font=("Roboto", 13, "bold"), fg_color=ACCENT_COLOR
        )
        self.btn_save_config.pack(fill="x", padx=15, pady=(5, 15))

    def _create_trading_config_card(self):
        """Trading Parameters."""
        card = self._create_card(self.right_col, "Risk & Strategy")
        
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=15, pady=(0, 15))
        
        # Helper to add labeled entry
        def add_param(row, col, label, key):
            ctk.CTkLabel(grid, text=label, font=LABEL_FONT, text_color="gray").grid(row=row, column=col, sticky="w", padx=5, pady=2)
            ent = ctk.CTkEntry(grid, width=100)
            ent.grid(row=row+1, column=col, sticky="ew", padx=5, pady=(0, 10))
            self.trading_entries[key] = ent
            return ent

        self.trading_entries = {}
        
        # Row 0
        add_param(0, 0, "Timeframes (csv)", "Timeframes")
        add_param(0, 1, "Max Candles", "Candles Limit")
        
        # Row 2
        add_param(2, 0, "Min Confidence", "Min Conf")
        add_param(2, 1, "Max Spread", "Max Spread")
        
        # Row 4
        add_param(4, 0, "Cooldown (min)", "Cooldown (m)")
        add_param(4, 1, "Max Hold Bars", "Max Hold")
        
        # SL/TP Mode
        ctk.CTkLabel(grid, text="SL/TP Mode", font=LABEL_FONT, text_color="gray").grid(row=6, column=0, sticky="w", padx=5)
        self.trading_entries["SL/TP Mode"] = ctk.CTkComboBox(grid, values=["ai", "manual"], width=100)
        self.trading_entries["SL/TP Mode"].grid(row=7, column=0, sticky="ew", padx=5, pady=(0, 10))
        
        add_param(6, 1, "Timezone", "Timezone")

        # Fixed SL/TP Section
        sep = ctk.CTkFrame(grid, height=1, fg_color="#555")
        sep.grid(row=8, column=0, columnspan=2, sticky="ew", pady=10)
        
        sl_frame = ctk.CTkFrame(grid, fg_color="transparent")
        sl_frame.grid(row=9, column=0, columnspan=2, sticky="ew")
        
        ctk.CTkLabel(sl_frame, text="Fixed SL/TP:", font=LABEL_FONT).pack(side="left", padx=5)
        self.entry_fixed_sl = ctk.CTkEntry(sl_frame, width=50, placeholder_text="SL")
        self.entry_fixed_sl.pack(side="left", padx=2)
        self.entry_fixed_tp = ctk.CTkEntry(sl_frame, width=50, placeholder_text="TP")
        self.entry_fixed_tp.pack(side="left", padx=2)
        
        ctk.CTkLabel(sl_frame, text="ATR Multipliers:", font=LABEL_FONT).pack(side="left", padx=(15, 5))
        self.entry_atr_sl = ctk.CTkEntry(sl_frame, width=50, placeholder_text="SLx")
        self.entry_atr_sl.pack(side="left", padx=2)
        self.entry_atr_tp = ctk.CTkEntry(sl_frame, width=50, placeholder_text="TPx")
        self.entry_atr_tp.pack(side="left", padx=2)
        
        # Preset Buttons (Grid layout for better alignment)
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=10)
        btn_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        ctk.CTkLabel(btn_frame, text="Presets:", font=("Roboto", 11, "bold")).grid(row=0, column=0, sticky="w")
        
        ctk.CTkButton(btn_frame, text="🛡️ Safe", width=90, fg_color="#f39c12", height=28,
                     command=lambda: self.set_mode("SAFE")).grid(row=0, column=1, padx=2)
                     
        ctk.CTkButton(btn_frame, text="⚔️ Aggressive", width=90, fg_color="#c0392b", height=28,
                     command=lambda: self.set_mode("AGGRESSIVE")).grid(row=0, column=2, padx=2)
                     
        ctk.CTkButton(btn_frame, text="🎯 Sniper", width=90, fg_color="#27ae60", height=28,
                     command=lambda: self.set_mode("SNIPER")).grid(row=0, column=3, padx=2)

    def _create_payload_card(self):
        """Notification & Payload."""
        card = self._create_card(self.right_col, "Notifications & Data")
        
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=15, pady=(0, 15))
        
        # Notifications
        self.chk_telegram = ctk.CTkCheckBox(grid, text="Enable Telegram")
        self.chk_telegram.pack(anchor="w", pady=5)
        
        ctk.CTkLabel(grid, text="Bot Token:", font=LABEL_FONT).pack(anchor="w", pady=(5,0))
        self.entry_bot_token = ctk.CTkEntry(grid)
        self.entry_bot_token.pack(fill="x", pady=(0, 5))

        ctk.CTkLabel(grid, text="Chat ID:", font=LABEL_FONT).pack(anchor="w")
        self.entry_chat_id = ctk.CTkEntry(grid)
        self.entry_chat_id.pack(fill="x", pady=(0, 10))
        
        # Payload
        row = ctk.CTkFrame(grid, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Payload Mode:").pack(side="left")
        self.combo_payload = ctk.CTkComboBox(row, values=["compact", "full"], width=100)
        self.combo_payload.pack(side="left", padx=5)

        row2 = ctk.CTkFrame(grid, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="Tail Data:").pack(side="left")
        self.entry_tail_n = IntSpinbox(row2, width=80, step_size=1)
        self.entry_tail_n.pack(side="left", padx=5)
        self.entry_tail_tf = ctk.CTkComboBox(row2, values=["M1", "M5", "M15", "H1", "H4", "D1"], width=70)
        self.entry_tail_tf.pack(side="left", padx=5)

    def _create_prompt_card(self):
        """Prompt Strategy."""
        card = self._create_card(self.main_scroll, "AI Strategy Logic")
        
        # Header controls
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=15, pady=(0, 5))
        
        self.prompt_mode_var = tk.StringVar(value="template")
        
        ctk.CTkRadioButton(head, text="Use Template", variable=self.prompt_mode_var, value="template").pack(side="left", padx=10)
        ctk.CTkRadioButton(head, text="Custom Instructions", variable=self.prompt_mode_var, value="custom").pack(side="left", padx=10)
        
        # Text Area
        self.txt_prompt = ctk.CTkTextbox(card, height=100, font=("Consolas", 12))
        self.txt_prompt.pack(fill="x", padx=15, pady=10)
        
        # Actions
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=15, pady=(0, 15))
        
        self.btn_ingest = ctk.CTkButton(
            actions, text="📚 Scan Knowledge Base", 
            command=self.scan_knowledge_callback, fg_color="#8e44ad"
        )
        self.btn_ingest.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.btn_manage = ctk.CTkButton(
            actions, text="📂 Manage Documents", 
            command=self.open_knowledge_manager_callback, fg_color="#34495e"
        )
        self.btn_manage.pack(side="left", fill="x", expand=True, padx=(5, 0))

    def _create_log_card(self):
        """Logs (Non-scrollable bottom section)."""
        # We put this directly in the main layout, not the scrollable frame, 
        # but to keep it simple with current architecture we append to scroll.
        # Ideally logs should be fixed at bottom. Let's make it a card at the end.
        
        card = self._create_card(self.main_scroll, "System Logs")
        
        self.log_textbox = ctk.CTkTextbox(card, height=150, state="disabled", font=("Consolas", 10))
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=10)

    # --- LOGIC METHODS (Unchanged from original mostly, just mapped) ---

    def run_test_signal(self):
        """Send a test signal (Mock Payload) to the AI analyzer."""
        try:
            port = int(self.entry_port.get())
            url = f"http://localhost:{port}/api/v1/analyze"
            
            from datetime import datetime
            now_iso = datetime.now().isoformat()
            
            payload = {
                "ticker": "XAUUSD",
                "timeframe": "H1",
                "open": 2025.50,
                "high": 2030.00,
                "low": 2020.00,
                "close": 2028.75,
                "timestamp": now_iso,
                "volume": 1500,
                "source": "manual_test"
            }
            
            self.log_callback(f">>> Sending TEST signal to {url}...")
            # self.log_callback(f"Payload: {str(payload)}")
            
            import requests
            config = self.config_manager.load_config()
            secret = config.get('server', {}).get('shared_secret', '')
            headers = {"X-Shared-Secret": secret}
            
            # Run in thread to not block UI
            import threading
            def _req():
                try:
                    response = requests.post(url, json=payload, headers=headers, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        self.log_msg(f"✓ AI Response: {data.get('action', 'UNKNOWN')}")
                        decision = data.get('decision', {})
                        reason = decision.get('reason', 'No reason provided')
                        self.log_msg(f"  Confidence: {decision.get('confidence', 0)}%")
                        self.log_msg(f"  Reason: {reason}")
                    else:
                        self.log_msg(f"✗ Error: {response.status_code} - {response.text}")
                except Exception as e:
                    self.log_msg(f"✗ Connect Failed: {e}")
            
            threading.Thread(target=_req, daemon=True).start()

        except Exception as e:
            self.log_msg(f"✗ Setup Failed: {e}")

    def _set_val(self, widget, value):
        """Helper to safely set entry value without duplication."""
        try:
            if isinstance(widget, ctk.CTkEntry):
                widget.delete(0, "end")
                widget.insert(0, str(value))
            elif isinstance(widget, ctk.CTkComboBox) or isinstance(widget, ctk.CTkOptionMenu):
                widget.set(str(value))
        except Exception:
            pass

    def _load_values(self):
        """Load values from config into widgets."""
        c = self.config
        
        # Server
        self._set_val(self.entry_port, c['server']['port'])
        if 'shared_secret' in c['server']:
            self._set_val(self.entry_secret, c['server']['shared_secret'])
        
        # LLM
        self.combo_provider.set(c['llm']['provider'])
        self.on_provider_change(c['llm']['provider'])
        self.entry_model.set(c['llm']['model'])
        self._set_val(self.entry_base_url, c['llm']['base_url'])
        self._set_val(self.entry_temp, c['llm']['temperature'])
        self._set_val(self.entry_max_tokens, c['llm']['max_tokens'])
        self._set_val(self.entry_timeout, c['llm']['timeout'])
        
        # API Keys
        self._set_val(self.entry_key_groq, c['api_keys'].get('groq', ''))
        self._set_val(self.entry_key_openai, c['api_keys'].get('openai', ''))
        self._set_val(self.entry_key_openrouter, c['api_keys'].get('openrouter', ''))
        self._set_val(self.entry_key_anthropic, c['api_keys'].get('anthropic', ''))
        self._set_val(self.entry_key_deepseek, c['api_keys'].get('deepseek', ''))
        self._set_val(self.entry_key_qwen, c['api_keys'].get('qwen', ''))
        self._set_val(self.entry_key_google, c['api_keys'].get('google', ''))
        
        # Trading
        t = c['trading']
        self._set_val(self.trading_entries["Timeframes"], ",".join(t['timeframes']))
        self._set_val(self.trading_entries["Candles Limit"], t['candles_limit'])
        self._set_val(self.trading_entries["Min Conf"], t['min_conf'])
        self._set_val(self.trading_entries["Max Spread"], t['max_spread'])
        self._set_val(self.trading_entries["Cooldown (m)"], t['cooldown_minutes'])
        self._set_val(self.trading_entries["Max Hold"], t['max_hold_bars'])
        self.trading_entries["SL/TP Mode"].set(t['sl_tp_mode'])
        self._set_val(self.trading_entries["Timezone"], t['timezone'])
        
        self._set_val(self.entry_fixed_sl, t.get('fixed_sl', 5.0))
        self._set_val(self.entry_fixed_tp, t.get('fixed_tp', 10.0))
        self._set_val(self.entry_atr_sl, t.get('atr_sl_multiplier', 1.5))
        self._set_val(self.entry_atr_tp, t.get('atr_tp_multiplier', 2.0))
        
        # Prompt
        self.prompt_mode_var.set(c['ai_prompt']['mode'])
        self.txt_prompt.delete("1.0", "end")
        self.txt_prompt.insert("1.0", c['ai_prompt']['custom_prompt'])
        
        # Payload
        self.combo_payload.set(c['payload']['data_mode'])
        self._set_val(self.entry_tail_n, c['payload']['tail_n'])
        self._set_val(self.entry_tail_tf, c['payload']['tail_tf'])
        
        # Telegram
        if c['notifications']['telegram_enabled']:
            self.chk_telegram.select()
        else:
            self.chk_telegram.deselect()
        self._set_val(self.entry_bot_token, c['notifications']['bot_token'])
        self._set_val(self.entry_chat_id, c['notifications']['chat_id'])
        
        self.log_msg(">>> UI Config Loaded.")

    def save_config(self):
        """Save configuration."""
        c = self.config
        
        # Server
        try:
            c['server']['port'] = int(self.entry_port.get())
        except ValueError:
            pass # Keep old
            
        c['server']['shared_secret'] = self.entry_secret.get()
        
        # LLM
        c['llm']['provider'] = self.combo_provider.get()
        c['llm']['model'] = self.entry_model.get()
        c['llm']['base_url'] = self.entry_base_url.get()
        try:
            c['llm']['temperature'] = float(self.entry_temp.get())
            c['llm']['max_tokens'] = int(self.entry_max_tokens.get())
            c['llm']['timeout'] = int(self.entry_timeout.get())
        except ValueError:
            pass
            
        # API Keys
        c['api_keys']['groq'] = self.entry_key_groq.get()
        c['api_keys']['openai'] = self.entry_key_openai.get()
        c['api_keys']['openrouter'] = self.entry_key_openrouter.get()
        c['api_keys']['anthropic'] = self.entry_key_anthropic.get()
        c['api_keys']['deepseek'] = self.entry_key_deepseek.get()
        c['api_keys']['qwen'] = self.entry_key_qwen.get()
        c['api_keys']['google'] = self.entry_key_google.get()
        
        # Trading
        t = c['trading']
        t['timeframes'] = [tf.strip() for tf in self.trading_entries["Timeframes"].get().split(",")]
        try:
            t['candles_limit'] = int(self.trading_entries["Candles Limit"].get())
            t['min_conf'] = float(self.trading_entries["Min Conf"].get())
            t['max_spread'] = float(self.trading_entries["Max Spread"].get())
            t['cooldown_minutes'] = int(self.trading_entries["Cooldown (m)"].get())
            t['max_hold_bars'] = int(self.trading_entries["Max Hold"].get())
            t['fixed_sl'] = float(self.entry_fixed_sl.get())
            t['fixed_tp'] = float(self.entry_fixed_tp.get())
            t['atr_sl_multiplier'] = float(self.entry_atr_sl.get())
            t['atr_tp_multiplier'] = float(self.entry_atr_tp.get())
        except ValueError:
            self.log_msg("⚠️ Invalid number format in trading config")
            
        t['sl_tp_mode'] = self.trading_entries["SL/TP Mode"].get()
        t['timezone'] = self.trading_entries["Timezone"].get()
        
        # Prompt
        c['ai_prompt']['mode'] = self.prompt_mode_var.get()
        c['ai_prompt']['custom_prompt'] = self.txt_prompt.get("1.0", "end-1c")
        
        # Payload
        c['payload']['data_mode'] = self.combo_payload.get()
        c['payload']['tail_n'] = int(self.entry_tail_n.get())
        c['payload']['tail_tf'] = self.entry_tail_tf.get()
        
        # Telegram
        c['notifications']['telegram_enabled'] = bool(self.chk_telegram.get())
        c['notifications']['bot_token'] = self.entry_bot_token.get()
        c['notifications']['chat_id'] = self.entry_chat_id.get()
        
        # Save
        self.config_manager.save_config(c)
        self.log_msg("✓ Configuration Saved Successfully")
        messagebox.showinfo("Success", "Configuration saved successfully!")

    def on_provider_change(self, choice):
        models = PROVIDER_MODELS.get(choice, [])
        self.entry_model.configure(values=models)
        if models:
            self.entry_model.set(models[0])

    def set_mode(self, mode: str):
        modes = {
            "AGGRESSIVE": {"min_conf": "0.55", "max_spread": "5.0", "cooldown": "30"},
            "SAFE": {"min_conf": "0.75", "max_spread": "2.0", "cooldown": "120"},
            "SNIPER": {"min_conf": "0.85", "max_spread": "1.0", "cooldown": "240"}
        }
        if mode in modes:
            self.trading_entries["Min Conf"].delete(0, "end")
            self.trading_entries["Min Conf"].insert(0, modes[mode]["min_conf"])
            self.trading_entries["Max Spread"].delete(0, "end")
            self.trading_entries["Max Spread"].insert(0, modes[mode]["max_spread"])
            self.trading_entries["Cooldown (m)"].delete(0, "end")
            self.trading_entries["Cooldown (m)"].insert(0, modes[mode]["cooldown"])
            self.log_msg(f"Mode applied: {mode}")

    def log_msg(self, message: str):
        if self.winfo_exists():
            self.log_callback(message)

    def load_config(self):
        self._load_values()
