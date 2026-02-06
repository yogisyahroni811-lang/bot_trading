import sys
import os
import multiprocessing
from core.logger import initialize_logger, get_logger

# Helper

def is_frozen():
    return getattr(sys, 'frozen', False)

def start_server(port=8000):
    import uvicorn
    from main import app
    print(f"Server starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)

def start_gui():
    from gui import SentinelXGUI
    root = SentinelXGUI()
    print("GUI starting...")
    root.mainloop()
    print("GUI ended.")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    initialize_logger()
    
    args = sys.argv[1:]
    if "--server" in args:
        start_server()
    else:
        start_gui()
