"""
IB API Connection Manager
Handles connection to Interactive Brokers TWS/Gateway
Supports multiple accounts under the same username
"""
import asyncio
from typing import Optional, Dict, Any, List, Callable, Set
from datetime import datetime
import ib_async
from ib_async import IB, Contract, Stock, Order, Trade, BarData, AccountValue
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.utils.logger import setup_logger
from config import IB_CONFIG

logger = setup_logger(__name__)


class ConnectionState:
    """Connection state enumeration"""
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    ERROR = "ERROR"


class IBConnectionManager:
    """
    Singleton manager for IB API connection
    Handles connection, reconnection, and event management
    Supports multiple accounts under the same username
    """
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.ib = IB()
            self.connection_state = ConnectionState.DISCONNECTED
            self.last_connection_time = None
            self.reconnect_attempts = 0
            self.max_reconnect_attempts = 5
            self.reconnect_delay = 5  # seconds
            # Trading mode: 'paper' or 'live'
            self.trading_mode = IB_CONFIG['default_mode']
            self.current_port = None
            self._callbacks: Dict[str, List[Callable]] = {
                'connection_status': [],
                'error': [],
                'order_status': [],
                'position': [],
                'account': []
            }
            # Multi-account support
            self._accounts: Set[str] = set()
            self._active_account: Optional[str] = None
            self._account_values: Dict[str, Dict[str, Any]] = {}  # account -> values
            self._account_summaries: Dict[str, List[Any]] = {}  # account -> summary items
            self._positions: Dict[str, List[Any]] = {}  # account -> positions
            self._orders: List[Trade] = []
            self._initialized = True
            
            # Set up IB event handlers
            self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Set up IB API event handlers"""
        # Use lambda to properly bind self
        self.ib.connectedEvent += lambda: self._on_connected()
        self.ib.disconnectedEvent += lambda: self._on_disconnected()
        self.ib.errorEvent += lambda reqId, errorCode, errorString, contract: self._on_error(reqId, errorCode, errorString, contract)
        self.ib.orderStatusEvent += lambda trade: self._on_order_status(trade)
        self.ib.positionEvent += lambda position: self._on_position(position)
        self.ib.accountValueEvent += lambda value: self._on_account_value(value)
        self.ib.accountSummaryEvent += lambda value: self._on_account_summary(value)
        
    async def connect(self, trading_mode: str = None) -> bool:
        """
        Connect to IB Gateway/TWS
        
        Args:
            trading_mode: 'paper' or 'live' - if provided, switches mode before connecting
        
        Returns:
            bool: True if connected successfully
        """
        # Set trading mode if provided
        if trading_mode:
            self.set_trading_mode(trading_mode)
            
        if self.is_connected():
            logger.info("Already connected to IB")
            return True
            
        try:
            self.connection_state = ConnectionState.CONNECTING
            self._notify_connection_status()
            
            # Get the appropriate port based on trading mode
            port = self.get_current_port()
            self.current_port = port
            
            logger.info(f"Connecting to IB at {IB_CONFIG['host']}:{port} ({self.trading_mode.upper()} mode)")
            
            await self.ib.connectAsync(
                host=IB_CONFIG['host'],
                port=port,
                clientId=IB_CONFIG['client_id'],
                timeout=IB_CONFIG['timeout']
            )
            
            # Get list of accounts
            self._accounts = set(self.ib.managedAccounts())
            if self._accounts:
                logger.info(f"Found {len(self._accounts)} accounts: {', '.join(self._accounts)}")
                # Set first account as active by default
                self._active_account = list(self._accounts)[0]
                logger.info(f"Active account set to: {self._active_account}")
            
            # Request account summaries for all accounts
            await self.ib.reqAccountSummaryAsync()
            
            # Request positions
            await self.ib.reqPositionsAsync()
            
            self.connection_state = ConnectionState.CONNECTED
            self.last_connection_time = datetime.now()
            self.reconnect_attempts = 0
            
            logger.info("Successfully connected to IB")
            self._notify_connection_status()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to IB: {str(e)}")
            self.connection_state = ConnectionState.ERROR
            self._notify_error(str(e))
            self._notify_connection_status()
            return False
    
    async def disconnect(self):
        """Disconnect from IB"""
        if self.is_connected():
            logger.info("Disconnecting from IB")
            self.ib.disconnect()
            self.connection_state = ConnectionState.DISCONNECTED
            self._notify_connection_status()
    
    def is_connected(self) -> bool:
        """Check if connected to IB"""
        return self.ib.isConnected()
    
    async def reconnect(self):
        """Attempt to reconnect with exponential backoff"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            self.connection_state = ConnectionState.ERROR
            self._notify_error("Max reconnection attempts reached")
            return False
            
        self.reconnect_attempts += 1
        delay = self.reconnect_delay * (2 ** (self.reconnect_attempts - 1))
        
        logger.info(f"Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts} in {delay}s")
        await asyncio.sleep(delay)
        
        return await self.connect()
    
    def subscribe_to_event(self, event_type: str, callback: Callable):
        """
        Subscribe to connection events
        
        Args:
            event_type: Type of event ('connection_status', 'error', etc.)
            callback: Function to call when event occurs
        """
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)
    
    def unsubscribe_from_event(self, event_type: str, callback: Callable):
        """Unsubscribe from connection events"""
        if event_type in self._callbacks and callback in self._callbacks[event_type]:
            self._callbacks[event_type].remove(callback)
    
    # Event handlers
    def _on_connected(self):
        """Handle connection event"""
        logger.info("IB API connected event received")
        
    def _on_disconnected(self):
        """Handle disconnection event"""
        logger.warning("IB API disconnected")
        self.connection_state = ConnectionState.DISCONNECTED
        self._notify_connection_status()
        
        # Attempt reconnection
        asyncio.create_task(self.reconnect())
        
    def _on_error(self, reqId: int, errorCode: int, errorString: str, contract: Contract):
        """Handle IB API errors"""
        if errorCode in [2104, 2106, 2158]:  # Info messages
            logger.info(f"IB Info: {errorString}")
        else:
            logger.error(f"IB Error {errorCode}: {errorString}")
            self._notify_error(f"Error {errorCode}: {errorString}")
    
    def _on_order_status(self, trade: Trade):
        """Handle order status updates"""
        logger.info(f"Order status update: {trade.order.orderId} - {trade.orderStatus.status}")
        for callback in self._callbacks['order_status']:
            callback(trade)
    
    def _on_position(self, position):
        """Handle position updates"""
        account = position.account
        if account not in self._positions:
            self._positions[account] = []
        self._positions[account].append(position)
        
        for callback in self._callbacks['position']:
            callback(position)
    
    def _on_account_value(self, value: AccountValue):
        """Handle account value updates"""
        account = value.account
        if account not in self._account_values:
            self._account_values[account] = {}
        self._account_values[account][value.tag] = value
        
        for callback in self._callbacks['account']:
            callback(value)
    
    def _on_account_summary(self, value):
        """Handle account summary updates"""
        account = value.account
        if account not in self._account_summaries:
            self._account_summaries[account] = []
        self._account_summaries[account].append(value)
    
    # Notification methods
    def _notify_connection_status(self):
        """Notify subscribers of connection status change"""
        status = {
            'state': self.connection_state,
            'connected': self.is_connected(),
            'last_connection': self.last_connection_time,
            'reconnect_attempts': self.reconnect_attempts,
            'accounts': list(self._accounts),
            'active_account': self._active_account
        }
        for callback in self._callbacks['connection_status']:
            callback(status)
    
    def _notify_error(self, error_message: str):
        """Notify subscribers of errors"""
        for callback in self._callbacks['error']:
            callback(error_message)
    
    # Account management methods
    def get_accounts(self) -> List[str]:
        """Get list of all accounts"""
        return list(self._accounts)
    
    def set_active_account(self, account: str) -> bool:
        """Set the active account for trading"""
        if account in self._accounts:
            self._active_account = account
            logger.info(f"Active account changed to: {account}")
            return True
        else:
            logger.error(f"Account {account} not found")
            return False
    
    def get_active_account(self) -> Optional[str]:
        """Get the currently active account"""
        return self._active_account
    
    # Public methods for data access
    def get_account_values(self, account: Optional[str] = None) -> Dict[str, Any]:
        """Get account values for specified account or active account"""
        account = account or self._active_account
        if account and account in self._account_values:
            return self._account_values[account].copy()
        return {}
    
    def get_all_account_values(self) -> Dict[str, Dict[str, Any]]:
        """Get account values for all accounts"""
        return self._account_values.copy()
    
    def get_account_summary(self, account: Optional[str] = None) -> List[Any]:
        """Get account summary for specified account or active account"""
        account = account or self._active_account
        if account and account in self._account_summaries:
            return self._account_summaries[account].copy()
        return []
    
    def get_positions(self, account: Optional[str] = None) -> List[Any]:
        """Get positions for specified account or active account"""
        account = account or self._active_account
        if account and account in self._positions:
            return self._positions[account].copy()
        return []
    
    def get_all_positions(self) -> Dict[str, List[Any]]:
        """Get positions for all accounts"""
        return self._positions.copy()
    
    def get_orders(self) -> List[Trade]:
        """Get current orders"""
        return self.ib.orders()
    
    def get_ib_client(self) -> IB:
        """Get the IB client instance for direct access"""
        return self.ib
    
    def set_trading_mode(self, mode: str):
        """Set trading mode ('paper' or 'live')"""
        if mode not in ['paper', 'live']:
            raise ValueError("Trading mode must be 'paper' or 'live'")
        
        old_mode = self.trading_mode
        self.trading_mode = mode
        logger.info(f"Trading mode changed from {old_mode} to {mode}")
    
    def get_trading_mode(self) -> str:
        """Get current trading mode"""
        return self.trading_mode
    
    def get_current_port(self) -> int:
        """Get the port number for current trading mode"""
        if self.trading_mode == 'paper':
            return IB_CONFIG['paper_port']
        else:
            return IB_CONFIG['live_port']
    
    def is_paper_trading(self) -> bool:
        """Check if currently in paper trading mode"""
        return self.trading_mode == 'paper'
    
    def is_live_trading(self) -> bool:
        """Check if currently in live trading mode"""
        return self.trading_mode == 'live'
    
    async def switch_trading_mode(self, new_mode: str) -> bool:
        """Switch trading mode and reconnect"""
        if new_mode == self.trading_mode:
            logger.info(f"Already in {new_mode} mode")
            return True
        
        was_connected = self.is_connected()
        
        # Disconnect if currently connected
        if was_connected:
            logger.info(f"Disconnecting to switch from {self.trading_mode} to {new_mode} mode")
            await self.disconnect()
        
        # Change mode
        self.set_trading_mode(new_mode)
        
        # Reconnect if we were previously connected
        if was_connected:
            logger.info(f"Reconnecting in {new_mode} mode")
            return await self.connect()
        
        return True


# Create singleton instance
ib_connection_manager = IBConnectionManager()
