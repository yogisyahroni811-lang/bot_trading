"""
Chart Visualization Tab for Sentinel-X.
Uses matplotlib to render OHLCV data dari Chart Manager.
Integrates dengan Chart Buffer untuk real-time updates.
"""

import customtkinter as ctk
import tkinter as tk
from typing import Dict, Any, Callable, List
from .base_tab import BaseTab
from datetime import datetime, timedelta
import random

# Matplotlib integration
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import numpy as np

from core.chart_manager import get_chart_manager
from core.logger import get_logger

logger = get_logger(__name__)

# Configuration
CHART_BG = "#1a1a2e"
TEXT_COLOR = "#e0e0e0"
UP_COLOR = "#00ff00"  # Green
DOWN_COLOR = "#ff0000"  # Red


class ChartTab(BaseTab):
    """Enhanced Chart Tab dengan Chart Manager integration."""
    
    TIMEFRAMES = ['M15', 'M30', 'H1', 'H4', 'D1']
    
    def __init__(self, parent, config_manager, log_callback: Callable, *args, **kwargs):
        self.log_callback = log_callback
        self.canvas = None
        self.ax = None
        self.ax_volume = None
        self.chart_manager = get_chart_manager()
        self.current_symbol = None
        self.current_timeframe = "H1"
        self.auto_refresh = True
        self.indicators_data = {}
        super().__init__(parent, config_manager, *args, **kwargs)

    def _init_components(self):
        """Initialize enhanced chart UI components."""
        # Main container dengan padding
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # ========== TOP CONTROLS ==========
        ctrl_frame = ctk.CTkFrame(main_frame, fg_color='#2d2d44')
        ctrl_frame.pack(fill='x', pady=(0, 10))
        
        # Symbol Selector
        ctk.CTkLabel(ctrl_frame, text="Symbol:", font=("Roboto", 12)).pack(side="left", padx=5)
        self.combo_symbol = ctk.CTkOptionMenu(
            ctrl_frame,
            values=["Select Symbol"],
            command=self._on_symbol_change,
            width=120,
            font=("Roboto", 11)
        )
        self.combo_symbol.pack(side="left", padx=5)
        
        # Refresh symbols button
        ctk.CTkButton(
            ctrl_frame,
            text="🔄",
            width=30,
            command=self._refresh_symbols,
            font=("Roboto", 10)
        ).pack(side="left", padx=2)
        
        # Timeframe Selector
        ctk.CTkLabel(ctrl_frame, text="Timeframe:", font=("Roboto", 12)).pack(side="left", padx=(20, 5))
        self.combo_tf = ctk.CTkOptionMenu(
            ctrl_frame,
            values=self.TIMEFRAMES,
            command=self._on_tf_change,
            width=80,
            font=("Roboto", 11)
        )
        self.combo_tf.set(self.current_timeframe)
        self.combo_tf.pack(side="left", padx=5)
        
        # Refresh Chart Button
        self.btn_refresh = ctk.CTkButton(
            ctrl_frame,
            text="📊 Refresh",
            command=self._load_chart_data,
            fg_color="#0984e3",
            width=100
        )
        self.btn_refresh.pack(side="right", padx=10)
        
        # Auto-refresh Toggle
        self.var_auto = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            ctrl_frame,
            text="Auto",
            variable=self.var_auto,
            font=("Roboto", 10)
        ).pack(side="right", padx=5)
        
        # Simulate Button (For Testing)
        self.btn_sim = ctk.CTkButton(
            ctrl_frame,
            text="🎲 Simulate",
            command=self._simulate_data,
            fg_color="#636e72",
            width=100
        )
        self.btn_sim.pack(side="right", padx=10)
        
        # Status Label
        self.lbl_status = ctk.CTkLabel(ctrl_frame, text="Waiting for chart data (100 candle buffer)...", text_color="gray")
        self.lbl_status.pack(side="right", padx=10)

        # ========== CHART AREA ==========
        chart_container = ctk.CTkFrame(main_frame, fg_color=CHART_BG)
        chart_container.pack(fill="both", expand=True)
        
        self._init_matplotlib(chart_container)
        
        # ========== INDICATORS PANEL ==========
        indicators_frame = ctk.CTkFrame(main_frame, fg_color='#1a1a2e', height=140)
        indicators_frame.pack(fill='x', pady=(10, 0))
        indicators_frame.pack_propagate(False)
        
        # Indicators header
        ctk.CTkLabel(
            indicators_frame,
            text='📈 Technical Indicators',
            font=('Roboto', 12, 'bold'),
            text_color='#00aaff'
        ).pack(anchor='w', padx=10, pady=(5, 2))
        
        # Indicators grid - menggunakan 2 rows dengan 3 columns
        self.indicators_grid = ctk.CTkFrame(indicators_frame, fg_color='transparent')
        self.indicators_grid.pack(fill='x', padx=10, pady=(2, 5))
        
        # Configure grid columns untuk equal width
        for i in range(3):
            self.indicators_grid.grid_columnconfigure(i, weight=1)
        
        # Create indicator labels
        self.indicator_labels = {}
        indicator_config = [
            ('Price', 'current_price', '{:.5f}'),
            ('SMA 20', 'sma_20', '{:.5f}'),
            ('EMA 9', 'ema_9', '{:.5f}'),
            ('RSI 14', 'rsi_14', '{:.1f}'),
            ('ATR 14', 'atr_14', '{:.5f}'),
            ('Trend', 'trend', '{}')
        ]
        
        for i, (display_name, key, fmt) in enumerate(indicator_config):
            frame = ctk.CTkFrame(self.indicators_grid, fg_color='transparent')
            # 3 items per row
            row = i // 3
            col = i % 3
            frame.grid(row=row, column=col, padx=10, pady=5, sticky='ew')
            
            ctk.CTkLabel(frame, text=f'{display_name}:', font=('Roboto', 10)).pack(side='left')
            label = ctk.CTkLabel(frame, text='-', font=('Roboto', 10, 'bold'))
            label.pack(side='left', padx=5)
            self.indicator_labels[key] = {'label': label, 'format': fmt}
        
        # Initial load
        self._refresh_symbols()
        self._schedule_auto_refresh()

    def _init_matplotlib(self, parent):
        """Setup matplotlib figure dengan candlestick support."""
        # Create figure dengan 2 subplots (price dan volume)
        self.fig = Figure(figsize=(10, 6), dpi=100, facecolor=CHART_BG)
        
        # Main price chart
        self.ax = self.fig.add_subplot(211)
        self.ax.set_facecolor(CHART_BG)
        
        # Volume chart
        self.ax_volume = self.fig.add_subplot(212, sharex=self.ax)
        self.ax_volume.set_facecolor(CHART_BG)
        self.ax_volume.set_ylabel('Volume', color='gray')
        
        # Style setup
        for ax in [self.ax, self.ax_volume]:
            ax.tick_params(axis='x', colors='gray', labelsize=8)
            ax.tick_params(axis='y', colors='gray', labelsize=8)
            ax.grid(True, color='#404040', linestyle='--', linewidth=0.5, alpha=0.5)
            ax.spines['bottom'].set_color('#404040')
            ax.spines['top'].set_color('#404040')
            ax.spines['left'].set_color('#404040')
            ax.spines['right'].set_color('#404040')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

    def _refresh_symbols(self):
        """Refresh list of available symbols dari chart manager."""
        try:
            status = self.chart_manager.get_all_symbols_status()
            symbols = list(status.keys())
            
            if symbols:
                self.combo_symbol.configure(values=['Select Symbol'] + symbols)
                self.lbl_status.configure(
                    text=f"Available: {len(symbols)} symbols",
                    text_color='#00ff00'
                )
                
                # Auto-select first symbol jika belum ada yang dipilih
                if not self.current_symbol and symbols:
                    self.current_symbol = symbols[0]
                    self.combo_symbol.set(self.current_symbol)
                    self._load_chart_data()
            else:
                self.lbl_status.configure(
                    text="No data - Connect MT5 EA (100 candle buffer)",
                    text_color='#ffaa00'
                )
        except Exception as e:
            logger.error(f"Failed to refresh symbols: {e}")
            self.lbl_status.configure(text=f"Error: {str(e)[:50]}", text_color='#ff0000')

    def _on_symbol_change(self, choice):
        """Handle symbol selection change."""
        if choice and choice != "Select Symbol":
            self.current_symbol = choice
            self.log_callback(f"Selected symbol: {choice}")
            self._load_chart_data()

    def _on_tf_change(self, choice):
        """Handle timeframe selection change."""
        self.current_timeframe = choice
        self.log_callback(f"Switched to {choice}")
        if self.current_symbol:
            self._load_chart_data()

    def _load_chart_data(self):
        """Load chart data dari Chart Manager."""
        if not self.current_symbol:
            self.lbl_status.configure(text="Select a symbol first", text_color='#ffaa00')
            return
        
        try:
            # Get candles
            candles = self.chart_manager.get_candles(
                self.current_symbol,
                self.current_timeframe,
                limit=100
            )
            
            if candles:
                # Get indicators
                chart_data = self.chart_manager.get_chart_data(
                    self.current_symbol,
                    self.current_timeframe
                )
                self.indicators_data = chart_data.get('indicators', {})
                
                # Update chart
                self._update_chart_display(candles)
                self._update_indicators_display()
                
                self.lbl_status.configure(
                    text=f"{self.current_symbol} {self.current_timeframe} - {len(candles)}/100 candles",
                    text_color='#00ff00'
                )
            else:
                self.lbl_status.configure(
                    text=f"No data for {self.current_symbol} {self.current_timeframe}",
                    text_color='#ffaa00'
                )
        
        except Exception as e:
            logger.error(f"Failed to load chart: {e}")
            self.lbl_status.configure(text=f"Error: {str(e)[:50]}", text_color='#ff0000')

    def _update_chart_display(self, candles: List[Dict]):
        """Update matplotlib chart dengan candle data."""
        # Clear axes
        self.ax.clear()
        self.ax_volume.clear()
        
        # Re-apply styles
        self.ax.set_facecolor(CHART_BG)
        self.ax_volume.set_facecolor(CHART_BG)
        self.ax.set_ylabel('Price', color='gray')
        self.ax_volume.set_ylabel('Volume', color='gray')
        
        for ax in [self.ax, self.ax_volume]:
            ax.tick_params(axis='x', colors='gray', labelsize=8)
            ax.tick_params(axis='y', colors='gray', labelsize=8)
            ax.grid(True, color='#404040', linestyle='--', linewidth=0.5, alpha=0.5)
            ax.spines['bottom'].set_color('#404040')
            ax.spines['top'].set_color('#404040')
            ax.spines['left'].set_color('#404040')
            ax.spines['right'].set_color('#404040')
        
        # Parse data
        dates = []
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []
        
        for c in candles:
            try:
                if isinstance(c['timestamp'], str):
                    dt = datetime.fromisoformat(c['timestamp'].replace('Z', '+00:00'))
                else:
                    dt = c['timestamp']
                dates.append(mdates.date2num(dt))
            except:
                dates.append(mdates.date2num(datetime.now()))
            
            opens.append(c['open'])
            highs.append(c['high'])
            lows.append(c['low'])
            closes.append(c['close'])
            volumes.append(c.get('volume', 0))
        
        # Calculate candle width dynamically based on data spacing
        # Use 70% of average distance between candles untuk consistency
        if len(dates) > 1:
            # Calculate average spacing between candles
            spacings = [dates[i+1] - dates[i] for i in range(len(dates)-1)]
            avg_spacing = sum(spacings) / len(spacings)
            # Use 70% of average spacing untuk candle width
            width = avg_spacing * 0.7
        else:
            # Fallback untuk single candle
            width = 0.01
        
        # Ensure minimum width untuk visibility
        width = max(width, 0.0005)
        
        for i in range(len(dates)):
            o, h, l, c = opens[i], highs[i], lows[i], closes[i]
            color = UP_COLOR if c >= o else DOWN_COLOR
            
            # Wick (line)
            self.ax.plot([dates[i], dates[i]], [l, h], color=color, linewidth=1.5, zorder=3)
            
            # Body (rectangle)
            self.ax.add_patch(
                Rectangle(
                    (dates[i] - width/2, min(o, c)),
                    width,
                    abs(c - o),
                    facecolor=color,
                    edgecolor=color,
                    linewidth=1.5,
                    zorder=4
                )
            )
        
        # Plot volume dengan same width
        colors_vol = [UP_COLOR if closes[i] >= opens[i] else DOWN_COLOR for i in range(len(dates))]
        self.ax_volume.bar(dates, volumes, width=width, color=colors_vol, alpha=0.6)
        
        # Plot SMA jika ada
        if len(closes) >= 20:
            sma_values = []
            for i in range(len(closes)):
                if i < 19:
                    sma_values.append(None)
                else:
                    sma_values.append(sum(closes[i-19:i+1]) / 20)
            
            valid_dates = [dates[i] for i in range(len(sma_values)) if sma_values[i] is not None]
            valid_sma = [v for v in sma_values if v is not None]
            
            if valid_dates:
                self.ax.plot(valid_dates, valid_sma, color='#74b9ff', 
                           linewidth=1.5, label='SMA 20', alpha=0.8)
                self.ax.legend(facecolor=CHART_BG, edgecolor='gray', 
                             labelcolor=TEXT_COLOR, loc='upper left')
        
        # Format x-axis
        self.ax.xaxis_date()
        self.ax_volume.xaxis_date()
        
        if self.current_timeframe in ['M15', 'M30', 'H1']:
            formatter = mdates.DateFormatter('%H:%M')
        else:
            formatter = mdates.DateFormatter('%m/%d')
        
        self.ax_volume.xaxis.set_major_formatter(formatter)
        self.fig.autofmt_xdate()
        
        # Title - Show candle count
        candle_count = len(candles)
        self.ax.set_title(
            f"{self.current_symbol} {self.current_timeframe} - {candle_count} Candles (Max 100)",
            color='white',
            fontsize=12,
            fontweight='bold'
        )
        
        self.canvas.draw()

    def _update_indicators_display(self):
        """Update indicator labels."""
        for key, config in self.indicator_labels.items():
            value = self.indicators_data.get(key)
            label = config['label']
            fmt = config['format']
            
            if value is not None:
                # Special formatting untuk trend
                if key == 'trend':
                    trend_colors = {
                        'strong_bullish': '#00ff00',
                        'bullish': '#90ff90',
                        'neutral': '#ffff00',
                        'bearish': '#ff9090',
                        'strong_bearish': '#ff0000'
                    }
                    color = trend_colors.get(value, '#888888')
                    label.configure(text=str(value).upper(), text_color=color)
                else:
                    # Format numerik
                    try:
                        text = fmt.format(value)
                        label.configure(text=text)
                    except:
                        label.configure(text=str(value))
            else:
                label.configure(text='N/A', text_color='#666666')

    def _schedule_auto_refresh(self):
        """Schedule auto-refresh setiap 5 detik."""
        if self.winfo_exists():
            if self.var_auto.get() and self.current_symbol:
                self._load_chart_data()
            
            self.after(5000, self._schedule_auto_refresh)

    def _simulate_data(self):
        """Generate dummy OHLC data untuk testing."""
        self.log_callback("Generating simulation data...")
        
        candles = []
        price = 1.0850 if 'EUR' in (self.current_symbol or '') else 2030.0
        now = datetime.now()
        
        # Generate 100 candles
        for i in range(100):
            timestamp = now - timedelta(minutes=15 * (50 - i))
            
            change = random.uniform(-0.0010, 0.0010)
            open_p = price
            close_p = price + change
            high_p = max(open_p, close_p) + random.uniform(0, 0.0005)
            low_p = min(open_p, close_p) - random.uniform(0, 0.0005)
            volume = random.randint(100, 1000)
            
            candles.append({
                'timestamp': timestamp.isoformat(),
                'open': open_p,
                'high': high_p,
                'low': low_p,
                'close': close_p,
                'volume': volume
            })
            
            price = close_p
        
        # Add ke chart manager
        if self.current_symbol:
            self.chart_manager.add_ohlcv_batch(
                self.current_symbol,
                self.current_timeframe,
                candles
            )
            self._load_chart_data()
        else:
            # Just display tanpa menyimpan
            self._update_chart_display(candles)
            self.lbl_status.configure(text="Simulated 100 candles displayed", text_color='#00aaff')

    def _load_values(self):
        """Load default values (BaseTab requirement)."""
        pass

    def save_config(self):
        """Save chart configuration (BaseTab requirement)."""
        pass

    def refresh(self):
        """Public method untuk refresh chart."""
        self._load_chart_data()
