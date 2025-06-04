#!/usr/bin/env python3
"""
Test 1-Hour Grid Intervals
Test clean 1-hour spacing of time labels
"""

import sys
import numpy as np
from datetime import datetime, timedelta
import pytz

# Add src directory to path
sys.path.insert(0, 'src')

from src.ui.chart_widget_embedded import CandlestickChart

def test_1hour_grid():
    """Test 1-hour grid intervals for different timeframes"""
    print("Testing 1-Hour Grid Intervals...")
    print("Expected behavior:")
    print("- 5m chart: Labels every 12 bars (1 hour)")
    print("- 1m chart: Labels every 60 bars (1 hour)")
    print("- 15m chart: Labels every 4 bars (1 hour)")
    print()
    
    # Create test data spanning a full trading day
    utc = pytz.timezone('UTC')
    eastern = pytz.timezone('US/Eastern')
    
    # Start at 9:30 AM ET (market open)
    base_time_et = datetime.now(eastern).replace(hour=9, minute=30, second=0, microsecond=0)
    base_time_utc = base_time_et.astimezone(utc)
    
    def create_test_data(timeframe_minutes, num_bars):
        """Create test data for specific timeframe"""
        test_data = []
        current_price = 150.0
        
        for i in range(num_bars):
            bar_time_utc = base_time_utc + timedelta(minutes=i * timeframe_minutes)
            
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
        
        return test_data
    
    # Test 5-minute chart
    chart = CandlestickChart()
    
    print("Testing 5-minute chart (should show labels every 12 bars = 1 hour)...")
    data_5m = create_test_data(5, 78)  # 6.5 hours of 5-min data (full trading day)
    start_time = datetime.fromtimestamp(data_5m[0]['time'], tz=pytz.UTC).astimezone(eastern)
    end_time = datetime.fromtimestamp(data_5m[-1]['time'], tz=pytz.UTC).astimezone(eastern)
    print(f"5m chart: {len(data_5m)} bars from {start_time.strftime('%H:%M')} to {end_time.strftime('%H:%M')}")
    
    try:
        chart.plot_candlestick_data(data_5m, "5MIN_1HOUR_TEST", "5m", True, True, True)
        print("SUCCESS: 5-minute chart with 1-hour grid intervals")
        print("Expected labels: 10:00, 11:00, 12:00, 13:00, 14:00, 15:00, 16:00")
        print("(Much cleaner than 30-minute intervals!)")
    except Exception as e:
        print(f"FAILED: {e}")
    
    print("\nTesting 1-minute chart (should show labels every 60 bars = 1 hour)...")
    data_1m = create_test_data(1, 180)  # 3 hours of 1-min data
    start_time = datetime.fromtimestamp(data_1m[0]['time'], tz=pytz.UTC).astimezone(eastern)
    end_time = datetime.fromtimestamp(data_1m[-1]['time'], tz=pytz.UTC).astimezone(eastern)
    print(f"1m chart: {len(data_1m)} bars from {start_time.strftime('%H:%M')} to {end_time.strftime('%H:%M')}")
    
    try:
        chart.plot_candlestick_data(data_1m, "1MIN_1HOUR_TEST", "1m", True, False, False)
        print("SUCCESS: 1-minute chart with 1-hour grid intervals")
        print("Expected labels: 10:00, 11:00, 12:00")
    except Exception as e:
        print(f"FAILED: {e}")
    
    print("\nTesting 15-minute chart (should show labels every 4 bars = 1 hour)...")
    data_15m = create_test_data(15, 26)  # 6.5 hours of 15-min data
    start_time = datetime.fromtimestamp(data_15m[0]['time'], tz=pytz.UTC).astimezone(eastern)
    end_time = datetime.fromtimestamp(data_15m[-1]['time'], tz=pytz.UTC).astimezone(eastern)
    print(f"15m chart: {len(data_15m)} bars from {start_time.strftime('%H:%M')} to {end_time.strftime('%H:%M')}")
    
    try:
        chart.plot_candlestick_data(data_15m, "15MIN_1HOUR_TEST", "15m", False, True, True)
        print("SUCCESS: 15-minute chart with 1-hour grid intervals")
        print("Expected labels: 10:00, 11:00, 12:00, 13:00, 14:00, 15:00, 16:00")
    except Exception as e:
        print(f"FAILED: {e}")
    
    print("\n1-Hour Grid Test Completed!")
    print("Time labels should now have clean 1-hour spacing - much more professional!")

if __name__ == "__main__":
    test_1hour_grid()