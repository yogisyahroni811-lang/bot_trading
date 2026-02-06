"""
Trade Decision Audit Logger.

Handles persistent logging of Judge decisions to the database for:
- Post-trade analysis
- Agent performance tuning
- Compliance and auditing

Data Flow:
TheJudge -> AuditLogger -> TradeDatabase (trades.db)
"""

import json
import time
from typing import Dict, Any, Optional
from dataclasses import asdict
from core.database import TradeDatabase
from core.logger import get_logger

logger = get_logger(__name__)

class AuditLogger:
    def __init__(self, db: Optional[TradeDatabase] = None):
        """
        Initialize AuditLogger.
        
        Args:
            db: Optional TradeDatabase instance. If None, creates a new connection.
        """
        self.db = db or TradeDatabase()

    def log_decision(
        self,
        symbol: str,
        timeframe: str,
        decision: str,
        market_data: Any,
        tier_1_result: tuple,
        tier_3_result: tuple,
        final_score: float,
        pro_response: str,
        con_response: str,
        execution_details: Optional[Dict[str, float]] = None,
        duration_ms: float = 0.0,
        error: Optional[str] = None
    ):
        """
        Log a full trade decision context to the database.
        
        Args:
            symbol: Trading pair symbol
            timeframe: Chart timeframe
            decision: "BUY", "SELL", or "HOLD"
            market_data: The raw market data object
            tier_1_result: (score, reason) from Tier 1
            tier_3_result: (score, reason) from Tier 3
            final_score: Calculated weighted score
            pro_response: Full text argument from Pro Agent
            con_response: Full text argument from Con Agent
            execution_details: Dict with {lot, sl, tp} if applicable
            duration_ms: Time taken to reach decision
            error: Error message if something failed
        """
        try:
            # Unpack tuples
            t1_score, t1_reason = tier_1_result
            t3_score, t3_reason = tier_3_result
            
            # Serialize market data safely
            try:
                # Assuming market_data might be a Pydantic model or dataclass 
                # If it's a simple object with __dict__, use that.
                # If it's a named tuple or custom class, handling might vary.
                # Simplest fallback is getting specific attrs we know exist.
                m_json = json.dumps({
                    'price': getattr(market_data, 'price', 0),
                    'rsi': getattr(market_data, 'rsi', 0),
                    'ma_fast': getattr(market_data, 'ma_fast', 0),
                    'ma_slow': getattr(market_data, 'ma_slow', 0),
                    'ma_trend': getattr(market_data, 'ma_trend', 'N/A'),
                    'balance': getattr(market_data, 'balance', 0)
                })
            except Exception:
                m_json = "{}"

            # Prepare execution details
            exec_lot = 0.0
            exec_sl = 0.0
            exec_tp = 0.0
            
            if execution_details:
                exec_lot = float(execution_details.get('lot', 0.0))
                exec_sl = float(execution_details.get('sl', 0.0))
                exec_tp = float(execution_details.get('tp', 0.0))

            query = '''
                INSERT INTO trade_audit_logs (
                    symbol, timeframe, decision, final_score,
                    price, rsi, ma_trend, market_data_json,
                    tier_1_score, tier_1_reason,
                    pro_agent_response, con_agent_response,
                    tier_3_score, tier_3_reason,
                    lot_size, stop_loss, take_profit,
                    execution_time_ms, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            params = (
                symbol,
                timeframe,
                decision,
                float(final_score),
                float(getattr(market_data, 'price', 0.0)),
                float(getattr(market_data, 'rsi', 0.0)),
                str(getattr(market_data, 'ma_trend', 'N/A')),
                m_json,
                float(t1_score),
                t1_reason,
                pro_response,
                con_response,
                float(t3_score),
                t3_reason,
                exec_lot,
                exec_sl,
                exec_tp,
                duration_ms,
                error
            )
            
            # Execute via DB pool
            with self.db.pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                
            logger.info("Audit log saved", extra={
                "context": {
                    "symbol": symbol,
                    "decision": decision,
                    "score": final_score
                }
            })

        except Exception as e:
            logger.error(f"Failed to save audit log: {e}", extra={
                "context": {
                    "error": str(e),
                    "symbol": symbol
                }
            })

    def fetch_recent_logs(self, limit: int = 50) -> list[dict]:
        """
        Fetch recent audit logs for display.
        
        Args:
            limit: values to return
            
        Returns:
            List of dicts containing log details
        """
        try:
            with self.db.pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        timestamp, symbol, decision, final_score, 
                        tier_1_reason, tier_3_reason, pro_agent_response, con_agent_response
                    FROM trade_audit_logs 
                    ORDER BY id DESC 
                    LIMIT ?
                """, (limit,))
                
                columns = [col[0] for col in cursor.description]
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                return results
                
        except Exception as e:
            logger.error(f"Failed to fetch audit logs: {e}")
            return []
