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
4. Simple > Complex: Let TypeScript catch errors instead of excessive runtime checks
5. Collaborative process: Work with user to identify most efficient solution


# Project Documentation
README.md: provides a high-level overview of the project.
claude.md: Contains specific instructions, persona, development standards for developing this project, and Architecture of the project.
MULTI_SYMBOL_MONITORING_PLAN.md: The official blueprint and feature roadmap for the current development epic.
IMPLEMENTATION_TRACKER.md: A detailed, task-level tracker for monitoring progress against the development plan.


## Development Environment

**Python Environment**: Use the Anaconda environment `ib_trade` 
- Path: `/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe`
- Python 3.11 required for compatibility with IB API and PyQt6

**Key Commands**:
```bash
# Run the application
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe main.py

# Run all tests (after installing pytest)
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe run_tests.py

# Run specific test suites
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe run_tests.py --unit          # Unit tests only
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe run_tests.py --integration   # Integration tests only  
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe run_tests.py --performance   # Performance benchmarks
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe run_tests.py --coverage      # With coverage report
```

## Architecture Overview

This is a sophisticated **event-driven, service-oriented architecture** for low-latency trading with Interactive Brokers.

**Current State**: The architecture is acknowledged as over-engineered for a single-user application. A hybrid optimization approach has been chosen - targeted simplification while adding new multi-symbol monitoring capabilities.

### Actual Implementation Architecture
```
├── Event-Driven Core
│   ├── event_bus.py            # Threaded pub-sub with event history
│   └── service_registry.py     # Lifecycle-managed DI container
│
├── Services Layer (src/services/) - Business Logic
│   ├── unified_data_service.py  # Consolidated market data hub
│   ├── data_service.py         # Legacy compatibility wrapper  
│   ├── connection_service.py   # IB API connection management
│   ├── order_service.py        # Order execution and management
│   ├── account_service.py      # Account data and risk tracking
│   ├── risk_service.py         # Position sizing calculations
│   ├── ib_connection_service.py # Low-level IB API wrapper
│   └── price_cache_service.py  # Intelligent price caching
│
├── Features Layer (src/features/) - Domain Logic
│   ├── connection/
│   │   ├── connection_manager.py # State-managed connection flow
│   │   ├── connection_dialog.py  # UI connection interface
│   │   └── connection_monitor.py # Connection health tracking
│   ├── market_data/
│   │   ├── data_manager.py      # Data orchestration
│   │   ├── market_scanner.py    # TWS scanner integration
│   │   └── price_processor.py   # Price validation & formatting
│   └── trading/
│       ├── trade_manager.py     # Trade workflow orchestration
│       ├── order_builder.py     # Complex order construction
│       └── position_tracker.py  # Position monitoring
│
├── UI Layer (src/ui/) - Presentation
│   ├── main_window.py          # Application orchestrator
│   ├── controllers/            # MVC controllers with BaseController
│   │   ├── base_controller.py  # Common controller functionality
│   │   ├── trading_controller.py # Trading workflow control
│   │   ├── connection_controller.py # Connection state management
│   │   └── market_data_controller.py # Data display control
│   └── panels/                 # Modular UI components
│       ├── connection_panel.py # Connection interface
│       ├── trading_panel.py    # Trading interface
│       └── status_panel.py     # Status display
│
└── Core Layer (src/core/) - Legacy (Migration in Progress)
    ├── data_fetcher.py         # Direct IB API operations
    ├── market_screener.py      # Scanner business logic
    ├── order_manager.py        # Order execution logic
    └── risk_calculator.py      # Risk calculation algorithms
```

### Key Architectural Patterns
- **Event-Driven Architecture**: Sophisticated `EventBus` with threaded processing, event history, and weak references
- **Service Registry Pattern**: Lifecycle-managed dependency injection with initialization ordering and cleanup
- **Unified Service Pattern**: `UnifiedDataService` consolidates multiple data sources with Qt signal integration
- **Legacy Wrapper Pattern**: `DataService` provides compatibility during migration from core to services
- **MVC with Base Classes**: `BaseController` provides common functionality for all UI controllers
- **State Management**: Connection state tracking with proper event publishing
- **Cache Abstraction**: `PriceCache` service with configurable TTL and batch operations

## Critical Technical Details

### IB API Integration
- **ib_async Integration**: `ib_connection_service.py` manages low-level IB API connections
- **Connection Management**: `connection_manager.py` handles state transitions and mode switching
- **Data Flow**: Market data flows through `unified_data_service.py` → Event Bus → UI controllers
- **Multi-Modal Architecture**: Supports both direct API calls and Qt signal-based async operations
- **Caching Strategy**: `price_cache_service.py` with intelligent TTL and batch price fetching
- **Order Execution**: Bracket orders with proper parent/child sequencing in `order_service.py`

### Performance Requirements
- Target: <200ms for all critical operations
- Price fetching: ~300ms with validation
- Chart updates: <200ms full render with 120fps crosshair
- UI responsiveness: <50ms for all interactions

### Configuration System
Comprehensive configuration management in `config.py` with 566 lines of settings:
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
- **Comprehensive error handling** with proper logging via `app_logger.py`
- **Validation layers** for all user inputs and API responses
- **Service-based architecture** - new features should use the service layer

### Testing Requirements
- **Unit tests** for all service classes in `tests/unit/services/`
- **Integration tests** for end-to-end workflows in `tests/integration/`
- **Performance benchmarks** with specific targets in `tests/performance/`
- All tests must pass before changes are considered complete
- **Note**: pytest needs to be installed in the ib_trade environment

### Working with Legacy Code
- **Migration Status**: `src/core/` contains original implementations being wrapped/migrated
- **Wrapper Pattern**: Services like `DataService` wrap `UnifiedDataService` for compatibility
- **Service Access**: Always use `ServiceRegistry.get_service()` or convenience functions
- **Migration Strategy**: 
  ```
  Phase 1: Core implementation (original)
  Phase 2: Service wrapper (compatibility)
  Phase 3: Unified service (consolidation)
  Phase 4: Legacy cleanup (removal)
  ```
- **Current Status**: Most services are in Phase 2-3, with active migration to unified pattern

### Data Flow Architecture

#### Price Data Flow (Actual Implementation)
```
UI Request → Controller → UnifiedDataService
    ↓
┌─ Direct IB API Call (data_fetcher.py)
│  └─ Raw price data
├─ Price Validation & Processing
├─ Cache Storage (price_cache_service.py)
├─ Event Publishing (EventBus)
└─ Qt Signals → UI Controllers → Panels
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
    ↓
UI Controllers Subscribe → Update Panels
```

#### Legacy Migration Strategy
```
Legacy Core Modules → Wrapper Services → Unified Services
Example: data_fetcher.py → data_service.py → unified_data_service.py
```

### Common Pitfalls
- **Blocking operations**: Always use async/threaded approaches for IB API calls
- **Price precision**: Different tick sizes for stocks ≥$1 (2 decimals) vs <$1 (4 decimals)
- **Order sequencing**: Bracket orders require proper parent/child transmit flag handling
- **Connection state**: Always check IB connection status before API operations

## Development Workflow

### Current Development: Multi-Symbol Monitoring System

For the next 8 weeks, development focuses on adding real-time monitoring for 50+ symbols. See:
- **[MULTI_SYMBOL_MONITORING_PLAN.md](MULTI_SYMBOL_MONITORING_PLAN.md)** - Technical specification
- **[IMPLEMENTATION_TRACKER.md](IMPLEMENTATION_TRACKER.md)** - Progress tracking

### General Development Guidelines

1. **Architecture First**: Review `service_registry.py` and `event_bus.py` to understand service patterns
2. **Planned Simplification**: Remove Feature layer, consolidate services, simplify DI container
3. **Service-Oriented**: Use existing services where possible (OrderService, RiskService)
4. **Provider Abstraction**: Easy switching between data providers (IB, Databento, etc.)
5. **Qt Integration**: Use Qt signals for UI responsiveness, prepare for chart library migration
6. **Testing Strategy**: Test services independently, use TA libraries for pattern detection
7. **Performance Monitoring**: Target <500ms for 50+ symbols, continuous profiling

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

### Planned Simplifications (Phase 1 of Multi-Symbol Monitoring)
1. **Remove Feature Layer**: Merge features into services to reduce abstraction
2. **Consolidate Data Services**: Single StreamingService instead of multiple
3. **Simplify DI**: Replace ServiceRegistry with simple factory pattern
4. **Unify Logging**: Merge 3 logger implementations into one

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

## ⚠️ CRITICAL KNOWN ISSUES (As of 2025-06-15)

### IMMEDIATE ATTENTION REQUIRED

1. **FINANCIAL SAFETY**: Risk calculator availability in RiskService can fail silently (src/services/risk_service.py:72-90)
   - **Impact**: Trades could execute without proper position sizing
   - **Priority**: CRITICAL - Fix before any live trading
   - **Solution**: Make risk calculator fail explicitly, add mandatory validation before order submission

2. **TESTING INFRASTRUCTURE**: pytest not installed in ib_trade environment
   - **Impact**: Cannot run test suite to validate changes
   - **Priority**: HIGH - Required for development
   - **Solution**: `pip install pytest pytest-cov` in ib_trade environment

3. **LOGGER DUPLICATION**: Three separate logger implementations
   - **Impact**: Confusion about which logger to use, maintenance overhead
   - **Priority**: MEDIUM - Code quality issue
   - **Solution**: Consolidate into single logger with optional Qt integration

### Verification Required
Before any production deployment, verify:
- [ ] Risk calculations always execute before trade submission
- [x] Event bus subscribers are properly managed (RESOLVED)
- [x] All imports resolve successfully (VERIFIED)
- [ ] Price validation includes timestamp checks

## Event-Driven Architecture Details

### EventBus Implementation
The `EventBus` is a sophisticated pub-sub system with:
- **Threaded Processing**: Events processed in separate worker thread to prevent UI blocking
- **Event History**: Maintains 1000 most recent events for debugging/monitoring
- **Type Safety**: Strongly-typed `EventType` enum prevents event naming conflicts
- **Error Isolation**: Individual subscriber failures don't affect other subscribers
- **Graceful Shutdown**: Proper cleanup with timeout handling

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
1. UI: OrderAssistant.fetch_price_clicked()
2. Controller: TradingController.handle_price_fetch()
3. Service: UnifiedDataService.fetch_price_data()
4. IB API: data_fetcher.get_latest_price_async()
5. Cache: price_cache_service.set()
6. Event: publish_event(PRICE_UPDATE, price_data)
7. Controllers: receive price update event
8. UI: Update price fields in OrderAssistant
```

### Order Flow Example
```
1. UI: OrderAssistant.place_order_clicked()
2. Controller: TradingController.handle_order_request()
3. Service: OrderService.create_bracket_order()
4. Validation: RiskService.validate_position_size()
5. IB API: order_manager.place_bracket_order()
6. Event: publish_event(ORDER_SUBMITTED, order_data)
7. UI: Show order status updates
```

### Connection Flow Example
```
1. UI: ConnectionDialog (mode selection)
2. Controller: ConnectionController.connect_to_ib()
3. Feature: ConnectionManager.connect()
4. Service: ib_connection_service.connect()
5. Event: publish_event(CONNECTION_STATUS_CHANGED)
6. UI: Update connection status across all panels
```

## Performance Optimization Strategies

### Caching Architecture
- **Multi-Layer Caching**: Price cache, stop levels cache, historical data cache
- **TTL Management**: Different cache lifetimes for different data types
- **Batch Operations**: Reduce API calls through intelligent batching
- **Cache Invalidation**: Event-driven cache updates

### Threading Strategy
- **EventBus Worker Thread**: Dedicated thread for event processing
- **Qt Signal Integration**: Thread-safe UI updates via Qt signals
- **IB API Threading**: Proper async/await patterns for IB operations
- **Non-Blocking UI**: Timer-based operations prevent UI freezing

### Memory Management
- **Event History Trimming**: Automatic cleanup of old events
- **Service Lifecycle**: Proper cleanup in ServiceRegistry
- **Weak References**: Prevent memory leaks in event subscriptions (where applicable)
- **Cache Size Limits**: Configurable cache size limits

## Testing Strategy

### Service Testing
```python
# Example service test
def test_data_service_price_fetch():
    service = DataService()
    service.initialize()
    
    # Mock IB connection
    with patch('src.services.ib_connection_service.ib') as mock_ib:
        mock_ib.reqMktData.return_value = mock_ticker
        
        result = service.fetch_price_data('AAPL')
        assert result['last'] > 0
        assert 'timestamp' in result
```

### Event Testing
```python
# Example event test
def test_price_update_event():
    event_received = []
    
    def handler(event):
        event_received.append(event)
    
    subscribe(EventType.PRICE_UPDATE, handler)
    publish_event(EventType.PRICE_UPDATE, {'symbol': 'AAPL'}, 'test')
    
    assert len(event_received) == 1
    assert event_received[0].data['symbol'] == 'AAPL'
```

### Integration Testing
- **End-to-End Workflows**: Test complete user journeys
- **Event Flow Testing**: Verify event propagation across services
- **Performance Benchmarks**: Validate against timing requirements
- **Error Handling**: Test service recovery scenarios