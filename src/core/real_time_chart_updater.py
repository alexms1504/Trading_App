"""
Real-Time Chart Updater
Provides streaming chart updates using ib_async without affecting order operations
"""

import asyncio
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np

from ib_async import IB, Stock, RealTimeBar, BarData
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from src.utils.logger import logger
from src.services.ib_connection_service import ib_connection_manager


@dataclass
class StreamingBar:
    """Represents a real-time bar update"""
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    wap: float = 0.0  # Volume weighted average price


class RealTimeChartUpdater(QObject):
    """
    Real-time chart updater using ib_async streaming capabilities
    Optimized for minimal latency without affecting trading operations
    """
    
    # Signals for chart updates
    new_bar_update = pyqtSignal(object)  # StreamingBar
    price_tick_update = pyqtSignal(float, float, float)  # last, bid, ask
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ib_manager = ib_connection_manager
        self.current_symbol = None
        self.streaming_contract = None
        self.is_streaming = False
        
        # Real-time data handlers
        self._rt_bars_subscription = None
        self._price_subscription = None
        
        # Buffering for performance
        self._price_buffer = []
        self._update_buffer_timer = QTimer()
        self._update_buffer_timer.timeout.connect(self._flush_price_buffer)
        
        # Performance tracking
        self._last_update_time = 0
        self._update_count = 0
        
    def start_streaming(self, symbol: str) -> bool:
        """
        Start real-time streaming for a symbol
        
        Args:
            symbol: Stock symbol to stream
            
        Returns:
            bool: True if streaming started successfully
        """
        try:
            if not self.ib_manager or not self.ib_manager.is_connected():
                logger.warning("IB not connected - cannot start real-time streaming")
                return False
                
            # Stop existing streaming
            self.stop_streaming()
            
            # Create contract
            self.streaming_contract = Stock(symbol, 'SMART', 'USD')
            self.current_symbol = symbol
            
            # Method 1: Real-time 5-second bars (fastest for chart updates)
            self._start_realtime_bars()
            
            # Method 2: Tick-by-tick price updates (for live price display)
            self._start_price_ticks()
            
            self.is_streaming = True
            logger.info(f"Started real-time streaming for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting real-time streaming: {e}")
            return False
    
    def _start_realtime_bars(self):
        """Start real-time 5-second bar updates"""
        try:
            if not self.ib_manager.ib:
                return
                
            # Request real-time 5-second bars
            # This provides OHLCV data every 5 seconds
            self._rt_bars_subscription = self.ib_manager.ib.reqRealTimeBars(
                contract=self.streaming_contract,
                barSize=5,  # 5-second bars
                whatToShow='TRADES',  # Use actual trades
                useRTH=False  # Include extended hours
            )
            
            # Set up the callback for new bars
            self._rt_bars_subscription.updateEvent += self._on_realtime_bar
            
            logger.info(f"Started real-time 5-second bars for {self.current_symbol}")
            
        except Exception as e:
            logger.error(f"Error starting real-time bars: {e}")
    
    def _start_price_ticks(self):
        """Start tick-by-tick price updates for live price display"""
        try:
            if not self.ib_manager.ib:
                return
                
            # Request market data for price ticks
            self._price_subscription = self.ib_manager.ib.reqMktData(
                contract=self.streaming_contract,
                genericTickList='',  # Standard price data
                snapshot=False,  # Streaming data
                regulatorySnapshot=False
            )
            
            # Set up price update callback
            self._price_subscription.updateEvent += self._on_price_tick
            
            logger.info(f"Started price tick streaming for {self.current_symbol}")
            
        except Exception as e:
            logger.error(f"Error starting price ticks: {e}")
    
    def _on_realtime_bar(self, bars, *args):
        """Handle incoming real-time bar data"""
        try:
            # Handle the callback signature - ib_async passes (subscription, bars)
            if isinstance(bars, (list, tuple)) and len(bars) > 0:
                # Extract the actual RealTimeBar from the list
                real_bar = bars[0] if isinstance(bars, (list, tuple)) else bars
            else:
                real_bar = bars
                
            # Convert to our StreamingBar format
            # Handle ib_async RealTimeBar attribute names safely
            streaming_bar = StreamingBar(
                time=real_bar.time,
                open=getattr(real_bar, 'open_', getattr(real_bar, 'open', 0.0)),
                high=getattr(real_bar, 'high', 0.0),
                low=getattr(real_bar, 'low', 0.0),
                close=getattr(real_bar, 'close', 0.0),
                volume=getattr(real_bar, 'volume', 0),
                wap=getattr(real_bar, 'wap', 0.0)
            )
            
            # Emit signal for chart update
            self.new_bar_update.emit(streaming_bar)
            
            # Performance tracking
            self._update_count += 1
            current_time = datetime.now().timestamp()
            if current_time - self._last_update_time > 60:  # Log every minute
                logger.info(f"Real-time updates: {self._update_count} bars/minute for {self.current_symbol}")
                self._update_count = 0
                self._last_update_time = current_time
            
        except Exception as e:
            logger.error(f"Error processing real-time bar: {e}")
    
    def _on_price_tick(self, ticker):
        """Handle incoming price tick data"""
        try:
            if hasattr(ticker, 'last') and hasattr(ticker, 'bid') and hasattr(ticker, 'ask'):
                last = float(ticker.last) if ticker.last and ticker.last > 0 else 0.0
                bid = float(ticker.bid) if ticker.bid and ticker.bid > 0 else 0.0  
                ask = float(ticker.ask) if ticker.ask and ticker.ask > 0 else 0.0
                
                if last > 0:  # Only emit if we have valid price data
                    # Buffer price updates to avoid overwhelming the UI
                    self._price_buffer.append((last, bid, ask))
                    
                    # Start timer for batched updates (100ms intervals)
                    if not self._update_buffer_timer.isActive():
                        self._update_buffer_timer.start(100)
                        
        except Exception as e:
            logger.error(f"Error processing price tick: {e}")
    
    def _flush_price_buffer(self):
        """Flush buffered price updates"""
        try:
            if self._price_buffer:
                # Use the most recent price from the buffer
                last, bid, ask = self._price_buffer[-1]
                self.price_tick_update.emit(last, bid, ask)
                self._price_buffer.clear()
                
            self._update_buffer_timer.stop()
            
        except Exception as e:
            logger.error(f"Error flushing price buffer: {e}")
    
    def stop_streaming(self):
        """Stop all real-time streaming"""
        try:
            if not self.ib_manager.ib:
                return
                
            # Cancel real-time bars
            if self._rt_bars_subscription:
                self.ib_manager.ib.cancelRealTimeBars(self._rt_bars_subscription)
                self._rt_bars_subscription = None
                
            # Cancel price ticks
            if self._price_subscription:
                self.ib_manager.ib.cancelMktData(self._price_subscription)
                self._price_subscription = None
                
            # Stop timers
            self._update_buffer_timer.stop()
            
            self.is_streaming = False
            logger.info(f"Stopped real-time streaming for {self.current_symbol}")
            
        except Exception as e:
            logger.error(f"Error stopping real-time streaming: {e}")
    
    def change_symbol(self, new_symbol: str):
        """Change the streaming symbol"""
        if new_symbol != self.current_symbol:
            self.start_streaming(new_symbol)


# Global instance
real_time_updater = RealTimeChartUpdater()