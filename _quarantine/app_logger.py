"""
Application Logger Wrapper
Centralizes logging and status messages for the trading app
"""

import logging
from datetime import datetime
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QStatusBar

from src.utils.logger import logger
from config import APP_CONFIG, STATUS_MSG_DURATION


class AppLogger(QObject):
    """
    Centralized logger that handles both file logging and UI status messages
    """
    
    # Signal for status bar updates (for decoupling)
    status_message = pyqtSignal(str, int)  # message, duration
    
    def __init__(self, status_bar: Optional[QStatusBar] = None):
        super().__init__()
        self.status_bar = status_bar
        self.debug_mode = APP_CONFIG.get('debug', False)
        
        # Connect signal if status bar provided
        if self.status_bar:
            self.status_message.connect(self._update_status_bar)
    
    def set_status_bar(self, status_bar: QStatusBar):
        """Set or update the status bar reference"""
        self.status_bar = status_bar
        if self.status_bar and not self.status_message.receivers():
            self.status_message.connect(self._update_status_bar)
    
    def _update_status_bar(self, message: str, duration: int):
        """Update the status bar with message"""
        if self.status_bar:
            self.status_bar.showMessage(message, duration)
    
    def _format_message(self, message: str, level: str = 'INFO') -> str:
        """Format message with timestamp in debug mode"""
        if self.debug_mode:
            timestamp = datetime.now().strftime('%H:%M:%S')
            return f"[{timestamp}] {level}: {message}"
        return message
    
    # Logging methods that mirror standard logger
    
    def debug(self, message: str, show_status: bool = False):
        """Log debug message"""
        logger.debug(message)
        if show_status and self.debug_mode:
            self.status(f"[DEBUG] {message}", duration='short')
    
    def info(self, message: str, show_status: bool = False, duration: str = 'normal'):
        """Log info message"""
        logger.info(message)
        if show_status:
            self.status(message, duration)
    
    def warning(self, message: str, show_status: bool = True, duration: str = 'normal'):
        """Log warning message"""
        logger.warning(message)
        if show_status:
            self.status(f"Warning - {message}", duration)
    
    def error(self, message: str, show_status: bool = True, duration: str = 'long'):
        """Log error message"""
        logger.error(message)
        if show_status:
            self.status(f"Error - {message}", duration)
    
    def success(self, message: str, show_status: bool = True, duration: str = 'normal'):
        """Log success message (info level with special formatting)"""
        logger.info(f"SUCCESS: {message}")
        if show_status:
            self.status(f"Success - {message}", duration)
    
    # Status bar specific methods
    
    def status(self, message: str, duration: str = 'normal'):
        """
        Show message in status bar
        
        Args:
            message: Message to display
            duration: 'short', 'normal', or 'long' (or milliseconds as int)
        """
        if isinstance(duration, str):
            duration_ms = STATUS_MSG_DURATION.get(duration, STATUS_MSG_DURATION['normal'])
        else:
            duration_ms = duration
            
        formatted_message = self._format_message(message)
        self.status_message.emit(formatted_message, duration_ms)
    
    def status_ready(self):
        """Show ready status"""
        self.status("Ready", duration=0)  # Permanent until overwritten
    
    def status_connecting(self, mode: str):
        """Show connecting status"""
        self.status(f"Connecting to {mode.title()} Trading...", duration='normal')
    
    def status_connected(self, mode: str, account: Optional[str] = None):
        """Show connected status"""
        if account:
            self.status(f"Connected to IB ({mode.upper()}) - Account: {account}", duration='long')
        else:
            self.status(f"Connected to IB ({mode.upper()})", duration='long')
    
    def status_disconnected(self):
        """Show disconnected status"""
        self.status("Disconnected from IB", duration='long')
    
    def status_order_submitted(self, symbol: str, quantity: int, order_type: str):
        """Show order submitted status"""
        self.status(f"Order submitted: {order_type} {quantity} {symbol}", duration='long')
    
    def status_order_filled(self, symbol: str, quantity: int, price: float):
        """Show order filled status"""
        self.status(f"Order filled: {quantity} {symbol} @ ${price:.2f}", duration='long')
    
    def status_price_fetched(self, symbol: str, price: float):
        """Show price fetched status"""
        self.status(f"Price fetched for {symbol}: ${price:.2f}", duration='normal')
    
    def status_symbol_selected(self, symbol: str, source: str = ""):
        """Show symbol selected status"""
        if source:
            self.status(f"Selected {symbol} from {source}", duration='short')
        else:
            self.status(f"Selected {symbol}", duration='short')
    
    # Special formatting methods
    
    def log_startup(self):
        """Log application startup"""
        logger.info("="*60)
        logger.info(f"{APP_CONFIG['name']} v{APP_CONFIG['version']} Starting")
        logger.info(f"Debug Mode: {self.debug_mode}")
        logger.info("="*60)
        self.status_ready()
    
    def log_shutdown(self):
        """Log application shutdown"""
        logger.info("="*60)
        logger.info(f"{APP_CONFIG['name']} Shutting Down")
        logger.info("="*60)


# Global app logger instance
app_logger = AppLogger()