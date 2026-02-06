"""
Tier 1: Mathematical Analysis & Hard Veto System
Pure math-based analysis with veto power over AI decisions
"""

from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import numpy as np

@dataclass
class Tier1Result:
    """Result from Tier 1 mathematical analysis."""
    trend_direction: str  # 'bullish', 'bearish', 'neutral'
    trend_strength: float  # 0.0 - 1.0
    structure_valid: bool
    veto_reason: Optional[str] = None
    support_levels: list = None
    resistance_levels: list = None
    ma_alignment: str = None  # 'aligned', 'mixed', 'crossing'
    
    def should_veto_buy(self) -> Tuple[bool, str]:
        """Check if BUY should be vetoed."""
        if self.trend_direction == 'bearish' and self.trend_strength > 0.7:
            return True, f"VETO: Bearish trend on higher timeframe (strength: {self.trend_strength:.2f})"
        if not self.structure_valid:
            return True, "VETO: Invalid market structure"
        return False, ""
    
    def should_veto_sell(self) -> Tuple[bool, str]:
        """Check if SELL should be vetoed."""
        if self.trend_direction == 'bullish' and self.trend_strength > 0.7:
            return True, f"VETO: Bullish trend on higher timeframe (strength: {self.trend_strength:.2f})"
        if not self.structure_valid:
            return True, "VETO: Invalid market structure"
        return False, ""

class Tier1MathEngine:
    """
    Pure mathematical analysis - NO AI involvement.
    This has HARD VETO power over AI decisions.
    """
    
    def __init__(self):
        self.min_trend_strength = 0.6  # Minimum to establish trend
        self.veto_threshold = 0.7  # Trend strength needed for veto
    
    def analyze(self, market_data: Dict) -> Tier1Result:
        """
        Perform pure mathematical analysis.
        
        Args:
            market_data: Dict with OHLCV, MAs, structure points
            
        Returns:
            Tier1Result with trend info and veto status
        """
        # Extract data
        candles = market_data.get('candles', [])
        ma_fast = market_data.get('ma_fast', [])
        ma_slow = market_data.get('ma_slow', [])
        ma_trend = market_data.get('ma_trend', [])  # MA200
        
        if not candles or len(candles) < 20:
            return Tier1Result(
                trend_direction='neutral',
                trend_strength=0.0,
                structure_valid=False,
                veto_reason="Insufficient data"
            )
        
        # 1. Trend Direction from MAs
        trend_direction, trend_strength = self._calculate_trend(
            ma_fast, ma_slow, ma_trend, candles
        )
        
        # 2. Market Structure Analysis
        structure_valid, support_levels, resistance_levels = self._analyze_structure(
            candles, trend_direction
        )
        
        # 3. MA Alignment
        ma_alignment = self._check_ma_alignment(ma_fast, ma_slow, ma_trend)
        
        # 4. Veto Logic
        veto_reason = None
        if trend_strength > self.veto_threshold:
            if trend_direction == 'bearish':
                veto_reason = "Strong bearish trend - BUY signals blocked"
            elif trend_direction == 'bullish':
                veto_reason = "Strong bullish trend - SELL signals blocked"
        
        return Tier1Result(
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            structure_valid=structure_valid,
            veto_reason=veto_reason,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            ma_alignment=ma_alignment
        )
    
    def _calculate_trend(self, ma_fast, ma_slow, ma_trend, candles) -> Tuple[str, float]:
        """Calculate trend direction and strength from MAs."""
        if not ma_fast or not ma_slow or len(ma_fast) < 2:
            return 'neutral', 0.0
        
        # Current and previous values
        fast_now, fast_prev = ma_fast[-1], ma_fast[-2]
        slow_now, slow_prev = ma_slow[-1], ma_slow[-2]
        
        # Trend direction
        if fast_now > slow_now and fast_prev <= slow_prev:
            direction = 'bullish'
            strength = self._calculate_trend_strength(ma_fast, ma_slow, ma_trend, 'bullish')
        elif fast_now < slow_now and fast_prev >= slow_prev:
            direction = 'bearish'
            strength = self._calculate_trend_strength(ma_fast, ma_slow, ma_trend, 'bearish')
        elif fast_now > slow_now:
            direction = 'bullish'
            strength = 0.5 + self._calculate_trend_strength(ma_fast, ma_slow, ma_trend, 'bullish') * 0.5
        elif fast_now < slow_now:
            direction = 'bearish'
            strength = 0.5 + self._calculate_trend_strength(ma_fast, ma_slow, ma_trend, 'bearish') * 0.5
        else:
            direction = 'neutral'
            strength = 0.0
        
        return direction, strength
    
    def _calculate_trend_strength(self, ma_fast, ma_slow, ma_trend, direction) -> float:
        """Calculate how strong the trend is (0.0 - 1.0)."""
        if not ma_fast or not ma_slow or len(ma_fast) < 5:
            return 0.0
        
        # Slope calculation
        fast_slope = (ma_fast[-1] - ma_fast[-5]) / 5
        slow_slope = (ma_slow[-1] - ma_slow[-5]) / 5
        
        # Alignment with trend MA
        trend_aligned = False
        if ma_trend and len(ma_trend) > 0:
            if direction == 'bullish' and ma_fast[-1] > ma_trend[-1]:
                trend_aligned = True
            elif direction == 'bearish' and ma_fast[-1] < ma_trend[-1]:
                trend_aligned = True
        
        # Calculate strength
        strength = min(abs(fast_slope) * 10, 1.0)  # Cap at 1.0
        
        if trend_aligned:
            strength = min(strength * 1.3, 1.0)  # Boost if aligned with trend
        
        return strength
    
    def _analyze_structure(self, candles, trend_direction) -> Tuple[bool, list, list]:
        """Analyze market structure for Higher Highs/Lower Lows."""
        if len(candles) < 10:
            return False, [], []
        
        highs = [c['high'] for c in candles[-20:]]
        lows = [c['low'] for c in candles[-20:]]
        
        # Find swing points (simplified)
        swing_highs = []
        swing_lows = []
        
        for i in range(2, len(highs) - 2):
            # Swing high
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                swing_highs.append(highs[i])
            
            # Swing low
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                swing_lows.append(lows[i])
        
        # Check structure validity
        structure_valid = True
        if trend_direction == 'bullish' and len(swing_highs) >= 2:
            if swing_highs[-1] < swing_highs[-2]:  # Lower high in bullish trend = warning
                structure_valid = False
        elif trend_direction == 'bearish' and len(swing_lows) >= 2:
            if swing_lows[-1] > swing_lows[-2]:  # Higher low in bearish trend = warning
                structure_valid = False
        
        # Support/Resistance levels (recent swing points)
        support = sorted(swing_lows[-3:]) if swing_lows else [min(lows)]
        resistance = sorted(swing_highs[-3:], reverse=True) if swing_highs else [max(highs)]
        
        return structure_valid, support, resistance
    
    def _check_ma_alignment(self, ma_fast, ma_slow, ma_trend) -> str:
        """Check if MAs are aligned or crossing."""
        if not ma_fast or not ma_slow or len(ma_fast) < 2:
            return 'mixed'
        
        # Check for recent cross
        fast_now, fast_prev = ma_fast[-1], ma_fast[-2]
        slow_now, slow_prev = ma_slow[-1], ma_slow[-2]
        
        if (fast_now > slow_now and fast_prev <= slow_prev) or \
           (fast_now < slow_now and fast_prev >= slow_prev):
            return 'crossing'
        
        # Check alignment with trend MA
        if ma_trend and len(ma_trend) > 0:
            if fast_now > slow_now > ma_trend[-1]:
                return 'aligned_bullish'
            elif fast_now < slow_now < ma_trend[-1]:
                return 'aligned_bearish'
        
        return 'mixed'
    
    def get_context_for_tier3(self, tier1_result: Tier1Result) -> str:
        """Generate context summary for Tier 3 AI debate."""
        context = f"""
TIER 1 MATHEMATICAL ANALYSIS:
- Trend Direction: {tier1_result.trend_direction.upper()}
- Trend Strength: {tier1_result.trend_strength:.2f}/1.0
- MA Alignment: {tier1_result.ma_alignment}
- Structure Valid: {tier1_result.structure_valid}
- Support Levels: {[f'{s:.5f}' for s in tier1_result.support_levels[-3:]]}
- Resistance Levels: {[f'{r:.5f}' for r in tier1_result.resistance_levels[-3:]]}
"""
        if tier1_result.veto_reason:
            context += f"\n⚠️ VETO ACTIVE: {tier1_result.veto_reason}"
        
        return context


# Singleton
tier1_engine = None

def get_tier1_engine() -> Tier1MathEngine:
    """Get Tier 1 engine singleton."""
    global tier1_engine
    if tier1_engine is None:
        tier1_engine = Tier1MathEngine()
    return tier1_engine