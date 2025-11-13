-- Database Initialization SQL
-- Creates all tables for ML Trading System
-- Runs automatically on first database startup via docker-compose

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- MIGRATION 001: Core Trading Tables
-- ============================================================

-- Candles table for OHLCV data
CREATE TABLE IF NOT EXISTS candles (
    candle_id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open NUMERIC(12, 5) NOT NULL,
    high NUMERIC(12, 5) NOT NULL,
    low NUMERIC(12, 5) NOT NULL,
    close NUMERIC(12, 5) NOT NULL,
    volume BIGINT,
    interval VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timestamp, interval)
);

-- Features table for ML model inputs
CREATE TABLE IF NOT EXISTS features (
    feature_id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    label INTEGER,  -- -1, 0, 1 for SHORT, NEUTRAL, LONG
    features JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timestamp)
);

-- Macro events table
CREATE TABLE IF NOT EXISTS macro_events (
    event_id SERIAL PRIMARY KEY,
    event_time TIMESTAMP NOT NULL,
    currency VARCHAR(10) NOT NULL,
    event_name VARCHAR(255) NOT NULL,
    impact VARCHAR(20),  -- low, medium, high
    forecast VARCHAR(50),
    previous VARCHAR(50),
    actual VARCHAR(50),
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- MIGRATION 002: Performance & Monitoring Tables
-- ============================================================

-- Model performance metrics
CREATE TABLE IF NOT EXISTS model_metrics (
    metric_id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    metric_value NUMERIC(12, 6),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System logs
CREATE TABLE IF NOT EXISTS system_logs (
    log_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    log_level VARCHAR(20) NOT NULL,
    component VARCHAR(100),
    message TEXT,
    extra_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- MIGRATION 003: Paper Trading Tables
-- ============================================================

-- Paper trading positions table
CREATE TABLE IF NOT EXISTS paper_positions (
    position_id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    direction INTEGER NOT NULL, -- 1 = LONG, -1 = SHORT
    entry_time TIMESTAMP NOT NULL,
    entry_price NUMERIC(12, 5) NOT NULL,
    position_size NUMERIC(12, 2) NOT NULL,
    position_value NUMERIC(12, 2) NOT NULL,
    stop_loss NUMERIC(12, 5) NOT NULL,
    take_profit NUMERIC(12, 5) NOT NULL,
    risk_amount NUMERIC(12, 2) NOT NULL,
    atr NUMERIC(12, 5),
    regime VARCHAR(20),
    confidence NUMERIC(5, 4),
    status VARCHAR(20) NOT NULL DEFAULT 'open', -- 'open' or 'closed'
    exit_time TIMESTAMP,
    exit_price NUMERIC(12, 5),
    exit_reason VARCHAR(50),
    pnl NUMERIC(12, 2),
    pnl_pct NUMERIC(8, 4),
    holding_hours NUMERIC(8, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Paper trading portfolio snapshots
CREATE TABLE IF NOT EXISTS paper_portfolio (
    snapshot_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    equity NUMERIC(12, 2) NOT NULL,
    open_positions INTEGER NOT NULL DEFAULT 0,
    total_trades INTEGER NOT NULL DEFAULT 0,
    winning_trades INTEGER NOT NULL DEFAULT 0,
    losing_trades INTEGER NOT NULL DEFAULT 0,
    total_pnl NUMERIC(12, 2) NOT NULL DEFAULT 0,
    win_rate NUMERIC(5, 2),
    profit_factor NUMERIC(8, 4),
    max_drawdown_pct NUMERIC(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Model predictions log (for chart visualization)
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    prediction INTEGER NOT NULL, -- -1, 0, 1
    confidence_short NUMERIC(5, 4),
    confidence_long NUMERIC(5, 4),
    regime VARCHAR(20),
    signal_strength VARCHAR(20),
    top_features JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Indexes for Performance
-- ============================================================

-- Candles indexes
CREATE INDEX IF NOT EXISTS idx_candles_symbol ON candles(symbol);
CREATE INDEX IF NOT EXISTS idx_candles_timestamp ON candles(timestamp);
CREATE INDEX IF NOT EXISTS idx_candles_symbol_timestamp ON candles(symbol, timestamp);

-- Features indexes
CREATE INDEX IF NOT EXISTS idx_features_symbol ON features(symbol);
CREATE INDEX IF NOT EXISTS idx_features_timestamp ON features(timestamp);

-- Macro events indexes
CREATE INDEX IF NOT EXISTS idx_macro_events_time ON macro_events(event_time);
CREATE INDEX IF NOT EXISTS idx_macro_events_currency ON macro_events(currency);

-- Paper trading indexes
CREATE INDEX IF NOT EXISTS idx_paper_positions_symbol ON paper_positions(symbol);
CREATE INDEX IF NOT EXISTS idx_paper_positions_status ON paper_positions(status);
CREATE INDEX IF NOT EXISTS idx_paper_positions_entry_time ON paper_positions(entry_time);
CREATE INDEX IF NOT EXISTS idx_paper_portfolio_timestamp ON paper_portfolio(timestamp);
CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions(timestamp);
CREATE INDEX IF NOT EXISTS idx_predictions_symbol ON predictions(symbol);

-- ============================================================
-- Triggers and Functions
-- ============================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for paper_positions updated_at
CREATE TRIGGER update_paper_positions_updated_at BEFORE UPDATE
    ON paper_positions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- Initial Data (Optional)
-- ============================================================

-- Insert initial portfolio snapshot
INSERT INTO paper_portfolio (timestamp, equity, open_positions, total_trades)
VALUES (CURRENT_TIMESTAMP, 10000.00, 0, 0)
ON CONFLICT DO NOTHING;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE '✅ Database initialization complete!';
    RAISE NOTICE 'Tables created: candles, features, macro_events, model_metrics, system_logs, paper_positions, paper_portfolio, predictions';
END $$;
