"""
Connection Monitor
Monitors connection health and handles reconnection
"""

from typing import Optional, Callable
from PyQt6.QtCore import QTimer, QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel

from .connection_manager import ConnectionManager, ConnectionState
from src.utils.logger import logger
from config import TIMER_CONFIG


class ConnectionMonitor(QObject):
    """Monitors IB connection health"""
    
    # Signals
    connection_lost = pyqtSignal()
    reconnection_attempted = pyqtSignal(bool)  # Success/failure
    
    def __init__(self, connection_manager: ConnectionManager):
        super().__init__()
        self.connection_manager = connection_manager
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_connection)
        self.last_state = ConnectionState.DISCONNECTED
        
    def start_monitoring(self, interval_ms: int = None):
        """Start monitoring connection"""
        if interval_ms is None:
            interval_ms = TIMER_CONFIG['connection_check_interval']
        self.check_timer.start(interval_ms)
        logger.info(f"Started connection monitoring (interval: {interval_ms}ms)")
        
    def stop_monitoring(self):
        """Stop monitoring connection"""
        self.check_timer.stop()
        logger.info("Stopped connection monitoring")
        
    def check_connection(self):
        """Check connection status"""
        try:
            current_state = self.connection_manager.state
            is_connected = self.connection_manager.is_connected()
            
            # Detect connection loss
            if self.last_state == ConnectionState.CONNECTED and not is_connected:
                logger.warning("Connection lost detected")
                self.connection_lost.emit()
                
            # Update account info if connected
            if is_connected:
                self.connection_manager.update_account_info()
                
            self.last_state = current_state
            
        except Exception as e:
            logger.error(f"Error in connection check: {str(e)}")
            
    def attempt_reconnection(self):
        """Attempt to reconnect using last known settings"""
        try:
            if self.connection_manager.is_connected():
                return True
                
            # Get last connection info
            info = self.connection_manager.get_connection_info()
            mode = self.connection_manager.mode
            
            if mode is None:
                logger.error("No previous connection mode found")
                self.reconnection_attempted.emit(False)
                return False
                
            # Attempt reconnection
            logger.info(f"Attempting reconnection to {mode.value} mode...")
            success = self.connection_manager.connect(mode)
            
            self.reconnection_attempted.emit(success)
            return success
            
        except Exception as e:
            logger.error(f"Reconnection failed: {str(e)}")
            self.reconnection_attempted.emit(False)
            return False
            

class ConnectionStatusWidget(QWidget):
    """Widget displaying connection status"""
    
    def __init__(self, connection_manager: ConnectionManager):
        super().__init__()
        self.connection_manager = connection_manager
        self.init_ui()
        
        # Subscribe to connection state changes
        connection_manager.add_state_callback(self.on_state_changed)
        
    def init_ui(self):
        """Initialize the UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Status indicator
        self.status_label = QLabel("● Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
        layout.addWidget(self.status_label)
        
        # Connection info
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(self.info_label)
        
    def on_state_changed(self, state: ConnectionState, message: str):
        """Handle connection state change"""
        if state == ConnectionState.CONNECTED:
            info = self.connection_manager.get_connection_info()
            mode = info.get('mode', 'UNKNOWN').upper()
            port = info.get('port', 'N/A')
            
            self.status_label.setText(f"● Connected")
            self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
            self.info_label.setText(f"({mode}:{port})")
            
        elif state == ConnectionState.CONNECTING:
            self.status_label.setText("● Connecting...")
            self.status_label.setStyleSheet("color: orange; font-weight: bold; font-size: 14px;")
            self.info_label.setText("")
            
        elif state == ConnectionState.ERROR:
            self.status_label.setText("● Error")
            self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
            self.info_label.setText(f"({message[:30]}...)" if len(message) > 30 else f"({message})")
            
        else:  # DISCONNECTED
            self.status_label.setText("● Disconnected")
            self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
            self.info_label.setText("")