"""
KORA Structured Logging System

Provides JSON-formatted logging for production environments with:
- Structured log entries (JSON format)
- Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Context enrichment (site_id, run_id, etc.)
- File and console handlers
- Log rotation
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs JSON-structured log entries.

    Each log entry contains:
    - timestamp: ISO 8601 UTC timestamp
    - level: Log level name
    - logger: Logger name
    - message: Log message
    - context: Additional context fields
    - exception: Exception info if present
    """

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.context = context or {}

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add static context
        if self.context:
            log_entry["context"] = self.context.copy()
        else:
            log_entry["context"] = {}

        # Add dynamic context from record
        if hasattr(record, "context") and record.context:
            log_entry["context"].update(record.context)

        # Add extra fields directly to context
        for key in ["site_id", "run_id", "optimizer_run", "horizon", "solver"]:
            if hasattr(record, key):
                log_entry["context"][key] = getattr(record, key)

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add source location for errors
        if record.levelno >= logging.ERROR:
            log_entry["source"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        return json.dumps(log_entry)


class HumanFormatter(logging.Formatter):
    """
    Human-readable formatter for console output during development.

    Format: [TIMESTAMP] LEVEL | LOGGER | MESSAGE
    """

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname

        if self.use_colors:
            color = self.COLORS.get(level, "")
            level_str = f"{color}{level:8}{self.RESET}"
        else:
            level_str = f"{level:8}"

        # Truncate logger name if too long
        logger_name = record.name
        if len(logger_name) > 20:
            logger_name = "..." + logger_name[-17:]

        base_msg = f"[{timestamp}] {level_str} | {logger_name:20} | {record.getMessage()}"

        # Add context if present
        context_parts = []
        if hasattr(record, "context") and record.context:
            for k, v in record.context.items():
                context_parts.append(f"{k}={v}")
        for key in ["site_id", "run_id"]:
            if hasattr(record, key):
                context_parts.append(f"{key}={getattr(record, key)}")

        if context_parts:
            base_msg += f" [{', '.join(context_parts)}]"

        # Add exception if present
        if record.exc_info:
            base_msg += "\n" + self.formatException(record.exc_info)

        return base_msg


class ContextLogger(logging.LoggerAdapter):
    """
    Logger adapter that adds context to all log messages.

    Usage:
        logger = get_logger("kora.optimizer", site_id="mahavelona")
        logger.info("Starting optimization", extra={"horizon": 24})
    """

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        # Merge extra with context
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


def setup_logging(
    level: str = "INFO",
    json_output: bool = False,
    log_file: Optional[str | Path] = None,
    max_bytes: int = 10_000_000,  # 10 MB
    backup_count: int = 5,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Configure the logging system.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: If True, output JSON format; otherwise human-readable
        log_file: Optional file path for log output
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        context: Static context to include in all log entries
    """
    # Get numeric level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Choose formatter
    if json_output:
        formatter = JSONFormatter(context=context)
    else:
        formatter = HumanFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (always JSON for parsing)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(JSONFormatter(context=context))
        root_logger.addHandler(file_handler)

    # Suppress noisy loggers
    logging.getLogger("pyomo").setLevel(logging.WARNING)
    logging.getLogger("pyomo.core").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("pymodbus").setLevel(logging.WARNING)


def get_logger(
    name: str,
    **context: Any,
) -> ContextLogger:
    """
    Get a logger with optional context.

    Args:
        name: Logger name (typically module name)
        **context: Key-value pairs to include in all log entries

    Returns:
        ContextLogger with the specified context
    """
    base_logger = logging.getLogger(name)
    return ContextLogger(base_logger, context)


class LogContext:
    """
    Context manager for temporarily adding context to logs.

    Usage:
        with LogContext(logger, run_id="abc123"):
            logger.info("Processing")  # Includes run_id
    """

    def __init__(self, logger: ContextLogger, **context: Any):
        self.logger = logger
        self.context = context
        self.old_extra = None

    def __enter__(self) -> ContextLogger:
        self.old_extra = self.logger.extra.copy()
        self.logger.extra.update(self.context)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.logger.extra = self.old_extra


# Convenience functions for quick logging
def log_optimizer_run(
    logger: ContextLogger,
    site_id: str,
    horizon_hours: int,
    solver: str,
    status: str,
    solve_time_sec: Optional[float] = None,
    curtailment_rate: Optional[float] = None,
    revenue: Optional[float] = None,
) -> None:
    """Log an optimizer run with standard fields."""
    context = {
        "site_id": site_id,
        "horizon_hours": horizon_hours,
        "solver": solver,
        "status": status,
    }
    if solve_time_sec is not None:
        context["solve_time_sec"] = round(solve_time_sec, 2)
    if curtailment_rate is not None:
        context["curtailment_rate"] = round(curtailment_rate, 4)
    if revenue is not None:
        context["revenue"] = round(revenue, 2)

    if status == "success":
        logger.info(
            f"Optimizer run completed: {curtailment_rate*100:.1f}% curtailment",
            extra={"context": context},
        )
    elif status == "timeout":
        logger.warning(
            "Optimizer run timed out",
            extra={"context": context},
        )
    else:
        logger.error(
            f"Optimizer run failed: {status}",
            extra={"context": context},
        )


def log_telemetry_event(
    logger: ContextLogger,
    site_id: str,
    event_type: str,
    data: Dict[str, Any],
) -> None:
    """Log a telemetry event."""
    logger.debug(
        f"Telemetry: {event_type}",
        extra={
            "context": {
                "site_id": site_id,
                "event_type": event_type,
                "data": data,
            }
        },
    )


def log_alert(
    logger: ContextLogger,
    site_id: str,
    alert_type: str,
    message: str,
    severity: str = "warning",
    data: Optional[Dict[str, Any]] = None,
) -> None:
    """Log an alert event."""
    context = {
        "site_id": site_id,
        "alert_type": alert_type,
        "severity": severity,
    }
    if data:
        context["alert_data"] = data

    log_method = getattr(logger, severity, logger.warning)
    log_method(f"ALERT [{alert_type}]: {message}", extra={"context": context})


# Auto-configure from environment
def configure_from_env() -> None:
    """Configure logging from environment variables."""
    level = os.environ.get("KORA_LOG_LEVEL", "INFO")
    json_output = os.environ.get("KORA_LOG_FORMAT", "").lower() == "json"
    log_file = os.environ.get("KORA_LOG_FILE")

    context = {}
    if os.environ.get("KORA_SITE_ID"):
        context["site_id"] = os.environ["KORA_SITE_ID"]
    if os.environ.get("KORA_ENV"):
        context["environment"] = os.environ["KORA_ENV"]

    setup_logging(
        level=level,
        json_output=json_output,
        log_file=log_file,
        context=context if context else None,
    )
