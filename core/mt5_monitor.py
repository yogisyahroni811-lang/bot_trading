"""
MT5/EA Connection Monitor
Track connection status dari MT5 EA
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict
from threading import Lock
from core.logger import get_logger

logger = get_logger(__name__)

class MT5ConnectionMonitor:
    """
    Monitor status koneksi MT5 EA.
    
    Status:
    - 'disconnected' (Abu-abu): Belum pernah terhubung atau tidak ada data > 30 detik
    - 'connected' (Hijau): Menerima data dari EA dalam 30 detik terakhir
    - 'error' (Merah): Ada error dari EA atau response error
    """
    
    STATUS_FILE = "config/mt5_connection.json"
    TIMEOUT_SECONDS = 30  # Dianggap disconnect jika tidak ada data 30 detik
    
    def __init__(self):
        self.last_ping_time = None
        self.last_data_time = None
        self.connection_status = 'disconnected'  # 'disconnected', 'connected', 'error'
        self.error_message = None
        self.ea_version = None
        self.total_requests = 0
        self.error_count = 0
        self.lock = Lock()
        
        # Load previous state jika ada
        self._load_state()
    
    def record_ping(self, ea_version: str = None):
        """Record ping dari EA (heartbeat)."""
        with self.lock:
            self.last_ping_time = datetime.now()
            self.connection_status = 'connected'
            self.error_message = None
            
            if ea_version:
                self.ea_version = ea_version
            
            self._save_state()
    
    def record_data_received(self, symbol: str = None):
        """Record saat menerima data market dari EA."""
        with self.lock:
            self.last_data_time = datetime.now()
            self.connection_status = 'connected'
            self.error_message = None
            self.total_requests += 1
            
            logger.debug(f"Data received from MT5: {symbol or 'Unknown'}")
            self._save_state()
    
    def record_error(self, error_msg: str):
        """Record error dari EA atau sistem."""
        with self.lock:
            self.error_count += 1
            self.error_message = error_msg
            
            # Hanya set error jika belum connected
            # atau jika error berulang
            if self.connection_status != 'connected' or self.error_count > 3:
                self.connection_status = 'error'
            
            logger.error(f"MT5 Connection Error: {error_msg}")
            self._save_state()
    
    def check_connection_status(self) -> str:
        """
        Check current connection status.
        
        Returns:
            'disconnected', 'connected', atau 'error'
        """
        with self.lock:
            # Jika sedang error, tetap error sampai di-reset
            if self.connection_status == 'error' and self.error_message:
                # Cek apakah sudah 60 detik tanpa error baru
                if self.last_data_time:
                    time_since_data = (datetime.now() - self.last_data_time).total_seconds()
                    if time_since_data > 60:
                        # Reset ke disconnected setelah 60 detik
                        self.connection_status = 'disconnected'
                        self.error_message = None
                        self.error_count = 0
                return self.connection_status
            
            # Cek timeout untuk connected
            if self.connection_status == 'connected':
                last_activity = self.last_data_time or self.last_ping_time
                
                if last_activity:
                    time_diff = (datetime.now() - last_activity).total_seconds()
                    
                    if time_diff > self.TIMEOUT_SECONDS:
                        self.connection_status = 'disconnected'
                        logger.info(f"MT5 disconnected (no activity for {time_diff:.0f}s)")
            
            return self.connection_status
    
    def get_status_info(self) -> Dict:
        """Get detailed status information."""
        status = self.check_connection_status()
        
        info = {
            'status': status,
            'status_text': self._get_status_text(status),
            'color': self._get_status_color(status),
            'last_ping': self._format_time(self.last_ping_time),
            'last_data': self._format_time(self.last_data_time),
            'ea_version': self.ea_version or 'Unknown',
            'total_requests': self.total_requests,
            'error_count': self.error_count,
            'error_message': self.error_message
        }
        
        return info
    
    def _get_status_text(self, status: str) -> str:
        """Get human-readable status text."""
        texts = {
            'disconnected': 'MT5: Not Connected',
            'connected': 'MT5: Connected',
            'error': 'MT5: Error'
        }
        return texts.get(status, 'MT5: Unknown')
    
    def _get_status_color(self, status: str) -> str:
        """Get color code for status."""
        colors = {
            'disconnected': '#888888',  # Abu-abu
            'connected': '#00ff00',     # Hijau
            'error': '#ff0000'          # Merah
        }
        return colors.get(status, '#888888')
    
    def _format_time(self, dt: Optional[datetime]) -> Optional[str]:
        """Format datetime untuk display."""
        if not dt:
            return None
        return dt.strftime('%H:%M:%S')
    
    def _save_state(self):
        """Save state ke file."""
        try:
            os.makedirs(os.path.dirname(self.STATUS_FILE), exist_ok=True)
            
            state = {
                'connection_status': self.connection_status,
                'last_ping_time': self.last_ping_time.isoformat() if self.last_ping_time else None,
                'last_data_time': self.last_data_time.isoformat() if self.last_data_time else None,
                'ea_version': self.ea_version,
                'total_requests': self.total_requests,
                'error_count': self.error_count,
                'error_message': self.error_message,
                'saved_at': datetime.now().isoformat()
            }
            
            with open(self.STATUS_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        
        except Exception as e:
            logger.error(f"Failed to save MT5 connection state: {e}")
    
    def _load_state(self):
        """Load state dari file."""
        try:
            if os.path.exists(self.STATUS_FILE):
                with open(self.STATUS_FILE, 'r') as f:
                    state = json.load(f)
                
                self.connection_status = state.get('connection_status', 'disconnected')
                self.ea_version = state.get('ea_version')
                self.total_requests = state.get('total_requests', 0)
                self.error_count = state.get('error_count', 0)
                
                # Parse times
                if state.get('last_ping_time'):
                    self.last_ping_time = datetime.fromisoformat(state['last_ping_time'])
                if state.get('last_data_time'):
                    self.last_data_time = datetime.fromisoformat(state['last_data_time'])
                
                logger.info(f"Loaded MT5 connection state: {self.connection_status}")
        
        except Exception as e:
            logger.error(f"Failed to load MT5 connection state: {e}")
    
    def reset(self):
        """Reset connection state."""
        with self.lock:
            self.connection_status = 'disconnected'
            self.last_ping_time = None
            self.last_data_time = None
            self.error_message = None
            self.error_count = 0
            self._save_state()
            logger.info("MT5 connection state reset")


# Singleton
_connection_monitor = None

def get_mt5_monitor() -> MT5ConnectionMonitor:
    """Get global MT5ConnectionMonitor instance."""
    global _connection_monitor
    if _connection_monitor is None:
        _connection_monitor = MT5ConnectionMonitor()
    return _connection_monitor