# EventBus Removal & Architecture Simplification Plan

## Executive Summary

This document outlines the pragmatic approach to removing EventBus and simplifying the architecture for the trading application. The focus is on **actual simplification** rather than replacing one complex system with another.

**Key Decision**: Remove EventBus entirely and use direct Qt signal connections between services and UI components.

## Current State Analysis

### EventBus Usage Statistics
- **17 event types defined**, only **2 actively used** (11% utilization)
- **1 publisher**: UnifiedDataService
- **1 subscriber**: MarketDataController  
- **Single flow**: Price updates from data service to UI controller
- **283 lines of code** for minimal benefit

### Why Remove EventBus?
1. **Over-engineered** for a single-user application
2. **Underutilized** - 89% of defined events unused
3. **Performance overhead** - Threading and queue processing
4. **Complexity without benefit** - Direct connections are simpler

## Architecture Philosophy

### Core Principles
1. **Services own their signals** - No global state or singletons
2. **Direct connections** - Controllers connect directly to service signals
3. **Explicit dependencies** - Constructor injection, no dynamic lookups
4. **Measure, don't assume** - Performance claims backed by data
5. **Simplicity first** - Remove abstractions that don't add value

### What We're NOT Doing
- ❌ Creating SignalHub (just EventBus with different syntax)
- ❌ Adding more abstraction layers
- ❌ Global singleton patterns
- ❌ Complex batching before measuring need

## Implementation Plan

### Phase 1: Remove EventBus with Minimal Changes (2 days)

#### Step 1: Use Existing Service Signals
```python
# UnifiedDataService already has Qt signals!
class UnifiedDataService(BaseService, QObject):
    fetch_completed = pyqtSignal(dict)  # Already exists
    
    def _on_price_data_processed(self, symbol: str, price_data: dict):
        # OLD: EventBus
        # publish_event(EventType.PRICE_UPDATE, price_data)
        
        # NEW: Use existing signal
        self.fetch_completed.emit(price_data)
```

#### Step 2: Direct Controller Connections
```python
class MarketDataController(BaseController):
    def initialize(self):
        # Get service reference
        self._data_service = get_data_service()
        
        # OLD: EventBus subscription
        # subscribe(EventType.PRICE_UPDATE, self._on_price_update)
        
        # NEW: Direct connection
        self._data_service.fetch_completed.connect(self._on_price_update_direct)
```

#### Step 3: Clean Up
- Remove all EventBus imports
- Delete event_bus.py (283 lines)
- Delete EventType enum
- Remove from ServiceRegistry

### Phase 2: Simplify Service Dependencies (2 days)

#### Current Problem: Circular Dependencies
```python
# BAD: Dynamic lookup creating circular dependency
def _ensure_risk_calculator(self):
    from src.services import get_account_service  # Import inside method!
    account_service = get_account_service()
```

#### Solution: Constructor Injection
```python
# GOOD: Explicit dependency injection
class RiskService(BaseService):
    def __init__(self, account_service: AccountService):
        super().__init__("RiskService")
        self.account_service = account_service  # Explicit dependency
```

#### MainWindow Service Creation
```python
def _init_services(self):
    # Create in dependency order with explicit wiring
    self.ib_connection = IBConnectionService()
    self.account_service = AccountService(self.ib_connection)
    self.risk_service = RiskService(self.account_service)
    self.order_service = OrderService(self.ib_connection, self.risk_service)
    self.data_service = UnifiedDataService(self.ib_connection)
```

### Phase 3: Add Missing Critical Signals (3 days)

#### Service-Owned Signals Pattern
```python
class OrderService(BaseService, QObject):
    # Service owns its communication contract
    order_submitted = pyqtSignal(dict)
    order_filled = pyqtSignal(dict)
    order_failed = pyqtSignal(dict, str)
    
    def place_order(self, order_request: dict):
        try:
            # Validate with risk service
            if not self.risk_service.validate_trade(order_request):
                self.order_failed.emit(order_request, "Risk validation failed")
                return False
                
            # Place order
            order_id = self._execute_order(order_request)
            self.order_submitted.emit({**order_request, 'order_id': order_id})
            return True
            
        except Exception as e:
            self.order_failed.emit(order_request, str(e))
            return False
```

### Phase 4: Multi-Symbol Streaming Design (4 days)

#### Performance-First Approach
```python
class MultiSymbolStreaming(QObject):
    """Direct IB API streaming for multiple symbols."""
    
    # Individual and batch signals
    price_updated = pyqtSignal(str, dict)
    batch_updated = pyqtSignal(dict)
    
    def __init__(self, ib_connection):
        super().__init__()
        self.ib = ib_connection.ib
        self.active_tickers = {}
        
        # Batch timer for UI efficiency
        self.batch_timer = QTimer()
        self.batch_timer.timeout.connect(self._emit_batch)
        self.batch_timer.setInterval(50)  # 20 FPS
```

### Phase 5: Remove ServiceRegistry (2 days)

#### From Complex DI to Simple Management
```python
# OLD: 233 lines of complex dependency injection
ServiceRegistry.register_service('data', service)
ServiceRegistry.initialize_all_services()

# NEW: Simple and explicit
class ServiceManager:
    def __init__(self):
        self.services = {}
    
    def add(self, name: str, service):
        self.services[name] = service
    
    def cleanup_all(self):
        for service in reversed(self.services.values()):
            if hasattr(service, 'cleanup'):
                service.cleanup()
```

## Performance Measurement Strategy

### Don't Guess, Measure
```python
class PerformanceMonitor:
    def measure(self, operation: str):
        """Context manager for timing."""
        class Timer:
            def __enter__(self):
                self.start = time.perf_counter()
            def __exit__(self, *args):
                elapsed = (time.perf_counter() - self.start) * 1000
                if elapsed > 100:  # Log slow operations
                    logger.warning(f"{operation}: {elapsed:.1f}ms")
        return Timer()

# Usage
with perf.measure("price_update"):
    service.fetch_price_data(symbol)
```

## Migration Safety

### Parallel Operation During Transition
```python
# Temporary feature flag
USE_EVENTBUS = False  # Easy rollback

if USE_EVENTBUS:
    publish_event(EventType.PRICE_UPDATE, data)
else:
    self.price_updated.emit(data)
```

### Testing Strategy
1. **Unit tests** for each signal connection
2. **Integration tests** for complete flows
3. **Performance benchmarks** before/after
4. **Parallel run** for safety during migration

## Expected Outcomes

### Code Reduction
- **-283 lines**: EventBus removal
- **-233 lines**: ServiceRegistry simplification  
- **-200 lines**: Reduced service boilerplate
- **Net reduction**: ~700 lines (40% of infrastructure)

### Performance Improvements
- **Remove 1 thread**: No EventBus worker
- **Direct signal delivery**: <5ms vs ~50ms with EventBus
- **Better debugging**: Qt signal tools vs custom event history
- **Lower memory**: No event history or queue

### Architecture Benefits
- **Explicit dependencies**: Easy to trace and test
- **No global state**: Better for testing
- **Service isolation**: Clear boundaries
- **Simpler mental model**: Direct connections

## Success Criteria

1. ✅ All EventBus imports removed
2. ✅ Services use direct Qt signal connections
3. ✅ No circular dependencies
4. ✅ Performance metrics collected and improved
5. ✅ 50+ symbols supported with <500ms latency
6. ✅ ~40% reduction in infrastructure code

## Timeline

**Week 1**: EventBus removal and dependency cleanup
**Week 2**: Add missing signals and multi-symbol foundation  
**Week 3**: ServiceRegistry removal and optimization

Total: 3 weeks to significantly simpler architecture