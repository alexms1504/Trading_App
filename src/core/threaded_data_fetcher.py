"""
Threaded Data Fetcher
Multi-threaded market data fetching to prevent UI blocking during price and stop loss data retrieval
"""

from typing import Optional, Dict, Any
from PyQt6.QtCore import QThread, pyqtSignal, QObject, QRunnable, QThreadPool
from PyQt6.QtWidgets import QApplication

from src.utils.logger import logger
from src.core.data_fetcher import data_fetcher


class PriceFetchWorker(QRunnable):
    """Worker thread for fetching price and stop loss data"""
    
    def __init__(self, symbol: str, direction: str, callback_obj):
        super().__init__()
        self.symbol = symbol
        self.direction = direction
        self.callback_obj = callback_obj
        self.setAutoDelete(True)
        
    def run(self):
        """Execute the price fetching in background thread"""
        try:
            logger.info(f"Background thread fetching price data for {self.symbol}")
            
            # Create event loop for this thread since ib_async needs it
            import asyncio
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Fetch price and stop loss data (this is the slow operation)
                price_data = data_fetcher.get_price_and_stops(self.symbol, self.direction)
                
                if price_data:
                    # Emit success signal with data
                    logger.info(f"Price data fetched: {self.symbol} - Price: ${price_data.get('current_price', 'N/A')}")
                    logger.info(f"Price data keys: {list(price_data.keys())}")
                    self.callback_obj.price_data_ready.emit(price_data)
                    logger.info(f"Successfully fetched price data for {self.symbol} in background")
                else:
                    # Emit error signal
                    logger.error(f"No price data returned for {self.symbol}")
                    self.callback_obj.price_fetch_error.emit(f"Failed to fetch market data for {self.symbol}")
            finally:
                # Clean up the event loop
                loop.close()
                
        except Exception as e:
            error_msg = f"Error fetching price data for {self.symbol}: {str(e)}"
            logger.error(error_msg)
            self.callback_obj.price_fetch_error.emit(error_msg)


class PriceFetchCallback(QObject):
    """Callback object for price fetch signals"""
    price_data_ready = pyqtSignal(dict)
    price_fetch_error = pyqtSignal(str)


class ThreadedDataFetcher(QObject):
    """
    Multi-threaded data fetcher that prevents UI blocking
    Uses QThreadPool for efficient thread management
    """
    
    # Signals for communicating with UI thread
    fetch_started = pyqtSignal(str)  # symbol
    fetch_completed = pyqtSignal(dict)  # price_data
    fetch_failed = pyqtSignal(str)  # error_message
    
    def __init__(self):
        super().__init__()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(3)  # Limit to 3 concurrent price fetches
        self.callback_obj = PriceFetchCallback()
        
        # Connect callback signals
        self.callback_obj.price_data_ready.connect(self.on_price_data_ready)
        self.callback_obj.price_fetch_error.connect(self.on_price_fetch_error)
        
        logger.info(f"ThreadedDataFetcher initialized with max {self.thread_pool.maxThreadCount()} threads")
        
    def fetch_price_and_stops_async(self, symbol: str, direction: str = 'BUY'):
        """
        Fetch price and stop loss data asynchronously without blocking UI
        
        Args:
            symbol: Stock symbol to fetch
            direction: 'BUY' or 'SELL' for directional stop loss calculations
        """
        try:
            logger.info(f"Starting async price fetch for {symbol} ({direction})")
            
            # Emit started signal
            self.fetch_started.emit(symbol)
            
            # Create and submit worker to thread pool
            worker = PriceFetchWorker(symbol, direction, self.callback_obj)
            self.thread_pool.start(worker)
            
            logger.info(f"Submitted {symbol} price fetch to thread pool")
            
        except Exception as e:
            error_msg = f"Error starting async price fetch for {symbol}: {str(e)}"
            logger.error(error_msg)
            self.fetch_failed.emit(error_msg)
            
    def on_price_data_ready(self, price_data: dict):
        """Handle successful price data fetch"""
        try:
            symbol = price_data.get('symbol', 'UNKNOWN')
            current_price = price_data.get('current_price', 0)
            logger.info(f"Price data ready for {symbol}: ${current_price:.2f}")
            
            # Emit completion signal to UI thread
            self.fetch_completed.emit(price_data)
            
        except Exception as e:
            logger.error(f"Error processing price data: {str(e)}")
            self.fetch_failed.emit(f"Error processing price data: {str(e)}")
            
    def on_price_fetch_error(self, error_message: str):
        """Handle price fetch error"""
        logger.error(f"Price fetch error: {error_message}")
        self.fetch_failed.emit(error_message)
        
    def get_active_thread_count(self) -> int:
        """Get number of currently active threads"""
        return self.thread_pool.activeThreadCount()
        
    def wait_for_completion(self, timeout_ms: int = 5000) -> bool:
        """Wait for all threads to complete (for testing/shutdown)"""
        return self.thread_pool.waitForDone(timeout_ms)
        
    def cleanup(self):
        """Cleanup thread pool resources"""
        try:
            logger.info("Cleaning up ThreadedDataFetcher...")
            self.thread_pool.clear()  # Remove pending tasks
            self.thread_pool.waitForDone(3000)  # Wait up to 3 seconds for completion
            logger.info("ThreadedDataFetcher cleanup completed")
        except Exception as e:
            logger.error(f"Error during ThreadedDataFetcher cleanup: {str(e)}")


class MarketDataWorker(QRunnable):
    """Worker for fetching market data for screener symbols"""
    
    def __init__(self, symbols: list, callback_obj):
        super().__init__()
        self.symbols = symbols
        self.callback_obj = callback_obj
        self.setAutoDelete(True)
        
    def run(self):
        """Execute market data fetching for screener"""
        try:
            logger.info(f"Background thread fetching market data for {len(self.symbols)} symbols")
            
            # Create event loop for this thread since ib_async needs it
            import asyncio
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Import here to avoid circular dependencies
                from src.core.market_screener import market_screener
                
                # Fetch real market data (this is the slow operation)
                market_data = market_screener._fetch_current_prices(self.symbols)
                
                # Emit results
                self.callback_obj.market_data_ready.emit(market_data)
                logger.info(f"Successfully fetched market data for {len(market_data)} symbols")
            finally:
                # Clean up the event loop
                loop.close()
            
        except Exception as e:
            error_msg = f"Error fetching market data: {str(e)}"
            logger.error(error_msg)
            self.callback_obj.market_data_error.emit(error_msg)


class MarketDataCallback(QObject):
    """Callback object for market data fetch signals"""
    market_data_ready = pyqtSignal(dict)
    market_data_error = pyqtSignal(str)


class ThreadedMarketDataFetcher(QObject):
    """
    Threaded market data fetcher for screener real price updates
    """
    
    # Signals
    fetch_started = pyqtSignal(int)  # number of symbols
    fetch_completed = pyqtSignal(dict)  # market_data
    fetch_failed = pyqtSignal(str)  # error_message
    
    def __init__(self):
        super().__init__()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(2)  # Limit market data fetching
        self.callback_obj = MarketDataCallback()
        
        # Connect callback signals
        self.callback_obj.market_data_ready.connect(self.on_market_data_ready)
        self.callback_obj.market_data_error.connect(self.on_market_data_error)
        
        logger.info(f"ThreadedMarketDataFetcher initialized with max {self.thread_pool.maxThreadCount()} threads")
        
    def fetch_market_data_async(self, symbols: list):
        """
        Fetch market data for symbols asynchronously
        
        Args:
            symbols: List of symbols to fetch market data for
        """
        try:
            if not symbols:
                return
                
            logger.info(f"Starting async market data fetch for {len(symbols)} symbols")
            
            # Emit started signal
            self.fetch_started.emit(len(symbols))
            
            # Create and submit worker
            worker = MarketDataWorker(symbols, self.callback_obj)
            self.thread_pool.start(worker)
            
            logger.info(f"Submitted market data fetch to thread pool")
            
        except Exception as e:
            error_msg = f"Error starting async market data fetch: {str(e)}"
            logger.error(error_msg)
            self.fetch_failed.emit(error_msg)
            
    def on_market_data_ready(self, market_data: dict):
        """Handle successful market data fetch"""
        try:
            logger.info(f"Market data ready for {len(market_data)} symbols")
            self.fetch_completed.emit(market_data)
        except Exception as e:
            logger.error(f"Error processing market data: {str(e)}")
            self.fetch_failed.emit(f"Error processing market data: {str(e)}")
            
    def on_market_data_error(self, error_message: str):
        """Handle market data fetch error"""
        logger.error(f"Market data fetch error: {error_message}")
        self.fetch_failed.emit(error_message)
        
    def cleanup(self):
        """Cleanup thread pool resources"""
        try:
            logger.info("Cleaning up ThreadedMarketDataFetcher...")
            self.thread_pool.clear()
            self.thread_pool.waitForDone(3000)
            logger.info("ThreadedMarketDataFetcher cleanup completed")
        except Exception as e:
            logger.error(f"Error during ThreadedMarketDataFetcher cleanup: {str(e)}")


# Create singleton instances
threaded_data_fetcher = ThreadedDataFetcher()
threaded_market_data_fetcher = ThreadedMarketDataFetcher()