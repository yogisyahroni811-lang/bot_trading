from typing import List, Tuple
from .models import MarketData, AccountState

class RiskManager:
    def __init__(self, daily_loss_limit_pct: float = 0.04):
        self.daily_loss_limit_pct = daily_loss_limit_pct

    def check_guardrails(self, market_data: MarketData, account: AccountState) -> Tuple[bool, str]:
        # 1. Daily Loss Limit
        if account.is_locked:
            return False, "ACCOUNT LOCKED: Previous violation."

        if account.daily_pnl_pct <= -self.daily_loss_limit_pct:
            return False, f"DAILY LOSS LIMIT HIT: {account.daily_pnl_pct:.2%} <= -{self.daily_loss_limit_pct:.2%}"

        # 2. News Grounding
        # "Bot berhenti 30 menit sebelum/setudah berita High Impact."
        if market_data.news_impact == "HIGH":
            if market_data.minutes_to_news <= 30 and market_data.minutes_to_news >= -30:
                 # Assuming minutes_to_news can be negative if passed?
                 # Or usually it's "time until". If "time since", we'd need another field.
                 # Assuming minutes_to_news represents proximity (absolute or remaining).
                 # If we only have "minutes to news", let's assume it's positive.
                 return False, f"NEWS GROUNDING: High Impact news in {market_data.minutes_to_news} mins."

        return True, "Guardrails Passed."
