from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum
from datetime import datetime

class TradeDirection(Enum):
    LONG = "LONG"
    SHORT = "SHORT"

@dataclass
class MarketData:
    symbol: str
    timestamp: datetime
    current_price: float
    # Macro / Structure
    h4_trend: str  # "BULLISH", "BEARISH", "SIDEWAYS"
    structure_score: float # -1 to 1

    # Technicals
    ma_50: float
    ma_200: float
    rsi: float

    # Context
    news_impact: str # "HIGH", "MEDIUM", "LOW", "NONE"
    minutes_to_news: int

    # Levels (Mocking RAG output for relevant levels) - moved to end because they have defaults
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)

@dataclass
class TradeSetup:
    symbol: str
    direction: TradeDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    description: str

@dataclass
class TierResult:
    score: float # -1 to 1 or 0 to 1 depending on logic
    reasoning: List[str]
    details: dict = field(default_factory=dict)

@dataclass
class Decision:
    setup: TradeSetup
    approved: bool
    final_score: float
    tier1_result: TierResult
    tier2_result: TierResult
    tier3_result: TierResult
    audit_log: List[str]
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class AccountState:
    balance: float
    daily_pnl_pct: float # e.g. -0.02 for -2%
    is_locked: bool # True if daily limit hit
