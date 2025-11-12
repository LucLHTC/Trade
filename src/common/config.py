"""
Configuration management for the trading system.
Loads environment variables and provides typed access to configuration.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database Configuration
    postgres_host: str = Field(default="db", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="trading", alias="POSTGRES_DB")
    postgres_user: str = Field(default="trader", alias="POSTGRES_USER")
    postgres_password: str = Field(default="traderpwd", alias="POSTGRES_PASSWORD")

    # API Configuration
    api_host: str = Field(default="api", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_base_url: str = Field(default="http://api:8000", alias="API_BASE_URL")

    # Timezone
    tz: str = Field(default="UTC", alias="TZ")

    # Alpha Vantage API
    alphavantage_api_key: Optional[str] = Field(default=None, alias="ALPHAVANTAGE_API_KEY")

    # Trading Configuration
    initial_equity: float = Field(default=10000.0, alias="INITIAL_EQUITY")
    risk_per_trade: float = Field(default=0.01, alias="RISK_PER_TRADE")
    max_trades_per_week: int = Field(default=3, alias="MAX_TRADES_PER_WEEK")

    # Model Configuration
    model_path: str = Field(default="models/current/model.pkl", alias="MODEL_PATH")
    shadow_model_path: str = Field(default="models/shadow/model.pkl", alias="SHADOW_MODEL_PATH")
    training_window_days: int = Field(default=90, alias="TRAINING_WINDOW_DAYS")
    validation_window_days: int = Field(default=10, alias="VALIDATION_WINDOW_DAYS")

    # Drift Detection
    drift_psi_threshold: float = Field(default=0.25, alias="DRIFT_PSI_THRESHOLD")
    drift_ks_pvalue: float = Field(default=0.01, alias="DRIFT_KS_PVALUE")

    # Feature Engineering
    lookahead_periods: int = Field(default=3, alias="LOOKAHEAD_PERIODS")
    label_threshold_multiplier: float = Field(default=0.7, alias="LABEL_THRESHOLD_MULTIPLIER")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_dir: str = Field(default="logs/errors", alias="LOG_DIR")

    # Scheduler
    scheduler_enabled: bool = Field(default=True, alias="SCHEDULER_ENABLED")
    hourly_jobs_enabled: bool = Field(default=True, alias="HOURLY_JOBS_ENABLED")
    daily_jobs_enabled: bool = Field(default=True, alias="DAILY_JOBS_ENABLED")

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings
