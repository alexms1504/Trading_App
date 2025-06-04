"""
Unit tests for IB Connection Manager
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.ib_connection import IBConnectionManager, ConnectionState


@pytest.fixture
def ib_manager():
    """Create a fresh IB connection manager instance"""
    # Reset singleton
    IBConnectionManager._instance = None
    IBConnectionManager._initialized = False
    return IBConnectionManager()


@pytest.mark.asyncio
async def test_singleton_pattern():
    """Test that IBConnectionManager follows singleton pattern"""
    manager1 = IBConnectionManager()
    manager2 = IBConnectionManager()
    assert manager1 is manager2


@pytest.mark.asyncio
async def test_initial_state(ib_manager):
    """Test initial state of connection manager"""
    assert ib_manager.connection_state == ConnectionState.DISCONNECTED
    assert not ib_manager.is_connected()
    assert ib_manager.reconnect_attempts == 0


@pytest.mark.asyncio
async def test_event_subscription(ib_manager):
    """Test event subscription mechanism"""
    callback_called = False
    test_data = None
    
    def test_callback(data):
        nonlocal callback_called, test_data
        callback_called = True
        test_data = data
    
    # Subscribe to event
    ib_manager.subscribe_to_event('connection_status', test_callback)
    
    # Trigger event
    ib_manager._notify_connection_status()
    
    assert callback_called
    assert test_data is not None
    assert 'state' in test_data
    assert test_data['state'] == ConnectionState.DISCONNECTED


@pytest.mark.asyncio
async def test_event_unsubscription(ib_manager):
    """Test event unsubscription"""
    callback_count = 0
    
    def test_callback(data):
        nonlocal callback_count
        callback_count += 1
    
    # Subscribe
    ib_manager.subscribe_to_event('error', test_callback)
    ib_manager._notify_error("Test error 1")
    assert callback_count == 1
    
    # Unsubscribe
    ib_manager.unsubscribe_from_event('error', test_callback)
    ib_manager._notify_error("Test error 2")
    assert callback_count == 1  # Should not increase


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
