"""
KORA Result Cache

Caches optimization results to avoid redundant solves and enable fast lookups.

Features:
- File-based caching with TTL
- Input fingerprinting for cache keys
- Automatic cleanup of expired entries
- Memory-efficient design for embedded systems
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .logging import get_logger

logger = get_logger(__name__)


@dataclass
class CacheConfig:
    """Cache configuration."""
    cache_dir: Path
    ttl_hours: int = 24  # Cache entries expire after 24 hours
    max_entries: int = 100  # Maximum number of cached results
    enabled: bool = True


class ResultCache:
    """
    File-based cache for optimization results.

    Caches are keyed by a fingerprint of the inputs, allowing fast lookup
    for repeated optimizations with identical parameters.

    Usage:
        cache = ResultCache(CacheConfig(cache_dir=Path("./cache")))

        # Check cache before solving
        key = cache.compute_key(inputs_dict)
        cached = cache.get(key)
        if cached:
            return cached

        # Solve and cache result
        result = solve_optimization(inputs)
        cache.set(key, result)
    """

    def __init__(self, config: CacheConfig):
        self.config = config
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.config.cache_dir / "index.json"
        self._index: Dict[str, Dict[str, Any]] = self._load_index()

    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """Load cache index from disk."""
        if self._index_path.exists():
            try:
                with open(self._index_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load cache index: {e}")
        return {}

    def _save_index(self) -> None:
        """Save cache index to disk."""
        try:
            with open(self._index_path, "w") as f:
                json.dump(self._index, f)
        except IOError as e:
            logger.warning(f"Failed to save cache index: {e}")

    def _cache_path(self, key: str) -> Path:
        """Get file path for a cache entry."""
        return self.config.cache_dir / f"{key}.json"

    @staticmethod
    def compute_key(inputs: Dict[str, Any]) -> str:
        """
        Compute a cache key from optimization inputs.

        The key is a hash of the serialized inputs, ensuring that
        identical inputs always produce the same key.
        """
        # Sort keys for consistent ordering
        serialized = json.dumps(inputs, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a cached result.

        Returns None if:
        - Cache is disabled
        - Key not found
        - Entry has expired
        - Cache file is corrupted
        """
        if not self.config.enabled:
            return None

        if key not in self._index:
            logger.debug(f"Cache miss: key {key} not in index")
            return None

        entry = self._index[key]

        # Check TTL
        created_at = datetime.fromisoformat(entry["created_at"])
        expires_at = created_at + timedelta(hours=self.config.ttl_hours)
        if datetime.utcnow() > expires_at:
            logger.debug(f"Cache miss: key {key} expired")
            self._remove(key)
            return None

        # Load from file
        cache_path = self._cache_path(key)
        if not cache_path.exists():
            logger.debug(f"Cache miss: file not found for {key}")
            del self._index[key]
            self._save_index()
            return None

        try:
            with open(cache_path, "r") as f:
                result = json.load(f)
            logger.info(f"Cache hit: {key}")
            return result
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to read cache file {key}: {e}")
            self._remove(key)
            return None

    def set(self, key: str, result: Dict[str, Any]) -> None:
        """
        Store a result in the cache.

        Automatically enforces max_entries limit by removing oldest entries.
        """
        if not self.config.enabled:
            return

        # Enforce max entries
        while len(self._index) >= self.config.max_entries:
            oldest_key = min(
                self._index.keys(),
                key=lambda k: self._index[k]["created_at"]
            )
            self._remove(oldest_key)

        # Write cache file
        cache_path = self._cache_path(key)
        try:
            with open(cache_path, "w") as f:
                json.dump(result, f)
        except IOError as e:
            logger.warning(f"Failed to write cache file {key}: {e}")
            return

        # Update index
        self._index[key] = {
            "created_at": datetime.utcnow().isoformat(),
            "size_bytes": cache_path.stat().st_size,
        }
        self._save_index()

        logger.debug(f"Cached result: {key}")

    def _remove(self, key: str) -> None:
        """Remove a cache entry."""
        cache_path = self._cache_path(key)
        if cache_path.exists():
            try:
                cache_path.unlink()
            except IOError:
                pass

        if key in self._index:
            del self._index[key]
            self._save_index()

    def clear(self) -> None:
        """Clear all cached entries."""
        for key in list(self._index.keys()):
            self._remove(key)
        logger.info("Cache cleared")

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns the number of entries removed.
        """
        removed = 0
        cutoff = datetime.utcnow() - timedelta(hours=self.config.ttl_hours)

        for key in list(self._index.keys()):
            created_at = datetime.fromisoformat(self._index[key]["created_at"])
            if created_at < cutoff:
                self._remove(key)
                removed += 1

        if removed > 0:
            logger.info(f"Cleaned up {removed} expired cache entries")

        return removed

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_size = sum(
            entry.get("size_bytes", 0)
            for entry in self._index.values()
        )

        return {
            "enabled": self.config.enabled,
            "entries": len(self._index),
            "max_entries": self.config.max_entries,
            "total_size_bytes": total_size,
            "ttl_hours": self.config.ttl_hours,
            "cache_dir": str(self.config.cache_dir),
        }


# Singleton instance for convenience
_cache: Optional[ResultCache] = None


def get_cache() -> ResultCache:
    """Get the global cache instance."""
    global _cache
    if _cache is None:
        cache_dir = Path(os.environ.get("KORA_CACHE_DIR", "./cache"))
        _cache = ResultCache(CacheConfig(cache_dir=cache_dir))
    return _cache


def cached_solve(
    inputs: Dict[str, Any],
    solver_fn: callable,
) -> Dict[str, Any]:
    """
    Wrapper that caches optimization results.

    Usage:
        def solve_model(inputs):
            # ... expensive solve ...
            return result

        result = cached_solve(inputs_dict, solve_model)
    """
    cache = get_cache()

    key = cache.compute_key(inputs)
    cached_result = cache.get(key)

    if cached_result is not None:
        return cached_result

    # Solve and cache
    result = solver_fn(inputs)
    cache.set(key, result)

    return result
