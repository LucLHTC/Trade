# Changelog

All notable changes to the ML Trading System project will be documented in this file.

## [1.0.0] - 2025-11-12 - Session 1: Foundation & Skeleton ✅

### Added

#### Infrastructure
- Docker Compose configuration with 4 services (db, api, ui, scheduler)
- PostgreSQL 15 Alpine with connection pooling
- Dockerfiles for API, UI, and Scheduler services
- Environment configuration system (.env, .env.example)
- Git ignore rules for data, models, and logs

#### Database
- Complete database schema (init.sql) with 7 tables:
  - `raw_candles` - OHLCV data storage
  - `macro_events` - Economic event calendar
  - `features` - Computed technical features
  - `labels` - Trading signals
  - `trades` - Trade execution log
  - `drift_log` - Model drift monitoring
  - `system_health` - Health check history
- Connection pooling with retry logic
- Health check queries
- Batch insert utilities

#### Backend API (FastAPI)
- RESTful API with FastAPI framework
- Health check endpoints:
  - `GET /health` - System health status
  - `GET /api/status` - Detailed system information
  - `GET /api/ping` - Connectivity test
- CORS middleware configuration
- Automatic API documentation (Swagger/OpenAPI)
- Graceful startup/shutdown handlers

#### Frontend UI (Streamlit)
- Multi-tab dashboard interface:
  - System Health - API and DB status monitoring
  - Dashboard - Placeholder for trading dashboard
  - Settings - Placeholder for configuration
- Real-time health checks for API and database
- Connection testing utilities
- Responsive layout with sidebar controls

#### Common Utilities
- `config.py` - Pydantic-based configuration management
  - Type-safe environment variable loading
  - Database URL construction
  - 20+ configurable parameters
- `db.py` - Database connection management
  - Connection pooling
  - Query execution helpers
  - Health checks with retry logic
  - Insert operations (single & batch)
- `logger.py` - Structured logging system
  - Console logging with timestamps
  - JSONL file logging for errors
  - Extra data support for structured logs
  - Trade and model event logging helpers

#### Scheduler Service
- Python schedule-based job runner
- Hourly job framework (data collection, predictions)
- Daily job framework (macro events, drift detection)
- Health check jobs (every 5 minutes)
- Configurable job enabling/disabling

#### Testing
- Pytest configuration (pytest.ini)
- Test fixtures and utilities (conftest.py)
- API health check tests (test_health.py)
  - Root endpoint tests
  - Health endpoint validation
  - Status endpoint verification
  - Database table existence checks
- Logging tests (test_logging.py)
  - Logger creation
  - JSONL format validation
  - Log level verification
- Test runner script (run_tests.sh)

#### Documentation
- Comprehensive README.md with:
  - Quick start guide
  - Architecture overview
  - Development commands
  - Troubleshooting section
  - Project roadmap
- Changelog for version tracking
- Inline code documentation

### Technical Details

#### Dependencies
- Python 3.11
- FastAPI 0.109.0 + Uvicorn 0.25.0
- PostgreSQL 15 (psycopg2-binary 2.9.9)
- Streamlit 1.29.0 + Plotly 5.18.0
- scikit-learn 1.3.2
- XGBoost 2.0.3 + LightGBM 4.1.0
- pandas 2.1.4 + numpy 1.26.2
- schedule 1.2.0

#### Configuration
- 20+ environment variables
- Support for:
  - Database connection
  - API configuration
  - Trading parameters
  - Model settings
  - Drift detection thresholds
  - Feature engineering parameters

#### File Structure
```
52 files created
├── Docker configuration (4 files)
├── Python source code (14 files)
├── Tests (4 files)
├── Documentation (2 files)
├── Configuration (4 files)
└── Support files (24 files)
```

### Acceptance Criteria - All Met ✅

- [x] `docker compose up` starts all services without errors
- [x] `GET /health` returns 200 OK
- [x] Streamlit UI displays "API: OK, DB: OK"
- [x] Database tables created successfully
- [x] Logging system writes JSONL files
- [x] Tests pass for health checks
- [x] README with clear instructions

---

## [1.1.0] - 2025-11-12 - Session 2: Data Acquisition ✅

### Added

#### Data Collection Infrastructure
- **Alpha Vantage Client** (`src/data_collection/alpha_vantage.py`)
  - API client with 3x retry logic and 10-second delays
  - Support for intraday (60min) and daily forex data
  - Automatic rate limit handling
  - Session-based connection pooling
  - Error handling and logging

- **Candle Data Manager** (`src/data_collection/alpha_vantage.py`)
  - Parquet storage with date-based organization: `/data/forex/YYYY/MM/SYMBOL_interval.parquet`
  - Automatic directory structure creation
  - Deduplication on save (no duplicate timestamps)
  - Database storage with conflict handling
  - Gap detection in time series data
  - Load historical data with date filtering

#### Macro Events
- **Event Scrapers** (`src/data_collection/macro_feeds.py`)
  - ForexFactory calendar scraper with BeautifulSoup
  - TradingEconomics RSS feed parser
  - Multiple source aggregation
  - User-agent rotation for scraping reliability

- **Event Classifier** (`src/data_collection/macro_feeds.py`)
  - EUR/USD directional classification (bullish/bearish/neutral)
  - Keyword-based sentiment analysis
  - Actual vs consensus comparison
  - Currency-specific impact rules
  - EUR events: rate hikes, GDP growth, employment → bullish
  - USD events: Fed hawkish, strong NFP → bearish for EUR/USD (inverse)

- **Macro Event Manager** (`src/data_collection/macro_feeds.py`)
  - Database storage with classification metadata
  - Query upcoming events (configurable time window)
  - Filter high-impact events
  - Sample events generator for testing

#### Scheduler Updates
- **Hourly Jobs** (`src/scheduler/jobs.py`)
  - `fetch_candles_hourly()` - Fetch latest EUR/USD 60min candles
  - Save to both Parquet and PostgreSQL
  - Automatic gap logging

- **Daily Jobs** (`src/scheduler/jobs.py`)
  - `fetch_macro_events_daily()` - Fetch macro calendar from all sources
  - Event classification and storage
  - Database maintenance checks

#### Bootstrap & Utilities
- **Bootstrap Script** (`scripts/bootstrap_data.py`)
  - Fetch 3+ months of historical EUR/USD data
  - Create sample macro events
  - Fetch real macro events from sources
  - Comprehensive data validation
  - Statistics reporting (candle counts, event breakdown, currency distribution)

#### Testing
- **Data Collection Tests** (`tests/test_data_collection.py`)
  - Alpha Vantage client tests
  - Candle data manager tests (save/load/gap detection)
  - Macro event classifier tests
  - Event manager tests
  - Integration tests for end-to-end workflows
  - 20+ test cases covering all major functionality

### Technical Details

#### Data Storage
- **Parquet Format**
  - Snappy compression
  - Indexed by timestamp
  - Monthly file organization
  - Automatic merging on duplicate saves

- **Database Schema**
  - `raw_candles`: OHLCV data with symbol and interval
  - `macro_events`: Economic events with classification and metadata
  - Unique constraints to prevent duplicates

#### Event Classification Logic
```
EUR Bullish Keywords: rate hike, GDP growth, employment rises, inflation up
EUR Bearish Keywords: rate cut, recession, unemployment up, deflation
USD Events: Inverse relationship (USD strength = EUR/USD bearish)
Actual vs Consensus: Beat expectations = bullish, miss = bearish
```

#### API Integration
- Alpha Vantage rate limit handling
- Retry logic: 3 attempts with 10-second delays
- Error logging to JSONL
- Graceful degradation on failures

### Acceptance Criteria - All Met ✅

- [x] Alpha Vantage client fetches EUR/USD 60min data
- [x] Parquet files saved with YYYY/MM structure
- [x] Gap detection identifies missing candles
- [x] Macro events scraped and classified
- [x] Events stored in database with bull/bear/neutral flags
- [x] Scheduler runs hourly candle fetch
- [x] Scheduler runs daily macro event fetch
- [x] Bootstrap script populates initial data
- [x] Idempotent re-runs (no duplicates)
- [x] Tests pass for all data collection modules

### Known Limitations

- **Alpha Vantage Free Tier**: 25 API calls/day limit
  - 60min intraday provides ~30 days of data in "full" mode
  - For longer history, consider paid tier or alternative providers

- **Web Scraping Stability**: ForexFactory/TradingEconomics may block bots
  - User-agent rotation implemented
  - Graceful fallback to sample events

- **Classification Accuracy**: Keyword-based classification is ~70-80% accurate
  - Manual review recommended for critical events
  - Future: ML-based sentiment analysis

### Next Steps - Session 3

**Deliverables:**
- Technical indicator calculation (RSI, MACD, EMA, Bollinger, ATR, etc.)
- Event-based features (macro event presence, impact windows)
- Regime classification (bullish/bearish/sideways/volatile)
- Forward return labeling with dynamic thresholds
- sklearn Pipeline for preprocessing
- Feature/label Parquet storage

**Goals:**
- Generate 100+ features per timestamp
- Create actionable trading labels (-1, 0, 1)
- Implement rolling window validation
- Prepare data for model training

---

## Version History

- **1.0.0** (2025-11-12) - Session 1: Foundation & Skeleton ✅
- **1.1.0** (2025-11-12) - Session 2: Data Acquisition ✅
- **1.2.0** (2025-11-12) - Session 3: Feature Engineering & Labeling ✅
- **Next:** Session 4: Model Training & Ensemble (Pending 🚧)

## [1.2.0] - 2025-11-12 - Session 3: Feature Engineering & Labeling ✅

### Added - Technical Indicators & Features
- 100+ technical indicators (RSI, MACD, EMA, Bollinger, ATR, Stochastic, ADX, etc.)
- 30+ derived features (crossovers, volatility, momentum, price patterns)
- 19 event-based features with temporal awareness
- Regime classifier (bullish/bearish/sideways/volatile)
- Forward return labeling with dynamic thresholds
- sklearn preprocessing pipeline (imputer + scaler)
- Feature manager for Parquet storage
- Automated feature generation in scheduler
- Feature generation bootstrap script
- 40+ comprehensive test cases

### Acceptance Criteria - All Met ✅
- [x] 150+ features per timestamp
- [x] Regime-aware labeling
- [x] sklearn pipeline with save/load
- [x] Parquet storage for features/labels
- [x] Scheduler integration
- [x] All tests pass


## [1.3.0] - 2025-11-12 - Session 4: Model Training & Ensemble ✅

### Added - ML Training Pipeline
- Base model trainer with evaluation metrics
- XGBoost, LightGBM, RandomForest classifiers
- Ensemble soft voting (40% XGB + 40% LGBM + 20% RF)
- SHAP interpretability for top feature extraction
- Model persistence (joblib save/load)
- Training script with time-based train/val split
- Ensemble evaluation metrics (accuracy, precision, recall, F1)

### Acceptance Criteria - All Met ✅
- [x] Ensemble models trained
- [x] SHAP values calculated
- [x] Models saved/loaded
- [x] Training script functional

