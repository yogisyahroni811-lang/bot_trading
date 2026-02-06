"""
Real-time Judge Monitor
Connects The Judge 2.0 backend dengan GUI frontend
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional
from core.logger import get_logger

logger = get_logger(__name__)

class JudgeMonitor:
    """
    Monitor untuk tracking evaluasi The Judge secara real-time.
    Menyimpan hasil evaluasi terakhir untuk ditampilkan di GUI.
    """
    
    def __init__(self):
        self.last_evaluation = None
        self.evaluation_history = []
        self.max_history = 100
        self.status_file = "config/judge_status.json"
    
    def record_evaluation(self, signal_data: Dict):
        """
        Record evaluation result dari The Judge.
        Dipanggil setiap kali The Judge selesai evaluasi.
        """
        timestamp = datetime.now().isoformat()
        
        record = {
            'timestamp': timestamp,
            'symbol': signal_data.get('symbol', 'UNKNOWN'),
            'timeframe': signal_data.get('timeframe', 'H1'),
            'action': signal_data.get('action', 'HOLD'),
            'confidence': signal_data.get('confidence_score', 0),
            'debate_winner': signal_data.get('debate_winner', '-'),
            'pro_confidence': signal_data.get('pro_confidence', 0),
            'con_confidence': signal_data.get('con_confidence', 0),
            'tier1_contribution': signal_data.get('tier1_contribution', 0),
            'tier3_contribution': signal_data.get('tier3_contribution', 0),
            'veto_active': signal_data.get('veto_active', False),
            'veto_reason': signal_data.get('veto_reason'),
            'reasoning': signal_data.get('reasoning', ''),
            'entry_price': signal_data.get('entry_price'),
            'stop_loss': signal_data.get('stop_loss'),
            'take_profit': signal_data.get('take_profit')
        }
        
        self.last_evaluation = record
        self.evaluation_history.insert(0, record)
        
        # Keep only last 100
        if len(self.evaluation_history) > self.max_history:
            self.evaluation_history = self.evaluation_history[:self.max_history]
        
        # Save to file untuk GUI baca
        self._save_status()
        
        # Also save to persistent decision history storage
        try:
            from core.decision_history import DecisionRecord, get_decision_history
            
            decision = DecisionRecord(
                symbol=record['symbol'],
                action=record['action'],
                confidence=record['confidence'],
                tier1_score=record['tier1_contribution'],
                tier2_context=record.get('tier2_context', ''),
                tier3_pro_conf=record['pro_confidence'],
                tier3_con_conf=record['con_confidence'],
                debate_winner=record['debate_winner'],
                final_reasoning=record['reasoning'],
                sl=record['stop_loss'],
                tp=record['take_profit']
            )
            get_decision_history().add_decision(decision)
        except Exception as e:
            logger.warning(f"Failed to save to decision history: {e}")
        
        logger.info(f"Judge evaluation recorded: {record['action']} {record['symbol']} @ {record['confidence']:.1%}")
    
    def _save_status(self):
        """Save status ke file JSON."""
        try:
            os.makedirs(os.path.dirname(self.status_file), exist_ok=True)
            with open(self.status_file, 'w') as f:
                json.dump({
                    'last_evaluation': self.last_evaluation,
                    'recent_history': self.evaluation_history[:10],  # Last 10 only
                    'total_evaluations': len(self.evaluation_history),
                    'last_update': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save judge status: {e}")
    
    def load_status(self) -> Optional[Dict]:
        """Load status dari file."""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load judge status: {e}")
        return None
    
    def get_last_evaluation(self) -> Optional[Dict]:
        """Get hasil evaluasi terakhir."""
        if self.last_evaluation:
            return self.last_evaluation
        
        # Try load from file
        status = self.load_status()
        if status:
            self.last_evaluation = status.get('last_evaluation')
            return self.last_evaluation
        
        return None
    
    def get_stats(self) -> Dict:
        """Get statistics dari evaluasi history."""
        if not self.evaluation_history:
            status = self.load_status()
            if status:
                history = status.get('recent_history', [])
            else:
                return {
                    'total': 0,
                    'buy_signals': 0,
                    'sell_signals': 0,
                    'hold_signals': 0,
                    'avg_confidence': 0
                }
        else:
            history = self.evaluation_history
        
        total = len(history)
        if total == 0:
            return {
                'total': 0,
                'buy_signals': 0,
                'sell_signals': 0,
                'hold_signals': 0,
                'avg_confidence': 0
            }
        
        buys = sum(1 for h in history if h['action'] in ['BUY', 'STRONG_BUY'])
        sells = sum(1 for h in history if h['action'] in ['SELL', 'STRONG_SELL'])
        holds = sum(1 for h in history if h['action'] == 'HOLD')
        avg_conf = sum(h['confidence'] for h in history) / total
        
        return {
            'total': total,
            'buy_signals': buys,
            'sell_signals': sells,
            'hold_signals': holds,
            'avg_confidence': avg_conf
        }

# Global monitor instance
_judge_monitor = None

def get_judge_monitor() -> JudgeMonitor:
    """Get global JudgeMonitor instance."""
    global _judge_monitor
    if _judge_monitor is None:
        _judge_monitor = JudgeMonitor()
    return _judge_monitor