"""
Data Manager
Central manager for all market data operations
"""

from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
import asyncio

from .price_processor import PriceProcessor
from .data_cache import DataCache
from src.services.unified_data_service import unified_data_service
from src.services.event_bus import EventType, Event, publish_event
from src.utils.logger import logger


class DataManager:
    """Manages market data fetching, processing, and distribution"""
    
    def __init__(self):
        self.price_processor = PriceProcessor()
        self.data_cache = DataCache()
        self.unified_service = unified_data_service
        self._subscribers: Dict[str, List[Callable]] = {}
        self._setup_service_connections()
        
    def _setup_service_connections(self):
        """Setup connections to unified data service"""
        # Connect to service signals
        self.unified_service.fetch_completed.connect(self._on_fetch_completed)
        self.unified_service.fetch_failed.connect(self._on_fetch_failed)
        logger.info("DataManager connected to UnifiedDataService")
        
    def fetch_price_data(self, symbol: str, direction: str = 'BUY') -> bool:
        """
        Fetch price data for a symbol
        
        Args:
            symbol: Stock symbol
            direction: Trade direction for stop loss calculations
            
        Returns:
            True if fetch was initiated
        """
        try:
            # Check cache first
            cached_data = self.data_cache.get_price_data(symbol)
            if cached_data:
                logger.info(f"Using cached data for {symbol}")
                self._process_and_publish(cached_data, direction)
                return True
                
            # Initiate fetch
            logger.info(f"Fetching fresh price data for {symbol}")
            self.unified_service.fetch_price_data(symbol, direction)
            return True
            
        except Exception as e:
            logger.error(f"Error fetching price data: {str(e)}")
            publish_event(Event(
                EventType.MARKET_DATA_ERROR,
                {'error_message': f"Failed to fetch data for {symbol}: {str(e)}"}
            ))
            return False
            
    def fetch_historical_data(self, symbol: str, duration: str = "1D", 
                            bar_size: str = "1 min") -> Optional[Dict]:
        """
        Fetch historical data for a symbol
        
        Args:
            symbol: Stock symbol
            duration: Duration string (e.g., "1D", "1W", "1M")
            bar_size: Bar size (e.g., "1 min", "5 mins", "1 hour")
            
        Returns:
            Historical data dictionary or None
        """
        try:
            # Check cache
            cache_key = f"{symbol}_{duration}_{bar_size}"
            cached_data = self.data_cache.get_historical_data(cache_key)
            if cached_data:
                return cached_data
                
            # TODO: Implement historical data fetching
            # For now, return None
            logger.warning(f"Historical data fetching not yet implemented for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {str(e)}")
            return None
            
    def subscribe_to_symbol(self, symbol: str, callback: Callable):
        """Subscribe to real-time updates for a symbol"""
        symbol = symbol.upper()
        if symbol not in self._subscribers:
            self._subscribers[symbol] = []
        if callback not in self._subscribers[symbol]:
            self._subscribers[symbol].append(callback)
            logger.info(f"Added subscriber for {symbol}")
            
    def unsubscribe_from_symbol(self, symbol: str, callback: Callable):
        """Unsubscribe from symbol updates"""
        symbol = symbol.upper()
        if symbol in self._subscribers and callback in self._subscribers[symbol]:
            self._subscribers[symbol].remove(callback)
            if not self._subscribers[symbol]:
                del self._subscribers[symbol]
            logger.info(f"Removed subscriber for {symbol}")
            
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price for a symbol"""
        cached_data = self.data_cache.get_price_data(symbol)
        if cached_data and 'current_price' in cached_data:
            return cached_data['current_price']
        return None
        
    def _on_fetch_completed(self, price_data: dict):
        """Handle completed price fetch"""
        try:
            symbol = price_data.get('symbol')
            direction = price_data.get('direction', 'BUY')
            
            logger.info(f"Received price data for {symbol}")
            
            # Cache the raw data
            self.data_cache.cache_price_data(symbol, price_data)
            
            # Process and publish
            self._process_and_publish(price_data, direction)
            
            # Notify subscribers
            self._notify_subscribers(symbol, price_data)
            
        except Exception as e:
            logger.error(f"Error handling fetch completion: {str(e)}")
            
    def _on_fetch_failed(self, error_msg: str):
        """Handle failed price fetch"""
        logger.error(f"Price fetch failed: {error_msg}")
        publish_event(Event(
            EventType.MARKET_DATA_ERROR,
            {'error_message': error_msg}
        ))
        
    def _process_and_publish(self, price_data: dict, direction: str):
        """Process price data and publish update event"""
        try:
            # Process the data
            processed_data = self.price_processor.process_price_data(price_data, direction)
            
            # Publish price update event
            publish_event(Event(
                EventType.PRICE_UPDATE,
                processed_data
            ))
            
            logger.info(f"Published price update for {processed_data.get('symbol')}")
            
        except Exception as e:
            logger.error(f"Error processing price data: {str(e)}")
            publish_event(Event(
                EventType.MARKET_DATA_ERROR,
                {'error_message': f"Failed to process price data: {str(e)}"}
            ))
            
    def _notify_subscribers(self, symbol: str, data: dict):
        """Notify all subscribers of symbol data update"""
        symbol = symbol.upper()
        if symbol in self._subscribers:
            for callback in self._subscribers[symbol]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in subscriber callback: {str(e)}")
                    
    def cleanup(self):
        """Cleanup resources"""
        try:
            # Clear cache
            self.data_cache.clear()
            
            # Clear subscribers
            self._subscribers.clear()
            
            logger.info("DataManager cleaned up")
            
        except Exception as e:
            logger.error(f"Error during DataManager cleanup: {str(e)}")