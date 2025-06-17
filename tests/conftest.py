"""
Shared pytest configuration and fixtures for all tests.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock
import asyncio
from datetime import datetime, timedelta
import numpy as np

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import after path setup
from src.services.event_bus import EventBus, EventType
from src.services.service_registry import ServiceRegistry
from src.services.base_service import BaseService

# Configure pytest markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "critical: Critical financial safety tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "performance: Performance benchmarks")
    config.addinivalue_line("markers", "stress: Stress tests")
    config.addinivalue_line("markers", "unit: Unit tests")

# Fixtures for test isolation
@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean environment for each test."""
    # Clear any existing services
    if hasattr(ServiceRegistry, '_instance'):
        ServiceRegistry._instance = None
    
    # Clear event bus
    if hasattr(EventBus, '_instance'):
        EventBus._instance = None
    
    yield
    
    # Cleanup after test
    if hasattr(ServiceRegistry, '_instance') and ServiceRegistry._instance:
        try:
            ServiceRegistry.cleanup_all_services()
        except:
            pass

@pytest.fixture
def event_bus():
    """Provide a fresh EventBus instance."""
    bus = EventBus()
    bus.start()
    yield bus
    bus.stop()

@pytest.fixture
def service_registry():
    """Provide a fresh ServiceRegistry instance."""
    return ServiceRegistry()

@pytest.fixture
def mock_ib_connection():
    """Mock IB connection for testing."""
    mock_conn = MagicMock()
    mock_conn.isConnected.return_value = True
    mock_conn.reqMktData = MagicMock()
    mock_conn.placeOrder = MagicMock()
    mock_conn.cancelOrder = MagicMock()
    return mock_conn

@pytest.fixture
def mock_account_data():
    """Mock account data for testing."""
    return {
        'NetLiquidation': 100000.0,
        'BuyingPower': 50000.0,
        'AvailableFunds': 50000.0,
        'Currency': 'USD',
        'AccountType': 'PAPER',
        'TotalCashValue': 50000.0
    }

@pytest.fixture
def sample_market_data():
    """Provide sample market data for testing."""
    return {
        'AAPL': {
            'symbol': 'AAPL',
            'last': 150.25,
            'bid': 150.24,
            'ask': 150.26,
            'volume': 1000000,
            'timestamp': datetime.now()
        },
        'MSFT': {
            'symbol': 'MSFT',
            'last': 380.50,
            'bid': 380.49,
            'ask': 380.51,
            'volume': 500000,
            'timestamp': datetime.now()
        },
        'TSLA': {
            'symbol': 'TSLA',
            'last': 0.85,  # Penny stock example
            'bid': 0.8499,
            'ask': 0.8501,
            'volume': 2000000,
            'timestamp': datetime.now()
        }
    }

@pytest.fixture
def edge_case_prices():
    """Provide edge case prices for testing."""
    return {
        'zero': 0.0,
        'negative': -1.0,
        'nan': np.nan,
        'inf': np.inf,
        'very_small': 0.0001,
        'very_large': 999999.99,
        'penny_threshold': 0.9999,
        'normal': 50.25
    }

@pytest.fixture
def mock_risk_calculator():
    """Mock risk calculator for testing."""
    calc = MagicMock()
    calc.calculate_position_size.return_value = {
        'shares': 100,
        'position_value': 15025.0,
        'risk_amount': 1000.0,
        'stop_distance': 2.25
    }
    return calc

@pytest.fixture
def sample_order_params():
    """Sample order parameters for testing."""
    return {
        'symbol': 'AAPL',
        'direction': 'LONG',
        'shares': 100,
        'entry_price': 150.25,
        'stop_loss': 148.00,
        'targets': [
            {'price': 152.50, 'percentage': 50},
            {'price': 155.00, 'percentage': 50}
        ],
        'order_type': 'LMT',
        'stop_type': 'STP'
    }

@pytest.fixture
def mock_service():
    """Create a mock service for testing."""
    class MockService(BaseService):
        def __init__(self):
            super().__init__("MockService")
            self.initialized = False
            
        def initialize(self):
            self.initialized = True
            return True
            
        def cleanup(self):
            self.initialized = False
    
    return MockService()

@pytest.fixture
def async_event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# Performance benchmark fixtures
@pytest.fixture
def benchmark_timer():
    """Simple timer for performance measurements."""
    class Timer:
        def __init__(self):
            self.start_time = None
            self.elapsed = None
            
        def __enter__(self):
            self.start_time = datetime.now()
            return self
            
        def __exit__(self, *args):
            self.elapsed = (datetime.now() - self.start_time).total_seconds() * 1000  # ms
    
    return Timer

# Financial safety assertions
class FinancialSafetyAssertions:
    """Custom assertions for financial safety."""
    
    @staticmethod
    def assert_position_size_valid(shares, max_shares=10000):
        """Assert position size is valid."""
        assert shares > 0, "Position size must be greater than 0"
        assert shares <= max_shares, f"Position size {shares} exceeds maximum {max_shares}"
        assert shares == int(shares), "Position size must be a whole number"
    
    @staticmethod
    def assert_price_valid(price, symbol=None):
        """Assert price is valid."""
        assert price is not None, "Price cannot be None"
        assert not np.isnan(price), "Price cannot be NaN"
        assert not np.isinf(price), "Price cannot be infinite"
        assert price > 0, "Price must be positive"
        assert price < 1000000, "Price exceeds reasonable maximum"
    
    @staticmethod
    def assert_risk_within_limits(risk_amount, account_value, max_risk_pct=2.0):
        """Assert risk is within limits."""
        risk_pct = (risk_amount / account_value) * 100
        assert risk_pct <= max_risk_pct, f"Risk {risk_pct:.2f}% exceeds maximum {max_risk_pct}%"
    
    @staticmethod
    def assert_stop_loss_present(order_params):
        """Assert stop loss is present in order."""
        assert 'stop_loss' in order_params, "Stop loss is required for all orders"
        assert order_params['stop_loss'] > 0, "Stop loss must be a positive price"

@pytest.fixture
def safety_assertions():
    """Provide financial safety assertions."""
    return FinancialSafetyAssertions()

# Test data generators
@pytest.fixture
def market_data_generator():
    """Generate realistic market data for testing."""
    def generate(symbol, base_price=100.0, volatility=0.02):
        """Generate market data with random walk."""
        prices = []
        price = base_price
        for _ in range(100):
            change = np.random.normal(0, volatility * price)
            price = max(0.01, price + change)  # Ensure positive
            prices.append({
                'symbol': symbol,
                'last': round(price, 2 if price >= 1 else 4),
                'bid': round(price - 0.01, 2 if price >= 1 else 4),
                'ask': round(price + 0.01, 2 if price >= 1 else 4),
                'volume': np.random.randint(1000, 1000000),
                'timestamp': datetime.now()
            })
        return prices
    
    return generate

# Mock IB API responses
@pytest.fixture
def mock_ib_ticker():
    """Mock IB ticker object."""
    ticker = MagicMock()
    ticker.contract.symbol = 'AAPL'
    ticker.last = 150.25
    ticker.bid = 150.24
    ticker.ask = 150.26
    ticker.volume = 1000000
    ticker.time = datetime.now()
    return ticker

# Environment setup
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    os.environ['TESTING'] = 'true'
    os.environ['IB_CONNECTION_MODE'] = 'paper'
    yield
    # Cleanup not needed as each test gets fresh environment

# Async helpers
@pytest.fixture
def run_async():
    """Helper to run async functions in tests."""
    def _run_async(coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    return _run_async