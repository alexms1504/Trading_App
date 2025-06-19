"""
Connection Dialog
UI components for connection management
"""

from typing import Optional, List, Tuple, Callable
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QMessageBox, QComboBox,
    QSpinBox, QLineEdit, QGroupBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from .connection_manager import ConnectionMode
from config import CONNECTION_CONFIG, UI_MESSAGES
from src.utils.logger import logger


class ConnectionDialog(QDialog):
    """Dialog for establishing IB connection"""
    
    # Signals
    connection_requested = pyqtSignal(dict)  # Emits connection parameters
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to Interactive Brokers")
        self.setModal(True)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        
        # Welcome message
        welcome_label = QLabel(UI_MESSAGES['welcome']['title'])
        welcome_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(welcome_label)
        
        info_label = QLabel(UI_MESSAGES['welcome']['subtitle'])
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Trading mode selection
        mode_group = QGroupBox("Trading Mode")
        mode_layout = QVBoxLayout()
        
        self.mode_group = QButtonGroup()
        self.paper_radio = QRadioButton("Paper Trading (Simulated)")
        self.paper_radio.setChecked(True)
        self.live_radio = QRadioButton("Live Trading (Real Money)")
        
        self.mode_group.addButton(self.paper_radio, 0)
        self.mode_group.addButton(self.live_radio, 1)
        
        mode_layout.addWidget(self.paper_radio)
        mode_layout.addWidget(self.live_radio)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Connection settings
        settings_group = QGroupBox("Connection Settings")
        settings_layout = QVBoxLayout()
        
        # Host
        host_layout = QHBoxLayout()
        host_layout.addWidget(QLabel("Host:"))
        self.host_input = QLineEdit(CONNECTION_CONFIG['ib_gateway']['host'])
        host_layout.addWidget(self.host_input)
        settings_layout.addLayout(host_layout)
        
        # Port (auto-updates based on mode)
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_input = QSpinBox()
        self.port_input.setRange(1000, 65535)
        self.port_input.setValue(CONNECTION_CONFIG['ib_gateway']['paper_port'])
        port_layout.addWidget(self.port_input)
        settings_layout.addLayout(port_layout)
        
        # Client ID
        client_layout = QHBoxLayout()
        client_layout.addWidget(QLabel("Client ID:"))
        self.client_id_input = QSpinBox()
        self.client_id_input.setRange(0, 999)
        self.client_id_input.setValue(CONNECTION_CONFIG['ib_gateway']['client_id'])
        client_layout.addWidget(self.client_id_input)
        settings_layout.addLayout(client_layout)
        
        # Advanced settings checkbox
        self.show_advanced = QCheckBox("Show advanced settings")
        self.show_advanced.toggled.connect(self.toggle_advanced_settings)
        settings_layout.addWidget(self.show_advanced)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.connect_button = QPushButton("Connect")
        self.connect_button.setDefault(True)
        self.connect_button.clicked.connect(self.on_connect_clicked)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.connect_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        # Connect mode change to update port
        self.mode_group.buttonClicked.connect(self.on_mode_changed)
        
        # Initially hide advanced settings
        self.host_input.parent().setVisible(False)
        self.client_id_input.parent().setVisible(False)
        
    def on_mode_changed(self):
        """Handle trading mode change"""
        if self.paper_radio.isChecked():
            self.port_input.setValue(CONNECTION_CONFIG['ib_gateway']['paper_port'])
        else:
            self.port_input.setValue(CONNECTION_CONFIG['ib_gateway']['live_port'])
            
    def toggle_advanced_settings(self, checked: bool):
        """Toggle visibility of advanced settings"""
        self.host_input.parent().setVisible(checked)
        self.client_id_input.parent().setVisible(checked)
        
    def on_connect_clicked(self):
        """Handle connect button click"""
        # Gather connection parameters
        params = {
            'mode': ConnectionMode.PAPER if self.paper_radio.isChecked() else ConnectionMode.LIVE,
            'host': self.host_input.text(),
            'port': self.port_input.value(),
            'client_id': self.client_id_input.value()
        }
        
        # Emit signal and close dialog
        self.connection_requested.emit(params)
        self.accept()
        
        
class AccountSelectionDialog(QDialog):
    """Dialog for selecting trading account"""
    
    def __init__(self, accounts: List[Tuple[str, float]], parent=None):
        super().__init__(parent)
        self.accounts = accounts
        self.selected_account = None
        self.setWindowTitle("Select Trading Account")
        self.setModal(True)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        
        # Message
        label = QLabel("Multiple trading accounts found.\nPlease select the account you want to use:")
        layout.addWidget(label)
        
        # Account list
        self.account_combo = QComboBox()
        for account, net_liq in self.accounts:
            self.account_combo.addItem(f"{account} (${net_liq:,.2f})", account)
        layout.addWidget(self.account_combo)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        ok_button = QPushButton("Select")
        ok_button.setDefault(True)
        ok_button.clicked.connect(self.accept)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
    def accept(self):
        """Handle account selection"""
        self.selected_account = self.account_combo.currentData()
        super().accept()
        
        
def show_connection_dialog(parent=None) -> Optional[dict]:
    """Show connection dialog and return connection parameters"""
    dialog = ConnectionDialog(parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        # Get parameters from signal
        params = None
        def capture_params(p):
            nonlocal params
            params = p
        dialog.connection_requested.connect(capture_params)
        return params
    return None
    

def show_account_selection_dialog(accounts: List[Tuple[str, float]], parent=None) -> Optional[str]:
    """Show account selection dialog and return selected account"""
    dialog = AccountSelectionDialog(accounts, parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.selected_account
    return None