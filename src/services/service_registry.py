"""
Service Registry
Singleton pattern for service access and lifecycle management
"""

from typing import Dict, Optional, Any, List
import threading

from src.services.base_service import BaseService
from src.services.connection_service import ConnectionService
from src.services.account_service import AccountService
from src.services.order_service import OrderService
from src.utils.logger import logger


class ServiceRegistry:
    """
    Singleton service registry for managing application services
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if self._initialized:
            return
            
        self._services: Dict[str, BaseService] = {}
        self._service_order: List[str] = []  # Order for initialization/cleanup
        self._initialized = True
        logger.info("ServiceRegistry initialized")
        
    def register_service(self, name: str, service: BaseService):
        """
        Register a service
        
        Args:
            name: Service name
            service: Service instance
        """
        if name in self._services:
            logger.warning(f"Service '{name}' already registered, replacing...")
            
        self._services[name] = service
        if name not in self._service_order:
            self._service_order.append(name)
            
        logger.info(f"Registered service: {name}")
        
    def get_service(self, name: str) -> Optional[BaseService]:
        """
        Get a service by name
        
        Args:
            name: Service name
            
        Returns:
            Service instance or None
        """
        service = self._services.get(name)
        if not service:
            logger.error(f"Service '{name}' not found")
        return service
        
    def get_connection_service(self) -> Optional[ConnectionService]:
        """Get the connection service"""
        return self.get_service('connection')
        
    def get_data_service(self) -> Optional[BaseService]:
        """Get the data service"""
        return self.get_service('data')
        
    def get_account_service(self) -> Optional[AccountService]:
        """Get the account service"""
        return self.get_service('account')
        
    def get_order_service(self) -> Optional[OrderService]:
        """Get the order service"""
        return self.get_service('order')
        
    def initialize_all_services(self) -> bool:
        """
        Initialize all registered services in order
        
        Returns:
            True if all services initialized successfully
        """
        logger.info("Initializing all services...")
        
        all_success = True
        initialized_services = []
        
        try:
            for name in self._service_order:
                service = self._services.get(name)
                if service:
                    logger.info(f"Initializing service: {name}")
                    if service.initialize():
                        initialized_services.append(name)
                        logger.info(f"Service '{name}' initialized successfully")
                    else:
                        logger.error(f"Failed to initialize service: {name}")
                        all_success = False
                        break
                        
            if not all_success:
                # Cleanup any services that were initialized
                logger.warning("Some services failed to initialize, cleaning up...")
                for name in reversed(initialized_services):
                    service = self._services.get(name)
                    if service:
                        try:
                            service.cleanup()
                        except Exception as e:
                            logger.error(f"Error cleaning up service '{name}': {str(e)}")
                            
            return all_success
            
        except Exception as e:
            logger.error(f"Error initializing services: {str(e)}")
            return False
            
    def cleanup_all_services(self):
        """Cleanup all services in reverse order"""
        logger.info("Cleaning up all services...")
        
        # Cleanup in reverse order of initialization
        for name in reversed(self._service_order):
            service = self._services.get(name)
            if service:
                try:
                    logger.info(f"Cleaning up service: {name}")
                    service.cleanup()
                    logger.info(f"Service '{name}' cleaned up successfully")
                except Exception as e:
                    logger.error(f"Error cleaning up service '{name}': {str(e)}")
                    
    def get_all_services(self) -> Dict[str, BaseService]:
        """Get all registered services"""
        return self._services.copy()
        
    def is_service_initialized(self, name: str) -> bool:
        """Check if a service is initialized"""
        service = self._services.get(name)
        return service.is_initialized() if service else False
        
    def get_service_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all services"""
        status = {}
        for name, service in self._services.items():
            status[name] = {
                'registered': True,
                'initialized': service.is_initialized() if service else False,
                'class': service.__class__.__name__ if service else 'Unknown'
            }
        return status
        
    def reset(self):
        """Reset the registry (mainly for testing)"""
        self.cleanup_all_services()
        self._services.clear()
        self._service_order.clear()
        logger.info("ServiceRegistry reset")


# Global registry instance
_service_registry = ServiceRegistry()


# Convenience functions for global access
def get_service_registry() -> ServiceRegistry:
    """Get the global service registry instance"""
    return _service_registry


def register_service(name: str, service: BaseService):
    """Register a service in the global registry"""
    _service_registry.register_service(name, service)


def get_service(name: str) -> Optional[BaseService]:
    """Get a service from the global registry"""
    return _service_registry.get_service(name)


def get_connection_service() -> Optional[ConnectionService]:
    """Get the connection service from the global registry"""
    return _service_registry.get_connection_service()


def get_data_service() -> Optional[BaseService]:
    """Get the data service from the global registry"""
    return _service_registry.get_data_service()


def get_account_service() -> Optional[AccountService]:
    """Get the account service from the global registry"""
    return _service_registry.get_account_service()


def get_order_service() -> Optional[OrderService]:
    """Get the order service from the global registry"""
    return _service_registry.get_order_service()


def get_risk_service():
    """Get the risk service from the global registry"""
    from src.services.risk_service import RiskService
    service = _service_registry.get_service('risk')
    return service if isinstance(service, RiskService) else None


def initialize_all_services() -> bool:
    """Initialize all services in the global registry"""
    return _service_registry.initialize_all_services()


def cleanup_all_services():
    """Cleanup all services in the global registry"""
    _service_registry.cleanup_all_services()


def get_service_status() -> Dict[str, Dict[str, Any]]:
    """Get status of all services in the global registry"""
    return _service_registry.get_service_status()