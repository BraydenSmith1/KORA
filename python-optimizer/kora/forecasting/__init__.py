"""
KORA Forecasting Module

Provides AI/ML forecasting capabilities for microgrid optimization:
- Solar PV production forecasts (weather-based)
- Demand forecasts (pattern-based with price elasticity)
- Battery SoC projections
- Outage risk assessment
"""

from .base import ForecastResult, BaseForecaster
from .weather import OpenMeteoClient, WeatherData
from .solar import PVForecaster
from .demand import DemandForecaster
from .battery import SoCProjector, SoCProjection
from .risk import OutageRiskCalculator, RiskAssessment
from .service import ForecastService

__all__ = [
    "ForecastResult",
    "BaseForecaster",
    "OpenMeteoClient",
    "WeatherData",
    "PVForecaster",
    "DemandForecaster",
    "SoCProjector",
    "SoCProjection",
    "OutageRiskCalculator",
    "RiskAssessment",
    "ForecastService",
]
