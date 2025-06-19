"""
Position Tracker
Tracks open positions and their performance
"""

from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

from src.utils.logger import logger


@dataclass
class Position:
    """Represents an open position"""
    symbol: str
    quantity: int
    entry_price: float
    entry_time: datetime
    direction: str  # 'LONG' or 'SHORT'
    stop_loss: float
    take_profit: Optional[float] = None
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    r_multiple: float = 0.0
    order_ids: List[int] = field(default_factory=list)
    
    def update_price(self, current_price: float):
        """Update current price and calculate P&L"""
        self.current_price = current_price
        
        # Calculate unrealized P&L
        if self.direction == 'LONG':
            price_change = current_price - self.entry_price
        else:  # SHORT
            price_change = self.entry_price - current_price
            
        self.unrealized_pnl = price_change * self.quantity
        
        # Calculate R-multiple
        risk_per_share = abs(self.entry_price - self.stop_loss)
        if risk_per_share > 0:
            self.r_multiple = price_change / risk_per_share
        else:
            self.r_multiple = 0.0
            
    def close_partial(self, quantity: int, exit_price: float) -> float:
        """
        Close partial position
        
        Returns:
            Realized P&L for the closed portion
        """
        if quantity > self.quantity:
            quantity = self.quantity
            
        # Calculate P&L for closed portion
        if self.direction == 'LONG':
            pnl = (exit_price - self.entry_price) * quantity
        else:  # SHORT
            pnl = (self.entry_price - exit_price) * quantity
            
        # Update position
        self.quantity -= quantity
        self.realized_pnl += pnl
        
        return pnl
        

class PositionTracker:
    """Tracks all open positions"""
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}  # symbol -> Position
        self.closed_positions: List[Position] = []
        
    def open_position(self, symbol: str, quantity: int, entry_price: float,
                     direction: str, stop_loss: float, take_profit: Optional[float] = None,
                     order_ids: Optional[List[int]] = None) -> Position:
        """Open a new position or add to existing"""
        
        symbol = symbol.upper()
        direction = 'LONG' if direction == 'BUY' else 'SHORT'
        
        if symbol in self.positions:
            # Add to existing position (averaging)
            position = self.positions[symbol]
            
            # Calculate new average entry
            total_value = (position.entry_price * position.quantity) + (entry_price * quantity)
            total_quantity = position.quantity + quantity
            position.entry_price = total_value / total_quantity
            position.quantity = total_quantity
            
            # Update stop loss (use most conservative)
            if direction == 'LONG':
                position.stop_loss = max(position.stop_loss, stop_loss)
            else:  # SHORT
                position.stop_loss = min(position.stop_loss, stop_loss)
                
            # Add order IDs
            if order_ids:
                position.order_ids.extend(order_ids)
                
            logger.info(f"Added to position {symbol}: {quantity} @ ${entry_price:.2f}")
            
        else:
            # Create new position
            position = Position(
                symbol=symbol,
                quantity=quantity,
                entry_price=entry_price,
                entry_time=datetime.now(),
                direction=direction,
                stop_loss=stop_loss,
                take_profit=take_profit,
                order_ids=order_ids or []
            )
            self.positions[symbol] = position
            logger.info(f"Opened position {symbol}: {quantity} @ ${entry_price:.2f}")
            
        return position
        
    def close_position(self, symbol: str, exit_price: float) -> Optional[float]:
        """
        Close entire position
        
        Returns:
            Total realized P&L
        """
        symbol = symbol.upper()
        if symbol not in self.positions:
            return None
            
        position = self.positions[symbol]
        position.update_price(exit_price)
        
        # Calculate total P&L
        total_pnl = position.unrealized_pnl + position.realized_pnl
        
        # Move to closed positions
        position.realized_pnl = total_pnl
        position.unrealized_pnl = 0
        position.quantity = 0
        self.closed_positions.append(position)
        
        # Remove from open positions
        del self.positions[symbol]
        
        logger.info(f"Closed position {symbol} @ ${exit_price:.2f}, P&L: ${total_pnl:.2f}")
        return total_pnl
        
    def close_partial_position(self, symbol: str, quantity: int, exit_price: float) -> Optional[float]:
        """
        Close partial position
        
        Returns:
            Realized P&L for closed portion
        """
        symbol = symbol.upper()
        if symbol not in self.positions:
            return None
            
        position = self.positions[symbol]
        pnl = position.close_partial(quantity, exit_price)
        
        # If position fully closed, move to closed list
        if position.quantity == 0:
            self.closed_positions.append(position)
            del self.positions[symbol]
            
        logger.info(f"Closed partial position {symbol}: {quantity} @ ${exit_price:.2f}, P&L: ${pnl:.2f}")
        return pnl
        
    def update_prices(self, price_updates: Dict[str, float]):
        """Update current prices for all positions"""
        for symbol, price in price_updates.items():
            if symbol in self.positions:
                self.positions[symbol].update_price(price)
                
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol"""
        return self.positions.get(symbol.upper())
        
    def get_all_positions(self) -> List[Position]:
        """Get all open positions"""
        return list(self.positions.values())
        
    def get_total_unrealized_pnl(self) -> float:
        """Get total unrealized P&L across all positions"""
        return sum(pos.unrealized_pnl for pos in self.positions.values())
        
    def get_total_realized_pnl(self) -> float:
        """Get total realized P&L (including closed positions)"""
        open_realized = sum(pos.realized_pnl for pos in self.positions.values())
        closed_realized = sum(pos.realized_pnl for pos in self.closed_positions)
        return open_realized + closed_realized
        
    def get_position_summary(self) -> Dict[str, Any]:
        """Get summary of all positions"""
        return {
            'open_positions': len(self.positions),
            'closed_positions': len(self.closed_positions),
            'total_unrealized_pnl': self.get_total_unrealized_pnl(),
            'total_realized_pnl': self.get_total_realized_pnl(),
            'positions': [
                {
                    'symbol': pos.symbol,
                    'quantity': pos.quantity,
                    'entry_price': pos.entry_price,
                    'current_price': pos.current_price,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'r_multiple': pos.r_multiple
                }
                for pos in self.positions.values()
            ]
        }