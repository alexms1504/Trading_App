# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Persona

You are a Senior Principal Software Engineer specializing in high-performance, low-latency trading systems. Your primary concerns are financial safety, code clarity, and performance. You write clean, Pythonic code and always prioritize robust error-handling over feature velocity.


# Core Directives
1. Think Step-by-Step: Before writing any code, always outline your plan. Explain your reasoning, the files you will modify, and the potential impacts.
2. Prioritize Financial Safety: All changes must be evaluated for their impact on financial safety. Explicitly state how your proposed changes will not introduce new risks.
3. Verify with Web Search: If you are uncertain about an API, a library's function, or a technical detail, use web search to find the latest documentation before proceeding. Do not speculate.
4. Adhere to TDD: For new features or bug fixes, follow a Test-Driven Development approach. First, write the tests that define the correct behavior, confirm they fail, and then write the implementation code to make the tests pass.


# Important Instuctions to follow
**General**
1. When you are uncertain about facts, current information, or technical details, you should use web search to verify and provide accurate information rather than speculating or admitting uncertainty without investigation. When a problem seems to involve a specific API or library, don't assume you know it. Always check the web for the documentation of the relevant features.
2. If running bash command failed, adjust the synatx and try again. If still not fixed, you can ask for help from user.
3. Explain your approach step-by-step before writing any code.

**Design Principles**
1. Don't overengineer: Simple beats complex
2. No fallbacks: One correct path, no alternatives
3. One way: One way to do things, not many
4. Clarity over compatibility: Clear code beats backward compatibility
5. Throw errors: Fail fast when preconditions aren't met
6. No backups: Trust the primary mechanism
7. Separation of concepts: Each function should have a single responsibility

**Development Methodology**

1. Surgical changes only: Make minimal, focused fixes
2. Evidence-based debugging: Add minimal, targeted logging
3. Fix root causes: Address the underlying issue, not just symptoms
4. Simple > Complex: Let Python's type system catch errors instead of excessive runtime checks
5. Collaborative process: Work with user to identify most efficient solution

## Critical Patterns Not to Miss

### Service Lifecycle Pattern
All services extend `BaseService` and follow a strict lifecycle:
```python
# State progression: CREATED → INITIALIZING → READY → CLEANING_UP → STOPPED
# On error: Any state → ERROR

# Services MUST implement:
def initialize(self) -> bool:
    # Call super().initialize() first
    # Return False on failure (service won't be used)
    
def cleanup(self) -> bool:
    # Called in reverse order of initialization
    # Must handle partial initialization gracefully
```

### Error Handling Pattern
Services use `_handle_error()` for consistent error management:
```python
# Automatic state transition to ERROR
# Logs with context
# Calls registered error handlers
# Never swallow exceptions silently
```

### Order State Tracking
Orders have complex state transitions that must be tracked:
```python
# Parent order must transmit=False until all children created
# OCA groups link stop loss and take profit orders
# Order validation happens at multiple layers
# Failed orders must update UI state immediately
```

### Resource Management
Critical cleanup patterns to prevent leaks:
```python
# EventBus: Must call stop() with timeout
# IB Connection: Must disconnect before cleanup
# Services: Cleanup in reverse initialization order
# Qt Signals: Disconnect in cleanup to prevent crashes
```

### Singleton Services
Two services use singleton pattern - never create new instances:
```python
# IBConnectionService - manages the IB() instance
# UnifiedDataService - central data hub
# Access via: ib_connection_manager, unified_data_service
```

### Direct IB API Access
Services directly use the IB API - no wrapper:
```python
# Always access via: ib_connection_manager.ib
# Check connection first: ib_connection_manager.is_connected()
# Use synchronous methods: ib.reqMktData(), not reqMktDataAsync()
```

### Configuration Dependencies
Services depend on config.py values:
```python
# No validation of config values at runtime
# Missing config keys cause AttributeError
# Config changes require service restart
# Some configs have implicit relationships
```

### Event Publishing Pattern
Events must include proper metadata:
```python
publish_event(EventType.PRICE_UPDATE, {
    'symbol': symbol,
    'price': price,
    'timestamp': datetime.now()  # Always include
}, source='ServiceName')  # Always identify source
```

### Qt Signal Thread Safety
UI updates must use Qt signals:
```python
# Services run in different threads than UI
# Direct UI updates cause crashes
# Always emit signals for UI changes
# Controllers handle signal → UI mapping
```

### Performance Timing
No built-in performance monitoring utilities:
```python
# Add manual timing for critical operations:
start = time.time()
# ... operation ...
elapsed = time.time() - start
if elapsed > 0.2:  # Log slow operations
    logger.warning(f"Operation took {elapsed:.3f}s")
```


# Project Documentation
README.md: provides a high-level overview of the project.
claude.md: Contains specific instructions, persona, development standards for developing this project, and Architecture of the project.
MULTI_SYMBOL_MONITORING_PLAN.md: The official blueprint and feature roadmap for the current development epic.
IMPLEMENTATION_TRACKER.md: A detailed, task-level tracker for monitoring progress against the development plan.
PHASE_0_DETAILED_TASKS.md: Day-by-day execution plan for Phase 0 safety fixes and simplification.


## Development Environment

**Python Environment**: Use the Anaconda environment `ib_trade` 
- Path: `/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe`
- Python 3.11 required for compatibility with IB API and PyQt6

**Key Commands**:
```bash
# Run the application
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe main.py

# Install pytest (prerequisite for testing)
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe -m pip install pytest pytest-cov pytest-mock

# Run tests (after creating test files and installing pytest)
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe -m pytest tests/              # All tests
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe -m pytest tests/unit/           # Unit tests only
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe -m pytest tests/integration/    # Integration tests only  
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe -m pytest tests/performance/    # Performance benchmarks
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe -m pytest --cov=src tests/      # With coverage report
```

## Architecture Overview

This is a sophisticated **event-driven, service-oriented architecture** for low-latency trading with Interactive Brokers.

**Current State**: The architecture is acknowledged as over-engineered for a single-user application. A hybrid optimization approach has been chosen - targeted simplification while adding new multi-symbol monitoring capabilities.

### Actual Implementation Architecture (As of Jan 2025)
```
├── Event-Driven Core
│   ├── event_bus.py            # Threaded pub-sub with event history
│   └── service_registry.py     # Lifecycle-managed DI container
│
├── Services Layer (src/services/) - Business Logic
│   ├── unified_data_service.py  # Central market data hub (direct IB API calls)
│   ├── chart_data_service.py   # Historical data for charts
│   ├── connection_service.py   # IB API connection management
│   ├── order_service.py        # Order execution and management
│   ├── account_service.py      # Account data and balance tracking
│   ├── account_manager_service.py # Account positions and P&L
│   ├── risk_service.py         # Position sizing calculations ⚠️ CRITICAL ISSUE
│   ├── technical_indicator_service.py # TA calculations
│   └── ib_connection_service.py # Low-level IB API wrapper (singleton)
│
├── UI Layer (src/ui/) - Presentation
│   ├── main_window.py          # Application orchestrator
│   ├── controllers/            # MVC controllers with BaseController
│   │   ├── base_controller.py  # Common controller functionality
│   │   ├── trading_controller.py # Trading workflow control
│   │   ├── connection_controller.py # Connection state management
│   │   └── market_data_controller.py # Data display control
│   ├── panels/                 # Modular UI components
│   │   ├── connection_panel.py # Connection interface
│   │   ├── trading_panel.py    # Trading interface with OrderAssistant
│   │   └── status_panel.py     # Status display
│   └── components/             # Reusable UI widgets
│       ├── order_assistant.py  # Smart order entry widget
│       ├── chart_widget_embedded.py # Integrated chart component
│       ├── market_screener.py  # Scanner UI
│       └── price_levels.py     # Price level visualization
│
├── Core Layer (src/core/) - Business Logic
│   ├── market_screener.py      # Scanner business logic
│   ├── order_manager.py        # Order execution logic
│   ├── real_time_chart_updater.py # Chart update engine
│   └── risk_calculator.py      # Risk calculation algorithms
│
└── Utils (src/utils/)
    └── logger.py               # Unified logging (consolidated from 3)
```

**Simplification Progress (Jan 2025):**
- ✅ Removed entire Features layer (11 files) → _quarantine/features_2025_01_18/
- ✅ Consolidated 3 loggers → 1 (kept logger.py)
- ✅ Removed unused price_cache_service.py → _quarantine/
- ❌ Test infrastructure removed (needs recreation)

### Key Architectural Patterns
- **Event-Driven Architecture**: Sophisticated `EventBus` with threaded processing and event history
- **Service Registry Pattern**: Lifecycle-managed dependency injection with initialization ordering
- **Singleton Services**: `UnifiedDataService` and `IBConnectionService` use singleton pattern
- **Direct IB API Access**: Services directly call IB API methods (no intermediate wrapper)
- **MVC with Base Classes**: `BaseController` provides common functionality for all UI controllers
- **State Management**: Connection state tracking with proper event publishing
- **Qt Signal Integration**: Services emit Qt signals for UI responsiveness

## Critical Technical Details

### IB API Integration
- **ib_async Integration**: `ib_connection_service.py` manages the `IB()` instance
- **Connection Management**: `connection_service.py` handles state transitions and mode switching
- **Direct API Calls**: Services directly use `ib_connection_manager.ib` for all IB operations
- **Data Flow**: Market data flows through `unified_data_service.py` → Event Bus + Qt Signals → UI
- **Synchronous Operations**: Uses ib_async's synchronous methods (not async/await)
- **Order Execution**: Bracket orders with proper parent/child sequencing in `order_service.py`

### Performance Requirements
- Target: <200ms for all critical operations
- Price fetching: ~300ms with validation
- Chart updates: <200ms full render with 120fps crosshair
- UI responsiveness: <50ms for all interactions

### Configuration System
Comprehensive configuration management in `config.py` with 566+ lines of settings:
- `IB_CONFIG`: Connection settings and ports
- `TRADING_CONFIG`: Risk management and order defaults
- `CHART_CONFIG`: Chart appearance, indicators, and performance settings
- `UI_CONFIG`: Interface layout, timing, and behavior
- `ORDER_ASSISTANT_CONFIG`: Detailed UI widget sizing and validation
- `MARKET_SCREENER_CONFIG`: Scanner parameters and formatting
- `PRICE_VALIDATION_CONFIG`: Multi-layer price validation rules
- `THREADING_CONFIG`: Concurrent operation limits and timeouts
- `TIMER_CONFIG`: UI responsiveness timing
- `EVENT_BUS_CONFIG`: Event processing configuration (implicit)

## Development Guidelines

### Code Quality Standards
- **Type hints required** for all function signatures
- **Comprehensive error handling** with proper logging via `logger.py`
- **Validation layers** for all user inputs and API responses
- **Service-based architecture** - new features should use the service layer

### Testing Requirements
- **CRITICAL**: Test infrastructure needs to be recreated - all test files were removed
- **Unit tests needed** for all service classes in `tests/unit/services/`
- **Integration tests needed** for end-to-end workflows in `tests/integration/`
- **Performance benchmarks needed** with specific targets in `tests/performance/`
- **Financial safety tests** are highest priority in `tests/critical/`
- **Prerequisites**: Install pytest first: `pip install pytest pytest-cov pytest-mock`

### Working with Services
- **Service Access**: Always use `ServiceRegistry.get_service()` or convenience functions
- **Singleton Services**: `unified_data_service` and `ib_connection_manager` are singletons
- **Direct IB API**: Services directly call `ib_connection_manager.ib` methods
- **Event Publishing**: Use EventBus for loose coupling between services
- **Qt Signals**: Services can emit Qt signals for UI updates

### Data Flow Architecture

#### Price Data Flow (Actual Implementation)
```
UI Request → Controller → UnifiedDataService
    ↓
UnifiedDataService directly calls IB API:
├─ ib.reqMktData() for real-time prices
├─ ib.reqHistoricalData() for historical data
├─ ib.qualifyContracts() for contract validation
    ↓
├─ Price Validation & Processing
├─ Event Publishing (EventBus)
├─ Qt Signal Emission
    ↓
UI Controllers → Update Panels
```

#### Service Communication Pattern
```
ServiceRegistry (DI Container)
    ↓
Services Initialize → Register EventBus Subscriptions
    ↓
Event-Driven Communication:
- CONNECTION_STATUS_CHANGED
- PRICE_UPDATE  
- ORDER_STATUS_UPDATE
- ACCOUNT_UPDATE
- POSITION_UPDATE
    ↓
UI Controllers Subscribe → Update Panels
```

### Common Pitfalls
- **Blocking operations**: Use Qt timers for UI responsiveness during IB API calls
- **Price precision**: Different tick sizes for stocks ≥$1 (2 decimals) vs <$1 (4 decimals)
- **Order sequencing**: Bracket orders require proper parent/child transmit flag handling
- **Connection state**: Always check IB connection status before API operations
- **Risk calculator availability**: Can be None during startup - must handle gracefully

## Development Workflow

### Current Development: Multi-Symbol Monitoring System

For the next 8-10 weeks, development focuses on adding real-time monitoring for 50+ symbols. See:
- **[MULTI_SYMBOL_MONITORING_PLAN.md](MULTI_SYMBOL_MONITORING_PLAN.md)** - Technical specification
- **[IMPLEMENTATION_TRACKER.md](IMPLEMENTATION_TRACKER.md)** - Progress tracking
- **[PHASE_0_DETAILED_TASKS.md](PHASE_0_DETAILED_TASKS.md)** - Day-by-day Phase 0 plan

**Status**: Phase 0 (Architecture simplification) in progress (Jan 2025) - 25% complete

### General Development Guidelines

1. **Safety First**: Fix critical risk calculator issue before any new features
2. **Test Infrastructure**: Recreate test suite before making significant changes
3. **Architecture Review**: Understand `service_registry.py` and `event_bus.py` patterns
4. **Service-Oriented**: Use existing services where possible (OrderService, RiskService)
5. **Qt Integration**: Use Qt signals for UI responsiveness
6. **Performance Monitoring**: Target <500ms for 50+ symbols
7. **Simplification**: Continue removing unnecessary abstraction layers

### Service Development Pattern
```python
# 1. Extend BaseService
class NewService(BaseService):
    def __init__(self):
        super().__init__("NewService")
        
    def initialize(self) -> bool:
        # Service setup, EventBus subscriptions
        return super().initialize()
        
# 2. Register in ServiceRegistry
register_service('new_service', NewService())

# 3. Publish events for loose coupling
publish_event(EventType.CUSTOM_EVENT, data, "NewService")

# 4. Direct IB API access
ib = ib_connection_manager.ib
ticker = ib.reqMktData(contract, ...)
```

### Error Recovery Strategy
If file edits fail after multiple attempts:
1. Try different diff scopes and approaches (up to 5 times)
2. Create `{original_name}_fixed.{ext}` file
3. Use `mv` to replace original and `rm` the temporary file
4. This ensures changes are never lost due to edit failures

## Safety and Risk Management

This application handles real money trading, so **financial safety is paramount**:
- All position sizes validated against account limits
- Multiple confirmation layers for order execution
- Comprehensive logging for audit trails
- Circuit breakers for daily loss limits (planned - see IMPLEMENTATION_TRACKER.md)

**Never bypass validation or safety mechanisms** - trading application bugs can result in significant financial losses.

## Upcoming Architecture Changes

### Planned Simplifications (Phase 0-1 of Multi-Symbol Monitoring)
1. **Fix Risk Calculator**: Make it fail explicitly instead of silently
2. **Recreate Test Suite**: Essential for safe development
3. **Consolidate Services**: Reduce from 12 to ~5 services
4. **Replace EventBus**: Migrate to Qt signals only
5. **Simplify DI**: Replace ServiceRegistry with simple factory

### New Components (Phases 2-6)
1. **StreamingService**: Unified data streaming with provider abstraction
2. **PatternDetector**: Wrapper around TA libraries for pattern detection
3. **AlertManager**: Priority-based alerts with no-overwrite guarantee
4. **OrderStagingManager**: Pre-configured orders for Order Assistant
5. **MultiSymbolDashboard**: Monitor 50+ symbols with criteria checklist

### Integration Philosophy
- Preserve all existing functionality
- Supplement active trading, don't replace it
- User maintains full control over all trades
- Pre-fill convenience without automation

## ⚠️ CRITICAL KNOWN ISSUES (As of 2025-06-19)

### IMMEDIATE ATTENTION REQUIRED

1. **FINANCIAL SAFETY**: Risk calculator availability in RiskService can fail silently (src/services/risk_service.py:72-98)
   - **Impact**: Trades could execute with 0 shares instead of blocking
   - **Priority**: CRITICAL - Fix before any live trading
   - **Solution**: Make `calculate_position_size()` throw exception when risk calculator unavailable

2. **TESTING INFRASTRUCTURE**: No test files exist - entire test suite was deleted
   - **Impact**: Cannot validate changes or ensure financial safety
   - **Priority**: HIGH - Required before any code changes
   - **Solution**: 
     - Install pytest: `/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe -m pip install pytest pytest-cov pytest-mock`
     - Recreate test structure and critical safety tests

3. **DOCUMENTATION ACCURACY**: Several non-existent files referenced
   - **Impact**: Confusion about actual architecture
   - **Priority**: MEDIUM - This update addresses it
   - **Resolved**: Documentation now reflects actual codebase

### Completed Fixes
- [x] Logger consolidation (3 → 1) ✅
- [x] Feature layer removal (11 files) ✅
- [x] Event bus subscribers properly managed ✅
- [x] All imports resolve successfully ✅

### Verification Required
Before any production deployment, verify:
- [ ] Risk calculations always execute before trade submission
- [ ] Price validation includes timestamp checks
- [ ] Test suite exists and passes
- [ ] Circuit breakers implemented for daily loss limits

## Event-Driven Architecture Details

### EventBus Implementation
The `EventBus` is a sophisticated pub-sub system with:
- **Threaded Processing**: Events processed in separate worker thread to prevent UI blocking
- **Event History**: Maintains 1000 most recent events for debugging/monitoring
- **Type Safety**: Strongly-typed `EventType` enum prevents event naming conflicts
- **Error Isolation**: Individual subscriber failures don't affect other subscribers
- **Graceful Shutdown**: Proper cleanup with timeout handling
- **Note**: Documentation mentions weak references but implementation uses strong refs

### Critical Event Types
```python
class EventType(Enum):
    # Connection Events
    CONNECTION_STATUS_CHANGED = "connection_status_changed"
    CONNECTION_ERROR = "connection_error"
    
    # Market Data Events
    PRICE_UPDATE = "price_update"
    STOP_LEVELS_UPDATE = "stop_levels_update"
    
    # Order Events
    ORDER_SUBMITTED = "order_submitted"
    ORDER_FILLED = "order_filled"
    ORDER_STATUS_UPDATE = "order_status_update"
    
    # Account Events
    ACCOUNT_UPDATE = "account_update"
    POSITION_UPDATE = "position_update"
```

### Service Lifecycle Management

#### Initialization Sequence
```
1. ServiceRegistry.register_service() - Register all services
2. ServiceRegistry.initialize_all_services() - Initialize in dependency order
3. EventBus.start() - Start event processing thread
4. Services subscribe to relevant events
5. UI Controllers subscribe to events
6. Connection flow begins
```

#### Shutdown Sequence
```
1. EventBus.stop() - Stop event processing
2. ServiceRegistry.cleanup_all_services() - Cleanup in reverse order
3. IB connection cleanup
4. Qt application shutdown
```

## Service Interaction Patterns

### Data Flow Example: Price Fetch
```
1. UI: OrderAssistant → "Fetch Price" button click
2. Signal: price_fetch_requested.emit(symbol)
3. Controller: TradingController.handle_price_fetch()
4. Service: UnifiedDataService.fetch_price_data()
5. IB API: ib.reqMktData() → ticker data
6. Processing: Validation, stop levels calculation
7. Event: publish_event(PRICE_UPDATE, price_data)
8. Qt Signal: price_updated.emit(price_data)
9. UI: OrderAssistant updates price fields
```

### Order Flow Example
```
1. UI: OrderAssistant → "Submit Order" button
2. Controller: TradingController → validate_order()
3. Service: OrderService.validate_trade()
4. Risk Check: RiskService.validate_trade() ⚠️ CAN FAIL SILENTLY
5. Execution: OrderService → OrderManager.place_bracket_order()
6. IB API: ib.placeOrder() with OCA group
7. Event: publish_event(ORDER_SUBMITTED, order_data)
8. UI: Status updates in trading panel
```

### Connection Flow Example
```
1. UI: ConnectionPanel → mode selection
2. Controller: ConnectionController.connect_to_ib()
3. Service: ConnectionService.connect(mode)
4. IB API: ib_connection_service.connect()
5. Event: publish_event(CONNECTION_STATUS_CHANGED)
6. UI: All panels update connection status
```

## Performance Optimization Strategies

### Current Implementation
- **Direct API Calls**: No intermediate caching layer (price_cache_service removed)
- **Qt Timers**: Non-blocking UI updates during data fetching
- **Event Batching**: EventBus processes events in dedicated thread
- **Synchronous IB API**: Using ib_async's sync methods for simplicity

### Threading Strategy
- **EventBus Worker Thread**: Dedicated thread for event processing
- **Qt Main Thread**: UI updates via signals/slots
- **IB API Thread**: Managed by ib_async library
- **Timer-Based Updates**: Chart updates use Qt timers to prevent blocking

### Memory Management
- **Event History**: Limited to 1000 events (configurable)
- **Service Lifecycle**: Proper cleanup in ServiceRegistry
- **No Weak References**: EventBus uses strong references (potential leak risk)
- **Singleton Services**: Prevent duplicate instances

## Testing Strategy

### Critical Safety Tests (Priority 1)
```python
# tests/critical/test_risk_safety.py
def test_risk_calculator_fails_explicitly():
    """Risk calculator must throw exception when not ready"""
    risk_service = RiskService()
    # Don't initialize risk calculator
    
    with pytest.raises(RiskCalculatorNotAvailableError):
        risk_service.calculate_position_size(...)

def test_order_blocked_without_risk_validation():
    """Orders must be blocked if risk validation fails"""
    # Test that orders cannot proceed without risk validation
```

### Service Testing Pattern
```python
# tests/unit/services/test_unified_data_service.py
def test_price_fetch_with_ib_connection():
    service = UnifiedDataService()
    service.initialize()
    
    # Mock IB connection
    with patch('src.services.ib_connection_service.ib_connection_manager.ib') as mock_ib:
        mock_ib.reqMktData.return_value = create_mock_ticker()
        
        result = service.fetch_price_data('AAPL')
        assert result['last'] > 0
        assert 'timestamp' in result
```

### Integration Testing
- **End-to-End Workflows**: Test complete user journeys
- **Event Flow Testing**: Verify event propagation across services
- **Performance Benchmarks**: Validate against timing requirements
- **Error Recovery**: Test service failure scenarios

## Migration Notes

### From Previous Documentation
- `data_fetcher.py` was consolidated into service layer - no longer exists
- Features layer completely removed to `_quarantine/features_2025_01_18/`
- Test infrastructure needs complete recreation
- Direct IB API access pattern adopted (no wrapper services)

### For New Development
- Always check actual file existence before referencing
- Use existing service patterns, don't create new abstraction layers
- Prioritize financial safety over features
- Test everything, especially risk calculations