from typing import List, Tuple
from src.core.models import MarketData, TradeSetup, TierResult

class Agent:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    def argue(self, data: MarketData, setup: TradeSetup, tier_results: List[TierResult]) -> str:
        raise NotImplementedError

class ProAgent(Agent):
    def argue(self, data: MarketData, setup: TradeSetup, tier_results: List[TierResult]) -> str:
        # Simulate finding reasons to take the trade
        reasons = []
        for res in tier_results:
            if res.score > 0:
                reasons.extend(res.reasoning)

        if not reasons:
            return "I cannot find strong reasons to support this trade."

        return "Supportive Arguments: " + " | ".join(reasons)

class ContraAgent(Agent):
    def argue(self, data: MarketData, setup: TradeSetup, tier_results: List[TierResult]) -> str:
        # Simulate finding reasons to REJECT the trade
        reasons = []
        critical = False

        # Check for obvious risks
        if data.news_impact == "HIGH" and data.minutes_to_news < 60:
            reasons.append("HIGH IMPACT NEWS IMMINENT.")
            critical = True

        if abs(data.structure_score) < 0.5:
             reasons.append("Market Structure is weak/choppy.")

        for i, res in enumerate(tier_results):
            if res.score < 0:
                reasons.extend(res.reasoning)
                # Tier 1 (Macro) failure is critical
                if i == 0:
                    critical = True
                # Very low score is critical
                if res.score <= -0.5:
                    critical = True

        if not reasons:
            return "No major red flags found."

        prefix = "CRITICAL OBJECTIONS: " if critical else "MINOR OBJECTIONS: "
        return prefix + " | ".join(reasons)

class AdversarialCouncil:
    def __init__(self):
        self.pro = ProAgent("Optimist", "Find Bullish Case")
        self.contra = ContraAgent("Skeptic", "Find Bearish Case")

    def deliberate(self, data: MarketData, setup: TradeSetup, tier_results: List[TierResult]) -> Tuple[str, str, float]:
        pro_arg = self.pro.argue(data, setup, tier_results)
        contra_arg = self.contra.argue(data, setup, tier_results)

        # Mock Judge Logic
        confidence = 0.5

        if "CRITICAL OBJECTIONS" in contra_arg:
            confidence -= 0.4
        elif "MINOR OBJECTIONS" in contra_arg:
            confidence -= 0.1
        elif "No major red flags" in contra_arg:
            confidence += 0.4

        if "Supportive" in pro_arg:
            confidence += 0.2

        return pro_arg, contra_arg, min(max(confidence, 0.0), 1.0)
