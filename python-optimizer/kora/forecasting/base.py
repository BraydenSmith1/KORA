"""
Base classes and datastructures for KORA forecasting.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ForecastResult:
    """
    Standard forecast result format.

    All forecasters return this structure for consistency.
    """
    site_id: str
    forecast_time: datetime
    horizon_hours: int
    values: List[float]  # Hourly values (units depend on forecast type)
    method: str  # e.g., "physics_v1", "pattern_v1", "ml_v1"
    units: str = "kW"  # Unit of values
    confidence: Optional[float] = None  # 0-1 confidence score
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if len(self.values) != self.horizon_hours:
            raise ValueError(
                f"Values length ({len(self.values)}) must match horizon_hours ({self.horizon_hours})"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "site_id": self.site_id,
            "forecast_time": self.forecast_time.isoformat(),
            "horizon_hours": self.horizon_hours,
            "values": self.values,
            "method": self.method,
            "units": self.units,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


class BaseForecaster(ABC):
    """
    Abstract base class for all forecasters.

    Provides common interface and validation patterns.
    """

    @abstractmethod
    def forecast(self, hours: int = 24) -> ForecastResult:
        """
        Generate forecast for the next N hours.

        Args:
            hours: Forecast horizon (1-48 hours)

        Returns:
            ForecastResult with hourly values
        """
        pass

    @abstractmethod
    def validate_inputs(self) -> List[str]:
        """
        Validate forecaster configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        pass

    def get_provider_function(self):
        """
        Return a callable compatible with KoraService.set_forecast_providers().

        Returns:
            Callable[[], List[float]] - function returning hourly values
        """
        def provider() -> List[float]:
            result = self.forecast(hours=24)
            return result.values
        return provider
