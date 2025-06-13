"""
Simplified AccountService - Direct delegation to AccountManagerService
This replaces the complex AccountService with clean delegation
"""

from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime
import asyncio
from ib_async import util

from src.services.base_service import BaseService
from src.services.account_manager_service import AccountManagerService
from src.services.ib_connection_service import ib_connection_manager
from src.utils.logger import logger


class AccountService(BaseService):
    """
    Simplified AccountService that directly delegates to AccountManagerService
    Eliminates the triple-wrapper pattern: AccountService → AccountManagerService (no more AccountManager)
    """
    
    def __init__(self):
        super().__init__("AccountService")
        self.ib_manager = ib_connection_manager
        
        # Direct delegation to AccountManagerService
        self._service = AccountManagerService()
        
        # For backward compatibility, expose callback lists directly
        self.account_update_callbacks = self._service.account_update_callbacks
        self.position_update_callbacks = self._service.position_update_callbacks
        
    def initialize(self) -> bool:
        """Initialize the account service"""
        try:
            if not super().initialize():
                return False
                
            logger.info("Initializing AccountService with direct delegation...")
            
            # Initialize the underlying service
            success = self._service.initialize()
            if success:
                self._initialized = True
                logger.info("AccountService initialized successfully")
            else:
                logger.error("Failed to initialize underlying AccountManagerService")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to initialize AccountService: {str(e)}")
            self._initialized = False
            return False
            
    def cleanup(self):
        """Cleanup account service resources"""
        try:
            logger.info("Cleaning up AccountService...")
            self._service.cleanup()
            self._initialized = False
            logger.info("AccountService cleaned up successfully")
        except Exception as e:
            logger.error(f"Error cleaning up AccountService: {str(e)}")
    
    # Direct delegation methods - all methods delegate to _service
    def register_account_update_callback(self, callback: Callable):
        """Register a callback for account updates"""
        return self._service.register_account_update_callback(callback)
    
    def unregister_account_update_callback(self, callback: Callable):
        """Unregister an account update callback"""
        return self._service.unregister_account_update_callback(callback)
    
    def register_position_update_callback(self, callback: Callable):
        """Register a callback for position updates"""
        return self._service.register_position_update_callback(callback)
    
    def unregister_position_update_callback(self, callback: Callable):
        """Unregister a position update callback"""
        return self._service.unregister_position_update_callback(callback)
    
    def update_account_data(self) -> bool:
        """Update account data from IB"""
        if not self._check_initialized():
            return False
        return self._service.update_account_data()
    
    def update_positions(self) -> bool:
        """Update positions from IB"""
        if not self._check_initialized():
            return False
        return self._service.update_positions_enhanced()
    
    def get_account_value(self) -> float:
        """Get total account value"""
        return self._service.get_net_liquidation()
    
    def get_buying_power(self) -> float:
        """Get available buying power"""
        return self._service.get_buying_power()
    
    def get_cash_balance(self) -> float:
        """Get cash balance"""
        return self._service.get_total_cash_value()
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        return self._service.get_positions_formatted()
    
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get position for a specific symbol"""
        return self._service.get_position_by_symbol(symbol)
    
    def get_daily_pnl(self) -> float:
        """Get daily P&L"""
        return self._service.get_daily_pnl()
    
    def get_unrealized_pnl(self) -> float:
        """Get unrealized P&L"""
        return self._service.get_unrealized_pnl()
    
    def get_realized_pnl(self) -> float:
        """Get realized P&L"""
        return self._service.get_realized_pnl()
    
    def get_account_summary(self) -> Dict[str, Any]:
        """Get comprehensive account summary"""
        return self._service.get_account_summary_enhanced()
    
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
            
    def _check_initialized(self) -> bool:
        """Check if service is initialized"""
        if not self._initialized:
            logger.error("AccountService not initialized")
            return False
        return True


# Helper function for backward compatibility
def get_account_service() -> AccountService:
    """Get account service instance"""
    from src.services.service_registry import ServiceRegistry
    registry = ServiceRegistry()
    return registry.get_service('account')