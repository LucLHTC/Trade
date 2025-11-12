"""
FastAPI application for the ML trading system.
Provides REST API endpoints for predictions, trades, and system monitoring.
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import Dict, Any
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.common.config import get_settings
from src.common.db import get_db
from src.common.logger import get_logger

# Initialize
settings = get_settings()
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ML Trading System API",
    description="API for autonomous algorithmic trading system",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("🚀 Starting ML Trading System API")
    logger.info(f"Environment: {settings.tz}")
    logger.info(f"Database: {settings.postgres_host}:{settings.postgres_port}")

    # Test database connection
    try:
        db = get_db()
        if db.health_check():
            logger.info("✅ Database connection successful")
        else:
            logger.error("❌ Database health check failed")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("🛑 Shutting down ML Trading System API")
    from src.common.db import close_db

    close_db()


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "ML Trading System API",
        "version": "1.0.0",
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Validates API, database, and system status.
    """
    health_status = {
        "api": "healthy",
        "database": "unknown",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Check database
    try:
        db = get_db()
        if db.health_check():
            health_status["database"] = "healthy"
        else:
            health_status["database"] = "unhealthy"
            health_status["api"] = "degraded"
    except Exception as e:
        health_status["database"] = "failed"
        health_status["database_error"] = str(e)
        health_status["api"] = "degraded"
        logger.error(f"Database health check failed: {e}")

    # Determine HTTP status code
    if health_status["api"] == "healthy":
        return JSONResponse(content=health_status, status_code=status.HTTP_200_OK)
    else:
        return JSONResponse(
            content=health_status, status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@app.get("/api/status")
async def get_status():
    """
    Get detailed system status including configuration.
    """
    db = get_db()

    status_info = {
        "api": {
            "status": "online",
            "version": "1.0.0",
            "uptime": "N/A",  # TODO: Track uptime
        },
        "database": {
            "status": "healthy" if db.health_check() else "unhealthy",
            "host": settings.postgres_host,
            "port": settings.postgres_port,
            "database": settings.postgres_db,
        },
        "configuration": {
            "initial_equity": settings.initial_equity,
            "risk_per_trade": settings.risk_per_trade,
            "max_trades_per_week": settings.max_trades_per_week,
            "training_window_days": settings.training_window_days,
            "drift_psi_threshold": settings.drift_psi_threshold,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }

    return status_info


@app.get("/api/ping")
async def ping():
    """Simple ping endpoint for connectivity tests."""
    return {"message": "pong", "timestamp": datetime.utcnow().isoformat()}


# Additional endpoints will be added in future sessions:
# - POST /api/predict - Model predictions
# - POST /api/simulate - Run simulation
# - GET /api/trades - Get trades
# - GET /api/drift - Drift detection status
# - POST /api/retrain - Trigger model retraining


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
