"""
Chart Widget using Plotly for embedded interactive charts
Provides TradingView-like charts embedded directly in PyQt6
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import json

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
    print("Warning: QWebEngineView not available. Install with: pip install PyQt6-WebEngine")

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import pandas as pd
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("Warning: Plotly not available. Install with: pip install plotly pandas")

from src.utils.logger import logger
from src.core.chart_data_manager import chart_data_manager


class ChartWidget(QWidget):
    """
    Interactive candlestick chart widget using Plotly
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
        self.update_timer = QTimer()
        
        self.init_ui()
        self.setup_connections()
        
        if not WEB_ENGINE_AVAILABLE or not PLOTLY_AVAILABLE:
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
        chart_container.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border: 1px solid #444;
                border-radius: 5px;
            }
        """)
        
        self.chart_layout = QVBoxLayout(chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        
        if WEB_ENGINE_AVAILABLE and PLOTLY_AVAILABLE:
            # Create web view for embedded chart
            self.web_view = QWebEngineView()
            self.web_view.setStyleSheet("background-color: #1e1e1e;")
            self.chart_layout.addWidget(self.web_view)
            
            # Show initial empty state
            self.show_empty_chart()
        else:
            # Show error message
            error_label = QLabel("Install PyQt6-WebEngine and plotly for charts")
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
        """Show empty chart placeholder"""
        if not self.web_view:
            return
            
        html = """
        <html>
        <head>
            <style>
                body {
                    background-color: #1e1e1e;
                    color: #888;
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }
            </style>
        </head>
        <body>
            <div>Select a symbol to display chart</div>
        </body>
        </html>
        """
        self.web_view.setHtml(html)
        
    def setup_connections(self):
        """Setup signal connections"""
        self.timeframe_combo.currentTextChanged.connect(self.on_timeframe_changed)
        self.refresh_button.clicked.connect(self.refresh_chart)
        self.auto_refresh_combo.currentTextChanged.connect(self.on_auto_refresh_changed)
        self.update_timer.timeout.connect(self.refresh_chart)
        
    def show_charts_unavailable(self):
        """Show message when charts are not available"""
        self.status_label.setText("Charts unavailable - install dependencies")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        self.refresh_button.setEnabled(False)
        logger.warning("Plotly or QWebEngineView not available - charts disabled")
        
    def set_symbol(self, symbol: str):
        """Set the chart symbol and load data"""
        if not symbol or not WEB_ENGINE_AVAILABLE or not PLOTLY_AVAILABLE:
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
        if not self.current_symbol or not WEB_ENGINE_AVAILABLE or not PLOTLY_AVAILABLE:
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
            if not WEB_ENGINE_AVAILABLE or not PLOTLY_AVAILABLE or not chart_data:
                return
                
            logger.info(f"Updating chart display: {len(chart_data)} bars for {self.current_symbol} {self.current_timeframe}")
            
            # Convert to DataFrame for easier manipulation
            df = pd.DataFrame(chart_data)
            df['datetime'] = pd.to_datetime(df['time'], unit='s')
            
            # Create subplots with shared x-axis
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.7, 0.3],
                subplot_titles=(f'{self.current_symbol} - {self.current_timeframe}', 'Volume')
            )
            
            # Add candlestick chart
            fig.add_trace(
                go.Candlestick(
                    x=df['datetime'],
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name='OHLC',
                    increasing_line_color='#26a69a',
                    decreasing_line_color='#ef5350',
                    increasing_fillcolor='#26a69a',
                    decreasing_fillcolor='#ef5350'
                ),
                row=1, col=1
            )
            
            # Add volume bars
            colors = ['#26a69a' if close >= open else '#ef5350' 
                     for close, open in zip(df['close'], df['open'])]
            
            fig.add_trace(
                go.Bar(
                    x=df['datetime'],
                    y=df['volume'],
                    name='Volume',
                    marker_color=colors,
                    opacity=0.5
                ),
                row=2, col=1
            )
            
            # Update layout with dark theme
            fig.update_layout(
                template='plotly_dark',
                height=600,
                showlegend=False,
                xaxis_rangeslider_visible=False,
                margin=dict(l=50, r=50, t=50, b=50),
                plot_bgcolor='#1e1e1e',
                paper_bgcolor='#1e1e1e',
                font=dict(color='#d1d4dc', size=11),
                xaxis=dict(
                    gridcolor='#2B2B43',
                    showgrid=True,
                    zeroline=False
                ),
                yaxis=dict(
                    gridcolor='#2B2B43',
                    showgrid=True,
                    zeroline=False,
                    side='right'
                ),
                xaxis2=dict(
                    gridcolor='#2B2B43',
                    showgrid=True,
                    zeroline=False
                ),
                yaxis2=dict(
                    gridcolor='#2B2B43',
                    showgrid=True,
                    zeroline=False,
                    side='right'
                )
            )
            
            # Update axes
            fig.update_xaxes(
                rangebreaks=[
                    dict(bounds=["sat", "mon"]),  # Hide weekends
                ],
                rangeslider_visible=False
            )
            
            # Configure chart interaction
            config = {
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
                'toImageButtonOptions': {
                    'format': 'png',
                    'filename': f'{self.current_symbol}_chart',
                    'height': 600,
                    'width': 1000,
                    'scale': 1
                }
            }
            
            # Convert to HTML
            html = fig.to_html(
                config=config,
                include_plotlyjs='cdn',
                div_id="chart"
            )
            
            # Add custom CSS to ensure proper sizing
            custom_html = f"""
            <html>
            <head>
                <style>
                    body {{
                        margin: 0;
                        padding: 0;
                        background-color: #1e1e1e;
                    }}
                    #chart {{
                        width: 100%;
                        height: 100vh;
                    }}
                </style>
            </head>
            <body>
                {html}
            </body>
            </html>
            """
            
            # Load HTML in web view
            if self.web_view:
                self.web_view.setHtml(custom_html)
                
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
        
    def cleanup(self):
        """Cleanup resources"""
        try:
            self.update_timer.stop()
        except Exception as e:
            logger.error(f"Error during chart cleanup: {str(e)}")