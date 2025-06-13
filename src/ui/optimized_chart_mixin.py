"""
Optimized Chart Mixin
Provides real-time chart optimization methods that can be mixed into existing chart widgets
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import numpy as np

from PyQt6.QtCore import QTimer, pyqtSlot
from src.utils.logger import logger
from src.core.real_time_chart_updater import real_time_updater, StreamingBar


class OptimizedChartMixin:
    """
    Mixin class to add real-time optimization to existing chart widgets
    Can be added to ChartWidgetEmbedded without breaking existing functionality
    """
    
    def init_real_time_optimization(self):
        """Initialize real-time chart optimization - call this in your chart widget __init__"""
        # Real-time data management
        self._rt_enabled = False
        self._rt_bars_buffer = []
        self._last_bar_time = None
        self._current_bar = None
        
        # Performance optimization
        self._chart_update_timer = QTimer()
        self._chart_update_timer.timeout.connect(self._batch_update_chart)
        self._pending_updates = False
        
        # Connect to real-time updater
        real_time_updater.new_bar_update.connect(self._on_streaming_bar_update)
        real_time_updater.price_tick_update.connect(self._on_price_tick_update)
        
        logger.info("Real-time chart optimization initialized")
    
    def enable_real_time_mode(self, symbol: str):
        """
        Enable real-time mode for faster updates
        
        Args:
            symbol: Symbol to stream
        """
        try:
            if not hasattr(self, '_rt_enabled'):
                self.init_real_time_optimization()
            
            # Start streaming data
            success = real_time_updater.start_streaming(symbol)
            if success:
                self._rt_enabled = True
                self.current_symbol = symbol
                
                # Reduce traditional refresh interval to backup mode
                if hasattr(self, 'update_timer'):
                    self.update_timer.stop()
                    # Keep slow refresh as backup (30s instead of 5s)
                    self.update_timer.start(30000)
                
                logger.info(f"Real-time mode enabled for {symbol}")
                return True
            else:
                logger.warning(f"Failed to enable real-time mode for {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error enabling real-time mode: {e}")
            return False
    
    def disable_real_time_mode(self):
        """Disable real-time mode and return to traditional refresh"""
        try:
            self._rt_enabled = False
            real_time_updater.stop_streaming()
            
            # Restore traditional refresh interval
            if hasattr(self, 'update_timer'):
                self.update_timer.stop()
                self.update_timer.start(5000)  # Back to 5s refresh
                
            logger.info("Real-time mode disabled")
            
        except Exception as e:
            logger.error(f"Error disabling real-time mode: {e}")
    
    @pyqtSlot(object)
    def _on_streaming_bar_update(self, streaming_bar: StreamingBar):
        """Handle incoming streaming bar data"""
        try:
            if not self._rt_enabled or not hasattr(self, 'current_symbol'):
                return
                
            # Buffer the update for batch processing
            self._rt_bars_buffer.append(streaming_bar)
            
            # Schedule batch update if not already pending
            if not self._pending_updates:
                self._pending_updates = True
                # Small delay to batch rapid updates
                self._chart_update_timer.start(250)  # 250ms batch interval
                
        except Exception as e:
            logger.error(f"Error handling streaming bar update: {e}")
    
    @pyqtSlot(float, float, float)
    def _on_price_tick_update(self, last: float, bid: float, ask: float):
        """Handle live price tick updates"""
        try:
            if not self._rt_enabled:
                return
                
            # Update current price display (if you have price labels)
            if hasattr(self, 'update_live_price'):
                self.update_live_price(last, bid, ask)
                
            # Update current bar with latest price
            if self._current_bar and last > 0:
                self._current_bar.close = last
                if last > self._current_bar.high:
                    self._current_bar.high = last
                if last < self._current_bar.low:
                    self._current_bar.low = last
                    
                # Trigger lightweight update for current bar
                if hasattr(self, 'update_current_bar_display'):
                    self.update_current_bar_display(self._current_bar)
                    
        except Exception as e:
            logger.error(f"Error handling price tick update: {e}")
    
    def _batch_update_chart(self):
        """Process batched real-time updates efficiently"""
        try:
            if not self._rt_bars_buffer:
                self._pending_updates = False
                self._chart_update_timer.stop()
                return
                
            # Process all buffered bars
            new_bars = self._rt_bars_buffer.copy()
            self._rt_bars_buffer.clear()
            
            # Efficiently update chart with new bars
            self._apply_streaming_bars(new_bars)
            
            self._pending_updates = False
            self._chart_update_timer.stop()
            
            logger.debug(f"Processed {len(new_bars)} streaming bars")
            
        except Exception as e:
            logger.error(f"Error in batch chart update: {e}")
            self._pending_updates = False
            self._chart_update_timer.stop()
    
    def _apply_streaming_bars(self, new_bars: List[StreamingBar]):
        """
        Apply streaming bars to chart data efficiently
        Override this method in your chart widget
        """
        try:
            # This is the method you'll override in your chart widget
            # to efficiently update the matplotlib chart with new data
            
            for bar in new_bars:
                # Example: Add to your chart data arrays
                if hasattr(self, 'chart_data') and self.chart_data:
                    # Convert StreamingBar to your chart format
                    new_data_point = {
                        'time': bar.time,
                        'open': bar.open,
                        'high': bar.high,
                        'low': bar.low,
                        'close': bar.close,
                        'volume': bar.volume
                    }
                    
                    # Check if this is an update to the last bar or a new bar
                    if (self.chart_data and 
                        abs((bar.time - self.chart_data[-1]['time']).total_seconds()) < 30):
                        # Update existing bar
                        self.chart_data[-1] = new_data_point
                    else:
                        # New bar
                        self.chart_data.append(new_data_point)
                        # Keep only recent data to avoid memory issues
                        if len(self.chart_data) > 1000:
                            self.chart_data = self.chart_data[-500:]
            
            # Update the chart display efficiently
            if hasattr(self, 'update_chart_display'):
                self.update_chart_display(incremental=True)
            
        except Exception as e:
            logger.error(f"Error applying streaming bars: {e}")
    
    def get_real_time_performance_info(self) -> Dict[str, Any]:
        """Get performance information about real-time updates"""
        return {
            'rt_enabled': getattr(self, '_rt_enabled', False),
            'streaming': real_time_updater.is_streaming,
            'symbol': real_time_updater.current_symbol,
            'buffer_size': len(getattr(self, '_rt_bars_buffer', [])),
            'pending_updates': getattr(self, '_pending_updates', False)
        }

