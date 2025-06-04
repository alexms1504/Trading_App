"""
Async Data Fetcher
True asynchronous data fetching using IB API's async methods for optimal performance
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool
from ib_async import Stock

from src.utils.logger import logger
from src.core.ib_connection import ib_connection_manager


class AsyncPriceWorker(QRunnable):
    """Worker for async price fetching in background thread"""
    
    class Signals(QObject):
        """Custom signals for the worker"""
        completed = pyqtSignal(dict)
        failed = pyqtSignal(str)
        progress = pyqtSignal(str)
    
    def __init__(self, symbol: str, direction: str = 'BUY'):
        super().__init__()
        self.symbol = symbol
        self.direction = direction
        self.signals = self.Signals()
        
    def run(self):
        """Run async price fetch in worker thread"""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the async fetch
            price_data = loop.run_until_complete(self._fetch_price_data_async())
            
            if price_data:
                self.signals.completed.emit(price_data)
            else:
                self.signals.failed.emit(f"Failed to fetch data for {self.symbol}")
                
        except Exception as e:
            error_msg = f"Error in async price fetch: {str(e)}"
            logger.error(error_msg)
            self.signals.failed.emit(error_msg)
            
    async def _fetch_price_data_async(self) -> Optional[Dict[str, Any]]:
        """Fetch price data using true async operations"""
        try:
            if not ib_connection_manager.is_connected():
                logger.error("Not connected to IB")
                return None
                
            ib = ib_connection_manager.ib
            if not ib:
                logger.error("IB client not available")
                return None
                
            # Create and qualify contract
            contract = Stock(self.symbol, 'SMART', 'USD')
            await ib.qualifyContractsAsync(contract)
            
            # Request market data
            ticker = ib.reqMktData(contract, '', False, False)
            
            # Wait for data with incremental checking
            total_wait = 0
            max_wait = 0.8  # Maximum 800ms
            increment = 0.1  # Check every 100ms
            
            while total_wait < max_wait:
                await asyncio.sleep(increment)
                total_wait += increment
                
                # Check if we have data
                if ticker.last or ticker.bid or ticker.ask or ticker.close:
                    break
                    
                self.signals.progress.emit(f"Waiting for data... {int(total_wait * 1000)}ms")
            
            # Extract price
            current_price = None
            if ticker.last and ticker.last > 0:
                current_price = ticker.last
            elif ticker.close and ticker.close > 0:
                current_price = ticker.close
            elif ticker.bid and ticker.ask and ticker.bid > 0 and ticker.ask > 0:
                current_price = (ticker.bid + ticker.ask) / 2
                
            # Cancel market data
            ib.cancelMktData(contract)
            
            if not current_price:
                logger.error(f"No valid price data for {self.symbol}")
                return None
                
            # Get historical data for stop loss levels
            stop_levels = await self._fetch_stop_levels_async(contract, current_price)
            
            # Prepare result
            result = {
                'symbol': self.symbol,
                'current_price': current_price,
                'price_data': {
                    'symbol': self.symbol,
                    'last': ticker.last,
                    'bid': ticker.bid,
                    'ask': ticker.ask,
                    'close': ticker.close,
                    'latest_price': current_price,
                    'timestamp': datetime.now()
                },
                'stop_levels': stop_levels,
                'direction': self.direction,
                'timestamp': datetime.now()
            }
            
            logger.info(f"Async fetch completed for {self.symbol}: ${current_price:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error in async price fetch: {str(e)}")
            return None
            
    async def _fetch_stop_levels_async(self, contract, current_price: float) -> Dict[str, float]:
        """Fetch stop loss levels using async operations"""
        try:
            ib = ib_connection_manager.ib
            stop_levels = {}
            
            # Fetch 5-minute bars
            bars_5min = await ib.reqHistoricalDataAsync(
                contract,
                endDateTime='',
                durationStr='1 D',
                barSizeSetting='5 mins',
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1
            )
            
            if bars_5min and len(bars_5min) >= 2:
                prior_bar = bars_5min[-2]
                current_bar = bars_5min[-1]
                stop_levels['prior_5min_low'] = prior_bar.low
                stop_levels['current_5min_low'] = current_bar.low
                
                # Lowest of recent bars
                recent_bars = bars_5min[-5:]
                stop_levels['recent_5min_low'] = min(bar.low for bar in recent_bars)
            
            # Fetch daily bars
            bars_daily = await ib.reqHistoricalDataAsync(
                contract,
                endDateTime='',
                durationStr='5 D',
                barSizeSetting='1 day',
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1
            )
            
            if bars_daily and len(bars_daily) >= 1:
                current_day = bars_daily[-1]
                stop_levels['day_low'] = current_day.low
                
                if len(bars_daily) >= 2:
                    prior_day = bars_daily[-2]
                    stop_levels['prior_day_low'] = prior_day.low
            
            # Add percentage stop
            if self.direction == 'BUY':
                stop_levels['2_percent'] = current_price * 0.98
            else:
                stop_levels['2_percent'] = current_price * 1.02
                
            return stop_levels
            
        except Exception as e:
            logger.error(f"Error fetching stop levels: {str(e)}")
            return {}


class AsyncDataFetcher(QObject):
    """
    Async data fetcher using thread pool for true non-blocking operations
    """
    
    # Signals
    fetch_started = pyqtSignal(str)
    fetch_completed = pyqtSignal(dict)
    fetch_failed = pyqtSignal(str)
    fetch_progress = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(2)  # Limit concurrent fetches
        
    def fetch_price_async(self, symbol: str, direction: str = 'BUY'):
        """Start async price fetch"""
        try:
            logger.info(f"Starting async price fetch for {symbol}")
            
            # Emit started signal
            self.fetch_started.emit(symbol)
            
            # Create and configure worker
            worker = AsyncPriceWorker(symbol, direction)
            worker.signals.completed.connect(self.fetch_completed.emit)
            worker.signals.failed.connect(self.fetch_failed.emit)
            worker.signals.progress.connect(self.fetch_progress.emit)
            
            # Start worker
            self.thread_pool.start(worker)
            
        except Exception as e:
            error_msg = f"Error starting async fetch: {str(e)}"
            logger.error(error_msg)
            self.fetch_failed.emit(error_msg)
            
    def cleanup(self):
        """Cleanup thread pool"""
        self.thread_pool.waitForDone(1000)  # Wait up to 1 second
        

# Create singleton instance
async_data_fetcher = AsyncDataFetcher()