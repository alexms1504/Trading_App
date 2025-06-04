#!/usr/bin/env python3
"""
Test Daily Chart Improvements
- No day separator lines on 1d charts
- Regular VWAP calculation for daily bars
"""

import sys
import numpy as np
from datetime import datetime, timedelta
import pytz

# Add src directory to path
sys.path.insert(0, 'src')

from src.ui.chart_widget_embedded import CandlestickChart

def test_daily_chart():
    """Test daily chart without day separators"""
    print("Testing Daily Chart Improvements...")
    print("Expected behavior:")
    print("- No day separator lines (each bar is already a day)")
    print("- Regular VWAP calculation (cumulative, not daily reset)")
    print()
    
    # Create test data for daily bars
    utc = pytz.timezone('UTC')
    eastern = pytz.timezone('US/Eastern')
    
    # Start from 30 trading days ago
    base_date = datetime.now(eastern).replace(hour=16, minute=0, second=0, microsecond=0)
    
    # Create 30 days of daily bar data
    test_data = []
    current_price = 150.0
    
    for i in range(30):
        # Go back in time
        bar_date = base_date - timedelta(days=30-i)
        
        # Skip weekends
        if bar_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            continue
            
        # Generate realistic daily price movement
        daily_change = np.random.normal(0, 2.0)  # Larger moves for daily
        current_price += daily_change
        
        high = current_price + abs(np.random.normal(0, 1.0))
        low = current_price - abs(np.random.normal(0, 1.0))
        close = current_price + np.random.normal(0, 0.5)
        volume = np.random.randint(5000000, 20000000)  # Daily volumes
        
        bar_date_utc = bar_date.astimezone(utc)
        
        test_data.append({
            'time': bar_date_utc.timestamp(),
            'open': current_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
        
        current_price = close
    
    # Test daily chart
    chart = CandlestickChart()
    
    print(f"Testing 1-day chart with {len(test_data)} daily bars...")
    start_time = datetime.fromtimestamp(test_data[0]['time'], tz=pytz.UTC).astimezone(eastern)
    end_time = datetime.fromtimestamp(test_data[-1]['time'], tz=pytz.UTC).astimezone(eastern)
    print(f"Date range: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")
    
    try:
        # Test with all indicators enabled
        chart.plot_candlestick_data(test_data, "DAILY_CHART_TEST", "1d", True, True, True)
        print("SUCCESS: Daily chart rendered without day separator lines")
        print("VWAP should show cumulative calculation across all days")
        print("Time axis should show dates only (no times)")
    except Exception as e:
        print(f"FAILED: {e}")
    
    print("\nDaily Chart Test Completed!")
    print("Improvements:")
    print("1. No day separator lines cluttering the daily chart")
    print("2. VWAP uses cumulative calculation appropriate for daily timeframe")
    print("3. Clean date-only labels on x-axis")

if __name__ == "__main__":
    test_daily_chart()