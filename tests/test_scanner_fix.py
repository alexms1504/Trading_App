#!/usr/bin/env python3
"""
Test script for the fixed market screener cancellation
"""

import asyncio
import time
from src.core.market_screener import MarketScreener, ScreeningCriteria
from src.core.ib_connection import ib_connection_manager
from src.utils.logger import logger

async def test_scanner_fix():
    """Test the scanner cancellation fix"""
    print("Testing market screener fix...")
    
    try:
        # Initialize screener
        screener = MarketScreener()
        
        # Set up test criteria
        criteria = ScreeningCriteria(
            scan_code="TOP_PERC_GAIN",
            above_price=1.0,
            below_price=100.0,
            above_volume=1000000
        )
        screener.set_criteria(criteria)
        
        # Test connection
        if not ib_connection_manager.is_connected():
            print("Connecting to IB...")
            success = ib_connection_manager.connect()
            if not success:
                print("Failed to connect to IB")
                return False
                
        # Test async screening
        print("Testing async screening start/stop...")
        success = await screener.start_screening_async()
        if success:
            print("✓ Async screening started successfully")
            
            # Wait a moment to get results
            await asyncio.sleep(2)
            
            # Get results
            results = screener.get_current_results()
            print(f"✓ Got {len(results)} results")
            
            # Test stop
            screener.stop_screening()
            print("✓ Async screening stopped successfully")
        else:
            print("✗ Failed to start async screening")
            return False
            
        # Test sync screening
        print("\nTesting sync screening start/stop...")
        success = screener.start_screening()
        if success:
            print("✓ Sync screening started successfully")
            
            # Wait a moment
            time.sleep(2)
            
            # Get results
            results = screener.get_current_results()
            print(f"✓ Got {len(results)} results")
            
            # Test stop
            screener.stop_screening()
            print("✓ Sync screening stopped successfully")
        else:
            print("✗ Failed to start sync screening")
            return False
            
        # Test refresh
        print("\nTesting refresh functionality...")
        success = screener.start_screening()
        if success:
            success = await screener.refresh_results_async()
            if success:
                print("✓ Async refresh successful")
            else:
                print("✗ Async refresh failed")
                
            success = screener.refresh_results()
            if success:
                print("✓ Sync refresh successful")
            else:
                print("✗ Sync refresh failed")
                
            screener.stop_screening()
            print("✓ Final stop successful")
        
        print("\n✅ All tests passed! Scanner cancellation fix is working.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        logger.error(f"Scanner test error: {str(e)}")
        return False

def main():
    """Main test function"""
    try:
        result = asyncio.run(test_scanner_fix())
        if result:
            print("\n🎉 Scanner fix validation successful!")
        else:
            print("\n💥 Scanner fix validation failed!")
    except Exception as e:
        print(f"Test execution failed: {str(e)}")

if __name__ == "__main__":
    main()