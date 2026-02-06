
import sys
import os
import customtkinter as ctk
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.getcwd())

from gui_components.chart_tab import ChartTab

def log_msg(msg):
    print(f"[LOG] {msg}")

def test_chart_tab():
    ctk.set_appearance_mode("Dark")
    root = ctk.CTk()
    root.geometry("800x600")
    
    config_mock = MagicMock()
    config_mock.load_config.return_value = {}
    config_mock.config = {}

    print("Attempting to instantiate ChartTab...")
    try:
        chart_tab = ChartTab(
            parent=root,
            config_manager=config_mock,
            log_callback=log_msg
        )
        chart_tab.pack(fill="both", expand=True)
        print("ChartTab instantiated successfully.")
        
        # Verify matplotlib setup
        print("Checking matplotlib canvas...")
        if chart_tab.canvas:
            print("Canvas exists.")
        
        # Test Simulate
        print("Testing simulation...")
        chart_tab._simulate_data()
        
        root.after(2000, root.destroy)
        root.mainloop()
        
    except Exception as e:
        print(f"CRASHED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chart_tab()
