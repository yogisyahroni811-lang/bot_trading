"""
Custom GUI Widgets for Sentinel-X.

Contains reusable custom widgets extracted from monolithic gui.py.
"""

import customtkinter as ctk


class IntSpinbox(ctk.CTkFrame):
    """
    Custom spinbox widget for integer/float input with +/- buttons.
    
    Originally from gui.py lines 17-71.
    """
    
    def __init__(self, *args, width=100, height=32, step_size=1, command=None, **kwargs):
        super().__init__(*args, width=width, height=height, **kwargs)
        
        self.step_size = step_size
        self.command = command
        
        self.configure(fg_color=("gray78", "gray28"))
        
        self.grid_columnconfigure((0, 2), weight=0)
        self.grid_columnconfigure(1, weight=1)
        
        # Subtract button
        self.subtract_button = ctk.CTkButton(
            self,
            text="-",
            width=height - 6,
            height=height - 6,
            command=self.subtract_button_callback
        )
        self.subtract_button.grid(row=0, column=0, padx=(3, 0), pady=3)
        
        # Entry field
        self.entry = ctk.CTkEntry(self, width=width - (2 * height), height=height - 6, border_width=0)
        self.entry.grid(row=0, column=1, columnspan=1, padx=3, pady=3, sticky="ew")
        
        # Add button
        self.add_button = ctk.CTkButton(
            self,
            text="+",
            width=height - 6,
            height=height - 6,
            command=self.add_button_callback
        )
        self.add_button.grid(row=0, column=2, padx=(0, 3), pady=3)
        
        # Default value
        self.entry.insert(0, "0.0")
    
    def add_button_callback(self):
        """Increment value by step_size."""
        try:
            value = float(self.entry.get()) + self.step_size
            self.entry.delete(0, "end")
            self.entry.insert(0, value)
        except ValueError:
            return
        if self.command is not None:
            self.command()
    
    def subtract_button_callback(self):
        """Decrement value by step_size."""
        try:
            value = float(self.entry.get()) - self.step_size
            self.entry.delete(0, "end")
            self.entry.insert(0, value)
        except ValueError:
            return
        if self.command is not None:
            self.command()
    
    def get(self):
        """Get current value as float."""
        try:
            return float(self.entry.get())
        except ValueError:
            return 0.0
    
    def set(self, value):
        """Set value."""
        self.entry.delete(0, "end")
        self.entry.insert(0, str(float(value)))
