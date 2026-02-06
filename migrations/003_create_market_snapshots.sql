-- Migration 003: Create Market Snapshots for RAG
CREATE TABLE IF NOT EXISTS market_snapshots (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    raw_json TEXT NOT NULL,
    -- Stores the full 100-candle data for all TFs
    compressed_summary TEXT,
    -- Stores the Analyst output (future proofing)
    vector_id TEXT -- Link to ChromaDB
);
CREATE INDEX IF NOT EXISTS idx_snapshots_symbol_time ON market_snapshots(symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_snapshots_vector ON market_snapshots(vector_id);