"""
Order Service
Handles order creation, validation, submission, and management
"""

from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime

from src.services.base_service import BaseService
from src.core.order_manager import OrderManager
from src.services.ib_connection_service import ib_connection_manager
from src.utils.logger import logger
from config import TRADING_CONFIG


class OrderService(BaseService):
    """Service for managing trading orders"""
    
    def __init__(self):
        super().__init__("OrderService")
        self.ib_manager = ib_connection_manager
        self.order_manager = None
        self.order_update_callbacks: List[Callable] = []
        self._active_orders_cache: List[Dict] = []
        
    def initialize(self) -> bool:
        """Initialize the order service"""
        try:
            # Call parent initialization first
            if not super().initialize():
                return False
                
            logger.info("Initializing OrderService...")
            
            # Initialize order manager
            self.order_manager = OrderManager()
            
            self._initialized = True
            logger.info("OrderService initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OrderService: {str(e)}")
            self._initialized = False
            return False
            
    def cleanup(self):
        """Cleanup order service resources"""
        try:
            logger.info("Cleaning up OrderService...")
            
            self.order_manager = None
            self.order_update_callbacks.clear()
            self._active_orders_cache.clear()
            
            self._initialized = False
            logger.info("OrderService cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error cleaning up OrderService: {str(e)}")
            
    def set_risk_calculator(self, account_manager):
        """Legacy method - risk calculations now handled through RiskService"""
        # Kept for compatibility during migration
        logger.info("Risk calculator request redirected to RiskService")
    
    def validate_trade(self, **kwargs) -> Tuple[bool, List[str]]:
        """Validate trade using RiskService"""
        from src.services.service_registry import get_risk_service
        risk_service = get_risk_service()
        if not risk_service:
            return False, ["Risk service not available"]
        return risk_service.validate_trade(**kwargs)
    
    def calculate_r_multiple(self, entry_price: float, stop_loss: float, target_price: float, 
                           order_type: str = 'LMT', limit_price: Optional[float] = None) -> float:
        """Calculate R-multiple for a trade"""
        from src.services.service_registry import get_risk_service
        risk_service = get_risk_service()
        if not risk_service:
            return 0.0
        return risk_service.calculate_r_multiple(entry_price, stop_loss, target_price, order_type, limit_price)
    
    def check_api_configuration(self) -> Tuple[bool, List[str]]:
        """Check API configuration"""
        if not self.order_manager:
            return False, ["Order manager not available"]
        return self.order_manager.check_api_configuration()
            
    def register_order_update_callback(self, callback: Callable):
        """Register a callback for order updates"""
        if callback not in self.order_update_callbacks:
            self.order_update_callbacks.append(callback)
            logger.info(f"Registered order update callback: {callback}")
            
    def unregister_order_update_callback(self, callback: Callable):
        """Unregister an order update callback"""
        if callback in self.order_update_callbacks:
            self.order_update_callbacks.remove(callback)
            logger.info(f"Unregistered order update callback: {callback}")
            
    def validate_order(self, order_params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate order parameters
        
        Args:
            order_params: Dictionary containing order parameters
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # Required fields
            required_fields = ['symbol', 'quantity', 'direction', 'order_type', 
                             'entry_price', 'stop_loss']
            
            for field in required_fields:
                if field not in order_params:
                    errors.append(f"Missing required field: {field}")
                    
            if errors:
                return False, errors
                
            # Validate symbol
            symbol = order_params.get('symbol', '')
            if not symbol or len(symbol) > 10:
                errors.append("Invalid symbol")
                
            # Validate quantity
            quantity = order_params.get('quantity', 0)
            if quantity <= 0:
                errors.append("Quantity must be greater than 0")
                
            # Validate direction
            direction = order_params.get('direction', '')
            if direction not in ['BUY', 'SELL']:
                errors.append("Direction must be 'BUY' or 'SELL'")
                
            # Validate order type
            order_type = order_params.get('order_type', '')
            if order_type not in ['LMT', 'MKT', 'STOPLMT']:
                errors.append("Invalid order type")
                
            # Validate prices
            entry_price = order_params.get('entry_price', 0)
            stop_loss = order_params.get('stop_loss', 0)
            
            if entry_price <= 0:
                errors.append("Entry price must be greater than 0")
                
            if stop_loss <= 0:
                errors.append("Stop loss must be greater than 0")
                
            # Direction-specific validation
            if direction == 'BUY':
                if stop_loss >= entry_price:
                    errors.append("Stop loss must be below entry price for BUY orders")
            else:  # SELL
                if stop_loss <= entry_price:
                    errors.append("Stop loss must be above entry price for SELL orders")
                    
            # Validate take profit if not using multiple targets
            if not order_params.get('use_multiple_targets', False):
                take_profit = order_params.get('take_profit', 0)
                if take_profit <= 0:
                    errors.append("Take profit must be greater than 0")
                    
                if direction == 'BUY':
                    if take_profit <= entry_price:
                        errors.append("Take profit must be above entry price for BUY orders")
                else:  # SELL
                    if take_profit >= entry_price:
                        errors.append("Take profit must be below entry price for SELL orders")
                        
            # Validate multiple targets if used
            if order_params.get('use_multiple_targets', False):
                profit_targets = order_params.get('profit_targets', [])
                if not profit_targets:
                    errors.append("Profit targets required when using multiple targets")
                else:
                    total_percent = sum(target.get('percent', 0) for target in profit_targets)
                    if total_percent != 100:
                        errors.append(f"Profit target percentages must total 100% (got {total_percent}%)")
                        
                    for i, target in enumerate(profit_targets):
                        target_price = target.get('price', 0)
                        if target_price <= 0:
                            errors.append(f"Target {i+1} price must be greater than 0")
                            
                        if direction == 'BUY':
                            if target_price <= entry_price:
                                errors.append(f"Target {i+1} must be above entry price for BUY orders")
                        else:  # SELL
                            if target_price >= entry_price:
                                errors.append(f"Target {i+1} must be below entry price for SELL orders")
                                
            # Validate STOP LIMIT specific fields
            if order_type == 'STOPLMT':
                limit_price = order_params.get('limit_price', 0)
                if limit_price <= 0:
                    errors.append("Limit price required for STOP LIMIT orders")
                    
            return len(errors) == 0, errors
            
        except Exception as e:
            logger.error(f"Error validating order: {str(e)}")
            errors.append(f"Validation error: {str(e)}")
            return False, errors
            
    def create_order(self, order_params: Dict[str, Any]) -> Tuple[bool, str, Optional[List]]:
        """
        Create and submit an order
        
        Args:
            order_params: Dictionary containing order parameters
            
        Returns:
            Tuple of (success, message, trades)
        """
        if not self._check_initialized():
            return False, "Order service not initialized", None
            
        if not self.order_manager:
            return False, "Order manager not available", None
            
        # Validate order first
        is_valid, errors = self.validate_order(order_params)
        if not is_valid:
            return False, "Order validation failed: " + "; ".join(errors), None
            
        try:
            # Check if using multiple targets
            if order_params.get('use_multiple_targets', False):
                # Submit multiple target order
                success, message, trades = self.order_manager.submit_multiple_target_order(
                    symbol=order_params['symbol'],
                    quantity=order_params['quantity'],
                    entry_price=order_params['entry_price'],
                    stop_loss=order_params['stop_loss'],
                    profit_targets=order_params['profit_targets'],
                    direction=order_params['direction'],
                    order_type=order_params['order_type'],
                    account=order_params.get('account'),
                    limit_price=order_params.get('limit_price')
                )
            else:
                # Submit single target bracket order
                success, message, trades = self.order_manager.submit_bracket_order(
                    symbol=order_params['symbol'],
                    quantity=order_params['quantity'],
                    entry_price=order_params['entry_price'],
                    stop_loss=order_params['stop_loss'],
                    take_profit=order_params['take_profit'],
                    direction=order_params['direction'],
                    order_type=order_params['order_type'],
                    account=order_params.get('account'),
                    limit_price=order_params.get('limit_price')
                )
                
            if success:
                # Update active orders cache
                self._update_active_orders_cache()
                
                # Notify callbacks
                self._notify_order_update({
                    'event': 'order_created',
                    'symbol': order_params['symbol'],
                    'trades': trades,
                    'message': message
                })
                
            return success, message, trades
            
        except Exception as e:
            error_msg = f"Error creating order: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
            
    def cancel_order(self, order_id: int) -> Tuple[bool, str]:
        """Cancel an order by ID"""
        if not self._check_initialized():
            return False, "Order service not initialized"
            
        if not self.order_manager:
            return False, "Order manager not available"
            
        try:
            success, message = self.order_manager.cancel_order(order_id)
            
            if success:
                # Update active orders cache
                self._update_active_orders_cache()
                
                # Notify callbacks
                self._notify_order_update({
                    'event': 'order_cancelled',
                    'order_id': order_id,
                    'message': message
                })
                
            return success, message
            
        except Exception as e:
            error_msg = f"Error cancelling order: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
    def get_active_orders(self) -> List[Dict[str, Any]]:
        """Get list of active orders"""
        if self.order_manager:
            self._active_orders_cache = self.order_manager.get_active_orders()
        return self._active_orders_cache
        
    def get_order_status(self, order_id: int) -> Optional[str]:
        """Get status of a specific order"""
        if self.order_manager:
            return self.order_manager.get_order_status(order_id)
        return None
        
    def clear_filled_orders(self):
        """Remove filled and cancelled orders from active orders"""
        if self.order_manager:
            self.order_manager.clear_filled_orders()
            self._update_active_orders_cache()
            
    def get_order_history(self) -> List[Dict[str, Any]]:
        """Get order history"""
        if self.order_manager:
            return self.order_manager.order_history
        return []
        
    def calculate_order_risk(self, order_params: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate risk metrics for an order
        
        Returns:
            Dictionary containing risk metrics
        """
        try:
            entry_price = order_params.get('entry_price', 0)
            stop_loss = order_params.get('stop_loss', 0)
            quantity = order_params.get('quantity', 0)
            
            # Calculate risk per share
            risk_per_share = abs(entry_price - stop_loss)
            
            # Calculate total dollar risk
            dollar_risk = risk_per_share * quantity
            
            # Calculate position value
            position_value = entry_price * quantity
            
            # Calculate R-multiple for take profit
            r_multiple = 0
            if not order_params.get('use_multiple_targets', False):
                take_profit = order_params.get('take_profit', 0)
                if risk_per_share > 0:
                    profit_distance = abs(take_profit - entry_price)
                    r_multiple = profit_distance / risk_per_share
                    
            return {
                'risk_per_share': risk_per_share,
                'dollar_risk': dollar_risk,
                'position_value': position_value,
                'r_multiple': r_multiple,
                'risk_reward_ratio': r_multiple  # Same as R-multiple
            }
            
        except Exception as e:
            logger.error(f"Error calculating order risk: {str(e)}")
            return {}
            
    def _update_active_orders_cache(self):
        """Update the active orders cache"""
        self._active_orders_cache = self.get_active_orders()
        
    def _notify_order_update(self, update_data: Dict[str, Any]):
        """Notify all registered callbacks of order update"""
        for callback in self.order_update_callbacks:
            try:
                callback(update_data)
            except Exception as e:
                logger.error(f"Error in order update callback: {str(e)}")
                
    def get_confirmation_data(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get order confirmation data for display
        
        Returns:
            Dictionary containing formatted order details
        """
        try:
            risk_metrics = self.calculate_order_risk(order_params)
            
            confirmation_data = {
                'symbol': order_params.get('symbol', ''),
                'direction': order_params.get('direction', ''),
                'quantity': order_params.get('quantity', 0),
                'order_type': order_params.get('order_type', ''),
                'entry_price': order_params.get('entry_price', 0),
                'stop_loss': order_params.get('stop_loss', 0),
                'position_value': risk_metrics.get('position_value', 0),
                'dollar_risk': risk_metrics.get('dollar_risk', 0),
                'risk_per_share': risk_metrics.get('risk_per_share', 0)
            }
            
            if order_params.get('use_multiple_targets', False):
                confirmation_data['profit_targets'] = order_params.get('profit_targets', [])
            else:
                confirmation_data['take_profit'] = order_params.get('take_profit', 0)
                confirmation_data['r_multiple'] = risk_metrics.get('r_multiple', 0)
                
            if order_params.get('order_type') == 'STOPLMT':
                confirmation_data['limit_price'] = order_params.get('limit_price', 0)
                
            return confirmation_data
            
        except Exception as e:
            logger.error(f"Error getting confirmation data: {str(e)}")
            return {}