"""
Order Builder
Constructs trading orders with proper validation
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.utils.logger import logger


class OrderType(Enum):
    """Order types"""
    MARKET = "MKT"
    LIMIT = "LMT"
    STOP_LIMIT = "STOPLMT"
    

class OrderDirection(Enum):
    """Order directions"""
    BUY = "BUY"
    SELL = "SELL"
    

@dataclass
class OrderTarget:
    """Profit target for scaling out"""
    price: float
    percent: float  # Percentage of position
    quantity: Optional[int] = None
    

@dataclass
class OrderRequest:
    """Complete order request with all parameters"""
    symbol: str
    quantity: int
    direction: OrderDirection
    order_type: OrderType
    entry_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    limit_price: Optional[float] = None  # For STOP_LIMIT orders
    targets: Optional[List[OrderTarget]] = None
    risk_percent: float = 1.0
    account: Optional[str] = None
    

class OrderBuilder:
    """Builds and validates trading orders"""
    
    def __init__(self):
        self.reset()
        
    def reset(self):
        """Reset builder state"""
        self._symbol = None
        self._quantity = None
        self._direction = None
        self._order_type = OrderType.LIMIT
        self._entry_price = None
        self._stop_loss = None
        self._take_profit = None
        self._limit_price = None
        self._targets = []
        self._risk_percent = 1.0
        self._account = None
        
    def symbol(self, symbol: str) -> 'OrderBuilder':
        """Set symbol"""
        self._symbol = symbol.upper().strip()
        return self
        
    def quantity(self, quantity: int) -> 'OrderBuilder':
        """Set quantity"""
        self._quantity = max(1, int(quantity))
        return self
        
    def direction(self, direction: OrderDirection) -> 'OrderBuilder':
        """Set direction"""
        self._direction = direction
        return self
        
    def order_type(self, order_type: OrderType) -> 'OrderBuilder':
        """Set order type"""
        self._order_type = order_type
        return self
        
    def entry_price(self, price: float) -> 'OrderBuilder':
        """Set entry price"""
        self._entry_price = max(0.01, float(price))
        return self
        
    def stop_loss(self, price: float) -> 'OrderBuilder':
        """Set stop loss price"""
        self._stop_loss = max(0.01, float(price))
        return self
        
    def take_profit(self, price: float) -> 'OrderBuilder':
        """Set take profit price"""
        self._take_profit = max(0.01, float(price))
        return self
        
    def limit_price(self, price: float) -> 'OrderBuilder':
        """Set limit price for STOP_LIMIT orders"""
        self._limit_price = max(0.01, float(price))
        return self
        
    def add_target(self, price: float, percent: float) -> 'OrderBuilder':
        """Add a profit target"""
        target = OrderTarget(
            price=max(0.01, float(price)),
            percent=max(0, min(100, float(percent)))
        )
        self._targets.append(target)
        return self
        
    def risk_percent(self, percent: float) -> 'OrderBuilder':
        """Set risk percentage"""
        self._risk_percent = max(0.1, min(10.0, float(percent)))
        return self
        
    def account(self, account: str) -> 'OrderBuilder':
        """Set account"""
        self._account = account
        return self
        
    def build(self) -> Tuple[bool, Optional[OrderRequest], List[str]]:
        """
        Build the order request
        
        Returns:
            Tuple of (success, order_request, errors)
        """
        errors = []
        
        # Validate required fields
        if not self._symbol:
            errors.append("Symbol is required")
        if not self._quantity:
            errors.append("Quantity is required")
        if not self._direction:
            errors.append("Direction is required")
        if self._entry_price is None:
            errors.append("Entry price is required")
        if self._stop_loss is None:
            errors.append("Stop loss is required")
            
        # Validate stop loss vs entry
        if self._entry_price and self._stop_loss:
            if self._direction == OrderDirection.BUY:
                if self._stop_loss >= self._entry_price:
                    errors.append("Stop loss must be below entry for BUY orders")
            else:  # SELL
                if self._stop_loss <= self._entry_price:
                    errors.append("Stop loss must be above entry for SELL orders")
                    
        # Validate take profit
        if self._take_profit:
            if self._direction == OrderDirection.BUY:
                if self._take_profit <= self._entry_price:
                    errors.append("Take profit must be above entry for BUY orders")
            else:  # SELL
                if self._take_profit >= self._entry_price:
                    errors.append("Take profit must be below entry for SELL orders")
                    
        # Validate targets
        if self._targets:
            if self._take_profit:
                errors.append("Cannot use both single take profit and multiple targets")
                
            total_percent = sum(t.percent for t in self._targets)
            if abs(total_percent - 100) > 0.01:
                errors.append(f"Target percentages must total 100% (got {total_percent:.1f}%)")
                
            # Calculate quantities for targets
            for target in self._targets:
                target.quantity = int(self._quantity * target.percent / 100)
                
            # Validate target prices
            for i, target in enumerate(self._targets):
                if self._direction == OrderDirection.BUY:
                    if target.price <= self._entry_price:
                        errors.append(f"Target {i+1} must be above entry for BUY orders")
                else:  # SELL
                    if target.price >= self._entry_price:
                        errors.append(f"Target {i+1} must be below entry for SELL orders")
                        
        # Validate STOP_LIMIT specific
        if self._order_type == OrderType.STOP_LIMIT:
            if not self._limit_price:
                errors.append("Limit price required for STOP_LIMIT orders")
                
        if errors:
            return False, None, errors
            
        # Build order request
        order = OrderRequest(
            symbol=self._symbol,
            quantity=self._quantity,
            direction=self._direction,
            order_type=self._order_type,
            entry_price=self._entry_price,
            stop_loss=self._stop_loss,
            take_profit=self._take_profit,
            limit_price=self._limit_price,
            targets=self._targets if self._targets else None,
            risk_percent=self._risk_percent,
            account=self._account
        )
        
        return True, order, []
        
    def build_from_dict(self, params: Dict) -> Tuple[bool, Optional[OrderRequest], List[str]]:
        """Build order from dictionary parameters"""
        self.reset()
        
        # Set all parameters
        if 'symbol' in params:
            self.symbol(params['symbol'])
        if 'quantity' in params:
            self.quantity(params['quantity'])
        if 'direction' in params:
            self.direction(OrderDirection(params['direction']))
        if 'order_type' in params:
            self.order_type(OrderType(params['order_type']))
        if 'entry_price' in params:
            self.entry_price(params['entry_price'])
        if 'stop_loss' in params:
            self.stop_loss(params['stop_loss'])
        if 'take_profit' in params:
            self.take_profit(params['take_profit'])
        if 'limit_price' in params:
            self.limit_price(params['limit_price'])
        if 'risk_percent' in params:
            self.risk_percent(params['risk_percent'])
        if 'account' in params:
            self.account(params['account'])
            
        # Handle multiple targets
        if params.get('use_multiple_targets') and 'profit_targets' in params:
            for target in params['profit_targets']:
                self.add_target(target['price'], target['percent'])
                
        return self.build()