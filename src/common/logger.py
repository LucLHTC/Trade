"""
Logging utilities for the trading system.
Supports both standard logging and JSONL format for structured logs.
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import os
import sys


class JSONLHandler(logging.Handler):
    """Custom logging handler that writes logs in JSONL format."""

    def __init__(self, log_dir: str):
        super().__init__()
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def emit(self, record: logging.LogRecord):
        """Emit a log record as a JSON line."""
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }

            # Add exception info if present
            if record.exc_info:
                log_entry["exception"] = self.format(record)

            # Add extra fields if present
            if hasattr(record, "extra_data"):
                log_entry["extra"] = record.extra_data

            # Write to daily log file
            log_file = self.log_dir / f"{datetime.utcnow().strftime('%Y%m%d')}.jsonl"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")

        except Exception as e:
            # Fallback to stderr if logging fails
            print(f"Failed to write log: {e}", file=sys.stderr)


def setup_logger(
    name: str,
    level: str = "INFO",
    log_dir: Optional[str] = None,
    use_jsonl: bool = True,
) -> logging.Logger:
    """
    Set up a logger with both console and JSONL file handlers.

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for JSONL log files
        use_jsonl: Whether to enable JSONL file logging

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Console handler with color support
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # JSONL file handler for structured logs
    if use_jsonl and log_dir:
        jsonl_handler = JSONLHandler(log_dir)
        jsonl_handler.setLevel(logging.WARNING)  # Only log warnings and errors to file
        logger.addHandler(jsonl_handler)

    return logger


def get_logger(
    name: str,
    level: Optional[str] = None,
    log_dir: Optional[str] = None,
) -> logging.Logger:
    """
    Get a logger instance with automatic configuration.

    Args:
        name: Logger name (typically __name__)
        level: Optional logging level override
        log_dir: Optional log directory override

    Returns:
        Configured logger instance
    """
    # Load settings (avoid circular import by importing here)
    try:
        from src.common.config import get_settings

        settings = get_settings()
        level = level or settings.log_level
        log_dir = log_dir or settings.log_dir
    except Exception:
        level = level or "INFO"
        log_dir = log_dir or "logs/errors"

    return setup_logger(name, level=level, log_dir=log_dir)


def log_with_extra(logger: logging.Logger, level: str, message: str, **extra_data):
    """
    Log a message with additional structured data.

    Args:
        logger: Logger instance
        level: Log level (info, warning, error, etc.)
        message: Log message
        **extra_data: Additional key-value pairs to include in JSONL
    """
    log_method = getattr(logger, level.lower())
    log_method(message, extra={"extra_data": extra_data})


def log_trade_execution(
    logger: logging.Logger,
    trade_id: str,
    action: str,
    symbol: str,
    price: float,
    **kwargs,
):
    """
    Log a trade execution with structured data.

    Args:
        logger: Logger instance
        trade_id: Unique trade identifier
        action: Trade action (entry, exit, etc.)
        symbol: Trading symbol
        price: Execution price
        **kwargs: Additional trade metadata
    """
    log_with_extra(
        logger,
        "info",
        f"Trade {action}: {symbol} @ {price}",
        trade_id=trade_id,
        action=action,
        symbol=symbol,
        price=price,
        **kwargs,
    )


def log_model_event(
    logger: logging.Logger, event_type: str, model_name: str, **kwargs
):
    """
    Log a model-related event.

    Args:
        logger: Logger instance
        event_type: Type of event (training, prediction, drift, etc.)
        model_name: Name of the model
        **kwargs: Additional event metadata
    """
    log_with_extra(
        logger,
        "info",
        f"Model event [{event_type}]: {model_name}",
        event_type=event_type,
        model_name=model_name,
        **kwargs,
    )


# Example usage in modules:
# from src.common.logger import get_logger
# logger = get_logger(__name__)
# logger.info("This is an info message")
# log_with_extra(logger, "error", "Something went wrong", error_code=500, trace="...")
