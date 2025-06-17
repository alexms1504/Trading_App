"""
Unit tests for EventBus service.
Test thread safety, event delivery, and error isolation.
"""

import pytest
from unittest.mock import Mock, patch
import threading
import time
from queue import Queue

from src.services.event_bus import EventBus, EventType, Event

@pytest.mark.unit
class TestEventBus:
    """Test EventBus functionality."""
    
    def test_singleton_pattern(self):
        """Test that EventBus is a singleton."""
        bus1 = EventBus()
        bus2 = EventBus()
        assert bus1 is bus2
    
    def test_subscribe_and_publish(self, event_bus):
        """Test basic subscribe and publish functionality."""
        received_events = []
        
        def handler(event):
            received_events.append(event)
        
        # Subscribe to event
        event_bus.subscribe(EventType.PRICE_UPDATE, handler)
        
        # Publish event
        test_data = {'symbol': 'AAPL', 'price': 150.0}
        event_bus.publish(EventType.PRICE_UPDATE, test_data, 'test_source')
        
        # Wait for event processing
        time.sleep(0.1)
        
        assert len(received_events) == 1
        assert received_events[0].type == EventType.PRICE_UPDATE
        assert received_events[0].data == test_data
        assert received_events[0].source == 'test_source'
    
    def test_unsubscribe(self, event_bus):
        """Test unsubscribe functionality."""
        call_count = 0
        
        def handler(event):
            nonlocal call_count
            call_count += 1
        
        # Subscribe
        event_bus.subscribe(EventType.ORDER_SUBMITTED, handler)
        
        # Publish first event
        event_bus.publish(EventType.ORDER_SUBMITTED, {}, 'test')
        time.sleep(0.1)
        assert call_count == 1
        
        # Unsubscribe
        event_bus.unsubscribe(EventType.ORDER_SUBMITTED, handler)
        
        # Publish second event
        event_bus.publish(EventType.ORDER_SUBMITTED, {}, 'test')
        time.sleep(0.1)
        assert call_count == 1  # Should not increase
    
    def test_subscriber_exception_isolation(self, event_bus):
        """Test that exceptions in one subscriber don't affect others."""
        results = []
        
        def bad_handler(event):
            results.append('bad_handler')
            raise ValueError("Test exception")
        
        def good_handler(event):
            results.append('good_handler')
        
        # Subscribe both handlers
        event_bus.subscribe(EventType.CONNECTION_ERROR, bad_handler)
        event_bus.subscribe(EventType.CONNECTION_ERROR, good_handler)
        
        # Publish event
        event_bus.publish(EventType.CONNECTION_ERROR, {}, 'test')
        time.sleep(0.1)
        
        # Both handlers should have been called
        assert 'bad_handler' in results
        assert 'good_handler' in results
    
    def test_event_history(self, event_bus):
        """Test event history functionality."""
        # Publish multiple events
        for i in range(5):
            event_bus.publish(EventType.ACCOUNT_UPDATE, {'index': i}, 'test')
        
        time.sleep(0.1)
        
        # Get event history
        history = event_bus.get_event_history()
        assert len(history) >= 5
        
        # Check events are in order
        account_events = [e for e in history if e.type == EventType.ACCOUNT_UPDATE]
        assert len(account_events) == 5
        for i, event in enumerate(account_events):
            assert event.data['index'] == i
    
    def test_event_history_max_size(self, event_bus):
        """Test that event history respects max size."""
        # Publish many events (more than max history size of 1000)
        for i in range(1500):
            event_bus.publish(EventType.PRICE_UPDATE, {'index': i}, 'test')
        
        time.sleep(0.5)
        
        # History should be capped
        history = event_bus.get_event_history()
        assert len(history) <= 1000
        
        # Should contain the most recent events
        indices = [e.data['index'] for e in history if e.type == EventType.PRICE_UPDATE]
        assert max(indices) >= 1400  # Recent events preserved
    
    def test_stop_with_pending_events(self, event_bus):
        """Test graceful shutdown with pending events."""
        processed = []
        
        def slow_handler(event):
            time.sleep(0.05)  # Simulate slow processing
            processed.append(event.data['id'])
        
        event_bus.subscribe(EventType.ORDER_FILLED, slow_handler)
        
        # Publish multiple events quickly
        for i in range(10):
            event_bus.publish(EventType.ORDER_FILLED, {'id': i}, 'test')
        
        # Stop immediately
        event_bus.stop()
        
        # Some events should have been processed
        assert len(processed) > 0
        # But probably not all due to timeout
        assert len(processed) <= 10
    
    def test_concurrent_subscribe_unsubscribe(self, event_bus):
        """Test thread safety of subscribe/unsubscribe operations."""
        handlers = []
        errors = []
        
        def create_handler(idx):
            def handler(event):
                pass
            handler.idx = idx
            return handler
        
        def subscriber_thread(idx):
            try:
                handler = create_handler(idx)
                handlers.append(handler)
                
                # Rapidly subscribe and unsubscribe
                for _ in range(100):
                    event_bus.subscribe(EventType.PRICE_UPDATE, handler)
                    event_bus.unsubscribe(EventType.PRICE_UPDATE, handler)
            except Exception as e:
                errors.append(e)
        
        # Run concurrent operations
        threads = [threading.Thread(target=subscriber_thread, args=(i,)) 
                  for i in range(10)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # No errors should occur
        assert len(errors) == 0
    
    def test_publish_when_stopped(self):
        """Test publishing events when EventBus is stopped."""
        bus = EventBus()
        # Don't start the bus
        
        received = []
        bus.subscribe(EventType.PRICE_UPDATE, lambda e: received.append(e))
        
        # Publish should not raise exception
        bus.publish(EventType.PRICE_UPDATE, {'test': 'data'}, 'test')
        
        # But event should not be processed
        time.sleep(0.1)
        assert len(received) == 0
    
    def test_event_type_filtering(self, event_bus):
        """Test that handlers only receive subscribed event types."""
        price_events = []
        order_events = []
        
        event_bus.subscribe(EventType.PRICE_UPDATE, 
                          lambda e: price_events.append(e))
        event_bus.subscribe(EventType.ORDER_SUBMITTED, 
                          lambda e: order_events.append(e))
        
        # Publish different event types
        event_bus.publish(EventType.PRICE_UPDATE, {'price': 100}, 'test')
        event_bus.publish(EventType.ORDER_SUBMITTED, {'order': 123}, 'test')
        event_bus.publish(EventType.CONNECTION_ERROR, {'error': 'test'}, 'test')
        
        time.sleep(0.1)
        
        assert len(price_events) == 1
        assert len(order_events) == 1
        # Connection error should not be received by either
    
    @pytest.mark.performance
    def test_event_processing_performance(self, event_bus, benchmark_timer):
        """Test event processing performance."""
        received_count = 0
        
        def handler(event):
            nonlocal received_count
            received_count += 1
        
        event_bus.subscribe(EventType.PRICE_UPDATE, handler)
        
        # Measure time to process many events
        with benchmark_timer() as timer:
            for i in range(1000):
                event_bus.publish(EventType.PRICE_UPDATE, {'i': i}, 'test')
            
            # Wait for all events to be processed
            while received_count < 1000 and timer.elapsed < 5000:
                time.sleep(0.01)
        
        assert received_count == 1000
        assert timer.elapsed < 1000  # Should process 1000 events in < 1 second