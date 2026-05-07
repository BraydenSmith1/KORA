"""
Forecast Service - Main interface for KORA forecasting.

Coordinates all forecasters and provides a unified API for:
- Solar PV forecasts
- Demand forecasts
- Battery SoC projections
- Outage risk assessment

Usage:
    from kora.forecasting import ForecastService
    from kora.config import load_config

    config = load_config("mahavelona.yaml")
    service = ForecastService.from_config(config, latitude=-18.9, longitude=47.5)

    # Get forecasts
    pv = service.get_pv_forecast(hours=24)
    demand = service.get_demand_forecast(hours=24)
    risk = service.get_risk_assessment(initial_soc_kwh=50)

    # Get provider functions for optimizer
    pv_provider, demand_provider = service.get_forecast_providers()
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable, List, Optional, Tuple, TYPE_CHECKING

from .base import ForecastResult
from .weather import OpenMeteoClient
from .solar import PVForecaster
from .demand import DemandForecaster
from .battery import SoCProjector, SoCProjection
from .risk import OutageRiskCalculator, RiskAssessment
from .cache import ForecastCache

if TYPE_CHECKING:
    from ..config import SiteConfig

logger = logging.getLogger(__name__)


class ForecastService:
    """
    Main forecast service for KORA.

    Provides a unified interface to all forecasting capabilities.
    Designed to integrate with KoraService via forecast providers.
    """

    def __init__(
        self,
        pv_forecaster: PVForecaster,
        demand_forecaster: DemandForecaster,
        soc_projector: SoCProjector,
        risk_calculator: OutageRiskCalculator,
        site_id: str = "default",
    ):
        """
        Initialize forecast service with components.

        Args:
            pv_forecaster: Solar PV forecaster
            demand_forecaster: Demand forecaster
            soc_projector: Battery SoC projector
            risk_calculator: Outage risk calculator
            site_id: Site identifier
        """
        self.pv_forecaster = pv_forecaster
        self.demand_forecaster = demand_forecaster
        self.soc_projector = soc_projector
        self.risk_calculator = risk_calculator
        self.site_id = site_id

        # Internal cache for forecast results
        self._forecast_cache = ForecastCache(default_ttl_sec=3600)
        self._last_pv_forecast: Optional[ForecastResult] = None
        self._last_demand_forecast: Optional[ForecastResult] = None

    @classmethod
    def from_config(
        cls,
        config: "SiteConfig",
        latitude: float = -18.9,
        longitude: float = 47.5,
    ) -> "ForecastService":
        """
        Create forecast service from site configuration.

        Args:
            config: Site configuration
            latitude: Site latitude for weather data
            longitude: Site longitude for weather data

        Returns:
            Configured ForecastService
        """
        # Create weather client (shared by PV forecaster)
        weather = OpenMeteoClient(latitude, longitude)

        # Create forecasters
        pv = PVForecaster(
            capacity_kwp=config.solar.capacity_kw,
            weather_client=weather,
            latitude=latitude,
            longitude=longitude,
            site_id=config.site_id,
        )

        demand = DemandForecaster(
            peak_load_kw=config.demand.peak_load_kw,
            base_load_kw=config.demand.base_load_kw,
            elasticity=config.demand.elasticity,
            site_id=config.site_id,
        )

        soc = SoCProjector(
            capacity_kwh=config.battery.capacity_kwh,
            power_kw=config.battery.power_kw,
            soc_min_pct=config.battery.soc_min_percent,
            soc_max_pct=config.battery.soc_max_percent,
            eta_charge=config.battery.efficiency_charge,
            eta_discharge=config.battery.efficiency_discharge,
            site_id=config.site_id,
        )

        risk = OutageRiskCalculator(
            battery_capacity_kwh=config.battery.capacity_kwh,
            battery_power_kw=config.battery.power_kw,
            peak_demand_kw=config.demand.peak_load_kw,
            site_id=config.site_id,
        )

        return cls(
            pv_forecaster=pv,
            demand_forecaster=demand,
            soc_projector=soc,
            risk_calculator=risk,
            site_id=config.site_id,
        )

    @classmethod
    def create_default(
        cls,
        latitude: float = -18.9,
        longitude: float = 47.5,
        site_id: str = "mahavelona",
    ) -> "ForecastService":
        """
        Create forecast service with Mahavelona defaults.

        Useful for quick testing without a config file.
        """
        weather = OpenMeteoClient(latitude, longitude)

        return cls(
            pv_forecaster=PVForecaster(
                capacity_kwp=118.5,
                weather_client=weather,
                latitude=latitude,
                longitude=longitude,
                site_id=site_id,
            ),
            demand_forecaster=DemandForecaster(
                peak_load_kw=53.0,
                base_load_kw=8.0,
                elasticity=0.6,
                site_id=site_id,
            ),
            soc_projector=SoCProjector(
                capacity_kwh=115.0,
                power_kw=54.0,
                soc_min_pct=20.0,
                soc_max_pct=95.0,
                site_id=site_id,
            ),
            risk_calculator=OutageRiskCalculator(
                battery_capacity_kwh=115.0,
                battery_power_kw=54.0,
                peak_demand_kw=53.0,
                site_id=site_id,
            ),
            site_id=site_id,
        )

    # =========================================================================
    # Main Forecast Methods
    # =========================================================================

    def get_pv_forecast(self, hours: int = 24, use_cache: bool = True) -> ForecastResult:
        """
        Get solar PV production forecast.

        Args:
            hours: Forecast horizon (1-48)
            use_cache: Use cached result if available

        Returns:
            ForecastResult with hourly PV values in kW
        """
        cache_key = f"pv_{self.site_id}_{hours}"

        if use_cache:
            cached = self._forecast_cache.get(cache_key)
            if cached:
                logger.debug("Using cached PV forecast")
                return cached

        result = self.pv_forecaster.forecast(hours)
        self._last_pv_forecast = result

        if use_cache:
            self._forecast_cache.set(cache_key, result)

        logger.info(f"Generated PV forecast: {sum(result.values):.1f} kWh over {hours}h")
        return result

    def get_demand_forecast(
        self,
        hours: int = 24,
        price_schedule: Optional[List[float]] = None,
        reference_price: float = 1750.0,
        use_cache: bool = True,
    ) -> ForecastResult:
        """
        Get demand forecast.

        Args:
            hours: Forecast horizon (1-48)
            price_schedule: Optional price schedule for elasticity
            reference_price: Reference price for elasticity calculation
            use_cache: Use cached result if available (ignored if price_schedule provided)

        Returns:
            ForecastResult with hourly demand values in kW
        """
        # Don't cache if price schedule is provided (dynamic)
        if price_schedule is not None:
            result = self.demand_forecaster.forecast(
                hours=hours,
                price_schedule=price_schedule,
                reference_price=reference_price,
            )
            self._last_demand_forecast = result
            return result

        cache_key = f"demand_{self.site_id}_{hours}"

        if use_cache:
            cached = self._forecast_cache.get(cache_key)
            if cached:
                logger.debug("Using cached demand forecast")
                return cached

        result = self.demand_forecaster.forecast(hours)
        self._last_demand_forecast = result

        if use_cache:
            self._forecast_cache.set(cache_key, result)

        logger.info(f"Generated demand forecast: {sum(result.values):.1f} kWh over {hours}h")
        return result

    def get_soc_projection(
        self,
        initial_soc_kwh: float,
        hours: int = 24,
        charge_schedule: Optional[List[float]] = None,
        discharge_schedule: Optional[List[float]] = None,
    ) -> SoCProjection:
        """
        Get battery SoC projection.

        Args:
            initial_soc_kwh: Current battery state
            hours: Projection horizon
            charge_schedule: Optional planned charge schedule
            discharge_schedule: Optional planned discharge schedule

        Returns:
            SoCProjection with hour-by-hour battery state
        """
        # Get forecasts (use cached if available)
        pv = self.get_pv_forecast(hours)
        demand = self.get_demand_forecast(hours)

        projection = self.soc_projector.project(
            initial_soc_kwh=initial_soc_kwh,
            pv_forecast=pv.values,
            demand_forecast=demand.values,
            charge_schedule=charge_schedule,
            discharge_schedule=discharge_schedule,
        )

        logger.info(
            f"SoC projection: {initial_soc_kwh:.1f} -> {projection.soc_kwh[-1]:.1f} kWh, "
            f"{len(projection.warnings)} warnings"
        )
        return projection

    def get_risk_assessment(
        self,
        initial_soc_kwh: float,
        hours: int = 24,
    ) -> RiskAssessment:
        """
        Get outage risk assessment.

        Args:
            initial_soc_kwh: Current battery state
            hours: Assessment horizon

        Returns:
            RiskAssessment with risk scores and recommendations
        """
        # Get forecasts and projection
        pv = self.get_pv_forecast(hours)
        demand = self.get_demand_forecast(hours)
        soc_projection = self.get_soc_projection(initial_soc_kwh, hours)

        risk = self.risk_calculator.assess(
            soc_projection=soc_projection,
            pv_forecast=pv.values,
            demand_forecast=demand.values,
        )

        logger.info(
            f"Risk assessment: {risk.alert_level} (overall={risk.overall_risk:.2f})"
        )
        return risk

    # =========================================================================
    # Optimizer Integration
    # =========================================================================

    def get_forecast_providers(self) -> Tuple[Callable[[], List[float]], Callable[[], List[float]]]:
        """
        Get forecast provider functions for KoraService integration.

        Returns:
            Tuple of (pv_provider, demand_provider) functions
            Each returns List[float] with 24 hourly kW values

        Usage:
            pv_provider, demand_provider = service.get_forecast_providers()
            kora_service.set_forecast_providers(pv_provider, demand_provider)
        """
        def pv_provider() -> List[float]:
            result = self.get_pv_forecast(hours=24)
            return result.values

        def demand_provider() -> List[float]:
            result = self.get_demand_forecast(hours=24)
            return result.values

        return pv_provider, demand_provider

    def get_pv_provider(self) -> Callable[[], List[float]]:
        """Get PV forecast provider function."""
        pv, _ = self.get_forecast_providers()
        return pv

    def get_demand_provider(self) -> Callable[[], List[float]]:
        """Get demand forecast provider function."""
        _, demand = self.get_forecast_providers()
        return demand

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def refresh_forecasts(self) -> None:
        """Force refresh all forecasts (invalidate cache)."""
        self._forecast_cache.clear()
        self._last_pv_forecast = None
        self._last_demand_forecast = None
        logger.info("Forecast cache cleared")

    def get_daily_summary(self, initial_soc_kwh: float) -> dict:
        """
        Get summary of next 24 hours.

        Args:
            initial_soc_kwh: Current battery state

        Returns:
            Dictionary with key metrics
        """
        pv = self.get_pv_forecast(24)
        demand = self.get_demand_forecast(24)
        risk = self.get_risk_assessment(initial_soc_kwh, 24)

        total_pv = sum(pv.values)
        total_demand = sum(demand.values)
        curtailment_potential = max(0, total_pv - total_demand)

        return {
            "site_id": self.site_id,
            "timestamp": datetime.utcnow().isoformat(),
            "pv_forecast_kwh": round(total_pv, 1),
            "demand_forecast_kwh": round(total_demand, 1),
            "surplus_kwh": round(curtailment_potential, 1),
            "peak_pv_kw": round(max(pv.values), 1),
            "peak_demand_kw": round(max(demand.values), 1),
            "risk_level": risk.alert_level,
            "risk_score": risk.overall_risk,
            "recommendations": risk.recommendations[:3],  # Top 3
        }

    def validate(self) -> List[str]:
        """Validate all forecaster configurations."""
        errors = []
        errors.extend(self.pv_forecaster.validate_inputs())
        errors.extend(self.demand_forecaster.validate_inputs())
        return errors
