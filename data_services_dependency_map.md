# Data Services Dependency Map

## Overview

This document maps all data service dependencies in the trading app, showing which components use which services and what methods they call.

## Service Architecture

### 1. UnifiedDataService (src/services/unified_data_service.py)
**Purpose**: Central consolidated service combining functionality from data_fetcher, data_service, and simple_threaded_fetcher

**Key Methods**:
- `fetch_price_data(symbol, direction)` - Non-blocking price fetch via QTimer
- `_fetch_price_and_stops_sync(symbol, direction)` - Synchronous price fetch
- `start_screening_async(criteria)` - Market screening operations
- `register_price_update_callback(callback)` - Backward compatibility
- `get_cached_stop_levels(symbol)`
- `clear_cache(symbol)`

**Dependencies**:
- `ib_connection_manager` - For IB API access
- `market_screener` - For screening operations
- `screener_price_cache` - For price caching
- EventBus - For publishing events

### 2. DataService (src/services/data_service.py)
**Status**: Legacy wrapper around UnifiedDataService
**Purpose**: Maintains backward compatibility

**Implementation**:
```python
class DataService:
    def __init__(self):
        self._unified_service = unified_data_service
```

All methods delegate to UnifiedDataService.

### 3. DataFetcher (src/core/data_fetcher.py)
**Status**: Legacy wrapper around UnifiedDataService
**Purpose**: Maintains backward compatibility for core components

**Key Methods**:
- `get_price_and_stops(symbol, direction)` - Delegates to `unified_data_service._fetch_price_and_stops_sync()`
- `cleanup_subscriptions()` - Delegates to unified service

### 4. ChartDataService (src/services/chart_data_service.py)
**Purpose**: Specialized service for chart data

**Dependencies**:
- `data_fetcher` - Uses `data_fetcher.ib_manager` for IB connection access
- Does NOT use data_fetcher for actual data fetching
- Implements its own `_get_historical_bars_sync()` method

**Key Methods**:
- `get_chart_data(symbol, timeframe, max_bars)` - Returns lightweight-charts format
- `_get_historical_bars_sync()` - Direct IB API calls for historical data

## Component Dependencies

### UI Components

#### 1. MainWindow (src/ui/main_window.py)
**Uses**: `DataService` (via service registry)
```python
data_service = DataService()
register_service('data', data_service)
```

#### 2. MarketDataController (src/ui/controllers/market_data_controller.py)
**Uses**: `DataService` (via `get_data_service()`)
**Methods Called**:
- `fetch_price_data(symbol, direction)`

#### 3. ChartWidgetEmbedded (src/ui/chart_widget_embedded.py)
**Uses**: `chart_data_manager` (legacy wrapper around ChartDataService)
**Methods Called**:
- `get_chart_data(symbol, timeframe, max_bars)`
- `get_available_timeframes()`
- `set_current_symbol(symbol)`
- `set_current_timeframe(timeframe)`

#### 4. MarketScreenerWidget (src/ui/market_screener.py)
**Uses**: `simple_threaded_market_screener` (from simple_threaded_fetcher.py)
**Methods Called**:
- `start_screening_async(criteria)`
- `refresh_results_async()`
- `fetch_real_prices_async()`
- `stop_screening_async()`

### Features

#### 1. DataManager (src/features/market_data/data_manager.py)
**Uses**: `unified_data_service` directly
**Methods Called**:
- `fetch_price_data(symbol, direction)`
- Connects to signals: `fetch_completed`, `fetch_failed`

### Legacy Wrappers

#### 1. SimpleThreadedDataFetcher (src/core/simple_threaded_fetcher.py)
**Status**: Legacy wrapper
**Delegates to**: `unified_data_service`
- Connects UnifiedDataService signals to its own signals
- `fetch_price_and_stops_async()` → `unified_data_service.fetch_price_data()`

#### 2. SimpleThreadedMarketScreener (src/core/simple_threaded_fetcher.py)
**Status**: Legacy wrapper
**Delegates to**: `unified_data_service` screening methods

## Dependency Tree

```
UnifiedDataService (Central Service)
├── DataService (Wrapper) 
│   └── Used by:
│       ├── MainWindow (via service registry)
│       └── MarketDataController (via get_data_service)
│
├── DataFetcher (Wrapper)
│   └── Used by:
│       └── ChartDataService (only for ib_manager access)
│
├── SimpleThreadedDataFetcher (Wrapper)
│   └── Used by:
│       └── (Legacy components if any)
│
├── SimpleThreadedMarketScreener (Wrapper)
│   └── Used by:
│       └── MarketScreenerWidget
│
└── Direct Usage:
    └── DataManager (features/market_data)

ChartDataService (Independent Service)
└── ChartDataManager (Wrapper)
    └── Used by:
        └── ChartWidgetEmbedded
```

## Safe Consolidation Opportunities

### 1. Replace DataService with UnifiedDataService
**Impact**: Minimal
- MainWindow: Change `DataService()` to `UnifiedDataService()`
- MarketDataController: Update `get_data_service()` to return UnifiedDataService
- Service Registry: Update type hints and imports

### 2. Remove DataFetcher Dependency from ChartDataService
**Current State**: ChartDataService only uses `data_fetcher.ib_manager`
**Solution**: 
```python
# Instead of:
self.data_fetcher = data_fetcher
ib = self.data_fetcher.ib_manager.ib

# Use:
from src.services.ib_connection_service import ib_connection_manager
self.ib_manager = ib_connection_manager
ib = self.ib_manager.ib
```

### 3. Update SimpleThreadedFetcher Users
**MarketScreenerWidget**: Can use UnifiedDataService directly
- Change imports and method calls
- UnifiedDataService already has all screening methods

### 4. Consolidate Service Registration
**Current**: Multiple wrapper services registered
**Proposed**: Register only UnifiedDataService and ChartDataService

## Circular Dependencies
**None Found**: The architecture uses proper service layers with no circular imports.

## Migration Path

1. **Phase 1**: Update ChartDataService to remove data_fetcher dependency
2. **Phase 2**: Update UI components to use UnifiedDataService directly
3. **Phase 3**: Remove legacy wrapper classes
4. **Phase 4**: Update service registry and type hints

## Summary

The data services can be safely consolidated by:
1. Using UnifiedDataService directly instead of DataService wrapper
2. Removing data_fetcher dependency from ChartDataService
3. Updating UI components to use UnifiedDataService
4. Removing all legacy wrapper classes

This will simplify the codebase while maintaining all functionality.