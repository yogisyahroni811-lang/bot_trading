from .models import MarketData, TradeSetup, TradeDirection, TierResult

class MacroAnalyzer:
    def analyze(self, market_data: MarketData, setup: TradeSetup) -> TierResult:
        reasoning = []
        score = 0.0

        # Check H4 Trend
        h4_trend = market_data.h4_trend.upper()
        reasoning.append(f"H4 Trend is {h4_trend}")

        # Rule: If H4 Bearish, no Buys. If H4 Bullish, no Sells.
        if setup.direction == TradeDirection.LONG:
            if h4_trend == "BEARISH":
                return TierResult(
                    score=-1.0,
                    reasoning=reasoning + ["FATAL: Attempting LONG in H4 BEARISH structure."]
                )
            elif h4_trend == "BULLISH":
                score += 0.5
                reasoning.append("Trend alignment: LONG in BULLISH structure.")

        elif setup.direction == TradeDirection.SHORT:
            if h4_trend == "BULLISH":
                return TierResult(
                    score=-1.0,
                    reasoning=reasoning + ["FATAL: Attempting SHORT in H4 BULLISH structure."]
                )
            elif h4_trend == "BEARISH":
                score += 0.5
                reasoning.append("Trend alignment: SHORT in BEARISH structure.")

        # Check Moving Averages
        price = market_data.current_price
        ma50 = market_data.ma_50
        ma200 = market_data.ma_200

        reasoning.append(f"Price: {price}, MA50: {ma50}, MA200: {ma200}")

        if setup.direction == TradeDirection.LONG:
            if price > ma200:
                score += 0.3
                reasoning.append("Price above MA200 (Bullish Baseline).")
            else:
                score -= 0.3
                reasoning.append("Price below MA200 (Weak for Long).")

            if price > ma50:
                score += 0.2
                reasoning.append("Price above MA50 (Momentum).")

        elif setup.direction == TradeDirection.SHORT:
            if price < ma200:
                score += 0.3
                reasoning.append("Price below MA200 (Bearish Baseline).")
            else:
                score -= 0.3
                reasoning.append("Price above MA200 (Weak for Short).")

            if price < ma50:
                score += 0.2
                reasoning.append("Price below MA50 (Momentum).")

        # Cap score at 1.0
        score = min(max(score, -1.0), 1.0)

        return TierResult(score=score, reasoning=reasoning)
