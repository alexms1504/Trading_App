"""
Trade Manager
Manages the complete trade lifecycle
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from .order_builder import OrderBuilder, OrderRequest
from .order_validator import OrderValidator
from src.services import get_order_service, get_risk_service
from src.services.event_bus import EventType, Event, publish_event
from src.utils.logger import logger


class TradeManager:
    """Manages complete trade lifecycle from creation to exit"""
    
    def __init__(self):
        self.order_builder = OrderBuilder()
        self.order_validator = OrderValidator()
        self.active_trades: Dict[int, Dict[str, Any]] = {}  # order_id -> trade info
        
    def create_trade(self, trade_params: Dict) -> Tuple[bool, str, Optional[List]]:
        """
        Create a new trade with validation
        
        Args:
            trade_params: Trade parameters dictionary
            
        Returns:
            Tuple of (success, message, trades)
        """
        try:
            # Build order request
            success, order_request, errors = self.order_builder.build_from_dict(trade_params)
            if not success:
                return False, "Order build failed: " + "; ".join(errors), None
                
            # Validate order
            is_valid, messages = self.order_validator.validate_order(trade_params)
            if not is_valid:
                return False, "Order validation failed: " + "; ".join(messages), None
                
            # Get warnings from messages
            warnings = [msg for msg in messages if "Warning" in msg]
            
            # Submit order through order service
            order_service = get_order_service()
            if not order_service:
                return False, "Order service not available", None
                
            success, message, trades = order_service.create_order(trade_params)
            
            if success and trades:
                # Track active trades
                for trade in trades:
                    if hasattr(trade, 'order') and hasattr(trade.order, 'orderId'):
                        order_id = trade.order.orderId
                        self.active_trades[order_id] = {
                            'order_id': order_id,
                            'symbol': trade_params['symbol'],
                            'quantity': trade_params['quantity'],
                            'direction': trade_params['direction'],
                            'entry_price': trade_params['entry_price'],
                            'stop_loss': trade_params['stop_loss'],
                            'created_at': datetime.now(),
                            'status': 'submitted',
                            'trade_object': trade
                        }
                        
                # Publish trade created event
                publish_event(Event(
                    EventType.ORDER_SUBMITTED,
                    {
                        'symbol': trade_params['symbol'],
                        'trades': trades,
                        'warnings': warnings
                    }
                ))
                
                # Include warnings in success message if any
                if warnings:
                    message += " (with warnings: " + "; ".join(warnings) + ")"
                    
            return success, message, trades
            
        except Exception as e:
            error_msg = f"Error creating trade: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
            
    def modify_trade(self, order_id: int, modifications: Dict) -> Tuple[bool, str]:
        """
        Modify an existing trade
        
        Args:
            order_id: Order ID to modify
            modifications: Dictionary of modifications
            
        Returns:
            Tuple of (success, message)
        """
        if order_id not in self.active_trades:
            return False, "Trade not found"
            
        try:
            # TODO: Implement trade modification logic
            # This would involve canceling and replacing orders
            
            return False, "Trade modification not yet implemented"
            
        except Exception as e:
            error_msg = f"Error modifying trade: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
    def cancel_trade(self, order_id: int) -> Tuple[bool, str]:
        """
        Cancel an active trade
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Tuple of (success, message)
        """
        if order_id not in self.active_trades:
            return False, "Trade not found"
            
        try:
            order_service = get_order_service()
            if not order_service:
                return False, "Order service not available"
                
            success, message = order_service.cancel_order(order_id)
            
            if success:
                # Update trade status
                self.active_trades[order_id]['status'] = 'cancelled'
                
                # Publish trade cancelled event
                publish_event(Event(
                    EventType.ORDER_CANCELLED,
                    {
                        'order_id': order_id,
                        'symbol': self.active_trades[order_id]['symbol']
                    }
                ))
                
            return success, message
            
        except Exception as e:
            error_msg = f"Error cancelling trade: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
    def get_active_trades(self) -> List[Dict[str, Any]]:
        """Get list of active trades"""
        return list(self.active_trades.values())
        
    def get_trade_status(self, order_id: int) -> Optional[str]:
        """Get status of a specific trade"""
        if order_id in self.active_trades:
            return self.active_trades[order_id]['status']
        return None
        
    def update_trade_status(self, order_id: int, status: str):
        """Update trade status"""
        if order_id in self.active_trades:
            self.active_trades[order_id]['status'] = status
            logger.info(f"Trade {order_id} status updated to: {status}")
            
    def calculate_trade_performance(self, order_id: int, current_price: float) -> Dict[str, float]:
        """
        Calculate current performance of a trade
        
        Returns:
            Dictionary with performance metrics
        """
        if order_id not in self.active_trades:
            return {}
            
        trade = self.active_trades[order_id]
        entry_price = trade['entry_price']
        quantity = trade['quantity']
        direction = trade['direction']
        
        # Calculate P&L
        if direction == 'BUY':
            price_change = current_price - entry_price
        else:  # SELL
            price_change = entry_price - current_price
            
        dollar_pnl = price_change * quantity
        percent_pnl = (price_change / entry_price) * 100
        
        # Calculate R-multiple
        stop_loss = trade['stop_loss']
        risk_per_share = abs(entry_price - stop_loss)
        r_multiple = price_change / risk_per_share if risk_per_share > 0 else 0
        
        return {
            'current_price': current_price,
            'entry_price': entry_price,
            'dollar_pnl': dollar_pnl,
            'percent_pnl': percent_pnl,
            'r_multiple': r_multiple
        }