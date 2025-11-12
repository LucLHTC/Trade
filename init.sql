-- Trading System Database Initialization
-- This script sets up the initial database schema for the ML trading system

-- Create extension for UUID support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: raw_candles
-- Stores parsed candle data per minute/hour
CREATE TABLE IF NOT EXISTS raw_candles (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    interval VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(18, 8) NOT NULL,
    high DECIMAL(18, 8) NOT NULL,
    low DECIMAL(18, 8) NOT NULL,
    close DECIMAL(18, 8) NOT NULL,
    volume DECIMAL(18, 2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(symbol, interval, timestamp)
);

CREATE INDEX idx_candles_symbol_timestamp ON raw_candles(symbol, timestamp);
CREATE INDEX idx_candles_timestamp ON raw_candles(timestamp);

-- Table: macro_events
-- Stores annotated economic events
CREATE TABLE IF NOT EXISTS macro_events (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    currency VARCHAR(10) NOT NULL,
    impact VARCHAR(10) CHECK (impact IN ('low', 'medium', 'high')),
    title TEXT NOT NULL,
    previous_value VARCHAR(50),
    consensus_value VARCHAR(50),
    actual_value VARCHAR(50),
    bullish BOOLEAN DEFAULT FALSE,
    bearish BOOLEAN DEFAULT FALSE,
    neutral BOOLEAN DEFAULT TRUE,
    source VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(timestamp, currency, title)
);

CREATE INDEX idx_events_timestamp ON macro_events(timestamp);
CREATE INDEX idx_events_currency_impact ON macro_events(currency, impact);

-- Table: features
-- Stores computed features per timestamp
CREATE TABLE IF NOT EXISTS features (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL UNIQUE,
    feature_data JSONB NOT NULL,
    regime VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_features_timestamp ON features(timestamp);
CREATE INDEX idx_features_regime ON features(regime);

-- Table: labels
-- Stores trade signals (1, 0, -1)
CREATE TABLE IF NOT EXISTS labels (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL UNIQUE,
    label INTEGER CHECK (label IN (-1, 0, 1)),
    forward_return DECIMAL(10, 6),
    threshold DECIMAL(10, 6),
    regime VARCHAR(20),
    macro_event_window BOOLEAN DEFAULT FALSE,
    spread DECIMAL(10, 6),
    sharpe_last_week DECIMAL(10, 4),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_labels_timestamp ON labels(timestamp);
CREATE INDEX idx_labels_label ON labels(label);

-- Table: trades
-- Stores executed trades (live/simulation)
CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entry_timestamp TIMESTAMPTZ NOT NULL,
    exit_timestamp TIMESTAMPTZ,
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) CHECK (direction IN ('long', 'short')),
    entry_price DECIMAL(18, 8) NOT NULL,
    exit_price DECIMAL(18, 8),
    position_size DECIMAL(18, 8) NOT NULL,
    stop_loss DECIMAL(18, 8) NOT NULL,
    take_profit DECIMAL(18, 8) NOT NULL,
    exit_reason VARCHAR(50) CHECK (exit_reason IN ('take_profit', 'stop_loss', 'max_time', 'manual')),
    pnl DECIMAL(18, 8),
    pnl_percent DECIMAL(10, 4),
    r_multiple DECIMAL(10, 4),
    mae DECIMAL(10, 4),
    mfe DECIMAL(10, 4),
    model_confidence DECIMAL(5, 4),
    top_features JSONB,
    regime VARCHAR(20),
    is_simulation BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trades_entry_timestamp ON trades(entry_timestamp);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_direction ON trades(direction);
CREATE INDEX idx_trades_is_simulation ON trades(is_simulation);

-- Table: drift_log
-- Logs model drift detection moments
CREATE TABLE IF NOT EXISTS drift_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    features_drifted TEXT[],
    psi_values JSONB,
    ks_test_results JSONB,
    action VARCHAR(50) CHECK (action IN ('retrain_triggered', 'monitoring', 'model_archived')),
    model_version VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_drift_timestamp ON drift_log(timestamp);
CREATE INDEX idx_drift_action ON drift_log(action);

-- Table: system_health
-- Stores system health checks and status
CREATE TABLE IF NOT EXISTS system_health (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    component VARCHAR(50) NOT NULL,
    status VARCHAR(20) CHECK (status IN ('healthy', 'degraded', 'failed')),
    message TEXT,
    details JSONB
);

CREATE INDEX idx_health_timestamp ON system_health(timestamp);
CREATE INDEX idx_health_component ON system_health(component);

-- Insert initial health check
INSERT INTO system_health (component, status, message)
VALUES ('database', 'healthy', 'Database initialized successfully');
