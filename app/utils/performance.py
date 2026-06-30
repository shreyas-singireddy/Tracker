"""Performance optimization utilities for FitOS.

Provides:
- @timed() decorator for performance logging
- Cache configuration for Streamlit rendering
- Utility functions
"""

import time
import functools
from app.core.logging import logger


def timed(threshold: float = 0.1):
    """Decorator that logs execution time of functions exceeding a threshold (in seconds).
    
    Usage:
        @timed(threshold=0.5)
        def slow_function():
            ...
    
    Args:
        threshold: Minimum seconds before a warning is logged (default: 0.1s)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            
            if elapsed > threshold:
                logger.warning(
                    f"PERF: {func.__module__}.{func.__qualname__} took {elapsed:.3f}s "
                    f"(threshold: {threshold}s)"
                )
            else:
                logger.debug(
                    f"PERF: {func.__module__}.{func.__qualname__} took {elapsed:.3f}s"
                )
            return result
        return wrapper
    return decorator


def batch_read(func):
    """Decorator that logs batch database reads for optimization analysis."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if isinstance(result, list) and len(result) > 10:
            logger.debug(
                f"BATCH: {func.__module__}.{func.__qualname__} returned {len(result)} rows"
            )
        return result
    return wrapper


class SimpleCache:
    """Simple in-memory cache with TTL for frequently accessed data.
    
    Used to cache analytics aggregations and dashboard data.
    NOT for caching critical transactional data.
    """
    
    def __init__(self, default_ttl: int = 60):
        self._cache = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str):
        """Retrieves cached value if not expired."""
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                return value
            del self._cache[key]
        return None
    
    def set(self, key: str, value, ttl: int = None):
        """Stores a value with TTL in seconds."""
        ttl = ttl or self.default_ttl
        self._cache[key] = (value, time.time() + ttl)
    
    def clear(self):
        """Clears all cached entries."""
        self._cache.clear()
    
    def invalidate(self, key: str):
        """Invalidates a specific cache entry."""
        self._cache.pop(key, None)


# Global cache instance for analytics
analytics_cache = SimpleCache(default_ttl=300)  # 5 minute TTL for analytics
dashboard_cache = SimpleCache(default_ttl=60)    # 1 minute TTL for dashboard data