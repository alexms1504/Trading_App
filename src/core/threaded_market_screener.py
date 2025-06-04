"""
Threaded Market Screener
Multi-threaded implementation of market screener to prevent UI blocking during screening operations
"""

from typing import List, Dict, Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal, QObject, QRunnable, QThreadPool
from dataclasses import dataclass

from src.utils.logger import logger
from src.core.market_screener import market_screener, ScreeningCriteria, ScanData


class ScreenerWorker(QRunnable):
    """Worker thread for market screening operations"""
    
    def __init__(self, operation: str, criteria: Optional[ScreeningCriteria], callback_obj):
        super().__init__()
        self.operation = operation
        self.criteria = criteria
        self.callback_obj = callback_obj
        self.setAutoDelete(True)
        
    def run(self):
        """Execute screening operation in background thread"""
        try:
            logger.info(f"Background thread executing screener operation: {self.operation}")
            
            # Create event loop for this thread since ib_async needs it
            import asyncio
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                self._execute_operation()
            finally:
                # Clean up the event loop
                loop.close()
                
        except Exception as e:
            error_msg = f"Error in screener worker ({self.operation}): {str(e)}"
            logger.error(error_msg)
            self.callback_obj.screening_error.emit(error_msg)
            
    def _execute_operation(self):
        """Execute the actual screening operation"""
        try:
            if self.operation == "start":
                # Set criteria if provided
                if self.criteria:
                    market_screener.set_criteria(self.criteria)
                
                # Start screening (blocking operation)
                success = market_screener.start_screening()
                
                if success:
                    # Get initial results
                    results = market_screener.get_formatted_results(fetch_real_data=False)
                    logger.info(f"Screener started successfully, got {len(results)} results")
                    self.callback_obj.screening_started.emit(len(results))
                    self.callback_obj.results_ready.emit(results)
                else:
                    logger.error("Failed to start screening")
                    self.callback_obj.screening_error.emit("Failed to start screening")
                    
            elif self.operation == "refresh":
                # Refresh results (blocking operation)
                success = market_screener.refresh_results()
                
                if success:
                    # Get updated results (without real data to avoid blocking)
                    results = market_screener.get_formatted_results(fetch_real_data=False)
                    self.callback_obj.results_ready.emit(results)
                else:
                    self.callback_obj.screening_error.emit("Failed to refresh results")
                    
            elif self.operation == "fetch_real_prices":
                # Get real market data (this is the slow operation)
                results = market_screener.get_formatted_results(fetch_real_data=True)
                self.callback_obj.real_prices_ready.emit(results)
                
            elif self.operation == "stop":
                # Stop screening
                market_screener.stop_screening()
                self.callback_obj.screening_stopped.emit()
                
        except Exception as e:
            error_msg = f"Error in screener operation ({self.operation}): {str(e)}"
            logger.error(error_msg)
            self.callback_obj.screening_error.emit(error_msg)


class ScreenerCallback(QObject):
    """Callback object for screener signals"""
    screening_started = pyqtSignal(int)  # number of results
    screening_stopped = pyqtSignal()
    results_ready = pyqtSignal(list)  # formatted results
    real_prices_ready = pyqtSignal(list)  # results with real prices
    screening_error = pyqtSignal(str)


class ThreadedMarketScreener(QObject):
    """
    Threaded market screener that prevents UI blocking during screening operations
    """
    
    # Signals for UI communication
    screening_started = pyqtSignal(int)  # number of results
    screening_stopped = pyqtSignal()
    results_updated = pyqtSignal(list)  # formatted results
    real_prices_updated = pyqtSignal(list)  # results with real prices
    screening_error = pyqtSignal(str)
    operation_started = pyqtSignal(str)  # operation type
    operation_completed = pyqtSignal(str)  # operation type
    
    def __init__(self):
        super().__init__()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(2)  # Limit concurrent screening operations
        self.callback_obj = ScreenerCallback()
        self.is_screening = False
        
        # Connect callback signals
        self.callback_obj.screening_started.connect(self.on_screening_started)
        self.callback_obj.screening_stopped.connect(self.on_screening_stopped)
        self.callback_obj.results_ready.connect(self.on_results_ready)
        self.callback_obj.real_prices_ready.connect(self.on_real_prices_ready)
        self.callback_obj.screening_error.connect(self.on_screening_error)
        
        logger.info(f"ThreadedMarketScreener initialized with max {self.thread_pool.maxThreadCount()} threads")
        
    def start_screening_async(self, criteria: ScreeningCriteria):
        """
        Start market screening asynchronously
        
        Args:
            criteria: Screening criteria to use
        """
        try:
            logger.info("Starting async market screening")
            
            # Emit operation started
            self.operation_started.emit("start")
            
            # Create and submit worker
            worker = ScreenerWorker("start", criteria, self.callback_obj)
            self.thread_pool.start(worker)
            
            logger.info("Submitted screening start to thread pool")
            
        except Exception as e:
            error_msg = f"Error starting async screening: {str(e)}"
            logger.error(error_msg)
            self.screening_error.emit(error_msg)
            
    def refresh_results_async(self):
        """
        Refresh screening results asynchronously
        """
        try:
            if not self.is_screening:
                logger.warning("Cannot refresh - screening not active")
                return
                
            logger.info("Starting async results refresh")
            
            # Emit operation started
            self.operation_started.emit("refresh")
            
            # Create and submit worker
            worker = ScreenerWorker("refresh", None, self.callback_obj)
            self.thread_pool.start(worker)
            
            logger.info("Submitted refresh to thread pool")
            
        except Exception as e:
            error_msg = f"Error starting async refresh: {str(e)}"
            logger.error(error_msg)
            self.screening_error.emit(error_msg)
            
    def fetch_real_prices_async(self):
        """
        Fetch real market prices asynchronously
        """
        try:
            if not self.is_screening:
                logger.warning("Cannot fetch real prices - screening not active")
                self.screening_error.emit("Start screening first")
                return
                
            logger.info("Starting async real price fetch")
            
            # Emit operation started
            self.operation_started.emit("fetch_real_prices")
            
            # Create and submit worker
            worker = ScreenerWorker("fetch_real_prices", None, self.callback_obj)
            self.thread_pool.start(worker)
            
            logger.info("Submitted real price fetch to thread pool")
            
        except Exception as e:
            error_msg = f"Error starting async real price fetch: {str(e)}"
            logger.error(error_msg)
            self.screening_error.emit(error_msg)
            
    def stop_screening_async(self):
        """
        Stop market screening asynchronously
        """
        try:
            logger.info("Starting async screening stop")
            
            # Emit operation started
            self.operation_started.emit("stop")
            
            # Create and submit worker
            worker = ScreenerWorker("stop", None, self.callback_obj)
            self.thread_pool.start(worker)
            
            logger.info("Submitted stop to thread pool")
            
        except Exception as e:
            error_msg = f"Error stopping async screening: {str(e)}"
            logger.error(error_msg)
            self.screening_error.emit(error_msg)
            
    def on_screening_started(self, result_count: int):
        """Handle screening started signal"""
        self.is_screening = True
        logger.info(f"Screening started with {result_count} results")
        self.screening_started.emit(result_count)
        self.operation_completed.emit("start")
        
    def on_screening_stopped(self):
        """Handle screening stopped signal"""
        self.is_screening = False
        logger.info("Screening stopped")
        self.screening_stopped.emit()
        self.operation_completed.emit("stop")
        
    def on_results_ready(self, results: list):
        """Handle results ready signal"""
        logger.info(f"Results ready: {len(results)} items")
        self.results_updated.emit(results)
        self.operation_completed.emit("refresh")
        
    def on_real_prices_ready(self, results: list):
        """Handle real prices ready signal"""
        logger.info(f"Real prices ready: {len(results)} items")
        self.real_prices_updated.emit(results)
        self.operation_completed.emit("fetch_real_prices")
        
    def on_screening_error(self, error_msg: str):
        """Handle screening error signal"""
        logger.error(f"Screening error: {error_msg}")
        self.screening_error.emit(error_msg)
        
    def get_active_thread_count(self) -> int:
        """Get number of currently active threads"""
        return self.thread_pool.activeThreadCount()
        
    def is_screening_active(self) -> bool:
        """Check if screening is currently active"""
        return self.is_screening
        
    def cleanup(self):
        """Cleanup thread pool resources"""
        try:
            logger.info("Cleaning up ThreadedMarketScreener...")
            self.thread_pool.clear()
            self.thread_pool.waitForDone(3000)
            
            # Also stop the underlying screener
            if self.is_screening:
                market_screener.stop_screening()
                
            logger.info("ThreadedMarketScreener cleanup completed")
        except Exception as e:
            logger.error(f"Error during ThreadedMarketScreener cleanup: {str(e)}")


# Create singleton instance
threaded_market_screener = ThreadedMarketScreener()