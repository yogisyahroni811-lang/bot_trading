

# =============================================================================
# THE JUDGE 2.0 - ADVERSARIAL AI SYSTEM
# =============================================================================

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class SignalAction(Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"

@dataclass
class Argument:
    """Single argument from an agent."""
    claim: str
    evidence: str
    confidence: float  # 0.0 - 1.0
    weight: float  # How important this argument is

@dataclass
class AgentAnalysis:
    """Complete analysis from one agent."""
    agent_name: str
    overall_bias: str  # 'bullish', 'bearish', 'neutral'
    arguments: List[Argument]
    key_points: List[str]
    risk_assessment: str
    recommendation: SignalAction
    confidence_score: float  # 0.0 - 1.0
    raw_output: str = ""  # Original LLM output

class Arbitrator:
    """
    The Judge - scores the debate between Pro and Con agents.
    Makes final decision based on argument quality and weight.
    """
    
    def __init__(self):
        self.min_confidence_threshold = 0.65
        self.tier1_weight = 0.30
        self.tier3_weight = 0.70
    
    def judge_debate(self, pro_analysis: AgentAnalysis, con_analysis: AgentAnalysis,
                    tier1_trend_strength: float, tier1_veto: bool, 
                    tier1_veto_reason: Optional[str]) -> Dict:
        """
        Score the debate and make final decision.
        
        Formula: Final Score = (Tier1 × 0.30) + (Debate Winner × 0.70)
        
        Args:
            pro_analysis: Analysis from Pro Agent
            con_analysis: Analysis from Con Agent
            tier1_trend_strength: 0.0-1.0 from Tier 1 math
            tier1_veto: Whether Tier 1 vetoed the trade
            tier1_veto_reason: Why veto happened
            
        Returns:
            Dict with final decision and reasoning
        """
        # Extract scores
        pro_score = pro_analysis.confidence_score
        con_score = con_analysis.confidence_score
        
        # Determine debate winner
        score_diff = pro_score - con_score
        
        if score_diff > 0.15:
            debate_winner = "PRO"
            debate_bias = "bullish"
            debate_score = pro_score
        elif score_diff < -0.15:
            debate_winner = "CON"
            debate_bias = "bearish"
            debate_score = con_score
        else:
            debate_winner = "NEUTRAL"
            debate_bias = "neutral"
            debate_score = (pro_score + con_score) / 2
        
        # Calculate final score with weights
        if tier1_veto:
            # Heavy penalty if vetoed - max 30% of normal score
            final_score = debate_score * 0.3
            action = SignalAction.HOLD
        else:
            tier1_contrib = tier1_trend_strength * self.tier1_weight
            debate_contrib = debate_score * self.tier3_weight
            final_score = tier1_contrib + debate_contrib
            
            # Determine action based on final score and bias
            if final_score >= self.min_confidence_threshold:
                if debate_bias == "bullish":
                    action = SignalAction.BUY if final_score < 0.8 else SignalAction.STRONG_BUY
                elif debate_bias == "bearish":
                    action = SignalAction.SELL if final_score < 0.8 else SignalAction.STRONG_SELL
                else:
                    action = SignalAction.HOLD
            else:
                action = SignalAction.HOLD
        
        # Generate comprehensive reasoning
        reasoning = self._generate_reasoning(
            pro_analysis, con_analysis, debate_winner,
            tier1_veto, tier1_veto_reason, final_score, action
        )
        
        return {
            "action": action.value,
            "confidence_score": round(final_score, 3),
            "debate_winner": debate_winner,
            "pro_confidence": round(pro_score, 3),
            "con_confidence": round(con_score, 3),
            "pro_argument_count": len(pro_analysis.arguments),
            "con_argument_count": len(con_analysis.arguments),
            "tier1_contribution": round(tier1_trend_strength * self.tier1_weight, 3),
            "tier3_contribution": round(debate_score * self.tier3_weight, 3),
            "veto_active": tier1_veto,
            "veto_reason": tier1_veto_reason,
            "reasoning": reasoning,
            "pro_key_points": pro_analysis.key_points[:3],
            "con_key_points": con_analysis.key_points[:3],
            "pro_risk": pro_analysis.risk_assessment,
            "con_risk": con_analysis.risk_assessment
        }
    
    def _generate_reasoning(self, pro: AgentAnalysis, con: AgentAnalysis,
                           winner: str, veto: bool, veto_reason: Optional[str],
                           score: float, action: SignalAction) -> str:
        """Generate detailed human-readable reasoning."""
        parts = []
        
        # Introduction
        parts.append(f"DECISION: {action.value}")
        parts.append(f"Confidence: {score:.1%}")
        
        # Debate winner section
        parts.append(f"\n[AI DEBATE]")
        parts.append(f"Winner: {winner}")
        parts.append(f"Pro Agent: {pro.confidence_score:.1%} confidence")
        parts.append(f"Con Agent: {con.confidence_score:.1%} confidence")
        
        # Winning side details
        if winner == "PRO":
            parts.append(f"\nPro Arguments ({len(pro.arguments)}):")
            for i, arg in enumerate(pro.key_points[:2], 1):
                parts.append(f"  {i}. {arg}")
        elif winner == "CON":
            parts.append(f"\nCon Arguments ({len(con.arguments)}):")
            for i, arg in enumerate(con.key_points[:2], 1):
                parts.append(f"  {i}. {arg}")
        else:
            parts.append(f"\nDebate Inconclusive - Arguments balanced")
        
        # Risk assessment
        parts.append(f"\n[RISK ASSESSMENT]")
        parts.append(f"Pro: {pro.risk_assessment}")
        parts.append(f"Con: {con.risk_assessment}")
        
        # Veto section
        if veto:
            parts.append(f"\n⚠️ TIER 1 VETO ⚠️")
            parts.append(f"{veto_reason}")
            parts.append(f"Trade blocked by mathematical analysis.")
        
        return "\n".join(parts)


class StructuredProAgent(ProAgent):
    """Pro Agent yang return structured analysis untuk The Judge 2.0"""
    
    async def analyze_structured(self, market_data: Dict, tier1_context: str, 
                                 narrative: str = "") -> AgentAnalysis:
        """Generate structured analysis for debate."""
        # Get raw analysis from parent
        raw_output = await self.argue(market_data, narrative)
        
        # Parse and structure (simplified - in real implementation, use LLM to extract)
        arguments = []
        
        # Extract basic arguments from market data
        close = market_data.get('close', 0)
        open_p = market_data.get('open', 0)
        
        if close > open_p:
            arguments.append(Argument(
                claim="Bullish price action",
                evidence=f"Close ({close}) > Open ({open_p})",
                confidence=0.6,
                weight=0.3
            ))
        
        # RSI analysis
        rsi = market_data.get('rsi')
        if rsi and 40 <= rsi <= 60:
            arguments.append(Argument(
                claim="RSI in optimal zone",
                evidence=f"RSI {rsi} - room to move",
                confidence=0.7,
                weight=0.25
            ))
        
        # Calculate confidence
        avg_conf = sum(arg.confidence * arg.weight for arg in arguments) / sum(arg.weight for arg in arguments) if arguments else 0.5
        
        return AgentAnalysis(
            agent_name="Pro Agent",
            overall_bias="bullish",
            arguments=arguments,
            key_points=[arg.claim for arg in arguments],
            risk_assessment="Standard risk, use stop loss",
            recommendation=SignalAction.BUY if avg_conf > 0.6 else SignalAction.HOLD,
            confidence_score=avg_conf,
            raw_output=raw_output
        )

class StructuredConAgent(ConAgent):
    """Con Agent yang return structured analysis untuk The Judge 2.0"""
    
    async def analyze_structured(self, market_data: Dict, tier1_context: str,
                                 narrative: str = "") -> AgentAnalysis:
        """Generate structured analysis for debate."""
        # Get raw analysis from parent
        raw_output = await self.argue(market_data, narrative)
        
        # Parse and structure
        arguments = []
        
        # Spread check
        spread = market_data.get('spread', 0)
        if spread > 3:
            arguments.append(Argument(
                claim="High spread warning",
                evidence=f"Spread {spread} pips - entry cost high",
                confidence=0.8,
                weight=0.35
            ))
        
        # Resistance check
        if "resistance" in tier1_context.lower():
            arguments.append(Argument(
                claim="Near resistance",
                evidence="Price approaching resistance zone",
                confidence=0.7,
                weight=0.3
            ))
        
        # Calculate confidence
        avg_conf = sum(arg.confidence * arg.weight for arg in arguments) / sum(arg.weight for arg in arguments) if arguments else 0.4
        
        return AgentAnalysis(
            agent_name="Con Agent",
            overall_bias="bearish",
            arguments=arguments,
            key_points=[arg.claim for arg in arguments],
            risk_assessment="Potential trap scenario",
            recommendation=SignalAction.SELL if avg_conf > 0.6 else SignalAction.HOLD,
            confidence_score=avg_conf,
            raw_output=raw_output
        )

# Singleton for easy access
_arbitrator = None

def get_arbitrator() -> Arbitrator:
    """Get Arbitrator singleton."""
    global _arbitrator
    if _arbitrator is None:
        _arbitrator = Arbitrator()
    return _arbitrator