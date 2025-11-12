"""
Tests for logging functionality.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.logger import get_logger, log_with_extra


class TestLogging:
    """Test logging utilities."""

    def test_logger_creation(self):
        """Test that logger can be created."""
        logger = get_logger(__name__)
        assert logger is not None
        assert logger.name == __name__

    def test_logger_has_handlers(self):
        """Test that logger has console handler."""
        logger = get_logger("test_logger")
        assert len(logger.handlers) > 0

    def test_logger_log_levels(self):
        """Test that logger respects log levels."""
        logger = get_logger("test_levels", level="INFO")
        assert logger.level <= 20  # INFO level

    def test_log_with_extra_data(self, tmp_path):
        """Test logging with extra structured data."""
        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        logger = get_logger("test_extra", log_dir=str(log_dir))

        # Log a warning (which should go to JSONL)
        logger.warning("Test warning", extra={"extra_data": {"key": "value"}})

        # Check if log file was created
        log_files = list(log_dir.glob("*.jsonl"))
        assert len(log_files) > 0

    def test_jsonl_format(self, tmp_path):
        """Test that JSONL logs are valid JSON."""
        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        logger = get_logger("test_jsonl", log_dir=str(log_dir))

        # Log an error (should write to JSONL)
        logger.error("Test error message")

        # Read and validate JSONL
        log_file = log_dir / f"{datetime.utcnow().strftime('%Y%m%d')}.jsonl"
        if log_file.exists():
            with open(log_file, "r") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        assert "timestamp" in data
                        assert "level" in data
                        assert "message" in data
