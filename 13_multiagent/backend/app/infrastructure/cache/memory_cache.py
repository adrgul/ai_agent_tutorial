"""Simple in-memory cache with TTL support."""
import time
from typing import Any, Optional, Dict, Tuple
from app.core.config import config
from app.core.logging import get_logger

logger = get_logger(__name__)


class MemoryCache:
    """Simple in-memory cache with TTL and basic statistics."""
    
    def __init__(self, default_ttl: int = None):
        self.default_ttl = default_ttl or config.CACHE_TTL
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if exists and not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            self._misses += 1
            return None
        
        value, expiry = self._cache[key]
        
        if time.time() > expiry:
            # Expired, remove it
            del self._cache[key]
            self._misses += 1
            return None
        
        self._hits += 1
        logger.debug(f"Cache hit: {key}")
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if not provided)
        """
        ttl = ttl if ttl is not None else self.default_ttl
        expiry = time.time() + ttl
        self._cache[key] = (value, expiry)
        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "size": len(self._cache),
        }


# Global cache instances for different purposes
routing_cache = MemoryCache()
kb_cache = MemoryCache()
synthesis_cache = MemoryCache()
