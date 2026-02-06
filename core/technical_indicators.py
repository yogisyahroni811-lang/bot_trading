"""
Technical Indicators Calculator
Fast calculation untuk technical indicators dari chart buffer
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from decimal import Decimal
from core.logger import get_logger

logger = get_logger(__name__)


class TechnicalIndicators:
    """
    Calculate technical indicators dari OHLCV data.
    Optimized untuk 100-candle buffer.
    """
    
    @staticmethod
    def sma(data: List[float], period: int) -> Optional[float]:
        """Simple Moving Average."""
        if len(data) < period:
            return None
        return sum(data[-period:]) / period
    
    @staticmethod
    def ema(data: List[float], period: int) -> Optional[float]:
        """Exponential Moving Average."""
        if len(data) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema_values = [data[0]]  # Start with first value
        
        for price in data[1:]:
            ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
        
        return ema_values[-1]
    
    @staticmethod
    def rsi(closes: List[float], period: int = 14) -> Optional[float]:
        """Relative Strength Index."""
        if len(closes) < period + 1:
            return None
        
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    @staticmethod
    def macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Dict]:
        """MACD (Moving Average Convergence Divergence)."""
        if len(closes) < slow:
            return None
        
        # Calculate EMAs
        def calc_ema(data, period):
            multiplier = 2 / (period + 1)
            ema = data[0]
            for price in data[1:]:
                ema = (price - ema) * multiplier + ema
            return ema
        
        ema_fast = calc_ema(closes, fast)
        ema_slow = calc_ema(closes, slow)
        
        macd_line = ema_fast - ema_slow
        
        # Calculate signal line (EMA of MACD)
        macd_history = []
        for i in range(slow, len(closes)):
            e_fast = calc_ema(closes[i-slow:i-slow+fast], fast) if i-slow+fast <= len(closes) else ema_fast
            e_slow = calc_ema(closes[i-slow:i], slow)
            macd_history.append(e_fast - e_slow)
        
        signal_line = calc_ema(macd_history, signal) if len(macd_history) >= signal else macd_line
        
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram,
            'trend': 'bullish' if histogram > 0 else 'bearish'
        }
    
    @staticmethod
    def bollinger_bands(closes: List[float], period: int = 20, std_dev: float = 2.0) -> Optional[Dict]:
        """Bollinger Bands."""
        if len(closes) < period:
            return None
        
        recent = closes[-period:]
        sma = sum(recent) / period
        variance = sum((x - sma) ** 2 for x in recent) / period
        std = np.sqrt(variance)
        
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        current = closes[-1]
        position = (current - lower) / (upper - lower) if upper != lower else 0.5
        
        return {
            'upper': upper,
            'middle': sma,
            'lower': lower,
            'bandwidth': ((upper - lower) / sma) * 100,
            'position': position,  # 0 = at lower, 1 = at upper
            'squeeze': std < np.mean([np.std(closes[i:i+period]) for i in range(0, len(closes)-period, period)]) if len(closes) >= period * 2 else False
        }
    
    @staticmethod
    def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
        """Average True Range."""
        if len(highs) < period + 1 or len(lows) < period + 1:
            return None
        
        true_ranges = []
        for i in range(1, len(highs)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            true_ranges.append(max(high_low, high_close, low_close))
        
        return sum(true_ranges[-period:]) / period
    
    @staticmethod
    def stochastic(highs: List[float], lows: List[float], closes: List[float], 
                   k_period: int = 14, d_period: int = 3) -> Optional[Dict]:
        """Stochastic Oscillator."""
        if len(highs) < k_period:
            return None
        
        recent_high = max(highs[-k_period:])
        recent_low = min(lows[-k_period:])
        current_close = closes[-1]
        
        if recent_high == recent_low:
            k = 50.0
        else:
            k = ((current_close - recent_low) / (recent_high - recent_low)) * 100
        
        # %D is SMA of %K
        d = k  # Simplified, ideally calculate SMA of last k_period %K values
        
        return {
            'k': k,
            'd': d,
            'signal': 'oversold' if k < 20 else 'overbought' if k > 80 else 'neutral'
        }
    
    @staticmethod
    def find_structure_levels(highs: List[float], lows: List[float], lookback: int = 20) -> Dict:
        """Find support and resistance levels (structure)."""
        if len(highs) < lookback:
            return {'support': None, 'resistance': None, 'structure_high': None, 'structure_low': None}
        
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        
        structure_high = max(recent_highs)
        structure_low = min(recent_lows)
        
        # Find key levels (multiple touches)
        from collections import Counter
        
        # Round to reasonable precision
        rounded_highs = [round(h, 5) for h in recent_highs]
        rounded_lows = [round(l, 5) for l in recent_lows]
        
        high_counts = Counter(rounded_highs)
        low_counts = Counter(rounded_lows)
        
        resistance = max(high_counts.items(), key=lambda x: x[1])[0] if high_counts else structure_high
        support = max(low_counts.items(), key=lambda x: x[1])[0] if low_counts else structure_low
        
        return {
            'support': support,
            'resistance': resistance,
            'structure_high': structure_high,
            'structure_low': structure_low,
            'range': structure_high - structure_low
        }
    
    @classmethod
    def calculate_all(cls, opens: List[float], highs: List[float], lows: List[float], 
                     closes: List[float], volumes: List[int]) -> Dict:
        """Calculate all technical indicators."""
        if len(closes) < 20:
            logger.warning("Not enough data untuk calculate all indicators")
            return {}
        
        indicators = {
            'sma_20': cls.sma(closes, 20),
            'sma_50': cls.sma(closes, 50) if len(closes) >= 50 else None,
            'ema_9': cls.ema(closes, 9),
            'ema_21': cls.ema(closes, 21),
            'rsi_14': cls.rsi(closes, 14),
            'macd': cls.macd(closes),
            'bollinger': cls.bollinger_bands(closes),
            'atr_14': cls.atr(highs, lows, closes, 14),
            'stochastic': cls.stochastic(highs, lows, closes),
            'structure': cls.find_structure_levels(highs, lows),
            'current_price': closes[-1] if closes else None,
            'price_change_24h': ((closes[-1] - closes[0]) / closes[0] * 100) if closes and len(closes) > 1 else 0
        }
        
        # Determine trend
        if len(closes) >= 20:
            sma20 = indicators.get('sma_20')
            ema9 = indicators.get('ema_9')
            
            if sma20 and ema9:
                if closes[-1] > ema9 > sma20:
                    indicators['trend'] = 'strong_bullish'
                elif closes[-1] > sma20:
                    indicators['trend'] = 'bullish'
                elif closes[-1] < ema9 < sma20:
                    indicators['trend'] = 'strong_bearish'
                elif closes[-1] < sma20:
                    indicators['trend'] = 'bearish'
                else:
                    indicators['trend'] = 'neutral'
            else:
                indicators['trend'] = 'neutral'
        else:
            indicators['trend'] = 'unknown'
        
        return indicators


class IndicatorCache:
    """Cache untuk technical indicators untuk avoid recalculation."""
    
    def __init__(self):
        self.cache: Dict[str, Dict] = {}
        self.last_calculation: Dict[str, float] = {}
        self.cache_ttl = 5  # Refresh setiap 5 detik
    
    def get_key(self, symbol: str, timeframe: str) -> str:
        return f"{symbol}_{timeframe}"
    
    def get(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """Get cached indicators jika masih valid."""
        key = self.get_key(symbol, timeframe)
        
        if key in self.cache:
            last_calc = self.last_calculation.get(key, 0)
            if time.time() - last_calc < self.cache_ttl:
                return self.cache[key]
        
        return None
    
    def set(self, symbol: str, timeframe: str, indicators: Dict):
        """Cache indicators."""
        key = self.get_key(symbol, timeframe)
        self.cache[key] = indicators
        self.last_calculation[key] = time.time()
    
    def invalidate(self, symbol: str = None, timeframe: str = None):
        """Invalidate cache."""
        if symbol and timeframe:
            key = self.get_key(symbol, timeframe)
            self.cache.pop(key, None)
            self.last_calculation.pop(key, None)
        elif symbol:
            keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{symbol}_")]
            for key in keys_to_remove:
                self.cache.pop(key, None)
                self.last_calculation.pop(key, None)
        else:
            self.cache.clear()
            self.last_calculation.clear()


# Global cache instance
_indicator_cache = IndicatorCache()


def calculate_indicators(symbol: str, timeframe: str, 
                        opens: List[float], highs: List[float], 
                        lows: List[float], closes: List[float], 
                        volumes: List[int], use_cache: bool = True) -> Dict:
    """
    Calculate all technical indicators untuk symbol/timeframe.
    Uses cache untuk performance.
    """
    global _indicator_cache
    
    # Check cache
    if use_cache:
        cached = _indicator_cache.get(symbol, timeframe)
        if cached:
            return cached
    
    # Calculate all indicators
    indicators = TechnicalIndicators.calculate_all(opens, highs, lows, closes, volumes)
    
    # Add metadata
    indicators['symbol'] = symbol
    indicators['timeframe'] = timeframe
    indicators['candle_count'] = len(closes)
    indicators['calculated_at'] = time.time()
    
    # Cache result
    if use_cache:
        _indicator_cache.set(symbol, timeframe, indicators)
    
    return indicators


def invalidate_cache(symbol: str = None, timeframe: str = None):
    """Invalidate indicator cache."""
    global _indicator_cache
    _indicator_cache.invalidate(symbol, timeframe)
