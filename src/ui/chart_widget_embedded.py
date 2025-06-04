"""
Embedded Chart Widget
Interactive candlestick chart using matplotlib for PyQt6 embedding
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import numpy as np
import pytz

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QGroupBox, QFrame, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

try:
    import matplotlib
    matplotlib.use('Qt5Agg')  # Use Qt5Agg backend for PyQt6 compatibility
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    import pandas as pd
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False
    print("Warning: matplotlib not available. Charts will be disabled.")

# Note: mplfinance not used in current implementation
# We draw candlesticks manually using matplotlib for better control

from src.utils.logger import logger
from src.core.chart_data_manager import chart_data_manager
from src.ui.price_levels import PriceLevelManager
from src.core.chart_performance_optimizer import chart_cache, chart_optimizer, indicator_optimizer


class CandlestickChart(FigureCanvas):
    """Custom matplotlib canvas for candlestick charts"""
    
    def __init__(self, parent=None):
        # Create figure with dark background
        self.fig = Figure(figsize=(10, 6), facecolor='#1e1e1e')
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Create subplots with better proportions (85% price, 15% volume)
        from matplotlib.gridspec import GridSpec
        gs = GridSpec(2, 1, height_ratios=[5, 1], hspace=0.02)
        self.price_ax = self.fig.add_subplot(gs[0])
        self.volume_ax = self.fig.add_subplot(gs[1], sharex=self.price_ax)
        
        # Adjust subplot heights and margins
        self.fig.subplots_adjust(hspace=0.05, top=0.98, bottom=0.08, left=0.05, right=0.98)
        
        # Style the axes
        self._style_axes()
        
        # Crosshair variables
        self.crosshair_v_price = None  # Vertical line in price chart
        self.crosshair_v_volume = None # Vertical line in volume chart
        self.crosshair_h = None       # Horizontal line in price chart
        self.ohlc_text = None         # OHLC display text
        self.current_data = None      # Store current chart data
        
        # Connect mouse events for crosshair with optimized handling
        self.fig.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.fig.canvas.mpl_connect('axes_leave_event', self._on_mouse_leave)
        
        # Performance optimization flags - reduced throttling for smoother experience
        self._last_crosshair_update = 0
        self._crosshair_throttle_ms = 16.67  # 60fps (1000ms/60fps = 16.67ms) - good balance
        
        # Blitting optimization disabled - causing dual chart rendering issue
        self._background = None
        self._use_blitting = False
        
    def _style_axes(self):
        """Apply dark theme styling to axes"""
        for ax in [self.price_ax, self.volume_ax]:
            ax.set_facecolor('#1e1e1e')
            ax.grid(True, color='#444444', linewidth=0.5, alpha=0.5)
            ax.tick_params(colors='white', which='both')
            ax.spines['bottom'].set_color('#666666')
            ax.spines['top'].set_color('#666666')
            ax.spines['left'].set_color('#666666')
            ax.spines['right'].set_color('#666666')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
    
    def plot_candlestick_data(self, data: List[Dict[str, Any]], symbol: str, timeframe: str, show_emas: bool = True, show_smas: bool = True, show_vwap: bool = True):
        """Plot candlestick and volume data with technical indicators"""
        try:
            # Clear previous plots
            self.price_ax.clear()
            self.volume_ax.clear()
            
            if not data:
                return
            
            # Optimize data for large datasets
            if len(data) > 1000:
                logger.info(f"Large dataset ({len(data)} points), downsampling for performance")
                data = chart_optimizer.downsample_data(data, max_points=800)
            
            # Store data for crosshair
            self.current_data = data
            
            # Convert to arrays for easier manipulation (convert to Eastern Time)
            eastern = pytz.timezone('US/Eastern')
            times = [datetime.fromtimestamp(d['time'], tz=pytz.UTC).astimezone(eastern) for d in data]
            opens = np.array([d['open'] for d in data])
            highs = np.array([d['high'] for d in data])
            lows = np.array([d['low'] for d in data])
            closes = np.array([d['close'] for d in data])
            volumes = np.array([d['volume'] for d in data])
            
            # Create candlestick chart with optimized drawing
            # Pre-calculate all colors for better performance
            colors = ['#26a69a' if closes[i] >= opens[i] else '#ef5350' for i in range(len(data))]
            
            # Draw all high-low lines at once for better performance
            for i in range(len(data)):
                # Draw high-low line
                self.price_ax.plot([i, i], [lows[i], highs[i]], color=colors[i], linewidth=1)
                
                # Draw open-close rectangle
                height = abs(closes[i] - opens[i])
                bottom = min(opens[i], closes[i])
                rect = Rectangle((i - 0.3, bottom), 0.6, height, 
                               facecolor=colors[i], edgecolor=colors[i])
                self.price_ax.add_patch(rect)
            
            # Plot volume bars with better visibility (reuse colors)
            self.volume_ax.bar(range(len(data)), volumes, color=colors, alpha=0.7, width=0.8)
            
            # Set labels and title
            self.price_ax.set_title(f'{symbol} - {timeframe}', color='white', fontsize=14, pad=10)
            self.price_ax.set_ylabel('Price ($)', color='white')
            self.volume_ax.set_ylabel('Volume', color='white')
            self.volume_ax.set_xlabel('Time', color='white')
            
            # Calculate and plot technical indicators
            self._plot_technical_indicators(closes, highs, lows, volumes, times, len(data), show_emas, show_smas, show_vwap, timeframe)
            
            # Add day separator lines (only for intraday timeframes)
            if timeframe not in ['1d', '1w', '1M']:  # Skip for daily and higher timeframes
                current_day = None
                for i, time in enumerate(times):
                    day = time.date()
                    if current_day is not None and day != current_day:
                        # Add vertical dashed line for new day
                        self.price_ax.axvline(x=i-0.5, color='#555555', linestyle='--', alpha=0.7, linewidth=1)
                        self.volume_ax.axvline(x=i-0.5, color='#555555', linestyle='--', alpha=0.7, linewidth=1)
                    current_day = day
            
            # Format x-axis with intelligent time labeling
            self._format_time_axis(times, timeframe)
            
            # Apply styling
            self._style_axes()
            
            # Smart rescaling to new data range
            logger.info(f"Setting chart limits for {symbol} - Data range: {len(data)} bars")
            if data:
                price_min = min(d['low'] for d in data)
                price_max = max(d['high'] for d in data)
                logger.info(f"Price range: ${price_min:.2f} - ${price_max:.2f}")
                
                # Calculate reasonable margins
                price_range = price_max - price_min
                y_margin = max(price_range * 0.05, 0.01)  # 5% margin or minimum 1 cent
                
                # Set explicit, safe limits
                self.price_ax.set_xlim(-0.5, len(data) - 0.5)
                self.price_ax.set_ylim(price_min - y_margin, price_max + y_margin)
                
                # Volume limits
                max_volume = max(d['volume'] for d in data) if data else 1000
                self.volume_ax.set_xlim(-0.5, len(data) - 0.5)
                self.volume_ax.set_ylim(0, max_volume * 1.1)  # 10% margin above max volume
                
                logger.info(f"Chart limits set - Price Y: {self.price_ax.get_ylim()}, X: {self.price_ax.get_xlim()}")
            else:
                logger.warning("No data available for chart scaling")
            
            # Redraw with optimized margins - use tight_layout for better performance
            self.fig.tight_layout()
            self.draw()
            
            # Blitting disabled - using optimized draw_idle() instead for stable rendering
            
        except Exception as e:
            logger.error(f"Error plotting candlestick data: {str(e)}")
    
    def _format_time_axis(self, times: list, timeframe: str):
        """Format x-axis with appropriate time labels based on timeframe to avoid overlapping"""
        try:
            total_bars = len(times)
            
            # Define optimal intervals based on timeframe to avoid overlapping (1-hour spacing)
            timeframe_intervals = {
                '1m': 60,   # Every 1 hour = 60 bars
                '3m': 20,   # Every 1 hour = 20 bars  
                '5m': 12,   # Every 1 hour = 12 bars
                '15m': 4,   # Every 1 hour = 4 bars
                '30m': 2,   # Every 1 hour = 2 bars
                '1h': 1,    # Every 1 hour = 1 bar
                '4h': 1,    # Every 4 hours = 1 bar
                '1d': 1     # Every day = 1 bar
            }
            
            # Get the optimal step for this timeframe
            optimal_step = timeframe_intervals.get(timeframe, 12)  # Default to 12 for 5m (1 hour)
            
            # For very small datasets, show more labels
            if total_bars <= 10:
                step = 1
            elif total_bars <= 20:
                step = max(2, optimal_step // 2)
            else:
                step = optimal_step
            
            # Ensure we don't skip too many bars for small datasets
            step = min(step, max(1, total_bars // 4))
            
            # Create indices for labels starting from a good time boundary
            indices = []
            
            # Find the best starting point (try to start on clean time boundaries)
            start_index = 0
            if total_bars > step:
                # Try to find a nice starting time (prioritize hour boundaries :00)
                for i in range(min(step, total_bars)):
                    time_obj = times[i]
                    minute = time_obj.minute
                    if minute == 0:  # Start on hour boundary
                        start_index = i
                        break
                    elif minute == 30 and start_index == 0:  # Fallback to half-hour if no hour found
                        start_index = i
            
            # Add indices at regular intervals
            for i in range(start_index, total_bars, step):
                indices.append(i)
            
            # Always include the last bar if it's not too close to the previous one
            if indices and total_bars - 1 - indices[-1] >= step // 2:
                indices.append(total_bars - 1)
            
            # Format labels based on timeframe and time span
            labels = []
            for i in indices:
                time_obj = times[i]
                
                # For intraday timeframes, show time in Eastern Time (no timezone indicator)
                if timeframe in ['1m', '3m', '5m', '15m', '30m', '1h']:
                    # Check if we're spanning multiple days
                    if total_bars > 50 and (times[-1].date() != times[0].date()):
                        # Multiple days - show date and time
                        labels.append(time_obj.strftime('%m/%d %H:%M'))
                    else:
                        # Single day - show time only
                        labels.append(time_obj.strftime('%H:%M'))
                else:
                    # For daily+ timeframes, show date
                    labels.append(time_obj.strftime('%m/%d'))
            
            # Apply labels to the volume axis (which controls x-axis for both charts)
            self.volume_ax.set_xticks(indices)
            self.volume_ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=7)
            
            # Reduce number of minor ticks for cleaner appearance
            self.volume_ax.tick_params(axis='x', which='minor', length=0)
            
        except Exception as e:
            logger.error(f"Error formatting time axis: {e}")
            # Fallback to simple labeling
            step = max(1, len(times) // 6)
            indices = list(range(0, len(times), step))
            labels = [times[i].strftime('%H:%M') for i in indices]
            self.volume_ax.set_xticks(indices)
            self.volume_ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=7)
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        try:
            if len(prices) < period:
                return np.full(len(prices), np.nan)
            
            alpha = 2.0 / (period + 1)
            ema = np.zeros_like(prices)
            ema[0] = prices[0]
            
            for i in range(1, len(prices)):
                ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
                
            # Set first period-1 values to NaN
            ema[:period-1] = np.nan
            return ema
            
        except Exception as e:
            logger.error(f"Error calculating EMA: {e}")
            return np.full(len(prices), np.nan)
    
    def _calculate_sma(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Simple Moving Average"""
        try:
            if len(prices) < period:
                return np.full(len(prices), np.nan)
            
            sma = np.full(len(prices), np.nan)
            for i in range(period-1, len(prices)):
                sma[i] = np.mean(prices[i-period+1:i+1])
                
            return sma
            
        except Exception as e:
            logger.error(f"Error calculating SMA: {e}")
            return np.full(len(prices), np.nan)
    
    def _calculate_vwap(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray) -> np.ndarray:
        """Calculate Volume Weighted Average Price"""
        try:
            typical_prices = (highs + lows + closes) / 3
            vwap = np.full(len(closes), np.nan)
            
            cumulative_volume = 0
            cumulative_pv = 0
            
            for i in range(len(closes)):
                cumulative_pv += typical_prices[i] * volumes[i]
                cumulative_volume += volumes[i]
                
                if cumulative_volume > 0:
                    vwap[i] = cumulative_pv / cumulative_volume
                    
            return vwap
            
        except Exception as e:
            logger.error(f"Error calculating VWAP: {e}")
            return np.full(len(closes), np.nan)
    
    def _calculate_daily_vwap(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray, times: list) -> np.ndarray:
        """Calculate VWAP separately for each day"""
        try:
            typical_prices = (highs + lows + closes) / 3
            vwap = np.full(len(closes), np.nan)
            
            # Group data by day and calculate VWAP for each day
            current_day = None
            day_cumulative_pv = 0
            day_cumulative_volume = 0
            day_start_index = 0
            
            for i in range(len(closes)):
                time_obj = times[i]
                day = time_obj.date()
                
                # Check if we've moved to a new day
                if current_day is not None and day != current_day:
                    # Reset cumulative values for new day
                    day_cumulative_pv = 0
                    day_cumulative_volume = 0
                    day_start_index = i
                
                # Add current bar to daily calculation
                day_cumulative_pv += typical_prices[i] * volumes[i]
                day_cumulative_volume += volumes[i]
                
                # Calculate VWAP for current bar
                if day_cumulative_volume > 0:
                    vwap[i] = day_cumulative_pv / day_cumulative_volume
                
                current_day = day
                    
            return vwap
            
        except Exception as e:
            logger.error(f"Error calculating daily VWAP: {e}")
            return np.full(len(closes), np.nan)
    
    def _plot_technical_indicators(self, closes: np.ndarray, highs: np.ndarray, lows: np.ndarray, volumes: np.ndarray, times: list, data_length: int, show_emas: bool, show_smas: bool, show_vwap: bool, timeframe: str):
        """Plot technical indicators on the price chart with optimized calculations"""
        try:
            x_indices = range(data_length)
            labels = []
            
            # Check cache first
            data_dict = {
                'closes': closes.tolist(),
                'highs': highs.tolist(), 
                'lows': lows.tolist(),
                'volumes': volumes.tolist(),
                'times': [t.timestamp() for t in times]
            }
            
            cached_indicators = chart_cache.get_cached_calculations("indicators", timeframe, [data_dict])
            
            if cached_indicators:
                # Use cached calculations
                if show_emas and 'emas' in cached_indicators:
                    ema5, ema10, ema21 = cached_indicators['emas']
                else:
                    ema5 = ema10 = ema21 = None
                    
                if show_smas and 'smas' in cached_indicators:
                    sma50, sma100, sma200 = cached_indicators['smas']
                else:
                    sma50 = sma100 = sma200 = None
                    
                if show_vwap and 'vwap' in cached_indicators:
                    vwap = cached_indicators['vwap']
                else:
                    vwap = None
            else:
                # Calculate indicators with optimized methods
                calculations = {}
                
                # Plot EMAs if enabled
                if show_emas:
                    ema5 = indicator_optimizer.calculate_ema_optimized(closes, 5)
                    ema10 = indicator_optimizer.calculate_ema_optimized(closes, 10)
                    ema21 = indicator_optimizer.calculate_ema_optimized(closes, 21)
                    calculations['emas'] = (ema5, ema10, ema21)
                else:
                    ema5 = ema10 = ema21 = None
                    
                # Calculate SMAs if enabled
                if show_smas:
                    sma50 = indicator_optimizer.calculate_sma_optimized(closes, 50)
                    sma100 = indicator_optimizer.calculate_sma_optimized(closes, 100)
                    sma200 = indicator_optimizer.calculate_sma_optimized(closes, 200)
                    calculations['smas'] = (sma50, sma100, sma200)
                else:
                    sma50 = sma100 = sma200 = None
                    
                # Calculate VWAP if enabled
                if show_vwap:
                    if timeframe == '1d':
                        vwap = indicator_optimizer.calculate_vwap_optimized(highs, lows, closes, volumes)
                    else:
                        vwap = self._calculate_daily_vwap(highs, lows, closes, volumes, times)
                    calculations['vwap'] = vwap
                else:
                    vwap = None
                
                # Cache the calculations
                chart_cache.store_calculations("indicators", timeframe, [data_dict], calculations)
            
            # Plot EMAs if enabled
            if show_emas and ema5 is not None:
                self.price_ax.plot(x_indices, ema5, color='#FFFFFF', linewidth=1.0, alpha=0.8, label='EMA 5')
                self.price_ax.plot(x_indices, ema10, color='#FF69B4', linewidth=1.0, alpha=0.8, label='EMA 10')
                self.price_ax.plot(x_indices, ema21, color='#FFD700', linewidth=1.0, alpha=0.8, label='EMA 21')
                labels.extend(['EMA 5', 'EMA 10', 'EMA 21'])
            
            # Plot SMAs if enabled
            if show_smas and sma50 is not None:
                self.price_ax.plot(x_indices, sma50, color='#32CD32', linewidth=1.0, alpha=0.7, label='SMA 50')
                self.price_ax.plot(x_indices, sma100, color='#6A5ACD', linewidth=1.0, alpha=0.7, label='SMA 100')
                self.price_ax.plot(x_indices, sma200, color='#00FFFF', linewidth=1.0, alpha=0.7, label='SMA 200')
                labels.extend(['SMA 50', 'SMA 100', 'SMA 200'])
            
            # Plot VWAP if enabled
            if show_vwap and vwap is not None:
                self.price_ax.plot(x_indices, vwap, color='#FFA500', linewidth=1.2, alpha=0.9, label='VWAP')
                labels.append('VWAP')
            
            # Add legend only if there are indicators to show
            if labels:
                self.price_ax.legend(loc='upper left', fontsize=6, facecolor='#2e2e2e', 
                                   edgecolor='#666666', labelcolor='white', 
                                   framealpha=0.8, handlelength=1.0, handletextpad=0.3)
            
        except Exception as e:
            logger.error(f"Error plotting technical indicators: {e}")
            
    def _on_mouse_move(self, event):
        """Handle mouse movement for crosshair with throttling"""
        if event.inaxes not in [self.price_ax, self.volume_ax] or not self.current_data:
            return
            
        # Throttle crosshair updates to 120fps for ultra-smooth performance
        import time
        current_time = time.time() * 1000  # milliseconds
        if current_time - self._last_crosshair_update < self._crosshair_throttle_ms:
            return
        self._last_crosshair_update = current_time
            
        # Get x coordinate (bar index)
        x = event.xdata
        if x is None:
            return
            
        # Round to nearest integer (bar index) - optimized
        bar_idx = max(0, min(int(x + 0.5), len(self.current_data) - 1))
        
        # Remove existing crosshair efficiently
        for element in [self.crosshair_v_price, self.crosshair_v_volume, self.crosshair_h, self.ohlc_text]:
            if element:
                try:
                    element.remove()
                except:
                    pass  # Ignore removal errors
            
        # Draw crosshair lines efficiently
        crosshair_color = '#888888'
        crosshair_props = {'color': crosshair_color, 'linestyle': '-', 'linewidth': 0.8, 'alpha': 0.8}
        
        self.crosshair_v_price = self.price_ax.axvline(x=bar_idx, **crosshair_props)
        self.crosshair_v_volume = self.volume_ax.axvline(x=bar_idx, **crosshair_props)
        self.crosshair_h = self.price_ax.axhline(y=event.ydata, **crosshair_props)
        
        # Get OHLC data for this bar
        bar_data = self.current_data[bar_idx]
        eastern = pytz.timezone('US/Eastern')
        bar_time = datetime.fromtimestamp(bar_data['time'], tz=pytz.UTC).astimezone(eastern)
        
        # Optimized OHLC text formatting
        ohlc_text = f"{bar_time.strftime('%m/%d %H:%M')} O:${bar_data['open']:.2f} H:${bar_data['high']:.2f} L:${bar_data['low']:.2f} C:${bar_data['close']:.2f} V:{bar_data['volume']:,}"
        
        # Add OHLC text with simpler styling
        self.ohlc_text = self.price_ax.text(0.5, 0.99, ohlc_text,
                                           transform=self.price_ax.transAxes,
                                           fontsize=8,
                                           fontfamily='monospace',
                                           color='white',
                                           bbox=dict(boxstyle='round,pad=0.2', 
                                                   facecolor='#2e2e2e', 
                                                   alpha=0.9,
                                                   edgecolor='none'),
                                           verticalalignment='top',
                                           horizontalalignment='center')
        
        # Use optimized drawing for smooth crosshair (120fps throttling active)
        self.draw_idle()
        
    def _on_mouse_leave(self, event):
        """Handle mouse leaving the axes"""
        # Remove crosshair when mouse leaves - safely
        if self.crosshair_v_price:
            try:
                self.crosshair_v_price.remove()
            except:
                pass  # Ignore removal errors
            self.crosshair_v_price = None
        if self.crosshair_v_volume:
            try:
                self.crosshair_v_volume.remove()
            except:
                pass  # Ignore removal errors
            self.crosshair_v_volume = None
        if self.crosshair_h:
            try:
                self.crosshair_h.remove()
            except:
                pass  # Ignore removal errors
            self.crosshair_h = None
        if self.ohlc_text:
            try:
                self.ohlc_text.remove()
            except:
                pass  # Ignore removal errors
            self.ohlc_text = None
            
        # Use optimized drawing for crosshair removal
        self.draw_idle()


class ChartWidget(QWidget):
    """
    Interactive candlestick chart widget for trading analysis
    Uses matplotlib for embedded charts in PyQt6
    """
    
    # Signals
    symbol_changed = pyqtSignal(str)  # Emitted when chart symbol changes
    timeframe_changed = pyqtSignal(str)  # Emitted when timeframe changes
    
    # Price level signals for Order Assistant sync
    chart_entry_changed = pyqtSignal(float)  # Entry price dragged on chart
    chart_stop_loss_changed = pyqtSignal(float)  # Stop loss dragged on chart
    chart_take_profit_changed = pyqtSignal(float)  # Take profit dragged on chart
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chart_manager = chart_data_manager
        self.current_symbol = None
        self.current_timeframe = '5m'
        self.chart_canvas = None
        self.update_timer = QTimer()
        
        # Technical indicator settings
        self.show_emas = True
        self.show_smas = True
        self.show_vwap = True
        
        # Price level management
        self.price_level_manager = None
        
        # Prevent excessive refreshing
        self._last_refresh_time = 0
        self._min_refresh_interval = 2000  # Minimum 2 seconds between refreshes
        
        self.init_ui()
        self.setup_connections()
        self.setup_price_levels()
        
        if not CHARTS_AVAILABLE:
            logger.warning("Charts not available - matplotlib import failed")
            self.show_charts_unavailable()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Chart controls section
        layout.addWidget(self.create_controls_section())
        
        # Chart display area
        layout.addWidget(self.create_chart_section())
        
        # Status section
        layout.addWidget(self.create_status_section())
        
    def create_controls_section(self) -> QWidget:
        """Create compact chart controls section"""
        controls_widget = QWidget()
        controls_widget.setMaximumHeight(40)  # Much smaller height
        controls_widget.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border-bottom: 1px solid #ddd;
            }
        """)
        
        layout = QHBoxLayout(controls_widget)
        layout.setContentsMargins(8, 4, 8, 4)  # Compact margins
        layout.setSpacing(8)  # Tight spacing
        
        # Symbol display (compact)
        self.symbol_label = QLabel("No Symbol")
        self.symbol_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #2196F3;")
        self.symbol_label.setMinimumWidth(80)
        layout.addWidget(self.symbol_label)
        
        # Separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.VLine)
        separator1.setFrameShadow(QFrame.Shadow.Sunken)
        separator1.setMaximumHeight(25)
        layout.addWidget(separator1)
        
        # Timeframe selector (compact)
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(['1m', '3m', '5m', '15m', '1h', '4h', '1d'])
        self.timeframe_combo.setCurrentText('5m')
        self.timeframe_combo.setMaximumWidth(55)
        self.timeframe_combo.setMaximumHeight(28)
        layout.addWidget(self.timeframe_combo)
        
        # Refresh button (compact)
        self.refresh_button = QPushButton("↻")
        self.refresh_button.setToolTip("Refresh chart data")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 3px;
                min-width: 28px;
                max-width: 28px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        layout.addWidget(self.refresh_button)
        
        # Rescale button (compact)
        self.rescale_button = QPushButton("⇲")
        self.rescale_button.setToolTip("Rescale chart to fit data")
        self.rescale_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 3px;
                min-width: 28px;
                max-width: 28px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        layout.addWidget(self.rescale_button)
        
        # Auto-refresh (compact)
        self.auto_refresh_combo = QComboBox()
        self.auto_refresh_combo.addItems(['Off', '5s', '10s', '30s', '1m'])
        self.auto_refresh_combo.setCurrentText('Off')
        self.auto_refresh_combo.setMaximumWidth(50)
        self.auto_refresh_combo.setMaximumHeight(28)
        layout.addWidget(self.auto_refresh_combo)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.VLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        separator2.setMaximumHeight(25)
        layout.addWidget(separator2)
        
        # Technical indicator checkboxes
        self.ema_checkbox = QCheckBox("EMA")
        self.ema_checkbox.setChecked(True)
        self.ema_checkbox.setToolTip("Show EMA (5, 10, 21)")
        self.ema_checkbox.setStyleSheet("font-size: 10px; color: #666;")
        layout.addWidget(self.ema_checkbox)
        
        self.sma_checkbox = QCheckBox("SMA")
        self.sma_checkbox.setChecked(True)
        self.sma_checkbox.setToolTip("Show SMA (50, 100, 200)")
        self.sma_checkbox.setStyleSheet("font-size: 10px; color: #666;")
        layout.addWidget(self.sma_checkbox)
        
        self.vwap_checkbox = QCheckBox("VWAP")
        self.vwap_checkbox.setChecked(True)
        self.vwap_checkbox.setToolTip("Show Volume Weighted Average Price")
        self.vwap_checkbox.setStyleSheet("font-size: 10px; color: #666;")
        layout.addWidget(self.vwap_checkbox)
        
        layout.addStretch()  # Push everything to the left
        
        return controls_widget
        
    def create_chart_section(self) -> QWidget:
        """Create chart display section"""
        chart_container = QWidget()
        chart_container.setMinimumHeight(400)
        chart_container.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border: 1px solid #444;
                border-radius: 5px;
            }
        """)
        
        self.chart_layout = QVBoxLayout(chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)  # No margins for maximum chart space
        
        if CHARTS_AVAILABLE:
            # Create matplotlib canvas
            self.chart_canvas = CandlestickChart()
            
            # Add only the chart canvas (toolbar removed for more space)
            self.chart_layout.addWidget(self.chart_canvas)
        else:
            # Show error message
            error_label = QLabel("matplotlib not available - install with: pip install matplotlib")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setStyleSheet("""
                QLabel {
                    color: #ff6b6b;
                    font-size: 16px;
                    font-weight: bold;
                    border: none;
                }
            """)
            self.chart_layout.addWidget(error_label)
            
        return chart_container
        
    def create_status_section(self) -> QWidget:
        """Create compact status section"""
        status_widget = QWidget()
        status_widget.setMaximumHeight(25)  # Compact height
        status_widget.setStyleSheet("""
            QWidget {
                background-color: #f9f9f9;
                border-top: 1px solid #ddd;
            }
        """)
        
        layout = QHBoxLayout(status_widget)
        layout.setContentsMargins(8, 2, 8, 2)  # Compact margins
        layout.setSpacing(12)
        
        self.status_label = QLabel("Ready for chart data")
        self.status_label.setStyleSheet("color: gray; font-style: italic; font-size: 10px;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        self.bars_count_label = QLabel("0 bars")
        self.bars_count_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.bars_count_label)
        
        # Separator
        separator = QLabel("|")
        separator.setStyleSheet("color: #ccc; font-size: 10px;")
        layout.addWidget(separator)
        
        self.last_update_label = QLabel("Never updated")
        self.last_update_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.last_update_label)
        
        return status_widget
        
    def setup_connections(self):
        """Setup signal connections"""
        self.timeframe_combo.currentTextChanged.connect(self.on_timeframe_changed)
        self.refresh_button.clicked.connect(self.refresh_chart)
        self.rescale_button.clicked.connect(self.rescale_chart)
        self.auto_refresh_combo.currentTextChanged.connect(self.on_auto_refresh_changed)
        self.update_timer.timeout.connect(self.refresh_chart)
        
        # Technical indicator checkboxes
        if hasattr(self, 'ema_checkbox'):
            self.ema_checkbox.toggled.connect(self.on_indicators_changed)
        if hasattr(self, 'sma_checkbox'):
            self.sma_checkbox.toggled.connect(self.on_indicators_changed)
        if hasattr(self, 'vwap_checkbox'):
            self.vwap_checkbox.toggled.connect(self.on_indicators_changed)
    
    def on_indicators_changed(self):
        """Handle technical indicator checkbox changes"""
        try:
            # Update indicator settings
            self.show_emas = self.ema_checkbox.isChecked() if hasattr(self, 'ema_checkbox') else True
            self.show_smas = self.sma_checkbox.isChecked() if hasattr(self, 'sma_checkbox') else True
            self.show_vwap = self.vwap_checkbox.isChecked() if hasattr(self, 'vwap_checkbox') else True
            
            # Refresh chart to show/hide indicators
            if self.current_symbol:
                self.load_chart_data()
                
        except Exception as e:
            logger.error(f"Error handling indicator changes: {e}")
        
    def show_charts_unavailable(self):
        """Show message when charts are not available"""
        self.status_label.setText("Charts unavailable - install matplotlib")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        self.refresh_button.setEnabled(False)
        logger.warning("matplotlib not available - charts disabled")
        
    def set_symbol(self, symbol: str):
        """
        Set the chart symbol and load data
        
        Args:
            symbol: Stock symbol to display
        """
        if not symbol or not CHARTS_AVAILABLE:
            return
            
        try:
            self.current_symbol = symbol.upper()
            self.symbol_label.setText(self.current_symbol)
            self.chart_manager.set_current_symbol(self.current_symbol)
            
            logger.info(f"Chart symbol set to: {self.current_symbol}")
            
            # Clear cache to force fresh data for new symbol
            self.chart_manager.clear_cache()
            
            # Load chart data
            self.load_chart_data()
            
            # Emit signal
            self.symbol_changed.emit(self.current_symbol)
            
        except Exception as e:
            logger.error(f"Error setting chart symbol: {str(e)}")
            self.status_label.setText(f"Error setting symbol: {str(e)}")
            
    def on_timeframe_changed(self, timeframe: str):
        """Handle timeframe change"""
        try:
            if timeframe != self.current_timeframe:
                self.current_timeframe = timeframe
                self.chart_manager.set_current_timeframe(timeframe)
                
                logger.info(f"Chart timeframe changed to: {timeframe}")
                
                # Reload chart data with new timeframe
                if self.current_symbol:
                    self.load_chart_data()
                    
                # Emit signal
                self.timeframe_changed.emit(timeframe)
                
        except Exception as e:
            logger.error(f"Error changing timeframe: {str(e)}")
            
    def on_auto_refresh_changed(self, interval: str):
        """Handle auto-refresh interval change"""
        try:
            # Stop existing timer
            self.update_timer.stop()
            
            if interval == 'Off':
                logger.info("Chart auto-refresh disabled")
            else:
                # Parse interval and start timer
                if interval == '5s':
                    self.update_timer.start(5000)
                elif interval == '10s':
                    self.update_timer.start(10000)
                elif interval == '30s':
                    self.update_timer.start(30000)
                elif interval == '1m':
                    self.update_timer.start(60000)
                    
                logger.info(f"Chart auto-refresh set to: {interval}")
                
        except Exception as e:
            logger.error(f"Error setting auto-refresh: {str(e)}")
            
    def load_chart_data(self):
        """Load and display chart data"""
        if not self.current_symbol or not CHARTS_AVAILABLE:
            return
            
        try:
            self.status_label.setText("Loading chart data...")
            
            # Get chart data from manager
            chart_data = self.chart_manager.get_chart_data(
                self.current_symbol, 
                self.current_timeframe
            )
            
            if chart_data:
                self.update_chart_display(chart_data)
                self.status_label.setText("Chart data loaded successfully")
                self.bars_count_label.setText(f"{len(chart_data)} bars")
                self.last_update_label.setText(f"Updated: {datetime.now().strftime('%H:%M:%S')}")
            else:
                self.status_label.setText("No chart data available")
                self.bars_count_label.setText("0 bars")
                
        except Exception as e:
            logger.error(f"Error loading chart data: {str(e)}")
            self.status_label.setText(f"Error loading data: {str(e)}")
            
    def update_chart_display(self, chart_data: List[Dict[str, Any]]):
        """
        Update the chart display with new data
        
        Args:
            chart_data: List of OHLCV data in lightweight-charts format
        """
        try:
            if not CHARTS_AVAILABLE or not chart_data or not self.chart_canvas:
                return
                
            logger.info(f"Updating chart display: {len(chart_data)} bars for {self.current_symbol} {self.current_timeframe}")
            
            # Store current price levels before plotting
            saved_entry = None
            saved_stop_loss = None
            saved_take_profit = None
            
            if self.price_level_manager:
                saved_entry = self.price_level_manager.entry_price
                saved_stop_loss = self.price_level_manager.stop_loss_price
                saved_take_profit = self.price_level_manager.take_profit_price
            
            # Plot the data using matplotlib with indicator settings
            self.chart_canvas.plot_candlestick_data(
                chart_data, 
                self.current_symbol, 
                self.current_timeframe,
                self.show_emas,
                self.show_smas,
                self.show_vwap
            )
            
            # Restore price levels after plotting
            if self.price_level_manager and (saved_entry or saved_stop_loss or saved_take_profit):
                # Re-set chart references in case axes were recreated
                if isinstance(self.chart_canvas, CandlestickChart):
                    self.price_level_manager.set_chart_references(
                        self.chart_canvas.price_ax,
                        self.chart_canvas
                    )
                    
                    # Reconnect drag events since the canvas was redrawn
                    self.price_level_manager.connect_drag_events()
                
                # Restore the price levels
                self.price_level_manager.update_price_levels(
                    entry=saved_entry,
                    stop_loss=saved_stop_loss,
                    take_profit=saved_take_profit
                )
                
                # Always rescale to include the restored price levels after chart replot
                self._rescale_to_include_price_levels(chart_data, saved_entry, saved_stop_loss, saved_take_profit)
                logger.info("Applied smart rescaling after chart data update with restored price levels")
                
        except Exception as e:
            logger.error(f"Error updating chart display: {str(e)}")
            
    def refresh_chart(self):
        """Refresh chart data with throttling to prevent excessive updates"""
        if not self.current_symbol:
            return
            
        # Throttle refreshes to prevent chart reset issues
        import time
        current_time = time.time() * 1000  # milliseconds
        if current_time - self._last_refresh_time < self._min_refresh_interval:
            logger.debug(f"Refresh throttled - too soon since last refresh")
            return
            
        self._last_refresh_time = current_time
        logger.info(f"Refreshing chart data for {self.current_symbol}")
        
        # Clear cache to force fresh data (but don't clear calculation cache unnecessarily)
        self.chart_manager.clear_cache()
        self.load_chart_data()
            
    def rescale_chart(self):
        """Force rescale chart to fit current data AND price levels"""
        try:
            if not CHARTS_AVAILABLE or not self.chart_canvas:
                return
                
            logger.info("Manual rescale requested")
            
            if isinstance(self.chart_canvas, CandlestickChart) and self.chart_canvas.current_data:
                data = self.chart_canvas.current_data
                
                # Calculate proper limits from actual data
                price_min = min(d['low'] for d in data)
                price_max = max(d['high'] for d in data)
                
                # Include price levels in rescaling calculation
                price_levels = []
                if self.price_level_manager:
                    if self.price_level_manager.entry_price:
                        price_levels.append(self.price_level_manager.entry_price)
                    if self.price_level_manager.stop_loss_price:
                        price_levels.append(self.price_level_manager.stop_loss_price)
                    if self.price_level_manager.take_profit_price:
                        price_levels.append(self.price_level_manager.take_profit_price)
                
                # Expand range to include price levels
                if price_levels:
                    price_min = min(price_min, min(price_levels))
                    price_max = max(price_max, max(price_levels))
                    logger.info(f"Rescale including price levels: {[f'${p:.2f}' for p in price_levels]}")
                
                price_range = price_max - price_min
                y_margin = max(price_range * 0.05, 0.01)
                
                max_volume = max(d['volume'] for d in data)
                
                # Set explicit limits
                self.chart_canvas.price_ax.set_xlim(-0.5, len(data) - 0.5)
                self.chart_canvas.price_ax.set_ylim(price_min - y_margin, price_max + y_margin)
                self.chart_canvas.volume_ax.set_xlim(-0.5, len(data) - 0.5)
                self.chart_canvas.volume_ax.set_ylim(0, max_volume * 1.1)
                
                # Redraw
                self.chart_canvas.draw()
                
                logger.info(f"Chart manually rescaled - New Y limits: {self.chart_canvas.price_ax.get_ylim()}")
                if price_levels:
                    self.status_label.setText("Chart rescaled to fit data and price levels")
                else:
                    self.status_label.setText("Chart rescaled to fit data")
                
        except Exception as e:
            logger.error(f"Error rescaling chart: {str(e)}")
            self.status_label.setText(f"Error rescaling: {str(e)}")
            
    def _check_and_rescale_for_price_levels(self, entry: Optional[float] = None,
                                          stop_loss: Optional[float] = None,
                                          take_profit: Optional[float] = None):
        """Check if price levels are outside current view and rescale if needed"""
        try:
            if not CHARTS_AVAILABLE or not self.chart_canvas or not isinstance(self.chart_canvas, CandlestickChart):
                return
                
            # Get current Y-axis limits
            y_min, y_max = self.chart_canvas.price_ax.get_ylim()
            
            # Collect all price levels
            price_levels = [price for price in [entry, stop_loss, take_profit] if price is not None]
            
            if not price_levels:
                return
                
            # Check if any price level is significantly outside current view (with 10% margin)
            margin = (y_max - y_min) * 0.1  # Increased margin to reduce unnecessary rescaling
            needs_rescale = any(
                price < (y_min - margin) or price > (y_max + margin) 
                for price in price_levels
            )
            
            if needs_rescale:
                logger.info(f"Price levels significantly outside view ({y_min:.2f}-{y_max:.2f}), rescaling...")
                self.rescale_chart()
                
        except Exception as e:
            logger.error(f"Error checking price levels for rescale: {str(e)}")
            
    def _rescale_to_include_price_levels(self, chart_data: List[Dict[str, Any]], 
                                       entry: Optional[float] = None,
                                       stop_loss: Optional[float] = None, 
                                       take_profit: Optional[float] = None):
        """Rescale chart to include both chart data and price levels"""
        try:
            if not CHARTS_AVAILABLE or not self.chart_canvas or not isinstance(self.chart_canvas, CandlestickChart):
                return
                
            if not chart_data:
                return
                
            # Get price range from chart data
            data_price_min = min(d['low'] for d in chart_data)
            data_price_max = max(d['high'] for d in chart_data)
            
            # Include price levels in range calculation
            price_levels = [price for price in [entry, stop_loss, take_profit] if price is not None]
            
            if price_levels:
                # Expand range to include price levels
                combined_min = min(data_price_min, min(price_levels))
                combined_max = max(data_price_max, max(price_levels))
                logger.info(f"Rescaling to include price levels - Data: ${data_price_min:.2f}-${data_price_max:.2f}, "
                          f"Price levels: {[f'${p:.2f}' for p in price_levels]}, "
                          f"Combined: ${combined_min:.2f}-${combined_max:.2f}")
            else:
                # No price levels, use data range
                combined_min = data_price_min
                combined_max = data_price_max
                logger.info(f"Rescaling chart data only: ${combined_min:.2f}-${combined_max:.2f}")
            
            # Calculate appropriate margins
            price_range = combined_max - combined_min
            if price_range < 0.01:  # Handle case where all prices are very close
                price_range = max(combined_max * 0.1, 0.1)  # Use 10% of price or minimum 10 cents
            y_margin = max(price_range * 0.08, 0.01)  # 8% margin or minimum 1 cent for better visibility
            
            # Apply new limits
            self.chart_canvas.price_ax.set_ylim(combined_min - y_margin, combined_max + y_margin)
            
            # Update volume limits (unchanged)
            max_volume = max(d['volume'] for d in chart_data)
            self.chart_canvas.volume_ax.set_ylim(0, max_volume * 1.1)
            
            # Redraw
            self.chart_canvas.draw_idle()
            
            logger.info(f"Chart rescaled with price levels - New Y limits: {self.chart_canvas.price_ax.get_ylim()}")
            
        except Exception as e:
            logger.error(f"Error rescaling chart with price levels: {str(e)}")
            
    def get_current_symbol(self) -> Optional[str]:
        """Get current chart symbol"""
        return self.current_symbol
        
    def get_current_timeframe(self) -> str:
        """Get current chart timeframe"""
        return self.current_timeframe
        
    def setup_price_levels(self):
        """Setup price level management for interactive lines"""
        try:
            if not CHARTS_AVAILABLE or not self.chart_canvas:
                return
                
            # Create price level manager
            self.price_level_manager = PriceLevelManager()
            
            # Set chart references
            if isinstance(self.chart_canvas, CandlestickChart):
                self.price_level_manager.set_chart_references(
                    self.chart_canvas.price_ax,
                    self.chart_canvas
                )
                
                # Connect drag events
                self.price_level_manager.connect_drag_events()
                
                # Connect signals for Order Assistant sync
                self.price_level_manager.entry_changed.connect(self.on_chart_entry_changed)
                self.price_level_manager.stop_loss_changed.connect(self.on_chart_stop_loss_changed)
                self.price_level_manager.take_profit_changed.connect(self.on_chart_take_profit_changed)
                
                # Connect drag completion signal for post-drag rescaling
                self.price_level_manager.drag_completed.connect(self.on_drag_completed)
                
                logger.info("Price level management initialized")
                
        except Exception as e:
            logger.error(f"Error setting up price levels: {e}")
            
    def on_chart_entry_changed(self, price: float):
        """Handle entry price changed from chart"""
        logger.info(f"Chart entry price changed to: ${price:.2f}")
        self.chart_entry_changed.emit(price)
        
    def on_chart_stop_loss_changed(self, price: float):
        """Handle stop loss price changed from chart"""
        logger.info(f"Chart stop loss changed to: ${price:.2f}")
        self.chart_stop_loss_changed.emit(price)
        
    def on_chart_take_profit_changed(self, price: float):
        """Handle take profit price changed from chart"""
        logger.info(f"Chart take profit changed to: ${price:.2f}")
        self.chart_take_profit_changed.emit(price)
        
    def on_drag_completed(self):
        """Handle drag operation completion - check if rescaling is needed"""
        try:
            if not self.price_level_manager:
                return
                
            # Get current price levels
            entry = self.price_level_manager.entry_price
            stop_loss = self.price_level_manager.stop_loss_price
            take_profit = self.price_level_manager.take_profit_price
            
            logger.info(f"Checking post-drag rescale - Entry: {entry}, SL: {stop_loss}, TP: {take_profit}")
            
            # Check if rescaling is needed with current price levels
            self.update_price_levels(entry=entry, stop_loss=stop_loss, take_profit=take_profit, auto_rescale=True)
            
        except Exception as e:
            logger.error(f"Error handling drag completion: {e}")
        
    def update_price_levels(self, entry: Optional[float] = None,
                          stop_loss: Optional[float] = None,
                          take_profit: Optional[float] = None,
                          auto_rescale: bool = False):
        """Update price levels on the chart (called from Order Assistant)"""
        try:
            if self.price_level_manager:
                self.price_level_manager.update_price_levels(entry, stop_loss, take_profit)
                logger.info(f"Updated chart price levels - Entry: {entry}, SL: {stop_loss}, TP: {take_profit}")
                
                # Always check if rescaling is needed when price levels are updated
                if self.chart_canvas and hasattr(self.chart_canvas, 'current_data') and self.chart_canvas.current_data:
                    # Skip rescaling if currently dragging to prevent feedback loops
                    is_dragging = (self.price_level_manager and 
                                 hasattr(self.price_level_manager, 'dragging') and 
                                 self.price_level_manager.dragging)
                    
                    if is_dragging:
                        logger.debug("Skipping rescale during drag operation to prevent feedback loop")
                        return
                    
                    # Check if any price level is outside current view
                    y_min, y_max = self.chart_canvas.price_ax.get_ylim()
                    price_levels = [price for price in [entry, stop_loss, take_profit] if price is not None]
                    
                    needs_rescale = False
                    if price_levels:
                        # Check if any price level is outside current view (with small buffer)
                        y_range = y_max - y_min
                        buffer = y_range * 0.05  # 5% buffer to ensure good visibility
                        
                        for price in price_levels:
                            # More aggressive rescaling - trigger if price is outside or very close to edges
                            if price <= y_min or price >= y_max or price < (y_min + buffer) or price > (y_max - buffer):
                                needs_rescale = True
                                logger.info(f"Price level ${price:.2f} outside/near view ({y_min:.2f}-{y_max:.2f}), rescaling needed")
                                break
                    
                    if needs_rescale or auto_rescale:
                        # Use smart rescaling that includes both data and price levels
                        self._rescale_to_include_price_levels(self.chart_canvas.current_data, entry, stop_loss, take_profit)
                
        except Exception as e:
            logger.error(f"Error updating price levels: {e}")
            
    def clear_price_levels(self):
        """Clear all price levels from chart"""
        try:
            if self.price_level_manager:
                self.price_level_manager.clear_price_levels()
                logger.info("Cleared all price levels from chart")
        except Exception as e:
            logger.error(f"Error clearing price levels: {e}")
        
    def cleanup(self):
        """Cleanup resources"""
        try:
            self.update_timer.stop()
            if self.chart_canvas:
                plt.close('all')  # Close all matplotlib figures
        except Exception as e:
            logger.error(f"Error during chart cleanup: {str(e)}")