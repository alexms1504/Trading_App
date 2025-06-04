"""
Chart Widget with Embedded lightweight-charts
Uses QWebEngineView to embed the chart directly in the PyQt6 window
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import os
import tempfile
import threading
import time

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QFont

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebChannel import QWebChannel
    from PyQt6.QtCore import QObject, pyqtSlot
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    WEB_ENGINE_AVAILABLE = False
    print("Warning: QWebEngineView not available. Install with: pip install PyQt6-WebEngine")

try:
    from lightweight_charts import Chart
    import pandas as pd
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False
    print("Warning: lightweight-charts-python not available.")

from src.utils.logger import logger
from src.core.chart_data_manager import chart_data_manager


class ChartBridge(QObject):
    """Bridge object for communication between Python and JavaScript"""
    update_chart = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
    @pyqtSlot(str)
    def log_from_js(self, message):
        """Receive log messages from JavaScript"""
        logger.info(f"JS: {message}")


class ChartWidget(QWidget):
    """
    Interactive candlestick chart widget using lightweight-charts
    Embedded directly in PyQt6 using QWebEngineView
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
        self.chart_bridge = None
        self.update_timer = QTimer()
        self.chart_html_path = None
        self.chart_server = None
        
        self.init_ui()
        self.setup_connections()
        
        if not WEB_ENGINE_AVAILABLE or not CHARTS_AVAILABLE:
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
            
            # Create bridge for Python-JS communication
            self.chart_bridge = ChartBridge()
            self.chart_bridge.update_chart.connect(self.on_update_chart_data)
            
            # Initialize with empty chart
            self.create_chart_html()
        else:
            # Show error message
            error_label = QLabel("QWebEngineView or lightweight-charts not available")
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
        
    def create_chart_html(self):
        """Create HTML file with lightweight-charts setup"""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading Chart</title>
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body {
            margin: 0;
            padding: 0;
            background-color: #1e1e1e;
            overflow: hidden;
        }
        #chart {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
        }
    </style>
</head>
<body>
    <div id="chart"></div>
    <script>
        // Create chart
        const chartOptions = {
            layout: {
                background: { type: 'solid', color: '#1e1e1e' },
                textColor: '#d1d4dc',
            },
            grid: {
                vertLines: { color: '#2B2B43' },
                horzLines: { color: '#2B2B43' },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
            },
            rightPriceScale: {
                borderColor: '#2B2B43',
            },
            timeScale: {
                borderColor: '#2B2B43',
                timeVisible: true,
                secondsVisible: false,
            },
        };
        
        const chart = LightweightCharts.createChart(document.getElementById('chart'), chartOptions);
        
        // Add candlestick series
        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        });
        
        // Add volume series
        const volumeSeries = chart.addHistogramSeries({
            color: '#26a69a',
            priceFormat: {
                type: 'volume',
            },
            priceScaleId: '',
            scaleMargins: {
                top: 0.8,
                bottom: 0,
            },
        });
        
        // Function to update chart data
        function updateChart(jsonData) {
            try {
                const data = JSON.parse(jsonData);
                
                // Prepare candlestick data
                const candleData = data.map(item => ({
                    time: item.time,
                    open: item.open,
                    high: item.high,
                    low: item.low,
                    close: item.close,
                }));
                
                // Prepare volume data
                const volumeData = data.map(item => ({
                    time: item.time,
                    value: item.volume,
                    color: item.close >= item.open ? '#26a69a80' : '#ef535080',
                }));
                
                // Update series
                candlestickSeries.setData(candleData);
                volumeSeries.setData(volumeData);
                
                // Fit content
                chart.timeScale().fitContent();
                
                console.log('Chart updated with ' + data.length + ' bars');
            } catch (e) {
                console.error('Error updating chart:', e);
            }
        }
        
        // Handle window resize
        window.addEventListener('resize', () => {
            chart.applyOptions({
                width: window.innerWidth,
                height: window.innerHeight,
            });
        });
        
        // Initial resize
        chart.applyOptions({
            width: window.innerWidth,
            height: window.innerHeight,
        });
        
        // Expose updateChart to Python
        window.updateChart = updateChart;
    </script>
</body>
</html>
"""
        
        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html_content)
            self.chart_html_path = f.name
            
        # Load HTML in web view
        if self.web_view:
            self.web_view.load(QUrl.fromLocalFile(self.chart_html_path))
            logger.info(f"Chart HTML loaded from: {self.chart_html_path}")
        
    def setup_connections(self):
        """Setup signal connections"""
        self.timeframe_combo.currentTextChanged.connect(self.on_timeframe_changed)
        self.refresh_button.clicked.connect(self.refresh_chart)
        self.auto_refresh_combo.currentTextChanged.connect(self.on_auto_refresh_changed)
        self.update_timer.timeout.connect(self.refresh_chart)
        
    def show_charts_unavailable(self):
        """Show message when charts are not available"""
        self.status_label.setText("Charts unavailable - install PyQt6-WebEngine")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        self.refresh_button.setEnabled(False)
        logger.warning("QWebEngineView not available - charts disabled")
        
    def set_symbol(self, symbol: str):
        """Set the chart symbol and load data"""
        if not symbol or not WEB_ENGINE_AVAILABLE or not CHARTS_AVAILABLE:
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
        if not self.current_symbol or not WEB_ENGINE_AVAILABLE or not CHARTS_AVAILABLE:
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
            if not WEB_ENGINE_AVAILABLE or not CHARTS_AVAILABLE or not chart_data:
                return
                
            logger.info(f"Updating chart display: {len(chart_data)} bars for {self.current_symbol} {self.current_timeframe}")
            
            # Convert data to JSON
            json_data = json.dumps(chart_data)
            
            # Update chart via JavaScript
            if self.web_view and self.web_view.page():
                js_code = f"if (window.updateChart) {{ window.updateChart('{json_data}'); }}"
                self.web_view.page().runJavaScript(js_code)
                
        except Exception as e:
            logger.error(f"Error updating chart display: {str(e)}")
            
    def on_update_chart_data(self, json_data: str):
        """Handle chart data update from bridge"""
        try:
            chart_data = json.loads(json_data)
            self.update_chart_display(chart_data)
        except Exception as e:
            logger.error(f"Error processing chart data from bridge: {str(e)}")
            
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
            
            # Clean up temporary HTML file
            if self.chart_html_path and os.path.exists(self.chart_html_path):
                os.unlink(self.chart_html_path)
                
        except Exception as e:
            logger.error(f"Error during chart cleanup: {str(e)}")