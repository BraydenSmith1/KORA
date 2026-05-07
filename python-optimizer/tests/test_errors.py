"""
Tests for KORA error handling and recovery.
"""

import pytest
import time
from unittest.mock import Mock, patch

from kora.errors import (
    KoraError,
    ConfigurationError,
    ConnectionError,
    SolverError,
    RetryConfig,
    RetryStrategy,
    retry,
    CircuitBreaker,
    CircuitState,
    CircuitOpenError,
    with_circuit_breaker,
    with_fallback,
    FallbackResult,
    safe_execute,
    validate_data,
    sanitize_telemetry,
    create_error_report,
)


class TestRetryDecorator:
    """Test retry functionality."""

    def test_succeeds_first_try(self):
        call_count = 0

        @retry(RetryConfig(max_attempts=3))
        def always_succeeds():
            nonlocal call_count
            call_count += 1
            return "success"

        result = always_succeeds()
        assert result == "success"
        assert call_count == 1

    def test_retries_on_failure(self):
        call_count = 0

        @retry(RetryConfig(max_attempts=3, initial_delay_sec=0.01))
        def fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"

        result = fails_twice()
        assert result == "success"
        assert call_count == 3

    def test_exhausts_retries(self):
        call_count = 0

        @retry(RetryConfig(max_attempts=3, initial_delay_sec=0.01))
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Connection failed")

        with pytest.raises(ConnectionError):
            always_fails()

        assert call_count == 3

    def test_exponential_backoff(self):
        config = RetryConfig(
            initial_delay_sec=1.0,
            max_delay_sec=60.0,
            strategy=RetryStrategy.EXPONENTIAL,
        )

        assert config.get_delay(0) == 1.0
        assert config.get_delay(1) == 2.0
        assert config.get_delay(2) == 4.0
        assert config.get_delay(3) == 8.0

    def test_max_delay_cap(self):
        config = RetryConfig(
            initial_delay_sec=1.0,
            max_delay_sec=5.0,
            strategy=RetryStrategy.EXPONENTIAL,
        )

        # Should cap at 5 seconds
        assert config.get_delay(10) == 5.0


class TestCircuitBreaker:
    """Test circuit breaker pattern."""

    def test_starts_closed(self):
        circuit = CircuitBreaker(name="test")
        assert circuit.state == CircuitState.CLOSED
        assert circuit.can_execute()

    def test_opens_after_failures(self):
        circuit = CircuitBreaker(name="test", failure_threshold=3)

        for i in range(3):
            circuit.record_failure(Exception("fail"))

        assert circuit.state == CircuitState.OPEN
        assert not circuit.can_execute()

    def test_success_resets_count(self):
        circuit = CircuitBreaker(name="test", failure_threshold=3)

        circuit.record_failure(Exception("fail"))
        circuit.record_failure(Exception("fail"))
        circuit.record_success()

        assert circuit.state == CircuitState.CLOSED
        assert circuit.failure_count == 0

    def test_half_open_after_timeout(self):
        circuit = CircuitBreaker(
            name="test",
            failure_threshold=2,
            timeout_sec=0.1,
        )

        circuit.record_failure(Exception("fail"))
        circuit.record_failure(Exception("fail"))
        assert circuit.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.15)
        assert circuit.can_execute()
        assert circuit.state == CircuitState.HALF_OPEN

    def test_closes_after_successes_in_half_open(self):
        circuit = CircuitBreaker(
            name="test",
            failure_threshold=2,
            success_threshold=2,
            timeout_sec=0.01,
        )

        # Open the circuit
        circuit.record_failure(Exception("fail"))
        circuit.record_failure(Exception("fail"))

        # Wait for half-open
        time.sleep(0.02)
        circuit.can_execute()

        # Successful calls in half-open
        circuit.record_success()
        circuit.record_success()

        assert circuit.state == CircuitState.CLOSED

    def test_decorator(self):
        circuit = CircuitBreaker(name="test", failure_threshold=2)

        @with_circuit_breaker(circuit)
        def flaky_function():
            raise Exception("fail")

        # First failures open the circuit
        with pytest.raises(Exception):
            flaky_function()
        with pytest.raises(Exception):
            flaky_function()

        # Circuit is now open
        with pytest.raises(CircuitOpenError):
            flaky_function()


class TestFallback:
    """Test fallback functionality."""

    def test_returns_result_on_success(self):
        @with_fallback(fallback_value="fallback")
        def succeeds():
            return "success"

        result = succeeds()
        assert result.value == "success"
        assert result.used_fallback is False

    def test_returns_fallback_on_failure(self):
        @with_fallback(fallback_value="fallback")
        def fails():
            raise Exception("fail")

        result = fails()
        assert result.value == "fallback"
        assert result.used_fallback is True
        assert "fail" in result.fallback_reason

    def test_fallback_function(self):
        def fallback_fn(*args, **kwargs):
            return "computed_fallback"

        @with_fallback(fallback_func=fallback_fn)
        def fails():
            raise Exception("fail")

        result = fails()
        assert result.value == "computed_fallback"
        assert result.used_fallback is True


class TestSafeExecute:
    """Test safe_execute helper."""

    def test_returns_result_on_success(self):
        result = safe_execute(lambda: 42)
        assert result == 42

    def test_returns_default_on_failure(self):
        result = safe_execute(lambda: 1 / 0, default=-1)
        assert result == -1

    def test_logs_error(self):
        with patch("kora.errors.logger") as mock_logger:
            safe_execute(lambda: 1 / 0, default=None, log_error=True)
            mock_logger.error.assert_called()


class TestDataValidation:
    """Test data validation helpers."""

    def test_validate_required_fields(self):
        data = {"a": 1, "b": 2}
        errors = validate_data(data, required_fields=["a", "b"])
        assert errors == []

    def test_missing_required_fields(self):
        data = {"a": 1}
        errors = validate_data(data, required_fields=["a", "b", "c"])
        assert len(errors) == 2
        assert any("b" in e for e in errors)
        assert any("c" in e for e in errors)

    def test_custom_validators(self):
        data = {"value": 10}
        validators = {"value": lambda v: v > 0}
        errors = validate_data(data, [], validators=validators)
        assert errors == []

    def test_failing_validator(self):
        data = {"value": -10}
        validators = {"value": lambda v: v > 0}
        errors = validate_data(data, [], validators=validators)
        assert len(errors) == 1


class TestSanitizeTelemetry:
    """Test telemetry sanitization."""

    def test_handles_nan(self):
        import math

        data = {"value": math.nan}
        result = sanitize_telemetry(data)
        assert result["value"] is None

    def test_handles_inf(self):
        import math

        data = {"value": math.inf}
        result = sanitize_telemetry(data)
        assert result["value"] is None

    def test_clamps_negative_power(self):
        data = {"solar_kw": -10}
        result = sanitize_telemetry(data)
        assert result["solar_kw"] == 0

    def test_clamps_soc(self):
        data = {"battery_soc": 150}
        result = sanitize_telemetry(data)
        assert result["battery_soc"] == 100

    def test_preserves_valid_values(self):
        data = {"voltage": 230, "frequency": 50}
        result = sanitize_telemetry(data)
        assert result["voltage"] == 230
        assert result["frequency"] == 50


class TestErrorReporting:
    """Test error reporting functionality."""

    def test_create_error_report(self):
        exception = SolverError("Solver failed")
        report = create_error_report(
            exception,
            site_id="test-site",
            context={"run_id": "abc123"},
        )

        assert report.error_type == "SolverError"
        assert report.message == "Solver failed"
        assert report.site_id == "test-site"
        assert report.context["run_id"] == "abc123"
        assert report.stack_trace is not None

    def test_error_report_to_dict(self):
        exception = ConfigurationError("Bad config")
        report = create_error_report(exception, site_id="test")
        data = report.to_dict()

        assert "error_type" in data
        assert "message" in data
        assert "timestamp" in data
        assert data["severity"] == "critical"  # ConfigurationError is critical

    def test_alert_message_format(self):
        exception = ConnectionError("Network error")
        report = create_error_report(exception, site_id="test-site")
        message = report.to_alert_message()

        assert "KORA Alert" in message
        assert "ConnectionError" in message
        assert "test-site" in message
