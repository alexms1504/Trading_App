"""
Technical Indicator Service
Service-based implementation of technical indicator calculations
Migrated from src/core/chart_performance_optimizer.py as part of architecture consolidation
"""

import numpy as np
from typing import Optional

from src.services.base_service import BaseService
from src.utils.logger import logger


class TechnicalIndicatorService(BaseService):
    """
    Service for optimized technical indicator calculations
    Provides vectorized operations for chart rendering performance
    """
    
    def __init__(self):
        super().__init__("TechnicalIndicatorService")
        
    def initialize(self) -> bool:
        """Initialize the service"""
        try:
            # Verify numpy is available
            np.array([1, 2, 3])
            logger.info("TechnicalIndicatorService initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize TechnicalIndicatorService: {str(e)}")
            return False
            
    def cleanup(self):
        """Cleanup service resources"""
        logger.info("TechnicalIndicatorService cleaned up")
        
    def calculate_ema_optimized(self, prices: np.ndarray, period: int) -> np.ndarray:
        """
        Calculate EMA using vectorized operations
        
        Args:
            prices: Array of price values
            period: EMA period
            
        Returns:
            Array of EMA values
        """
        try:
            if len(prices) < period:
                return np.full(len(prices), np.nan)
            
            alpha = 2.0 / (period + 1)
            ema = np.zeros_like(prices)
            ema[0] = prices[0]
            
            for i in range(1, len(prices)):
                ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
            
            return ema
            
        except Exception as e:
            logger.error(f"Error calculating EMA (period={period}): {str(e)}")
            return np.full(len(prices), np.nan)
    
    def calculate_sma_optimized(self, prices: np.ndarray, period: int) -> np.ndarray:
        """
        Calculate SMA using vectorized operations
        
        Args:
            prices: Array of price values
            period: SMA period
            
        Returns:
            Array of SMA values
        """
        try:
            if len(prices) < period:
                return np.full(len(prices), np.nan)
            
            sma = np.full(len(prices), np.nan)
            for i in range(period - 1, len(prices)):
                sma[i] = np.mean(prices[i - period + 1:i + 1])
            
            return sma
            
        except Exception as e:
            logger.error(f"Error calculating SMA (period={period}): {str(e)}")
            return np.full(len(prices), np.nan)
    
    def calculate_vwap_optimized(self, highs: np.ndarray, lows: np.ndarray, 
                               closes: np.ndarray, volumes: np.ndarray) -> np.ndarray:
        """
        Calculate VWAP using vectorized operations
        
        Args:
            highs: Array of high prices
            lows: Array of low prices
            closes: Array of close prices
            volumes: Array of volumes
            
        Returns:
            Array of VWAP values
        """
        try:
            if len(closes) == 0 or len(volumes) == 0:
                return np.array([])
            
            # Typical price: (high + low + close) / 3
            typical_prices = (highs + lows + closes) / 3
            
            # Price * Volume
            pv = typical_prices * volumes
            
            # Use cumulative sums for efficiency
            cumulative_pv = np.cumsum(pv)
            cumulative_volume = np.cumsum(volumes)
            
            # Avoid division by zero
            vwap = np.where(cumulative_volume > 0, cumulative_pv / cumulative_volume, np.nan)
            
            return vwap
            
        except Exception as e:
            logger.error(f"Error calculating VWAP: {str(e)}")
            return np.full(len(closes), np.nan)


# Legacy compatibility class for smooth migration
class TechnicalIndicatorOptimizer:
    """
    Legacy compatibility wrapper for TechnicalIndicatorService
    Maintains the original static method API while delegating to the service
    """
    
    def __init__(self):
        self._service = TechnicalIndicatorService()
        self._service.initialize()
    
    def calculate_ema_optimized(self, prices: np.ndarray, period: int) -> np.ndarray:
        return self._service.calculate_ema_optimized(prices, period)
        
    def calculate_sma_optimized(self, prices: np.ndarray, period: int) -> np.ndarray:
        return self._service.calculate_sma_optimized(prices, period)
        
    def calculate_vwap_optimized(self, highs: np.ndarray, lows: np.ndarray, 
                               closes: np.ndarray, volumes: np.ndarray) -> np.ndarray:
        return self._service.calculate_vwap_optimized(highs, lows, closes, volumes)
    
    # Static method compatibility (delegates to instance methods)
    @staticmethod
    def calculate_ema_optimized_static(prices: np.ndarray, period: int) -> np.ndarray:
        service = TechnicalIndicatorService()
        service.initialize()
        return service.calculate_ema_optimized(prices, period)
    
    @staticmethod  
    def calculate_sma_optimized_static(prices: np.ndarray, period: int) -> np.ndarray:
        service = TechnicalIndicatorService()
        service.initialize()
        return service.calculate_sma_optimized(prices, period)
    
    @staticmethod
    def calculate_vwap_optimized_static(highs: np.ndarray, lows: np.ndarray, 
                                      closes: np.ndarray, volumes: np.ndarray) -> np.ndarray:
        service = TechnicalIndicatorService()
        service.initialize()
        return service.calculate_vwap_optimized(highs, lows, closes, volumes)


# Global instance for compatibility
indicator_optimizer = TechnicalIndicatorOptimizer()


# Provide access to the service for dependency injection
def get_technical_indicator_service() -> TechnicalIndicatorService:
    """Get the technical indicator service instance"""
    service = TechnicalIndicatorService()
    service.initialize()
    return service