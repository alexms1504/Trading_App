"""
Integration tests for complete order flow.
Test the entire chain from UI request to IB API.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time
from datetime import datetime

from src.services.service_registry import ServiceRegistry
from src.services.event_bus import EventBus, EventType
from src.services.order_service import OrderService
from src.services.risk_service import RiskService
from src.services.account_manager_service import AccountManagerService
from src.services.ib_connection_service import IBConnectionService
from src.core.risk_calculator import RiskCalculator

@pytest.mark.integration
class TestOrderFlow:
    """Test complete order workflow from request to execution."""
    
    def setup_method(self):
        """Set up services for integration testing."""
        self.registry = ServiceRegistry()
        self.event_bus = EventBus()
        self.event_bus.start()
        
        # Track events
        self.events_received = []
        self.event_bus.subscribe(EventType.ORDER_SUBMITTED, 
                               lambda e: self.events_received.append(e))
        self.event_bus.subscribe(EventType.ORDER_STATUS_UPDATE,
                               lambda e: self.events_received.append(e))
    
    def teardown_method(self):
        """Clean up after tests."""
        self.event_bus.stop()
        self.registry.cleanup_all_services()
    
    def test_complete_order_flow_with_risk_validation(self, mock_account_data, mock_ib_connection):
        """Test complete order flow including risk validation."""
        # Set up account service
        account_service = AccountManagerService()
        account_service.update_account_data(mock_account_data)
        self.registry.register_service('account_service', account_service)
        
        # Set up risk service with calculator
        risk_service = RiskService()
        risk_service.set_account_manager(account_service)
        self.registry.register_service('risk_service', risk_service)
        
        # Set up order service
        order_service = OrderService()
        order_service.risk_service = risk_service
        
        # Mock IB connection and order manager
        with patch('src.services.order_service.OrderManager') as MockOrderManager:
            mock_order_manager = MockOrderManager.return_value
            mock_order_manager.place_bracket_order.return_value = {
                'parent_id': 123,
                'stop_id': 124,
                'target_ids': [125, 126]
            }
            
            order_service.order_manager = mock_order_manager
            order_service._initialized = True
            self.registry.register_service('order_service', order_service)
            
            # Initialize all services
            self.registry.initialize_all_services()
            
            # Create order request
            order_params = {
                'symbol': 'AAPL',
                'direction': 'LONG',
                'shares': 100,
                'entry_price': 150.00,
                'stop_loss': 147.50,  # $2.50 risk per share
                'targets': [
                    {'price': 152.50, 'percentage': 50},
                    {'price': 155.00, 'percentage': 50}
                ],
                'order_type': 'LMT',
                'stop_type': 'STP'
            }
            
            # Execute order
            result = order_service.create_order(order_params)
            
            # Verify order was created
            assert result is not None
            assert 'parent_id' in result
            assert result['parent_id'] == 123
            
            # Verify risk validation occurred
            mock_order_manager.place_bracket_order.assert_called_once()
            call_args = mock_order_manager.place_bracket_order.call_args[1]
            assert call_args['shares'] == 100
            assert call_args['entry_price'] == 150.00
            
            # Verify events were published
            time.sleep(0.1)  # Allow event processing
            assert len(self.events_received) > 0
            assert any(e.type == EventType.ORDER_SUBMITTED for e in self.events_received)
    
    def test_order_rejected_when_risk_check_fails(self, mock_account_data):
        """Test that orders are rejected when risk validation fails."""
        # Set up account service with limited buying power
        limited_account_data = {**mock_account_data, 'BuyingPower': 5000.0}
        account_service = AccountManagerService()
        account_service.update_account_data(limited_account_data)
        self.registry.register_service('account_service', account_service)
        
        # Set up risk service
        risk_service = RiskService()
        risk_service.set_account_manager(account_service)
        self.registry.register_service('risk_service', risk_service)
        
        # Set up order service
        order_service = OrderService()
        order_service.risk_service = risk_service
        order_service._initialized = True
        self.registry.register_service('order_service', order_service)
        
        # Initialize all services
        self.registry.initialize_all_services()
        
        # Create order that exceeds buying power
        order_params = {
            'symbol': 'AAPL',
            'direction': 'LONG',
            'shares': 1000,  # $150,000 worth, but only $5,000 buying power
            'entry_price': 150.00,
            'stop_loss': 147.50,
            'order_type': 'LMT',
            'stop_type': 'STP'
        }
        
        # Order should be rejected
        with pytest.raises(ValueError) as exc_info:
            order_service.create_order(order_params)
        
        assert 'risk validation failed' in str(exc_info.value).lower()
    
    def test_bracket_order_parent_child_sequencing(self, mock_account_data):
        """Test correct sequencing of bracket order components."""
        # Set up services
        account_service = AccountManagerService()
        account_service.update_account_data(mock_account_data)
        
        risk_service = RiskService()
        risk_service.set_account_manager(account_service)
        
        order_service = OrderService()
        order_service.risk_service = risk_service
        
        # Track order sequence
        order_sequence = []
        
        def mock_place_order(order):
            order_sequence.append({
                'type': order.orderType,
                'transmit': order.transmit,
                'parent_id': getattr(order, 'parentId', None)
            })
            return order.orderId
        
        # Mock IB connection
        with patch('src.services.order_service.OrderManager') as MockOrderManager:
            mock_order_manager = MockOrderManager.return_value
            mock_order_manager.ib = Mock()
            mock_order_manager.ib.placeOrder = mock_place_order
            
            # Mock order creation
            def create_order_side_effect(order_type, action, total_quantity, **kwargs):
                order = Mock()
                order.orderId = len(order_sequence) + 1
                order.orderType = order_type
                order.action = action
                order.totalQuantity = total_quantity
                order.transmit = kwargs.get('transmit', True)
                order.parentId = kwargs.get('parent_id', None)
                return order
            
            mock_order_manager._create_order = Mock(side_effect=create_order_side_effect)
            
            order_service.order_manager = mock_order_manager
            order_service._initialized = True
            
            # Create bracket order
            order_params = {
                'symbol': 'AAPL',
                'direction': 'LONG',
                'shares': 100,
                'entry_price': 150.00,
                'stop_loss': 147.50,
                'targets': [
                    {'price': 155.00, 'percentage': 100}
                ],
                'order_type': 'LMT',
                'stop_type': 'STP'
            }
            
            # Execute order (this will fail but we can check the sequence)
            try:
                order_service.create_order(order_params)
            except:
                pass  # Expected to fail due to mocking
            
            # Verify sequence
            assert len(order_sequence) >= 2  # At least parent and stop
            
            # Parent should transmit=False (except for last child)
            if len(order_sequence) > 1:
                assert order_sequence[0]['transmit'] == False
            
            # Children should reference parent
            for i in range(1, len(order_sequence)):
                assert order_sequence[i]['parent_id'] is not None
    
    def test_order_modification_validation(self, mock_account_data):
        """Test order modification with validation."""
        # Set up services
        account_service = AccountManagerService()
        account_service.update_account_data(mock_account_data)
        
        risk_service = RiskService()
        risk_service.set_account_manager(account_service)
        
        order_service = OrderService()
        order_service.risk_service = risk_service
        order_service._initialized = True
        
        # Mock existing order
        existing_order = {
            'order_id': 123,
            'symbol': 'AAPL',
            'shares': 100,
            'entry_price': 150.00,
            'stop_loss': 147.50,
            'status': 'SUBMITTED'
        }
        
        # Test modification
        modifications = {
            'stop_loss': 149.00  # Move stop up (valid)
        }
        
        # Modification should be validated
        errors = order_service.validate_order_modification(existing_order, modifications)
        assert len(errors) == 0
        
        # Test invalid modification
        invalid_modifications = {
            'stop_loss': 151.00  # Stop above entry (invalid for long)
        }
        
        errors = order_service.validate_order_modification(existing_order, invalid_modifications)
        assert len(errors) > 0
        assert any('stop loss' in e.lower() for e in errors)
    
    def test_multiple_target_order_flow(self, mock_account_data):
        """Test order flow with multiple profit targets."""
        # Set up services
        account_service = AccountManagerService()
        account_service.update_account_data(mock_account_data)
        
        risk_service = RiskService()
        risk_service.set_account_manager(account_service)
        
        order_service = OrderService()
        order_service.risk_service = risk_service
        
        with patch('src.services.order_service.OrderManager') as MockOrderManager:
            mock_order_manager = MockOrderManager.return_value
            
            # Track created orders
            orders_created = []
            
            def mock_place_bracket_order(**kwargs):
                orders_created.append(kwargs)
                return {
                    'parent_id': 123,
                    'stop_id': 124,
                    'target_ids': [125, 126, 127]
                }
            
            mock_order_manager.place_bracket_order = mock_place_bracket_order
            order_service.order_manager = mock_order_manager
            order_service._initialized = True
            
            # Create order with multiple targets
            order_params = {
                'symbol': 'AAPL',
                'direction': 'LONG',
                'shares': 300,
                'entry_price': 150.00,
                'stop_loss': 147.50,
                'targets': [
                    {'price': 152.50, 'percentage': 33},  # 99 shares
                    {'price': 155.00, 'percentage': 33},  # 99 shares
                    {'price': 157.50, 'percentage': 34}   # 102 shares
                ],
                'order_type': 'LMT',
                'stop_type': 'STP'
            }
            
            result = order_service.create_order(order_params)
            
            # Verify order creation
            assert len(orders_created) == 1
            order = orders_created[0]
            
            # Verify targets
            assert len(order['targets']) == 3
            
            # Verify share allocation
            total_target_shares = sum(t['shares'] for t in order['targets'])
            assert total_target_shares == 300  # All shares allocated
            
            # Verify percentages roughly match
            assert order['targets'][0]['shares'] == 99
            assert order['targets'][1]['shares'] == 99
            assert order['targets'][2]['shares'] == 102