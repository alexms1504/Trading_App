"""
Connection Service
Manages IB API connection lifecycle and related operations
"""

import asyncio
from typing import Optional, List, Callable, Dict, Any, Tuple
from enum import Enum

from src.services.base_service import BaseService, ServiceState
from src.services.account_manager_service import AccountManager
from src.core.risk_calculator import RiskCalculator
from src.core.order_manager import OrderManager
from config import IB_CONFIG, TIMER_CONFIG, UI_MESSAGES, DEFAULT_ACCOUNT_VALUES

# Try to import app_logger, fall back to simple logger for testing
try:
    from src.utils.app_logger import app_logger
except ImportError:
    from src.utils.simple_logger import simple_logger as app_logger


class ConnectionMode(Enum):
    """Trading connection modes"""
    PAPER = "paper"
    LIVE = "live"


# Dialog callback types
StartupDialogCallback = Callable[[str, str], Optional[ConnectionMode]]
AccountSelectionCallback = Callable[[List[Tuple[str, float]]], Optional[str]]
AccountConfirmationCallback = Callable[[str, float], bool]


class ConnectionService(BaseService):
    """
    Service that manages IB API connections
    Wraps connection logic from main.py
    """
    
    def __init__(self):
        super().__init__("ConnectionService")
        
        # Connection state
        self.ib_manager = None  # Will use global singleton when connecting
        self.account_manager: Optional[AccountManager] = None
        self.risk_calculator: Optional[RiskCalculator] = None
        self.order_manager: Optional[OrderManager] = None
        
        # Current state
        self.current_mode: ConnectionMode = ConnectionMode.PAPER
        self.is_connected: bool = False
        self.selected_account: Optional[str] = None
        self.available_accounts: List[str] = []
        
        # Callbacks
        self._connection_callbacks: List[Callable[[bool, str], None]] = []
        self._account_callbacks: List[Callable[[str], None]] = []
        self._account_info_callbacks: List[Callable[[float, float], None]] = []
        
        # Dialog callbacks (set by UI)
        self._startup_dialog_callback: Optional[StartupDialogCallback] = None
        self._account_selection_callback: Optional[AccountSelectionCallback] = None
        self._account_confirmation_callback: Optional[AccountConfirmationCallback] = None
        
    def initialize(self) -> bool:
        """Initialize the connection service"""
        if not super().initialize():
            return False
            
        # Service is ready but not connected
        self.is_connected = False
        return True
        
    def cleanup(self) -> bool:
        """Cleanup connection service resources"""
        # Disconnect if connected
        if self.is_connected:
            self.disconnect()
            
        return super().cleanup()
        
    def connect(self, mode: ConnectionMode = ConnectionMode.PAPER) -> bool:
        """
        Connect to IB API
        
        Args:
            mode: Trading mode (PAPER or LIVE)
            
        Returns:
            True if connection successful
        """
        try:
            app_logger.info(f"Connecting to IB in {mode.value} mode")
            self.current_mode = mode
            
            # Use the global IB connection manager singleton
            from src.services.ib_connection_service import ib_connection_manager
            self.ib_manager = ib_connection_manager
            
            # Run async connection
            # Note: We need to keep the IB connection operational after connecting
            # So we'll use util.run() which properly handles the event loop
            from ib_async import util
            
            async def connect_async():
                return await self.ib_manager.connect(mode.value)
            
            success = util.run(connect_async())
                
            if not success:
                app_logger.error("Failed to connect to IB")
                self._notify_connection(False, "Connection failed")
                return False
                
            # Initialize managers
            self._initialize_managers()
            
            # Initialize account manager to get account values
            try:
                from ib_async import util
                util.run(self.account_manager.initialize())
            except Exception as e:
                app_logger.warning(f"Failed to initialize account manager: {e}")
            
            # Get accounts
            self.available_accounts = self.ib_manager.get_accounts()
            app_logger.info(f"Found {len(self.available_accounts)} accounts")
            
            # Subscribe to events
            self._subscribe_to_events()
            
            # Update state
            self.is_connected = True
            mode_text = "LIVE" if mode == ConnectionMode.LIVE else "PAPER"
            self._notify_connection(True, f"Connected ({mode_text})")
            
            return True
            
        except Exception as e:
            self._handle_error(e, "Failed to connect to IB")
            self._notify_connection(False, f"Connection error: {str(e)}")
            return False
            
    def disconnect(self) -> bool:
        """
        Disconnect from IB API
        
        Returns:
            True if disconnection successful
        """
        try:
            app_logger.info("Disconnecting from IB")
            
            if self.ib_manager:
                # Run async disconnect
                from ib_async import util
                util.run(self.ib_manager.disconnect())
                    
            # Cleanup managers
            self._cleanup_managers()
            
            # Update state
            self.is_connected = False
            self.selected_account = None
            self.available_accounts = []
            
            self._notify_connection(False, "Disconnected")
            return True
            
        except Exception as e:
            self._handle_error(e, "Failed to disconnect from IB")
            return False
            
    def switch_mode(self, new_mode: ConnectionMode) -> bool:
        """
        Switch trading mode (requires reconnection)
        
        Args:
            new_mode: New trading mode
            
        Returns:
            True if switch successful
        """
        if self.current_mode == new_mode:
            app_logger.info(f"Already in {new_mode.value} mode")
            return True
            
        if self.is_connected:
            app_logger.info(f"Switching from {self.current_mode.value} to {new_mode.value}")
            self.disconnect()
            
        return self.connect(new_mode)
        
    def check_connection(self) -> Dict[str, Any]:
        """
        Check current connection status
        
        Returns:
            Connection status information
        """
        if not self.ib_manager:
            return {
                'connected': False,
                'mode': None,
                'account': None,
                'account_value': None
            }
            
        # Check actual connection
        actual_connected = self.ib_manager.is_connected()
        
        # Handle connection state change
        if actual_connected != self.is_connected:
            self.is_connected = actual_connected
            if not actual_connected:
                self._notify_connection(False, "Connection lost")
                
        # Get account info if connected
        account_value = None
        if self.is_connected and self.account_manager and self.selected_account:
            account_value = self.account_manager.get_net_liquidation(self.selected_account)
            
        return {
            'connected': self.is_connected,
            'mode': self.current_mode.value if self.is_connected else None,
            'account': self.selected_account,
            'account_value': account_value
        }
        
    def get_accounts(self) -> List[str]:
        """Get list of available accounts"""
        return self.available_accounts.copy()
        
    def select_account(self, account: str) -> bool:
        """
        Select trading account
        
        Args:
            account: Account ID
            
        Returns:
            True if account selected successfully
        """
        if account not in self.available_accounts:
            app_logger.error(f"Account {account} not available")
            return False
            
        try:
            self.selected_account = account
            
            if self.ib_manager:
                self.ib_manager.set_active_account(account)
                
            self._notify_account_selected(account)
            app_logger.info(f"Selected account: {account}")
            return True
            
        except Exception as e:
            self._handle_error(e, f"Failed to select account {account}")
            return False
            
    def get_account_value(self, account: Optional[str] = None) -> Optional[float]:
        """
        Get net liquidation value for account
        
        Args:
            account: Account ID (uses selected account if None)
            
        Returns:
            Net liquidation value or None
        """
        if not self.account_manager:
            return None
            
        account = account or self.selected_account
        if not account:
            return None
            
        return self.account_manager.get_net_liquidation(account)
        
    def add_connection_callback(self, callback: Callable[[bool, str], None]):
        """Add callback for connection status changes"""
        self._connection_callbacks.append(callback)
        
    def remove_connection_callback(self, callback: Callable[[bool, str], None]):
        """Remove connection callback"""
        if callback in self._connection_callbacks:
            self._connection_callbacks.remove(callback)
            
    def add_account_callback(self, callback: Callable[[str], None]):
        """Add callback for account selection changes"""
        self._account_callbacks.append(callback)
        
    def remove_account_callback(self, callback: Callable[[str], None]):
        """Remove account callback"""
        if callback in self._account_callbacks:
            self._account_callbacks.remove(callback)
            
    def _initialize_managers(self):
        """Initialize supporting managers"""
        self.account_manager = AccountManager()
        self.risk_calculator = RiskCalculator(self.account_manager)
        self.order_manager = OrderManager()
        
        app_logger.info("Initialized account, risk, and order managers")
        
    def _cleanup_managers(self):
        """Cleanup supporting managers"""
        self.account_manager = None
        self.risk_calculator = None
        self.order_manager = None
        self.ib_manager = None
        
    def _subscribe_to_events(self):
        """Subscribe to IB connection events"""
        if self.ib_manager:
            # Subscribe to connection events
            self.ib_manager.subscribe_to_event('connection_lost', self._on_connection_lost)
            self.ib_manager.subscribe_to_event('connection_restored', self._on_connection_restored)
            
    def _on_connection_lost(self):
        """Handle connection lost event"""
        app_logger.warning("IB connection lost")
        self.is_connected = False
        self._notify_connection(False, "Connection lost")
        
    def _on_connection_restored(self):
        """Handle connection restored event"""
        app_logger.info("IB connection restored")
        self.is_connected = True
        mode_text = "LIVE" if self.current_mode == ConnectionMode.LIVE else "PAPER"
        self._notify_connection(True, f"Connection restored ({mode_text})")
        
    def _notify_connection(self, connected: bool, message: str):
        """Notify connection callbacks"""
        for callback in self._connection_callbacks:
            try:
                callback(connected, message)
            except Exception as e:
                app_logger.error(f"Error in connection callback: {e}")
                
    def _notify_account_selected(self, account: str):
        """Notify account callbacks"""
        for callback in self._account_callbacks:
            try:
                callback(account)
            except Exception as e:
                app_logger.error(f"Error in account callback: {e}")
                
    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        status = super().get_status()
        status.update({
            'connected': self.is_connected,
            'mode': self.current_mode.value,
            'selected_account': self.selected_account,
            'available_accounts': len(self.available_accounts)
        })
        return status
        
    # Dialog callback setters
    def set_startup_dialog_callback(self, callback: StartupDialogCallback):
        """Set callback for startup connection dialog"""
        self._startup_dialog_callback = callback
        
    def set_account_selection_callback(self, callback: AccountSelectionCallback):
        """Set callback for account selection dialog"""
        self._account_selection_callback = callback
        
    def set_account_confirmation_callback(self, callback: AccountConfirmationCallback):
        """Set callback for single account confirmation"""
        self._account_confirmation_callback = callback
        
    # Enhanced connection flow methods
    def connect_with_dialog(self) -> bool:
        """
        Show connection dialog and connect
        
        Returns:
            True if connected successfully
        """
        # Show startup dialog
        if self._startup_dialog_callback:
            selected_mode = self._startup_dialog_callback(
                UI_MESSAGES['welcome_message'],
                UI_MESSAGES['trading_mode_info']
            )
            
            if not selected_mode:
                app_logger.info("User cancelled connection dialog")
                return False
                
            # Connect with selected mode
            if self.connect(selected_mode):
                # Handle account selection
                return self._handle_post_connection_flow()
                
        return False
        
    def _handle_post_connection_flow(self) -> bool:
        """Handle account selection after connection"""
        accounts = self.get_accounts()
        
        if not accounts:
            app_logger.error("No accounts found after connection")
            return False
            
        if len(accounts) == 1:
            # Single account - show confirmation
            account = accounts[0]
            net_liq = self.get_account_value(account) or DEFAULT_ACCOUNT_VALUES['net_liquidation']
            
            if self._account_confirmation_callback:
                if self._account_confirmation_callback(account, net_liq):
                    self.select_account(account)
                    self._update_account_info()
                    return True
            else:
                # No confirmation callback, just select the account
                self.select_account(account)
                self._update_account_info()
                return True
                
        else:
            # Multiple accounts - show selection dialog
            if self._account_selection_callback:
                # Prepare account info
                account_info = []
                for account in accounts:
                    net_liq = self.get_account_value(account) or 0
                    account_info.append((account, net_liq))
                    
                selected = self._account_selection_callback(account_info)
                if selected:
                    self.select_account(selected)
                    self._update_account_info()
                    return True
                    
        return False
        
    def switch_mode_with_confirmation(self, new_mode: ConnectionMode, confirm_callback: Callable[[str, str], bool]) -> bool:
        """
        Switch trading mode with confirmation dialog
        
        Args:
            new_mode: New trading mode
            confirm_callback: Callback to confirm mode switch
            
        Returns:
            True if switched successfully
        """
        if self.current_mode == new_mode:
            return True
            
        if self.is_connected:
            # Confirm with user
            current = self.current_mode.value.upper()
            new = new_mode.value.upper()
            
            if confirm_callback(current, new):
                # Disconnect and reconnect
                self.disconnect()
                if self.connect(new_mode):
                    return self._handle_post_connection_flow()
                    
        return False
        
    def _update_account_info(self):
        """Update account information and notify callbacks"""
        if not self.selected_account:
            return
            
        net_liq = self.get_account_value(self.selected_account) or 0
        buying_power = self.get_buying_power(self.selected_account) or 0
        
        # Notify callbacks
        for callback in self._account_info_callbacks:
            try:
                callback(net_liq, buying_power)
            except Exception as e:
                app_logger.error(f"Error in account info callback: {e}")
                
    def get_buying_power(self, account: Optional[str] = None) -> Optional[float]:
        """Get buying power for account"""
        if not self.account_manager:
            return None
            
        account = account or self.selected_account
        if not account:
            return None
            
        return self.account_manager.get_buying_power(account)
        
    def add_account_info_callback(self, callback: Callable[[float, float], None]):
        """Add callback for account info updates (net_liq, buying_power)"""
        self._account_info_callbacks.append(callback)
        
    def remove_account_info_callback(self, callback: Callable[[float, float], None]):
        """Remove account info callback"""
        if callback in self._account_info_callbacks:
            self._account_info_callbacks.remove(callback)
            
    def periodic_update(self):
        """Called periodically to update connection and account info"""
        # Check connection
        status = self.check_connection()
        
        # Update account info if connected
        if status['connected'] and self.selected_account:
            self._update_account_info()
            
    def get_connection_info(self) -> Dict[str, Any]:
        """Get detailed connection information for UI display"""
        return {
            'connected': self.is_connected,
            'mode': self.current_mode.value.upper() if self.is_connected else None,
            'port': self._get_current_port(),
            'account': self.selected_account,
            'accounts': self.available_accounts
        }
        
    def _get_current_port(self) -> int:
        """Get current connection port"""
        if self.current_mode == ConnectionMode.LIVE:
            return IB_CONFIG['live_port']
        return IB_CONFIG['paper_port']