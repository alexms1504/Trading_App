"""
Market Data Controller
Handles market data fetching and processing
"""

from typing import Optional, Dict, Callable
from PyQt6.QtCore import pyqtSignal, QObject

from .base_controller import BaseController
from src.services import get_data_service
from src.services.event_bus import EventType, Event, subscribe, unsubscribe
from src.utils.logger import logger
import config


class MarketDataController(BaseController):
    """Controller for market data operations"""
    
    # Market data signals
    price_data_received = pyqtSignal(dict)
    price_fetch_started = pyqtSignal(str)
    price_fetch_completed = pyqtSignal()
    price_fetch_failed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._price_update_callbacks = []
        self._market_error_callbacks = []
        
    def initialize(self) -> bool:
        """Initialize the controller"""
        if not super().initialize():
            return False
            
        try:
            # Subscribe to market data events
            subscribe(EventType.PRICE_UPDATE, self._on_price_update_event)
            subscribe(EventType.MARKET_DATA_ERROR, self._on_market_error_event)
            
            logger.info("MarketDataController initialized and subscribed to events")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize MarketDataController: {str(e)}")
            return False
            
    def cleanup(self):
        """Cleanup controller resources"""
        try:
            # Unsubscribe from events
            unsubscribe(EventType.PRICE_UPDATE, self._on_price_update_event)
            unsubscribe(EventType.MARKET_DATA_ERROR, self._on_market_error_event)
            
            # Clear callbacks
            self._price_update_callbacks.clear()
            self._market_error_callbacks.clear()
            
            super().cleanup()
            
        except Exception as e:
            logger.error(f"Error cleaning up MarketDataController: {str(e)}")
            
    def fetch_price_data(self, symbol: str, direction: str = 'BUY'):
        """
        Fetch price data for a symbol
        
        Args:
            symbol: Stock symbol
            direction: Trade direction for stop loss calculations
        """
        data_service = get_data_service()
        
        if not data_service:
            error_msg = "Data service not available"
            self.show_error(error_msg)
            self.price_fetch_failed.emit(error_msg)
            return
            
        try:
            logger.info(f"Requesting price data for {symbol} via DataService")
            
            # Emit start signal
            self.price_fetch_started.emit(symbol)
            self.update_status(f"Fetching real-time data for {symbol}...")
            
            # Request price data from service
            data_service.fetch_price_data(symbol, direction)
            
        except Exception as e:
            error_msg = f"Error requesting price data: {str(e)}"
            logger.error(error_msg)
            self.show_error(error_msg)
            self.price_fetch_failed.emit(error_msg)
            
    def add_price_update_callback(self, callback: Callable[[dict], None]):
        """Add callback for price updates"""
        if callback not in self._price_update_callbacks:
            self._price_update_callbacks.append(callback)
            
    def remove_price_update_callback(self, callback: Callable[[dict], None]):
        """Remove price update callback"""
        if callback in self._price_update_callbacks:
            self._price_update_callbacks.remove(callback)
            
    def add_market_error_callback(self, callback: Callable[[str], None]):
        """Add callback for market errors"""
        if callback not in self._market_error_callbacks:
            self._market_error_callbacks.append(callback)
            
    def remove_market_error_callback(self, callback: Callable[[str], None]):
        """Remove market error callback"""
        if callback in self._market_error_callbacks:
            self._market_error_callbacks.remove(callback)
            
    def _on_price_update_event(self, event: Event):
        """Handle price update event from EventBus"""
        try:
            price_data = event.data
            symbol = price_data.get('symbol', 'Unknown')
            current_price = price_data.get('current_price', 0)
            
            logger.info(f"MarketDataController received price update for {symbol}: ${current_price:.2f}")
            
            # Emit signal
            self.price_data_received.emit(price_data)
            self.price_fetch_completed.emit()
            
            # Update status
            self.update_status(f"Real price data fetched for {symbol}: ${current_price:.2f}", 5000)
            
            # Notify callbacks
            for callback in self._price_update_callbacks:
                try:
                    callback(price_data)
                except Exception as e:
                    logger.error(f"Error in price update callback: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error handling price update event: {str(e)}")
            
    def _on_market_error_event(self, event: Event):
        """Handle market data error event from EventBus"""
        try:
            error_msg = event.data.get('error_message', 'Unknown market data error')
            
            logger.error(f"MarketDataController received error: {error_msg}")
            
            # Show error
            self.show_error(error_msg)
            
            # Emit signal
            self.price_fetch_failed.emit(error_msg)
            
            # Notify callbacks
            for callback in self._market_error_callbacks:
                try:
                    callback(error_msg)
                except Exception as e:
                    logger.error(f"Error in market error callback: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error handling market error event: {str(e)}")
            
    def process_price_data_for_ui(self, price_data: dict) -> dict:
        """
        Process price data for UI display
        
        Returns:
            Processed data ready for UI
        """
        try:
            return {
                'symbol': price_data.get('symbol', ''),
                'entry_price': price_data.get('entry_price', 0),
                'stop_loss': price_data.get('stop_loss', 0),
                'take_profit': price_data.get('take_profit', 0),
                'current_price': price_data.get('current_price', 0),
                'bid': price_data.get('bid', 0),
                'ask': price_data.get('ask', 0),
                'last': price_data.get('last', price_data.get('current_price', 0)),
                'stop_levels': price_data.get('stop_levels', {})
            }
        except Exception as e:
            logger.error(f"Error processing price data for UI: {str(e)}")
            return {}