from typing import List
from .models import MarketData, TradeSetup, Decision, AccountState, TierResult
from .tier1_macro import MacroAnalyzer
from .tier2_area import AreaAnalyzer
from .tier3_trigger import TriggerAnalyzer
from .guardrails import RiskManager
from src.agents.adversarial import AdversarialCouncil

class Judge:
    def __init__(self):
        self.tier1 = MacroAnalyzer()
        self.tier2 = AreaAnalyzer()
        self.tier3 = TriggerAnalyzer()
        self.risk_manager = RiskManager()
        self.council = AdversarialCouncil()

    def evaluate(self, market_data: MarketData, setup: TradeSetup, account: AccountState) -> Decision:
        audit_log = []

        # 1. Guardrails
        ok, msg = self.risk_manager.check_guardrails(market_data, account)
        audit_log.append(f"Guardrails: {msg}")

        # Placeholder empty results for return if blocked
        empty_res = TierResult(0, [])

        if not ok:
            return Decision(
                setup=setup, approved=False, final_score=-1.0,
                tier1_result=empty_res, tier2_result=empty_res, tier3_result=empty_res,
                audit_log=audit_log
            )

        # 2. Tiers Evaluation
        t1_res = self.tier1.analyze(market_data, setup)
        t2_res = self.tier2.analyze(market_data, setup)
        t3_res = self.tier3.analyze(market_data, setup)

        # Weighted Score
        # T1: 50%, T2: 30%, T3: 20%
        # Assuming scores are -1.0 to 1.0
        weighted_score = (t1_res.score * 0.5) + (t2_res.score * 0.3) + (t3_res.score * 0.2)

        audit_log.append(f"Tier 1 Score: {t1_res.score:.2f} (w=0.5)")
        audit_log.append(f"Tier 2 Score: {t2_res.score:.2f} (w=0.3)")
        audit_log.append(f"Tier 3 Score: {t3_res.score:.2f} (w=0.2)")
        audit_log.append(f"Weighted Technical Score: {weighted_score:.2f}")

        # 3. Adversarial Audit
        pro_arg, contra_arg, confidence = self.council.deliberate(market_data, setup, [t1_res, t2_res, t3_res])

        audit_log.append(f"Adversarial Confidence: {confidence:.2f}")
        audit_log.append(f"Pro Agent: {pro_arg}")
        audit_log.append(f"Contra Agent: {contra_arg}")

        # Final Decision Logic
        # Technical score must be > 0.4 AND Confidence > 0.6 (arbitrary threshold based on "High Alpha")
        approved = False
        if weighted_score > 0.4 and confidence > 0.6:
            approved = True
            audit_log.append("DECISION: APPROVED")
        else:
            audit_log.append("DECISION: REJECTED")

        return Decision(
            setup=setup, approved=approved, final_score=weighted_score,
            tier1_result=t1_res, tier2_result=t2_res, tier3_result=t3_res,
            audit_log=audit_log
        )
