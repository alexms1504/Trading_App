"""
Chart Data Manager
Handles data fetching and formatting for chart display
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from ib_async import BarData

from src.utils.logger import logger
from src.core.data_fetcher import data_fetcher


class ChartDataManager:
    """
    Manages chart data fetching and formatting for lightweight-charts
    Provides optimized data for different timeframes and symbols
    """
    
    # Chart timeframe mappings for IB API
    CHART_TIMEFRAMES = {
        '1m': '1 min',
        '3m': '3 mins', 
        '5m': '5 mins',
        '15m': '15 mins',
        '1h': '1 hour',
        '4h': '4 hours', 
        '1d': '1 day'
    }
    
    # Duration mappings for different timeframes
    CHART_DURATIONS = {
        '1 min': '1 D',    # 1 day of 1-min bars
        '3 mins': '1 D',   # 1 day of 3-min bars
        '5 mins': '2 D',   # 2 days of 5-min bars
        '15 mins': '5 D',  # 5 days of 15-min bars
        '1 hour': '1 M',   # 1 month of hourly bars
        '4 hours': '3 M',  # 3 months of 4-hour bars
        '1 day': '1 Y'     # 1 year of daily bars
    }
    
    def __init__(self):
        """Initialize chart data manager"""
        self.data_fetcher = data_fetcher
        self.current_symbol = None
        self.current_timeframe = '5m'
        self.cached_data = {}  # Simple cache for recent data
        
    def get_chart_data(self, symbol: str, timeframe: str = '5m', max_bars: int = 500) -> List[Dict[str, Any]]:
        """
        Get chart data in lightweight-charts format
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            timeframe: Chart timeframe ('1m', '3m', '5m', '15m', '1h', '4h', '1d')
            max_bars: Maximum number of bars for performance
            
        Returns:
            List of dictionaries in lightweight-charts format
        """
        try:
            if timeframe not in self.CHART_TIMEFRAMES:
                logger.error(f"Unsupported timeframe: {timeframe}")
                return []
                
            bar_size = self.CHART_TIMEFRAMES[timeframe]
            duration = self.CHART_DURATIONS[bar_size]
            
            logger.info(f"Fetching chart data for {symbol} ({timeframe} / {bar_size} / {duration})")
            
            # Check cache first
            cache_key = f"{symbol}_{timeframe}"
            if cache_key in self.cached_data:
                cached_time, cached_bars = self.cached_data[cache_key]
                # Use cache if less than 1 minute old
                if (datetime.now() - cached_time).seconds < 60:
                    logger.info(f"Using cached chart data for {symbol} {timeframe}")
                    return cached_bars
            
            # Fetch historical bars using our proven sync method
            bars = self._get_historical_bars_sync(symbol, duration, bar_size, max_bars)
            
            if bars:
                # Convert to lightweight-charts format
                chart_data = self._convert_to_chart_format(bars)
                
                # Cache the result
                self.cached_data[cache_key] = (datetime.now(), chart_data)
                
                logger.info(f"Successfully fetched {len(chart_data)} bars for {symbol} {timeframe}")
                return chart_data
            else:
                logger.warning(f"No chart data available for {symbol} {timeframe}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting chart data for {symbol} {timeframe}: {str(e)}")
            return []
            
    def _get_historical_bars_sync(self, symbol: str, duration: str, bar_size: str, max_bars: int) -> Optional[List[BarData]]:
        """
        Get historical bars using synchronous method (optimized for Qt)
        Reuses the proven sync approach from data_fetcher
        """
        try:
            if not self.data_fetcher.ib_manager.is_connected():
                logger.error("Not connected to IB for chart data")
                return None
                
            ib = self.data_fetcher.ib_manager.ib
            if not ib:
                logger.error("IB client not available for chart data")
                return None
                
            # Create contract (same as data_fetcher approach)
            from ib_async import Stock
            contract = Stock(symbol, 'SMART', 'USD')
            
            try:
                ib.qualifyContracts(contract)
            except Exception as e:
                logger.error(f"Error qualifying contract for {symbol}: {str(e)}")
                return None
            
            # Request historical data
            bars = ib.reqHistoricalData(
                contract,
                endDateTime='',  # Up to now
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow='TRADES',
                useRTH=True,  # Regular trading hours only
                formatDate=1,
                keepUpToDate=False
            )
            
            if bars:
                # Limit to requested number of bars for performance
                limited_bars = bars[-max_bars:] if len(bars) > max_bars else bars
                logger.info(f"Retrieved {len(limited_bars)} chart bars for {symbol}")
                return limited_bars
            else:
                logger.warning(f"No historical bars received for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching chart bars for {symbol}: {str(e)}")
            return None
            
    def _convert_to_chart_format(self, bars: List[BarData]) -> List[Dict[str, Any]]:
        """
        Convert IB BarData to lightweight-charts format
        
        Args:
            bars: List of IB BarData objects
            
        Returns:
            List of dictionaries with time, open, high, low, close, volume
        """
        chart_data = []
        
        for bar in bars:
            try:
                # Convert to lightweight-charts format
                chart_bar = {
                    'time': int(bar.date.timestamp()),  # Unix timestamp
                    'open': float(bar.open),
                    'high': float(bar.high),
                    'low': float(bar.low),
                    'close': float(bar.close),
                    'volume': int(bar.volume) if bar.volume else 0
                }
                chart_data.append(chart_bar)
                
            except Exception as e:
                logger.warning(f"Error converting bar data: {str(e)}")
                continue
                
        return chart_data
        
    def get_available_timeframes(self) -> List[str]:
        """Get list of available timeframes"""
        return list(self.CHART_TIMEFRAMES.keys())
        
    def clear_cache(self):
        """Clear cached chart data"""
        self.cached_data.clear()
        logger.info("Chart data cache cleared")
        
    def set_current_symbol(self, symbol: str):
        """Set current symbol for tracking"""
        if symbol != self.current_symbol:
            self.current_symbol = symbol
            logger.info(f"Chart symbol changed to: {symbol}")
            
    def set_current_timeframe(self, timeframe: str):
        """Set current timeframe for tracking"""
        if timeframe != self.current_timeframe and timeframe in self.CHART_TIMEFRAMES:
            self.current_timeframe = timeframe
            logger.info(f"Chart timeframe changed to: {timeframe}")


# Create singleton instance
chart_data_manager = ChartDataManager()