"""
Chart Widget using lightweight-charts QtChart
Properly embedded in PyQt6 using the official QtChart widget
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

try:
    from lightweight_charts.widgets import QtChart
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False
    print("Warning: lightweight-charts QtChart not available")

from src.utils.logger import logger
from src.core.chart_data_manager import chart_data_manager


class ChartWidget(QWidget):
    """
    Interactive candlestick chart widget using lightweight-charts QtChart
    Fully embedded in PyQt6
    """
    
    # Signals
    symbol_changed = pyqtSignal(str)
    timeframe_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chart_manager = chart_data_manager
        self.current_symbol = None
        self.current_timeframe = '5m'
        self.chart = None
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
        controls_widget.setMaximumHeight(40)
        controls_widget.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border-bottom: 1px solid #ddd;
            }
        """)
        
        layout = QHBoxLayout(controls_widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Symbol display
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
        
        # Timeframe selector
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(['1m', '3m', '5m', '15m', '1h', '4h', '1d'])
        self.timeframe_combo.setCurrentText('5m')
        self.timeframe_combo.setMaximumWidth(55)
        self.timeframe_combo.setMaximumHeight(28)
        layout.addWidget(self.timeframe_combo)
        
        # Refresh button
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
        
        # Auto-refresh
        self.auto_refresh_combo = QComboBox()
        self.auto_refresh_combo.addItems(['Off', '5s', '10s', '30s', '1m'])
        self.auto_refresh_combo.setCurrentText('Off')
        self.auto_refresh_combo.setMaximumWidth(50)
        self.auto_refresh_combo.setMaximumHeight(28)
        layout.addWidget(self.auto_refresh_combo)
        
        # Test button
        self.test_button = QPushButton("Test")
        self.test_button.setToolTip("Load test data")
        self.test_button.setMaximumWidth(50)
        self.test_button.setMaximumHeight(28)
        self.test_button.clicked.connect(self.load_test_data)
        layout.addWidget(self.test_button)
        
        layout.addStretch()
        
        return controls_widget
        
    def create_chart_section(self) -> QWidget:
        """Create chart display section"""
        chart_container = QWidget()
        chart_container.setMinimumHeight(400)
        
        self.chart_layout = QVBoxLayout(chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        
        if CHARTS_AVAILABLE:
            # Create the QtChart widget
            try:
                self.chart = QtChart(self)
                logger.info("QtChart created successfully")
            except Exception as e:
                logger.error(f"Error creating QtChart: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                self.chart = None
                error_label = QLabel(f"Error creating chart: {str(e)}")
                error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                error_label.setStyleSheet("color: #ff6b6b; font-size: 14px; background-color: #1e1e1e;")
                self.chart_layout.addWidget(error_label)
                return chart_container
            
            # Configure chart appearance with minimal settings first
            try:
                self.chart.layout(background_color='#1e1e1e')
                logger.info("Chart layout configured")
            except Exception as e:
                logger.error(f"Error configuring chart layout: {e}")
            
            # Set chart size
            try:
                self.chart.resize(800, 500)
                logger.info("Chart resized")
            except Exception as e:
                logger.error(f"Error resizing chart: {e}")
            
            # Add the WebView from QtChart to our layout
            try:
                webview = self.chart.get_webview()
                self.chart_layout.addWidget(webview)
                logger.info("Chart webview added to layout")
            except Exception as e:
                logger.error(f"Error adding webview: {str(e)}")
                error_label = QLabel(f"Error displaying chart: {str(e)}")
                error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                error_label.setStyleSheet("color: #ff6b6b; font-size: 14px; background-color: #1e1e1e;")
                self.chart_layout.addWidget(error_label)
            
            # Don't initialize empty chart for now - it might cause crashes
            # QTimer.singleShot(1000, self.show_empty_chart)
            logger.info("Chart initialization complete - skipping empty chart setup")
        else:
            # Show error message
            error_label = QLabel("lightweight-charts QtChart not available")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setStyleSheet("""
                QLabel {
                    color: #ff6b6b;
                    font-size: 16px;
                    font-weight: bold;
                    border: none;
                    background-color: #1e1e1e;
                }
            """)
            self.chart_layout.addWidget(error_label)
            
        return chart_container
        
    def create_status_section(self) -> QWidget:
        """Create compact status section"""
        status_widget = QWidget()
        status_widget.setMaximumHeight(25)
        status_widget.setStyleSheet("""
            QWidget {
                background-color: #f9f9f9;
                border-top: 1px solid #ddd;
            }
        """)
        
        layout = QHBoxLayout(status_widget)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(12)
        
        self.status_label = QLabel("Ready for chart data")
        self.status_label.setStyleSheet("color: gray; font-style: italic; font-size: 10px;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        self.bars_count_label = QLabel("0 bars")
        self.bars_count_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.bars_count_label)
        
        separator = QLabel("|")
        separator.setStyleSheet("color: #ccc; font-size: 10px;")
        layout.addWidget(separator)
        
        self.last_update_label = QLabel("Never updated")
        self.last_update_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.last_update_label)
        
        return status_widget
        
    def show_empty_chart(self):
        """Show empty chart state"""
        try:
            if self.chart:
                logger.info("Setting empty chart state")
                # Create minimal empty DataFrame with required columns
                empty_df = pd.DataFrame(columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                self.chart.set(empty_df)
                logger.info("Empty chart data set")
                self.chart.watermark('Select a symbol to display chart')
                logger.info("Chart watermark set")
        except Exception as e:
            logger.error(f"Error in show_empty_chart: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
    def setup_connections(self):
        """Setup signal connections"""
        self.timeframe_combo.currentTextChanged.connect(self.on_timeframe_changed)
        self.refresh_button.clicked.connect(self.refresh_chart)
        self.auto_refresh_combo.currentTextChanged.connect(self.on_auto_refresh_changed)
        self.update_timer.timeout.connect(self.refresh_chart)
        
    def show_charts_unavailable(self):
        """Show message when charts are not available"""
        self.status_label.setText("Charts unavailable")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        self.refresh_button.setEnabled(False)
        logger.warning("QtChart not available - charts disabled")
        
    def set_symbol(self, symbol: str):
        """Set the chart symbol and load data"""
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
                
                if self.current_symbol:
                    self.load_chart_data()
                    
                self.timeframe_changed.emit(timeframe)
                
        except Exception as e:
            logger.error(f"Error changing timeframe: {str(e)}")
            
    def on_auto_refresh_changed(self, interval: str):
        """Handle auto-refresh interval change"""
        try:
            self.update_timer.stop()
            
            if interval == 'Off':
                logger.info("Chart auto-refresh disabled")
            else:
                intervals = {'5s': 5000, '10s': 10000, '30s': 30000, '1m': 60000}
                if interval in intervals:
                    self.update_timer.start(intervals[interval])
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
        """Update the chart display with new data"""
        try:
            if not CHARTS_AVAILABLE or not chart_data or not self.chart:
                return
                
            logger.info(f"Updating chart display: {len(chart_data)} bars for {self.current_symbol} {self.current_timeframe}")
            
            # Convert to DataFrame
            df = pd.DataFrame(chart_data)
            
            # Convert timestamp to datetime for lightweight-charts
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # Ensure proper column names and order
            df = df[['time', 'open', 'high', 'low', 'close', 'volume']]
            
            # Update the chart
            logger.info(f"Setting chart data: {len(df)} rows")
            logger.info(f"Data columns: {df.columns.tolist()}")
            logger.info(f"First row: {df.iloc[0].to_dict() if len(df) > 0 else 'No data'}")
            
            self.chart.set(df)
            logger.info("Chart data set successfully")
            
            # Update watermark with symbol info
            self.chart.watermark(f'{self.current_symbol} - {self.current_timeframe}')
            logger.info("Chart watermark updated")
            
            # Add volume if not already configured
            if hasattr(self.chart, 'volume_config'):
                self.chart.volume_config(
                    up_color='rgba(38, 166, 154, 0.5)',
                    down_color='rgba(239, 83, 80, 0.5)'
                )
                
        except Exception as e:
            logger.error(f"Error updating chart display: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
    def refresh_chart(self):
        """Refresh chart data"""
        if self.current_symbol:
            self.chart_manager.clear_cache()
            self.load_chart_data()
            
    def get_current_symbol(self) -> Optional[str]:
        """Get current chart symbol"""
        return self.current_symbol
        
    def get_current_timeframe(self) -> str:
        """Get current chart timeframe"""
        return self.current_timeframe
        
    def load_test_data(self):
        """Load test data for debugging"""
        try:
            logger.info("Loading test chart data...")
            
            # Create simple test data
            import random
            from datetime import timedelta
            
            data = []
            base_time = datetime.now() - timedelta(hours=24)
            base_price = 150.0
            
            for i in range(50):
                time = base_time + timedelta(minutes=i*5)
                change = random.uniform(-1, 1)
                open_price = base_price + change
                close_price = open_price + random.uniform(-0.5, 0.5)
                high_price = max(open_price, close_price) + random.uniform(0, 0.3)
                low_price = min(open_price, close_price) - random.uniform(0, 0.3)
                volume = random.randint(100000, 500000)
                
                data.append({
                    'time': time,
                    'open': round(open_price, 2),
                    'high': round(high_price, 2),
                    'low': round(low_price, 2),
                    'close': round(close_price, 2),
                    'volume': volume
                })
                
                base_price = close_price
            
            # Convert to DataFrame and update chart
            df = pd.DataFrame(data)
            logger.info(f"Test data created: {len(df)} rows")
            
            self.current_symbol = "TEST"
            self.symbol_label.setText("TEST")
            
            # Update chart directly
            self.chart.set(df)
            self.chart.watermark("TEST DATA")
            
            self.status_label.setText("Test data loaded")
            self.bars_count_label.setText(f"{len(df)} bars")
            
        except Exception as e:
            logger.error(f"Error loading test data: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self.status_label.setText(f"Test error: {str(e)}")
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            self.update_timer.stop()
            if self.chart:
                # QtChart cleanup if needed
                pass
        except Exception as e:
            logger.error(f"Error during chart cleanup: {str(e)}")