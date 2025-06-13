"""
Account Manager Service
Service-based implementation of account management functionality
Migrated from src/core/account_manager.py as part of architecture consolidation
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime, date
from decimal import Decimal

from src.services.base_service import BaseService
from src.services.ib_connection_service import ib_connection_manager
from src.utils.logger import logger
from config import TRADING_CONFIG


class AccountManagerService(BaseService):
    """
    Service for managing account data including:
    - Real-time account values
    - Buying power calculations
    - Margin requirements
    - Position tracking
    - P&L calculations
    - Risk metrics
    """
    
    def __init__(self):
        super().__init__("AccountManagerService")
        self.ib_manager = ib_connection_manager
        self._account_data: Dict[str, Dict[str, Any]] = {}
        self._positions: Dict[str, List[Any]] = {}
        self._daily_pnl: Dict[str, Dict[date, float]] = {}
        self._subscribed = False
        self._update_callbacks: List[Callable] = []
        
        # Enhanced callback system from AccountService
        self.account_update_callbacks: List[Callable] = []
        self.position_update_callbacks: List[Callable] = []
        
        # Caching layer from AccountService
        self._account_data_cache: Dict[str, Any] = {}
        self._positions_cache: List[Dict] = []
        
    def initialize(self) -> bool:
        """Initialize the service"""
        try:
            logger.info("AccountManagerService initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize AccountManagerService: {str(e)}")
            return False
            
    def cleanup(self):
        """Cleanup service resources"""
        if self._subscribed:
            self.ib_manager.unsubscribe_from_event('account', self._on_account_update)
            self.ib_manager.unsubscribe_from_event('position', self._on_position_update)
            self._subscribed = False
            
        # Clear enhanced callbacks
        self.account_update_callbacks.clear()
        self.position_update_callbacks.clear()
        self._account_data_cache.clear()
        self._positions_cache.clear()
        
        logger.info("AccountManagerService cleaned up")
    
    # Enhanced callback registration methods from AccountService
    def register_account_update_callback(self, callback: Callable):
        """Register a callback for account updates"""
        if callback not in self.account_update_callbacks:
            self.account_update_callbacks.append(callback)
            logger.debug(f"Registered account update callback: {callback.__name__}")
    
    def unregister_account_update_callback(self, callback: Callable):
        """Unregister an account update callback"""
        if callback in self.account_update_callbacks:
            self.account_update_callbacks.remove(callback)
            logger.debug(f"Unregistered account update callback: {callback.__name__}")
    
    def register_position_update_callback(self, callback: Callable):
        """Register a callback for position updates"""
        if callback not in self.position_update_callbacks:
            self.position_update_callbacks.append(callback)
            logger.debug(f"Registered position update callback: {callback.__name__}")
    
    def unregister_position_update_callback(self, callback: Callable):
        """Unregister a position update callback"""
        if callback in self.position_update_callbacks:
            self.position_update_callbacks.remove(callback)
            logger.debug(f"Unregistered position update callback: {callback.__name__}")
    
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
        
    async def initialize_async(self):
        """Initialize account manager and subscribe to updates"""
        if not self.ib_manager.is_connected():
            logger.error("IB not connected. Cannot initialize account manager.")
            return False
            
        # Subscribe to account updates
        self.ib_manager.subscribe_to_event('account', self._on_account_update)
        self.ib_manager.subscribe_to_event('position', self._on_position_update)
        self._subscribed = True
        
        # Get initial data
        await self.refresh_all_accounts()
        
        logger.info("Account Manager initialized with subscriptions")
        return True
    
    async def refresh_all_accounts(self):
        """Refresh data for all accounts"""
        accounts = self.ib_manager.get_accounts()
        
        for account in accounts:
            # Get account summary
            summary = self.ib_manager.get_account_summary(account)
            self._process_account_summary(account, summary)
            
            # Get positions
            positions = self.ib_manager.get_positions(account)
            self._positions[account] = positions
            
        self._notify_updates()
    
    def _process_account_summary(self, account: str, summary: List[Any]):
        """Process account summary data"""
        if account not in self._account_data:
            self._account_data[account] = {}
            
        for item in summary:
            # Try to convert to float, keep as string if not numeric
            try:
                value = float(item.value) if item.value else 0.0
            except (ValueError, TypeError):
                value = item.value
                
            self._account_data[account][item.tag] = {
                'value': value,
                'currency': item.currency,
                'timestamp': datetime.now()
            }
    
    def _on_account_update(self, value):
        """Handle real-time account value updates"""
        account = value.account
        if account not in self._account_data:
            self._account_data[account] = {}
            
        # Try to convert to float, keep as string if not numeric
        try:
            parsed_value = float(value.value) if value.value else 0.0
        except (ValueError, TypeError):
            parsed_value = value.value
            
        self._account_data[account][value.tag] = {
            'value': parsed_value,
            'currency': value.currency,
            'timestamp': datetime.now()
        }
        
        # Track daily P&L
        if value.tag == 'DailyPnL':
            today = date.today()
            if account not in self._daily_pnl:
                self._daily_pnl[account] = {}
            try:
                self._daily_pnl[account][today] = float(value.value)
            except (ValueError, TypeError):
                self._daily_pnl[account][today] = 0.0
        
        self._notify_updates()
    
    def _on_position_update(self, position):
        """Handle position updates"""
        account = position.account
        if account not in self._positions:
            self._positions[account] = []
            
        # Update or add position
        updated = False
        for i, pos in enumerate(self._positions[account]):
            if pos.contract.symbol == position.contract.symbol:
                self._positions[account][i] = position
                updated = True
                break
                
        if not updated:
            self._positions[account].append(position)
            
        self._notify_updates()
    
    def get_account_value(self, account: str, field: str) -> Optional[float]:
        """Get specific account value"""
        if account in self._account_data and field in self._account_data[account]:
            value = self._account_data[account][field]['value']
            # Return numeric values as float, non-numeric as None
            if isinstance(value, (int, float)):
                return float(value)
            return None
        return None
    
    def get_net_liquidation(self, account: Optional[str] = None) -> float:
        """Get net liquidation value for account"""
        account = account or self.ib_manager.get_active_account()
        if not account:
            return 0.0
            
        return self.get_account_value(account, 'NetLiquidation') or 0.0
    
    def get_buying_power(self, account: Optional[str] = None) -> float:
        """Get buying power for account"""
        account = account or self.ib_manager.get_active_account()
        if not account:
            return 0.0
            
        return self.get_account_value(account, 'BuyingPower') or 0.0
    
    def get_available_funds(self, account: Optional[str] = None) -> float:
        """Get available funds for trading"""
        account = account or self.ib_manager.get_active_account()
        if not account:
            return 0.0
            
        # Use AvailableFunds if available, otherwise BuyingPower
        available = self.get_account_value(account, 'AvailableFunds')
        if available is None:
            available = self.get_buying_power(account)
            
        return available
    
    def get_cash_balance(self, account: Optional[str] = None) -> float:
        """Get cash balance"""
        account = account or self.ib_manager.get_active_account()
        if not account:
            return 0.0
            
        return self.get_account_value(account, 'TotalCashValue') or 0.0
    
    def get_total_cash_value(self, account: Optional[str] = None) -> float:
        """Get total cash value (alias for get_cash_balance)"""
        return self.get_cash_balance(account)
    
    def get_total_positions_value(self, account: Optional[str] = None) -> float:
        """Get total positions value (alias for get_position_value)"""
        return self.get_position_value(account)
    
    def calculate_margin_requirement(self, symbol: str, quantity: int, price: float, 
                                   account: Optional[str] = None) -> float:
        """
        Calculate margin requirement for a position
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            price: Price per share
            account: Account to check (uses active if None)
            
        Returns:
            Margin requirement amount
        """
        account = account or self.ib_manager.get_active_account()
        if not account:
            return 0.0
            
        # Get account type and margin multiplier
        # For day trading accounts, typically 4:1 leverage (25% margin)
        # For regular margin accounts, typically 2:1 leverage (50% margin)
        
        order_value = quantity * price
        
        # Check if pattern day trader
        is_day_trader = self.get_account_value(account, 'DayTradesRemaining') is not None
        
        if is_day_trader:
            margin_req = order_value * 0.25  # 25% for day trading
        else:
            margin_req = order_value * 0.50  # 50% for regular margin
            
        return margin_req
    
    def validate_order_buying_power(self, order_value: float, 
                                  account: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate if order can be placed with available buying power
        
        Returns:
            Tuple of (is_valid, message)
        """
        account = account or self.ib_manager.get_active_account()
        if not account:
            return False, "No active account"
            
        buying_power = self.get_buying_power(account)
        
        # Apply margin buffer from config
        margin_buffer = TRADING_CONFIG.get('margin_buffer', 0.25)
        available_with_buffer = buying_power * (1 - margin_buffer)
        
        if order_value > buying_power:
            return False, f"Order value ${order_value:.2f} exceeds buying power ${buying_power:.2f}"
        elif order_value > available_with_buffer:
            return True, f"Warning: Order uses >{(1-margin_buffer)*100:.0f}% of buying power"
        else:
            return True, "Order within buying power limits"
    
    def get_positions(self, account: Optional[str] = None) -> List[Any]:
        """Get positions for account"""
        account = account or self.ib_manager.get_active_account()
        if not account or account not in self._positions:
            return []
            
        return self._positions[account]
    
    def get_position_value(self, account: Optional[str] = None) -> float:
        """Calculate total value of all positions"""
        positions = self.get_positions(account)
        total_value = 0.0
        
        for pos in positions:
            # Assuming position has marketValue attribute
            if hasattr(pos, 'marketValue'):
                total_value += abs(pos.marketValue)
            else:
                # Calculate manually if needed
                total_value += abs(pos.position * pos.avgCost)
                
        return total_value
    
    def calculate_position_concentration(self, symbol: str, 
                                       account: Optional[str] = None) -> float:
        """Calculate position concentration as % of portfolio"""
        account = account or self.ib_manager.get_active_account()
        if not account:
            return 0.0
            
        net_liq = self.get_net_liquidation(account)
        if net_liq == 0:
            return 0.0
            
        positions = self.get_positions(account)
        position_value = 0.0
        
        for pos in positions:
            if pos.contract.symbol == symbol:
                if hasattr(pos, 'marketValue'):
                    position_value = abs(pos.marketValue)
                else:
                    position_value = abs(pos.position * pos.avgCost)
                break
                
        return (position_value / net_liq) * 100
    
    def get_daily_pnl(self, account: Optional[str] = None) -> float:
        """Get today's P&L"""
        account = account or self.ib_manager.get_active_account()
        if not account:
            return 0.0
            
        return self.get_account_value(account, 'DailyPnL') or 0.0
    
    def get_unrealized_pnl(self, account: Optional[str] = None) -> float:
        """Get unrealized P&L"""
        account = account or self.ib_manager.get_active_account()
        if not account:
            return 0.0
            
        return self.get_account_value(account, 'UnrealizedPnL') or 0.0
    
    def get_realized_pnl(self, account: Optional[str] = None) -> float:
        """Get realized P&L"""
        account = account or self.ib_manager.get_active_account()
        if not account:
            return 0.0
            
        return self.get_account_value(account, 'RealizedPnL') or 0.0
    
    def get_account_summary(self, account: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive account summary"""
        account = account or self.ib_manager.get_active_account()
        if not account:
            return {}
            
        return {
            'account': account,
            'net_liquidation': self.get_net_liquidation(account),
            'buying_power': self.get_buying_power(account),
            'available_funds': self.get_available_funds(account),
            'cash_balance': self.get_cash_balance(account),
            'position_value': self.get_position_value(account),
            'daily_pnl': self.get_daily_pnl(account),
            'unrealized_pnl': self.get_unrealized_pnl(account),
            'realized_pnl': self.get_realized_pnl(account),
            'position_count': len(self.get_positions(account)),
            'timestamp': datetime.now()
        }
    
    def subscribe_to_updates(self, callback: Callable):
        """Subscribe to account updates"""
        self._update_callbacks.append(callback)
    
    def unsubscribe_from_updates(self, callback: Callable):
        """Unsubscribe from account updates"""
        if callback in self._update_callbacks:
            self._update_callbacks.remove(callback)
    
    def _notify_updates(self):
        """Notify all subscribers of updates"""
        for callback in self._update_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in update callback: {str(e)}")
    
    # Enhanced API methods from AccountService for simplified access
    def update_account_data(self) -> bool:
        """Update account data from IB"""
        try:
            # Use async method in sync context
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.refresh_all_accounts())
                    return True
                else:
                    loop.run_until_complete(self.refresh_all_accounts())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.refresh_all_accounts())
                loop.close()
            
            # Update cache
            self._account_data_cache = {
                'net_liquidation': self.get_net_liquidation(),
                'buying_power': self.get_buying_power(),
                'total_cash': self.get_total_cash_value(),
                'total_positions_value': self.get_total_positions_value(),
                'daily_pnl': self.get_daily_pnl(),
                'unrealized_pnl': self.get_unrealized_pnl(),
                'realized_pnl': self.get_realized_pnl(),
                'timestamp': datetime.now()
            }
            
            # Notify callbacks
            self._notify_account_update(self._account_data_cache)
            return True
            
        except Exception as e:
            logger.error(f"Error updating account data: {e}")
            return False
    
    def update_positions_enhanced(self) -> bool:
        """Update positions and notify callbacks"""
        try:
            success = self.update_account_data()  # This updates both account and positions
            
            if success:
                # Get formatted positions for UI
                positions = self.get_positions_formatted()
                self._positions_cache = positions
                
                # Notify position callbacks
                self._notify_position_update(positions)
                
                logger.info(f"Updated {len(positions)} positions")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating positions: {e}")
            return False
    
    def get_positions_formatted(self) -> List[Dict[str, Any]]:
        """Get positions in AccountService format"""
        positions = []
        
        for account, account_positions in self._positions.items():
            for position in account_positions:
                if hasattr(position, 'contract') and hasattr(position.contract, 'symbol'):
                    positions.append({
                        'symbol': position.contract.symbol,
                        'position': position.position,
                        'avg_cost': getattr(position, 'avgCost', 0),
                        'market_price': getattr(position, 'marketPrice', 0),
                        'market_value': getattr(position, 'marketValue', 0),
                        'unrealized_pnl': getattr(position, 'unrealizedPNL', 0),
                        'realized_pnl': getattr(position, 'realizedPNL', 0)
                    })
        
        return positions
    
    def get_position_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get position for a specific symbol"""
        positions = self.get_positions_formatted()
        for pos in positions:
            if pos['symbol'] == symbol:
                return pos
        return None
    
    def get_account_summary_enhanced(self) -> Dict[str, Any]:
        """Get comprehensive account summary"""
        return {
            'net_liquidation': self.get_net_liquidation(),
            'buying_power': self.get_buying_power(),
            'cash_balance': self.get_total_cash_value(),
            'daily_pnl': self.get_daily_pnl(),
            'unrealized_pnl': self.get_unrealized_pnl(),
            'realized_pnl': self.get_realized_pnl(),
            'positions_count': len(self.get_positions_formatted()),
            'positions_value': self.get_total_positions_value(),
            'last_update': self._account_data_cache.get('timestamp', None)
        }


# Provide access to the service for dependency injection
def get_account_manager_service() -> AccountManagerService:
    """Get the account manager service instance"""
    service = AccountManagerService()
    service.initialize()
    return service