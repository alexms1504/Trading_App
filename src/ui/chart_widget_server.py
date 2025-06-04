"""
Chart Widget using lightweight-charts in server mode
Embeds the chart using a local server approach
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import threading
import time
import socket
from contextlib import closing

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QFont

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    WEB_ENGINE_AVAILABLE = False

try:
    from lightweight_charts import Chart
    import pandas as pd
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False

from src.utils.logger import logger
from src.core.chart_data_manager import chart_data_manager


def find_free_port():
    """Find a free port on localhost"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


class ChartServer:
    """Manages the lightweight-charts server instance"""
    
    def __init__(self):
        self.chart = None
        self.port = None
        self.server_thread = None
        self.is_running = False
        
    def start(self):
        """Start the chart server"""
        if self.is_running:
            return self.port
            
        try:
            # Find a free port
            self.port = find_free_port()
            
            # Create chart instance
            self.chart = Chart(
                width=800,
                height=600,
                toolbox=True,
                inner_width=1.0,
                inner_height=0.8  # Leave space for volume
            )
            
            # Configure chart appearance
            self.chart.layout(
                background_color='#1e1e1e',
                text_color='#d1d4dc',
                font_size=12,
                font_family='Trebuchet MS'
            )
            
            self.chart.grid(
                vert_enabled=True,
                horz_enabled=True,
                color='#2B2B43'
            )
            
            self.chart.candle_style(
                up_color='#26a69a',
                down_color='#ef5350',
                border_up_color='#26a69a',
                border_down_color='#ef5350',
                wick_up_color='#26a69a',
                wick_down_color='#ef5350'
            )
            
            # Show the chart in server mode
            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True
            )
            self.server_thread.start()
            
            # Give server time to start
            time.sleep(0.5)
            
            self.is_running = True
            logger.info(f"Chart server started on port {self.port}")
            return self.port
            
        except Exception as e:
            logger.error(f"Error starting chart server: {str(e)}")
            return None
            
    def _run_server(self):
        """Run the chart server (blocking)"""
        try:
            self.chart.show(port=self.port, block=True)
        except Exception as e:
            logger.error(f"Chart server error: {str(e)}")
            
    def update_data(self, chart_data: List[Dict[str, Any]], symbol: str, timeframe: str):
        """Update chart with new data"""
        if not self.chart or not self.is_running:
            return False
            
        try:
            # Convert to DataFrame
            df = pd.DataFrame(chart_data)
            
            # Convert timestamp to datetime string
            df['time'] = pd.to_datetime(df['time'], unit='s').dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Update the chart
            self.chart.set(df[['time', 'open', 'high', 'low', 'close']])
            
            # Add volume as subchart
            if 'volume' in df.columns:
                volume_chart = self.chart.create_subchart(
                    width=1.0,
                    height=0.2,
                    sync=True
                )
                
                # Prepare volume data
                volume_df = df[['time', 'volume']].copy()
                
                # Create histogram for volume
                histogram = volume_chart.create_histogram(
                    color='rgba(76, 175, 80, 0.5)',
                    price_label=False
                )
                histogram.set(volume_df)
            
            # Update chart title
            self.chart.watermark(f'{symbol} - {timeframe}')
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating chart data: {str(e)}")
            return False
            
    def stop(self):
        """Stop the chart server"""
        if self.chart and self.is_running:
            try:
                self.chart.exit()
                self.is_running = False
                logger.info("Chart server stopped")
            except Exception as e:
                logger.error(f"Error stopping chart server: {str(e)}")


class ChartWidget(QWidget):
    """
    Interactive candlestick chart widget using lightweight-charts server mode
    """
    
    # Signals
    symbol_changed = pyqtSignal(str)
    timeframe_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chart_manager = chart_data_manager
        self.current_symbol = None
        self.current_timeframe = '5m'
        self.web_view = None
        self.chart_server = None
        self.update_timer = QTimer()
        
        self.init_ui()
        self.setup_connections()
        
        if not WEB_ENGINE_AVAILABLE or not CHARTS_AVAILABLE:
            self.show_charts_unavailable()
        else:
            self.start_chart_server()
        
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
        
        layout.addStretch()
        
        return controls_widget
        
    def create_chart_section(self) -> QWidget:
        """Create chart display section"""
        chart_container = QWidget()
        chart_container.setMinimumHeight(400)
        
        self.chart_layout = QVBoxLayout(chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        
        if WEB_ENGINE_AVAILABLE and CHARTS_AVAILABLE:
            # Create web view for embedded chart
            self.web_view = QWebEngineView()
            self.chart_layout.addWidget(self.web_view)
        else:
            # Show error message
            error_label = QLabel("Charts not available - install dependencies")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setStyleSheet("""
                QLabel {
                    color: #ff6b6b;
                    font-size: 16px;
                    font-weight: bold;
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
        
    def start_chart_server(self):
        """Start the lightweight-charts server"""
        if not CHARTS_AVAILABLE:
            return
            
        try:
            self.chart_server = ChartServer()
            port = self.chart_server.start()
            
            if port and self.web_view:
                # Load the chart URL in the web view
                url = f"http://localhost:{port}"
                self.web_view.load(QUrl(url))
                logger.info(f"Chart loaded from: {url}")
                self.status_label.setText("Chart server running")
                
        except Exception as e:
            logger.error(f"Error starting chart server: {str(e)}")
            self.status_label.setText("Chart server error")
        
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
                self.status_label.setText("Chart data loaded")
                self.bars_count_label.setText(f"{len(chart_data)} bars")
                self.last_update_label.setText(f"Updated: {datetime.now().strftime('%H:%M:%S')}")
            else:
                self.status_label.setText("No chart data available")
                self.bars_count_label.setText("0 bars")
                
        except Exception as e:
            logger.error(f"Error loading chart data: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")
            
    def update_chart_display(self, chart_data: List[Dict[str, Any]]):
        """Update the chart display with new data"""
        try:
            if not CHARTS_AVAILABLE or not chart_data or not self.chart_server:
                return
                
            logger.info(f"Updating chart: {len(chart_data)} bars for {self.current_symbol} {self.current_timeframe}")
            
            # Update chart via server
            success = self.chart_server.update_data(
                chart_data,
                self.current_symbol,
                self.current_timeframe
            )
            
            if not success:
                logger.error("Failed to update chart data")
                
        except Exception as e:
            logger.error(f"Error updating chart display: {str(e)}")
            
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
        
    def cleanup(self):
        """Cleanup resources"""
        try:
            self.update_timer.stop()
            
            # Stop chart server
            if self.chart_server:
                self.chart_server.stop()
                
        except Exception as e:
            logger.error(f"Error during chart cleanup: {str(e)}")