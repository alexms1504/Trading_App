# Phase 0: Critical Safety & Architecture Simplification - Detailed Tasks

## Overview
Phase 0 focuses on fixing critical safety issues and beginning architecture simplification before any new feature development. This phase is essential to ensure financial safety and create a stable foundation for the multi-symbol monitoring system.

## Timeline: 2 Weeks (10 Business Days)

## Week 1: Critical Safety Fixes (Days 1-5)

### Day 1-2: Risk Calculator Safety Fix
**Priority: 🔴 CRITICAL - FINANCIAL SAFETY**

#### Task 1.1: Fix RiskService Silent Failure
- **File**: `src/services/risk_service.py`
- **Issue**: `_ensure_risk_calculator()` returns False instead of raising exception
- **Changes Required**:
  ```python
  # Current (DANGEROUS):
  def _ensure_risk_calculator(self) -> bool:
      if not self.risk_calculator:
          return False  # Silent failure!
  
  # Fixed (SAFE):
  def _ensure_risk_calculator(self) -> None:
      if not self.risk_calculator:
          raise RuntimeError("Risk calculator not initialized - cannot proceed with trade")
  ```
- **Impact**: All methods using `_ensure_risk_calculator()` need error handling updates
- **Test**: Write unit tests to verify exception is raised

#### Task 1.2: Update Risk Calculation Methods
- **Methods to Update**:
  - `calculate_position_size()` - Remove empty result return
  - `validate_trade()` - Must fail explicitly
  - `calculate_r_multiple()` - Must not return 0.0 on failure
- **Pattern**:
  ```python
  def calculate_position_size(self, ...):
      self._ensure_risk_calculator()  # Will raise if not ready
      # ... rest of method
  ```

#### Task 1.3: Add Mandatory Risk Validation
- **File**: `src/services/order_service.py`
- **Add Pre-Order Validation**:
  ```python
  def place_order(self, order_request):
      # MANDATORY: Validate risk before ANY order
      risk_validation = self.risk_service.validate_trade(...)
      if not risk_validation['is_valid']:
          raise ValueError(f"Risk validation failed: {risk_validation['messages']}")
      # ... proceed with order
  ```

### Day 3: Testing Infrastructure Setup
**Priority: 🟠 HIGH - REQUIRED FOR VALIDATION**

#### Task 2.1: Install pytest in ib_trade Environment
```bash
/mnt/c/Users/alanc/anaconda3/envs/ib_trade/python.exe -m pip install pytest pytest-cov pytest-mock
```

#### Task 2.2: Create Critical Safety Test Suite
- **File**: `tests/critical/test_risk_safety.py`
- **Tests**:
  - Test risk calculator initialization failure
  - Test position size calculation with missing data
  - Test order rejection on risk validation failure
  - Test daily loss limit enforcement

#### Task 2.3: Create Test Runner Script
- **File**: `run_safety_tests.py`
- **Purpose**: Run only critical safety tests quickly
```python
#!/usr/bin/env python
"""Run critical safety tests only"""
import subprocess
import sys

if __name__ == "__main__":
    cmd = [sys.executable, "-m", "pytest", "tests/critical/", "-v"]
    subprocess.run(cmd)
```

### Day 4-5: Additional Safety Measures
**Priority: 🟠 HIGH - FINANCIAL SAFETY**

#### Task 3.1: Implement Daily Loss Limit Circuit Breaker
- **File**: Create `src/services/circuit_breaker_service.py`
- **Features**:
  - Track daily P&L
  - Automatic trading halt on limit breach
  - Manual override with double confirmation
  - Persistent state across restarts

#### Task 3.2: Add Order Size Validation
- **File**: `src/services/order_service.py`
- **Validations**:
  - Maximum position size (% of account)
  - Maximum order value ($)
  - Minimum share size (> 0)
  - Symbol validation (no typos)

#### Task 3.3: Implement Audit Logging
- **File**: Create `src/services/audit_service.py`
- **Log All**:
  - Order attempts (successful and failed)
  - Risk calculations
  - Circuit breaker activations
  - Configuration changes

## Week 2: Architecture Simplification (Days 6-10)

### Day 6: Logger Consolidation
**Priority: 🟡 MEDIUM - CODE QUALITY**

#### Task 4.1: Analyze Existing Loggers
- **Files to Review**:
  - `src/utils/logger.py`
  - `src/utils/app_logger.py`
  - `src/utils/simple_logger.py`
- **Identify**: Which logger is most complete and used most

#### Task 4.2: Create Unified Logger
- **File**: `src/utils/unified_logger.py`
- **Features**:
  - Single configuration point
  - File + console output
  - Rotating file handler
  - Structured logging (JSON option)
  - Performance metrics logging

#### Task 4.3: Migrate All Code to Unified Logger
- **Search & Replace**: Update all imports
- **Test**: Ensure no log messages are lost

### Day 7-8: Service Layer Consolidation (Part 1)
**Priority: 🟡 MEDIUM - ARCHITECTURE**

#### Task 5.1: Merge Data Services
- **Target**: Single `market_data_service.py`
- **Merge**:
  - `data_service.py`
  - `unified_data_service.py`
  - `price_cache_service.py`
- **Result**: One service for all market data operations

#### Task 5.2: Simplify Service Registry
- **Current**: Complex DI with lifecycle management
- **Target**: Simple service factory
- **File**: Create `src/services/service_factory.py`
```python
class ServiceFactory:
    _instances = {}
    
    @classmethod
    def get_service(cls, service_name: str):
        if service_name not in cls._instances:
            cls._instances[service_name] = cls._create_service(service_name)
        return cls._instances[service_name]
```

### Day 9: EventBus to Qt Signals Migration (Part 1)
**Priority: 🟡 MEDIUM - ARCHITECTURE**

#### Task 6.1: Create Qt Signal Manager
- **File**: `src/services/signal_manager.py`
- **Design**: Centralized Qt signals replacing EventBus
```python
class SignalManager(QObject):
    # Market data signals
    price_updated = pyqtSignal(str, dict)  # symbol, price_data
    
    # Connection signals  
    connection_status_changed = pyqtSignal(bool)
    
    # Order signals
    order_status_updated = pyqtSignal(dict)
```

#### Task 6.2: Identify High-Traffic Event Paths
- **Priority Migration**:
  1. Price updates (highest traffic)
  2. Connection status
  3. Order updates

### Day 10: Documentation & Verification
**Priority: 🟢 LOW - HOUSEKEEPING**

#### Task 7.1: Update Architecture Documentation
- **Files to Update**:
  - `CLAUDE.md` - New architecture state
  - `IMPLEMENTATION_TRACKER.md` - Mark Phase 0 progress
  - Create `ARCHITECTURE_CHANGES.md` - Document what changed

#### Task 7.2: Performance Baseline
- **Create Benchmarks**:
  - Current price fetch latency
  - Memory usage with 50 symbols
  - CPU usage patterns
- **File**: `benchmarks/baseline_metrics.py`

#### Task 7.3: Run Full Test Suite
- **Verify**:
  - All critical safety tests pass
  - No functionality regression
  - Performance within targets

## Success Criteria for Phase 0

### Safety Fixes ✓
- [ ] Risk calculator throws exceptions on failure
- [ ] Orders cannot proceed without risk validation
- [ ] Daily loss limit circuit breaker active
- [ ] All safety tests passing

### Architecture Simplification ✓
- [ ] 3 loggers → 1 unified logger
- [ ] Data services consolidated
- [ ] Service Registry simplified
- [ ] EventBus migration started

### Testing & Documentation ✓
- [ ] pytest installed and working
- [ ] Critical safety test suite complete
- [ ] Performance baseline established
- [ ] Documentation updated

## Risk Mitigation

### Rollback Strategy
1. Git tag before starting: `git tag pre-phase-0`
2. Feature flags for new behavior
3. Parallel run old and new services during migration
4. Comprehensive testing at each step

### Testing Strategy
1. Write tests BEFORE making changes (TDD)
2. Run tests after EVERY change
3. Manual testing with paper trading account
4. Never test with real money until Phase 0 complete

## Notes
- This plan prioritizes financial safety above all else
- Architecture changes are incremental and reversible
- Each task should be committed separately for easy rollback
- Update IMPLEMENTATION_TRACKER.md after each completed task