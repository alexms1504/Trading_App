"""
Status Panel
Status bar and notification area
"""

from typing import Optional
from PyQt6.QtWidgets import QStatusBar, QLabel
from PyQt6.QtCore import QTimer

from src.utils.logger import logger


class StatusPanel(QStatusBar):
    """Enhanced status bar with notification support"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._message_timer = QTimer()
        self._message_timer.timeout.connect(self._clear_temp_message)
        
    def _init_ui(self):
        """Initialize the UI"""
        # Permanent widgets
        self.connection_indicator = QLabel()
        self.addPermanentWidget(self.connection_indicator)
        
        # Set initial message
        self.showMessage("Ready to connect...")
        
    def show_message(self, message: str, duration_ms: int = 0):
        """
        Show a message in the status bar
        
        Args:
            message: Message to display
            duration_ms: Duration in milliseconds (0 = permanent)
        """
        self.showMessage(message)
        
        if duration_ms > 0:
            self._message_timer.stop()
            self._message_timer.start(duration_ms)
            
    def show_error(self, error: str, duration_ms: int = 10000):
        """Show error message with red styling"""
        self.setStyleSheet("QStatusBar { color: red; }")
        self.show_message(f"❌ {error}", duration_ms)
        
    def show_success(self, message: str, duration_ms: int = 5000):
        """Show success message with green styling"""
        self.setStyleSheet("QStatusBar { color: green; }")
        self.show_message(f"✅ {message}", duration_ms)
        
    def show_warning(self, warning: str, duration_ms: int = 7000):
        """Show warning message with orange styling"""
        self.setStyleSheet("QStatusBar { color: orange; }")
        self.show_message(f"⚠️ {warning}", duration_ms)
        
    def update_connection_status(self, connected: bool, mode: Optional[str] = None):
        """Update connection indicator"""
        if connected:
            mode_text = f" ({mode})" if mode else ""
            self.connection_indicator.setText(f"🟢 Connected{mode_text}")
            self.connection_indicator.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.connection_indicator.setText("🔴 Disconnected")
            self.connection_indicator.setStyleSheet("color: red; font-weight: bold;")
            
    def _clear_temp_message(self):
        """Clear temporary message and reset styling"""
        self._message_timer.stop()
        self.setStyleSheet("")  # Reset styling
        self.clearMessage()
        
    def clear(self):
        """Clear all messages"""
        self._message_timer.stop()
        self.clearMessage()
        self.setStyleSheet("")