"""
Integration tests for market data flow.
Test data integrity, validation, and edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from datetime import datetime, timedelta
import time

from src.services.unified_data_service import UnifiedDataService
from src.services.price_cache_service import PriceCacheService
from src.services.event_bus import EventBus, EventType
from src.features.market_data.price_processor import PriceProcessor

@pytest.mark.integration
class TestMarketDataFlow:
    """Test market data flow from IB API to UI."""
    
    def setup_method(self):
        """Set up services for testing."""
        self.event_bus = EventBus()
        self.event_bus.start()
        self.events_received = []
        
        # Subscribe to price updates
        self.event_bus.subscribe(EventType.PRICE_UPDATE,
                               lambda e: self.events_received.append(e))
    
    def teardown_method(self):
        """Clean up after tests."""
        self.event_bus.stop()
    
    @pytest.mark.parametrize("price,should_be_valid", [
        (0, False),
        (-1, False),
        (np.nan, False),
        (np.inf, False),
        (0.0001, True),  # Valid penny stock price
        (999999.99, True),  # Valid high price
        (1000000, False),  # Exceeds maximum
        (150.25, True),  # Normal price
    ])
    def test_price_validation_edge_cases(self, price, should_be_valid):
        """Test price validation for various edge cases."""
        processor = PriceProcessor()
        
        market_data = {
            'symbol': 'TEST',
            'last': price,
            'bid': price - 0.01 if price > 0.01 else 0,
            'ask': price + 0.01 if price < 999999 else price,
            'timestamp': datetime.now()
        }
        
        is_valid = processor.validate_price_data(market_data)
        assert is_valid == should_be_valid
    
    def test_stale_price_detection(self):
        """Test detection of stale price data."""
        processor = PriceProcessor()
        
        # Create stale data (5 minutes old)
        stale_data = {
            'symbol': 'AAPL',
            'last': 150.25,
            'bid': 150.24,
            'ask': 150.26,
            'timestamp': datetime.now() - timedelta(minutes=5)
        }
        
        # Should be marked as stale
        is_stale = processor.is_price_stale(stale_data, max_age_seconds=60)
        assert is_stale is True
        
        # Fresh data
        fresh_data = {**stale_data, 'timestamp': datetime.now()}
        is_stale = processor.is_price_stale(fresh_data, max_age_seconds=60)
        assert is_stale is False
    
    def test_after_hours_price_fallback(self):
        """Test price handling during after-hours when bid/ask unavailable."""
        processor = PriceProcessor()
        
        # After-hours data (no bid/ask)
        after_hours_data = {
            'symbol': 'AAPL',
            'last': 150.25,
            'bid': 0,  # No bid
            'ask': 0,  # No ask
            'close': 150.00,  # Previous close
            'timestamp': datetime.now()
        }
        
        # Process the data
        processed = processor.process_after_hours_price(after_hours_data)
        
        # Should use last price and create synthetic bid/ask
        assert processed['bid'] == 150.24  # last - 0.01
        assert processed['ask'] == 150.26  # last + 0.01
        assert processed['is_after_hours'] is True
    
    def test_penny_stock_precision(self):
        """Test correct decimal precision for penny stocks."""
        processor = PriceProcessor()
        
        # Penny stock (< $1)
        penny_data = {
            'symbol': 'PENNY',
            'last': 0.8567,
            'bid': 0.8566,
            'ask': 0.8568,
            'timestamp': datetime.now()
        }
        
        formatted = processor.format_price(penny_data)
        assert formatted['last'] == "0.8567"  # 4 decimal places
        
        # Regular stock (>= $1)
        regular_data = {
            'symbol': 'REGULAR',
            'last': 150.2567,
            'bid': 150.2466,
            'ask': 150.2668,
            'timestamp': datetime.now()
        }
        
        formatted = processor.format_price(regular_data)
        assert formatted['last'] == "150.26"  # 2 decimal places
    
    def test_cache_behavior_under_load(self):
        """Test price cache behavior under concurrent access."""
        cache = PriceCacheService()
        cache.initialize()
        
        import threading
        errors = []
        
        def cache_operations(symbol_base, thread_id):
            try:
                for i in range(100):
                    symbol = f"{symbol_base}_{thread_id}"
                    price = 100.0 + i
                    
                    # Set price
                    cache.set(symbol, {
                        'last': price,
                        'timestamp': datetime.now()
                    })
                    
                    # Get price
                    cached = cache.get(symbol)
                    assert cached is not None
                    assert cached['last'] == price
                    
                    # Clear occasionally
                    if i % 20 == 0:
                        cache.clear()
            except Exception as e:
                errors.append(e)
        
        # Run concurrent operations
        threads = []
        for i in range(10):
            t = threading.Thread(target=cache_operations, args=('TEST', i))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # No errors should occur
        assert len(errors) == 0
    
    def test_unified_data_service_integration(self, mock_ib_ticker):
        """Test UnifiedDataService integration with all components."""
        # Set up service
        data_service = UnifiedDataService()
        
        # Mock IB connection
        with patch('src.services.unified_data_service.get_ib_connection_service') as mock_get_ib:
            mock_ib_service = Mock()
            mock_ib_service.ib = Mock()
            mock_ib_service.ib.reqMktData.return_value = mock_ib_ticker
            mock_get_ib.return_value = mock_ib_service
            
            # Mock data fetcher
            with patch('src.services.unified_data_service.DataFetcher') as MockDataFetcher:
                mock_fetcher = MockDataFetcher.return_value
                mock_fetcher.get_latest_price_async.return_value = {
                    'symbol': 'AAPL',
                    'last': 150.25,
                    'bid': 150.24,
                    'ask': 150.26,
                    'volume': 1000000,
                    'timestamp': datetime.now()
                }
                
                data_service.data_fetcher = mock_fetcher
                data_service.initialize()
                
                # Fetch price data
                result = data_service.fetch_price_data('AAPL')
                
                # Verify result
                assert result is not None
                assert result['symbol'] == 'AAPL'
                assert result['last'] == 150.25
                
                # Verify event published
                time.sleep(0.1)
                assert len(self.events_received) > 0
                price_events = [e for e in self.events_received 
                              if e.type == EventType.PRICE_UPDATE]
                assert len(price_events) > 0
                assert price_events[0].data['symbol'] == 'AAPL'
    
    def test_smart_stop_calculation(self):
        """Test smart stop loss calculation based on market conditions."""
        processor = PriceProcessor()
        
        # Normal stock with normal volatility
        normal_result = processor.calculate_smart_stop(
            entry_price=150.00,
            direction='LONG',
            atr=2.5,  # Average True Range
            support_levels=[148.00, 145.00, 142.00]
        )
        
        # Should place stop below nearest support
        assert normal_result['stop_price'] < 148.00
        assert normal_result['stop_distance'] > 2.0  # Reasonable distance
        
        # Penny stock (high volatility)
        penny_result = processor.calculate_smart_stop(
            entry_price=0.85,
            direction='LONG',
            atr=0.05,
            support_levels=[0.80, 0.75, 0.70]
        )
        
        # Should have wider stop for penny stock
        assert penny_result['stop_distance_pct'] > 5.0  # At least 5%
    
    def test_bid_ask_spread_validation(self):
        """Test validation of bid-ask spreads."""
        processor = PriceProcessor()
        
        # Normal spread
        normal_spread = processor.validate_spread({
            'symbol': 'AAPL',
            'bid': 150.24,
            'ask': 150.26,
            'last': 150.25
        })
        assert normal_spread['valid'] is True
        assert normal_spread['spread'] == 0.02
        assert normal_spread['spread_pct'] < 0.1  # Less than 0.1%
        
        # Wide spread (suspicious)
        wide_spread = processor.validate_spread({
            'symbol': 'ILLIQUID',
            'bid': 100.00,
            'ask': 105.00,
            'last': 102.50
        })
        assert wide_spread['valid'] is False
        assert wide_spread['spread_pct'] > 4.0  # More than 4%
        assert 'wide spread' in wide_spread['reason'].lower()
    
    def test_multi_symbol_concurrent_updates(self):
        """Test handling concurrent updates for multiple symbols."""
        data_service = UnifiedDataService()
        
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        update_count = {symbol: 0 for symbol in symbols}
        
        # Subscribe to updates
        def count_updates(event):
            if event.data['symbol'] in update_count:
                update_count[event.data['symbol']] += 1
        
        self.event_bus.subscribe(EventType.PRICE_UPDATE, count_updates)
        
        # Mock price updates
        with patch.object(data_service, 'fetch_price_data') as mock_fetch:
            def mock_price_data(symbol):
                return {
                    'symbol': symbol,
                    'last': 100.0 + hash(symbol) % 100,
                    'timestamp': datetime.now()
                }
            
            mock_fetch.side_effect = mock_price_data
            data_service.initialize()
            
            # Simulate concurrent updates
            import threading
            
            def update_symbol(symbol):
                for _ in range(10):
                    data_service.fetch_price_data(symbol)
                    time.sleep(0.01)
            
            threads = []
            for symbol in symbols:
                t = threading.Thread(target=update_symbol, args=(symbol,))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            
            # Each symbol should have received updates
            time.sleep(0.2)
            for symbol in symbols:
                assert update_count[symbol] >= 5  # At least some updates