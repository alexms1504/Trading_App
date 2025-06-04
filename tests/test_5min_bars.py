#!/usr/bin/env python3
"""
Test 5-Minute Bar Extraction
Detailed analysis of how 5-minute bars are being extracted and which bar is selected
"""

import sys
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from ib_async import Stock
from src.core.ib_connection import IBConnectionManager
from src.utils.logger import logger

def analyze_5min_bars(symbol: str = 'AAPL'):
    """Analyze 5-minute bar extraction in detail"""
    print(f"\n{'='*60}")
    print(f"5-MINUTE BAR ANALYSIS FOR {symbol}")
    print(f"{'='*60}\n")
    
    # Initialize connection
    ib_manager = IBConnectionManager()
    
    # Connect to IB
    print("Connecting to IB...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    success = loop.run_until_complete(ib_manager.connect())
    
    if not success:
        print("❌ Failed to connect to IB TWS/Gateway")
        return False
        
    print("✅ Connected to IB successfully\n")
    
    try:
        ib = ib_manager.ib
        
        # Create contract
        contract = Stock(symbol, 'SMART', 'USD')
        ib.qualifyContracts(contract)
        
        # Get current time for reference
        current_time = datetime.now()
        print(f"Current Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Day of Week: {current_time.strftime('%A')}")
        
        # Determine if market is open
        market_open = current_time.hour >= 9 and current_time.hour < 16 and current_time.weekday() < 5
        print(f"Market Status: {'OPEN' if market_open else 'CLOSED'}\n")
        
        # Request 5-minute bars
        print("Requesting 5-minute bars...")
        bars_5min = ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr='1 D',
            barSizeSetting='5 mins',
            whatToShow='TRADES',
            useRTH=True,
            formatDate=1
        )
        
        if not bars_5min:
            print("❌ No bars received")
            return False
            
        print(f"✅ Received {len(bars_5min)} bars\n")
        
        # Display ALL bars with index
        print("ALL 5-MINUTE BARS:")
        print("-" * 80)
        print(f"{'Index':<6} {'Time':<20} {'Open':<8} {'High':<8} {'Low':<8} {'Close':<8} {'Volume':<10}")
        print("-" * 80)
        
        for i, bar in enumerate(bars_5min):
            print(f"{i:<6} {bar.date:<20} {bar.open:<8.2f} {bar.high:<8.2f} {bar.low:<8.2f} {bar.close:<8.2f} {bar.volume:<10}")
        
        print("\n" + "="*80 + "\n")
        
        # Analyze the last few bars in detail
        print("DETAILED ANALYSIS OF LAST 5 BARS:")
        print("-" * 80)
        
        for i in range(max(0, len(bars_5min) - 5), len(bars_5min)):
            bar = bars_5min[i]
            bar_index = f"bars[{i}] or bars[{i - len(bars_5min)}]"
            
            # Parse bar time
            if isinstance(bar.date, str):
                bar_time = datetime.strptime(bar.date, '%Y%m%d %H:%M:%S')
            else:
                bar_time = bar.date
                
            bar_end_time = bar_time + timedelta(minutes=5)
            
            print(f"\n{bar_index}:")
            print(f"  Start Time: {bar_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  End Time:   {bar_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Low Price:  ${bar.low:.2f}")
            print(f"  Is Complete: {'YES' if current_time >= bar_end_time else 'NO (still forming)'}")
            
        print("\n" + "="*80 + "\n")
        
        # Show which bar would be selected as "prior 5-min bar low"
        print("STOP LOSS SELECTION LOGIC:")
        print("-" * 80)
        
        if len(bars_5min) >= 2:
            prior_bar = bars_5min[-2]
            last_bar = bars_5min[-1]
            
            print(f"Selected 'Prior 5-min Bar': bars[-2]")
            print(f"  Time: {prior_bar.date}")
            print(f"  Low:  ${prior_bar.low:.2f}")
            print(f"\nLatest Bar (bars[-1], possibly incomplete):")
            print(f"  Time: {last_bar.date}")
            print(f"  Low:  ${last_bar.low:.2f}")
            
            # Also show lowest of recent bars
            recent_bars = bars_5min[-5:]
            lowest_recent = min(bar.low for bar in recent_bars)
            lowest_bar_idx = -5 + [i for i, bar in enumerate(recent_bars) if bar.low == lowest_recent][0]
            
            print(f"\nLowest of Last 5 Bars:")
            print(f"  Bar Index: bars[{lowest_bar_idx}]")
            print(f"  Low Price: ${lowest_recent:.2f}")
            
        else:
            print(f"Only {len(bars_5min)} bar(s) available - insufficient data")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        logger.exception("Full traceback:")
        
    finally:
        # Disconnect
        print(f"\nDisconnecting from IB...")
        loop.run_until_complete(ib_manager.disconnect())
        print("✅ Disconnected successfully")
    
    return True

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test 5-minute bar extraction')
    parser.add_argument('symbol', nargs='?', default='AAPL', help='Stock symbol to test (default: AAPL)')
    args = parser.parse_args()
    
    analyze_5min_bars(args.symbol)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        logger.exception("Full traceback:")