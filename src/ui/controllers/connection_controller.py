"""
Connection Controller
Handles IB connection management and UI updates
"""

from typing import Optional, Dict, List, Tuple, Callable
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtWidgets import QMessageBox

from .base_controller import BaseController
from src.services.connection_service import ConnectionService, ConnectionMode
from src.services import get_account_service, get_risk_service
from src.utils.logger import logger
import config


class ConnectionController(BaseController):
    """Controller for connection management"""
    
    # Connection signals
    connection_status_changed = pyqtSignal(bool, str)  # connected, message
    account_selected = pyqtSignal(str)
    account_info_updated = pyqtSignal(float, float)  # net_liq, buying_power
    mode_changed = pyqtSignal(str)  # paper/live
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.connection_service = None
        self.connection_check_timer = QTimer()
        self.account_update_timer = QTimer()
        
    def initialize(self) -> bool:
        """Initialize the controller"""
        if not super().initialize():
            return False
            
        try:
            # Initialize connection service
            self.connection_service = ConnectionService()
            self.connection_service.initialize()
            
            # Setup callbacks
            self._setup_connection_callbacks()
            
            # Setup timers
            self.connection_check_timer.timeout.connect(self._check_connection)
            self.connection_check_timer.start(config.TIMER_CONFIG['connection_check_interval'])
            
            self.account_update_timer.timeout.connect(self._update_account_info)
            self.account_update_timer.start(config.TIMER_CONFIG['account_update_interval'])
            
            logger.info("ConnectionController initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize ConnectionController: {str(e)}")
            return False
            
    def cleanup(self):
        """Cleanup controller resources"""
        try:
            # Stop timers
            self.connection_check_timer.stop()
            self.account_update_timer.stop()
            
            # Cleanup connection service
            if self.connection_service:
                self.connection_service.cleanup()
                
            super().cleanup()
            
        except Exception as e:
            logger.error(f"Error cleaning up ConnectionController: {str(e)}")
            
    def _setup_connection_callbacks(self):
        """Setup connection service callbacks"""
        if not self.connection_service:
            return
            
        # Dialog callbacks
        self.connection_service.set_startup_dialog_callback(self._show_startup_dialog)
        self.connection_service.set_account_selection_callback(self._show_account_selection_dialog)
        self.connection_service.set_account_confirmation_callback(self._show_account_confirmation_dialog)
        
        # Status callbacks
        self.connection_service.add_connection_callback(self._on_connection_status_changed)
        self.connection_service.add_account_callback(self._on_account_selected)
        self.connection_service.add_account_info_callback(self._on_account_info_updated)
        
    def start_connection_flow(self):
        """Start the connection flow"""
        if self.connection_service:
            self.connection_service.connect_with_dialog()
            
    def connect(self, mode: Optional[ConnectionMode] = None):
        """Connect to IB"""
        if self.connection_service:
            if mode:
                self.connection_service.connect_with_dialog()
            else:
                self.connection_service.connect_with_dialog()
                
    def disconnect(self):
        """Disconnect from IB"""
        if self.connection_service:
            self.connection_service.disconnect()
            
    def switch_mode(self, new_mode: ConnectionMode) -> bool:
        """Switch between paper and live mode"""
        if not self.connection_service:
            return False
            
        def confirm_switch(current: str, new: str) -> bool:
            reply = QMessageBox.question(
                self._parent_widget,
                "Switch Trading Mode",
                f"Switch from {current} to {new} mode?\n\n"
                f"This will disconnect and reconnect to IB.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            return reply == QMessageBox.StandardButton.Yes
            
        return self.connection_service.switch_mode_with_confirmation(new_mode, confirm_switch)
        
    def select_account(self, account: str) -> bool:
        """Select trading account"""
        if self.connection_service:
            return self.connection_service.select_account(account)
        return False
        
    def get_connection_info(self) -> Dict:
        """Get current connection information"""
        if self.connection_service:
            return self.connection_service.get_connection_info()
        return {
            'connected': False,
            'mode': None,
            'port': None,
            'account': None,
            'accounts': []
        }
        
    def is_connected(self) -> bool:
        """Check if connected"""
        return self.connection_service.is_connected if self.connection_service else False
        
    def _check_connection(self):
        """Periodic connection check"""
        if self.connection_service:
            self.connection_service.periodic_update()
            
    def _update_account_info(self):
        """Periodic account update"""
        try:
            if not self.is_connected():
                return
                
            account_service = get_account_service()
            if account_service and account_service.account_manager:
                # Update account data in background
                account_service.update_account_data()
                
        except Exception as e:
            logger.error(f"Error in periodic account update: {str(e)}")
            
    def _show_startup_dialog(self, welcome_text: str, info_text: str) -> Optional[ConnectionMode]:
        """Show startup connection dialog"""
        msg_box = QMessageBox(self._parent_widget)
        msg_box.setWindowTitle(config.UI_MESSAGES['dialog_titles']['connect'])
        msg_box.setText(welcome_text)
        msg_box.setInformativeText(info_text)
        
        # Add custom buttons
        paper_button = msg_box.addButton("Paper Trading", QMessageBox.ButtonRole.ActionRole)
        live_button = msg_box.addButton("Live Trading", QMessageBox.ButtonRole.ActionRole)
        cancel_button = msg_box.addButton(QMessageBox.StandardButton.Cancel)
        
        msg_box.setDefaultButton(paper_button)
        msg_box.exec()
        
        clicked_button = msg_box.clickedButton()
        if clicked_button == paper_button:
            self.mode_changed.emit("paper")
            return ConnectionMode.PAPER
        elif clicked_button == live_button:
            self.mode_changed.emit("live")
            return ConnectionMode.LIVE
        else:
            return None
            
    def _show_account_selection_dialog(self, accounts: list) -> Optional[str]:
        """Show account selection dialog"""
        msg_box = QMessageBox(self._parent_widget)
        msg_box.setWindowTitle(config.UI_MESSAGES['dialog_titles']['account_select'])
        msg_box.setText("Multiple trading accounts found.\n\nPlease select the account you want to use:")
        
        # Create account info text
        account_text = ""
        buttons = []
        for account, net_liq in accounts:
            account_text += f"\n{account}: ${net_liq:,.2f}"
            button = msg_box.addButton(f"{account} (${net_liq:,.2f})", QMessageBox.ButtonRole.ActionRole)
            buttons.append((button, account))
            
        msg_box.setInformativeText(account_text)
        msg_box.addButton(QMessageBox.StandardButton.Cancel)
        msg_box.exec()
        
        clicked_button = msg_box.clickedButton()
        for button, account in buttons:
            if clicked_button == button:
                return account
        return None
        
    def _show_account_confirmation_dialog(self, account: str, net_liq: float) -> bool:
        """Show single account confirmation dialog"""
        reply = QMessageBox.information(
            self._parent_widget,
            config.UI_MESSAGES['dialog_titles']['account_connected'],
            f"Connected to account: {account}\nNet Liquidation: ${net_liq:,.2f}",
            QMessageBox.StandardButton.Ok
        )
        return True
        
    def _on_connection_status_changed(self, connected: bool, message: str):
        """Handle connection status change"""
        self.connection_status_changed.emit(connected, message)
        self.update_status(message, config.STATUS_MSG_DURATION['normal'])
        
        if connected:
            self._setup_services_on_connect()
        else:
            self._cleanup_services_on_disconnect()
            
    def _on_account_selected(self, account: str):
        """Handle account selection"""
        self.account_selected.emit(account)
        logger.info(f"Account selected: {account}")
        
    def _on_account_info_updated(self, net_liq: float, buying_power: float):
        """Handle account info update"""
        self.account_info_updated.emit(net_liq, buying_power)
        
    def _setup_services_on_connect(self):
        """Setup services when connected"""
        try:
            # Setup RiskService with account manager
            risk_service = get_risk_service()
            if risk_service and self.connection_service.account_manager:
                risk_service.set_account_manager(self.connection_service.account_manager)
                
            # Setup AccountService with account manager
            account_service = get_account_service()
            if account_service and self.connection_service.account_manager:
                account_service.account_manager = self.connection_service.account_manager
                # Subscribe to account updates
                account_service.register_account_update_callback(self._on_account_update_from_service)
                
        except Exception as e:
            logger.error(f"Error setting up services on connect: {str(e)}")
            
    def _cleanup_services_on_disconnect(self):
        """Cleanup services when disconnected"""
        try:
            # Clear account manager from services
            account_service = get_account_service()
            if account_service:
                account_service.account_manager = None
                
            risk_service = get_risk_service()
            if risk_service:
                risk_service.set_account_manager(None)
                
        except Exception as e:
            logger.error(f"Error cleaning up services on disconnect: {str(e)}")
            
    def _on_account_update_from_service(self, account_data: dict):
        """Handle account update from AccountService"""
        try:
            net_liq = account_data.get('net_liquidation', 0)
            buying_power = account_data.get('buying_power', 0)
            
            # Emit update
            self.account_info_updated.emit(net_liq, buying_power)
            
            logger.info(f"Account updated: NLV=${net_liq:,.2f}, BP=${buying_power:,.2f}")
            
        except Exception as e:
            logger.error(f"Error handling account update: {str(e)}")