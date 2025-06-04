#!/usr/bin/env python3
"""
Test Interactive Price Levels
Test draggable entry, stop loss, and take profit lines on charts
"""

import sys
import numpy as np
from datetime import datetime, timedelta
import pytz

# Add src directory to path
sys.path.insert(0, 'src')

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from src.ui.chart_widget_embedded import ChartWidget

def test_price_levels():
    """Test interactive price levels on chart"""
    print("Testing Interactive Price Levels...")
    print("Expected behavior:")
    print("- Blue solid line for Entry price")
    print("- Red dashed line for Stop Loss")
    print("- Green dash-dot line for Take Profit")
    print("- Lines should be draggable (click and drag)")
    print()
    
    # Create Qt app
    app = QApplication(sys.argv)
    
    # Create window
    window = QWidget()
    window.setWindowTitle("Interactive Price Levels Test")
    window.setGeometry(100, 100, 1000, 700)
    
    layout = QVBoxLayout(window)
    
    # Create chart widget
    chart_widget = ChartWidget()
    layout.addWidget(chart_widget)
    
    # Generate test data
    utc = pytz.timezone('UTC')
    eastern = pytz.timezone('US/Eastern')
    base_time = datetime.now(eastern).replace(hour=9, minute=30, second=0, microsecond=0)
    base_time_utc = base_time.astimezone(utc)
    
    # Create 5-minute bar data
    test_data = []
    current_price = 150.0
    
    for i in range(78):  # Full trading day
        bar_time_utc = base_time_utc + timedelta(minutes=i * 5)
        
        change = np.random.normal(0, 0.3)
        current_price += change
        
        high = current_price + abs(np.random.normal(0, 0.1))
        low = current_price - abs(np.random.normal(0, 0.1))
        close = current_price + np.random.normal(0, 0.05)
        volume = np.random.randint(100000, 500000)
        
        test_data.append({
            'time': bar_time_utc.timestamp(),
            'open': current_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
        
        current_price = close
    
    # Set symbol and load data
    chart_widget.set_symbol("TEST")
    
    # Load chart data manually (bypass chart_data_manager)
    if chart_widget.chart_canvas:
        chart_widget.chart_canvas.plot_candlestick_data(
            test_data, "TEST", "5m", True, True, True
        )
    
    # Set some initial price levels
    entry_price = 150.0
    stop_loss = 148.0
    take_profit = 154.0
    
    print(f"Setting initial price levels:")
    print(f"Entry: ${entry_price:.2f} (Blue solid line)")
    print(f"Stop Loss: ${stop_loss:.2f} (Red dashed line)")
    print(f"Take Profit: ${take_profit:.2f} (Green dash-dot line)")
    
    # Update price levels on chart
    chart_widget.update_price_levels(
        entry=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit
    )
    
    # Connect signals to show when prices are dragged
    def on_entry_changed(price):
        print(f"Entry dragged to: ${price:.2f}")
        
    def on_stop_loss_changed(price):
        print(f"Stop Loss dragged to: ${price:.2f}")
        
    def on_take_profit_changed(price):
        print(f"Take Profit dragged to: ${price:.2f}")
        
    chart_widget.chart_entry_changed.connect(on_entry_changed)
    chart_widget.chart_stop_loss_changed.connect(on_stop_loss_changed)
    chart_widget.chart_take_profit_changed.connect(on_take_profit_changed)
    
    print("\nInteractive Price Levels Test Ready!")
    print("Try dragging the price lines on the chart.")
    print("The console will show when prices are changed.")
    
    window.show()
    return app.exec()

if __name__ == "__main__":
    test_price_levels()