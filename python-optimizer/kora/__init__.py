"""
KORA Optimizer - Production Package

This package provides production-ready microgrid optimization with:
- YAML-based site configuration
- Structured logging with JSON format
- Error handling with retry logic and circuit breakers
- Modbus telemetry collection
- Continuous service operation with health checks
"""

__version__ = "0.3.0"

# Configuration
from .config import (
    SiteConfig,
    BatteryConfig,
    SolarConfig,
    PricingConfig,
    DemandConfig,
    OptimizerConfig,
    load_config,
    ConfigValidationError,
)

# Logging
from .logging import (
    setup_logging,
    get_logger,
    log_optimizer_run,
    log_alert,
    configure_from_env,
)

# Error handling
from .errors import (
    KoraError,
    ConfigurationError,
    ConnectionError,
    ModbusError,
    ApiError,
    SolverError,
    SolverTimeoutError,
    SolverInfeasibleError,
    DataError,
    RetryConfig,
    retry,
    CircuitBreaker,
    with_circuit_breaker,
    with_fallback,
    safe_execute,
    sanitize_telemetry,
    create_error_report,
)

# Telemetry
from .telemetry import (
    ModbusCollector,
    ModbusRegister,
    TelemetryFrame,
    ApiPoster,
    TelemetryService,
)

# Service
from .service import (
    OptimizationResult,
    OptimizerRunner,
    KoraService,
)

# Caching
from .cache import (
    CacheConfig,
    ResultCache,
    get_cache,
    cached_solve,
)

# Forecasting
from .forecasting import (
    ForecastService,
    ForecastResult,
    PVForecaster,
    DemandForecaster,
    SoCProjector,
    SoCProjection,
    OutageRiskCalculator,
    RiskAssessment,
    OpenMeteoClient,
    WeatherData,
)

__all__ = [
    # Version
    "__version__",
    # Config
    "SiteConfig",
    "BatteryConfig",
    "SolarConfig",
    "PricingConfig",
    "DemandConfig",
    "OptimizerConfig",
    "load_config",
    "ConfigValidationError",
    # Logging
    "setup_logging",
    "get_logger",
    "log_optimizer_run",
    "log_alert",
    "configure_from_env",
    # Errors
    "KoraError",
    "ConfigurationError",
    "ConnectionError",
    "ModbusError",
    "ApiError",
    "SolverError",
    "SolverTimeoutError",
    "SolverInfeasibleError",
    "DataError",
    "RetryConfig",
    "retry",
    "CircuitBreaker",
    "with_circuit_breaker",
    "with_fallback",
    "safe_execute",
    "sanitize_telemetry",
    "create_error_report",
    # Telemetry
    "ModbusCollector",
    "ModbusRegister",
    "TelemetryFrame",
    "ApiPoster",
    "TelemetryService",
    # Service
    "OptimizationResult",
    "OptimizerRunner",
    "KoraService",
    # Cache
    "CacheConfig",
    "ResultCache",
    "get_cache",
    "cached_solve",
    # Forecasting
    "ForecastService",
    "ForecastResult",
    "PVForecaster",
    "DemandForecaster",
    "SoCProjector",
    "SoCProjection",
    "OutageRiskCalculator",
    "RiskAssessment",
    "OpenMeteoClient",
    "WeatherData",
]
