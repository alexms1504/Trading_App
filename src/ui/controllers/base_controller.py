"""
Base Controller
Base class for all UI controllers
"""

from typing import Optional, Any
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget, QMessageBox

from src.utils.logger import logger


class BaseController(QObject):
    """Base class for UI controllers"""
    
    # Common signals
    error_occurred = pyqtSignal(str)
    status_update = pyqtSignal(str, int)  # message, duration_ms
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._parent_widget = parent
        self._is_initialized = False
        
    def initialize(self) -> bool:
        """Initialize the controller"""
        try:
            self._is_initialized = True
            logger.info(f"{self.__class__.__name__} initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize {self.__class__.__name__}: {str(e)}")
            return False
            
    def cleanup(self):
        """Cleanup controller resources"""
        try:
            self._is_initialized = False
            logger.info(f"{self.__class__.__name__} cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up {self.__class__.__name__}: {str(e)}")
            
    def show_error(self, message: str, title: str = "Error"):
        """Show error dialog - thread-safe"""
        # Always emit signal first
        self.error_occurred.emit(message)
        
        # Use QTimer.singleShot to ensure dialog is shown on main thread
        if self._parent_widget:
            QTimer.singleShot(0, lambda: self._show_error_dialog(message, title))
    
    def _show_error_dialog(self, message: str, title: str):
        """Internal method to show error dialog on main thread"""
        try:
            if self._parent_widget:
                QMessageBox.critical(self._parent_widget, title, message)
        except Exception as e:
            logger.error(f"Error showing dialog: {e}")
        
    def show_warning(self, message: str, title: str = "Warning"):
        """Show warning dialog - thread-safe"""
        if self._parent_widget:
            QTimer.singleShot(0, lambda: self._show_warning_dialog(message, title))
    
    def _show_warning_dialog(self, message: str, title: str):
        """Internal method to show warning dialog on main thread"""
        try:
            if self._parent_widget:
                QMessageBox.warning(self._parent_widget, title, message)
        except Exception as e:
            logger.error(f"Error showing warning dialog: {e}")
            
    def show_info(self, message: str, title: str = "Information"):
        """Show info dialog - thread-safe"""
        if self._parent_widget:
            QTimer.singleShot(0, lambda: self._show_info_dialog(message, title))
    
    def _show_info_dialog(self, message: str, title: str):
        """Internal method to show info dialog on main thread"""
        try:
            if self._parent_widget:
                QMessageBox.information(self._parent_widget, title, message)
        except Exception as e:
            logger.error(f"Error showing info dialog: {e}")
            
    def update_status(self, message: str, duration_ms: int = 5000):
        """Update status bar"""
        self.status_update.emit(message, duration_ms)
        
    def is_initialized(self) -> bool:
        """Check if controller is initialized"""
        return self._is_initialized