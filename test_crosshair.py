#!/usr/bin/env python3
"""
Test Crosshair Functionality
Test TradingView-style crosshair with OHLC display
"""

import sys
import numpy as np
from datetime import datetime, timedelta
import pytz

# Add src directory to path
sys.path.insert(0, 'src')

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from src.ui.chart_widget_embedded import ChartWidget

def test_crosshair():
    """Test crosshair functionality on chart"""
    print("Testing Crosshair Functionality...")
    print("Expected behavior:")
    print("- Move mouse over chart to see crosshair")
    print("- Vertical line follows mouse across both price and volume charts")
    print("- Horizontal line shows price level")
    print("- OHLC data displayed at top of chart")
    print("- Crosshair disappears when mouse leaves chart")
    print()
    
    # Create Qt app
    app = QApplication(sys.argv)
    
    # Create window
    window = QWidget()
    window.setWindowTitle("Crosshair Test - TradingView Style")
    window.setGeometry(100, 100, 1200, 800)
    
    layout = QVBoxLayout(window)
    
    # Create chart widget
    chart_widget = ChartWidget()
    layout.addWidget(chart_widget)
    
    # Generate test data with realistic OHLC
    utc = pytz.timezone('UTC')
    eastern = pytz.timezone('US/Eastern')
    base_time = datetime.now(eastern).replace(hour=9, minute=30, second=0, microsecond=0)
    base_time_utc = base_time.astimezone(utc)
    
    # Create 5-minute bar data
    test_data = []
    current_price = 150.0
    
    for i in range(78):  # Full trading day
        bar_time_utc = base_time_utc + timedelta(minutes=i * 5)
        
        # Generate realistic OHLC
        open_price = current_price
        
        # Intrabar movement
        movement = np.random.normal(0, 0.5)
        high = open_price + abs(np.random.normal(0.2, 0.3))
        low = open_price - abs(np.random.normal(0.2, 0.3))
        close = open_price + movement
        
        # Ensure high/low contain open/close
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        volume = np.random.randint(100000, 500000)
        
        test_data.append({
            'time': bar_time_utc.timestamp(),
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': volume
        })
        
        current_price = close
    
    # Set symbol and load data
    chart_widget.set_symbol("CROSSHAIR_TEST")
    
    # Load chart data manually (bypass chart_data_manager)
    if chart_widget.chart_canvas:
        chart_widget.chart_canvas.plot_candlestick_data(
            test_data, "CROSSHAIR_TEST", "5m", True, True, True
        )
    
    print("\nCrosshair Test Ready!")
    print("Move your mouse over the chart to see:")
    print("1. Crosshair lines following your cursor")
    print("2. OHLC data box at the top showing bar details")
    print("3. Volume information for the selected bar")
    
    window.show()
    return app.exec()

if __name__ == "__main__":
    test_crosshair()