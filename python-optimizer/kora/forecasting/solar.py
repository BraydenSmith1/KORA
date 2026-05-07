"""
Solar PV production forecaster.

Uses physics-based model (PVWatts-style) with weather data to predict
solar panel output. No training data required.

Model:
    P_ac = GHI × Panel_Area × Efficiency × Temp_Factor × Cloud_Factor × Inverter_Eff × Soiling
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from .base import BaseForecaster, ForecastResult
from .weather import OpenMeteoClient, WeatherData, FallbackWeatherProvider

if TYPE_CHECKING:
    from ..config import SiteConfig

logger = logging.getLogger(__name__)


class PVForecaster(BaseForecaster):
    """
    Solar PV production forecaster.

    Uses physics-based model combining:
    - GHI/DNI from weather forecast
    - Panel capacity and efficiency
    - Temperature derating
    - Cloud cover adjustment
    - System losses (inverter, soiling, wiring)

    Usage:
        weather = OpenMeteoClient(latitude=-18.9, longitude=47.5)
        forecaster = PVForecaster(
            capacity_kwp=118.5,
            weather_client=weather
        )
        result = forecaster.forecast(hours=24)
        print(result.values)  # [0, 0, 5.2, 45.1, 78.5, ...]
    """

    # System efficiency parameters (typical values)
    NOMINAL_EFFICIENCY = 0.18       # 18% panel efficiency
    TEMP_COEFFICIENT = -0.004       # -0.4%/°C above 25°C (crystalline silicon)
    INVERTER_EFFICIENCY = 0.96      # 96% inverter efficiency
    SOILING_FACTOR = 0.97           # 3% soiling loss (dust, dirt)
    WIRING_LOSS = 0.98              # 2% wiring/connection losses
    PANEL_AREA_PER_KWP = 5.5        # ~5.5 m² per kWp (typical)

    def __init__(
        self,
        capacity_kwp: float,
        weather_client: Optional[OpenMeteoClient] = None,
        latitude: float = -18.9,
        longitude: float = 47.5,
        site_id: str = "default",
        use_fallback: bool = True,
    ):
        """
        Initialize PV forecaster.

        Args:
            capacity_kwp: Solar array capacity in kilowatt-peak
            weather_client: Weather data provider (creates one if not provided)
            latitude: Site latitude (for creating weather client)
            longitude: Site longitude (for creating weather client)
            site_id: Site identifier for results
            use_fallback: Use fallback provider if API fails
        """
        self.capacity_kwp = capacity_kwp
        self.latitude = latitude
        self.longitude = longitude
        self.site_id = site_id
        self.use_fallback = use_fallback

        if weather_client is not None:
            self.weather = weather_client
        else:
            self.weather = OpenMeteoClient(latitude, longitude)

        self.fallback = FallbackWeatherProvider(latitude, longitude)

    @classmethod
    def from_config(cls, config: "SiteConfig", latitude: float = -18.9, longitude: float = 47.5) -> "PVForecaster":
        """Create forecaster from site configuration."""
        return cls(
            capacity_kwp=config.solar.capacity_kw,
            latitude=latitude,
            longitude=longitude,
            site_id=config.site_id,
        )

    def forecast(self, hours: int = 24) -> ForecastResult:
        """
        Generate PV production forecast.

        Args:
            hours: Forecast horizon (1-48 hours)

        Returns:
            ForecastResult with hourly kW values
        """
        hours = min(48, max(1, hours))

        # Get weather data
        try:
            weather_data = self.weather.get_forecast(hours)
            weather_source = "open-meteo"
        except Exception as e:
            logger.warning(f"Weather API failed, using fallback: {e}")
            if self.use_fallback:
                weather_data = self.fallback.get_forecast(hours)
                weather_source = "fallback"
            else:
                raise

        # Pad if we got fewer hours than requested
        while len(weather_data) < hours:
            weather_data.append(weather_data[-1] if weather_data else WeatherData(
                time=datetime.now(),
                ghi=0, dni=0, cloud_cover=50, temperature=25,
                humidity=50, wind_speed=2, precipitation=0
            ))

        # Calculate PV output for each hour
        pv_kw = []
        for w in weather_data[:hours]:
            output = self._calculate_pv_output(w)
            pv_kw.append(round(output, 2))

        return ForecastResult(
            site_id=self.site_id,
            forecast_time=datetime.utcnow(),
            horizon_hours=hours,
            values=pv_kw,
            method="physics_v1",
            units="kW",
            metadata={
                "capacity_kwp": self.capacity_kwp,
                "weather_source": weather_source,
                "latitude": self.latitude,
                "longitude": self.longitude,
            }
        )

    def _calculate_pv_output(self, weather: WeatherData) -> float:
        """
        Calculate PV output for a single hour.

        Uses simplified PVWatts-style calculation:
        1. Convert GHI to DC power based on panel area and efficiency
        2. Apply temperature derating
        3. Apply cloud cover adjustment (in addition to GHI effect)
        4. Apply system losses (inverter, soiling, wiring)
        5. Clamp to capacity

        Args:
            weather: Weather data for the hour

        Returns:
            Expected AC power output in kW
        """
        hour = weather.time.hour

        # No output at night (conservative: 5am-7pm in tropics)
        if hour < 5 or hour > 19:
            return 0.0

        # Zero GHI means no sun
        if weather.ghi <= 0:
            return 0.0

        # Calculate panel area
        panel_area_m2 = self.capacity_kwp * self.PANEL_AREA_PER_KWP

        # DC power from irradiance
        # GHI (W/m²) × Area (m²) × Efficiency = DC Power (W)
        p_dc_w = weather.ghi * panel_area_m2 * self.NOMINAL_EFFICIENCY
        p_dc_kw = p_dc_w / 1000

        # Temperature derating
        # Panels lose ~0.4% efficiency per °C above 25°C
        temp_factor = 1.0 + self.TEMP_COEFFICIENT * (weather.temperature - 25)
        temp_factor = max(0.7, min(1.1, temp_factor))  # Clamp to reasonable range

        # Cloud cover adjustment
        # GHI already accounts for some cloud effect, but add extra reduction
        # for diffuse light scattering that reduces panel efficiency
        cloud_factor = 1.0 - (weather.cloud_cover / 100) * 0.2  # Max 20% additional reduction

        # System losses
        system_efficiency = (
            self.INVERTER_EFFICIENCY *
            self.SOILING_FACTOR *
            self.WIRING_LOSS
        )

        # Final AC output
        p_ac = p_dc_kw * temp_factor * cloud_factor * system_efficiency

        # Clamp to inverter/capacity limit
        return min(max(0, p_ac), self.capacity_kwp)

    def validate_inputs(self) -> List[str]:
        """Validate forecaster configuration."""
        errors = []
        if self.capacity_kwp <= 0:
            errors.append("PV capacity must be positive")
        if not (-90 <= self.latitude <= 90):
            errors.append("Latitude must be between -90 and 90")
        if not (-180 <= self.longitude <= 180):
            errors.append("Longitude must be between -180 and 180")
        return errors

    def get_daily_energy_estimate(self, hours: int = 24) -> float:
        """
        Estimate total daily energy production.

        Args:
            hours: Hours to sum (default 24)

        Returns:
            Total energy in kWh
        """
        forecast = self.forecast(hours)
        return sum(forecast.values)  # Each hour value is in kW, so sum = kWh
