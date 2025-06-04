#!/usr/bin/env python3
"""
Test Stop Loss Data Fetching
Test script to verify historical data retrieval for stop loss calculations
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.ib_connection import IBConnectionManager
from src.core.data_fetcher import data_fetcher
from src.utils.logger import logger

def test_stop_loss_data():
    """Test stop loss data fetching"""
    print("=== Testing Stop Loss Data Fetching ===\n")
    
    # Initialize connection
    ib_manager = IBConnectionManager()
    
    # Connect to IB
    print("Connecting to IB...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    success = loop.run_until_complete(ib_manager.connect())
    
    if not success:
        print("❌ Failed to connect to IB TWS/Gateway")
        print("Make sure TWS or IB Gateway is running and accepting connections")
        return False
        
    print("✅ Connected to IB successfully")
    
    # Test symbols
    test_symbols = ['AAPL', 'MSFT', 'TSLA']
    
    for symbol in test_symbols:
        print(f"\n--- Testing {symbol} ---")
        
        try:
            # Fetch price and stops
            result = data_fetcher.get_price_and_stops(symbol, 'BUY')
            
            if result:
                current_price = result['current_price']
                stop_levels = result['stop_levels']
                
                print(f"✅ Current price: ${current_price:.2f}")
                print(f"Stop levels available: {list(stop_levels.keys())}")
                
                for level_name, level_price in stop_levels.items():
                    print(f"   {level_name}: ${level_price:.2f}")
                    
                # Check for critical stop levels
                if 'prior_5min_low' in stop_levels:
                    print("✅ Prior 5min bar low data available")
                else:
                    print("⚠️  Prior 5min bar low data NOT available")
                    
                if 'day_low' in stop_levels:
                    print("✅ Day low data available")
                else:
                    print("⚠️  Day low data NOT available")
                    
            else:
                print(f"❌ Failed to fetch data for {symbol}")
                
        except Exception as e:
            print(f"❌ Error testing {symbol}: {str(e)}")
            
    # Disconnect
    print(f"\nDisconnecting from IB...")
    loop.run_until_complete(ib_manager.disconnect())
    print("✅ Disconnected successfully")
    
    return True

if __name__ == "__main__":
    try:
        test_stop_loss_data()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        logger.exception("Full traceback:")