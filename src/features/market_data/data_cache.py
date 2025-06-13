"""
Data Cache
Caches market data to reduce API calls
"""

from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import json

from src.utils.logger import logger


class CacheEntry:
    """Single cache entry with expiration"""
    
    def __init__(self, data: Any, ttl_seconds: int = 300):
        self.data = data
        self.timestamp = datetime.now()
        self.ttl = timedelta(seconds=ttl_seconds)
        
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return datetime.now() > self.timestamp + self.ttl
        
    def age_seconds(self) -> float:
        """Get age of cache entry in seconds"""
        return (datetime.now() - self.timestamp).total_seconds()
        

class DataCache:
    """Caches market data with TTL"""
    
    def __init__(self):
        self._price_cache: Dict[str, CacheEntry] = {}
        self._historical_cache: Dict[str, CacheEntry] = {}
        self._quote_cache: Dict[str, CacheEntry] = {}
        
        # Default TTLs
        self.price_ttl = 60  # 1 minute for price data
        self.historical_ttl = 300  # 5 minutes for historical data
        self.quote_ttl = 30  # 30 seconds for quotes
        
    def cache_price_data(self, symbol: str, data: dict):
        """Cache price data for a symbol"""
        symbol = symbol.upper()
        self._price_cache[symbol] = CacheEntry(data, self.price_ttl)
        logger.debug(f"Cached price data for {symbol}")
        
    def get_price_data(self, symbol: str) -> Optional[dict]:
        """Get cached price data if not expired"""
        symbol = symbol.upper()
        
        if symbol in self._price_cache:
            entry = self._price_cache[symbol]
            if not entry.is_expired():
                logger.debug(f"Cache hit for {symbol} (age: {entry.age_seconds():.1f}s)")
                return entry.data
            else:
                # Remove expired entry
                del self._price_cache[symbol]
                logger.debug(f"Cache expired for {symbol}")
                
        return None
        
    def cache_historical_data(self, key: str, data: dict):
        """Cache historical data"""
        self._historical_cache[key] = CacheEntry(data, self.historical_ttl)
        logger.debug(f"Cached historical data for {key}")
        
    def get_historical_data(self, key: str) -> Optional[dict]:
        """Get cached historical data if not expired"""
        if key in self._historical_cache:
            entry = self._historical_cache[key]
            if not entry.is_expired():
                logger.debug(f"Historical cache hit for {key}")
                return entry.data
            else:
                del self._historical_cache[key]
                
        return None
        
    def cache_quote(self, symbol: str, quote: dict):
        """Cache quote data"""
        symbol = symbol.upper()
        self._quote_cache[symbol] = CacheEntry(quote, self.quote_ttl)
        
    def get_quote(self, symbol: str) -> Optional[dict]:
        """Get cached quote if not expired"""
        symbol = symbol.upper()
        
        if symbol in self._quote_cache:
            entry = self._quote_cache[symbol]
            if not entry.is_expired():
                return entry.data
            else:
                del self._quote_cache[symbol]
                
        return None
        
    def invalidate_symbol(self, symbol: str):
        """Invalidate all caches for a symbol"""
        symbol = symbol.upper()
        
        if symbol in self._price_cache:
            del self._price_cache[symbol]
        if symbol in self._quote_cache:
            del self._quote_cache[symbol]
            
        # Also invalidate related historical entries
        keys_to_remove = [k for k in self._historical_cache if k.startswith(symbol)]
        for key in keys_to_remove:
            del self._historical_cache[key]
            
        logger.debug(f"Invalidated all caches for {symbol}")
        
    def clear(self):
        """Clear all caches"""
        self._price_cache.clear()
        self._historical_cache.clear()
        self._quote_cache.clear()
        logger.info("All caches cleared")
        
    def cleanup_expired(self):
        """Remove expired entries from all caches"""
        # Clean price cache
        expired = [s for s, e in self._price_cache.items() if e.is_expired()]
        for symbol in expired:
            del self._price_cache[symbol]
            
        # Clean historical cache
        expired = [k for k, e in self._historical_cache.items() if e.is_expired()]
        for key in expired:
            del self._historical_cache[key]
            
        # Clean quote cache
        expired = [s for s, e in self._quote_cache.items() if e.is_expired()]
        for symbol in expired:
            del self._quote_cache[symbol]
            
        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired cache entries")
            
    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        return {
            'price_cache_size': len(self._price_cache),
            'historical_cache_size': len(self._historical_cache),
            'quote_cache_size': len(self._quote_cache),
            'total_entries': len(self._price_cache) + len(self._historical_cache) + len(self._quote_cache)
        }