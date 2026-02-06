"""
Chart Manager - Central manager untuk chart data dan indicators
Integrates buffer, indicators, dan provides API untuk AI
"""

import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from threading import Lock
from decimal import Decimal

from core.chart_buffer import (
    get_or_create_buffer, get_buffer, Candle, 
    get_all_symbols, clear_symbol, clear_all_buffers
)
from core.technical_indicators import calculate_indicators, invalidate_cache
from core.logger import get_logger

logger = get_logger(__name__)


class ChartManager:
    """
    Central manager untuk chart operations.
    Provides unified API untuk GUI, AI, dan MT5 sync.
    """
    
    TIMEFRAMES = ['M15', 'M30', 'H1', 'H4', 'D1']
    
    def __init__(self):
        self._lock = Lock()
        self._last_sync: Dict[str, Dict[str, float]] = {}  # symbol -> timeframe -> timestamp
        logger.info("ChartManager initialized")
    
    def add_candle_data(self, symbol: str, timeframe: str, 
                       timestamp: datetime, open_price: float, 
                       high: float, low: float, close: float, 
                       volume: int):
        """
        Add candle data dari MT5 atau sumber lain.
        Ini adalah entry point utama untuk chart data.
        """
        try:
            # Normalize symbol
            symbol = symbol.upper().replace('/', '')
            timeframe = timeframe.upper()
            
            if timeframe not in self.TIMEFRAMES:
                logger.warning(f"Unsupported timeframe: {timeframe}")
                return False
            
            # Create candle
            candle = Candle(
                timestamp=timestamp,
                open=Decimal(str(open_price)),
                high=Decimal(str(high)),
                low=Decimal(str(low)),
                close=Decimal(str(close)),
                volume=volume
            )
            
            # Get atau create buffer
            buffer = get_or_create_buffer(symbol)
            buffer.add_candle(timeframe, candle)
            
            # Record sync time
            if symbol not in self._last_sync:
                self._last_sync[symbol] = {}
            self._last_sync[symbol][timeframe] = time.time()
            
            # Invalidate cache untuk indicators
            invalidate_cache(symbol, timeframe)
            
            logger.debug(f"Added {timeframe} candle untuk {symbol}: {close}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to add candle data: {e}")
            return False
    
    def add_ohlcv_batch(self, symbol: str, timeframe: str, 
                       candles: List[Dict]) -> bool:
        """
        Add multiple candles (untuk historical data atau backfill).
        """
        try:
            symbol = symbol.upper().replace('/', '')
            timeframe = timeframe.upper()
            
            buffer = get_or_create_buffer(symbol)
            
            for candle_data in candles:
                candle = Candle(
                    timestamp=datetime.fromisoformat(candle_data['timestamp']),
                    open=Decimal(str(candle_data['open'])),
                    high=Decimal(str(candle_data['high'])),
                    low=Decimal(str(candle_data['low'])),
                    close=Decimal(str(candle_data['close'])),
                    volume=candle_data['volume']
                )
                buffer.add_candle(timeframe, candle)
            
            invalidate_cache(symbol, timeframe)
            logger.info(f"Added {len(candles)} {timeframe} candles untuk {symbol}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to add batch candles: {e}")
            return False
    
    def get_chart_data(self, symbol: str, timeframe: str) -> Dict:
        """
        Get chart data + indicators untuk symbol/timeframe.
        Primary API untuk AI decision making.
        """
        try:
            symbol = symbol.upper().replace('/', '')
            buffer = get_buffer(symbol)
            
            if not buffer:
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'available': False,
                    'error': 'No data available'
                }
            
            # Get OHLCV arrays
            opens, highs, lows, closes, volumes = buffer.get_ohlcv(timeframe)
            
            if len(closes) < 5:
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'available': False,
                    'error': 'Insufficient data'
                }
            
            # Calculate indicators
            indicators = calculate_indicators(
                symbol, timeframe, opens, highs, lows, closes, volumes
            )
            
            # Get last candle info
            last_candle = buffer.get_last_candle(timeframe)
            
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'available': True,
                'candle_count': len(closes),
                'last_price': float(last_candle.close) if last_candle else None,
                'last_update': last_candle.timestamp.isoformat() if last_candle else None,
                'ohlcv': {
                    'open': opens[-1],
                    'high': highs[-1],
                    'low': lows[-1],
                    'close': closes[-1],
                    'volume': volumes[-1]
                },
                'indicators': indicators
            }
        
        except Exception as e:
            logger.error(f"Failed to get chart data untuk {symbol} {timeframe}: {e}")
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'available': False,
                'error': str(e)
            }
    
    def get_multi_timeframe_data(self, symbol: str) -> Dict[str, Dict]:
        """
        Get data untuk all timeframes.
        Berguna untuk multi-timeframe analysis (The Judge Tier 1).
        """
        result = {}
        for tf in self.TIMEFRAMES:
            result[tf] = self.get_chart_data(symbol, tf)
        return result
    
    def get_chart_arrays(self, symbol: str, timeframe: str) -> Tuple[List, List, List, List, List]:
        """
        Get raw OHLCV arrays untuk custom calculations.
        """
        buffer = get_buffer(symbol)
        if buffer:
            return buffer.get_ohlcv(timeframe)
        return [], [], [], [], []
    
    def get_candles(self, symbol: str, timeframe: str, limit: int = 100) -> List[Dict]:
        """
        Get candles sebagai list of dictionaries untuk GUI display.
        """
        buffer = get_buffer(symbol)
        if not buffer:
            return []
        
        candles = buffer.get_candles(timeframe)
        if limit:
            candles = candles[-limit:]
        
        return [c.to_dict() for c in candles]
    
    def get_all_symbols_status(self) -> Dict:
        """Get status semua symbols."""
        symbols = get_all_symbols()
        status = {}
        
        for symbol in symbols:
            buffer = get_buffer(symbol)
            if buffer:
                status[symbol] = {
                    'buffer_sizes': buffer.get_buffer_sizes(),
                    'last_prices': {tf: float(price) if price else None 
                                   for tf, price in buffer.last_prices.items()}
                }
        
        return status
    
    def is_data_fresh(self, symbol: str, timeframe: str, max_age_seconds: int = 300) -> bool:
        """Check if data is fresh (updated dalam max_age_seconds)."""
        if symbol not in self._last_sync:
            return False
        if timeframe not in self._last_sync[symbol]:
            return False
        
        last_update = self._last_sync[symbol][timeframe]
        return (time.time() - last_update) < max_age_seconds
    
    def get_data_age(self, symbol: str, timeframe: str) -> Optional[float]:
        """Get age of data in seconds."""
        if symbol in self._last_sync and timeframe in self._last_sync[symbol]:
            return time.time() - self._last_sync[symbol][timeframe]
        return None
    
    def clear_symbol_data(self, symbol: str):
        """Clear all data untuk symbol."""
        clear_symbol(symbol)
        if symbol in self._last_sync:
            del self._last_sync[symbol]
        invalidate_cache(symbol)
        logger.info(f"Cleared all data untuk {symbol}")
    
    def clear_all_data(self):
        """Clear all chart data."""
        clear_all_buffers()
        self._last_sync.clear()
        invalidate_cache()
        logger.info("Cleared all chart data")


# Singleton instance
_chart_manager = None

def get_chart_manager() -> ChartManager:
    """Get global ChartManager instance."""
    global _chart_manager
    if _chart_manager is None:
        _chart_manager = ChartManager()
    return _chart_manager
