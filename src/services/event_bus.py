"""
Event Bus
Provides publish-subscribe pattern for decoupled communication between services
"""

from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import threading
import queue

from src.utils.logger import logger


class EventType(Enum):
    """Enumeration of event types"""
    # Connection events
    CONNECTION_STATUS_CHANGED = "connection_status_changed"
    CONNECTION_ERROR = "connection_error"
    
    # Account events
    ACCOUNT_UPDATE = "account_update"
    POSITION_UPDATE = "position_update"
    BUYING_POWER_UPDATE = "buying_power_update"
    
    # Market data events
    PRICE_UPDATE = "price_update"
    MARKET_DATA_ERROR = "market_data_error"
    STOP_LEVELS_UPDATE = "stop_levels_update"
    
    # Order events
    ORDER_SUBMITTED = "order_submitted"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_ERROR = "order_error"
    ORDER_STATUS_UPDATE = "order_status_update"
    
    # UI events
    UI_SYMBOL_SELECTED = "ui_symbol_selected"
    UI_FETCH_REQUESTED = "ui_fetch_requested"
    UI_ORDER_REQUESTED = "ui_order_requested"
    
    # System events
    SERVICE_INITIALIZED = "service_initialized"
    SERVICE_CLEANUP = "service_cleanup"
    APPLICATION_SHUTDOWN = "application_shutdown"


@dataclass
class Event:
    """Event data structure"""
    type: EventType
    data: Dict[str, Any]
    source: str  # Source service/component name
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class EventBus:
    """
    Central event bus for publish-subscribe communication
    Thread-safe implementation
    """
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._lock = threading.RLock()
        self._event_queue = queue.Queue()
        self._running = False
        self._worker_thread = None
        self._event_history: List[Event] = []
        self._max_history_size = 1000
        
    def start(self):
        """Start the event bus worker thread"""
        with self._lock:
            if not self._running:
                self._running = True
                self._worker_thread = threading.Thread(target=self._process_events, daemon=True)
                self._worker_thread.start()
                logger.info("EventBus started")
                
    def stop(self):
        """Stop the event bus worker thread"""
        with self._lock:
            if self._running:
                self._running = False
                self._event_queue.put(None)  # Sentinel to wake up the thread
                if self._worker_thread:
                    self._worker_thread.join(timeout=5)
                logger.info("EventBus stopped")
                
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """
        Subscribe to an event type
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
                
            # Simply store the callback directly
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)
                logger.info(f"Subscribed {callback} to {event_type.value}")
                
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """
        Unsubscribe from an event type
        
        Args:
            event_type: Type of event to unsubscribe from
            callback: Function to remove from subscribers
        """
        with self._lock:
            if event_type in self._subscribers and callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                logger.info(f"Unsubscribed {callback} from {event_type.value}")
                
    def publish(self, event: Event):
        """
        Publish an event
        
        Args:
            event: Event to publish
        """
        if self._running:
            self._event_queue.put(event)
            logger.debug(f"Published event: {event.type.value} from {event.source}")
        else:
            logger.warning(f"EventBus not running, event dropped: {event.type.value}")
            
    def publish_event(self, event_type: EventType, data: Dict[str, Any], source: str):
        """
        Convenience method to publish an event
        
        Args:
            event_type: Type of event
            data: Event data
            source: Source of the event
        """
        event = Event(type=event_type, data=data, source=source)
        self.publish(event)
        
    def _process_events(self):
        """Process events from the queue (runs in worker thread)"""
        while self._running:
            try:
                # Get event from queue with timeout
                event = self._event_queue.get(timeout=1)
                
                if event is None:  # Sentinel value
                    break
                    
                # Process the event
                self._dispatch_event(event)
                
                # Add to history
                self._add_to_history(event)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing event: {str(e)}")
                
    def _dispatch_event(self, event: Event):
        """Dispatch an event to all subscribers"""
        with self._lock:
            subscribers = self._subscribers.get(event.type, []).copy()
            logger.info(f"Dispatching {event.type.value} event to {len(subscribers)} subscribers")
            
        # Dispatch outside the lock to avoid deadlocks
        for callback in subscribers:
            try:
                logger.info(f"Calling subscriber {callback.__name__ if hasattr(callback, '__name__') else str(callback)}")
                callback(event)
                logger.info(f"Successfully called subscriber {callback.__name__ if hasattr(callback, '__name__') else str(callback)}")
            except Exception as e:
                logger.error(f"Error in event subscriber {callback}: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                
    def _add_to_history(self, event: Event):
        """Add event to history for debugging/monitoring"""
        with self._lock:
            self._event_history.append(event)
            
            # Trim history if it gets too large
            if len(self._event_history) > self._max_history_size:
                self._event_history = self._event_history[-self._max_history_size:]
                
    def get_event_history(self, event_type: Optional[EventType] = None, 
                         limit: int = 100) -> List[Event]:
        """
        Get event history
        
        Args:
            event_type: Filter by event type (None for all events)
            limit: Maximum number of events to return
            
        Returns:
            List of events
        """
        with self._lock:
            if event_type:
                filtered = [e for e in self._event_history if e.type == event_type]
                return filtered[-limit:]
            else:
                return self._event_history[-limit:]
                
    def clear_history(self):
        """Clear event history"""
        with self._lock:
            self._event_history.clear()
            
    def get_subscriber_count(self, event_type: Optional[EventType] = None) -> Dict[str, int]:
        """
        Get subscriber counts
        
        Args:
            event_type: Specific event type or None for all
            
        Returns:
            Dictionary of event types to subscriber counts
        """
        with self._lock:
            if event_type:
                subscribers = self._subscribers.get(event_type, [])
                live_count = sum(1 for ref in subscribers if ref() is not None)
                return {event_type.value: live_count}
            else:
                counts = {}
                for evt_type, subscribers in self._subscribers.items():
                    live_count = sum(1 for ref in subscribers if ref() is not None)
                    counts[evt_type.value] = live_count
                return counts


# Global event bus instance
_event_bus = EventBus()


# Convenience functions for global access
def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    return _event_bus


def subscribe(event_type: EventType, callback: Callable[[Event], None]):
    """Subscribe to an event on the global event bus"""
    _event_bus.subscribe(event_type, callback)


def unsubscribe(event_type: EventType, callback: Callable[[Event], None]):
    """Unsubscribe from an event on the global event bus"""
    _event_bus.unsubscribe(event_type, callback)


def publish(event: Event):
    """Publish an event to the global event bus"""
    _event_bus.publish(event)


def publish_event(event_type: EventType, data: Dict[str, Any], source: str):
    """Publish an event to the global event bus (convenience method)"""
    _event_bus.publish_event(event_type, data, source)


def start_event_bus():
    """Start the global event bus"""
    _event_bus.start()


def stop_event_bus():
    """Stop the global event bus"""
    _event_bus.stop()