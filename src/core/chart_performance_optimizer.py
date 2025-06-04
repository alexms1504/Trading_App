"""
Chart Performance Optimizer
Optimizes chart rendering performance through various techniques
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np
from src.utils.logger import logger


class ChartCache:
    """Cache for chart calculations to avoid redundant processing"""
    
    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}
        
    def get_cache_key(self, symbol: str, timeframe: str, data_hash: str) -> str:
        """Generate cache key for chart data"""
        return f"{symbol}_{timeframe}_{data_hash}"
        
    def get_data_hash(self, data: List[Dict[str, Any]]) -> str:
        """Generate hash for data to detect changes"""
        if not data:
            return "empty"
        
        # Use first, middle, and last bars + length for quick hash
        try:
            first = data[0]
            middle = data[len(data) // 2] if len(data) > 1 else first
            last = data[-1]
            
            hash_str = f"{len(data)}_{first['time']}_{first['close']}_{middle['close']}_{last['time']}_{last['close']}"
            return str(hash(hash_str))
        except Exception:
            return str(datetime.now().timestamp())
    
    def get_cached_calculations(self, symbol: str, timeframe: str, data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Get cached technical indicator calculations"""
        data_hash = self.get_data_hash(data)
        cache_key = self.get_cache_key(symbol, timeframe, data_hash)
        
        if cache_key in self._cache:
            logger.info(f"Cache hit for chart calculations: {symbol} {timeframe}")
            return self._cache[cache_key].copy()
        
        return None
    
    def store_calculations(self, symbol: str, timeframe: str, data: List[Dict[str, Any]], calculations: Dict[str, Any]):
        """Store technical indicator calculations in cache"""
        data_hash = self.get_data_hash(data)
        cache_key = self.get_cache_key(symbol, timeframe, data_hash)
        
        # Remove oldest entries if cache is full
        if len(self._cache) >= self.max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[cache_key] = calculations.copy()
        logger.info(f"Cached chart calculations: {symbol} {timeframe}")
    
    def clear(self):
        """Clear all cached data"""
        self._cache.clear()
        logger.info("Chart cache cleared")


class ChartDataOptimizer:
    """Optimizes chart data for faster rendering"""
    
    @staticmethod
    def downsample_data(data: List[Dict[str, Any]], max_points: int = 500) -> List[Dict[str, Any]]:
        """Downsample data for better performance on large datasets"""
        if len(data) <= max_points:
            return data
        
        # Calculate step size
        step = len(data) // max_points
        if step <= 1:
            return data
        
        # Keep important points (first, last, and evenly spaced)
        downsampled = []
        
        # Always keep first and last
        downsampled.append(data[0])
        
        # Add evenly spaced points
        for i in range(step, len(data) - step, step):
            downsampled.append(data[i])
        
        # Always keep last
        if data[-1] not in downsampled:
            downsampled.append(data[-1])
        
        logger.info(f"Downsampled data from {len(data)} to {len(downsampled)} points")
        return downsampled
    
    @staticmethod
    def optimize_volume_data(volumes: np.ndarray) -> np.ndarray:
        """Optimize volume data for rendering"""
        # Normalize volume for better visual representation
        if len(volumes) == 0:
            return volumes
        
        max_vol = np.max(volumes)
        if max_vol > 0:
            # Scale volumes to reasonable range for rendering
            return volumes / max_vol * 100
        
        return volumes


class TechnicalIndicatorOptimizer:
    """Optimizes technical indicator calculations"""
    
    @staticmethod
    def calculate_ema_optimized(prices: np.ndarray, period: int) -> np.ndarray:
        """Optimized EMA calculation using vectorized operations"""
        if len(prices) < period:
            return np.full(len(prices), np.nan)
        
        alpha = 2.0 / (period + 1)
        
        # Use pandas-style calculation for better performance
        ema = np.zeros_like(prices, dtype=np.float64)
        ema[0] = prices[0]
        
        # Vectorized calculation for better performance
        for i in range(1, len(prices)):
            ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
        
        # Set initial values to NaN
        ema[:period-1] = np.nan
        return ema
    
    @staticmethod
    def calculate_sma_optimized(prices: np.ndarray, period: int) -> np.ndarray:
        """Optimized SMA calculation using rolling window"""
        if len(prices) < period:
            return np.full(len(prices), np.nan)
        
        sma = np.full(len(prices), np.nan, dtype=np.float64)
        
        # Use numpy's convolve for faster calculation
        valid_start = period - 1
        if valid_start < len(prices):
            convolved = np.convolve(prices, np.ones(period)/period, mode='valid')
            sma[valid_start:valid_start+len(convolved)] = convolved
        
        return sma
    
    @staticmethod
    def calculate_vwap_optimized(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray) -> np.ndarray:
        """Optimized VWAP calculation"""
        typical_prices = (highs + lows + closes) / 3
        pv = typical_prices * volumes
        
        # Use cumulative sums for efficiency
        cumulative_pv = np.cumsum(pv)
        cumulative_volume = np.cumsum(volumes)
        
        # Avoid division by zero
        vwap = np.where(cumulative_volume > 0, cumulative_pv / cumulative_volume, np.nan)
        
        return vwap


# Global instances
chart_cache = ChartCache(max_size=20)
chart_optimizer = ChartDataOptimizer()
indicator_optimizer = TechnicalIndicatorOptimizer()