"""
Order Manager - Fixed Version
Handles order creation, submission, and management for MVP
Fixed to properly handle IB bracket order structure
"""

from typing import Dict, Optional, List, Tuple
from datetime import datetime
import asyncio

from ib_async import Stock, Order, Trade, LimitOrder, StopOrder, MarketOrder, BracketOrder, StopLimitOrder, util

from src.utils.logger import logger
from src.services.ib_connection_service import ib_connection_manager


class OrderManager:
    """
    Fixed order manager for MVP - handles bracket order creation and submission
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
                           account: Optional[str] = None,
                           limit_price: Optional[float] = None) -> Tuple[bool, str, Optional[List[Trade]]]:
        """
        Submit a bracket order (parent + stop loss + take profit)
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            entry_price: Entry price (for limit orders) or stop price (for stop limit orders)
            stop_loss: Stop loss price
            take_profit: Take profit price
            direction: 'BUY' or 'SELL'
            order_type: 'LMT', 'MKT', or 'STOPLMT'
            account: Account to use (optional)
            limit_price: Limit price for STOP LIMIT orders (optional)
            
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
            if limit_price is not None:
                limit_price = self.round_price_to_tick_size(limit_price, symbol)
            
            logger.info(f"Rounded prices - Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit}")
            if limit_price is not None:
                logger.info(f"Rounded limit price: {limit_price}")
            
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
            qualified_contracts = ib.qualifyContracts(contract)
            if qualified_contracts:
                contract = qualified_contracts[0]
                logger.info(f"Contract qualified: {contract.symbol} on {contract.exchange}")
            else:
                logger.error(f"Failed to qualify contract for {symbol}")
                return False, f"Failed to qualify contract for {symbol}", None
            
            # Create bracket order using IB's method
            logger.info(f"Creating bracket order: {direction} {quantity} shares of {symbol}")
            logger.info(f"  Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit}")
            
            # Create bracket order - always start with IB's bracketOrder method
            bracket = ib.bracketOrder(
                action=direction,
                quantity=quantity,
                limitPrice=entry_price,
                takeProfitPrice=take_profit,
                stopLossPrice=stop_loss
            )
            
            # CRITICAL: Set up OCA group for child orders
            # IB's bracketOrder doesn't always set OCA groups properly
            if len(bracket) >= 3:
                # Log the actual order structure to debug
                logger.info("Analyzing bracket order structure:")
                for i, order in enumerate(bracket):
                    logger.info(f"  bracket[{i}]: orderType={order.orderType}, action={order.action}, "
                              f"parentId={order.parentId}, transmit={order.transmit}")
                
                # Create unique OCA group
                oca_group = f"OCA_{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                
                # IB's bracketOrder returns: [parent, takeProfit, stopLoss]
                # But let's verify by checking orderType
                parent_idx = None
                tp_idx = None
                sl_idx = None
                
                for i, order in enumerate(bracket):
                    if order.orderType == 'LMT' and order.parentId == 0:
                        parent_idx = i
                    elif order.orderType == 'LMT' and order.parentId > 0:
                        tp_idx = i
                    elif order.orderType == 'STP' and order.parentId > 0:
                        sl_idx = i
                
                logger.info(f"Identified order indices - Parent: {parent_idx}, TP: {tp_idx}, SL: {sl_idx}")
                
                # Set OCA on take profit and stop loss ONLY (not parent)
                if tp_idx is not None:
                    bracket[tp_idx].ocaGroup = oca_group
                    bracket[tp_idx].ocaType = 1
                if sl_idx is not None:
                    bracket[sl_idx].ocaGroup = oca_group
                    bracket[sl_idx].ocaType = 1
                
                logger.info(f"Set OCA group '{oca_group}' on child orders")
                
                # Verify child orders have opposite action
                opposite_action = 'SELL' if direction == 'BUY' else 'BUY'
                for i in range(1, len(bracket)):
                    if bracket[i].action != opposite_action:
                        logger.warning(f"Child order {i} has wrong action: {bracket[i].action}, should be {opposite_action}")
                        bracket[i].action = opposite_action
                        logger.info(f"Corrected child order {i} action to {opposite_action}")
            
            # Now modify the parent order based on order type
            if order_type == 'MKT':
                # Modify parent to be a market order
                bracket[0].orderType = 'MKT'
                bracket[0].lmtPrice = None
                logger.info("Modified parent order to MARKET order")
                
            elif order_type == 'STOPLMT':
                # Modify parent to be a stop limit order
                bracket[0].orderType = 'STP LMT'
                bracket[0].lmtPrice = limit_price  # Limit price when stop triggers
                bracket[0].auxPrice = entry_price  # Stop trigger price
                logger.info(f"Modified parent to STOP LIMIT - Stop: {entry_price}, Limit: {limit_price}")
                
            # else: LMT - no modification needed, already a limit order
            
            # Log the bracket order details
            logger.info(f"Bracket order created with {len(bracket)} orders:")
            logger.info(f"Bracket structure: Parent[0], TakeProfit[1], StopLoss[2]")
            for i, order in enumerate(bracket):
                order_name = ["Parent", "TakeProfit", "StopLoss"][i] if i < 3 else f"Order{i}"
                logger.info(f"  {order_name}: Type={order.orderType}, Action={order.action}, "
                          f"Qty={order.totalQuantity}, ParentId={order.parentId}, "
                          f"OCA={order.ocaGroup}, Transmit={order.transmit}")
                if hasattr(order, 'lmtPrice') and order.lmtPrice is not None:
                    logger.info(f"    LimitPrice={order.lmtPrice}")
                if hasattr(order, 'auxPrice') and order.auxPrice is not None:
                    logger.info(f"    StopPrice={order.auxPrice}")
                
            # Set account on all orders if specified
            target_account = account or self.ib_manager.get_active_account()
            if target_account:
                for order in bracket:
                    order.account = target_account
                logger.info(f"Set account {target_account} on all bracket orders")
                
            # Verify transmit flags and parent relationships
            # IB's bracketOrder should set these correctly:
            # Parent: transmit=False, TP: transmit=False, SL: transmit=True
            if len(bracket) >= 3:
                logger.info(f"Transmit flags: Parent={bracket[0].transmit}, TP={bracket[1].transmit}, SL={bracket[2].transmit}")
                
                # Ensure parent order has an ID
                if not hasattr(bracket[0], 'orderId') or bracket[0].orderId == 0:
                    bracket[0].orderId = ib.client.getReqId()
                    logger.info(f"Assigned order ID {bracket[0].orderId} to parent order")
                
                parent_id = bracket[0].orderId
                
                # Ensure child orders reference the parent
                for i in range(1, len(bracket)):
                    if bracket[i].parentId == 0:
                        bracket[i].parentId = parent_id
                        logger.info(f"Set parentId={parent_id} on child order {i}")
                
                # Only adjust transmit flags if needed
                if bracket[0].transmit or bracket[1].transmit or not bracket[2].transmit:
                    logger.warning("Adjusting transmit flags...")
                    bracket[0].transmit = False
                    bracket[1].transmit = False  
                    bracket[2].transmit = True
                    logger.info("Transmit flags adjusted")
                
            # Place all orders in the bracket
            trades = []
            logger.info("Submitting orders to IB...")
            
            # Final verification before submission
            logger.info("FINAL ORDER STRUCTURE BEFORE SUBMISSION:")
            for i, order in enumerate(bracket):
                order_name = ["Parent", "TakeProfit", "StopLoss"][i] if i < 3 else f"Order{i}"
                logger.info(f"  {order_name} [{i}]:")
                logger.info(f"    OrderType: {order.orderType}")
                logger.info(f"    Action: {order.action}")
                logger.info(f"    Quantity: {order.totalQuantity}")
                logger.info(f"    ParentId: {order.parentId}")
                logger.info(f"    OCA Group: '{order.ocaGroup}'")
                logger.info(f"    OCA Type: {getattr(order, 'ocaType', 'Not set')}")
                logger.info(f"    Transmit: {order.transmit}")
                if hasattr(order, 'lmtPrice') and order.lmtPrice is not None:
                    logger.info(f"    Limit Price: {order.lmtPrice}")
                if hasattr(order, 'auxPrice') and order.auxPrice is not None:
                    logger.info(f"    Stop Price: {order.auxPrice}")
            
            for i, order in enumerate(bracket):
                order_name = ["Parent", "TakeProfit", "StopLoss"][i] if i < 3 else f"Order{i}"
                logger.info(f"Placing {order_name} order...")
                trade = ib.placeOrder(contract, order)
                trades.append(trade)
                self.active_orders[trade.order.orderId] = trade
                logger.info(f"Placed {order_name} - ID: {trade.order.orderId}, Status: {trade.orderStatus.status if trade.orderStatus else 'Unknown'}")
            
            # Give IB time to process the orders
            logger.info("Waiting for IB to process orders...")
            util.run(asyncio.sleep(1))
            
            # Check order statuses after submission
            logger.info("Order statuses after submission:")
            needs_confirmation = False
            cancelled_orders = 0
            
            for i, trade in enumerate(trades):
                order_name = ["Parent", "TakeProfit", "StopLoss"][i] if i < 3 else f"Order{i}"
                status = trade.orderStatus.status if trade.orderStatus else 'Unknown'
                logger.info(f"  {order_name} (ID={trade.order.orderId}): Status={status}")
                
                if status == 'PreSubmitted':
                    logger.info(f"    Order is PreSubmitted (waiting for market hours or confirmation)")
                    needs_confirmation = True
                elif status == 'Cancelled':
                    cancelled_orders += 1
                    logger.warning(f"    Order was CANCELLED")
                elif status == 'Inactive':
                    logger.warning(f"    Order is INACTIVE - may need confirmation in TWS")
                    needs_confirmation = True
                    
            # Provide user guidance based on order status
            if cancelled_orders > 0:
                logger.warning(f"WARNING: {cancelled_orders} orders were cancelled. Check TWS for details.")
            
            if needs_confirmation:
                logger.warning("WARNING: Orders may require manual confirmation in TWS.")
                logger.warning("Check: TWS -> Configuration -> API -> Settings -> 'Bypass Order Precautions for API Orders'")
                
            # Check if all orders failed
            active_orders = sum(1 for trade in trades if trade.orderStatus and trade.orderStatus.status not in ['Cancelled', 'Inactive'])
            if active_orders == 0:
                logger.error("ERROR: All bracket orders were cancelled or inactive!")
                return False, "All orders were cancelled - check TWS configuration", trades
                
            # Log summary
            logger.info(f"Bracket order submitted for {symbol}:")
            if len(trades) >= 3:
                parent_order = trades[0].order
                tp_order = trades[1].order
                sl_order = trades[2].order
                
                logger.info(f"  Parent: {parent_order.orderType} {parent_order.action} {quantity} @ "
                          f"{'MKT' if order_type == 'MKT' else entry_price}")
                logger.info(f"  Take Profit: {tp_order.orderType} {tp_order.action} {quantity} @ {take_profit}")
                logger.info(f"  Stop Loss: {sl_order.orderType} {sl_order.action} {quantity} @ {stop_loss}")
                
            # Log order IDs
            parent_id = trades[0].order.orderId if trades else None
            logger.info(f"Bracket order submission complete for {symbol}")
            logger.info(f"Total orders placed: {len(trades)}")
            if len(trades) >= 3:
                logger.info(f"Parent: {trades[0].order.orderId}, TP: {trades[1].order.orderId}, SL: {trades[2].order.orderId}")
            
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
                                   account: Optional[str] = None,
                                   limit_price: Optional[float] = None) -> Tuple[bool, str, Optional[List[Trade]]]:
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
            qualified_contracts = ib.qualifyContracts(contract)
            if qualified_contracts:
                contract = qualified_contracts[0]
                logger.info(f"Contract qualified for multiple targets: {contract.symbol} on {contract.exchange}")
            else:
                logger.error(f"Failed to qualify contract for {symbol}")
                return False, f"Failed to qualify contract for {symbol}", None
            
            # Set account
            target_account = account or self.ib_manager.get_active_account()
            
            # Create separate bracket orders for each profit target
            all_trades = []
            bracket_groups = []
            
            logger.info(f"Creating {len(profit_targets)} separate bracket orders...")
            
            for i, target in enumerate(profit_targets):
                # Use the pre-calculated quantity from order assistant (handles rounding correctly)
                target_quantity = target.get('quantity', int(quantity * target['percent'] / 100))
                if target_quantity <= 0:
                    continue
                    
                logger.info(f"Creating bracket {i+1}: {target_quantity} shares @ {target['price']} ({target['percent']}%) [using corrected allocation]")
                
                # Create bracket order for this target
                bracket = ib.bracketOrder(
                    action=direction,
                    quantity=target_quantity,
                    limitPrice=entry_price,
                    takeProfitPrice=target['price'],
                    stopLossPrice=stop_loss
                )
                
                # Set up OCA group for this bracket
                if len(bracket) >= 3:
                    oca_group = f"OCA_{symbol}_{i}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                    bracket[1].ocaGroup = oca_group  # Take profit
                    bracket[2].ocaGroup = oca_group  # Stop loss
                    bracket[1].ocaType = 1
                    bracket[2].ocaType = 1
                    logger.info(f"Set OCA group '{oca_group}' for bracket {i+1}")
                
                # Modify for different order types
                if order_type == 'MKT':
                    bracket[0].orderType = 'MKT'
                    bracket[0].lmtPrice = None
                elif order_type == 'STOPLMT':
                    bracket[0].orderType = 'STP LMT'
                    bracket[0].lmtPrice = limit_price
                    bracket[0].auxPrice = entry_price
                    
                # Set account on all orders if specified
                if target_account:
                    for order in bracket:
                        order.account = target_account
                    
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
                util.run(asyncio.sleep(0.5))
            
            # Give IB time to process all orders
            logger.info("Waiting for IB to process all bracket orders...")
            util.run(asyncio.sleep(2))
            
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
            if trade and hasattr(trade, 'orderStatus') and trade.orderStatus and trade.orderStatus.status not in ['Filled', 'Cancelled', 'Inactive']:
                active.append({
                    'order_id': order_id,
                    'symbol': trade.contract.symbol,
                    'action': trade.order.action,
                    'quantity': trade.order.totalQuantity,
                    'status': trade.orderStatus.status if (trade and hasattr(trade, 'orderStatus') and trade.orderStatus) else 'Unknown',
                    'filled': trade.orderStatus.filled if (trade and hasattr(trade, 'orderStatus') and trade.orderStatus) else 0,
                    'remaining': trade.orderStatus.remaining if (trade and hasattr(trade, 'orderStatus') and trade.orderStatus) else 0
                })
        return active
        
    def get_order_status(self, order_id: int) -> Optional[str]:
        """Get status of a specific order"""
        if order_id in self.active_orders:
            trade = self.active_orders[order_id]
            if trade and hasattr(trade, 'orderStatus') and trade.orderStatus:
                return trade.orderStatus.status
            return 'Unknown'
        return None
        
    def clear_filled_orders(self):
        """Remove filled and cancelled orders from active orders"""
        to_remove = []
        for order_id, trade in self.active_orders.items():
            if trade and hasattr(trade, 'orderStatus') and trade.orderStatus and trade.orderStatus.status in ['Filled', 'Cancelled', 'Inactive']:
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