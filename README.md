# 📈 ML Trading System

Autonomous algorithmic trading system using machine learning for EUR/USD mid-frequency trading.

## 🎯 Project Overview

This is a **self-learning ML trading system** that:
- Trades EUR/USD with 2-3 trades per week (mid-frequency)
- Uses ensemble ML models (XGBoost, LightGBM, Random Forest)
- Implements drift detection and automatic retraining
- Provides real-time monitoring via Streamlit UI
- Runs locally in Docker containers

## 🏗️ Architecture

### Services
- **PostgreSQL**: Database for candles, features, labels, trades, and drift logs
- **FastAPI**: REST API for predictions, trades, and system status
- **Streamlit**: Interactive dashboard for monitoring and control
- **Scheduler**: Automated jobs for data collection and model updates

### Tech Stack
- **Backend**: Python 3.11, FastAPI, PostgreSQL
- **ML**: scikit-learn, XGBoost, LightGBM, SHAP, Optuna
- **Data**: pandas, numpy, pyarrow (Parquet)
- **UI**: Streamlit, Plotly
- **Infrastructure**: Docker, docker-compose

## 📦 Project Structure

```
trading-system/
├── docker-compose.yml          # Container orchestration
├── requirements.txt            # Python dependencies
├── .env                        # Environment configuration
├── init.sql                    # Database schema
├── src/
│   ├── common/                 # Shared utilities
│   │   ├── config.py          # Configuration management
│   │   ├── db.py              # Database utilities
│   │   └── logger.py          # JSONL logging
│   ├── api/                    # FastAPI application
│   │   └── main.py            # API endpoints
│   ├── data_collection/        # Data acquisition (Session 2)
│   ├── features/               # Feature engineering (Session 3)
│   ├── labeling/               # Label generation (Session 3)
│   ├── training/               # Model training (Session 4)
│   ├── inference/              # Predictions (Session 5)
│   ├── drift/                  # Drift detection (Session 7)
│   ├── risk/                   # Risk management (Session 5)
│   ├── trading/                # Trade execution (Session 5)
│   └── scheduler/              # Automated jobs
│       └── jobs.py            # Scheduled tasks
├── ui/
│   └── app.py                 # Streamlit dashboard
├── data/                       # Data storage
│   ├── forex/                 # Candle data
│   ├── features/              # Feature files
│   └── labels/                # Label files
├── models/                     # Model storage
│   ├── current/               # Active model
│   ├── shadow/                # Shadow model
│   └── archived/              # Historical models
├── logs/                       # Log files
│   └── errors/                # Error logs (JSONL)
└── tests/                      # Test suite
```

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- At least 4GB RAM available
- Alpha Vantage API key (free tier: https://www.alphavantage.co/support/#api-key)

### Setup

1. **Clone the repository**
   ```bash
   cd /path/to/Trade
   ```

2. **Configure environment**
   ```bash
   # Copy example env file
   cp .env.example .env

   # Edit .env and add your API keys
   nano .env
   ```

3. **Start the system**
   ```bash
   docker compose up --build
   ```

   This will start all services:
   - PostgreSQL: `localhost:5432`
   - FastAPI: `http://localhost:8000`
   - Streamlit UI: `http://localhost:8501`
   - Scheduler: background service

4. **Verify installation**
   - Open browser to `http://localhost:8501`
   - Check "System Health" tab
   - Ensure API and Database show "✅ healthy"

5. **Bootstrap historical data** (Session 2+)
   ```bash
   # Run the bootstrap script to fetch initial data
   docker compose exec api python scripts/bootstrap_data.py
   ```

   This will:
   - Fetch EUR/USD 60min candles from Alpha Vantage
   - Create sample macro events
   - Attempt to fetch real macro events
   - Validate and report data statistics

### Access Points

| Service | URL | Description |
|---------|-----|-------------|
| Streamlit UI | http://localhost:8501 | Interactive dashboard |
| FastAPI Docs | http://localhost:8000/docs | API documentation |
| API Health | http://localhost:8000/health | Health check endpoint |
| PostgreSQL | localhost:5432 | Database (user: trader) |

## 🧪 Testing

### Manual Health Check

```bash
# Test API
curl http://localhost:8000/health

# Test database connection
docker compose exec db psql -U trader -d trading -c "SELECT 1;"
```

### Run automated tests

```bash
# Run all tests
docker compose exec api pytest tests/ -v

# Run specific test
docker compose exec api pytest tests/test_health.py -v
```

## 📊 Current Status: Session 4 Complete

### ✅ Session 1: Foundation
- [x] Docker infrastructure setup
- [x] PostgreSQL database with schema
- [x] FastAPI with health endpoints
- [x] Streamlit UI with system monitoring
- [x] Configuration management
- [x] Database utilities
- [x] JSONL logging system
- [x] Scheduler framework

### ✅ Session 2: Data Acquisition
- [x] Alpha Vantage API client with retry logic
- [x] EUR/USD 60min candle data fetching
- [x] Parquet storage with date-based organization
- [x] Gap detection in candle data
- [x] Macro event scrapers (ForexFactory, TradingEconomics)
- [x] Event classification (bullish/bearish/neutral for EUR/USD)
- [x] Automated hourly and daily data collection jobs
- [x] Bootstrap script for historical data
- [x] Comprehensive data collection tests

### ✅ Session 3: Feature Engineering & Labeling
- [x] Technical indicators (100+ indicators: RSI, MACD, EMA, Bollinger, ATR, Stochastic, ADX, etc.)
- [x] Derived features (crossovers, volatility, momentum, price patterns)
- [x] Event-based features (19 event features with lookback/lookahead)
- [x] Regime classifier (bullish/bearish/sideways/volatile)
- [x] Forward return labeling with dynamic thresholds
- [x] sklearn preprocessing pipeline (imputer + scaler)
- [x] Feature manager for Parquet storage
- [x] Automated feature generation in scheduler
- [x] Feature generation bootstrap script
- [x] Comprehensive feature tests (40+ test cases)

### ✅ Session 4: Model Training & Ensemble
- [x] Base model trainer with evaluation metrics
- [x] XGBoost, LightGBM, RandomForest trainers
- [x] Ensemble soft voting (weighted average)
- [x] SHAP interpretability for feature importance
- [x] Model persistence (save/load with joblib)
- [x] Training script with train/val split
- [x] Ensemble evaluation metrics

### 🚧 Coming in Future Sessions
- [ ] **Session 4**: Model training & ensemble
- [ ] **Session 5**: Inference, risk management, simulation
- [ ] **Session 6**: Full UI dashboard with visualizations
- [ ] **Session 7**: Drift detection & auto-retraining

## 🛠️ Development Commands

### Start services
```bash
docker compose up -d              # Start in background
docker compose up --build         # Rebuild and start
```

### View logs
```bash
docker compose logs -f api        # API logs
docker compose logs -f ui         # UI logs
docker compose logs -f scheduler  # Scheduler logs
docker compose logs -f db         # Database logs
```

### Stop services
```bash
docker compose down               # Stop all services
docker compose down -v            # Stop and remove volumes
```

### Database access
```bash
# Connect to database
docker compose exec db psql -U trader -d trading

# Run SQL file
docker compose exec db psql -U trader -d trading -f /path/to/file.sql
```

### Restart specific service
```bash
docker compose restart api
docker compose restart ui
docker compose restart scheduler
```

## 📝 Configuration

Edit `.env` file to customize:

```bash
# Trading parameters
INITIAL_EQUITY=10000.00
RISK_PER_TRADE=0.01
MAX_TRADES_PER_WEEK=3

# Model parameters
TRAINING_WINDOW_DAYS=90
VALIDATION_WINDOW_DAYS=10

# Drift detection
DRIFT_PSI_THRESHOLD=0.25
DRIFT_KS_PVALUE=0.01
```

## 🐛 Troubleshooting

### Database connection failed
```bash
# Check database status
docker compose ps db

# Restart database
docker compose restart db

# Check database logs
docker compose logs db
```

### API not responding
```bash
# Check API status
docker compose ps api

# View API logs
docker compose logs -f api

# Restart API
docker compose restart api
```

### Streamlit not loading
```bash
# Check UI status
docker compose ps ui

# Restart UI
docker compose restart ui
```

## 📈 Roadmap

### MVP Milestones
1. ✅ **Foundation** - Infrastructure setup
2. ⏳ **Data Pipeline** - Acquisition & storage
3. ⏳ **Feature Engineering** - Technical & event features
4. ⏳ **ML Training** - Ensemble models
5. ⏳ **Trading Logic** - Risk management & simulation
6. ⏳ **UI Dashboard** - Visualization & monitoring
7. ⏳ **Production** - Drift detection & automation

### Future Enhancements
- [ ] Multi-asset support (other forex pairs)
- [ ] Alternative data sources (OANDA, Twelve Data)
- [ ] MLflow integration for experiment tracking
- [ ] Advanced risk models (Kelly Criterion)
- [ ] React dashboard (alternative to Streamlit)
- [ ] Backtesting engine with historical data
- [ ] Live trading integration with brokers

## 📚 Documentation

- [Master Prompt](docs/master_prompt.md) - Complete system specification
- [API Reference](http://localhost:8000/docs) - FastAPI interactive docs
- [Database Schema](init.sql) - PostgreSQL table definitions

## 🤝 Contributing

This is a personal trading system project. For collaboration or questions, please open an issue.

## ⚠️ Disclaimer

This trading system is for educational and research purposes. Trading involves substantial risk of loss. Always test thoroughly with paper trading before considering live deployment. Past performance does not guarantee future results.

## 📄 License

Private project - All rights reserved

---

**Version**: 1.0.0 (Session 1)
**Last Updated**: 2025-11-12
**Status**: Foundation Complete ✅
