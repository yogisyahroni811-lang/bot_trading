from .models import MarketData, TradeSetup, TradeDirection, TierResult

class TriggerAnalyzer:
    def analyze(self, market_data: MarketData, setup: TradeSetup) -> TierResult:
        reasoning = []
        score = 0.0

        # 1. RSI Check
        rsi = market_data.rsi
        reasoning.append(f"RSI: {rsi}")

        if setup.direction == TradeDirection.LONG:
            if rsi < 30:
                score += 0.5
                reasoning.append("RSI Oversold (Bounce Potential).")
            elif 50 <= rsi <= 70:
                score += 0.3
                reasoning.append("RSI Bullish Momentum.")
            elif rsi > 70:
                score -= 0.5
                reasoning.append("RSI Overbought (Risk of pullback).")
            else:
                reasoning.append("RSI Neutral.")

        elif setup.direction == TradeDirection.SHORT:
            if rsi > 70:
                score += 0.5
                reasoning.append("RSI Overbought (Drop Potential).")
            elif 30 <= rsi <= 50:
                score += 0.3
                reasoning.append("RSI Bearish Momentum.")
            elif rsi < 30:
                score -= 0.5
                reasoning.append("RSI Oversold (Risk of bounce).")
            else:
                reasoning.append("RSI Neutral.")

        # 2. Simulated Candlestick Pattern (Mock)
        # In a real system, this would be input from M15/M5 data or LLM vision
        # We'll just assume a favorable pattern if score is already positive
        if score > 0:
            score += 0.5
            reasoning.append("Mock AI: Favorable Candlestick Pattern detected.")
        else:
            score -= 0.2
            reasoning.append("Mock AI: Weak/Indecisive Price Action.")

        # Cap score
        score = min(max(score, -1.0), 1.0)

        return TierResult(score=score, reasoning=reasoning)
