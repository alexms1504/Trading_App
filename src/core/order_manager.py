"""
Order Manager
Handles order creation, submission, and management for MVP
Simplified synchronous version to avoid async complexity
"""

from typing import Dict, Optional, List, Tuple
from datetime import datetime

from ib_async import Stock, Order, Trade, LimitOrder, StopOrder, MarketOrder, BracketOrder

from src.utils.logger import logger
from src.core.ib_connection import ib_connection_manager


class OrderManager:
    """
    Simplified order manager for MVP - handles bracket order creation and submission
    """
    
    def __init__(self):
        """Initialize order manager"""
        self.ib_manager = ib_connection_manager
        self.active_orders: Dict[int, Trade] = {}
        self.order_history: List[Dict] = []
        
    def round_price_to_tick_size(self, price: float, symbol: str = "") -> float:
        """
        Round price to appropriate tick size for the instrument
        
        Args:
            price: Raw price to round
            symbol: Symbol (for future instrument-specific rules)
            
        Returns:
            Properly rounded price
        """
        try:
            # For most US stocks, use penny increments (2 decimal places)
            # Sub-penny stocks (< $1) can use 4 decimal places, but round to 0.0001
            
            if price >= 1.0:
                # Stocks >= $1: Round to nearest penny (0.01)
                return round(price, 2)
            else:
                # Stocks < $1: Round to nearest 0.0001 (sub-penny)
                return round(price, 4)
                
        except Exception as e:
            logger.error(f"Error rounding price {price}: {str(e)}")
            return round(price, 2)  # Default to 2 decimal places
        
    def submit_bracket_order(self,
                           symbol: str,
                           quantity: int,
                           entry_price: float,
                           stop_loss: float,
                           take_profit: float,
                           direction: str = 'BUY',
                           order_type: str = 'LMT',
                           account: Optional[str] = None) -> Tuple[bool, str, Optional[List[Trade]]]:
        """
        Submit a bracket order (parent + stop loss + take profit)
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            entry_price: Entry price (for limit orders)
            stop_loss: Stop loss price
            take_profit: Take profit price
            direction: 'BUY' or 'SELL'
            order_type: 'LMT' or 'MKT'
            account: Account to use (optional)
            
        Returns:
            Tuple of (success, message, trades)
        """
        try:
            logger.info(f"\n=== BRACKET ORDER SUBMISSION START ===")
            logger.info(f"Symbol: {symbol}, Quantity: {quantity}, Direction: {direction}")
            logger.info(f"Original prices - Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit}, Type: {order_type}")
            
            # CRITICAL FIX: Round all prices to proper tick sizes to avoid Error 110
            entry_price = self.round_price_to_tick_size(entry_price, symbol)
            stop_loss = self.round_price_to_tick_size(stop_loss, symbol)
            take_profit = self.round_price_to_tick_size(take_profit, symbol)
            
            logger.info(f"Rounded prices - Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit}")
            
            if not self.ib_manager.is_connected():
                return False, "Not connected to IB", None
                
            # Get IB client directly from the connection manager
            ib = self.ib_manager.ib
            if not ib:
                return False, "IB client not available", None
                
            logger.info(f"IB client available, connection status: {ib.isConnected()}")
                
            # Create contract
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Qualify the contract to ensure it's valid
            ib.qualifyContracts(contract)
            
            # Create bracket order using IB's method
            logger.info(f"Creating bracket order: {direction} {quantity} shares of {symbol}")
            logger.info(f"  Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit}")
            
            # CRITICAL FIX: For market orders, use None for limitPrice
            if order_type == 'MKT':
                bracket = ib.bracketOrder(
                    action=direction,
                    quantity=quantity,
                    limitPrice=None,  # No limit price for market orders
                    takeProfitPrice=take_profit,
                    stopLossPrice=stop_loss
                )
            else:
                bracket = ib.bracketOrder(
                    action=direction,
                    quantity=quantity,
                    limitPrice=entry_price,
                    takeProfitPrice=take_profit,
                    stopLossPrice=stop_loss
                )
            
            # Log the bracket order details
            logger.info(f"Bracket order created with {len(bracket)} orders:")
            for i, order in enumerate(bracket):
                logger.info(f"  Order {i}: Type={order.orderType}, Action={order.action}, "
                          f"Quantity={order.totalQuantity}, ParentId={order.parentId}, "
                          f"OcaGroup={order.ocaGroup}, Transmit={order.transmit}")
                if hasattr(order, 'lmtPrice') and order.lmtPrice:
                    logger.info(f"    LimitPrice={order.lmtPrice}")
                if hasattr(order, 'auxPrice') and order.auxPrice:
                    logger.info(f"    StopPrice={order.auxPrice}")
            
            # Note: Market order handling is done in bracket creation above
            logger.info(f"Bracket order type: {bracket.parent.orderType}")
                
            # Set account on all orders if specified
            target_account = account or self.ib_manager.get_active_account()
            if target_account:
                bracket.parent.account = target_account
                bracket.stopLoss.account = target_account
                bracket.takeProfit.account = target_account
                
            # Check transmit flags before submission
            logger.info("Checking transmit flags and order relationships:")
            for i, order in enumerate(bracket):
                logger.info(f"  Order {i} transmit flag: {order.transmit}")
                logger.info(f"    ParentId: {order.parentId}, OcaGroup: {order.ocaGroup}")
                
            # CRITICAL FIX: Ensure proper transmit flag settings for bracket orders
            # Only the last order should have transmit=True in a bracket
            if len(bracket) >= 3:
                logger.info("Correcting transmit flags for proper bracket submission...")
                bracket[0].transmit = False  # Parent - don't transmit yet
                bracket[1].transmit = False  # Stop loss - don't transmit yet  
                bracket[2].transmit = True   # Take profit - transmit all at once
                
                logger.info("Updated transmit flags:")
                for i, order in enumerate(bracket):
                    logger.info(f"  Order {i} transmit flag: {order.transmit}")
                
            # Place all orders in the bracket - EXACT pattern from example
            trades = []
            logger.info("Submitting orders to IB...")
            for i, order in enumerate(bracket):
                logger.info(f"Placing order {i} (Type={order.orderType}, Transmit={order.transmit})...")
                trade = ib.placeOrder(contract, order)
                trades.append(trade)
                self.active_orders[trade.order.orderId] = trade
                logger.info(f"Placed order ID {trade.order.orderId}: {order.orderType} {order.action} {order.totalQuantity}")
                logger.info(f"  Order status: {trade.orderStatus.status}")
            
            # Give IB time to process the orders
            logger.info("Waiting for IB to process orders...")
            ib.sleep(1)
            
            # Check order statuses after submission
            logger.info("Order statuses after submission:")
            needs_confirmation = False
            cancelled_orders = 0
            
            for i, trade in enumerate(trades):
                status = trade.orderStatus.status
                logger.info(f"  Trade {i} (ID={trade.order.orderId}): Status={status}")
                
                # Check for common issues
                if status == 'PreSubmitted':
                    logger.info(f"    Order {trade.order.orderId} is PreSubmitted (waiting for market hours or confirmation)")
                    needs_confirmation = True
                elif status == 'Cancelled':
                    cancelled_orders += 1
                    why_held = getattr(trade.orderStatus, 'whyHeld', 'Unknown')
                    logger.warning(f"    Order {trade.order.orderId} was CANCELLED: {why_held}")
                elif status == 'Inactive':
                    logger.warning(f"    Order {trade.order.orderId} is INACTIVE - may need confirmation in TWS")
                    needs_confirmation = True
                    
            # Provide user guidance based on order status
            if cancelled_orders > 0:
                logger.warning(f"WARNING: {cancelled_orders} orders were cancelled. Check TWS for details.")
            
            if needs_confirmation:
                logger.warning("WARNING: Orders may require manual confirmation in TWS.")
                logger.warning("Check: TWS -> Configuration -> API -> Settings -> 'Bypass Order Precautions for API Orders'")
                
            # Check if all orders failed
            active_orders = sum(1 for trade in trades if trade.orderStatus.status not in ['Cancelled', 'Inactive'])
            if active_orders == 0:
                logger.error("ERROR: All bracket orders were cancelled or inactive!")
                logger.error("This usually means:")
                logger.error("  1. TWS requires manual order confirmation (most common)")
                logger.error("  2. Insufficient buying power")  
                logger.error("  3. Market is closed for this instrument")
                logger.error("  4. Account restrictions")
                return False, "All orders were cancelled - check TWS configuration", trades
                
            # Log what we did
            logger.info(f"Bracket order submitted for {symbol}:")
            logger.info(f"  Parent: {bracket.parent.orderType} {bracket.parent.action} {quantity} @ {'MKT' if order_type == 'MKT' else entry_price}")
            logger.info(f"  Stop Loss: STP {bracket.stopLoss.action} {quantity} @ {stop_loss}")
            logger.info(f"  Take Profit: LMT {bracket.takeProfit.action} {quantity} @ {take_profit}")
                
            # Log order details
            parent_id = trades[0].order.orderId if trades else None
            logger.info(f"Bracket order submission complete for {symbol}")
            logger.info(f"Total orders placed: {len(trades)}")
            if len(trades) >= 3:
                logger.info(f"Parent: {trades[0].order.orderId}, Stop: {trades[1].order.orderId}, TP: {trades[2].order.orderId}")
            else:
                logger.warning(f"Expected 3 orders but only {len(trades)} were placed!")
                for i, trade in enumerate(trades):
                    logger.warning(f"  Trade {i}: ID={trade.order.orderId}, Type={trade.order.orderType}")
            
            # Add to history
            self.order_history.append({
                'timestamp': datetime.now(),
                'symbol': symbol,
                'direction': direction,
                'quantity': quantity,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'parent_id': parent_id,
                'status': 'SUBMITTED'
            })
            
            logger.info(f"=== BRACKET ORDER SUBMISSION END ===\n")
            return True, f"Bracket order submitted successfully (ID: {parent_id})", trades
            
        except Exception as e:
            error_msg = f"Error submitting bracket order: {str(e)}"
            logger.error(f"BRACKET ORDER ERROR: {error_msg}")
            logger.error(f"=== BRACKET ORDER SUBMISSION FAILED ===\n")
            return False, error_msg, None
            
    def submit_multiple_target_order(self,
                                   symbol: str,
                                   quantity: int,
                                   entry_price: float,
                                   stop_loss: float,
                                   profit_targets: List[Dict],
                                   direction: str = 'BUY',
                                   order_type: str = 'LMT',
                                   account: Optional[str] = None) -> Tuple[bool, str, Optional[List[Trade]]]:
        """
        Submit multiple separate bracket orders for partial scaling
        Creates independent bracket orders for each profit target to avoid OCA cancellation
        
        Args:
            symbol: Stock symbol
            quantity: Total number of shares
            entry_price: Entry price (for limit orders)
            stop_loss: Stop loss price
            profit_targets: List of dicts with 'price' and 'percent' keys
            direction: 'BUY' or 'SELL'
            order_type: 'LMT' or 'MKT'
            account: Account to use (optional)
            
        Returns:
            Tuple of (success, message, trades)
        """
        try:
            logger.info(f"\n=== MULTIPLE TARGET ORDER SUBMISSION START ===")
            logger.info(f"Symbol: {symbol}, Total Quantity: {quantity}, Direction: {direction}")
            logger.info(f"Original prices - Entry: {entry_price}, SL: {stop_loss}, Type: {order_type}")
            logger.info(f"Original profit targets: {profit_targets}")
            
            # CRITICAL FIX: Round all prices to proper tick sizes
            entry_price = self.round_price_to_tick_size(entry_price, symbol)
            stop_loss = self.round_price_to_tick_size(stop_loss, symbol)
            
            # Round profit target prices
            for target in profit_targets:
                target['price'] = self.round_price_to_tick_size(target['price'], symbol)
                
            logger.info(f"Rounded prices - Entry: {entry_price}, SL: {stop_loss}")
            logger.info(f"Rounded profit targets: {profit_targets}")
            
            if not self.ib_manager.is_connected():
                return False, "Not connected to IB", None
                
            ib = self.ib_manager.ib
            if not ib:
                return False, "IB client not available", None
                
            # Validate profit targets
            total_percent = sum(target['percent'] for target in profit_targets)
            if total_percent != 100:
                return False, f"Profit target percentages must total 100% (got {total_percent}%)", None
                
            # Create contract
            contract = Stock(symbol, 'SMART', 'USD')
            ib.qualifyContracts(contract)
            
            # Set account
            target_account = account or self.ib_manager.get_active_account()
            
            # Create separate bracket orders for each profit target
            all_trades = []
            bracket_groups = []
            
            logger.info(f"Creating {len(profit_targets)} separate bracket orders...")
            
            for i, target in enumerate(profit_targets):
                target_quantity = int(quantity * target['percent'] / 100)
                if target_quantity <= 0:
                    continue
                    
                logger.info(f"Creating bracket {i+1}: {target_quantity} shares @ {target['price']} ({target['percent']}%)")
                
                # Create bracket order for this target
                bracket = ib.bracketOrder(
                    action=direction,
                    quantity=target_quantity,
                    limitPrice=entry_price,
                    takeProfitPrice=target['price'],
                    stopLossPrice=stop_loss
                )
                
                # Modify for market orders if needed
                if order_type == 'MKT':
                    bracket.parent.orderType = 'MKT'
                    bracket.parent.lmtPrice = None
                    
                # Set account on all orders if specified
                if target_account:
                    bracket.parent.account = target_account
                    bracket.stopLoss.account = target_account
                    bracket.takeProfit.account = target_account
                    
                # Set transmit flags correctly for bracket orders
                bracket[0].transmit = False  # Parent - don't transmit yet
                bracket[1].transmit = False  # Stop loss - don't transmit yet  
                bracket[2].transmit = True   # Take profit - transmit all at once
                
                # Place all orders in this bracket
                bracket_trades = []
                logger.info(f"Submitting bracket {i+1} orders...")
                for j, order in enumerate(bracket):
                    trade = ib.placeOrder(contract, order)
                    bracket_trades.append(trade)
                    all_trades.append(trade)
                    self.active_orders[trade.order.orderId] = trade
                    logger.info(f"  Order {j}: {order.orderType} {order.action} {order.totalQuantity} (ID: {trade.order.orderId})")
                
                bracket_groups.append({
                    'target_index': i + 1,
                    'quantity': target_quantity,
                    'target_price': target['price'],
                    'percent': target['percent'],
                    'trades': bracket_trades,
                    'parent_id': bracket_trades[0].order.orderId if bracket_trades else None
                })
                
                # Small delay between bracket submissions
                ib.sleep(0.5)
            
            # Give IB time to process all orders
            logger.info("Waiting for IB to process all bracket orders...")
            ib.sleep(2)
            
            # Log results
            logger.info(f"Multiple target orders submitted for {symbol}:")
            total_orders = len(all_trades)
            total_brackets = len(bracket_groups)
            logger.info(f"  Created {total_brackets} separate bracket orders ({total_orders} total orders)")
            
            for group in bracket_groups:
                logger.info(f"  Bracket {group['target_index']}: {group['quantity']} shares")
                logger.info(f"    Entry: {order_type} @ {'MKT' if order_type == 'MKT' else entry_price}")
                logger.info(f"    Stop Loss: @ {stop_loss}")
                logger.info(f"    Take Profit: @ {group['target_price']} ({group['percent']}%)")
                logger.info(f"    Parent ID: {group['parent_id']}")
                
            # Add to history
            self.order_history.append({
                'timestamp': datetime.now(),
                'symbol': symbol,
                'direction': direction,
                'quantity': quantity,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'profit_targets': profit_targets,
                'bracket_groups': bracket_groups,
                'status': 'SUBMITTED',
                'order_type': 'MULTIPLE_BRACKETS'
            })
            
            success_msg = f"Submitted {total_brackets} bracket orders for partial scaling ({total_orders} total orders)"
            logger.info(f"=== MULTIPLE TARGET ORDER SUBMISSION END ===\n")
            return True, success_msg, all_trades
            
        except Exception as e:
            error_msg = f"Error submitting multiple target order: {str(e)}"
            logger.error(f"MULTIPLE TARGET ORDER ERROR: {error_msg}")
            logger.error(f"=== MULTIPLE TARGET ORDER SUBMISSION FAILED ===\n")
            return False, error_msg, None
            
    def cancel_order(self, order_id: int) -> Tuple[bool, str]:
        """
        Cancel an order by ID
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if not self.ib_manager.is_connected():
                return False, "Not connected to IB"
                
            ib = self.ib_manager.ib
            if not ib:
                return False, "IB client not available"
                
            # Find the trade
            if order_id not in self.active_orders:
                return False, f"Order {order_id} not found in active orders"
                
            trade = self.active_orders[order_id]
            
            # Cancel the order
            ib.cancelOrder(trade.order)
            
            logger.info(f"Cancel request sent for order {order_id}")
            return True, f"Cancel request sent for order {order_id}"
            
        except Exception as e:
            error_msg = f"Error canceling order: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
    def get_active_orders(self) -> List[Dict]:
        """Get list of active orders"""
        active = []
        for order_id, trade in self.active_orders.items():
            if trade.orderStatus.status not in ['Filled', 'Cancelled', 'Inactive']:
                active.append({
                    'order_id': order_id,
                    'symbol': trade.contract.symbol,
                    'action': trade.order.action,
                    'quantity': trade.order.totalQuantity,
                    'status': trade.orderStatus.status,
                    'filled': trade.orderStatus.filled,
                    'remaining': trade.orderStatus.remaining
                })
        return active
        
    def get_order_status(self, order_id: int) -> Optional[str]:
        """Get status of a specific order"""
        if order_id in self.active_orders:
            return self.active_orders[order_id].orderStatus.status
        return None
        
    def clear_filled_orders(self):
        """Remove filled and cancelled orders from active orders"""
        to_remove = []
        for order_id, trade in self.active_orders.items():
            if trade.orderStatus.status in ['Filled', 'Cancelled', 'Inactive']:
                to_remove.append(order_id)
                
        for order_id in to_remove:
            del self.active_orders[order_id]
            
        if to_remove:
            logger.info(f"Cleared {len(to_remove)} completed orders")
            
    def check_api_configuration(self) -> Tuple[bool, List[str]]:
        """
        Check API configuration and provide guidance
        Returns (is_configured_properly, list_of_issues)
        """
        issues = []
        
        try:
            if not self.ib_manager.is_connected():
                issues.append("Not connected to TWS/Gateway")
                return False, issues
                
            ib = self.ib_manager.ib
            if not ib:
                issues.append("IB client not available")
                return False, issues
                
            # Check if we can get account info (basic API permission test)
            try:
                accounts = ib.managedAccounts()
                if not accounts:
                    issues.append("No managed accounts found - check API permissions")
            except Exception as e:
                issues.append(f"Cannot access account info: {str(e)}")
                
            # Try to get positions (another permission test)
            try:
                positions = ib.positions()
                logger.info(f"Found {len(positions)} positions - API read access working")
            except Exception as e:
                issues.append(f"Cannot read positions: {str(e)}")
                
            # Common configuration issues
            if issues:
                issues.append("SOLUTION: In TWS/Gateway:")
                issues.append("  1. File → Global Configuration → API → Settings")
                issues.append("  2. Enable 'ActiveX and Socket Clients'")
                issues.append("  3. UNCHECK 'Read-Only API' if checked")
                issues.append("  4. Enable 'Download open orders on connection'")
                issues.append("  5. Consider enabling 'Bypass Order Precautions for API Orders'")
                issues.append("  6. Restart TWS/Gateway after changes")
                
            return len(issues) == 0, issues
            
        except Exception as e:
            issues.append(f"Error checking API configuration: {str(e)}")
            return False, issues