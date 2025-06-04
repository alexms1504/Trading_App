"""
Chart Widget
Interactive candlestick chart using lightweight-charts-python
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QGroupBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

try:
    from lightweight_charts import Chart
    import pandas as pd
    CHARTS_AVAILABLE = True
    # Try to import QWebEngineView for embedding
    try:
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebEngineCore import QWebEnginePage
        WEB_ENGINE_AVAILABLE = True
    except ImportError:
        WEB_ENGINE_AVAILABLE = False
        print("Warning: QWebEngineView not available. Chart embedding may not work.")
except ImportError:
    CHARTS_AVAILABLE = False
    WEB_ENGINE_AVAILABLE = False
    print("Warning: lightweight-charts-python not available. Charts will be disabled.")

from src.utils.logger import logger
from src.core.chart_data_manager import chart_data_manager


class ChartWidget(QWidget):
    """
    Interactive candlestick chart widget for trading analysis
    Uses lightweight-charts-python for professional chart display
    """
    
    # Signals
    symbol_changed = pyqtSignal(str)  # Emitted when chart symbol changes
    timeframe_changed = pyqtSignal(str)  # Emitted when timeframe changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chart_manager = chart_data_manager
        self.current_symbol = None
        self.current_timeframe = '5m'
        self.chart = None
        self.candlestick_series = None
        self.volume_series = None
        self.update_timer = QTimer()
        
        self.init_ui()
        self.setup_connections()
        
        if not CHARTS_AVAILABLE:
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
        
        # Auto-refresh (compact)
        self.auto_refresh_combo = QComboBox()
        self.auto_refresh_combo.addItems(['Off', '5s', '10s', '30s', '1m'])
        self.auto_refresh_combo.setCurrentText('Off')
        self.auto_refresh_combo.setMaximumWidth(50)
        self.auto_refresh_combo.setMaximumHeight(28)
        layout.addWidget(self.auto_refresh_combo)
        
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
        
        layout = QVBoxLayout(chart_container)
        layout.setContentsMargins(2, 2, 2, 2)  # Minimal margins for chart
        
        if CHARTS_AVAILABLE:
            # Initialize chart placeholder
            self.chart_placeholder = QLabel("Select a symbol to display chart")
            self.chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.chart_placeholder.setStyleSheet("""
                QLabel {
                    color: #888;
                    font-size: 16px;
                    font-style: italic;
                    border: none;
                }
            """)
            layout.addWidget(self.chart_placeholder)
            
            # Store layout reference for chart replacement
            self.chart_layout = layout
        else:
            # Show error message
            error_label = QLabel("lightweight-charts-python not available")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setStyleSheet("""
                QLabel {
                    color: #ff6b6b;
                    font-size: 16px;
                    font-weight: bold;
                    border: none;
                }
            """)
            layout.addWidget(error_label)
            
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
        self.auto_refresh_combo.currentTextChanged.connect(self.on_auto_refresh_changed)
        self.update_timer.timeout.connect(self.refresh_chart)
        
    def show_charts_unavailable(self):
        """Show message when charts are not available"""
        self.status_label.setText("Charts unavailable - install lightweight-charts-python")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        self.refresh_button.setEnabled(False)
        logger.warning("lightweight-charts-python not available - charts disabled")
        
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
            if not CHARTS_AVAILABLE or not chart_data:
                return
                
            logger.info(f"Updating chart display: {len(chart_data)} bars for {self.current_symbol} {self.current_timeframe}")
            
            # Create or update the chart
            self._create_chart(chart_data)
                
        except Exception as e:
            logger.error(f"Error updating chart display: {str(e)}")
            
    def _create_chart(self, chart_data: List[Dict[str, Any]]):
        """
        Create the lightweight-charts chart with data
        
        Args:
            chart_data: Chart data in lightweight-charts format
        """
        try:
            # Remove placeholder if it exists
            if hasattr(self, 'chart_placeholder') and self.chart_placeholder:
                self.chart_layout.removeWidget(self.chart_placeholder)
                self.chart_placeholder.deleteLater()
                self.chart_placeholder = None
            
            # Clean up existing chart
            if self.chart:
                self.chart.exit()
                self.chart = None
                
            # Convert chart data to pandas DataFrame
            df = self._convert_to_dataframe(chart_data)
            
            # Create new chart with better configuration
            self.chart = Chart(
                width=1000,  # Larger default width
                height=600,  # Larger default height
                toolbox=True,
                inner_width=1.0,
                inner_height=0.85,  # Leave 15% for volume
                scale_candles_only=False
            )
            
            # Set chart data (lightweight-charts uses the main chart for candlestick)
            self.chart.set(df)
            
            # Configure chart appearance
            self.chart.layout(background_color='#1e1e1e', text_color='#ffffff')
            self.chart.grid(vert_enabled=True, horz_enabled=True, color='#444444')
            self.chart.legend(visible=True, font_size=12)
            
            # Add volume as histogram if available
            if 'volume' in df.columns:
                self._add_volume_histogram(df)
            
            # Configure volume appearance
            self.chart.volume_config(
                up_color='rgba(38, 166, 154, 0.5)',
                down_color='rgba(239, 83, 80, 0.5)'
            )
            
            # Show the chart as a separate window for now
            # TODO: Future enhancement - embed using platform-specific window embedding
            self.chart.show(block=False)
            
            logger.info(f"Chart created successfully for {self.current_symbol}")
            
        except Exception as e:
            logger.error(f"Error creating chart: {str(e)}")
            import traceback
            logger.error(f"Chart creation traceback: {traceback.format_exc()}")
            # Fallback to text display
            self._show_fallback_data(chart_data)
            
    def _convert_to_dataframe(self, chart_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Convert chart data to pandas DataFrame
        
        Args:
            chart_data: List of OHLCV dictionaries
            
        Returns:
            pandas DataFrame with proper format for lightweight-charts
        """
        try:
            # Convert timestamps to datetime strings for lightweight-charts
            formatted_data = []
            for bar in chart_data:
                formatted_bar = {
                    'time': pd.to_datetime(bar['time'], unit='s').strftime('%Y-%m-%d %H:%M:%S'),
                    'open': float(bar['open']),
                    'high': float(bar['high']),
                    'low': float(bar['low']),
                    'close': float(bar['close']),
                    'volume': int(bar['volume']) if bar.get('volume') else 0
                }
                formatted_data.append(formatted_bar)
            
            df = pd.DataFrame(formatted_data)
            logger.info(f"Converted {len(df)} bars to DataFrame")
            return df
            
        except Exception as e:
            logger.error(f"Error converting to DataFrame: {str(e)}")
            return pd.DataFrame()
            
    def _add_volume_histogram(self, df: pd.DataFrame):
        """
        Add volume histogram to chart
        
        Args:
            df: DataFrame with volume data
        """
        try:
            # Create volume subchart with smaller height
            volume_chart = self.chart.create_subchart(height=0.15)
            
            # Prepare volume data - lightweight-charts expects specific format for histograms
            volume_data = df[['time', 'volume']].copy()
            volume_data = volume_data.rename(columns={'volume': 'value'})
            
            # Set volume data as histogram
            volume_chart.create_histogram(color='rgba(76, 175, 80, 0.5)')
            volume_chart.set(volume_data)
            
            logger.info("Volume histogram added to chart")
            
        except Exception as e:
            logger.error(f"Error adding volume histogram: {str(e)}")
            logger.info("Continuing without volume display")
            
    def _show_fallback_data(self, chart_data: List[Dict[str, Any]]):
        """
        Show fallback text when chart creation fails
        
        Args:
            chart_data: Chart data to display as text
        """
        try:
            fallback_label = QLabel()
            fallback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fallback_label.setStyleSheet("""
                QLabel {
                    color: #888;
                    font-size: 12px;
                    font-family: monospace;
                    border: none;
                }
            """)
            
            if chart_data:
                first_bar = chart_data[0]
                last_bar = chart_data[-1]
                fallback_text = (
                    f"{self.current_symbol} ({self.current_timeframe})\n"
                    f"{len(chart_data)} bars loaded\n"
                    f"From: {datetime.fromtimestamp(first_bar['time']).strftime('%Y-%m-%d %H:%M')}\n"
                    f"To: {datetime.fromtimestamp(last_bar['time']).strftime('%Y-%m-%d %H:%M')}\n"
                    f"Last Close: ${last_bar['close']:.2f}\n"
                    f"Last Volume: {last_bar['volume']:,}"
                )
            else:
                fallback_text = "No chart data available"
                
            fallback_label.setText(fallback_text)
            self.chart_layout.addWidget(fallback_label)
            
        except Exception as e:
            logger.error(f"Error showing fallback data: {str(e)}")
            
    def refresh_chart(self):
        """Refresh chart data"""
        if self.current_symbol:
            # Clear cache to force fresh data
            self.chart_manager.clear_cache()
            self.load_chart_data()
            
    def get_current_symbol(self) -> Optional[str]:
        """Get current chart symbol"""
        return self.current_symbol
        
    def get_current_timeframe(self) -> str:
        """Get current chart timeframe"""
        return self.current_timeframe
        
    def cleanup(self):
        """Cleanup resources"""
        try:
            self.update_timer.stop()
            if self.chart:
                self.chart.exit()
                self.chart = None
            self.candlestick_series = None
            self.volume_series = None
        except Exception as e:
            logger.error(f"Error during chart cleanup: {str(e)}")