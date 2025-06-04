"""
Test bracket order submission
"""
from ib_async import IB, Stock
import time

def test_bracket():
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=2)
    
    # Create contract
    contract = Stock('AAPL', 'SMART', 'USD')
    ib.qualifyContracts(contract)
    
    # Get current price (simulate)
    entry = 185.0
    stop = 180.0
    target = 190.0
    
    # Create bracket order
    bracket = ib.bracketOrder('BUY', 10, entry, target, stop)
    
    # Check what was created
    print("Bracket order created:")
    print(f"  Parent: {bracket.parent.orderType}, transmit={bracket.parent.transmit}")
    print(f"  TP: {bracket.takeProfit.orderType}, transmit={bracket.takeProfit.transmit}, parentId={bracket.takeProfit.parentId}")
    print(f"  SL: {bracket.stopLoss.orderType}, transmit={bracket.stopLoss.transmit}, parentId={bracket.stopLoss.parentId}")
    
    # For market order, modify parent
    # bracket.parent.orderType = 'MKT'
    # bracket.parent.lmtPrice = None
    
    # Place all orders
    print("\nPlacing bracket order...")
    for i, order in enumerate(bracket):
        trade = ib.placeOrder(contract, order)
        print(f"Order {i} placed - ID: {trade.order.orderId}")
    
    # Wait a bit
    time.sleep(2)
    
    # Check status
    print("\nOrder status:")
    for trade in ib.trades():
        print(f"ID {trade.order.orderId}: {trade.orderStatus.status}")
    
    ib.disconnect()

if __name__ == '__main__':
    test_bracket()