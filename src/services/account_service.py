"""
Account Service
Manages account data, positions, and portfolio information
"""

from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime
import asyncio
from ib_async import util

from src.services.base_service import BaseService
from src.services.account_manager_service import AccountManager
from src.services.ib_connection_service import ib_connection_manager
from src.utils.logger import logger


class AccountService(BaseService):
    """Service for managing account-related operations"""
    
    def __init__(self):
        super().__init__("AccountService")
        self.ib_manager = ib_connection_manager
        self.account_manager = None
        self.account_update_callbacks: List[Callable] = []
        self.position_update_callbacks: List[Callable] = []
        self._account_data_cache: Dict[str, Any] = {}
        self._positions_cache: List[Dict] = []
        
    def initialize(self) -> bool:
        """Initialize the account service"""
        try:
            # Call parent initialization first
            if not super().initialize():
                return False
                
            logger.info("Initializing AccountService...")
            
            # Initialize account manager
            self.account_manager = AccountManager()
            
            self._initialized = True
            logger.info("AccountService initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize AccountService: {str(e)}")
            self._initialized = False
            return False
            
    def cleanup(self):
        """Cleanup account service resources"""
        try:
            logger.info("Cleaning up AccountService...")
            
            self.account_manager = None
            self.account_update_callbacks.clear()
            self.position_update_callbacks.clear()
            self._account_data_cache.clear()
            self._positions_cache.clear()
            
            self._initialized = False
            logger.info("AccountService cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error cleaning up AccountService: {str(e)}")
            
    def register_account_update_callback(self, callback: Callable):
        """Register a callback for account updates"""
        if callback not in self.account_update_callbacks:
            self.account_update_callbacks.append(callback)
            logger.info(f"Registered account update callback: {callback}")
            
    def unregister_account_update_callback(self, callback: Callable):
        """Unregister an account update callback"""
        if callback in self.account_update_callbacks:
            self.account_update_callbacks.remove(callback)
            logger.info(f"Unregistered account update callback: {callback}")
            
    def register_position_update_callback(self, callback: Callable):
        """Register a callback for position updates"""
        if callback not in self.position_update_callbacks:
            self.position_update_callbacks.append(callback)
            logger.info(f"Registered position update callback: {callback}")
            
    def unregister_position_update_callback(self, callback: Callable):
        """Unregister a position update callback"""
        if callback in self.position_update_callbacks:
            self.position_update_callbacks.remove(callback)
            logger.info(f"Unregistered position update callback: {callback}")
            
    def update_account_data(self) -> bool:
        """Update account data from IB"""
        if not self._check_initialized():
            return False
            
        if not self.account_manager:
            logger.error("Account manager not initialized")
            return False
            
        try:
            # Get account values synchronously from cached data
            # The account manager already receives real-time updates
            success = True
            
            if success:
                # Cache the data
                self._account_data_cache = {
                    'total_cash': self.account_manager.get_total_cash_value(),
                    'net_liquidation': self.account_manager.get_net_liquidation(),
                    'buying_power': self.account_manager.get_buying_power(),
                    'total_positions_value': self.account_manager.get_total_positions_value(),
                    'daily_pnl': self.account_manager.get_daily_pnl(),
                    'unrealized_pnl': self.account_manager.get_unrealized_pnl(),
                    'realized_pnl': self.account_manager.get_realized_pnl(),
                    'timestamp': datetime.now()
                }
                
                # Notify callbacks
                self._notify_account_update(self._account_data_cache)
                
                logger.info("Account data updated successfully")
                return True
            else:
                logger.error("Failed to update account data")
                return False
                
        except Exception as e:
            logger.error(f"Error updating account data: {str(e)}")
            return False
            
    def update_positions(self) -> bool:
        """Update positions from IB"""
        if not self._check_initialized():
            return False
            
        if not self.account_manager:
            logger.error("Account manager not initialized")
            return False
            
        try:
            # Update positions
            success = self.account_manager.update_positions()
            
            if success:
                # Get formatted positions
                positions = self.get_positions()
                
                # Cache the positions
                self._positions_cache = positions
                
                # Notify callbacks
                self._notify_position_update(positions)
                
                logger.info(f"Updated {len(positions)} positions")
                return True
            else:
                logger.error("Failed to update positions")
                return False
                
        except Exception as e:
            logger.error(f"Error updating positions: {str(e)}")
            return False
            
    def get_account_value(self) -> float:
        """Get current account value (net liquidation)"""
        if self.account_manager:
            return self.account_manager.get_net_liquidation()
        return self._account_data_cache.get('net_liquidation', 0.0)
        
    def get_buying_power(self) -> float:
        """Get current buying power"""
        if self.account_manager:
            return self.account_manager.get_buying_power()
        return self._account_data_cache.get('buying_power', 0.0)
        
    def get_cash_balance(self) -> float:
        """Get current cash balance"""
        if self.account_manager:
            return self.account_manager.get_total_cash_value()
        return self._account_data_cache.get('total_cash', 0.0)
        
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        if not self.account_manager:
            return self._positions_cache
            
        positions = []
        for position in self.account_manager.positions.values():
            positions.append({
                'symbol': position.contract.symbol,
                'position': position.position,
                'avg_cost': position.avgCost,
                'market_price': getattr(position, 'marketPrice', 0),
                'market_value': getattr(position, 'marketValue', 0),
                'unrealized_pnl': getattr(position, 'unrealizedPNL', 0),
                'realized_pnl': getattr(position, 'realizedPNL', 0)
            })
            
        return positions
        
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get position for a specific symbol"""
        positions = self.get_positions()
        for pos in positions:
            if pos['symbol'] == symbol:
                return pos
        return None
        
    def get_daily_pnl(self) -> float:
        """Get daily P&L"""
        if self.account_manager:
            return self.account_manager.get_daily_pnl()
        return self._account_data_cache.get('daily_pnl', 0.0)
        
    def get_unrealized_pnl(self) -> float:
        """Get unrealized P&L"""
        if self.account_manager:
            return self.account_manager.get_unrealized_pnl()
        return self._account_data_cache.get('unrealized_pnl', 0.0)
        
    def get_realized_pnl(self) -> float:
        """Get realized P&L"""
        if self.account_manager:
            return self.account_manager.get_realized_pnl()
        return self._account_data_cache.get('realized_pnl', 0.0)
        
    def calculate_position_size(self, 
                              entry_price: float,
                              stop_loss: float,
                              risk_percent: float) -> int:
        """
        Calculate position size based on risk parameters
        
        Args:
            entry_price: Entry price per share
            stop_loss: Stop loss price per share
            risk_percent: Risk percentage of account
            
        Returns:
            Number of shares
        """
        try:
            account_value = self.get_account_value()
            if account_value <= 0:
                logger.warning("Invalid account value for position sizing")
                return 0
                
            # Calculate risk per share
            risk_per_share = abs(entry_price - stop_loss)
            if risk_per_share <= 0:
                logger.warning("Invalid risk per share")
                return 0
                
            # Calculate dollar risk
            dollar_risk = account_value * (risk_percent / 100.0)
            
            # Calculate position size
            shares = int(dollar_risk / risk_per_share)
            
            # Validate against buying power
            position_value = shares * entry_price
            buying_power = self.get_buying_power()
            
            if position_value > buying_power:
                # Adjust to fit within buying power
                max_shares = int(buying_power / entry_price)
                logger.warning(f"Position size {shares} exceeds buying power, reducing to {max_shares}")
                shares = max_shares
                
            return max(0, shares)
            
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return 0
            
    def _notify_account_update(self, account_data: Dict[str, Any]):
        """Notify all registered callbacks of account update"""
        for callback in self.account_update_callbacks:
            try:
                callback(account_data)
            except Exception as e:
                logger.error(f"Error in account update callback: {str(e)}")
                
    def _notify_position_update(self, positions: List[Dict[str, Any]]):
        """Notify all registered callbacks of position update"""
        for callback in self.position_update_callbacks:
            try:
                callback(positions)
            except Exception as e:
                logger.error(f"Error in position update callback: {str(e)}")
                
    def get_account_summary(self) -> Dict[str, Any]:
        """Get comprehensive account summary"""
        return {
            'account_value': self.get_account_value(),
            'buying_power': self.get_buying_power(),
            'cash_balance': self.get_cash_balance(),
            'daily_pnl': self.get_daily_pnl(),
            'unrealized_pnl': self.get_unrealized_pnl(),
            'realized_pnl': self.get_realized_pnl(),
            'positions_count': len(self.get_positions()),
            'positions_value': self._account_data_cache.get('total_positions_value', 0.0),
            'last_update': self._account_data_cache.get('timestamp', None)
        }
        
    def is_position_size_valid(self, symbol: str, shares: int, price: float) -> Tuple[bool, str]:
        """
        Validate if a position size is valid
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            position_value = shares * price
            buying_power = self.get_buying_power()
            
            if position_value > buying_power:
                return False, f"Insufficient buying power: ${buying_power:,.2f} available, ${position_value:,.2f} required"
                
            # Check if we already have a position
            existing_position = self.get_position(symbol)
            if existing_position:
                return True, f"Adding to existing position of {existing_position['position']} shares"
                
            return True, ""
            
        except Exception as e:
            logger.error(f"Error validating position size: {str(e)}")
            return False, "Error validating position size"