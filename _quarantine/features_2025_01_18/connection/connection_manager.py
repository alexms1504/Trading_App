"""
Connection Manager
Central component for managing IB API connections
"""

from typing import Optional, Callable, List, Dict, Any
from enum import Enum
import asyncio

from src.services.ib_connection_service import ib_connection_manager
from src.services.account_manager_service import AccountManagerService
from src.services.event_bus import EventType, Event, publish_event
from src.utils.logger import logger
from config import CONNECTION_CONFIG


class ConnectionState(Enum):
    """Connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class ConnectionMode(Enum):
    """Connection modes"""
    PAPER = "paper"
    LIVE = "live"


class ConnectionManager:
    """Manages IB API connections with state tracking and events"""
    
    def __init__(self):
        self.ib_manager = ib_connection_manager
        self.account_manager: Optional[AccountManagerService] = None
        self.state = ConnectionState.DISCONNECTED
        self.mode: Optional[ConnectionMode] = None
        self.selected_account: Optional[str] = None
        
        # Callbacks
        self._state_callbacks: List[Callable[[ConnectionState, str], None]] = []
        self._account_callbacks: List[Callable[[str], None]] = []
        self._account_info_callbacks: List[Callable[[float, float], None]] = []
        
    def add_state_callback(self, callback: Callable[[ConnectionState, str], None]):
        """Add callback for connection state changes"""
        if callback not in self._state_callbacks:
            self._state_callbacks.append(callback)
            
    def add_account_callback(self, callback: Callable[[str], None]):
        """Add callback for account selection"""
        if callback not in self._account_callbacks:
            self._account_callbacks.append(callback)
            
    def add_account_info_callback(self, callback: Callable[[float, float], None]):
        """Add callback for account info updates"""
        if callback not in self._account_info_callbacks:
            self._account_info_callbacks.append(callback)
            
    def connect(self, mode: ConnectionMode, host: str = None, port: int = None, 
                client_id: int = None) -> bool:
        """
        Connect to IB API
        
        Args:
            mode: Paper or Live trading mode
            host: IB Gateway/TWS host
            port: IB Gateway/TWS port
            client_id: Client ID for connection
            
        Returns:
            True if connection successful
        """
        try:
            self._set_state(ConnectionState.CONNECTING, f"Connecting to {mode.value} trading...")
            
            # Use config defaults if not provided
            if host is None:
                host = CONNECTION_CONFIG['ib_gateway']['host']
            if port is None:
                port = (CONNECTION_CONFIG['ib_gateway']['paper_port'] if mode == ConnectionMode.PAPER 
                       else CONNECTION_CONFIG['ib_gateway']['live_port'])
            if client_id is None:
                client_id = CONNECTION_CONFIG['ib_gateway']['client_id']
                
            # Store mode
            self.mode = mode
            
            # Connect to IB
            success = self.ib_manager.connect(host, port, client_id)
            
            if success:
                # Initialize account manager
                self.account_manager = AccountManagerService()
                
                # Let connection stabilize
                asyncio.set_event_loop(asyncio.new_event_loop())
                loop = asyncio.get_event_loop()
                loop.run_until_complete(asyncio.sleep(1))
                
                # Get available accounts
                accounts = self._get_accounts()
                
                if not accounts:
                    self._set_state(ConnectionState.ERROR, "No accounts found")
                    self.disconnect()
                    return False
                    
                # Auto-select if single account
                if len(accounts) == 1:
                    self.selected_account = accounts[0][0]
                    self._notify_account_selected(self.selected_account)
                    
                self._set_state(ConnectionState.CONNECTED, 
                              f"Connected to {mode.value} trading on port {port}")
                
                # Publish connection event
                publish_event(Event(
                    EventType.CONNECTION_STATUS,
                    {
                        'connected': True,
                        'mode': mode.value,
                        'port': port,
                        'accounts': [acc[0] for acc in accounts]
                    }
                ))
                
                return True
                
            else:
                self._set_state(ConnectionState.ERROR, "Failed to connect to IB")
                return False
                
        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(error_msg)
            self._set_state(ConnectionState.ERROR, error_msg)
            return False
            
    def disconnect(self):
        """Disconnect from IB API"""
        try:
            logger.info("Disconnecting from IB...")
            
            # Clear account manager
            self.account_manager = None
            self.selected_account = None
            
            # Disconnect IB
            self.ib_manager.disconnect()
            
            self._set_state(ConnectionState.DISCONNECTED, "Disconnected from IB")
            
            # Publish disconnection event
            publish_event(Event(
                EventType.CONNECTION_STATUS,
                {'connected': False}
            ))
            
        except Exception as e:
            logger.error(f"Error during disconnect: {str(e)}")
            
    def select_account(self, account: str) -> bool:
        """Select trading account"""
        if not self.is_connected():
            return False
            
        try:
            self.selected_account = account
            self.ib_manager.selected_account = account
            
            # Update account info
            if self.account_manager:
                account_data = self.account_manager.accounts.get(account, {})
                net_liq = account_data.get('NetLiquidation', 0)
                buying_power = account_data.get('BuyingPower', 0)
                self._notify_account_info_updated(net_liq, buying_power)
                
            self._notify_account_selected(account)
            
            # Publish account selected event
            publish_event(Event(
                EventType.ACCOUNT_SELECTED,
                {'account': account}
            ))
            
            return True
            
        except Exception as e:
            logger.error(f"Error selecting account: {str(e)}")
            return False
            
    def get_accounts(self) -> List[tuple]:
        """Get available accounts with net liquidation values"""
        return self._get_accounts()
        
    def is_connected(self) -> bool:
        """Check if connected to IB"""
        return self.state == ConnectionState.CONNECTED and self.ib_manager.is_connected()
        
    def get_connection_info(self) -> Dict[str, Any]:
        """Get current connection information"""
        return {
            'connected': self.is_connected(),
            'state': self.state.value,
            'mode': self.mode.value if self.mode else None,
            'port': self.ib_manager.port if self.is_connected() else None,
            'account': self.selected_account,
            'accounts': [acc[0] for acc in self.get_accounts()] if self.is_connected() else []
        }
        
    def update_account_info(self):
        """Update account information"""
        if not self.is_connected() or not self.account_manager or not self.selected_account:
            return
            
        try:
            # Request account updates
            self.ib_manager.request_account_updates(self.selected_account)
            
            # Wait a bit for updates
            asyncio.set_event_loop(asyncio.new_event_loop())
            loop = asyncio.get_event_loop()
            loop.run_until_complete(asyncio.sleep(0.5))
            
            # Get updated values
            account_data = self.account_manager.accounts.get(self.selected_account, {})
            net_liq = account_data.get('NetLiquidation', 0)
            buying_power = account_data.get('BuyingPower', 0)
            
            self._notify_account_info_updated(net_liq, buying_power)
            
            # Publish account update event
            publish_event(Event(
                EventType.ACCOUNT_UPDATE,
                {
                    'account': self.selected_account,
                    'net_liquidation': net_liq,
                    'buying_power': buying_power,
                    'data': account_data
                }
            ))
            
        except Exception as e:
            logger.error(f"Error updating account info: {str(e)}")
            
    def _get_accounts(self) -> List[tuple]:
        """Get accounts from IB"""
        if not self.ib_manager.is_connected():
            return []
            
        try:
            accounts = self.ib_manager.get_accounts()
            account_values = []
            
            for account in accounts:
                # Try to get account value
                self.ib_manager.request_account_updates(account)
                
                # Brief wait for account data
                asyncio.set_event_loop(asyncio.new_event_loop())
                loop = asyncio.get_event_loop()
                loop.run_until_complete(asyncio.sleep(0.5))
                
                # Get net liquidation value
                if self.account_manager and account in self.account_manager.accounts:
                    net_liq = self.account_manager.accounts[account].get('NetLiquidation', 0)
                else:
                    net_liq = 0
                    
                account_values.append((account, net_liq))
                
            return account_values
            
        except Exception as e:
            logger.error(f"Error getting accounts: {str(e)}")
            return []
            
    def _set_state(self, state: ConnectionState, message: str):
        """Update connection state"""
        self.state = state
        logger.info(f"Connection state: {state.value} - {message}")
        
        # Notify callbacks
        for callback in self._state_callbacks:
            try:
                callback(state, message)
            except Exception as e:
                logger.error(f"Error in state callback: {str(e)}")
                
    def _notify_account_selected(self, account: str):
        """Notify account selection"""
        for callback in self._account_callbacks:
            try:
                callback(account)
            except Exception as e:
                logger.error(f"Error in account callback: {str(e)}")
                
    def _notify_account_info_updated(self, net_liq: float, buying_power: float):
        """Notify account info update"""
        for callback in self._account_info_callbacks:
            try:
                callback(net_liq, buying_power)
            except Exception as e:
                logger.error(f"Error in account info callback: {str(e)}")