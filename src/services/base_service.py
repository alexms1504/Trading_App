"""
Base Service Class
Common interface and functionality for all services
"""

import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from enum import Enum

# Try to import app_logger, fall back to simple logger for testing
try:
    from src.utils.app_logger import app_logger
except ImportError:
    from src.utils.simple_logger import simple_logger as app_logger


class ServiceState(Enum):
    """Service lifecycle states"""
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    CLEANING_UP = "cleaning_up"
    STOPPED = "stopped"


class BaseService:
    """
    Base class for all services
    Provides common functionality like lifecycle management, logging, and error handling
    """
    
    def __init__(self, name: str):
        """
        Initialize base service
        
        Args:
            name: Service name for logging and identification
        """
        self.name = name
        self.state = ServiceState.CREATED
        self._initialized = False
        self._error_handlers: Dict[str, Callable] = {}
        self._state_listeners: list[Callable] = []
        self._start_time: Optional[datetime] = None
        
        app_logger.debug(f"Service created: {self.name}")
        
    def initialize(self) -> bool:
        """
        Initialize service resources
        
        Returns:
            True if initialization successful
        """
        try:
            app_logger.info(f"Initializing service: {self.name}")
            self._set_state(ServiceState.INITIALIZING)
            self._start_time = datetime.now()
            
            # Derived classes implement specific initialization
            # If we get here without error, mark as ready
            self._set_state(ServiceState.READY)
            app_logger.info(f"Service ready: {self.name}")
            return True
            
        except Exception as e:
            self._handle_error(e, "Failed to initialize service")
            return False
            
    def cleanup(self) -> bool:
        """
        Cleanup service resources
        
        Returns:
            True if cleanup successful
        """
        try:
            app_logger.info(f"Cleaning up service: {self.name}")
            self._set_state(ServiceState.CLEANING_UP)
            
            # Derived classes implement specific cleanup
            # If we get here without error, mark as stopped
            self._set_state(ServiceState.STOPPED)
            app_logger.info(f"Service stopped: {self.name}")
            return True
            
        except Exception as e:
            self._handle_error(e, "Failed to cleanup service")
            return False
            
    def is_ready(self) -> bool:
        """Check if service is ready for use"""
        return self.state == ServiceState.READY
        
    def get_state(self) -> ServiceState:
        """Get current service state"""
        return self.state
        
    def get_uptime(self) -> Optional[float]:
        """Get service uptime in seconds"""
        if self._start_time and self.state == ServiceState.READY:
            return (datetime.now() - self._start_time).total_seconds()
        return None
        
    def add_state_listener(self, callback: Callable[[ServiceState], None]):
        """Add listener for state changes"""
        self._state_listeners.append(callback)
        
    def remove_state_listener(self, callback: Callable[[ServiceState], None]):
        """Remove state change listener"""
        if callback in self._state_listeners:
            self._state_listeners.remove(callback)
            
    def add_error_handler(self, error_type: str, handler: Callable[[Exception], None]):
        """Add custom error handler for specific error types"""
        self._error_handlers[error_type] = handler
        
    def _set_state(self, new_state: ServiceState):
        """Update service state and notify listeners"""
        old_state = self.state
        self.state = new_state
        
        if old_state != new_state:
            app_logger.debug(f"{self.name} state changed: {old_state.value} -> {new_state.value}")
            
            # Notify listeners
            for listener in self._state_listeners:
                try:
                    listener(new_state)
                except Exception as e:
                    app_logger.error(f"Error in state listener: {e}")
                    
    def _handle_error(self, error: Exception, context: str = ""):
        """
        Handle errors with logging and optional custom handlers
        
        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
        """
        self._set_state(ServiceState.ERROR)
        
        error_type = type(error).__name__
        error_msg = f"{self.name} error"
        if context:
            error_msg += f" ({context})"
        error_msg += f": {error_type}: {str(error)}"
        
        app_logger.error(error_msg)
        
        # Check for custom error handler
        if error_type in self._error_handlers:
            try:
                self._error_handlers[error_type](error)
            except Exception as handler_error:
                app_logger.error(f"Error in custom error handler: {handler_error}")
                
    def _wrap_method(self, method: Callable, method_name: str) -> Callable:
        """
        Wrap a method with error handling
        
        Args:
            method: Method to wrap
            method_name: Name for logging
            
        Returns:
            Wrapped method
        """
        def wrapped(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except Exception as e:
                self._handle_error(e, f"in {method_name}")
                raise
                
        return wrapped
        
    def get_status(self) -> Dict[str, Any]:
        """
        Get service status information
        
        Returns:
            Dictionary with status information
        """
        return {
            'name': self.name,
            'state': self.state.value,
            'ready': self.is_ready(),
            'uptime': self.get_uptime(),
            'start_time': self._start_time.isoformat() if self._start_time else None
        }
        
    def is_initialized(self) -> bool:
        """Check if service is initialized"""
        return self._initialized and self.state == ServiceState.READY
        
    def _check_initialized(self) -> bool:
        """Check if service is initialized and log error if not"""
        if not self.is_initialized():
            app_logger.error(f"{self.name} not initialized")
            return False
        return True