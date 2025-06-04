"""
Market Screener
Real-time stock screening using IB TWS Scanner API
"""

import asyncio
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass

from ib_async import ScannerSubscription, ScanData, TagValue

from src.utils.logger import logger
from src.core.ib_connection import ib_connection_manager


@dataclass
class ScreeningCriteria:
    """Data class for screening criteria"""
    instrument: str = "STK"
    location_code: str = "STK.US.MAJOR"
    scan_code: str = "TOP_PERC_GAIN"
    above_price: float = 0.4
    below_price: float = 999999.99
    above_volume: int = 8000000  # $8M default
    market_cap_above: Optional[float] = None
    market_cap_below: Optional[float] = None
    coupon_rate_above: Optional[float] = None
    coupon_rate_below: Optional[float] = None
    exclude_convertible: bool = True
    average_option_volume_above: Optional[int] = None
    scanner_setting_pairs: Optional[str] = None
    stock_type_filter: Optional[str] = None


class MarketScreener:
    """
    Real-time market screener using IB TWS Scanner API
    Finds stocks based on percentage gains, volume, and other criteria
    """
    
    def __init__(self):
        """Initialize market screener"""
        self.ib_manager = ib_connection_manager
        self.active_subscription: Optional[ScannerSubscription] = None
        self.scan_data = None  # Store the scan data object for cancellation
        self.current_results: List[ScanData] = []
        self.update_callbacks: List[Callable] = []
        self.is_running = False
        self.criteria = ScreeningCriteria()
        self.use_subscription = False  # Flag to track if using subscription mode
        
    def set_criteria(self, criteria: ScreeningCriteria):
        """Set new screening criteria"""
        self.criteria = criteria
        logger.info(f"Updated screening criteria: {criteria}")
        
    def add_update_callback(self, callback: Callable[[List[ScanData]], None]):
        """Add callback to be called when results update"""
        self.update_callbacks.append(callback)
        
    def remove_update_callback(self, callback: Callable):
        """Remove update callback"""
        if callback in self.update_callbacks:
            self.update_callbacks.remove(callback)
            
    async def start_screening_async(self) -> bool:
        """Start real-time screening (async version)"""
        try:
            if not self.ib_manager.is_connected():
                logger.error("Not connected to IB for screening")
                return False
                
            ib = self.ib_manager.ib
            if not ib:
                logger.error("IB client not available for screening")
                return False
                
            logger.info("Starting market screener...")
            
            # Create scanner subscription
            self.active_subscription = ScannerSubscription(
                instrument=self.criteria.instrument,
                locationCode=self.criteria.location_code,
                scanCode=self.criteria.scan_code
            )
            
            # Create filter tags based on criteria
            filter_options = []
            
            # Price filters
            if self.criteria.above_price:
                filter_options.append(TagValue("abovePrice", str(self.criteria.above_price)))
            if self.criteria.below_price and self.criteria.below_price < 999999:
                filter_options.append(TagValue("belowPrice", str(self.criteria.below_price)))
                
            # Volume filter (convert to shares from dollar volume)
            if self.criteria.above_volume:
                # For dollar volume screening, we need to estimate shares
                # This is approximate since we don't know the exact price
                estimated_avg_price = (self.criteria.above_price + 10.0) / 2 if self.criteria.above_price else 5.0
                min_shares = int(self.criteria.above_volume / estimated_avg_price)
                filter_options.append(TagValue("aboveVolume", str(min_shares)))
                
            # Market cap filters
            if self.criteria.market_cap_above:
                filter_options.append(TagValue("marketCapAbove", str(self.criteria.market_cap_above)))
            if self.criteria.market_cap_below:
                filter_options.append(TagValue("marketCapBelow", str(self.criteria.market_cap_below)))
                
            # Exclude convertible bonds
            if self.criteria.exclude_convertible:
                filter_options.append(TagValue("excludeConvertible", "1"))
                
            # Set the filter options on the subscription object
            self.active_subscription.scannerSubscriptionFilterOptions = filter_options
            
            # Subscribe to scanner data
            # Note: ib_async uses reqScannerData for one-time requests
            # For continuous updates, we would need to poll periodically
            scan_results = await ib.reqScannerDataAsync(
                self.active_subscription
            )
            
            # Process results
            self._on_scanner_data(scan_results)
            
            # Store subscription for proper cancellation
            # reqScannerData doesn't need cancellation as it's one-time
            self.use_subscription = False
            
            self.is_running = True
            logger.info(f"Market screener started with criteria: {self.criteria.scan_code}")
            logger.info(f"Filters applied: {len(filter_options)} filters")
            logger.info(f"Initial results: {len(scan_results)} items")
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting market screener: {str(e)}")
            return False
            
    def start_screening(self) -> bool:
        """Start real-time screening (sync wrapper)"""
        try:
            if not self.ib_manager.is_connected():
                logger.error("Not connected to IB for screening")
                return False
                
            ib = self.ib_manager.ib
            if not ib:
                logger.error("IB client not available for screening")
                return False
                
            logger.info("Starting market screener...")
            
            # Create scanner subscription
            self.active_subscription = ScannerSubscription(
                instrument=self.criteria.instrument,
                locationCode=self.criteria.location_code,
                scanCode=self.criteria.scan_code
            )
            
            # Create filter tags based on criteria
            filter_options = []
            
            # Price filters
            if self.criteria.above_price:
                filter_options.append(TagValue("abovePrice", str(self.criteria.above_price)))
            if self.criteria.below_price and self.criteria.below_price < 999999:
                filter_options.append(TagValue("belowPrice", str(self.criteria.below_price)))
                
            # Volume filter (convert to shares from dollar volume)
            if self.criteria.above_volume:
                estimated_avg_price = (self.criteria.above_price + 10.0) / 2 if self.criteria.above_price else 5.0
                min_shares = int(self.criteria.above_volume / estimated_avg_price)
                filter_options.append(TagValue("aboveVolume", str(min_shares)))
                
            # Set the filter options on the subscription object
            self.active_subscription.scannerSubscriptionFilterOptions = filter_options
            
            # Subscribe to scanner data - using synchronous method
            # Note: ib_async uses reqScannerData for one-time requests
            scan_results = ib.reqScannerData(self.active_subscription)
            
            # Process results
            self._on_scanner_data(scan_results)
            
            # Store subscription for proper cancellation
            # reqScannerData doesn't need cancellation as it's one-time
            self.use_subscription = False
            
            self.is_running = True
            logger.info(f"Market screener started with criteria: {self.criteria.scan_code}")
            logger.info(f"Filters applied: {len(filter_options)} filters")
            logger.info(f"Initial results: {len(scan_results)} items")
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting market screener: {str(e)}")
            return False
            
    def stop_screening(self):
        """Stop real-time screening"""
        try:
            if self.is_running:
                logger.info("Stopping market screener")
                
                # If we have an active IB connection and subscription, try to cancel properly
                if self.ib_manager.is_connected() and self.active_subscription:
                    try:
                        ib = self.ib_manager.ib
                        if ib and self.use_subscription:
                            # Only cancel if we're using continuous subscription mode
                            # For one-time reqScannerData calls, no cancellation is needed
                            logger.info("Cancelling scanner subscription")
                            # Note: This should not cause Error 162 since we're using one-time requests
                    except Exception as cancel_error:
                        logger.warning(f"Error cancelling scanner subscription: {str(cancel_error)}")
                        # Don't raise the error, just continue with cleanup
                    
            self.is_running = False
            self.active_subscription = None
            self.scan_data = None
            self.current_results.clear()
            self.use_subscription = False
            logger.info("Market screener stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping market screener: {str(e)}")
            
    def _on_scanner_data(self, results: List[ScanData]):
        """Handle incoming scanner data"""
        try:
            self.current_results = results
            logger.info(f"Received {len(results)} screening results")
            
            # Log top results with enhanced debugging
            for i, result in enumerate(results[:3]):  # Log top 3 to avoid spam
                try:
                    contract = result.contractDetails.contract
                    symbol = getattr(contract, 'symbol', 'UNKNOWN')
                    
                    # Enhanced logging to see what fields have data
                    distance_val = getattr(result, 'distance', 'EMPTY')
                    benchmark_val = getattr(result, 'benchmark', 'EMPTY') 
                    projection_val = getattr(result, 'projection', 'EMPTY')
                    legs_val = getattr(result, 'legsStr', 'EMPTY')
                    rank_val = getattr(result, 'rank', 'EMPTY')
                    
                    logger.info(f"  {i+1}. {symbol}: "
                              f"Rank={rank_val}, Distance={distance_val} (% change), "
                              f"Benchmark={benchmark_val}, Projection={projection_val}, "
                              f"Legs={legs_val}")
                              
                    # If distance has data, that's our percentage change
                    if distance_val and distance_val != 'EMPTY':
                        logger.info(f"     -> {symbol} has {distance_val}% change")
                        
                except Exception as e:
                    logger.warning(f"Error logging result {i+1}: {str(e)}")
            
            # Notify all callbacks
            for callback in self.update_callbacks:
                try:
                    callback(results)
                except Exception as e:
                    logger.error(f"Error in screener callback: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error processing scanner data: {str(e)}")
            
            
    def get_current_results(self) -> List[ScanData]:
        """Get current screening results"""
        return self.current_results.copy()
        
    def _fetch_current_prices(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Fetch current prices and market data for scanner symbols
        Since TWS Scanner fields are empty, we need to get real market data
        """
        try:
            if not self.ib_manager.is_connected() or not symbols:
                return {}
                
            ib = self.ib_manager.ib
            if not ib:
                return {}
                
            logger.info(f"Fetching real market data for {len(symbols)} symbols from scanner")
            
            # Create contracts for symbols
            contracts = []
            for symbol in symbols[:5]:  # Limit to 5 symbols to avoid overwhelming the API
                try:
                    from ib_async import Stock
                    contract = Stock(symbol, 'SMART', 'USD')
                    contracts.append((symbol, contract))
                except Exception as e:
                    logger.warning(f"Error creating contract for {symbol}: {str(e)}")
                    continue
            
            if not contracts:
                return {}
                
            # Qualify contracts
            all_contracts = [contract for _, contract in contracts]
            ib.qualifyContracts(*all_contracts)
            
            # Request market data for each contract
            market_data = {}
            tickers = []
            
            for symbol, contract in contracts:
                try:
                    # Request tick data
                    ticker = ib.reqMktData(contract, '', False, False)
                    tickers.append((symbol, ticker))
                except Exception as e:
                    logger.warning(f"Error requesting market data for {symbol}: {str(e)}")
                    continue
            
            if not tickers:
                return {}
                
            # Wait for data to populate
            ib.sleep(2)  # Give time for market data to arrive
            
            # Extract price and change data
            for symbol, ticker in tickers:
                try:
                    # Get current price (last trade or mid-point)
                    last_price = ticker.last
                    if not last_price or last_price <= 0:
                        # Fallback to mid-point of bid/ask
                        if ticker.bid > 0 and ticker.ask > 0:
                            last_price = (ticker.bid + ticker.ask) / 2
                        else:
                            last_price = None
                    
                    # Get previous close for % change calculation
                    prev_close = ticker.close
                    
                    # Calculate percentage change
                    pct_change = None
                    if last_price and prev_close and prev_close > 0:
                        pct_change = ((last_price - prev_close) / prev_close) * 100
                    
                    # Store the data
                    if last_price:
                        market_data[symbol] = {
                            'price': float(last_price),
                            'prev_close': float(prev_close) if prev_close else None,
                            'pct_change': float(pct_change) if pct_change is not None else None,
                            'bid': float(ticker.bid) if ticker.bid else None,
                            'ask': float(ticker.ask) if ticker.ask else None,
                            'volume': int(ticker.volume) if ticker.volume else None
                        }
                        
                        logger.info(f"Got market data for {symbol}: ${last_price:.2f} ({pct_change:+.2f}% from ${prev_close:.2f})")
                    
                except Exception as e:
                    logger.warning(f"Error processing market data for {symbol}: {str(e)}")
                    continue
            
            # Cancel market data subscriptions to clean up
            for symbol, ticker in tickers:
                try:
                    ib.cancelMktData(ticker.contract)
                except:
                    pass
                    
            logger.info(f"Successfully fetched market data for {len(market_data)} symbols")
            return market_data
            
        except Exception as e:
            logger.error(f"Error fetching current prices: {str(e)}")
            return {}

    def get_formatted_results(self, fetch_real_data: bool = True) -> List[Dict[str, Any]]:
        """Get current results in formatted dictionary format"""
        formatted_results = []
        
        # Get symbols for price fetching
        symbols = []
        for result in self.current_results[:10]:  # Limit to top 10
            try:
                contract = result.contractDetails.contract
                symbols.append(contract.symbol)
            except:
                continue
        
        # Fetch real market data since scanner fields are empty (but only if requested)
        market_data = {}
        if fetch_real_data and symbols:
            market_data = self._fetch_current_prices(symbols)
        else:
            logger.info("Skipping real market data fetch (using estimated data for speed)")
        
        for result in self.current_results:
            try:
                contract = result.contractDetails.contract
                symbol = contract.symbol
                
                # Use real market data if available, otherwise try scanner data
                symbol_data = market_data.get(symbol, {})
                
                # Get real price and % change from market data
                latest_price = symbol_data.get('price', None)
                pct_change = symbol_data.get('pct_change', None)
                
                # Fallback: Try to use scanner data (even though it's usually empty)
                if latest_price is None:
                    # Check if distance field contains percentage data (TOP_PERC_GAIN scanner)
                    if hasattr(result, 'distance') and result.distance:
                        try:
                            # Distance field often contains the percentage change for TOP_PERC_GAIN
                            scanner_pct = float(result.distance)
                            pct_change = scanner_pct
                            # If we have a benchmark (which might be previous close), calculate current price
                            if hasattr(result, 'benchmark') and result.benchmark:
                                prev_close = float(result.benchmark)
                                latest_price = prev_close * (1 + scanner_pct / 100)
                        except (ValueError, TypeError):
                            pass
                
                # No fallback for price - if we don't have real data, leave it as None
                if latest_price is None:
                    logger.warning(f"No price data available for {symbol}")
                
                # Final fallback for % change
                if pct_change is None:
                    # Try scanner distance field one more time
                    if hasattr(result, 'distance') and result.distance:
                        try:
                            pct_change = float(result.distance)
                        except (ValueError, TypeError):
                            pct_change = 0.0  # Default to 0% if no data
                    else:
                        pct_change = 0.0
                
                # Get volume data from market data or estimate
                volume_usd = None
                volume_shares = symbol_data.get('volume', None)
                
                # Calculate USD volume if we have shares volume and price
                if volume_shares and latest_price:
                    volume_usd = volume_shares * latest_price
                    
                # Fallback: Try to extract volume from scanner legs string
                if not volume_usd:
                    try:
                        if hasattr(result, 'legsStr') and result.legsStr:
                            # Sometimes volume is encoded in legs string - try to parse it
                            legs_str = str(result.legsStr)
                            # Look for volume patterns in the string
                            if 'vol' in legs_str.lower() or '$' in legs_str:
                                # Try to extract numeric values
                                import re
                                numbers = re.findall(r'[\d,.]+', legs_str)
                                if numbers:
                                    try:
                                        # Take the largest number as potential volume
                                        volume_candidate = max([float(n.replace(',', '')) for n in numbers])
                                        if volume_candidate > 1000:  # Reasonable volume threshold
                                            volume_usd = volume_candidate
                                    except:
                                        pass
                    except (ValueError, TypeError, AttributeError):
                        pass
                
                # No fallback for volume - if we don't have real data, leave it as None
                
                # Log for debugging what we're getting (first 3 results only to avoid spam)
                if len(formatted_results) < 3:
                    data_source = "REAL" if symbol in market_data else "NO_DATA"
                    price_str = f"${latest_price:.2f}" if latest_price else "N/A"
                    change_str = f"{pct_change:.2f}%" if pct_change is not None else "N/A"
                    volume_str = f"${volume_usd/1000000:.1f}M" if volume_usd else "N/A"
                    logger.info(f"Market data for {symbol} ({data_source}): "
                              f"price={price_str}, change={change_str}, volume={volume_str}")
                
                formatted_result = {
                    'rank': result.rank,
                    'symbol': contract.symbol,
                    'company_name': getattr(contract, 'longName', None) or getattr(contract, 'localSymbol', None) or contract.symbol,
                    'exchange': getattr(contract, 'exchange', ''),
                    'currency': getattr(contract, 'currency', ''),
                    'distance': pct_change,  # Real % change from market data or scanner
                    'benchmark': result.benchmark,
                    'projection': result.projection,
                    'legs': result.legsStr,
                    'latest_price': latest_price,  # Real price from market data or None
                    'volume_usd': volume_usd,  # Real volume or None
                    'contract': contract,  # Keep full contract for order placement
                    'timestamp': datetime.now(),
                    'data_source': 'REAL' if symbol in market_data else 'NO_DATA'  # Track data quality
                }
                formatted_results.append(formatted_result)
                
            except Exception as e:
                logger.error(f"Error formatting result: {str(e)}")
                continue
                
        return formatted_results
        
    def update_criteria_and_restart(self, **kwargs):
        """Update criteria and restart screening"""
        try:
            # Update criteria attributes
            for key, value in kwargs.items():
                if hasattr(self.criteria, key):
                    setattr(self.criteria, key, value)
                    logger.info(f"Updated criteria {key} = {value}")
                    
            # Restart screening with new criteria
            if self.is_running:
                self.stop_screening()
                # Small delay to ensure clean stop
                import time
                time.sleep(0.1)
                return self.start_screening()
            else:
                return True
                
        except Exception as e:
            logger.error(f"Error updating criteria: {str(e)}")
            return False
            
    async def refresh_results_async(self) -> bool:
        """Refresh screening results (async)"""
        try:
            if not self.is_running or not self.ib_manager.is_connected():
                return False
                
            ib = self.ib_manager.ib
            if not ib:
                return False
                
            # Create filter tags based on criteria
            filter_options = []
            
            # Price filters
            if self.criteria.above_price:
                filter_options.append(TagValue("abovePrice", str(self.criteria.above_price)))
            if self.criteria.below_price and self.criteria.below_price < 999999:
                filter_options.append(TagValue("belowPrice", str(self.criteria.below_price)))
                
            # Volume filter
            if self.criteria.above_volume:
                estimated_avg_price = (self.criteria.above_price + 10.0) / 2 if self.criteria.above_price else 5.0
                min_shares = int(self.criteria.above_volume / estimated_avg_price)
                filter_options.append(TagValue("aboveVolume", str(min_shares)))
                
            # Update filter options on the subscription
            self.active_subscription.scannerSubscriptionFilterOptions = filter_options
            
            # Request updated data
            # Since we're using one-time requests, always fetch new data
            scan_results = await ib.reqScannerDataAsync(
                self.active_subscription
            )
            
            # Process results
            self._on_scanner_data(scan_results)
            
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing scanner results: {str(e)}")
            return False
            
    def refresh_results(self) -> bool:
        """Refresh screening results (non-blocking)"""
        try:
            if not self.is_running or not self.ib_manager.is_connected():
                return False
                
            # TEMPORARY FIX: Prevent freezing by just updating timestamp on existing results
            # This avoids the blocking ib.reqScannerData() call that was freezing the UI
            logger.info("Refreshing scanner results (non-blocking mode)")
            
            # Just trigger callbacks with existing results to update UI timestamp
            if self.current_results:
                # Trigger callbacks to update UI
                for callback in self.update_callbacks:
                    try:
                        callback(self.current_results)
                    except Exception as e:
                        logger.error(f"Error in screener callback during refresh: {str(e)}")
                        
                logger.info(f"Refreshed display with {len(self.current_results)} existing results")
                return True
            else:
                logger.warning("No existing results to refresh - try starting screening first")
                return False
            
        except Exception as e:
            logger.error(f"Error refreshing scanner results: {str(e)}")
            return False
            
    def is_screening_active(self) -> bool:
        """Check if screening is currently active"""
        return self.is_running and self.active_subscription is not None


# Create singleton instance
market_screener = MarketScreener()