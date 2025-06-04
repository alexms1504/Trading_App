#!/usr/bin/env python3
"""
Test script for data fetcher functionality
Tests real price fetching and stop loss calculations
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.utils.logger import logger
from src.core.ib_connection import ib_connection_manager
from src.core.data_fetcher import data_fetcher


async def test_data_fetcher():
    """Test the data fetcher functionality"""
    print("🔌 Testing Data Fetcher...")
    
    try:
        # Connect to IB
        print("Connecting to IB...")
        connected = await ib_connection_manager.connect()
        
        if not connected:
            print("❌ Failed to connect to IB")
            return False
            
        print("✅ Connected to IB successfully")
        
        # Test symbols
        test_symbols = ['AAPL', 'SPY', 'MSFT']
        
        for symbol in test_symbols:
            print(f"\n📊 Testing {symbol}...")
            
            # Test latest price fetch
            print(f"  Fetching latest price for {symbol}...")
            price_data = data_fetcher.get_latest_price(symbol)
            
            if price_data:
                print(f"  ✅ Latest price: ${price_data['latest_price']:.2f}")
                print(f"     Last: ${price_data.get('last', 'N/A')}")
                print(f"     Bid: ${price_data.get('bid', 'N/A')}")
                print(f"     Ask: ${price_data.get('ask', 'N/A')}")
            else:
                print(f"  ❌ Failed to get price for {symbol}")
                continue
                
            # Test stop loss calculations
            print(f"  Calculating stop loss levels for {symbol}...")
            stop_levels = data_fetcher.calculate_stop_loss_levels(
                symbol, price_data['latest_price'], 'BUY'
            )
            
            if stop_levels:
                print(f"  ✅ Stop loss levels calculated:")
                for level_name, level_price in stop_levels.items():
                    print(f"     {level_name}: ${level_price:.2f}")
            else:
                print(f"  ⚠️  No stop loss levels calculated")
                
            # Test combined function
            print(f"  Testing combined price and stops...")
            combined_data = data_fetcher.get_price_and_stops(symbol, 'BUY')
            
            if combined_data:
                print(f"  ✅ Combined data fetched successfully")
                print(f"     Current price: ${combined_data['current_price']:.2f}")
                print(f"     Available stops: {list(combined_data['stop_levels'].keys())}")
            else:
                print(f"  ❌ Failed to get combined data")
                
        print("\n🧹 Cleaning up...")
        data_fetcher.cleanup_subscriptions()
        await ib_connection_manager.disconnect()
        
        print("✅ Data fetcher test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        logger.error(f"Data fetcher test error: {str(e)}")
        return False


def main():
    """Main test function"""
    print("=" * 50)
    print("🧪 DATA FETCHER TEST")
    print("=" * 50)
    print("\nThis test will:")
    print("1. Connect to IB TWS/Gateway")
    print("2. Fetch real market data for test symbols")
    print("3. Calculate stop loss levels using historical data")
    print("4. Test the combined price and stops function")
    print("\nMake sure IB TWS/Gateway is running before proceeding.")
    
    input("\nPress Enter to start test...")
    
    # Run the async test
    try:
        result = asyncio.run(test_data_fetcher())
        if result:
            print("\n🎉 All tests passed!")
        else:
            print("\n💥 Some tests failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()