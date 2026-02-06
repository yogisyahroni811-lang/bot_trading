"""
Decision History Storage
Menyimpan riwayat keputusan trading dari The Judge
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from threading import Lock
from core.logger import get_logger

logger = get_logger(__name__)


class DecisionRecord:
    """Record single decision dari The Judge."""
    
    def __init__(
        self,
        symbol: str,
        action: str,
        confidence: float,
        tier1_score: float,
        tier2_context: str,
        tier3_pro_conf: float,
        tier3_con_conf: float,
        debate_winner: str,
        final_reasoning: str,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        lot_size: Optional[float] = None
    ):
        self.id = f"{int(time.time() * 1000)}_{symbol}"
        self.timestamp = datetime.now()
        self.symbol = symbol
        self.action = action
        self.confidence = confidence
        self.tier1_score = tier1_score
        self.tier2_context = tier2_context
        self.tier3_pro_conf = tier3_pro_conf
        self.tier3_con_conf = tier3_con_conf
        self.debate_winner = debate_winner
        self.final_reasoning = final_reasoning
        self.sl = sl
        self.tp = tp
        self.lot_size = lot_size
        self.executed = False
        self.pnl = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON storage."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'action': self.action,
            'confidence': self.confidence,
            'tier1_score': self.tier1_score,
            'tier2_context': self.tier2_context,
            'tier3_pro_conf': self.tier3_pro_conf,
            'tier3_con_conf': self.tier3_con_conf,
            'debate_winner': self.debate_winner,
            'final_reasoning': self.final_reasoning,
            'sl': self.sl,
            'tp': self.tp,
            'lot_size': self.lot_size,
            'executed': self.executed,
            'pnl': self.pnl
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DecisionRecord':
        """Create DecisionRecord from dictionary."""
        record = cls(
            symbol=data['symbol'],
            action=data['action'],
            confidence=data['confidence'],
            tier1_score=data.get('tier1_score', 0.0),
            tier2_context=data.get('tier2_context', ''),
            tier3_pro_conf=data.get('tier3_pro_conf', 0.0),
            tier3_con_conf=data.get('tier3_con_conf', 0.0),
            debate_winner=data.get('debate_winner', '-'),
            final_reasoning=data.get('final_reasoning', ''),
            sl=data.get('sl'),
            tp=data.get('tp'),
            lot_size=data.get('lot_size')
        )
        record.id = data.get('id', record.id)
        record.timestamp = datetime.fromisoformat(data['timestamp'])
        record.executed = data.get('executed', False)
        record.pnl = data.get('pnl')
        return record


class DecisionHistoryStorage:
    """
    Storage untuk decision history.
    
    Features:
    - Auto-save ke JSON file
    - Filter by symbol, date range, search text
    - Limit max records (auto cleanup old records)
    """
    
    STORAGE_FILE = "config/decision_history.json"
    MAX_RECORDS = 1000  # Keep last 1000 decisions
    
    def __init__(self):
        self.decisions: List[DecisionRecord] = []
        self.lock = Lock()
        self._load_history()
        logger.info(f"DecisionHistoryStorage initialized with {len(self.decisions)} records")
    
    def add_decision(self, decision: DecisionRecord) -> str:
        """Add new decision to history."""
        with self.lock:
            self.decisions.insert(0, decision)  # Newest first
            
            # Cleanup old records if exceeding limit
            if len(self.decisions) > self.MAX_RECORDS:
                removed = len(self.decisions) - self.MAX_RECORDS
                self.decisions = self.decisions[:self.MAX_RECORDS]
                logger.info(f"Cleaned up {removed} old decision records")
            
            self._save_history()
            logger.info(f"Added decision: {decision.action} {decision.symbol} ({decision.confidence:.1%})")
            return decision.id
    
    def get_decisions(
        self,
        symbol: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search_text: Optional[str] = None,
        limit: int = 100
    ) -> List[DecisionRecord]:
        """Get filtered decisions."""
        with self.lock:
            filtered = self.decisions.copy()
            
            # Filter by symbol
            if symbol and symbol != 'All':
                filtered = [d for d in filtered if d.symbol == symbol]
            
            # Filter by action
            if action and action != 'All':
                filtered = [d for d in filtered if d.action == action]
            
            # Filter by date range
            if start_date:
                filtered = [d for d in filtered if d.timestamp >= start_date]
            if end_date:
                filtered = [d for d in filtered if d.timestamp <= end_date]
            
            # Filter by search text (search in symbol, action, reasoning)
            if search_text:
                search_lower = search_text.lower()
                filtered = [
                    d for d in filtered 
                    if (search_lower in d.symbol.lower() or
                        search_lower in d.action.lower() or
                        search_lower in d.final_reasoning.lower())
                ]
            
            return filtered[:limit]
    
    def get_unique_symbols(self) -> List[str]:
        """Get list of unique symbols from history."""
        with self.lock:
            symbols = sorted(set(d.symbol for d in self.decisions))
            return symbols
    
    def update_trade_result(self, decision_id: str, pnl: float) -> bool:
        """Update PnL for executed trade."""
        with self.lock:
            for decision in self.decisions:
                if decision.id == decision_id:
                    decision.executed = True
                    decision.pnl = pnl
                    self._save_history()
                    logger.info(f"Updated trade result for {decision_id}: PnL={pnl:.2f}")
                    return True
            return False
    
    def get_statistics(self) -> Dict:
        """Get statistics dari decision history."""
        with self.lock:
            if not self.decisions:
                return {
                    'total_decisions': 0,
                    'executed_trades': 0,
                    'win_rate': 0.0,
                    'avg_confidence': 0.0,
                    'total_pnl': 0.0
                }
            
            executed = [d for d in self.decisions if d.executed]
            winners = [d for d in executed if d.pnl and d.pnl > 0]
            
            total_pnl = sum(d.pnl for d in executed if d.pnl) if executed else 0.0
            avg_conf = sum(d.confidence for d in self.decisions) / len(self.decisions)
            
            return {
                'total_decisions': len(self.decisions),
                'executed_trades': len(executed),
                'win_rate': len(winners) / len(executed) * 100 if executed else 0.0,
                'avg_confidence': avg_conf * 100,
                'total_pnl': total_pnl
            }
    
    def clear_history(self):
        """Clear all decision history."""
        with self.lock:
            self.decisions = []
            self._save_history()
            logger.info("Decision history cleared")
    
    def _save_history(self):
        """Save decisions to file."""
        try:
            os.makedirs(os.path.dirname(self.STORAGE_FILE), exist_ok=True)
            
            data = {
                'saved_at': datetime.now().isoformat(),
                'total_records': len(self.decisions),
                'decisions': [d.to_dict() for d in self.decisions]
            }
            
            with open(self.STORAGE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        
        except Exception as e:
            logger.error(f"Failed to save decision history: {e}")
    
    def _load_history(self):
        """Load decisions from file."""
        try:
            if os.path.exists(self.STORAGE_FILE):
                with open(self.STORAGE_FILE, 'r') as f:
                    data = json.load(f)
                
                self.decisions = [
                    DecisionRecord.from_dict(d) 
                    for d in data.get('decisions', [])
                ]
                logger.info(f"Loaded {len(self.decisions)} decisions from storage")
        
        except Exception as e:
            logger.error(f"Failed to load decision history: {e}")
            self.decisions = []


# Singleton
_history_storage = None

def get_decision_history() -> DecisionHistoryStorage:
    """Get global DecisionHistoryStorage instance."""
    global _history_storage
    if _history_storage is None:
        _history_storage = DecisionHistoryStorage()
    return _history_storage
