"""
Customer demand forecaster.

Uses pattern-based model with:
- Time-of-day patterns (morning, evening peaks)
- Day-of-week effects (weekend vs weekday)
- Price elasticity (demand response to pricing)

Patterns are based on typical Madagascar microgrid consumption.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Optional, TYPE_CHECKING

import numpy as np

from .base import BaseForecaster, ForecastResult

if TYPE_CHECKING:
    from ..config import SiteConfig

logger = logging.getLogger(__name__)


class DemandForecaster(BaseForecaster):
    """
    Customer demand forecaster.

    Uses pattern-based approach combining:
    - Historical demand patterns (time-of-day)
    - Day-of-week effects
    - Price elasticity for demand response
    - Customer segment mix (households, SMEs, public)

    Usage:
        forecaster = DemandForecaster(
            peak_load_kw=53,
            base_load_kw=8,
            elasticity=0.6
        )
        result = forecaster.forecast(hours=24)
        print(result.values)  # [8.2, 7.5, 6.3, 5.1, 7.8, ...]
    """

    # Hourly demand pattern (fraction of peak)
    # Based on typical Madagascar microgrid with evening peak
    HOURLY_PATTERN = {
        0: 0.20,   # Midnight - low (some lights, refrigeration)
        1: 0.15,   # 1am
        2: 0.15,   # 2am
        3: 0.15,   # 3am
        4: 0.15,   # 4am
        5: 0.20,   # 5am - early risers
        6: 0.35,   # 6am - morning activity starts
        7: 0.45,   # 7am - breakfast, SMEs opening
        8: 0.50,   # 8am - business hours
        9: 0.48,   # 9am
        10: 0.45,  # 10am - solar surplus window
        11: 0.50,  # 11am - lunch prep
        12: 0.40,  # 12pm - midday lull
        13: 0.38,  # 1pm
        14: 0.45,  # 2pm
        15: 0.50,  # 3pm - afternoon activity
        16: 0.60,  # 4pm - shops busy
        17: 0.75,  # 5pm - evening cooking starts
        18: 0.95,  # 6pm - peak lighting + cooking
        19: 1.00,  # 7pm - PEAK (lighting, TV, cooking)
        20: 0.90,  # 8pm - still high
        21: 0.70,  # 9pm - winding down
        22: 0.50,  # 10pm
        23: 0.30,  # 11pm
    }

    # Weekend factor (fraction of weekday demand)
    WEEKEND_FACTOR = 0.85

    def __init__(
        self,
        peak_load_kw: float = 53.0,
        base_load_kw: float = 8.0,
        elasticity: float = 0.6,
        customer_count: int = 251,
        site_id: str = "default",
    ):
        """
        Initialize demand forecaster.

        Args:
            peak_load_kw: Maximum demand (at hour 19)
            base_load_kw: Minimum baseload (overnight)
            elasticity: Price elasticity of demand (0.6 = 10% price increase -> 6% demand decrease)
            customer_count: Number of customers (for future per-capita modeling)
            site_id: Site identifier for results
        """
        self.peak_load_kw = peak_load_kw
        self.base_load_kw = base_load_kw
        self.elasticity = elasticity
        self.customer_count = customer_count
        self.site_id = site_id

    @classmethod
    def from_config(cls, config: "SiteConfig") -> "DemandForecaster":
        """Create forecaster from site configuration."""
        return cls(
            peak_load_kw=config.demand.peak_load_kw,
            base_load_kw=config.demand.base_load_kw,
            elasticity=config.demand.elasticity,
            site_id=config.site_id,
        )

    def forecast(
        self,
        hours: int = 24,
        start_time: Optional[datetime] = None,
        price_schedule: Optional[List[float]] = None,
        reference_price: float = 1750.0,
        add_noise: bool = True,
    ) -> ForecastResult:
        """
        Generate demand forecast.

        Args:
            hours: Forecast horizon (1-48 hours)
            start_time: Starting datetime (default: now)
            price_schedule: If provided, apply price elasticity
            reference_price: Baseline price for elasticity calculation (Ariary/kWh)
            add_noise: Add random variation (±5%)

        Returns:
            ForecastResult with hourly kW values
        """
        hours = min(48, max(1, hours))
        start_time = start_time or datetime.now()

        demand_kw = []

        for h in range(hours):
            current_time = start_time + timedelta(hours=h)
            hour = current_time.hour
            day_of_week = current_time.weekday()

            # Base demand from hourly pattern
            pattern_value = self.HOURLY_PATTERN.get(hour, 0.3)
            base_demand = self.base_load_kw + (self.peak_load_kw - self.base_load_kw) * pattern_value

            # Weekend adjustment (Saturday=5, Sunday=6)
            if day_of_week >= 5:
                base_demand *= self.WEEKEND_FACTOR

            # Price elasticity adjustment
            if price_schedule is not None and h < len(price_schedule):
                price = price_schedule[h]
                # Elasticity formula: demand_change = -elasticity × price_change
                # If price goes up 10%, demand goes down by (elasticity × 10)%
                price_change_pct = (price - reference_price) / reference_price
                elasticity_factor = 1.0 - self.elasticity * price_change_pct
                # Clamp to reasonable range (demand can't go below 50% or above 200%)
                elasticity_factor = max(0.5, min(2.0, elasticity_factor))
                base_demand *= elasticity_factor

            # Add random noise (±5%)
            if add_noise:
                noise = np.random.uniform(0.95, 1.05)
                base_demand *= noise

            # Ensure minimum baseload
            final_demand = max(self.base_load_kw, base_demand)
            demand_kw.append(round(final_demand, 2))

        return ForecastResult(
            site_id=self.site_id,
            forecast_time=datetime.utcnow(),
            horizon_hours=hours,
            values=demand_kw,
            method="pattern_v1",
            units="kW",
            metadata={
                "peak_load_kw": self.peak_load_kw,
                "base_load_kw": self.base_load_kw,
                "elasticity": self.elasticity,
                "price_adjusted": price_schedule is not None,
                "customer_count": self.customer_count,
            }
        )

    def forecast_with_price_response(
        self,
        hours: int = 24,
        price_schedule: List[float] = None,
        reference_price: float = 1750.0,
    ) -> tuple[ForecastResult, ForecastResult]:
        """
        Generate both baseline and price-adjusted demand forecasts.

        Useful for comparing demand with/without dynamic pricing.

        Args:
            hours: Forecast horizon
            price_schedule: Hourly prices
            reference_price: Baseline price

        Returns:
            Tuple of (baseline_forecast, adjusted_forecast)
        """
        baseline = self.forecast(hours=hours, price_schedule=None, add_noise=False)
        adjusted = self.forecast(
            hours=hours,
            price_schedule=price_schedule,
            reference_price=reference_price,
            add_noise=False
        )
        return baseline, adjusted

    def validate_inputs(self) -> List[str]:
        """Validate forecaster configuration."""
        errors = []
        if self.peak_load_kw <= 0:
            errors.append("Peak load must be positive")
        if self.base_load_kw < 0:
            errors.append("Base load cannot be negative")
        if self.base_load_kw > self.peak_load_kw:
            errors.append("Base load cannot exceed peak load")
        if not (0 <= self.elasticity <= 2):
            errors.append("Elasticity should be between 0 and 2")
        return errors

    def get_daily_energy_estimate(self, hours: int = 24) -> float:
        """
        Estimate total daily energy consumption.

        Args:
            hours: Hours to sum (default 24)

        Returns:
            Total energy in kWh
        """
        forecast = self.forecast(hours, add_noise=False)
        return sum(forecast.values)

    def get_peak_hours(self, threshold_pct: float = 0.8) -> List[int]:
        """
        Get hours when demand exceeds threshold percentage of peak.

        Args:
            threshold_pct: Threshold as fraction of peak (0.8 = 80%)

        Returns:
            List of hour indices (0-23)
        """
        return [
            hour for hour, pattern in self.HOURLY_PATTERN.items()
            if pattern >= threshold_pct
        ]

    def get_surplus_hours(self, threshold_pct: float = 0.5) -> List[int]:
        """
        Get hours when demand is low (potential solar surplus).

        Args:
            threshold_pct: Threshold as fraction of peak (0.5 = below 50%)

        Returns:
            List of hour indices (0-23)
        """
        return [
            hour for hour, pattern in self.HOURLY_PATTERN.items()
            if pattern < threshold_pct
        ]
