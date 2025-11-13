-- Migration 003: Paper Trading Tables
-- Create tables for paper trading positions and portfolio tracking

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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_paper_positions_symbol ON paper_positions(symbol);
CREATE INDEX IF NOT EXISTS idx_paper_positions_status ON paper_positions(status);
CREATE INDEX IF NOT EXISTS idx_paper_positions_entry_time ON paper_positions(entry_time);
CREATE INDEX IF NOT EXISTS idx_paper_portfolio_timestamp ON paper_portfolio(timestamp);
CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions(timestamp);
CREATE INDEX IF NOT EXISTS idx_predictions_symbol ON predictions(symbol);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_paper_positions_updated_at BEFORE UPDATE
    ON paper_positions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
