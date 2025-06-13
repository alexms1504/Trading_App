"""
Order Validator
Validates orders against risk rules and market conditions
"""

from typing import List, Tuple, Optional
from datetime import datetime

from src.services import get_risk_service, get_account_service
from src.utils.logger import logger
from config import TRADING_CONFIG


class OrderValidator:
    """Validates trading orders before submission"""
    
    def __init__(self):
        self.validation_rules = [
            self._validate_risk_limits,
            self._validate_position_sizing,
            self._validate_buying_power,
            self._validate_market_hours,
            self._validate_price_sanity
        ]
        
    def validate_order(self, order_params: dict) -> Tuple[bool, List[str]]:
        """
        Validate order against all rules
        
        Returns:
            Tuple of (is_valid, list_of_messages)
        """
        messages = []
        warnings = []
        errors = []
        
        # Run all validation rules
        for rule in self.validation_rules:
            try:
                rule_valid, rule_messages = rule(order_params)
                if not rule_valid:
                    errors.extend(rule_messages)
                else:
                    # Collect warnings (messages when valid)
                    warnings.extend(rule_messages)
            except Exception as e:
                logger.error(f"Error in validation rule {rule.__name__}: {str(e)}")
                errors.append(f"Validation error: {str(e)}")
                
        # Combine all messages
        messages.extend(errors)
        messages.extend(warnings)
        
        return len(errors) == 0, messages
        
    def _validate_risk_limits(self, order_params: dict) -> Tuple[bool, List[str]]:
        """Validate against risk limits"""
        messages = []
        
        risk_service = get_risk_service()
        if not risk_service:
            return True, ["Risk service not available - skipping risk validation"]
            
        # Use risk service validation
        is_valid, risk_messages = risk_service.validate_trade(
            symbol=order_params.get('symbol'),
            entry_price=order_params.get('entry_price', 0),
            stop_loss=order_params.get('stop_loss', 0),
            take_profit=order_params.get('take_profit', 0),
            shares=order_params.get('quantity', 0),
            direction=order_params.get('direction', 'BUY')
        )
        
        messages.extend(risk_messages)
        return is_valid, messages
        
    def _validate_position_sizing(self, order_params: dict) -> Tuple[bool, List[str]]:
        """Validate position size"""
        messages = []
        
        quantity = order_params.get('quantity', 0)
        entry_price = order_params.get('entry_price', 0)
        
        if quantity <= 0:
            messages.append("Order quantity must be greater than 0")
            return False, messages
            
        # Check max position size
        position_value = quantity * entry_price
        max_position = TRADING_CONFIG.get('max_position_size', 100000)
        
        if position_value > max_position:
            messages.append(f"Position size ${position_value:,.2f} exceeds maximum ${max_position:,.2f}")
            return False, messages
            
        # Warning for large positions
        if position_value > max_position * 0.8:
            messages.append(f"Warning: Large position size ${position_value:,.2f}")
            
        return True, messages
        
    def _validate_buying_power(self, order_params: dict) -> Tuple[bool, List[str]]:
        """Validate against available buying power"""
        messages = []
        
        account_service = get_account_service()
        if not account_service:
            return True, ["Account service not available - skipping buying power check"]
            
        quantity = order_params.get('quantity', 0)
        entry_price = order_params.get('entry_price', 0)
        position_value = quantity * entry_price
        
        buying_power = account_service.get_buying_power()
        
        if buying_power <= 0:
            messages.append("No buying power available")
            return False, messages
            
        if position_value > buying_power:
            messages.append(f"Insufficient buying power: Need ${position_value:,.2f}, have ${buying_power:,.2f}")
            return False, messages
            
        # Warning if using significant portion of buying power
        bp_usage = (position_value / buying_power) * 100
        if bp_usage > 50:
            messages.append(f"Warning: Using {bp_usage:.1f}% of available buying power")
            
        return True, messages
        
    def _validate_market_hours(self, order_params: dict) -> Tuple[bool, List[str]]:
        """Validate market hours"""
        messages = []
        
        # Get current time
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        weekday = now.weekday()
        
        # Basic market hours check (NYSE: 9:30 AM - 4:00 PM ET, Mon-Fri)
        # This is simplified - real implementation would check holidays, pre/post market, etc.
        
        if weekday > 4:  # Saturday = 5, Sunday = 6
            messages.append("Warning: Market is closed (weekend)")
            
        # Convert to ET (simplified - assumes system is in ET)
        market_open = 9 * 60 + 30  # 9:30 AM in minutes
        market_close = 16 * 60  # 4:00 PM in minutes
        current_minutes = hour * 60 + minute
        
        if current_minutes < market_open or current_minutes > market_close:
            if current_minutes < market_open - 60:  # More than 1 hour before open
                messages.append("Warning: Market is closed (pre-market)")
            elif current_minutes > market_close + 120:  # More than 2 hours after close
                messages.append("Warning: Market is closed (after-hours)")
            else:
                messages.append("Warning: Extended hours trading")
                
        return True, messages  # Always return True - just warnings
        
    def _validate_price_sanity(self, order_params: dict) -> Tuple[bool, List[str]]:
        """Validate prices are reasonable"""
        messages = []
        
        entry_price = order_params.get('entry_price', 0)
        stop_loss = order_params.get('stop_loss', 0)
        take_profit = order_params.get('take_profit', 0)
        
        # Check for extreme prices
        if entry_price > 10000:
            messages.append(f"Warning: Unusually high entry price ${entry_price:.2f}")
        elif entry_price < 0.01:
            messages.append("Entry price too low (minimum $0.01)")
            return False, messages
            
        # Check for extreme stop loss distance
        if entry_price > 0 and stop_loss > 0:
            stop_distance = abs(entry_price - stop_loss) / entry_price * 100
            if stop_distance > 20:
                messages.append(f"Warning: Stop loss is {stop_distance:.1f}% from entry")
            elif stop_distance < 0.1:
                messages.append(f"Warning: Stop loss very close to entry ({stop_distance:.2f}%)")
                
        # Check for extreme take profit
        if entry_price > 0 and take_profit > 0:
            profit_distance = abs(take_profit - entry_price) / entry_price * 100
            if profit_distance > 50:
                messages.append(f"Warning: Take profit is {profit_distance:.1f}% from entry")
                
        return True, messages