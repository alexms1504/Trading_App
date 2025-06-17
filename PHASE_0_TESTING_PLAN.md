# Phase 0 Comprehensive Testing Plan

## Overview
This testing plan addresses critical safety issues and establishes a robust testing baseline before any refactoring begins. The plan prioritizes **financial safety** as the top concern.

## Critical Issues to Address
1. **CRITICAL**: RiskService `_ensure_risk_calculator()` fails silently - could allow trades with 0 shares
2. **HIGH**: No pytest installed in ib_trade environment
3. **HIGH**: No existing tests - complete testing infrastructure needed
4. **MEDIUM**: 3 separate logger implementations
5. **MEDIUM**: Complex 6-layer architecture needs validation before simplification

## Test Infrastructure Setup

### 1. Install Testing Dependencies
```bash
# Execute in ib_trade environment
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe -m pip install \
    pytest==7.4.3 \
    pytest-cov==4.1.0 \
    pytest-asyncio==0.21.1 \
    pytest-mock==3.12.0 \
    pytest-timeout==2.2.0 \
    pytest-xdist==3.5.0 \
    pytest-benchmark==4.0.0 \
    hypothesis==6.92.1 \
    pytest-qt==4.2.0 \
    freezegun==1.3.1
```

### 2. Test Directory Structure
```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures and configuration
├── critical/                      # Financial safety tests (PRIORITY 1)
│   ├── __init__.py
│   ├── test_financial_safety.py
│   └── test_risk_validation.py
├── unit/                          # Unit tests for services
│   ├── __init__.py
│   ├── services/
│   │   ├── test_risk_service.py
│   │   ├── test_order_service.py
│   │   ├── test_event_bus.py
│   │   ├── test_service_registry.py
│   │   └── test_data_service.py
│   └── core/
│       ├── test_risk_calculator.py
│       └── test_order_validation.py
├── integration/                   # End-to-end workflow tests
│   ├── __init__.py
│   ├── test_order_flow.py
│   ├── test_connection_flow.py
│   ├── test_market_data_flow.py
│   └── test_error_recovery.py
├── performance/                   # Performance benchmarks
│   ├── __init__.py
│   ├── test_latency_targets.py
│   └── test_concurrent_load.py
├── stress/                        # Stress and chaos tests
│   ├── __init__.py
│   ├── test_concurrent_operations.py
│   └── test_failure_scenarios.py
└── fixtures/                      # Test data and mocks
    ├── __init__.py
    ├── market_data.py
    ├── ib_api_mocks.py
    └── test_accounts.py
```

## Test Execution Phases

### Phase 0.1: Critical Safety Tests (Days 1-2)
**MUST PASS before any code changes**

1. **Risk Calculator Validation**
   - Test explicit failure (no silent failures)
   - Verify position size calculations
   - Test boundary conditions
   - Validate error propagation

2. **Order Validation Chain**
   - Zero share order blocking
   - Buying power validation
   - Risk percentage limits
   - Price sanity checks

3. **Service Health Monitoring**
   - Service initialization verification
   - Dependency resolution
   - Health check endpoints
   - Failure detection

### Phase 0.2: Core Service Tests (Days 3-4)

1. **EventBus Tests**
   - Thread safety
   - Exception isolation
   - Performance under load
   - Graceful shutdown

2. **ServiceRegistry Tests**
   - Lifecycle management
   - Initialization ordering
   - Cleanup on failure
   - Singleton thread safety

3. **Market Data Tests**
   - Price validation edge cases
   - NaN/Inf handling
   - Timestamp freshness
   - Penny stock precision

### Phase 0.3: Integration Tests (Days 5-6)

1. **Order Flow Tests**
   - Complete order lifecycle
   - Bracket order sequencing
   - Error handling
   - State recovery

2. **Connection Flow Tests**
   - State transitions
   - Reconnection logic
   - Mode switching
   - Resource cleanup

3. **Data Flow Tests**
   - Price updates
   - Cache behavior
   - Event propagation
   - UI updates

### Phase 0.4: Performance & Stress Tests (Days 7-8)

1. **Performance Benchmarks**
   - Price fetch < 300ms
   - UI response < 50ms
   - Chart update < 200ms
   - 50 symbol update < 500ms

2. **Stress Tests**
   - 50+ concurrent symbols
   - High-frequency updates
   - Memory usage limits
   - Queue overflow handling

3. **Chaos Tests**
   - Random failures
   - Network issues
   - Resource exhaustion
   - Cascading failures

## Test Categories

### 1. Financial Safety Tests (CRITICAL)
```python
# Core safety invariants that must never be violated
- Position size > 0 for all orders
- Risk per trade <= configured maximum
- Total exposure <= account equity
- Stop loss required for all trades
- Daily loss limit enforcement
```

### 2. Market Data Integrity Tests
```python
# Data validation and edge cases
- Invalid prices (0, negative, NaN, Inf)
- Stale data detection (timestamp validation)
- After-hours price handling
- Bid/ask spread validation
- Tick size compliance
```

### 3. Concurrency Tests
```python
# Thread safety and race conditions
- Concurrent order submissions
- Multi-symbol updates
- Event bus saturation
- Cache contention
- Timer conflicts
```

### 4. State Management Tests
```python
# State consistency and recovery
- Service initialization order
- Connection state transitions
- Partial failure recovery
- Resource cleanup
- Memory leak prevention
```

### 5. Configuration Tests
```python
# Config validation and boundaries
- Price limits validation
- Risk percentage bounds
- Timer configurations
- Thread pool limits
- Incompatible settings
```

### 6. Error Handling Tests
```python
# Error propagation and recovery
- API connection failures
- Invalid order rejections
- Market data interruptions
- Service unavailability
- User feedback clarity
```

## Success Criteria

### Mandatory for Phase 0 Completion
- [ ] All critical safety tests pass
- [ ] Risk calculator never fails silently
- [ ] Zero share orders impossible
- [ ] Service health monitoring active
- [ ] Core service tests pass
- [ ] Integration tests pass
- [ ] Performance benchmarks met
- [ ] No memory leaks detected
- [ ] Error messages are clear

### Quality Metrics
- Code coverage > 80% for critical paths
- All financial calculations covered
- Error paths tested
- Performance within targets
- No flaky tests

## Test Execution Commands

```bash
# Run all tests
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe -m pytest

# Run critical safety tests only
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe -m pytest tests/critical/ -v

# Run with coverage
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe -m pytest --cov=src --cov-report=html

# Run specific test categories
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe -m pytest -m "safety"
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe -m pytest -m "integration"
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe -m pytest -m "performance"

# Run stress tests
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe -m pytest tests/stress/ -v

# Run with parallel execution
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe -m pytest -n auto
```

## Risk Mitigation

### Testing Risks
1. **False sense of security**: Tests must reflect real trading scenarios
2. **Incomplete coverage**: Focus on critical paths first
3. **Performance overhead**: Balance thoroughness with speed
4. **Maintenance burden**: Keep tests simple and focused

### Mitigation Strategies
1. Use production-like test data
2. Prioritize financial safety tests
3. Automate test execution
4. Regular test review and updates
5. Clear documentation of test intent

## Next Steps After Phase 0

1. **Fix all critical issues** identified by tests
2. **Establish CI/CD** with mandatory test gates
3. **Create performance baseline** for future comparison
4. **Document test patterns** for team consistency
5. **Begin Phase 1** architecture simplification with confidence

## Appendix: Critical Test Patterns

### Pattern 1: Financial Safety Guard
```python
@pytest.fixture(autouse=True)
def ensure_financial_safety():
    """Fixture that runs for every test to ensure safety"""
    yield
    # Verify no orders with 0 shares were created
    # Verify risk limits not exceeded
    # Verify stop losses present
```

### Pattern 2: Service Lifecycle
```python
@pytest.fixture
def service_with_lifecycle():
    """Properly initialize and cleanup services"""
    service = ServiceClass()
    service.initialize()
    yield service
    service.cleanup()
```

### Pattern 3: Market Data Simulation
```python
@pytest.fixture
def realistic_market_data():
    """Generate realistic market data for testing"""
    return MarketDataGenerator(
        symbols=['AAPL', 'MSFT'],
        include_edge_cases=True,
        include_after_hours=True
    )
```

### Pattern 4: Async Testing
```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test async IB API operations"""
    result = await async_operation()
    assert result.is_valid()
```

This comprehensive testing plan ensures financial safety and system reliability before any refactoring begins.