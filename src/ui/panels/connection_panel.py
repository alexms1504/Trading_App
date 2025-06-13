"""
Connection Panel
Top panel for connection controls and account information
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, 
    QRadioButton, QButtonGroup, QComboBox
)
from PyQt6.QtCore import pyqtSignal

from src.utils.logger import logger
import config


class ConnectionPanel(QWidget):
    """Panel for connection and account controls"""
    
    # Signals
    connect_requested = pyqtSignal()
    disconnect_requested = pyqtSignal()
    mode_changed = pyqtSignal(str)  # 'paper' or 'live'
    account_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
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
        self.trading_mode_group.buttonClicked.connect(self._on_mode_changed)
        
        # Connection controls
        self.connect_button = QPushButton("Connect to IB")
        self.connect_button.clicked.connect(self.connect_requested.emit)
        self.connect_button.setMaximumWidth(config.WINDOW_CONFIG['widget_widths']['connect_button_max'])
        
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_requested.emit)
        self.disconnect_button.setMaximumWidth(config.WINDOW_CONFIG['widget_widths']['disconnect_button_max'])
        self.disconnect_button.setEnabled(False)
        
        # Connection status indicator
        self.connection_status_label = QLabel("● Disconnected")
        self.connection_status_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
        
        # Account selector
        account_label = QLabel("Account:")
        self.account_selector = QComboBox()
        self.account_selector.setMinimumWidth(150)
        self.account_selector.setEnabled(False)
        self.account_selector.currentTextChanged.connect(self._on_account_changed)
        
        # Account info display
        self.account_value_label = QLabel("Value: N/A")
        self.account_value_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        # Add widgets to layout
        layout.addWidget(trading_mode_label)
        layout.addWidget(self.paper_radio)
        layout.addWidget(self.live_radio)
        layout.addWidget(QLabel("|"))  # Separator
        layout.addWidget(self.connect_button)
        layout.addWidget(self.disconnect_button)
        layout.addWidget(self.connection_status_label)
        layout.addWidget(QLabel("|"))  # Separator
        layout.addWidget(account_label)
        layout.addWidget(self.account_selector)
        layout.addWidget(QLabel("|"))  # Separator
        layout.addWidget(self.account_value_label)
        layout.addStretch()  # Push everything to the left
        
        # Style the panel
        self.setStyleSheet("""
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
        
    def _on_mode_changed(self):
        """Handle mode radio button change"""
        mode = 'paper' if self.paper_radio.isChecked() else 'live'
        self.mode_changed.emit(mode)
        
    def _on_account_changed(self, account: str):
        """Handle account selection change"""
        if account:
            self.account_changed.emit(account)
            
    def update_connection_status(self, connected: bool, info: dict = None):
        """Update connection status display"""
        if connected:
            # Get connection info
            mode = info.get('mode', 'UNKNOWN') if info else 'UNKNOWN'
            port = info.get('port', 'N/A') if info else 'N/A'
            
            self.connection_status_label.setText(f"● Connected ({mode}:{port})")
            self.connection_status_label.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.account_selector.setEnabled(True)
            
            # Update account selector if needed
            if info:
                accounts = info.get('accounts', [])
                if accounts and self.account_selector.count() == 0:
                    self.account_selector.addItems(accounts)
                    if info.get('account'):
                        self.account_selector.setCurrentText(info['account'])
                        
            # Disable trading mode selection when connected
            self.paper_radio.setEnabled(False)
            self.live_radio.setEnabled(False)
        else:
            self.connection_status_label.setText("● Disconnected")
            self.connection_status_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)
            self.account_selector.setEnabled(False)
            self.account_selector.clear()
            self.account_value_label.setText("NLV: N/A | BP: N/A")
            
            # Enable trading mode selection when disconnected
            self.paper_radio.setEnabled(True)
            self.live_radio.setEnabled(True)
            
    def update_account_info(self, net_liq: float, buying_power: float):
        """Update account information display"""
        self.account_value_label.setText(
            f"NLV: ${net_liq:,.2f} | BP: ${buying_power:,.2f}"
        )
        
    def set_selected_account(self, account: str):
        """Set the selected account"""
        index = self.account_selector.findText(account)
        if index >= 0:
            self.account_selector.setCurrentIndex(index)
            
    def set_trading_mode(self, mode: str):
        """Set trading mode radio button"""
        if mode == 'paper':
            self.paper_radio.setChecked(True)
        else:
            self.live_radio.setChecked(True)