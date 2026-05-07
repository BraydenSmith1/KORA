"""
Weather data provider using Open-Meteo API.

Open-Meteo is a free, open-source weather API with:
- No API key required for basic usage
- Solar radiation data (GHI, DNI)
- 48-hour forecasts
- Historical data for validation

API Docs: https://open-meteo.com/en/docs
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import requests

from .cache import ForecastCache, get_weather_cache

logger = logging.getLogger(__name__)


@dataclass
class WeatherData:
    """Hourly weather data point."""
    time: datetime
    ghi: float           # Global Horizontal Irradiance (W/m²)
    dni: float           # Direct Normal Irradiance (W/m²)
    cloud_cover: float   # Cloud cover percentage (0-100)
    temperature: float   # Temperature (°C)
    humidity: float      # Relative humidity (0-100)
    wind_speed: float    # Wind speed (m/s)
    precipitation: float # Precipitation (mm)


class OpenMeteoClient:
    """
    Open-Meteo API client for weather forecasts.

    Fetches solar radiation and weather data for PV forecasting.

    Usage:
        client = OpenMeteoClient(latitude=-18.9, longitude=47.5)
        weather = client.get_forecast(hours=24)
        for w in weather:
            print(f"{w.time}: GHI={w.ghi} W/m², Cloud={w.cloud_cover}%")
    """

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(
        self,
        latitude: float,
        longitude: float,
        cache: Optional[ForecastCache] = None,
    ):
        """
        Initialize weather client.

        Args:
            latitude: Site latitude (e.g., -18.9 for Madagascar)
            longitude: Site longitude (e.g., 47.5 for Madagascar)
            cache: Optional cache instance (uses global cache if not provided)
        """
        self.latitude = latitude
        self.longitude = longitude
        self.cache = cache if cache is not None else get_weather_cache()

    def get_forecast(self, hours: int = 48) -> List[WeatherData]:
        """
        Fetch weather forecast from Open-Meteo.

        Args:
            hours: Forecast horizon (max 168 = 7 days)

        Returns:
            List of WeatherData for each hour

        Raises:
            requests.RequestException: If API request fails
        """
        cache_key = f"weather_{self.latitude}_{self.longitude}_{hours}"

        # Check cache first
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Weather cache hit for {cache_key}")
            return cached

        logger.info(f"Fetching weather from Open-Meteo for ({self.latitude}, {self.longitude})")

        # Build request parameters
        # Note: Open-Meteo uses 'shortwave_radiation' for GHI and 'direct_radiation' for direct component
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "hourly": ",".join([
                "shortwave_radiation",       # GHI (W/m²)
                "direct_radiation",          # Direct component (W/m²)
                "cloud_cover",               # %
                "temperature_2m",            # °C
                "relative_humidity_2m",      # %
                "wind_speed_10m",            # m/s
                "precipitation",             # mm
            ]),
            "forecast_days": min(7, (hours // 24) + 1),
            "timezone": "auto",
        }

        try:
            response = requests.get(
                self.BASE_URL,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error(f"Weather API request failed: {e}")
            raise

        # Parse response
        results = self._parse_response(data, hours)

        # Cache results (1 hour TTL)
        self.cache.set(cache_key, results, ttl_sec=3600)
        logger.info(f"Cached {len(results)} hours of weather data")

        return results

    def _parse_response(self, data: dict, hours: int) -> List[WeatherData]:
        """Parse Open-Meteo JSON response into WeatherData objects."""
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])[:hours]

        results = []
        for i, time_str in enumerate(times):
            try:
                results.append(WeatherData(
                    time=datetime.fromisoformat(time_str),
                    ghi=hourly.get("shortwave_radiation", [0])[i] or 0,
                    dni=hourly.get("direct_radiation", [0])[i] or 0,
                    cloud_cover=hourly.get("cloud_cover", [0])[i] or 0,
                    temperature=hourly.get("temperature_2m", [25])[i] or 25,
                    humidity=hourly.get("relative_humidity_2m", [50])[i] or 50,
                    wind_speed=hourly.get("wind_speed_10m", [0])[i] or 0,
                    precipitation=hourly.get("precipitation", [0])[i] or 0,
                ))
            except (IndexError, TypeError) as e:
                logger.warning(f"Failed to parse weather hour {i}: {e}")
                continue

        return results

    def get_current(self) -> Optional[WeatherData]:
        """
        Get current weather conditions.

        Returns:
            Current WeatherData or None if unavailable
        """
        forecast = self.get_forecast(hours=1)
        return forecast[0] if forecast else None


class FallbackWeatherProvider:
    """
    Fallback weather provider when API is unavailable.

    Uses synthetic data based on typical Madagascar patterns.
    """

    def __init__(self, latitude: float = -18.9, longitude: float = 47.5):
        self.latitude = latitude
        self.longitude = longitude

    def get_forecast(self, hours: int = 48) -> List[WeatherData]:
        """Generate synthetic weather data."""
        logger.warning("Using fallback weather provider (no real data)")

        now = datetime.now()
        results = []

        for h in range(hours):
            hour = (now.hour + h) % 24

            # Synthetic GHI curve (peaks at noon)
            if 5 <= hour <= 19:
                # Bell curve approximation
                noon_offset = abs(hour - 12)
                ghi = max(0, 1000 * (1 - (noon_offset / 7) ** 2))
                dni = ghi * 0.85  # Approximate DNI from GHI
            else:
                ghi = 0
                dni = 0

            results.append(WeatherData(
                time=datetime(now.year, now.month, now.day, hour),
                ghi=ghi,
                dni=dni,
                cloud_cover=30,  # Assume 30% average cloud cover
                temperature=25,  # Tropical average
                humidity=65,
                wind_speed=3,
                precipitation=0,
            ))

        return results
