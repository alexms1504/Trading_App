#!/usr/bin/env python3
"""
Trading App - Main Entry Point
A low-latency trading application for Interactive Brokers
"""

import sys
import asyncio
from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QStatusBar, QMessageBox, QComboBox, QPushButton, QButtonGroup, QRadioButton
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot, QThreadPool, QRunnable, QObject
from PyQt6.QtGui import QAction, QIcon, QKeyEvent

from src.utils.logger import logger
from src.core.ib_connection import IBConnectionManager
from src.core.account_manager import AccountManager
from src.core.risk_calculator import RiskCalculator
from src.core.order_manager import OrderManager
from src.core.data_fetcher import data_fetcher
from src.core.simple_threaded_fetcher import simple_threaded_data_fetcher
from src.ui.order_assistant import OrderAssistantWidget
from src.ui.market_screener import MarketScreenerWidget
from src.ui.chart_widget_embedded import ChartWidget
import config


# PriceFetchTimer class removed - replaced with threaded_data_fetcher for non-blocking price fetching


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.ib_manager: Optional[IBConnectionManager] = None
        self.account_manager: Optional[AccountManager] = None
        self.risk_calculator: Optional[RiskCalculator] = None
        self.order_manager: Optional[OrderManager] = None
        self.order_assistant: Optional[OrderAssistantWidget] = None
        self.market_screener: Optional[MarketScreenerWidget] = None
        self.chart_widget: Optional[ChartWidget] = None
        self.connection_timer = QTimer()
        self.threaded_fetcher = simple_threaded_data_fetcher
        
        self.init_ui()
        self.setup_connections()
        self.setup_threaded_connections()
        
        # Show connection dialog on startup
        QTimer.singleShot(500, self.show_startup_connection_dialog)
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Trading Assistant - MVP")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main vertical layout
        main_layout = QVBoxLayout(central_widget)
        
        # TOP SECTION - Connection and Account Controls
        top_controls = self.create_top_controls()
        main_layout.addWidget(top_controls)
        
        # MIDDLE SECTION - Trading Interface
        middle_layout = QHBoxLayout()
        
        # Left side - Order Assistant
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.order_assistant = OrderAssistantWidget()
        left_layout.addWidget(self.order_assistant)
        left_widget.setMaximumWidth(450)  # Narrower width for order assistant
        
        # Center - Chart Widget
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        
        # Add chart widget
        self.chart_widget = ChartWidget()
        center_layout.addWidget(self.chart_widget)
        
        # Right side - Market Screener
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.market_screener = MarketScreenerWidget()
        right_layout.addWidget(self.market_screener)
        right_widget.setMaximumWidth(420)  # Even narrower width for screener
        
        # Add all three sections to middle layout
        middle_layout.addWidget(left_widget, 1)  # Ratio 1
        middle_layout.addWidget(center_widget, 2)  # Ratio 2 (larger for charts)
        middle_layout.addWidget(right_widget, 1)  # Ratio 1
        
        # Add middle section to main layout
        main_layout.addLayout(middle_layout)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create status bar
        self.create_status_bar()
        
    def create_top_controls(self):
        """Create the top control panel with connection and account controls"""
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(10, 5, 10, 5)
        
        # Trading mode selection
        trading_mode_label = QLabel("Mode:")
        self.trading_mode_group = QButtonGroup()
        
        self.paper_radio = QRadioButton("Paper")
        self.paper_radio.setChecked(True)  # Default to paper
        self.paper_radio.setStyleSheet("QRadioButton { color: #2196F3; font-weight: bold; }")
        self.trading_mode_group.addButton(self.paper_radio, 0)
        
        self.live_radio = QRadioButton("Live")
        self.live_radio.setStyleSheet("QRadioButton { color: #FF5722; font-weight: bold; }")
        self.trading_mode_group.addButton(self.live_radio, 1)
        
        # Connect trading mode change
        self.trading_mode_group.buttonClicked.connect(self.on_trading_mode_changed)
        
        # Connection controls
        self.connect_button = QPushButton("Connect to IB")
        self.connect_button.clicked.connect(self.connect_to_ib)
        self.connect_button.setMaximumWidth(120)
        
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_from_ib)
        self.disconnect_button.setMaximumWidth(120)
        self.disconnect_button.setEnabled(False)
        
        # Connection status indicator
        self.connection_status_label = QLabel("● Disconnected")
        self.connection_status_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
        
        # Account selector
        account_label = QLabel("Account:")
        self.account_selector = QComboBox()
        self.account_selector.setMinimumWidth(150)
        self.account_selector.setEnabled(False)
        self.account_selector.currentTextChanged.connect(self.on_account_changed)
        
        # Account info display
        self.account_value_label = QLabel("Value: N/A")
        self.account_value_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        # Add widgets to layout
        top_layout.addWidget(trading_mode_label)
        top_layout.addWidget(self.paper_radio)
        top_layout.addWidget(self.live_radio)
        top_layout.addWidget(QLabel("|"))  # Separator
        top_layout.addWidget(self.connect_button)
        top_layout.addWidget(self.disconnect_button)
        top_layout.addWidget(self.connection_status_label)
        top_layout.addWidget(QLabel("|"))  # Separator
        top_layout.addWidget(account_label)
        top_layout.addWidget(self.account_selector)
        top_layout.addWidget(QLabel("|"))  # Separator
        top_layout.addWidget(self.account_value_label)
        top_layout.addStretch()  # Push everything to the left
        
        # Style the top panel
        top_widget.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                border-bottom: 1px solid #ccc;
            }
            QPushButton {
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:disabled {
                color: #999;
            }
        """)
        
        return top_widget
        
    def create_menu_bar(self):
        """Create the application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        connect_action = QAction('Connect to IB', self)
        connect_action.triggered.connect(self.connect_to_ib)
        file_menu.addAction(connect_action)
        
        disconnect_action = QAction('Disconnect', self)
        disconnect_action.triggered.connect(self.disconnect_from_ib)
        file_menu.addAction(disconnect_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Settings menu
        settings_menu = menubar.addMenu('Settings')
        
        config_action = QAction('Configuration', self)
        config_action.triggered.connect(self.show_config_dialog)
        settings_menu.addAction(config_action)
        
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_status_bar(self):
        """Create a simplified status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add permanent message
        self.status_bar.showMessage("Ready to connect...")
        
    def setup_connections(self):
        """Setup signal connections and timers"""
        # Setup connection check timer (every 2 seconds)
        self.connection_timer.timeout.connect(self.check_connection_status)
        self.connection_timer.start(2000)
        
        # Order Assistant connections
        self.order_assistant.order_submitted.connect(self.on_order_submitted)
        self.order_assistant.fetch_price_requested.connect(self.on_fetch_price_requested)
        
        # Connect Order Assistant price changes to chart
        self.order_assistant.entry_price_changed.connect(self.on_order_assistant_entry_changed)
        self.order_assistant.stop_loss_changed.connect(self.on_order_assistant_stop_loss_changed)
        self.order_assistant.take_profit_changed.connect(self.on_order_assistant_take_profit_changed)
        
        # Market Screener connections
        self.market_screener.symbol_selected.connect(self.on_screener_symbol_selected)
        
        # Chart Widget connections
        if self.chart_widget:
            # When symbol selected from screener, update chart
            self.market_screener.symbol_selected.connect(self.on_chart_symbol_selected)
            
            # When "Fetch Price" clicked in Order Assistant, update chart
            self.order_assistant.fetch_price_requested.connect(self.on_fetch_price_chart_update)
            
            # Connect price level signals from chart to Order Assistant
            self.chart_widget.chart_entry_changed.connect(self.on_chart_price_changed_entry)
            self.chart_widget.chart_stop_loss_changed.connect(self.on_chart_price_changed_stop_loss)
            self.chart_widget.chart_take_profit_changed.connect(self.on_chart_price_changed_take_profit)
            
    def setup_threaded_connections(self):
        """Setup connections for threaded operations"""
        # Connect threaded data fetcher signals
        self.threaded_fetcher.fetch_started.connect(self.on_threaded_fetch_started)
        self.threaded_fetcher.fetch_completed.connect(self.on_threaded_fetch_completed)
        self.threaded_fetcher.fetch_failed.connect(self.on_threaded_fetch_failed)
        logger.info("Threaded data fetcher connections established")
        
    def show_startup_connection_dialog(self):
        """Show connection dialog on app startup"""
        try:
            # Create custom dialog with Paper/Live buttons
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Connect to Interactive Brokers")
            msg_box.setText("Welcome to Trading Assistant!\n\nSelect your trading mode to connect:")
            msg_box.setInformativeText(
                "📄 Paper Trading (Port 7497) - Safe for testing\n"
                "💰 Live Trading (Port 7496) - Real money\n\n"
                "After connecting, you can choose your account."
            )
            
            # Add custom buttons
            paper_button = msg_box.addButton("Paper Trading", QMessageBox.ButtonRole.AcceptRole)
            live_button = msg_box.addButton("Live Trading", QMessageBox.ButtonRole.AcceptRole)
            skip_button = msg_box.addButton("Skip", QMessageBox.ButtonRole.RejectRole)
            
            # Set paper as default
            msg_box.setDefaultButton(paper_button)
            
            # Show dialog and get result
            msg_box.exec()
            clicked_button = msg_box.clickedButton()
            
            if clicked_button == paper_button:
                self.paper_radio.setChecked(True)
                self.status_bar.showMessage("Connecting to Paper Trading...", 3000)
                QTimer.singleShot(100, self.connect_to_ib)
            elif clicked_button == live_button:
                self.live_radio.setChecked(True)
                self.status_bar.showMessage("Connecting to Live Trading...", 3000)
                QTimer.singleShot(100, self.connect_to_ib)
            else:
                self.status_bar.showMessage("Connect to IB when ready to start trading", 5000)
                
        except Exception as e:
            logger.error(f"Error in startup connection dialog: {str(e)}")
    
    def show_account_selection_dialog(self, accounts):
        """Show dialog to select account when multiple accounts are available"""
        try:
            # Create custom dialog for account selection
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Select Trading Account")
            msg_box.setText("Connected successfully!\n\nMultiple accounts found. Please select your trading account:")
            
            # Get account details for display
            account_info = []
            for account in accounts:
                net_liq = self.account_manager.get_net_liquidation(account) if self.account_manager else 0
                account_info.append(f"{account} (${net_liq:,.2f})")
            
            msg_box.setInformativeText("\n".join(account_info))
            
            # Add button for each account
            account_buttons = []
            for i, account in enumerate(accounts):
                net_liq = self.account_manager.get_net_liquidation(account) if self.account_manager else 0
                button_text = f"{account}\n${net_liq:,.2f}"
                button = msg_box.addButton(button_text, QMessageBox.ButtonRole.AcceptRole)
                account_buttons.append((button, account))
            
            # Set first account as default
            if account_buttons:
                msg_box.setDefaultButton(account_buttons[0][0])
            
            # Show dialog and get result
            msg_box.exec()
            clicked_button = msg_box.clickedButton()
            
            # Find which account was selected
            selected_account = None
            for button, account in account_buttons:
                if clicked_button == button:
                    selected_account = account
                    break
            
            if selected_account:
                # Set the selected account
                self.account_selector.setCurrentText(selected_account)
                self.ib_manager.set_active_account(selected_account)
                self.update_account_info()
                self.status_bar.showMessage(f"Account selected: {selected_account}", 3000)
                logger.info(f"User selected account: {selected_account}")
                
        except Exception as e:
            logger.error(f"Error in account selection dialog: {str(e)}")
    
    def show_single_account_confirmation(self, account):
        """Show confirmation dialog when only one account is available"""
        try:
            net_liq = self.account_manager.get_net_liquidation(account) if self.account_manager else 0
            
            QMessageBox.information(
                self,
                "Account Connected",
                f"Connected successfully!\n\n"
                f"Trading Account: {account}\n"
                f"Account Value: ${net_liq:,.2f}\n\n"
                f"Ready to start trading!",
                QMessageBox.StandardButton.Ok
            )
            
            self.status_bar.showMessage(f"Ready to trade with account: {account}", 5000)
            logger.info(f"Single account connected: {account}")
            
        except Exception as e:
            logger.error(f"Error in single account confirmation: {str(e)}")
        
    def connect_to_ib(self):
        """Connect to Interactive Brokers"""
        try:
            # Get selected trading mode
            trading_mode = 'paper' if self.paper_radio.isChecked() else 'live'
            
            self.status_bar.showMessage(f"Connecting to IB TWS/Gateway ({trading_mode.upper()} mode)...")
            
            # Initialize connection manager
            self.ib_manager = IBConnectionManager()
            
            # Run connection in a separate thread to avoid blocking UI
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Connect with specified trading mode
            success = loop.run_until_complete(self.ib_manager.connect(trading_mode))
            
            if success:
                # Initialize account manager
                self.account_manager = AccountManager()
                
                # Initialize the account manager
                loop.run_until_complete(self.account_manager.initialize())
                
                # Initialize risk calculator
                self.risk_calculator = RiskCalculator(self.account_manager)
                
                # Initialize order manager
                self.order_manager = OrderManager()
                
                # Connect risk calculator to Order Assistant
                self.order_assistant.set_risk_calculator(self.risk_calculator)
                
                # Get accounts and populate selector
                accounts = self.ib_manager.get_accounts()
                if accounts:
                    # Clear and populate account selector
                    self.account_selector.clear()
                    self.account_selector.addItems(accounts)
                    self.account_selector.setEnabled(True)
                    
                    # Set the active account (first one by default)
                    active_account = self.ib_manager.get_active_account()
                    if active_account:
                        self.account_selector.setCurrentText(active_account)
                    
                    logger.info(f"Connected with {len(accounts)} accounts: {', '.join(accounts)}")
                    
                    # Show account selection dialog if multiple accounts
                    if len(accounts) > 1:
                        QTimer.singleShot(500, lambda: self.show_account_selection_dialog(accounts))
                    else:
                        # Single account - show confirmation
                        QTimer.singleShot(500, lambda: self.show_single_account_confirmation(accounts[0]))
                
                self.update_connection_status(True)
                mode_text = self.ib_manager.get_trading_mode().upper()
                self.status_bar.showMessage(f"Connected to IB successfully! ({mode_text} mode)", 5000)
                
                # Start updating account info
                self.update_account_info()
                
                # Subscribe to connection events
                self.ib_manager.subscribe_to_event(
                    'connection_lost', 
                    lambda: self.update_connection_status(False)
                )
                self.ib_manager.subscribe_to_event(
                    'connection_restored', 
                    lambda: self.update_connection_status(True)
                )
            else:
                self.show_error("Failed to connect to IB TWS/Gateway")
                
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            self.show_error(f"Connection error: {str(e)}")
            
    def disconnect_from_ib(self):
        """Disconnect from Interactive Brokers"""
        if self.ib_manager:
            try:
                # Run disconnect in event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.ib_manager.disconnect())
                
                self.ib_manager = None
                self.account_manager = None
                self.update_connection_status(False)
                self.account_selector.clear()
                self.account_selector.setEnabled(False)
                self.account_value_label.setText("Value: N/A")
                self.status_bar.showMessage("Disconnected from IB", 5000)
                
                # Re-enable trading mode selection
                self.paper_radio.setEnabled(True)
                self.live_radio.setEnabled(True)
            except Exception as e:
                logger.error(f"Disconnect error: {str(e)}")
                
    def check_connection_status(self):
        """Periodically check connection status"""
        if self.ib_manager:
            is_connected = self.ib_manager.is_connected()
            self.update_connection_status(is_connected)
            
            # Update account info if connected
            if is_connected:
                self.update_account_info()
            
    def update_connection_status(self, connected: bool):
        """Update connection status indicator"""
        if connected:
            mode = self.ib_manager.get_trading_mode().upper() if self.ib_manager else "UNKNOWN"
            port = self.ib_manager.current_port if self.ib_manager else "N/A"
            self.connection_status_label.setText(f"● Connected ({mode}:{port})")
            self.connection_status_label.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            # Disable trading mode selection when connected
            self.paper_radio.setEnabled(False)
            self.live_radio.setEnabled(False)
        else:
            self.connection_status_label.setText("● Disconnected")
            self.connection_status_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)
            # Enable trading mode selection when disconnected
            self.paper_radio.setEnabled(True)
            self.live_radio.setEnabled(True)
            
    def on_trading_mode_changed(self):
        """Handle trading mode change"""
        if self.ib_manager and self.ib_manager.is_connected():
            # If connected, ask user if they want to switch and reconnect
            trading_mode = 'paper' if self.paper_radio.isChecked() else 'live'
            current_mode = self.ib_manager.get_trading_mode()
            
            if trading_mode != current_mode:
                reply = QMessageBox.question(
                    self, 
                    "Switch Trading Mode", 
                    f"Switch from {current_mode.upper()} to {trading_mode.upper()} mode?\n\n"
                    f"This will disconnect and reconnect to IB.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.switch_trading_mode(trading_mode)
                else:
                    # Revert the radio button selection
                    if current_mode == 'paper':
                        self.paper_radio.setChecked(True)
                    else:
                        self.live_radio.setChecked(True)
        else:
            # Not connected, just update the mode for next connection
            trading_mode = 'paper' if self.paper_radio.isChecked() else 'live'
            self.status_bar.showMessage(f"Trading mode set to {trading_mode.upper()}", 3000)
            
    def switch_trading_mode(self, new_mode: str):
        """Switch trading mode and reconnect"""
        try:
            self.status_bar.showMessage(f"Switching to {new_mode.upper()} mode...")
            
            # Run switch in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            success = loop.run_until_complete(self.ib_manager.switch_trading_mode(new_mode))
            
            if success:
                self.update_connection_status(True)
                self.status_bar.showMessage(f"Switched to {new_mode.upper()} mode successfully!", 5000)
                
                # Update accounts and UI
                accounts = self.ib_manager.get_accounts()
                if accounts:
                    self.account_selector.clear()
                    self.account_selector.addItems(accounts)
                    active_account = self.ib_manager.get_active_account()
                    if active_account:
                        self.account_selector.setCurrentText(active_account)
                        
                self.update_account_info()
            else:
                self.show_error(f"Failed to switch to {new_mode.upper()} mode")
                
        except Exception as e:
            error_msg = f"Error switching trading mode: {str(e)}"
            logger.error(error_msg)
            self.show_error(error_msg)
            
    def show_config_dialog(self):
        """Show configuration dialog (placeholder)"""
        QMessageBox.information(self, "Configuration", 
                              "Configuration dialog will be implemented in a future version.")
        
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About Trading Assistant",
                         "Trading Assistant MVP\n\n"
                         "A low-latency trading application for Interactive Brokers\n"
                         "Version: 0.1.0 (MVP)")
        
    def show_error(self, message: str):
        """Show error message dialog"""
        QMessageBox.critical(self, "Error", message)
        
        
    def on_account_changed(self, account: str):
        """Handle account selection change"""
        if not account or not self.ib_manager:
            return
            
        # Set the new active account
        if self.ib_manager.set_active_account(account):
            logger.info(f"Switched to account: {account}")
            self.status_bar.showMessage(f"Switched to account: {account}", 3000)
            self.update_account_info()
        else:
            logger.error(f"Failed to switch to account: {account}")
            
    def update_account_info(self):
        """Update account information display"""
        if not self.account_manager or not self.ib_manager:
            return
            
        account = self.ib_manager.get_active_account()
        if not account:
            return
            
        # Get account values
        net_liq = self.account_manager.get_net_liquidation(account)
        buying_power = self.account_manager.get_buying_power(account)
        
        # Update display
        self.account_value_label.setText(
            f"Value: ${net_liq:,.2f} | BP: ${buying_power:,.2f}"
        )
        
        # Update Order Assistant with account value and buying power
        if self.order_assistant:
            self.order_assistant.set_account_value(net_liq)
            self.order_assistant.set_buying_power(buying_power)
        
    def on_order_submitted(self, order_data: dict):
        """Handle order submission from Order Assistant"""
        if not self.ib_manager or not self.ib_manager.is_connected():
            self.show_error("Not connected to IB. Please connect first.")
            return
            
        # Validate trade using risk calculator
        if self.risk_calculator:
            is_valid, messages = self.risk_calculator.validate_trade(
                symbol=order_data['symbol'],
                entry_price=order_data['entry_price'],
                stop_loss=order_data['stop_loss'],
                take_profit=order_data['take_profit'],
                shares=order_data['quantity'],
                direction=order_data['direction']
            )
            
            if not is_valid:
                self.show_error("Trade Validation Failed:\n\n" + "\n".join(messages))
                return
                
            # Show warnings if any
            warnings = [msg for msg in messages if "Warning" in msg or "Large" in msg or "High" in msg]
            if warnings:
                warning_msg = "Trade Warnings:\n\n" + "\n".join(warnings) + "\n\nContinue anyway?"
                reply = QMessageBox.warning(self, "Trade Warnings", warning_msg,
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply != QMessageBox.StandardButton.Yes:
                    return
        
        # Calculate R-multiple for display
        r_multiple = 0
        if self.risk_calculator:
            r_multiple = self.risk_calculator.calculate_r_multiple(
                order_data['entry_price'],
                order_data['stop_loss'],
                order_data['take_profit']
            )
            
        # Show enhanced confirmation dialog
        order_value = order_data['quantity'] * order_data['entry_price']
        dollar_risk = order_data['quantity'] * abs(order_data['entry_price'] - order_data['stop_loss'])
        
        # Calculate portfolio and BP percentages
        net_liq = self.account_manager.get_net_liquidation(self.ib_manager.get_active_account()) if self.account_manager else 100000
        buying_power = self.account_manager.get_buying_power(self.ib_manager.get_active_account()) if self.account_manager else 100000
        portfolio_pct = (order_value / net_liq * 100) if net_liq > 0 else 0
        bp_pct = (order_value / buying_power * 100) if buying_power > 0 else 0
        
        # Build profit targets text
        if order_data.get('use_multiple_targets', False):
            targets_text = ""
            for i, target in enumerate(order_data['profit_targets'], 1):
                if target['price'] > 0:
                    target_qty = int(order_data['quantity'] * target['percent'] / 100)
                    targets_text += f"\nTarget {i}: ${target['price']:.2f} ({target['percent']}% = {target_qty} shares)"
        else:
            targets_text = f"\nTake Profit: ${order_data['take_profit']:.2f} (R={r_multiple:.1f})"
        
        message = f"""
Order Preview:
{order_data['direction']} {order_data['quantity']} shares of {order_data['symbol']}
Entry: ${order_data['entry_price']:.2f} ({order_data['order_type']})
Stop Loss: ${order_data['stop_loss']:.2f}{targets_text}

Position Value: ${order_value:,.2f} ({portfolio_pct:.1f}% of Portfolio, {bp_pct:.1f}% of BP)
Dollar Risk: ${dollar_risk:,.2f}
Risk: {order_data['risk_percent']:.2f}%

Submit this order?
        """
        
        reply = QMessageBox.question(self, "Confirm Order", message.strip(),
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # Submit the order
            self.submit_order(order_data)
            
    def on_fetch_price_requested(self, symbol: str):
        """Handle price fetch request with non-blocking threaded execution"""
        if not self.ib_manager or not self.ib_manager.is_connected():
            self.show_error("Not connected to IB. Please connect first.")
            # Reset fetch button
            self.order_assistant.hide_fetch_progress()
            return
            
        try:
            logger.info(f"Starting threaded fetch for {symbol}")
            
            # Update UI to show fetching state with progress
            self.order_assistant.show_fetch_progress()
            self.status_bar.showMessage(f"Fetching real-time data for {symbol}...")
            
            # Get current direction for stop loss calculations
            direction = 'BUY' if self.order_assistant.long_button.isChecked() else 'SELL'
            
            # Start threaded price fetch (non-blocking)
            self.threaded_fetcher.fetch_price_and_stops_async(symbol, direction)
                
        except Exception as e:
            error_msg = f"Error starting threaded price fetch: {str(e)}"
            logger.error(error_msg)
            self.show_error(error_msg)
            self.reset_fetch_button()
            
    def on_price_data_received(self, price_data: dict):
        """Handle received price data from worker thread"""
        try:
            self.process_price_data(price_data)
            current_price = price_data['current_price']
            symbol = price_data['symbol']
            self.status_bar.showMessage(f"Real price data fetched for {symbol}: ${current_price:.2f}", 5000)
        except Exception as e:
            logger.error(f"Error processing price data: {str(e)}")
            self.show_error(f"Error processing price data: {str(e)}")
        finally:
            self.reset_fetch_button()
            
    def on_price_fetch_error(self, error_msg: str):
        """Handle price fetch error from worker thread"""
        logger.error(error_msg)
        self.show_error(error_msg)
        self.reset_fetch_button()
            
    def process_price_data(self, price_data: dict):
        """Process price data and update UI"""
        try:
            symbol = price_data['symbol']
            current_price = price_data['current_price']
            stop_levels = price_data['stop_levels']
            direction = price_data['direction']
            
            # Validate current price first
            if current_price <= 0 or current_price > 5000:  # Reasonable stock price range
                logger.error(f"Invalid current price received: ${current_price:.2f}")
                self.show_error(f"Invalid price data received for {symbol}: ${current_price:.2f}")
                return
            
            # Update entry price based on direction
            if direction == 'BUY':
                # For buying, use current price or ask if available
                entry_price = current_price
                if 'ask' in price_data['price_data'] and price_data['price_data']['ask']:
                    ask_price = price_data['price_data']['ask']
                    if 0 < ask_price <= 5000:  # Validate ask price
                        entry_price = ask_price
            else:
                # For selling, use current price or bid if available
                entry_price = current_price
                if 'bid' in price_data['price_data'] and price_data['price_data']['bid']:
                    bid_price = price_data['price_data']['bid']
                    if 0 < bid_price <= 5000:  # Validate bid price
                        entry_price = bid_price
            
            # Final validation of entry price
            if entry_price <= 0 or entry_price > 5000:
                logger.error(f"Invalid entry price calculated: ${entry_price:.2f}")
                return
                
            logger.info(f"Setting entry price to ${entry_price:.2f} for {symbol}")
            self.order_assistant.entry_price.setValue(entry_price)
            
            # Set default stop loss based on direction - use lower of prior and current 5min
            if direction == 'BUY':
                # For LONG positions, use the lower of prior 5min and current 5min
                prior_5min = stop_levels.get('prior_5min_low')
                current_5min = stop_levels.get('current_5min_low')
                
                if prior_5min and current_5min:
                    # Use the lower of the two (safer stop loss) with smart adjustment
                    raw_stop = min(prior_5min, current_5min)
                    default_stop = self._apply_smart_stop_adjustment(raw_stop, entry_price, 'BUY')
                    logger.info(f"Using lower 5min stop: Prior=${prior_5min:.4f}, Current=${current_5min:.4f}, Raw=${raw_stop:.4f}, Adjusted=${default_stop:.4f}")
                elif prior_5min:
                    default_stop = self._apply_smart_stop_adjustment(prior_5min, entry_price, 'BUY')
                    logger.info(f"Using prior 5min stop: Raw=${prior_5min:.4f}, Adjusted=${default_stop:.4f}")
                elif current_5min:
                    default_stop = self._apply_smart_stop_adjustment(current_5min, entry_price, 'BUY')
                    logger.info(f"Using current 5min stop: Raw=${current_5min:.4f}, Adjusted=${default_stop:.4f}")
                else:
                    default_stop = stop_levels.get('2_percent', current_price * 0.98)
                    logger.info(f"Using 2% stop fallback: ${default_stop:.4f}")
            else:
                # For SHORT positions, use the higher of prior 5min and current 5min
                prior_5min = stop_levels.get('prior_5min_low')
                current_5min = stop_levels.get('current_5min_low')
                
                if prior_5min and current_5min:
                    # Use the higher of the two (safer stop loss for shorts) with smart adjustment
                    raw_stop = max(prior_5min, current_5min)
                    default_stop = self._apply_smart_stop_adjustment(raw_stop, entry_price, 'SELL')
                    logger.info(f"Using higher 5min stop for SHORT: Prior=${prior_5min:.4f}, Current=${current_5min:.4f}, Raw=${raw_stop:.4f}, Adjusted=${default_stop:.4f}")
                elif prior_5min:
                    default_stop = self._apply_smart_stop_adjustment(prior_5min, entry_price, 'SELL')
                elif current_5min:
                    default_stop = self._apply_smart_stop_adjustment(current_5min, entry_price, 'SELL')
                else:
                    default_stop = stop_levels.get('2_percent', current_price * 1.02)
            
            self.order_assistant.stop_loss_price.setValue(default_stop)
            
            # Set take profit (simple 2:1 risk/reward)
            risk_distance = abs(entry_price - default_stop)
            if direction == 'BUY':
                take_profit = entry_price + (2 * risk_distance)
            else:
                take_profit = entry_price - (2 * risk_distance)
            
            # Validate and set take profit
            take_profit = max(0.01, min(5000.0, take_profit))  # Clamp to reasonable range
            self.order_assistant.take_profit_price.setValue(take_profit)
            # Manually trigger chart update since setValue doesn't emit signals when called programmatically
            self.order_assistant.on_take_profit_price_changed(take_profit)
            
            # Update price info display
            price_info = price_data['price_data']
            last = price_info.get('last', current_price)
            bid = price_info.get('bid', current_price - 0.01)
            ask = price_info.get('ask', current_price + 0.01)
            self.order_assistant.update_price_info(last, bid, ask)
            
            # Update stop loss options
            self.order_assistant.update_stop_loss_options(stop_levels)
            
            # Update chart price levels
            if self.chart_widget:
                self.chart_widget.update_price_levels(
                    entry=entry_price,
                    stop_loss=default_stop,
                    take_profit=take_profit
                )
            
        except Exception as e:
            error_msg = f"Error processing price data: {str(e)}"
            logger.error(error_msg)
            self.show_error(error_msg)
        
    def reset_fetch_button(self):
        """Reset the fetch price button to normal state"""
        if self.order_assistant:
            self.order_assistant.hide_fetch_progress()
            
    def on_threaded_fetch_started(self, symbol: str):
        """Handle threaded fetch started signal"""
        logger.info(f"Threaded fetch started for {symbol}")
        # UI is already updated in on_fetch_price_requested
        
    def on_threaded_fetch_completed(self, price_data: dict):
        """Handle threaded fetch completed signal"""
        try:
            logger.info(f"on_threaded_fetch_completed called with data keys: {list(price_data.keys())}")
            logger.info(f"Current price: ${price_data.get('current_price', 'N/A')}")
            self.process_price_data(price_data)
            current_price = price_data['current_price']
            symbol = price_data['symbol']
            self.status_bar.showMessage(f"Real price data fetched for {symbol}: ${current_price:.2f}", 5000)
            logger.info(f"Threaded fetch completed for {symbol}: ${current_price:.2f}")
        except Exception as e:
            logger.error(f"Error processing threaded price data: {str(e)}")
            logger.exception("Full traceback:")
            self.show_error(f"Error processing price data: {str(e)}")
        finally:
            self.reset_fetch_button()
            
    def on_threaded_fetch_failed(self, error_msg: str):
        """Handle threaded fetch failed signal"""
        logger.error(f"Threaded fetch failed: {error_msg}")
        self.show_error(error_msg)
        self.reset_fetch_button()
            
    def on_screener_symbol_selected(self, symbol: str):
        """Handle symbol selection from market screener"""
        try:
            logger.info(f"Screener symbol selected: {symbol}")
            
            # Set the symbol in Order Assistant
            self.order_assistant.symbol_input.setText(symbol)
            
            # Automatically fetch price data for the selected symbol
            if self.ib_manager and self.ib_manager.is_connected():
                self.on_fetch_price_requested(symbol)
                self.status_bar.showMessage(f"Selected {symbol} from screener and fetching price...", 3000)
            else:
                self.status_bar.showMessage(f"Selected {symbol} from screener (connect to IB to fetch prices)", 3000)
                
        except Exception as e:
            error_msg = f"Error handling screener symbol selection: {str(e)}"
            logger.error(error_msg)
            self.show_error(error_msg)
        
    def submit_order(self, order_data: dict):
        """Submit the order to IB"""
        if not self.order_manager:
            self.show_error("Order manager not initialized")
            return
            
        # Show progress
        self.status_bar.showMessage("Submitting order...")
        
        # Submit the order synchronously
        try:
            # Check if using multiple targets
            if order_data.get('use_multiple_targets', False):
                success, message, trades = self.order_manager.submit_multiple_target_order(
                    symbol=order_data['symbol'],
                    quantity=order_data['quantity'],
                    entry_price=order_data['entry_price'],
                    stop_loss=order_data['stop_loss'],
                    profit_targets=order_data['profit_targets'],
                    direction=order_data['direction'],
                    order_type=order_data['order_type'],
                    account=self.ib_manager.get_active_account()
                )
            else:
                success, message, trades = self.order_manager.submit_bracket_order(
                    symbol=order_data['symbol'],
                    quantity=order_data['quantity'],
                    entry_price=order_data['entry_price'],
                    stop_loss=order_data['stop_loss'],
                    take_profit=order_data['take_profit'],
                    direction=order_data['direction'],
                    order_type=order_data['order_type'],
                    account=self.ib_manager.get_active_account()
                )
            
            if success:
                # Success message with important notes
                order_ids = [t.order.orderId for t in trades] if trades else []
                
                # Check if orders need confirmation in TWS
                needs_confirmation = False
                if trades:
                    for trade in trades:
                        if trade.orderStatus.status in ['PreSubmitted', 'Inactive']:
                            needs_confirmation = True
                            break
                
                if needs_confirmation:
                    success_msg = f"""Order submitted successfully!
                    
Order IDs: {order_ids}

⚠️  IMPORTANT: Your orders may require manual confirmation in TWS.

If orders are not executing automatically:
1. Check TWS for pending orders requiring confirmation
2. Go to TWS → File → Global Configuration → API → Settings
3. Enable "Bypass Order Precautions for API Orders"
4. Restart TWS after making changes

Check the TWS Order Management window for your bracket orders."""
                else:
                    success_msg = f"Order submitted successfully!\n\nOrder IDs: {order_ids}\n\nBracket orders are active in TWS."
                    
                QMessageBox.information(self, "Order Submitted", success_msg)
                
                # DON'T clear the order form - user requested to keep values
                # self.order_assistant.clear_form()
                
                # Update status
                self.status_bar.showMessage(f"Order submitted: {order_data['symbol']} - {message}", 5000)
                logger.info(f"Order submitted successfully: {order_ids}")
                
                # Check API configuration and warn if needed
                if self.order_manager:
                    is_configured, config_issues = self.order_manager.check_api_configuration()
                    if not is_configured and config_issues:
                        config_msg = "API Configuration Issues Detected:\n\n" + "\n".join(config_issues)
                        QMessageBox.warning(self, "API Configuration", config_msg)
                        
            else:
                # Enhanced error message with guidance
                error_msg = f"Order submission failed:\n\n{message}"
                
                # Add configuration guidance for common issues
                if "cancelled" in message.lower() or "confirmation" in message.lower():
                    error_msg += f"""\n\n🔧 Common Solutions:

1. TWS Configuration:
   • File → Global Configuration → API → Settings
   • Enable "Bypass Order Precautions for API Orders"
   • Uncheck "Read-Only API" if checked
   • Restart TWS after changes

2. Check TWS Order Management for any pending confirmations

3. Verify account has sufficient buying power

4. Ensure market is open for {order_data['symbol']}"""
                
                self.show_error(error_msg)
                self.status_bar.showMessage("Order submission failed", 5000)
                
        except Exception as e:
            error_msg = f"Error submitting order: {str(e)}"
            logger.error(error_msg)
            self.show_error(error_msg)
            self.status_bar.showMessage("Order submission error", 5000)
            
    def closeEvent(self, event):
        """Handle application close event"""
        # Disconnect from IB if connected
        if self.ib_manager:
            self.disconnect_from_ib()
            
        # Stop timers
        self.connection_timer.stop()
        
        # Cleanup threaded fetcher
        if self.threaded_fetcher:
            self.threaded_fetcher.cleanup()
        
        # Cleanup market screener
        if self.market_screener:
            self.market_screener.cleanup()
        
        # Cleanup chart widget
        if self.chart_widget:
            self.chart_widget.cleanup()
        
        event.accept()


    def on_fetch_price_chart_update(self, symbol: str):
        """Handle Fetch Price button - update chart only when user explicitly requests"""
        try:
            if self.chart_widget and symbol:
                self.chart_widget.set_symbol(symbol.upper())
                logger.info(f"Chart updated with symbol from Fetch Price: {symbol}")
                
        except Exception as e:
            logger.error(f"Error updating chart from Fetch Price: {str(e)}")
            
    def on_chart_symbol_selected(self, symbol: str):
        """Handle symbol selection from Market Screener - update chart"""
        try:
            if self.chart_widget and symbol:
                self.chart_widget.set_symbol(symbol)
                logger.info(f"Chart updated with symbol from Market Screener: {symbol}")
                
        except Exception as e:
            logger.error(f"Error updating chart from Market Screener: {str(e)}")
            
    def on_chart_price_changed_entry(self, price: float):
        """Handle entry price changed from chart dragging"""
        try:
            if self.order_assistant:
                # Validate price before setting
                price = max(0.0001, min(10000.0, price))
                self.order_assistant.entry_price.setValue(price)
                logger.info(f"Updated Order Assistant entry price from chart: ${price:.2f}")
        except Exception as e:
            logger.error(f"Error updating entry price from chart: {str(e)}")
            
    def on_chart_price_changed_stop_loss(self, price: float):
        """Handle stop loss price changed from chart dragging"""
        try:
            if self.order_assistant:
                self.order_assistant.stop_loss_price.setValue(price)
                logger.info(f"Updated Order Assistant stop loss from chart: ${price:.2f}")
        except Exception as e:
            logger.error(f"Error updating stop loss from chart: {str(e)}")
            
    def on_chart_price_changed_take_profit(self, price: float):
        """Handle take profit price changed from chart dragging"""
        try:
            if self.order_assistant:
                self.order_assistant.take_profit_price.setValue(price)
                # Update R-multiple when dragging chart line (but don't update chart again)
                self.order_assistant.on_take_profit_price_manual_changed(price)
                logger.info(f"Updated Order Assistant take profit from chart: ${price:.2f}")
        except Exception as e:
            logger.error(f"Error updating take profit from chart: {str(e)}")
            
    def on_order_assistant_entry_changed(self, price: float):
        """Handle entry price changed from Order Assistant"""
        try:
            if self.chart_widget and self.order_assistant:
                # Get all current price levels for comprehensive rescaling
                entry = price
                stop_loss = self.order_assistant.stop_loss_price.value()
                take_profit = self.order_assistant.take_profit_price.value()
                self.chart_widget.update_price_levels(entry=entry, stop_loss=stop_loss, take_profit=take_profit, auto_rescale=True)
                logger.info(f"Updated chart entry price from Order Assistant: ${price:.2f}")
        except Exception as e:
            logger.error(f"Error updating chart entry price: {str(e)}")
            
    def on_order_assistant_stop_loss_changed(self, price: float):
        """Handle stop loss changed from Order Assistant"""
        try:
            if self.chart_widget and self.order_assistant:
                # Get all current price levels for comprehensive rescaling
                entry = self.order_assistant.entry_price.value()
                stop_loss = price
                take_profit = self.order_assistant.take_profit_price.value()
                self.chart_widget.update_price_levels(entry=entry, stop_loss=stop_loss, take_profit=take_profit, auto_rescale=True)
                logger.info(f"Updated chart stop loss from Order Assistant: ${price:.2f}")
        except Exception as e:
            logger.error(f"Error updating chart stop loss: {str(e)}")
            
    def on_order_assistant_take_profit_changed(self, price: float):
        """Handle take profit changed from Order Assistant"""
        try:
            if self.chart_widget and self.order_assistant:
                # Get all current price levels for comprehensive rescaling
                entry = self.order_assistant.entry_price.value()
                stop_loss = self.order_assistant.stop_loss_price.value()
                take_profit = price
                self.chart_widget.update_price_levels(entry=entry, stop_loss=stop_loss, take_profit=take_profit, auto_rescale=True)
                logger.info(f"Updated chart take profit from Order Assistant: ${price:.2f}")
        except Exception as e:
            logger.error(f"Error updating chart take profit: {str(e)}")
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle global keyboard events for quick symbol input"""
        try:
            # Get the pressed key as text
            key_text = event.text()
            
            # Check if it's an alphabetic character (A-Z, a-z)
            if key_text and key_text.isalpha():
                # Check if symbol input is already focused
                if self.order_assistant and hasattr(self.order_assistant, 'symbol_input'):
                    symbol_input = self.order_assistant.symbol_input
                    
                    # If symbol input is not focused, focus it and start fresh
                    if not symbol_input.hasFocus():
                        symbol_input.setFocus()
                        symbol_input.clear()
                        symbol_input.insert(key_text.upper())
                        self.status_bar.showMessage(f"Symbol input focused - typing: {key_text.upper()}", 2000)
                        logger.info(f"Global keyboard: Auto-focused symbol input with '{key_text.upper()}'")
                        return
            
            # Check for Enter key to trigger fetch price when symbol is focused
            elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                if (self.order_assistant and hasattr(self.order_assistant, 'symbol_input') and 
                    self.order_assistant.symbol_input.hasFocus()):
                    # Let the symbol input handle the Enter key (already connected to fetch)
                    pass
            
            # For other keys, call parent implementation
            super().keyPressEvent(event)
            
        except Exception as e:
            logger.error(f"Error in global key press handler: {str(e)}")
            super().keyPressEvent(event)
            
    def _apply_smart_stop_adjustment(self, price: float, entry_price: float, direction: str) -> float:
        """Apply smart stop loss adjustment based on stock price and direction"""
        try:
            if direction == 'BUY':
                # For LONG positions, subtract adjustment (stop should be below the low)
                if entry_price >= 1.0:
                    return price - 0.01  # Subtract 1 cent for stocks >= $1
                else:
                    return price - 0.0001  # Subtract 0.01 cent for stocks < $1
            else:
                # For SHORT positions, add adjustment (stop should be above the high)
                if entry_price >= 1.0:
                    return price + 0.01
                else:
                    return price + 0.0001
        except Exception as e:
            logger.error(f"Error applying smart stop adjustment: {str(e)}")
            return price  # Return original price if error


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