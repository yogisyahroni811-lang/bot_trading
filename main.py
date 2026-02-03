import sys
import os
from datetime import datetime
from src.core.models import MarketData, TradeSetup, TradeDirection, AccountState
from src.core.judge import Judge

def run_scenario(name, data, setup, account):
    judge = Judge()
    print(f"\n{'='*20} SCENARIO: {name} {'='*20}")
    print(f"Symbol: {data.symbol} | Price: {data.current_price}")
    print(f"Setup: {setup.direction.value} @ {setup.entry_price}")

    decision = judge.evaluate(data, setup, account)

    print("\n--- AUDIT LOG ---")
    for line in decision.audit_log:
        print(line)

    print(f"\nFINAL RESULT: {'APPROVED' if decision.approved else 'REJECTED'}")
    print("="*60)

def main():
    # Base Account
    account = AccountState(balance=10000, daily_pnl_pct=0.0, is_locked=False)

    # 1. Strong Buy Scenario
    data_strong = MarketData(
        symbol="BTCUSD", timestamp=datetime.now(), current_price=50000,
        h4_trend="BULLISH", structure_score=1.0,
        ma_50=49000, ma_200=45000, rsi=60,
        support_levels=[50000, 48000], resistance_levels=[55000],
        news_impact="NONE", minutes_to_news=120
    )
    setup_strong = TradeSetup("BTCUSD", TradeDirection.LONG, 50000, 49000, 52000, "Classic Breakout")
    run_scenario("STRONG BUY", data_strong, setup_strong, account)

    # 2. News Risk Scenario
    data_news = MarketData(
        symbol="BTCUSD", timestamp=datetime.now(), current_price=50000,
        h4_trend="BULLISH", structure_score=1.0,
        ma_50=49000, ma_200=45000, rsi=60,
        support_levels=[50000, 48000], resistance_levels=[55000],
        news_impact="HIGH", minutes_to_news=10
    )
    run_scenario("NEWS RISK", data_news, setup_strong, account)

    # 3. Macro Mismatch Scenario (Short in Bullish Trend)
    setup_short = TradeSetup("BTCUSD", TradeDirection.SHORT, 50000, 51000, 48000, "Counter Trend")
    run_scenario("MACRO MISMATCH (SHORT)", data_strong, setup_short, account)

if __name__ == "__main__":
    main()
