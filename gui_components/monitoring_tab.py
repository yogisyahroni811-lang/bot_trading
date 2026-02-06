"""
Monitoring Dashboard Tab.

Displays live server health metrics and trade decision audit logs.
"""

import customtkinter as ctk
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Optional
from core.audit_log import AuditLogger
from core.logger import get_logger

logger = get_logger(__name__)

class MonitoringTab(ctk.CTkFrame):
    def __init__(self, parent, audit_logger: Optional[AuditLogger] = None):
        super().__init__(parent)
        
        # Use provided logger or create new instance
        self.audit_logger = audit_logger or AuditLogger()
        self.should_update = False
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the dashboard layout."""
        # Split into two sections: Metrics (Top) and Logs (Bottom)
        self.grid_rowconfigure(0, weight=0) # Metrics
        self.grid_rowconfigure(1, weight=1) # Logs
        self.grid_columnconfigure(0, weight=1)
        
        # --- Section 1: Server Health (Placeholder for now) ---
        self.metrics_frame = ctk.CTkFrame(self, height=60, fg_color="#1e1e24")
        self.metrics_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            self.metrics_frame, 
            text="System Monitor", 
            font=("Roboto", 16, "bold")
        ).pack(side="left", padx=15, pady=10)
        
        self.refresh_btn = ctk.CTkButton(
            self.metrics_frame,
            text="Refresh Logs",
            width=100,
            command=self.refresh_logs,
            fg_color="#4B4ACF", 
            hover_color="#3B3A9F"
        )
        self.refresh_btn.pack(side="right", padx=5, pady=10)

        self.export_btn = ctk.CTkButton(
            self.metrics_frame,
            text="Export CSV",
            width=100,
            command=self.export_csv,
            fg_color="#2D2D2D",
            hover_color="#3D3D3D"
        )
        self.export_btn.pack(side="right", padx=5, pady=10)
        
        # --- Section 2: Audit Logs Table ---
        self.logs_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.logs_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        # We need to use standard tkinter Treeview for the table as CTk doesn't have one
        # Styling the Treeview to match Dark Mode
        style = ttk.Style()
        style.theme_use("clam")
        
        style.configure(
            "Audit.Treeview",
            background="#2b2b2b",
            foreground="white",
            fieldbackground="#2b2b2b",
            borderwidth=0,
            rowheight=30
        )
        style.configure(
            "Audit.Treeview.Heading",
            background="#1e1e24",
            foreground="white",
            relief="flat",
            font=("Roboto", 10, "bold")
        )
        style.map("Audit.Treeview", background=[("selected", "#4B4ACF")])
        
        columns = ("timestamp", "symbol", "decision", "score", "reason")
        self.tree = ttk.Treeview(
            self.logs_frame, 
            columns=columns, 
            show="headings",
            style="Audit.Treeview",
            selectmode="browse"
        )
        
        # Define Columns
        self.tree.heading("timestamp", text="Time")
        self.tree.column("timestamp", width=150)
        
        self.tree.heading("symbol", text="Symbol")
        self.tree.column("symbol", width=80)
        
        self.tree.heading("decision", text="Decision")
        self.tree.column("decision", width=80)
        
        self.tree.heading("score", text="Score")
        self.tree.column("score", width=60)
        
        self.tree.heading("reason", text="Judge Reason")
        self.tree.column("reason", width=400)
        
        # Scrollbar
        scrollbar = ctk.CTkScrollbar(self.logs_frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind double click
        self.tree.bind("<Double-1>", self.on_row_double_click)
        
        # Start auto-refresh
        self.start_monitoring()

    def start_monitoring(self):
        """Start the monitoring loop."""
        self.should_update = True
        self.refresh_logs()
        # Schedule next update in 5 seconds
        self.after(5000, self.auto_refresh)
        
    def stop_monitoring(self):
        """Stop the monitoring."""
        self.should_update = False

    def auto_refresh(self):
        if self.should_update:
            self.refresh_logs()
            self.after(5000, self.auto_refresh)

    def refresh_logs(self):
        """Fetch and display logs."""
        # Fetch logs in a separate thread to avoid freezing UI? 
        # For SQLite it's fast enough for main thread usually, but let's be safe later.
        # For now, keep it simple.
        logs = self.audit_logger.fetch_recent_logs(limit=50)
        
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Insert new
        for log in logs:
            # Format score
            score_formatted = f"{log.get('final_score', 0.0):.2f}"
            
            # Combine reasons if tier 3 missing
            reason = log.get('tier_3_reason') or log.get('tier_1_reason', 'N/A')
            
            self.tree.insert(
                "", 
                "end", 
                values=(
                    log.get('timestamp'),
                    log.get('symbol'),
                    log.get('decision'),
                    score_formatted,
                    reason
                )
            )

    def export_csv(self):
        """Export logs to CSV."""
        from tkinter import filedialog
        import csv
        from datetime import datetime
        
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv")],
                initialfile=f"trade_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            
            if not filename:
                return
                
            logs = self.audit_logger.fetch_recent_logs(limit=1000) # Fetch more for export
            
            if not logs:
                return

            keys = logs[0].keys()
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(logs)
                
            tk.messagebox.showinfo("Export Success", f"Exported {len(logs)} rows to {filename}")
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            tk.messagebox.showerror("Export Failed", str(e))

    def on_row_double_click(self, event):
        """Show details popup on double click."""
        item = self.tree.selection()
        if not item:
            return
            
        # Get data (we need to fetch full data or store it hidden)
        # Simplified: Just grab from row values for now, 
        # but ideally we want the full Pro/Con arguments which are not in the table columns.
        # Let's get the index and re-fetch or look up in a local cache?
        # Actually, since we just refreshed, we could store `self.current_logs`.
        # For MVP, let's just show what we have + logic to fetch details if needed.
        
        # Better: Store the log object in a hidden way or just use the row index to find in self.current_logs
        pass # Todo: Detail view
