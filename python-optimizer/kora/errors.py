"""
KORA Error Handling and Recovery

Provides robust error handling with:
- Custom exception hierarchy
- Retry logic with exponential backoff
- Circuit breaker pattern
- Fallback strategies
- Error reporting
"""

from __future__ import annotations

import functools
import time
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from .logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


# =============================================================================
# Exception Hierarchy
# =============================================================================

class KoraError(Exception):
    """Base exception for all Kora errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class ConfigurationError(KoraError):
    """Raised when configuration is invalid or missing."""
    pass


class ConnectionError(KoraError):
    """Raised when connection to external service fails."""
    pass


class ModbusError(ConnectionError):
    """Raised when Modbus communication fails."""
    pass


class ApiError(ConnectionError):
    """Raised when API communication fails."""
    pass


class SolverError(KoraError):
    """Raised when the optimization solver fails."""
    pass


class SolverTimeoutError(SolverError):
    """Raised when solver exceeds time limit."""
    pass


class SolverInfeasibleError(SolverError):
    """Raised when no feasible solution exists."""
    pass


class DataError(KoraError):
    """Raised when input data is invalid or missing."""
    pass


class TelemetryError(KoraError):
    """Raised when telemetry data is unavailable or corrupt."""
    pass


# =============================================================================
# Retry Logic
# =============================================================================

class RetryStrategy(Enum):
    """Retry backoff strategies."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay_sec: float = 1.0
    max_delay_sec: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_JITTER
    retryable_exceptions: tuple = (ConnectionError, TimeoutError, OSError)

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number (0-indexed)."""
        if self.strategy == RetryStrategy.FIXED:
            delay = self.initial_delay_sec
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.initial_delay_sec * (attempt + 1)
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.initial_delay_sec * (2 ** attempt)
        elif self.strategy == RetryStrategy.EXPONENTIAL_JITTER:
            base_delay = self.initial_delay_sec * (2 ** attempt)
            jitter = random.uniform(0, base_delay * 0.5)
            delay = base_delay + jitter
        else:
            delay = self.initial_delay_sec

        return min(delay, self.max_delay_sec)


def retry(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable:
    """
    Decorator that retries a function on failure.

    Args:
        config: Retry configuration
        on_retry: Optional callback called on each retry with (exception, attempt)

    Example:
        @retry(RetryConfig(max_attempts=3))
        def fetch_data():
            ...
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e

                    if attempt < config.max_attempts - 1:
                        delay = config.get_delay(attempt)
                        logger.warning(
                            f"Retry {attempt + 1}/{config.max_attempts} for {func.__name__} "
                            f"after {delay:.1f}s: {e}"
                        )

                        if on_retry:
                            on_retry(e, attempt)

                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {config.max_attempts} retries failed for {func.__name__}: {e}"
                        )

            raise last_exception

        return wrapper

    return decorator


# =============================================================================
# Circuit Breaker
# =============================================================================

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by failing fast when a service is unavailable.
    """
    name: str
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_sec: float = 60.0

    state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    failure_count: int = field(default=0, init=False)
    success_count: int = field(default=0, init=False)
    last_failure_time: Optional[datetime] = field(default=None, init=False)

    def can_execute(self) -> bool:
        """Check if the circuit allows execution."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout_sec:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info(f"Circuit {self.name} entering HALF_OPEN state")
                    return True
            return False

        # HALF_OPEN state allows limited requests
        return True

    def record_success(self) -> None:
        """Record a successful execution."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit {self.name} recovered, now CLOSED")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self, exception: Exception) -> None:
        """Record a failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit {self.name} reopened after failure in HALF_OPEN")
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    f"Circuit {self.name} opened after {self.failure_count} failures"
                )


class CircuitOpenError(KoraError):
    """Raised when circuit breaker is open."""
    pass


def with_circuit_breaker(
    circuit: CircuitBreaker,
) -> Callable:
    """
    Decorator that applies circuit breaker pattern.

    Example:
        modbus_circuit = CircuitBreaker("modbus", failure_threshold=5)

        @with_circuit_breaker(modbus_circuit)
        def read_modbus():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            if not circuit.can_execute():
                raise CircuitOpenError(
                    f"Circuit {circuit.name} is open, fast-failing",
                    {"circuit_name": circuit.name, "state": circuit.state.value}
                )

            try:
                result = func(*args, **kwargs)
                circuit.record_success()
                return result
            except Exception as e:
                circuit.record_failure(e)
                raise

        return wrapper

    return decorator


# =============================================================================
# Fallback Strategies
# =============================================================================

@dataclass
class FallbackResult:
    """Result wrapper that indicates if fallback was used."""
    value: Any
    used_fallback: bool = False
    fallback_reason: Optional[str] = None


def with_fallback(
    fallback_value: Any = None,
    fallback_func: Optional[Callable[..., Any]] = None,
    exceptions: tuple = (Exception,),
) -> Callable:
    """
    Decorator that provides a fallback value or function on failure.

    Args:
        fallback_value: Static value to return on failure
        fallback_func: Function to call on failure (receives original args)
        exceptions: Exception types to catch

    Example:
        @with_fallback(fallback_value=[])
        def get_forecast():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., FallbackResult]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> FallbackResult:
            try:
                result = func(*args, **kwargs)
                return FallbackResult(value=result, used_fallback=False)
            except exceptions as e:
                logger.warning(f"Using fallback for {func.__name__}: {e}")

                if fallback_func:
                    value = fallback_func(*args, **kwargs)
                else:
                    value = fallback_value

                return FallbackResult(
                    value=value,
                    used_fallback=True,
                    fallback_reason=str(e),
                )

        return wrapper

    return decorator


# =============================================================================
# Error Recovery Helpers
# =============================================================================

def safe_execute(
    func: Callable[..., T],
    *args,
    default: T = None,
    log_error: bool = True,
    **kwargs,
) -> T:
    """
    Execute a function safely, returning default on any error.

    Args:
        func: Function to execute
        *args: Positional arguments
        default: Value to return on error
        log_error: Whether to log errors
        **kwargs: Keyword arguments

    Returns:
        Function result or default value
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_error:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
        return default


def validate_data(
    data: Dict[str, Any],
    required_fields: List[str],
    validators: Optional[Dict[str, Callable[[Any], bool]]] = None,
) -> List[str]:
    """
    Validate data dictionary and return list of errors.

    Args:
        data: Data to validate
        required_fields: Fields that must be present
        validators: Dict of field -> validation function

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check required fields
    for field in required_fields:
        if field not in data or data[field] is None:
            errors.append(f"Missing required field: {field}")

    # Run custom validators
    if validators:
        for field, validator in validators.items():
            if field in data and data[field] is not None:
                try:
                    if not validator(data[field]):
                        errors.append(f"Validation failed for field: {field}")
                except Exception as e:
                    errors.append(f"Validation error for {field}: {e}")

    return errors


def sanitize_telemetry(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize telemetry data by replacing invalid values.

    - NaN → None
    - Inf → None
    - Negative power values → 0
    - Out-of-range SOC → clamp to [0, 100]
    """
    import math

    result = {}

    for key, value in data.items():
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                result[key] = None
                continue

        # Specific field handling
        if key.endswith("_kw") or key.endswith("_power"):
            if isinstance(value, (int, float)) and value < 0:
                result[key] = 0
            else:
                result[key] = value
        elif "soc" in key.lower():
            if isinstance(value, (int, float)):
                result[key] = max(0, min(100, value))
            else:
                result[key] = value
        else:
            result[key] = value

    return result


# =============================================================================
# Error Reporting
# =============================================================================

@dataclass
class ErrorReport:
    """Structured error report for alerting."""
    error_type: str
    message: str
    site_id: Optional[str] = None
    severity: str = "error"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "site_id": self.site_id,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "stack_trace": self.stack_trace,
        }

    def to_alert_message(self) -> str:
        """Format as human-readable alert message."""
        lines = [
            f"🚨 KORA Alert: {self.error_type}",
            f"Site: {self.site_id or 'Unknown'}",
            f"Time: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Message: {self.message}",
        ]
        if self.context:
            lines.append("Context:")
            for k, v in self.context.items():
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)


def create_error_report(
    exception: Exception,
    site_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> ErrorReport:
    """Create an error report from an exception."""
    import traceback

    # Determine severity
    if isinstance(exception, (SolverInfeasibleError, ConfigurationError)):
        severity = "critical"
    elif isinstance(exception, (SolverTimeoutError, ConnectionError)):
        severity = "warning"
    else:
        severity = "error"

    return ErrorReport(
        error_type=type(exception).__name__,
        message=str(exception),
        site_id=site_id,
        severity=severity,
        context=context or {},
        stack_trace=traceback.format_exc(),
    )
