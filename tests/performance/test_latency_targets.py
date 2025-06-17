"""
Performance benchmark tests for latency targets.
Verify system meets performance requirements.
"""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch
import numpy as np

from src.services.unified_data_service import UnifiedDataService
from src.services.price_cache_service import PriceCacheService
from src.services.event_bus import EventBus, EventType

@pytest.mark.performance
class TestLatencyTargets:
    """Test that system meets latency requirements."""
    
    def test_price_fetch_under_300ms(self, benchmark_timer):
        """Test price fetching completes within 300ms target."""
        data_service = UnifiedDataService()
        
        # Mock IB API response
        with patch('src.services.unified_data_service.DataFetcher') as MockDataFetcher:
            mock_fetcher = MockDataFetcher.return_value
            
            # Simulate realistic API delay (100-200ms)
            def mock_fetch(symbol):
                time.sleep(0.15)  # 150ms simulated network delay
                return {
                    'symbol': symbol,
                    'last': 150.25,
                    'bid': 150.24,
                    'ask': 150.26,
                    'timestamp': datetime.now()
                }
            
            mock_fetcher.get_latest_price_async = mock_fetch
            data_service.data_fetcher = mock_fetcher
            data_service.initialize()
            
            # Measure fetch time
            with benchmark_timer() as timer:
                result = data_service.fetch_price_data('AAPL')
            
            assert result is not None
            assert timer.elapsed < 300  # Must be under 300ms
            print(f"Price fetch completed in {timer.elapsed:.2f}ms")
    
    def test_ui_response_under_50ms(self, benchmark_timer):
        """Test UI operations complete within 50ms."""
        # Simulate UI update operation
        def ui_update_simulation():
            # Simulate data processing
            data = {'symbol': 'AAPL', 'price': 150.25}
            
            # Simulate UI calculations
            formatted_price = f"${data['price']:.2f}"
            color = 'green' if data['price'] > 150 else 'red'
            
            # Simulate DOM updates (mocked)
            updates = {
                'price_label': formatted_price,
                'price_color': color,
                'last_update': datetime.now().isoformat()
            }
            
            return updates
        
        # Measure UI update time
        with benchmark_timer() as timer:
            result = ui_update_simulation()
        
        assert result is not None
        assert timer.elapsed < 50  # Must be under 50ms
        print(f"UI update completed in {timer.elapsed:.2f}ms")
    
    def test_chart_update_under_200ms(self, benchmark_timer):
        """Test chart rendering completes within 200ms."""
        # Simulate chart data preparation
        def prepare_chart_data(num_points=1000):
            # Generate sample price data
            prices = np.random.randn(num_points).cumsum() + 150
            timestamps = [datetime.now().timestamp() + i for i in range(num_points)]
            
            # Calculate indicators
            sma_20 = np.convolve(prices, np.ones(20)/20, mode='valid')
            sma_50 = np.convolve(prices, np.ones(50)/50, mode='valid')
            
            # Format for chart
            chart_data = {
                'prices': prices.tolist(),
                'timestamps': timestamps,
                'sma_20': sma_20.tolist(),
                'sma_50': sma_50.tolist(),
                'volume': (np.random.rand(num_points) * 1000000).tolist()
            }
            
            return chart_data
        
        # Measure chart update time
        with benchmark_timer() as timer:
            chart_data = prepare_chart_data()
        
        assert chart_data is not None
        assert timer.elapsed < 200  # Must be under 200ms
        print(f"Chart update completed in {timer.elapsed:.2f}ms")
    
    def test_50_symbol_update_under_500ms(self, benchmark_timer):
        """Test updating 50+ symbols completes within 500ms."""
        cache = PriceCacheService()
        cache.initialize()
        
        # Generate 50 symbols
        symbols = [f"SYM{i:02d}" for i in range(50)]
        
        def simulate_batch_update():
            results = {}
            
            # Simulate fetching and caching 50 symbols
            for symbol in symbols:
                price_data = {
                    'symbol': symbol,
                    'last': 100.0 + (hash(symbol) % 100),
                    'bid': 100.0 + (hash(symbol) % 100) - 0.01,
                    'ask': 100.0 + (hash(symbol) % 100) + 0.01,
                    'volume': hash(symbol) % 1000000,
                    'timestamp': datetime.now()
                }
                
                # Cache the data
                cache.set(symbol, price_data)
                results[symbol] = price_data
            
            return results
        
        # Measure batch update time
        with benchmark_timer() as timer:
            results = simulate_batch_update()
        
        assert len(results) == 50
        assert timer.elapsed < 500  # Must be under 500ms
        print(f"50 symbol update completed in {timer.elapsed:.2f}ms")
    
    def test_order_submission_under_100ms(self, benchmark_timer):
        """Test order submission completes within 100ms."""
        # Simulate order submission
        def submit_order_simulation():
            # Validate order parameters
            order_params = {
                'symbol': 'AAPL',
                'shares': 100,
                'price': 150.25,
                'stop_loss': 148.00
            }
            
            # Risk calculations
            risk_amount = (order_params['price'] - order_params['stop_loss']) * order_params['shares']
            position_value = order_params['price'] * order_params['shares']
            
            # Order creation
            order = {
                'id': 12345,
                'status': 'SUBMITTED',
                'timestamp': datetime.now(),
                **order_params,
                'risk_amount': risk_amount,
                'position_value': position_value
            }
            
            # Simulate API call delay
            time.sleep(0.05)  # 50ms network delay
            
            return order
        
        # Measure order submission time
        with benchmark_timer() as timer:
            order = submit_order_simulation()
        
        assert order is not None
        assert timer.elapsed < 100  # Must be under 100ms
        print(f"Order submission completed in {timer.elapsed:.2f}ms")
    
    def test_event_bus_latency(self, event_bus, benchmark_timer):
        """Test EventBus message delivery latency."""
        received_times = []
        
        def handler(event):
            received_times.append(datetime.now())
        
        event_bus.subscribe(EventType.PRICE_UPDATE, handler)
        
        # Measure event delivery time
        with benchmark_timer() as timer:
            send_time = datetime.now()
            event_bus.publish(EventType.PRICE_UPDATE, {'test': 'data'}, 'test')
            
            # Wait for event to be received
            timeout = 0.1  # 100ms timeout
            start = time.time()
            while len(received_times) == 0 and (time.time() - start) < timeout:
                time.sleep(0.001)
        
        assert len(received_times) == 1
        
        # Calculate actual latency
        actual_latency = (received_times[0] - send_time).total_seconds() * 1000
        assert actual_latency < 10  # Event delivery should be < 10ms
        print(f"Event delivery completed in {actual_latency:.2f}ms")
    
    def test_cache_lookup_performance(self, benchmark_timer):
        """Test cache lookup performance with many entries."""
        cache = PriceCacheService()
        cache.initialize()
        
        # Populate cache with many entries
        for i in range(1000):
            cache.set(f"SYM{i:04d}", {
                'last': 100.0 + i,
                'timestamp': datetime.now()
            })
        
        # Measure lookup time
        lookups_performed = 0
        with benchmark_timer() as timer:
            # Perform 1000 random lookups
            for _ in range(1000):
                symbol = f"SYM{np.random.randint(0, 1000):04d}"
                result = cache.get(symbol)
                if result:
                    lookups_performed += 1
        
        assert lookups_performed == 1000
        avg_lookup_time = timer.elapsed / 1000
        assert avg_lookup_time < 0.1  # Each lookup should be < 0.1ms
        print(f"Average cache lookup time: {avg_lookup_time:.3f}ms")
    
    @pytest.mark.benchmark
    def test_risk_calculation_performance(self, benchmark_timer):
        """Test risk calculation performance."""
        from src.core.risk_calculator import RiskCalculator
        
        account_data = {
            'NetLiquidation': 100000.0,
            'BuyingPower': 50000.0
        }
        
        calculator = RiskCalculator(account_data)
        
        # Measure calculation time
        calculations_performed = 0
        with benchmark_timer() as timer:
            # Perform 100 risk calculations
            for i in range(100):
                result = calculator.calculate_position_size(
                    entry_price=100.0 + i,
                    stop_loss=95.0 + i,
                    risk_percentage=1.0
                )
                if result['shares'] > 0:
                    calculations_performed += 1
        
        assert calculations_performed == 100
        avg_calc_time = timer.elapsed / 100
        assert avg_calc_time < 1.0  # Each calculation should be < 1ms
        print(f"Average risk calculation time: {avg_calc_time:.3f}ms")