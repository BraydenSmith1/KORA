"""
Tests for KORA logging system.
"""

import json
import logging
import pytest
from io import StringIO

from kora.logging import (
    JSONFormatter,
    HumanFormatter,
    setup_logging,
    get_logger,
    LogContext,
    log_optimizer_run,
)


class TestJSONFormatter:
    """Test JSON log formatting."""

    def test_basic_format(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "Test message"
        assert "timestamp" in data

    def test_with_context(self):
        formatter = JSONFormatter(context={"site_id": "test-site"})
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["context"]["site_id"] == "test-site"

    def test_with_exception(self):
        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert "Test error" in data["exception"]["message"]


class TestHumanFormatter:
    """Test human-readable log formatting."""

    def test_basic_format(self):
        formatter = HumanFormatter(use_colors=False)
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        assert "INFO" in output
        assert "test.module" in output
        assert "Test message" in output


class TestContextLogger:
    """Test context-aware logging."""

    def test_get_logger_with_context(self):
        logger = get_logger("test", site_id="test-site")
        assert logger.extra["site_id"] == "test-site"

    def test_log_context_manager(self):
        logger = get_logger("test", site_id="test-site")

        with LogContext(logger, run_id="abc123") as ctx_logger:
            assert ctx_logger.extra["run_id"] == "abc123"
            assert ctx_logger.extra["site_id"] == "test-site"

        # Context should be restored
        assert "run_id" not in logger.extra


class TestLogHelpers:
    """Test logging helper functions."""

    def test_log_optimizer_run_success(self, caplog):
        logger = get_logger("test")

        with caplog.at_level(logging.INFO):
            log_optimizer_run(
                logger,
                site_id="test",
                horizon_hours=24,
                solver="highs",
                status="success",
                solve_time_sec=5.2,
                curtailment_rate=0.08,
                revenue=1000,
            )

        assert "completed" in caplog.text.lower()
        assert "8.0%" in caplog.text  # curtailment rate

    def test_log_optimizer_run_failure(self, caplog):
        logger = get_logger("test")

        with caplog.at_level(logging.ERROR):
            log_optimizer_run(
                logger,
                site_id="test",
                horizon_hours=24,
                solver="highs",
                status="error",
            )

        assert "failed" in caplog.text.lower()


class TestSetupLogging:
    """Test logging setup."""

    def test_setup_basic(self):
        setup_logging(level="DEBUG", json_output=False)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
        assert len(root_logger.handlers) > 0

    def test_setup_json(self):
        setup_logging(level="INFO", json_output=True)

        root_logger = logging.getLogger()
        assert any(
            isinstance(h.formatter, JSONFormatter)
            for h in root_logger.handlers
        )
