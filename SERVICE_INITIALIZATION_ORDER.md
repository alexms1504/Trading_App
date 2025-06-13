# Service Initialization Order Documentation

**Generated**: 2024-12-06  
**Purpose**: Document current service initialization order before refactoring

## Current Service Registration Order (main_window.py)

1. **unified_data_service** (as 'data')
   - Pre-instantiated global instance
   - Depends on: IB connection service
   
2. **AccountService** (as 'account')
   - Creates AccountManager internally
   - AccountManager creates AccountManagerService
   - Dependencies: IB connection (via wrapper)
   
3. **OrderService** (as 'order')
   - Dependencies: account service, risk service (lazy loaded)
   
4. **RiskService** (as 'risk')
   - Dependencies: account service (for buying power)

## Service Initialization Flow

```
main_window._init_services()
    ↓
1. Create service instances (not initialized yet)
    - account_service = AccountService()
    - order_service = OrderService()  
    - risk_service = RiskService()
    ↓
2. Register all services
    - ServiceRegistry.register_service(name, instance)
    ↓
3. Initialize all services (ServiceRegistry.initialize_all_services())
    - Calls each service's initialize() method
    - Services can access other services via registry
```

## Critical Dependencies

### AccountService Dependencies
- **Direct**: None at instantiation
- **Indirect**: AccountManager → AccountManagerService → IB connection
- **Used by**: RiskService, OrderService, UI Controllers

### Service Access Patterns
```python
# Services access each other via:
get_account_service()  # Helper function
ServiceRegistry.get_service('account')  # Direct registry access
```

### Event Bus Subscriptions
- AccountService: Currently uses callbacks, not event bus
- Need to preserve callback compatibility during refactoring

## Risk Areas for Refactoring

1. **Initialization Order**: OrderService and RiskService expect AccountService
2. **Lazy Loading**: Some services use lazy loading for circular dependency avoidance
3. **Multiple Instances**: Connection service creates its own AccountManager
4. **UI Controllers**: Expect specific AccountService interface

## Validation Commands

```bash
# Test current initialization
python test_account_services.py

# Verify service registry after changes
python -c "from src.services.service_registry import ServiceRegistry; print(ServiceRegistry()._services.keys())"
```

## Rollback Information

If initialization fails after refactoring:
1. Check service registration order hasn't changed
2. Verify all expected methods exist on consolidated service
3. Ensure IB connection is established before account service init
4. Check for missing event bus subscriptions