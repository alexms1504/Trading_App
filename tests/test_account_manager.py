"""
Test the Account Manager
Displays account values, buying power, positions, and P&L
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.ib_connection import ib_connection_manager
from src.core.account_manager import account_manager
from src.utils.logger import setup_logger

logger = setup_logger("test_account_manager")


async def test_account_manager():
    """Test account manager functionality"""
    logger.info("Starting Account Manager test...")
    
    # First connect to IB
    connected = await ib_connection_manager.connect()
    if not connected:
        logger.error("Failed to connect to IB")
        return False
    
    # Wait for connection to stabilize
    await asyncio.sleep(2)
    
    # Initialize account manager
    initialized = await account_manager.initialize()
    if not initialized:
        logger.error("Failed to initialize account manager")
        return False
    
    # Wait for data to load
    await asyncio.sleep(2)
    
    # Get all accounts
    accounts = ib_connection_manager.get_accounts()
    logger.info(f"\nFound {len(accounts)} accounts")
    
    # Display data for each account
    for account in accounts:
        logger.info(f"\n{'='*60}")
        logger.info(f"ACCOUNT: {account}")
        logger.info(f"{'='*60}")
        
        # Get account summary
        summary = account_manager.get_account_summary(account)
        
        logger.info("\nAccount Values:")
        logger.info(f"  Net Liquidation: ${summary['net_liquidation']:,.2f}")
        logger.info(f"  Buying Power:    ${summary['buying_power']:,.2f}")
        logger.info(f"  Available Funds: ${summary['available_funds']:,.2f}")
        logger.info(f"  Cash Balance:    ${summary['cash_balance']:,.2f}")
        
        logger.info("\nPositions:")
        logger.info(f"  Position Count:  {summary['position_count']}")
        logger.info(f"  Position Value:  ${summary['position_value']:,.2f}")
        
        # Show individual positions
        positions = account_manager.get_positions(account)
        for pos in positions[:5]:  # Show first 5 positions
            logger.info(f"    {pos.contract.symbol}: {pos.position} shares @ ${pos.avgCost:.2f}")
        
        logger.info("\nP&L:")
        logger.info(f"  Daily P&L:       ${summary['daily_pnl']:,.2f}")
        logger.info(f"  Unrealized P&L:  ${summary['unrealized_pnl']:,.2f}")
        logger.info(f"  Realized P&L:    ${summary['realized_pnl']:,.2f}")
    
    # Test order validation
    logger.info(f"\n{'='*60}")
    logger.info("Order Validation Tests:")
    logger.info(f"{'='*60}")
    
    active_account = ib_connection_manager.get_active_account()
    buying_power = account_manager.get_buying_power(active_account)
    
    # Test different order sizes
    test_amounts = [1000, 10000, buying_power * 0.5, buying_power * 0.8, buying_power * 1.2]
    
    for amount in test_amounts:
        is_valid, message = account_manager.validate_order_buying_power(amount)
        status = "✓" if is_valid else "✗"
        logger.info(f"  ${amount:,.2f}: {status} {message}")
    
    # Test margin requirement calculation
    logger.info(f"\n{'='*60}")
    logger.info("Margin Requirement Tests:")
    logger.info(f"{'='*60}")
    
    test_orders = [
        ("AAPL", 100, 150.00),
        ("TSLA", 50, 200.00),
        ("SPY", 200, 400.00)
    ]
    
    for symbol, qty, price in test_orders:
        margin_req = account_manager.calculate_margin_requirement(symbol, qty, price)
        order_value = qty * price
        logger.info(f"  {symbol}: {qty} @ ${price:.2f}")
        logger.info(f"    Order Value: ${order_value:,.2f}")
        logger.info(f"    Margin Req:  ${margin_req:,.2f} ({margin_req/order_value*100:.1f}%)")
    
    # Test position concentration
    if positions:
        symbol = positions[0].contract.symbol
        concentration = account_manager.calculate_position_concentration(symbol)
        logger.info(f"\nPosition Concentration for {symbol}: {concentration:.2f}%")
    
    # Cleanup
    account_manager.cleanup()
    await ib_connection_manager.disconnect()
    
    logger.info("\nAccount Manager test completed successfully!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_account_manager())
    if success:
        print("\nAccount Manager test passed!")
    else:
        print("\nAccount Manager test failed!")
