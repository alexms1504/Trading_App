#!/usr/bin/env python3
"""
Test script to verify ScanData attribute fix
Tests the market screener after fixing contractDetails.contract issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.market_screener import market_screener, ScreeningCriteria
from src.core.ib_connection import ib_connection_manager
from src.utils.logger import logger

def test_scandata_fix():
    """Test the ScanData attribute fix"""
    print("Testing ScanData attribute fix...")
    
    # Check if connected to IB
    if not ib_connection_manager.is_connected():
        print("Not connected to IB. Please connect first.")
        return False
        
    # Set up criteria
    criteria = ScreeningCriteria(
        scan_code="TOP_PERC_GAIN",
        above_price=0.4,
        below_price=500.0,
        above_volume=8000000  # $8M
    )
    
    market_screener.set_criteria(criteria)
    
    # Start screening
    print("Starting market screening...")
    if not market_screener.start_screening():
        print("Failed to start screening")
        return False
        
    # Get results
    results = market_screener.get_current_results()
    print(f"\nReceived {len(results)} raw results")
    
    # Test raw ScanData objects
    if results:
        print("\nTesting raw ScanData attributes:")
        result = results[0]
        print(f"  - Type: {type(result)}")
        print(f"  - Has 'contract' attribute: {hasattr(result, 'contract')}")
        print(f"  - Has 'contractDetails' attribute: {hasattr(result, 'contractDetails')}")
        
        if hasattr(result, 'contractDetails'):
            print(f"  - contractDetails type: {type(result.contractDetails)}")
            if hasattr(result.contractDetails, 'contract'):
                print(f"  - contractDetails.contract type: {type(result.contractDetails.contract)}")
                print(f"  - Symbol: {result.contractDetails.contract.symbol}")
    
    # Test formatted results
    formatted_results = market_screener.get_formatted_results()
    print(f"\nFormatted {len(formatted_results)} results successfully")
    
    # Display top 5 results
    if formatted_results:
        print("\nTop 5 results:")
        for i, result in enumerate(formatted_results[:5]):
            print(f"{i+1}. {result['symbol']}: {result['distance']}% change")
    
    # Stop screening
    market_screener.stop_screening()
    print("\nTest completed successfully!")
    return True

if __name__ == "__main__":
    try:
        success = test_scandata_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)