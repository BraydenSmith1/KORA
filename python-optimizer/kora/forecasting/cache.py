"""
In-memory TTL cache for forecast data.

Simpler than the file-based ResultCache - designed for API response caching.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class CacheEntry:
    """Single cache entry with expiration."""
    value: Any
    expires_at: float  # Unix timestamp


class ForecastCache:
    """
    Simple in-memory TTL cache for forecast data.

    Usage:
        cache = ForecastCache(default_ttl_sec=3600)  # 1 hour default

        # Check cache
        data = cache.get("weather_-18.9_47.5")
        if data is None:
            data = fetch_from_api()
            cache.set("weather_-18.9_47.5", data)
    """

    def __init__(self, default_ttl_sec: int = 3600):
        """
        Initialize cache.

        Args:
            default_ttl_sec: Default time-to-live in seconds (default: 1 hour)
        """
        self.default_ttl_sec = default_ttl_sec
        self._cache: Dict[str, CacheEntry] = {}

    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        entry = self._cache.get(key)
        if entry is None:
            return None

        if time.time() > entry.expires_at:
            # Expired - remove and return None
            del self._cache[key]
            return None

        return entry.value

    def set(self, key: str, value: Any, ttl_sec: Optional[int] = None) -> None:
        """
        Store value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl_sec: Time-to-live in seconds (uses default if not specified)
        """
        ttl = ttl_sec if ttl_sec is not None else self.default_ttl_sec
        self._cache[key] = CacheEntry(
            value=value,
            expires_at=time.time() + ttl
        )

    def invalidate(self, key: str) -> bool:
        """
        Remove entry from cache.

        Args:
            key: Cache key

        Returns:
            True if entry existed and was removed
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> int:
        """
        Clear all entries.

        Returns:
            Number of entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        return count

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        now = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if now > entry.expires_at
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = time.time()
        valid_count = sum(
            1 for entry in self._cache.values()
            if now <= entry.expires_at
        )
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_count,
            "expired_entries": len(self._cache) - valid_count,
            "default_ttl_sec": self.default_ttl_sec,
        }


# Global cache instance for weather data
_weather_cache: Optional[ForecastCache] = None


def get_weather_cache() -> ForecastCache:
    """Get global weather cache instance (1-hour TTL)."""
    global _weather_cache
    if _weather_cache is None:
        _weather_cache = ForecastCache(default_ttl_sec=3600)
    return _weather_cache
