# Phase 0: Architecture Simplification - Detailed Tasks (REVISED)

## Overview
Phase 0 focuses on removing unnecessary complexity from the architecture while maintaining all existing functionality. The primary goals are removing EventBus, simplifying service dependencies, and preparing for efficient multi-symbol monitoring.

## Timeline: 3 Weeks (15 Business Days)

## Week 1: EventBus Removal & Direct Connections (Days 1-5)

### Day 1-2: Remove EventBus Usage
**Priority: 🔴 HIGH - ARCHITECTURE SIMPLIFICATION**

#### Task 1.1: Update UnifiedDataService
- **File**: `src/services/unified_data_service.py`
- **Changes**: Use existing Qt signals instead of EventBus
  ```python
  # OLD: EventBus publishing
  publish_event(EventType.PRICE_UPDATE, price_data, "UnifiedDataService")
  
  # NEW: Direct signal emission
  self.fetch_completed.emit(price_data)  # Signal already exists!
  ```
- **Locations**: 3 publish_event calls to update
- **Testing**: Verify price updates still flow to UI

#### Task 1.2: Update MarketDataController
- **File**: `src/ui/controllers/market_data_controller.py`
- **Changes**: Connect directly to service signals
  ```python
  # OLD: EventBus subscription
  subscribe(EventType.PRICE_UPDATE, self._on_price_update)
  
  # NEW: Direct connection
  self._data_service.fetch_completed.connect(self._on_price_update_direct)
  ```
- **Cleanup**: Remove EventBus imports and subscriptions

#### Task 1.3: Measure Performance Impact
- **Create**: `src/utils/performance_monitor.py`
- **Measure**: Signal delivery time before/after
- **Target**: <5ms for price update delivery

### Day 3: Clean Up EventBus Infrastructure
**Priority: 🟠 HIGH - CODE REDUCTION**

#### Task 2.1: Remove EventBus Files
- **Delete**: `src/services/event_bus.py` (283 lines)
- **Delete**: `src/types/common.py` (EventType enum)
- **Update**: Remove EventBus from `__init__.py` files

#### Task 2.2: Update Service Registry
- **File**: `src/services/service_registry.py`
- **Remove**: EventBus initialization and management
- **Remove**: `start_event_bus()` and `stop_event_bus()` calls

#### Task 2.3: Update Main Application
- **File**: `main.py`
- **Remove**: EventBus start/stop calls
- **Verify**: Application starts without EventBus

### Day 4-5: Simplify Service Dependencies
**Priority: 🟠 HIGH - REMOVE CIRCULAR DEPENDENCIES**

#### Task 3.1: Fix RiskService Dependencies
- **File**: `src/services/risk_service.py`
- **Current Problem**: Dynamic service lookup causing circular imports
  ```python
  # BAD: Dynamic lookup
  from src.services import get_account_service
  account_service = get_account_service()
  ```
- **Solution**: Constructor injection
  ```python
  def __init__(self, account_service: AccountService):
      self.account_service = account_service  # Explicit dependency
  ```

#### Task 3.2: Update MainWindow Service Creation
- **File**: `src/ui/main_window.py`
- **Create services in dependency order**:
  ```python
  # Explicit wiring - easy to understand and test
  self.ib_connection = IBConnectionService()
  self.account_service = AccountService(self.ib_connection)
  self.risk_service = RiskService(self.account_service)
  self.order_service = OrderService(self.ib_connection, self.risk_service)
  ```

#### Task 3.3: Remove Service Lookups
- **Search for**: All `get_*_service()` calls
- **Replace with**: Direct service references
- **Benefits**: No circular imports, clearer dependencies

## Week 2: Service-Owned Signals & Critical Flows (Days 6-10)

### Day 6-7: Add Missing Service Signals
**Priority: 🔴 HIGH - COMPLETE ARCHITECTURE**

#### Task 4.1: ConnectionService Signals
- **File**: `src/services/connection_service.py`
- **Add signals for connection lifecycle**:
  ```python
  class ConnectionService(BaseService, QObject):
      connection_changed = pyqtSignal(bool, str)  # connected, message
      account_selected = pyqtSignal(str)  # account_id
  ```
- **Emit on state changes**: Connection, disconnection, account selection

#### Task 4.2: OrderService Signals
- **File**: `src/services/order_service.py`
- **Add order lifecycle signals**:
  ```python
  class OrderService(BaseService, QObject):
      order_submitted = pyqtSignal(dict)
      order_filled = pyqtSignal(dict)
      order_failed = pyqtSignal(dict, str)
  ```
- **Emit at appropriate points**: Submit, fill, error

#### Task 4.3: Wire Controllers to Service Signals
- **Update**: All controllers to connect to service signals
- **Pattern**: Direct connections, no intermediaries
- **Test**: End-to-end signal flow

### Day 8: Remove ServiceRegistry
**Priority: 🟠 MEDIUM - SIMPLIFICATION**

#### Task 5.1: Create Simple ServiceManager
- **File**: `src/services/service_manager.py`
- **Simple container without complexity**:
  ```python
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

#### Task 5.2: Update MainWindow
- **Replace**: ServiceRegistry with ServiceManager
- **Simplify**: Service initialization code
- **Remove**: Complex lifecycle management

### Day 9-10: Multi-Symbol Foundation
**Priority: 🟠 MEDIUM - PREPARE FOR NEXT PHASE**

#### Task 6.1: Create MultiSymbolStreaming Service
- **File**: `src/services/multi_symbol_streaming.py`
- **Features**:
  - Direct IB API usage
  - Efficient subscription management
  - Batch update support
  - Performance monitoring

#### Task 6.2: Performance Testing
- **Test with**: 10-20 symbols
- **Measure**: Update latency, CPU usage, memory
- **Document**: Baseline metrics for comparison

#### Task 6.3: Create Simple Multi-Symbol UI
- **File**: `src/ui/components/multi_symbol_grid.py`
- **Basic grid**: Display multiple symbols
- **Connect to**: MultiSymbolStreaming service
- **Test**: UI responsiveness with updates

## Week 3: Final Cleanup & Optimization (Days 11-15)

### Day 11-12: Final Cleanup
**Priority: 🟢 LOW - HOUSEKEEPING**

#### Task 7.1: Remove Unused Code
- **Delete**: Any remaining EventBus references
- **Delete**: Unused service methods
- **Delete**: Complex BaseService if not needed

#### Task 7.2: Optimize Service Initialization
- **Remove**: Unnecessary state management
- **Simplify**: Service lifecycle to init/cleanup only
- **Document**: New patterns

### Day 13-14: Performance Optimization
**Priority: 🟠 MEDIUM - PERFORMANCE**

#### Task 8.1: Profile Application
- **Tools**: cProfile, memory_profiler
- **Identify**: Bottlenecks in signal delivery
- **Optimize**: Hot paths only

#### Task 8.2: Optimize Multi-Symbol Updates
- **Implement**: Smart batching for UI updates
- **Test**: With 50+ symbols
- **Target**: <500ms total latency

### Day 15: Documentation & Handoff
**Priority: 🟢 LOW - DOCUMENTATION**

#### Task 9.1: Update All Documentation
- **CLAUDE.md**: New architecture
- **README.md**: Updated setup instructions
- **EVENTBUS_REMOVAL_PLAN.md**: Mark as completed

#### Task 9.2: Create Migration Guide
- **Document**: What changed and why
- **Include**: Performance improvements
- **Add**: Troubleshooting section

## Success Criteria for Phase 0 (REVISED)

### EventBus Removal ✓
- [ ] All EventBus imports removed
- [ ] Services use direct Qt signal connections
- [ ] Performance improvement measured and documented
- [ ] No regression in functionality

### Service Simplification ✓
- [ ] No circular dependencies
- [ ] Explicit dependency injection
- [ ] ServiceRegistry replaced with simple manager
- [ ] Services own their signals

### Multi-Symbol Foundation ✓
- [ ] MultiSymbolStreaming service created
- [ ] Basic multi-symbol UI working
- [ ] Performance baseline with 20+ symbols
- [ ] <500ms update latency achieved

### Code Reduction ✓
- [ ] ~40% reduction in infrastructure code
- [ ] EventBus removed (-283 lines)
- [ ] ServiceRegistry simplified (-200+ lines)
- [ ] Cleaner, more maintainable architecture

## Risk Mitigation

### Rollback Strategy
1. Git tag before starting: `git tag pre-eventbus-removal`
2. Feature flag for EventBus usage:
   ```python
   USE_EVENTBUS = False  # Easy toggle for rollback
   ```
3. Keep EventBus code until migration verified
4. Test each service connection independently

### Testing Strategy
1. Test signal connections in isolation
2. Integration test complete flows
3. Performance benchmarks before/after
4. Parallel testing with both systems

### Migration Safety
1. One service at a time
2. Verify functionality after each change
3. Keep detailed logs of changes
4. Document any issues encountered

## Notes
- This revised plan focuses on actual simplification, not replacement
- Each change reduces complexity and improves maintainability
- Direct Qt signals are simpler and more performant than EventBus
- Services owning their signals provides better encapsulation
- Performance measurements guide optimization decisions
- Update IMPLEMENTATION_TRACKER.md after each completed task

## Key Changes from Original Plan
1. **No SignalHub** - Avoided creating EventBus replacement
2. **Direct connections** - Services to controllers without intermediaries
3. **Measure first** - Performance claims backed by actual data
4. **Simplicity focus** - Remove abstractions that don't add value
5. **Service ownership** - Each service manages its own signals