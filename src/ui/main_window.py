"""
Main Window
Refactored main window using controllers and panels
"""

import sys
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QKeyEvent

from src.ui.controllers import (
    TradingController, MarketDataController, ConnectionController
)
from src.ui.panels import ConnectionPanel, TradingPanel, StatusPanel
from src.services import (
    register_service, initialize_all_services, cleanup_all_services,
    AccountService, OrderService, RiskService
)
from src.services.unified_data_service import unified_data_service
from src.services.event_bus import start_event_bus, stop_event_bus
from src.utils.logger import logger
import config


class MainWindow(QMainWindow):
    """Main application window - orchestrates controllers and panels"""
    
    def __init__(self):
        super().__init__()
        
        # Start event bus
        start_event_bus()
        
        # Initialize services
        self._init_services()
        
        # Create controllers
        self.trading_controller = TradingController(self)
        self.market_data_controller = MarketDataController(self)
        self.connection_controller = ConnectionController(self)
        
        # Create UI panels
        self.connection_panel = ConnectionPanel()
        self.trading_panel = TradingPanel()
        self.status_panel = StatusPanel()
        
        # Initialize UI
        self._init_ui()
        
        # Setup connections
        self._setup_connections()
        
        # Initialize controllers
        self._init_controllers()
        
        # Start connection flow after UI is ready
        QTimer.singleShot(config.TIMER_CONFIG['startup_dialog_delay'], 
                         self.connection_controller.start_connection_flow)
        
    def _init_services(self):
        """Initialize and register all services"""
        try:
            logger.info("Initializing services...")
            
            # Create services
            account_service = AccountService()
            order_service = OrderService()
            risk_service = RiskService()
            
            # Register services
            register_service('data', unified_data_service)
            register_service('account', account_service)
            register_service('order', order_service)
            register_service('risk', risk_service)
            
            # Initialize all services
            if not initialize_all_services():
                logger.error("Failed to initialize all services")
                QMessageBox.critical(self, "Error", 
                    "Failed to initialize services. Application may not work correctly.")
            else:
                logger.info("All services initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing services: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to initialize services: {str(e)}")
            
    def _init_controllers(self):
        """Initialize all controllers"""
        try:
            self.trading_controller.initialize()
            self.market_data_controller.initialize()
            self.connection_controller.initialize()
            
            logger.info("All controllers initialized")
            
        except Exception as e:
            logger.error(f"Error initializing controllers: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to initialize controllers: {str(e)}")
            
    def _init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Trading Assistant - MVP")
        self.setGeometry(
            config.WINDOW_CONFIG['main_window']['position'][0],
            config.WINDOW_CONFIG['main_window']['position'][1],
            config.WINDOW_CONFIG['main_window']['size'][0],
            config.WINDOW_CONFIG['main_window']['size'][1]
        )
        
        # Create central widget with main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Add panels
        main_layout.addWidget(self.connection_panel)
        main_layout.addWidget(self.trading_panel)
        
        # Create menu bar
        self._create_menu_bar()
        
        # Set status bar
        self.setStatusBar(self.status_panel)
        
    def _create_menu_bar(self):
        """Create the application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        connect_action = QAction('Connect to IB', self)
        connect_action.triggered.connect(self.connection_controller.connect)
        file_menu.addAction(connect_action)
        
        disconnect_action = QAction('Disconnect', self)
        disconnect_action.triggered.connect(self.connection_controller.disconnect)
        file_menu.addAction(disconnect_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Settings menu
        settings_menu = menubar.addMenu('Settings')
        
        config_action = QAction('Configuration', self)
        config_action.triggered.connect(self._show_config_dialog)
        settings_menu.addAction(config_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
    def _setup_connections(self):
        """Setup all signal/slot connections"""
        # Connection Panel -> Connection Controller
        self.connection_panel.connect_requested.connect(self.connection_controller.connect)
        self.connection_panel.disconnect_requested.connect(self.connection_controller.disconnect)
        self.connection_panel.account_changed.connect(self.connection_controller.select_account)
        
        # Connection Controller -> Panels
        self.connection_controller.connection_status_changed.connect(self._on_connection_status_changed)
        self.connection_controller.account_selected.connect(self.connection_panel.set_selected_account)
        self.connection_controller.account_info_updated.connect(self.connection_panel.update_account_info)
        self.connection_controller.mode_changed.connect(self.connection_panel.set_trading_mode)
        
        # Trading Panel -> Controllers
        self.trading_panel.order_submitted.connect(self._on_order_submitted)
        self.trading_panel.fetch_price_requested.connect(self._on_fetch_price_requested)
        self.trading_panel.symbol_selected.connect(self._on_symbol_selected)
        
        # Market Data Controller -> Trading Panel
        self.market_data_controller.price_data_received.connect(self.trading_panel.update_price_data)
        self.market_data_controller.price_fetch_started.connect(
            lambda: self.trading_panel.order_assistant.show_fetch_progress()
        )
        self.market_data_controller.price_fetch_completed.connect(
            lambda: self.trading_panel.order_assistant.hide_fetch_progress()
        )
        self.market_data_controller.price_fetch_failed.connect(
            lambda: self.trading_panel.order_assistant.hide_fetch_progress()
        )
        
        # Controller status updates -> Status Panel
        self.trading_controller.status_update.connect(self.status_panel.show_message)
        self.market_data_controller.status_update.connect(self.status_panel.show_message)
        self.connection_controller.status_update.connect(self.status_panel.show_message)
        
        # Controller errors -> Status Panel
        self.trading_controller.error_occurred.connect(
            lambda msg: self.status_panel.show_error(msg)
        )
        self.market_data_controller.error_occurred.connect(
            lambda msg: self.status_panel.show_error(msg)
        )
        self.connection_controller.error_occurred.connect(
            lambda msg: self.status_panel.show_error(msg)
        )
        
    def _on_connection_status_changed(self, connected: bool, message: str):
        """Handle connection status change"""
        # Update connection panel
        info = self.connection_controller.get_connection_info()
        self.connection_panel.update_connection_status(connected, info)
        
        # Update status panel
        mode = info.get('mode')
        self.status_panel.update_connection_status(connected, mode)
        
        # Update Order Assistant when connected
        if connected:
            self.trading_panel.order_assistant.set_risk_calculator(None)
            
    def _on_order_submitted(self, order_data: dict):
        """Handle order submission from Trading Panel"""
        if not self.connection_controller.is_connected():
            self.trading_controller.show_error("Not connected to IB. Please connect first.")
            return
            
        # Validate order
        is_valid, messages = self.trading_controller.validate_order(order_data)
        
        if not is_valid:
            self.trading_controller.show_error(
                "Order Validation Failed:\n\n" + "\n".join(messages)
            )
            return
            
        # Check for warnings
        warnings = [msg for msg in messages if any(
            word in msg for word in ["Warning", "Large", "High"]
        )]
        
        if warnings:
            warning_msg = "Trade Warnings:\n\n" + "\n".join(warnings) + "\n\nContinue anyway?"
            reply = QMessageBox.warning(
                self, "Trade Warnings", warning_msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
                
        # Get confirmation
        if self.trading_controller.show_order_confirmation(order_data):
            # Add account if not present
            if 'account' not in order_data:
                info = self.connection_controller.get_connection_info()
                order_data['account'] = info.get('account')
                
            # Submit order
            self.trading_controller.submit_order(order_data)
            
    def _on_fetch_price_requested(self, symbol: str):
        """Handle price fetch request"""
        # Get current direction from Order Assistant
        direction = ('BUY' if self.trading_panel.order_assistant.long_button.isChecked() 
                    else 'SELL')
        
        # Fetch price data
        self.market_data_controller.fetch_price_data(symbol, direction)
        
    def _on_symbol_selected(self, symbol: str):
        """Handle symbol selection from screener"""
        try:
            logger.info(f"Symbol selected: {symbol}")
            
            # Automatically fetch price if connected
            if self.connection_controller.is_connected():
                self._on_fetch_price_requested(symbol)
                self.status_panel.show_message(
                    f"Selected {symbol} from screener and fetching price...", 3000
                )
            else:
                self.status_panel.show_message(
                    f"Selected {symbol} from screener (connect to IB to fetch prices)", 3000
                )
                
        except Exception as e:
            logger.error(f"Error handling symbol selection: {str(e)}")
            
    def _show_config_dialog(self):
        """Show configuration dialog"""
        QMessageBox.information(
            self, "Configuration",
            "Configuration dialog will be implemented in a future version."
        )
        
    def _show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "About Trading Assistant",
            "Trading Assistant MVP\n\n"
            "A low-latency trading application for Interactive Brokers\n"
            "Version: 0.1.0 (MVP)"
        )
        
    def keyPressEvent(self, event: QKeyEvent):
        """Handle global keyboard shortcuts"""
        try:
            # Get the pressed key as text
            key_text = event.text()
            
            # Quick symbol input (A-Z starts symbol entry)
            if key_text and key_text.isalpha():
                symbol_input = self.trading_panel.order_assistant.symbol_input
                
                # If symbol input not focused, focus it and start fresh
                if not symbol_input.hasFocus():
                    symbol_input.setFocus()
                    symbol_input.clear()
                    symbol_input.insert(key_text.upper())
                    self.status_panel.show_message(
                        f"Symbol input focused - typing: {key_text.upper()}", 2000
                    )
                    logger.info(f"Quick symbol input: '{key_text.upper()}'")
                    return
                    
            # For other keys, call parent implementation
            super().keyPressEvent(event)
            
        except Exception as e:
            logger.error(f"Error in key press handler: {str(e)}")
            super().keyPressEvent(event)
            
    def closeEvent(self, event):
        """Handle application close"""
        try:
            # Cleanup controllers
            self.trading_controller.cleanup()
            self.market_data_controller.cleanup()
            self.connection_controller.cleanup()
            
            # Cleanup panels
            self.trading_panel.cleanup()
            
            # Cleanup services
            cleanup_all_services()
            
            # Stop event bus
            stop_event_bus()
            
            logger.info("Application closed cleanly")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            
        event.accept()


def main():
    """Main entry point"""
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Trading Assistant")
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == '__main__':
    main()