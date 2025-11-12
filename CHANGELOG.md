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

### Next Steps - Session 2

**Deliverables:**
- Alpha Vantage API integration for EUR/USD 60min candles
- Macro event scraping (TradingEconomics/ForexFactory)
- Data validation and gap detection
- Parquet file storage with date-based organization
- Idempotent data collection (no duplicates)

**Goals:**
- Collect 3+ months of historical EUR/USD data
- Populate macro_events table with economic calendar
- Implement retry logic for API failures
- Schedule daily data collection jobs

---

## Version History

- **1.0.0** (2025-11-12) - Session 1: Foundation & Skeleton ✅
- **Next:** Session 2: Data Acquisition (In Progress 🚧)
