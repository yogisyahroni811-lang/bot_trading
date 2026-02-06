import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from .db_pool import get_pool
from .appdata import get_appdata_path

DB_PATH = get_appdata_path("database/trade_history.db")

class TradeDatabase:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.pool = get_pool(db_path)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Table: Trade History
            # Linked to Vector DB via 'trade_id'
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    timeframe TEXT,
                    action TEXT,
                    open_price REAL,
                    close_price REAL,
                    pnl REAL,
                    outcome TEXT, -- WIN / LOSS / BE
                    entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    exit_time TIMESTAMP,
                    ai_reason TEXT,
                    market_condition_json TEXT -- Snapshot of indicators
                )
            ''')
            
            # Table: Token Logs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS token_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    provider TEXT,
                    model TEXT,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    cost_usd REAL
                )
            ''')
            
            conn.commit()

    def log_token_usage(self, provider: str, model: str, input_tok: int, output_tok: int, cost: float):
        """Log token usage."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO token_logs (provider, model, input_tokens, output_tokens, cost_usd)
                VALUES (?, ?, ?, ?, ?)
            ''', (provider, model, input_tok, output_tok, cost))
            conn.commit()

    def get_token_stats(self) -> Dict[str, Any]:
        """Get aggregated token usage statistics."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total stats
            cursor.execute("SELECT SUM(input_tokens), SUM(output_tokens), SUM(cost_usd) FROM token_logs")
            total_in, total_out, total_cost = cursor.fetchone()
            
            # By Model (uses idx_token_logs_model for faster GROUP BY)
            cursor.execute('''
                SELECT model, SUM(input_tokens), SUM(output_tokens), SUM(cost_usd), COUNT(*)
                FROM token_logs
                GROUP BY model
            ''')
            by_model = [
                {"model": row[0], "input": row[1], "output": row[2], "cost": row[3], "calls": row[4]} 
                for row in cursor.fetchall()
            ]
            
            # By Provider (uses idx_token_logs_provider for faster GROUP BY)
            cursor.execute('''
                SELECT provider, SUM(input_tokens), SUM(output_tokens), SUM(cost_usd), COUNT(*)
                FROM token_logs
                GROUP BY provider
            ''')
            by_provider = [
                {"provider": row[0], "input": row[1], "output": row[2], "cost": row[3], "calls": row[4]} 
                for row in cursor.fetchall()
            ]
            
            return {
                "total_input": total_in or 0,
                "total_output": total_out or 0,
                "total_cost": total_cost or 0.0,
                "by_model": by_model,
                "by_provider": by_provider
            }

    def get_last_trade_time(self, symbol: str) -> Optional[datetime]:
        """Get the timestamp of the last executed trade for a symbol."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            # Check 'trades' table for executed trades
            cursor.execute('''
                SELECT entry_time FROM trades 
                WHERE symbol = ? 
                ORDER BY entry_time DESC LIMIT 1
            ''', (symbol,))
            row = cursor.fetchone()
            if row:
                try:
                    # Handle string timestamp if SQLite stores it as string
                    return datetime.fromisoformat(row[0]) if isinstance(row[0], str) else row[0]
                except ValueError:
                    # Fallback for non-ISO formats
                    return None
            return None

    def log_trade(self, trade_data: Dict[str, Any]):
        """Log a finished trade to the history."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO trades 
                (trade_id, symbol, timeframe, action, open_price, close_price, pnl, outcome, entry_time, exit_time, ai_reason, market_condition_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data['id'],
                trade_data['symbol'],
                trade_data['timeframe'],
                trade_data['action'],
                trade_data.get('open_price', 0.0),
                trade_data.get('close_price', 0.0),
                trade_data.get('pnl', 0.0),
                trade_data['outcome'],
                trade_data.get('entry_time', datetime.now().isoformat()),
                trade_data.get('exit_time', datetime.now().isoformat()),
                trade_data.get('reason', ''),
                json.dumps(trade_data.get('market_condition', {}))
            ))
            
            conn.commit()

    def get_trades_by_ids(self, trade_ids: List[str]) -> List[Dict]:
        """Retrieve full details for specific trade IDs (from Vector Search)."""
        if not trade_ids:
            return []
        
        with self.pool.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            placeholders = ','.join('?' * len(trade_ids))
            query = f"SELECT * FROM trades WHERE trade_id IN ({placeholders})"
            
            cursor.execute(query, trade_ids)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]

    def get_stats(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get simple winrate stats.
        
        Args:
            symbol: Optional symbol filter (e.g., 'EURUSD'). If None, returns stats for all symbols.
            
        Returns:
            Dictionary with total_trades and winrate percentage.
            
        Performance:
            Uses idx_trades_symbol_outcome composite index for optimized queries.
        """
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # FIXED: Use parameterized query to prevent SQL injection
            # OPTIMIZED: Uses idx_trades_symbol_outcome composite index
            if symbol:
                cursor.execute(
                    "SELECT COUNT(*), SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) FROM trades WHERE symbol = ?",
                    (symbol,)
                )
            else:
                cursor.execute("SELECT COUNT(*), SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) FROM trades")
            
            result = cursor.fetchone()
            total = result[0] if result[0] is not None else 0
            wins = result[1] if result[1] is not None else 0
            
            winrate = (wins / total * 100) if total and total > 0 else 0.0
            return {"total_trades": total, "winrate": winrate}
