"""
Simple Threaded Fetcher
A simpler approach using QTimer to avoid blocking the UI while fetching data
"""

from typing import Optional, Dict, Any
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication

from src.utils.logger import logger
from src.core.data_fetcher import data_fetcher
from src.core.market_screener import market_screener, ScreeningCriteria
from src.core.price_cache import screener_price_cache


class SimpleThreadedDataFetcher(QObject):
    """
    Simple non-blocking data fetcher using QTimer
    Fetches data in chunks to keep UI responsive
    """
    
    # Signals
    fetch_started = pyqtSignal(str)  # symbol
    fetch_completed = pyqtSignal(dict)  # price_data
    fetch_failed = pyqtSignal(str)  # error_message
    fetch_progress = pyqtSignal(str)  # status message
    
    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.timer.timeout.connect(self._fetch_step)
        self.current_symbol = None
        self.current_direction = None
        self.fetch_state = None
        
    def fetch_price_and_stops_async(self, symbol: str, direction: str = 'BUY'):
        """
        Start async price fetch using timer-based approach
        """
        try:
            logger.info(f"Starting timer-based price fetch for {symbol}")
            
            self.current_symbol = symbol
            self.current_direction = direction
            self.fetch_state = "starting"
            
            # Emit started signal
            self.fetch_started.emit(symbol)
            self.fetch_progress.emit(f"Fetching data for {symbol}...")
            
            # Start timer to fetch in next event loop iteration
            self.timer.setSingleShot(True)
            self.timer.setInterval(10)  # 10ms delay
            self.timer.start()
            
        except Exception as e:
            error_msg = f"Error starting price fetch: {str(e)}"
            logger.error(error_msg)
            self.fetch_failed.emit(error_msg)
            
    def _fetch_step(self):
        """Execute fetch in timer callback (non-blocking)"""
        try:
            # Process events to keep UI responsive
            QApplication.processEvents()
            
            logger.info(f"Fetching price data for {self.current_symbol} in main thread (non-blocking)")
            
            # Fetch the data (this call may take 2-3 seconds)
            price_data = data_fetcher.get_price_and_stops(self.current_symbol, self.current_direction)
            
            if price_data:
                logger.info(f"Successfully fetched price data for {self.current_symbol}")
                self.fetch_completed.emit(price_data)
            else:
                self.fetch_failed.emit(f"Failed to fetch market data for {self.current_symbol}")
                
        except Exception as e:
            error_msg = f"Error fetching price data: {str(e)}"
            logger.error(error_msg)
            self.fetch_failed.emit(error_msg)
            
    def cleanup(self):
        """Cleanup resources"""
        if self.timer.isActive():
            self.timer.stop()


class SimpleThreadedMarketScreener(QObject):
    """
    Simple non-blocking market screener using QTimer
    """
    
    # Signals
    screening_started = pyqtSignal(int)  # number of results
    screening_stopped = pyqtSignal()
    results_updated = pyqtSignal(list)  # formatted results
    real_prices_updated = pyqtSignal(list)  # results with real prices
    screening_error = pyqtSignal(str)
    operation_started = pyqtSignal(str)  # operation type
    operation_completed = pyqtSignal(str)  # operation type
    price_fetch_progress = pyqtSignal(int, int)  # current, total
    
    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.timer.timeout.connect(self._execute_step)
        self.current_operation = None
        self.current_criteria = None
        self.is_screening = False
        
    def start_screening_async(self, criteria: ScreeningCriteria):
        """Start screening asynchronously"""
        try:
            logger.info("Starting timer-based screening")
            
            self.current_operation = "start"
            self.current_criteria = criteria
            
            # Emit operation started
            self.operation_started.emit("start")
            
            # Start timer to execute in next event loop iteration
            self.timer.setSingleShot(True)
            self.timer.setInterval(10)
            self.timer.start()
            
        except Exception as e:
            error_msg = f"Error starting screening: {str(e)}"
            logger.error(error_msg)
            self.screening_error.emit(error_msg)
            
    def refresh_results_async(self):
        """Refresh results asynchronously"""
        try:
            if not self.is_screening:
                logger.warning("Cannot refresh - screening not active")
                return
                
            logger.info("Starting timer-based refresh")
            
            self.current_operation = "refresh"
            
            # Emit operation started
            self.operation_started.emit("refresh")
            
            # Start timer
            self.timer.setSingleShot(True)
            self.timer.setInterval(10)
            self.timer.start()
            
        except Exception as e:
            error_msg = f"Error starting refresh: {str(e)}"
            logger.error(error_msg)
            self.screening_error.emit(error_msg)
            
    def fetch_real_prices_async(self):
        """Fetch real prices asynchronously"""
        try:
            if not self.is_screening:
                self.screening_error.emit("Start screening first")
                return
                
            logger.info("Starting timer-based real price fetch")
            
            self.current_operation = "fetch_real_prices"
            
            # Emit operation started
            self.operation_started.emit("fetch_real_prices")
            
            # Start timer
            self.timer.setSingleShot(True)
            self.timer.setInterval(10)
            self.timer.start()
            
        except Exception as e:
            error_msg = f"Error starting real price fetch: {str(e)}"
            logger.error(error_msg)
            self.screening_error.emit(error_msg)
            
    def stop_screening_async(self):
        """Stop screening asynchronously"""
        try:
            logger.info("Stopping screening")
            
            self.current_operation = "stop"
            
            # Emit operation started
            self.operation_started.emit("stop")
            
            # Execute immediately
            market_screener.stop_screening()
            self.is_screening = False
            self.screening_stopped.emit()
            self.operation_completed.emit("stop")
            
        except Exception as e:
            error_msg = f"Error stopping screening: {str(e)}"
            logger.error(error_msg)
            self.screening_error.emit(error_msg)
            
    def _fetch_real_prices_in_chunks(self, symbols: list):
        """Fetch real prices in chunks to keep UI responsive"""
        try:
            # Import here to avoid circular dependencies
            from src.core.ib_connection import ib_connection_manager
            
            if not ib_connection_manager.is_connected() or not symbols:
                self.screening_error.emit("Not connected or no symbols")
                return
                
            ib = ib_connection_manager.ib
            if not ib:
                self.screening_error.emit("IB client not available")
                return
                
            logger.info(f"Fetching real market data for {len(symbols)} symbols")
            
            # Create contracts for symbols
            from ib_async import Stock
            market_data = {}
            
            # Step 1: Check cache first
            cached_data = screener_price_cache.get_batch(symbols)
            if cached_data:
                market_data.update(cached_data)
                logger.info(f"Using cached data for {len(cached_data)} symbols")
            
            # Only fetch symbols not in cache
            symbols_to_fetch = [s for s in symbols[:10] if s not in cached_data]
            
            if not symbols_to_fetch:
                logger.info("All prices found in cache!")
                # Emit progress for cached items
                self.price_fetch_progress.emit(len(cached_data), len(cached_data))
            else:
                logger.info(f"Need to fetch {len(symbols_to_fetch)} symbols (cache miss)")
            
            tickers = []
            
            # Step 1: Qualify all contracts first (batch operation)
            contracts = []
            for symbol in symbols_to_fetch:
                try:
                    contract = Stock(symbol, 'SMART', 'USD')
                    contracts.append((symbol, contract))
                except Exception as e:
                    logger.warning(f"Error creating contract for {symbol}: {str(e)}")
                    continue
            
            # Qualify all contracts at once
            if contracts:
                all_contracts = [c[1] for c in contracts]
                ib.qualifyContracts(*all_contracts)
                
                # Step 2: Start all market data requests without delays
                for symbol, contract in contracts:
                    try:
                        ticker = ib.reqMktData(contract, '', False, False)
                        tickers.append((symbol, ticker))
                    except Exception as e:
                        logger.warning(f"Error requesting data for {symbol}: {str(e)}")
                        continue
            
            # Step 3: Use shorter wait time with incremental checking
            if tickers:
                # Try shorter wait first
                ib.sleep(0.3)
                QApplication.processEvents()
                
                # Check if we have data, if not wait a bit more
                has_data = any(ticker.last or ticker.bid or ticker.ask for _, ticker in tickers)
                if not has_data:
                    ib.sleep(0.3)
                    QApplication.processEvents()
                
                # Final check
                has_data = any(ticker.last or ticker.bid or ticker.ask for _, ticker in tickers)
                if not has_data:
                    ib.sleep(0.2)  # Total wait: 0.8s instead of 1.0s
            
            # Step 4: Collect all data
            processed = len(cached_data)  # Start with cached count
            total = len(cached_data) + len(tickers)
            
            for symbol, ticker in tickers:
                try:
                    # Emit progress
                    processed += 1
                    self.price_fetch_progress.emit(processed, total)
                    
                    # Extract price with multiple fallbacks
                    last_price = ticker.last
                    if not last_price or last_price <= 0:
                        if ticker.bid and ticker.ask and ticker.bid > 0 and ticker.ask > 0:
                            last_price = (ticker.bid + ticker.ask) / 2
                        elif ticker.close and ticker.close > 0:
                            last_price = ticker.close
                    
                    # Get previous close for % change
                    prev_close = ticker.close
                    
                    # Calculate percentage change
                    pct_change = None
                    if last_price and prev_close and prev_close > 0:
                        pct_change = ((last_price - prev_close) / prev_close) * 100
                    
                    # Store the data
                    if last_price:
                        price_data = {
                            'price': float(last_price),
                            'prev_close': float(prev_close) if prev_close else None,
                            'pct_change': float(pct_change) if pct_change is not None else None,
                            'bid': float(ticker.bid) if ticker.bid else None,
                            'ask': float(ticker.ask) if ticker.ask else None,
                            'volume': int(ticker.volume) if ticker.volume else None,
                            'timestamp': datetime.now()
                        }
                        market_data[symbol] = price_data
                        
                        # Cache the price data
                        screener_price_cache.set(symbol, price_data)
                        
                        logger.info(f"Got price for {symbol}: ${last_price:.2f}")
                    
                    # Cancel market data immediately
                    ib.cancelMktData(ticker.contract)
                    
                except Exception as e:
                    logger.warning(f"Error processing data for {symbol}: {str(e)}")
                    continue
                    
            # Now update the results with real prices
            formatted_results = []
            current_results = market_screener.get_current_results()
            
            for result in current_results:
                try:
                    contract = result.contractDetails.contract
                    symbol = contract.symbol
                    
                    # Use real market data if available
                    symbol_data = market_data.get(symbol, {})
                    
                    formatted_result = {
                        'rank': result.rank,
                        'symbol': symbol,
                        'company_name': contract.symbol,
                        'exchange': getattr(contract, 'exchange', ''),
                        'currency': getattr(contract, 'currency', ''),
                        'distance': symbol_data.get('pct_change', 0),
                        'benchmark': result.benchmark,
                        'projection': result.projection,
                        'legs': result.legsStr,
                        'latest_price': symbol_data.get('price', None),
                        'volume_usd': symbol_data.get('volume', 0) * symbol_data.get('price', 1) if symbol_data.get('volume') and symbol_data.get('price') else None,
                        'contract': contract,
                        'timestamp': datetime.now(),
                        'data_source': 'REAL' if symbol in market_data else 'NO_DATA'
                    }
                    formatted_results.append(formatted_result)
                    
                except Exception as e:
                    logger.error(f"Error formatting result: {str(e)}")
                    continue
                    
            self.real_prices_updated.emit(formatted_results)
            logger.info(f"Emitted {len(formatted_results)} results with real prices")
            self.operation_completed.emit("fetch_real_prices")
            
        except Exception as e:
            error_msg = f"Error fetching real prices: {str(e)}"
            logger.error(error_msg)
            self.screening_error.emit(error_msg)
            self.operation_completed.emit("fetch_real_prices")
    
    def _execute_step(self):
        """Execute operation in timer callback"""
        try:
            # Process events to keep UI responsive
            QApplication.processEvents()
            
            if self.current_operation == "start":
                # Set criteria
                market_screener.set_criteria(self.current_criteria)
                
                # Start screening
                success = market_screener.start_screening()
                
                if success:
                    results = market_screener.get_formatted_results(fetch_real_data=False)
                    logger.info(f"Screening started with {len(results)} results")
                    self.is_screening = True
                    self.screening_started.emit(len(results))
                    self.results_updated.emit(results)
                else:
                    self.screening_error.emit("Failed to start screening")
                    
            elif self.current_operation == "refresh":
                success = market_screener.refresh_results()
                
                if success:
                    results = market_screener.get_formatted_results(fetch_real_data=False)
                    self.results_updated.emit(results)
                else:
                    self.screening_error.emit("Failed to refresh results")
                    
            elif self.current_operation == "fetch_real_prices":
                # First get current results without real data
                current_results = market_screener.get_current_results()
                if not current_results:
                    self.screening_error.emit("No screening results to fetch prices for")
                    return
                    
                # Get just the symbols from top results
                symbols = []
                for result in current_results[:10]:  # Limit to top 10
                    try:
                        contract = result.contractDetails.contract
                        symbols.append(contract.symbol)
                    except:
                        continue
                
                logger.info(f"Fetching real prices for {len(symbols)} symbols")
                
                # Process in chunks to keep UI responsive
                self._fetch_real_prices_in_chunks(symbols)
                # Note: operation_completed is emitted from within _fetch_real_prices_in_chunks
                return
                
            self.operation_completed.emit(self.current_operation)
            
        except Exception as e:
            error_msg = f"Error in operation {self.current_operation}: {str(e)}"
            logger.error(error_msg)
            self.screening_error.emit(error_msg)
            
    def is_screening_active(self) -> bool:
        """Check if screening is active"""
        return self.is_screening
        
    def cleanup(self):
        """Cleanup resources"""
        if self.timer.isActive():
            self.timer.stop()
        if self.is_screening:
            market_screener.stop_screening()


# Create singleton instances
simple_threaded_data_fetcher = SimpleThreadedDataFetcher()
simple_threaded_market_screener = SimpleThreadedMarketScreener()