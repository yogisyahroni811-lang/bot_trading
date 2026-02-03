from typing import List
from .models import MarketData, TradeSetup, TradeDirection, TierResult

class AreaAnalyzer:
    def analyze(self, market_data: MarketData, setup: TradeSetup) -> TierResult:
        reasoning = []
        score = 0.0

        price = market_data.current_price

        # Simulating RAG retrieval of "proven strategies" by checking proximity to key levels
        # In a real system, this would query ChromaDB for "Is this a valid Order Block setup?"

        threshold = 0.005 # 0.5% proximity

        if setup.direction == TradeDirection.LONG:
            # Look for Support
            nearest_support = self._find_nearest(price, market_data.support_levels)
            if nearest_support:
                distance_pct = abs(price - nearest_support) / price
                reasoning.append(f"Nearest Support: {nearest_support} (Dist: {distance_pct:.2%})")

                if distance_pct <= threshold:
                    score = 1.0
                    reasoning.append("Price is at valid Support Area (High Probability).")
                elif distance_pct <= threshold * 2:
                    score = 0.5
                    reasoning.append("Price is near Support Area.")
                else:
                    score = -0.5
                    reasoning.append("Price is far from Support (Buying in middle of nowhere).")
            else:
                score = -1.0
                reasoning.append("No clear Support level identified by RAG.")

        elif setup.direction == TradeDirection.SHORT:
            # Look for Resistance
            nearest_res = self._find_nearest(price, market_data.resistance_levels)
            if nearest_res:
                distance_pct = abs(price - nearest_res) / price
                reasoning.append(f"Nearest Resistance: {nearest_res} (Dist: {distance_pct:.2%})")

                if distance_pct <= threshold:
                    score = 1.0
                    reasoning.append("Price is at valid Resistance Area (High Probability).")
                elif distance_pct <= threshold * 2:
                    score = 0.5
                    reasoning.append("Price is near Resistance Area.")
                else:
                    score = -0.5
                    reasoning.append("Price is far from Resistance (Selling in middle of nowhere).")
            else:
                score = -1.0
                reasoning.append("No clear Resistance level identified by RAG.")

        return TierResult(score=score, reasoning=reasoning)

    def _find_nearest(self, price: float, levels: List[float]) -> float:
        if not levels:
            return None
        return min(levels, key=lambda x: abs(x - price))
