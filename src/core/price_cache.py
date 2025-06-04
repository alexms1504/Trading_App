"""
Price Cache Manager
Caches recently fetched prices to reduce API calls and improve performance
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import OrderedDict
from src.utils.logger import logger


class PriceCache:
    """
    In-memory price cache with TTL (time-to-live)
    """
    
    def __init__(self, max_age_seconds: int = 60, max_size: int = 100):
        """
        Initialize price cache
        
        Args:
            max_age_seconds: Maximum age of cached prices in seconds
            max_size: Maximum number of cached items
        """
        self.max_age = timedelta(seconds=max_age_seconds)
        self.max_size = max_size
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        
    def get(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get cached price data for symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Cached price data or None if not found/expired
        """
        if symbol not in self._cache:
            return None
            
        cached_item = self._cache[symbol]
        timestamp = cached_item.get('timestamp')
        
        if not timestamp:
            return None
            
        # Check if cache entry is expired
        age = datetime.now() - timestamp
        if age > self.max_age:
            # Remove expired entry
            del self._cache[symbol]
            logger.info(f"Cache expired for {symbol} (age: {age.seconds}s)")
            return None
            
        # Move to end (most recently used)
        self._cache.move_to_end(symbol)
        
        logger.info(f"Cache hit for {symbol} (age: {age.seconds}s)")
        return cached_item.copy()
        
    def set(self, symbol: str, data: Dict[str, Any]):
        """
        Store price data in cache
        
        Args:
            symbol: Stock symbol
            data: Price data to cache
        """
        # Ensure we have a timestamp
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
            
        # Remove oldest items if cache is full
        if len(self._cache) >= self.max_size:
            # Remove least recently used item
            self._cache.popitem(last=False)
            
        # Store in cache
        self._cache[symbol] = data
        logger.info(f"Cached price for {symbol}")
        
    def get_batch(self, symbols: list) -> Dict[str, Dict[str, Any]]:
        """
        Get multiple cached prices at once
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dict of symbol -> price data (only for cached items)
        """
        result = {}
        for symbol in symbols:
            cached = self.get(symbol)
            if cached:
                result[symbol] = cached
        return result
        
    def set_batch(self, data: Dict[str, Dict[str, Any]]):
        """
        Store multiple prices in cache
        
        Args:
            data: Dict of symbol -> price data
        """
        for symbol, price_data in data.items():
            self.set(symbol, price_data)
            
    def clear(self):
        """Clear all cached data"""
        self._cache.clear()
        logger.info("Price cache cleared")
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dict with cache statistics
        """
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'max_age_seconds': self.max_age.seconds,
            'symbols': list(self._cache.keys())
        }
        

# Global price cache instance (1 minute TTL, 100 items max)
price_cache = PriceCache(max_age_seconds=60, max_size=100)

# Screener-specific cache with shorter TTL (30 seconds for rapid updates)
screener_price_cache = PriceCache(max_age_seconds=30, max_size=50)