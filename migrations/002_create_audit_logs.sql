-- Migration: Create trade_audit_logs table
-- Purpose: Store detailed audit trail of trade decisions including agent arguments and scoring
CREATE TABLE IF NOT EXISTS trade_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    symbol TEXT NOT NULL,
    timeframe TEXT,
    decision TEXT NOT NULL,
    -- BUY, SELL, HOLD
    final_score REAL,
    -- Market Snapshot
    price REAL,
    rsi REAL,
    ma_trend TEXT,
    market_data_json TEXT,
    -- Full market data snapshot
    -- Structure / Tier 1
    tier_1_score REAL,
    tier_1_reason TEXT,
    -- Debate / Tier 3
    pro_agent_response TEXT,
    con_agent_response TEXT,
    tier_3_score REAL,
    tier_3_reason TEXT,
    -- Execution Details (if applicable)
    lot_size REAL,
    stop_loss REAL,
    take_profit REAL,
    -- Metadata
    execution_time_ms REAL,
    error_message TEXT
);
-- Indices for fast retrieval
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON trade_audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_symbol ON trade_audit_logs(symbol);
CREATE INDEX IF NOT EXISTS idx_audit_decision ON trade_audit_logs(decision);