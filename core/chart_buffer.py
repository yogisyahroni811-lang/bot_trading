"""
Chart Buffer - Ring Buffer untuk OHLCV data
Menyimpan 100 candle terakhir per timeframe dengan auto-cleanup
"""

import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import deque
from threading import Lock
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, asdict
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Candle:
    """Single candlestick data."""
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'open': float(self.open),
            'high': float(self.high),
            'low': float(self.low),
            'close': float(self.close),
            'volume': self.volume
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Candle':
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            open=Decimal(str(data['open'])),
            high=Decimal(str(data['high'])),
            low=Decimal(str(data['low'])),
            close=Decimal(str(data['close'])),
            volume=data['volume']
        )


class RingBuffer:
    """
    Circular buffer untuk candle data.
    O(1) insert, O(1) access, auto-maintains max size.
    """
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.buffer: deque = deque(maxlen=max_size)
        self.lock = Lock()
        self.last_update = None
    
    def add(self, candle: Candle):
        """Add new candle. Auto-removes oldest if full."""
        with self.lock:
            self.buffer.append(candle)
            self.last_update = datetime.now()
    
    def get_all(self) -> List[Candle]:
        """Get all candles (oldest first)."""
        with self.lock:
            return list(self.buffer)
    
    def get_last(self, n: int = 1) -> List[Candle]:
        """Get last N candles (newest first)."""
        with self.lock:
            return list(self.buffer)[-n:] if n <= len(self.buffer) else list(self.buffer)
    
    def get_last_candle(self) -> Optional[Candle]:
        """Get most recent candle."""
        with self.lock:
            return self.buffer[-1] if self.buffer else None
    
    def get_range(self, start_idx: int, end_idx: int) -> List[Candle]:
        """Get candles in range [start_idx, end_idx)."""
        with self.lock:
            candles = list(self.buffer)
            return candles[start_idx:end_idx]
    
    def clear(self):
        """Clear all data."""
        with self.lock:
            self.buffer.clear()
            self.last_update = None
    
    def __len__(self) -> int:
        with self.lock:
            return len(self.buffer)
    
    def is_full(self) -> bool:
        with self.lock:
            return len(self.buffer) >= self.max_size
    
    def get_timestamps(self) -> List[datetime]:
        """Get all timestamps."""
        with self.lock:
            return [c.timestamp for c in self.buffer]
    
    def get_ohlcv_arrays(self) -> Tuple[List, List, List, List, List]:
        """Get OHLCV as separate arrays untuk technical analysis."""
        with self.lock:
            candles = list(self.buffer)
            opens = [float(c.open) for c in candles]
            highs = [float(c.high) for c in candles]
            lows = [float(c.low) for c in candles]
            closes = [float(c.close) for c in candles]
            volumes = [c.volume for c in candles]
            return opens, highs, lows, closes, volumes


class TimeframeBuffer:
    """Manages ring buffers untuk multiple timeframes."""
    
    TIMEFRAMES = ['M15', 'M30', 'H1', 'H4', 'D1']
    
    def __init__(self, symbol: str, max_candles: int = 100):
        self.symbol = symbol
        self.max_candles = max_candles
        self.buffers: Dict[str, RingBuffer] = {
            tf: RingBuffer(max_candles) for tf in self.TIMEFRAMES
        }
        self.last_prices: Dict[str, Optional[Decimal]] = {tf: None for tf in self.TIMEFRAMES}
        logger.info(f"TimeframeBuffer initialized for {symbol}")
    
    def add_candle(self, timeframe: str, candle: Candle):
        """Add candle ke specific timeframe."""
        if timeframe not in self.buffers:
            logger.warning(f"Unknown timeframe: {timeframe}")
            return
        
        self.buffers[timeframe].add(candle)
        self.last_prices[timeframe] = candle.close
        
        logger.debug(f"Added {timeframe} candle to {self.symbol}: {candle.close}")
    
    def get_candles(self, timeframe: str) -> List[Candle]:
        """Get all candles untuk timeframe."""
        if timeframe in self.buffers:
            return self.buffers[timeframe].get_all()
        return []
    
    def get_last_candle(self, timeframe: str) -> Optional[Candle]:
        """Get last candle untuk timeframe."""
        if timeframe in self.buffers:
            return self.buffers[timeframe].get_last_candle()
        return None
    
    def get_ohlcv(self, timeframe: str) -> Tuple[List, List, List, List, List]:
        """Get OHLCV arrays untuk timeframe."""
        if timeframe in self.buffers:
            return self.buffers[timeframe].get_ohlcv_arrays()
        return [], [], [], [], []
    
    def get_all_timeframes_data(self) -> Dict[str, List[Candle]]:
        """Get data untuk all timeframes."""
        return {tf: self.buffers[tf].get_all() for tf in self.TIMEFRAMES}
    
    def clear_timeframe(self, timeframe: str):
        """Clear specific timeframe data."""
        if timeframe in self.buffers:
            self.buffers[timeframe].clear()
            self.last_prices[timeframe] = None
            logger.info(f"Cleared {timeframe} data for {self.symbol}")
    
    def clear_all(self):
        """Clear all timeframe data."""
        for tf in self.TIMEFRAMES:
            self.buffers[tf].clear()
            self.last_prices[tf] = None
        logger.info(f"Cleared all data for {self.symbol}")
    
    def get_buffer_sizes(self) -> Dict[str, int]:
        """Get current buffer sizes."""
        return {tf: len(self.buffers[tf]) for tf in self.TIMEFRAMES}


# Global chart buffer storage
_chart_buffers: Dict[str, TimeframeBuffer] = {}
_buffer_lock = Lock()


def get_or_create_buffer(symbol: str, max_candles: int = 100) -> TimeframeBuffer:
    """Get existing buffer atau create new one."""
    global _chart_buffers
    
    with _buffer_lock:
        if symbol not in _chart_buffers:
            _chart_buffers[symbol] = TimeframeBuffer(symbol, max_candles)
        return _chart_buffers[symbol]


def get_buffer(symbol: str) -> Optional[TimeframeBuffer]:
    """Get existing buffer."""
    with _buffer_lock:
        return _chart_buffers.get(symbol)


def get_all_symbols() -> List[str]:
    """Get all symbols dengan data."""
    with _buffer_lock:
        return list(_chart_buffers.keys())


def clear_symbol(symbol: str):
    """Clear all data untuk symbol."""
    global _chart_buffers
    
    with _buffer_lock:
        if symbol in _chart_buffers:
            del _chart_buffers[symbol]
            logger.info(f"Removed buffer for {symbol}")


def clear_all_buffers():
    """Clear all chart buffers."""
    global _chart_buffers
    
    with _buffer_lock:
        _chart_buffers.clear()
        logger.info("Cleared all chart buffers")
