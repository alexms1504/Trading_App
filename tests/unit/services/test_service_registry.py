"""
Unit tests for ServiceRegistry.
Test lifecycle management and dependency resolution.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import threading

from src.services.service_registry import ServiceRegistry
from src.services.base_service import BaseService

@pytest.mark.unit
class TestServiceRegistry:
    """Test ServiceRegistry functionality."""
    
    def test_singleton_pattern(self):
        """Test that ServiceRegistry is a singleton."""
        registry1 = ServiceRegistry()
        registry2 = ServiceRegistry()
        assert registry1 is registry2
    
    def test_register_service(self, service_registry, mock_service):
        """Test service registration."""
        service_registry.register_service('test_service', mock_service)
        
        # Service should be retrievable
        retrieved = service_registry.get_service('test_service')
        assert retrieved is mock_service
    
    def test_register_duplicate_service(self, service_registry, mock_service):
        """Test registering duplicate service name."""
        service_registry.register_service('test_service', mock_service)
        
        # Create another service
        another_service = Mock(spec=BaseService)
        
        # Should log warning but not raise exception
        service_registry.register_service('test_service', another_service)
        
        # Original service should be replaced
        retrieved = service_registry.get_service('test_service')
        assert retrieved is another_service
    
    def test_get_nonexistent_service(self, service_registry):
        """Test getting non-existent service."""
        result = service_registry.get_service('nonexistent')
        assert result is None
    
    def test_initialize_all_services(self, service_registry):
        """Test initializing all registered services."""
        # Create mock services
        services = []
        for i in range(3):
            service = Mock(spec=BaseService)
            service.initialize.return_value = True
            service.name = f"Service{i}"
            services.append(service)
            service_registry.register_service(f'service_{i}', service)
        
        # Initialize all
        service_registry.initialize_all_services()
        
        # All services should be initialized
        for service in services:
            service.initialize.assert_called_once()
    
    def test_initialize_with_failure(self, service_registry):
        """Test initialization when one service fails."""
        # Create services where middle one fails
        service1 = Mock(spec=BaseService)
        service1.initialize.return_value = True
        service1.name = "Service1"
        
        service2 = Mock(spec=BaseService)
        service2.initialize.return_value = False  # Fails
        service2.name = "Service2"
        
        service3 = Mock(spec=BaseService)
        service3.initialize.return_value = True
        service3.name = "Service3"
        
        service_registry.register_service('service_1', service1)
        service_registry.register_service('service_2', service2)
        service_registry.register_service('service_3', service3)
        
        # Initialize all
        service_registry.initialize_all_services()
        
        # All should be attempted
        service1.initialize.assert_called_once()
        service2.initialize.assert_called_once()
        service3.initialize.assert_called_once()
    
    def test_cleanup_all_services(self, service_registry):
        """Test cleanup of all services."""
        # Create and register services
        services = []
        for i in range(3):
            service = Mock(spec=BaseService)
            service.cleanup = Mock()
            service.name = f"Service{i}"
            services.append(service)
            service_registry.register_service(f'service_{i}', service)
        
        # Cleanup all
        service_registry.cleanup_all_services()
        
        # All services should be cleaned up
        for service in services:
            service.cleanup.assert_called_once()
    
    def test_cleanup_with_exceptions(self, service_registry):
        """Test cleanup continues even if some services raise exceptions."""
        # Create services where one raises exception
        service1 = Mock(spec=BaseService)
        service1.cleanup = Mock()
        service1.name = "Service1"
        
        service2 = Mock(spec=BaseService)
        service2.cleanup = Mock(side_effect=Exception("Cleanup failed"))
        service2.name = "Service2"
        
        service3 = Mock(spec=BaseService)
        service3.cleanup = Mock()
        service3.name = "Service3"
        
        service_registry.register_service('service_1', service1)
        service_registry.register_service('service_2', service2)
        service_registry.register_service('service_3', service3)
        
        # Cleanup should not raise
        service_registry.cleanup_all_services()
        
        # All cleanups should be attempted
        service1.cleanup.assert_called_once()
        service2.cleanup.assert_called_once()
        service3.cleanup.assert_called_once()
    
    def test_get_all_services(self, service_registry):
        """Test getting all registered services."""
        services = {}
        for i in range(3):
            service = Mock(spec=BaseService)
            service.name = f"Service{i}"
            services[f'service_{i}'] = service
            service_registry.register_service(f'service_{i}', service)
        
        all_services = service_registry.get_all_services()
        assert len(all_services) == 3
        assert all_services == services
    
    def test_service_status_reporting(self, service_registry):
        """Test service status reporting."""
        # Create services with different states
        service1 = Mock(spec=BaseService)
        service1.initialize.return_value = True
        service1.is_initialized = True
        service1.name = "Service1"
        
        service2 = Mock(spec=BaseService)
        service2.initialize.return_value = False
        service2.is_initialized = False
        service2.name = "Service2"
        
        service_registry.register_service('service_1', service1)
        service_registry.register_service('service_2', service2)
        
        # Get status
        status = service_registry.get_services_status()
        
        assert 'service_1' in status
        assert 'service_2' in status
        assert status['service_1']['initialized'] is True
        assert status['service_2']['initialized'] is False
    
    def test_thread_safety(self, service_registry):
        """Test thread safety of service registry operations."""
        errors = []
        services_added = []
        
        def register_services(start_idx):
            try:
                for i in range(10):
                    service = Mock(spec=BaseService)
                    service.name = f"Service{start_idx}_{i}"
                    service_name = f'service_{start_idx}_{i}'
                    service_registry.register_service(service_name, service)
                    services_added.append(service_name)
            except Exception as e:
                errors.append(e)
        
        # Run concurrent registrations
        threads = []
        for i in range(5):
            t = threading.Thread(target=register_services, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # No errors should occur
        assert len(errors) == 0
        
        # All services should be registered
        all_services = service_registry.get_all_services()
        assert len(all_services) == 50  # 5 threads * 10 services each
    
    def test_convenience_functions(self, service_registry):
        """Test convenience getter functions."""
        # Mock specific services
        account_service = Mock(spec=BaseService)
        account_service.name = "AccountService"
        
        order_service = Mock(spec=BaseService)
        order_service.name = "OrderService"
        
        risk_service = Mock(spec=BaseService)
        risk_service.name = "RiskService"
        
        service_registry.register_service('account_service', account_service)
        service_registry.register_service('order_service', order_service)
        service_registry.register_service('risk_service', risk_service)
        
        # Test convenience functions
        from src.services.service_registry import (
            get_account_service, get_order_service, get_risk_service
        )
        
        assert get_account_service() is account_service
        assert get_order_service() is order_service
        assert get_risk_service() is risk_service