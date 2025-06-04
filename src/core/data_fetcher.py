"""
Data Fetcher
Handles real-time and historical market data from Interactive Brokers
"""

import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from ib_async import Stock, Contract, BarData, Ticker, util

from src.utils.logger import logger
from src.core.ib_connection import ib_connection_manager


class DataFetcher:
    """
    Handles market data fetching from IB
    Provides real-time prices and historical data for stop loss calculations
    """
    
    def __init__(self):
        """Initialize data fetcher"""
        self.ib_manager = ib_connection_manager
        self.active_subscriptions: Dict[str, Ticker] = {}
        
    async def get_latest_price_async(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest market price for a symbol
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            
        Returns:
            Dict with price data or None if failed
        """
        try:
            if not self.ib_manager.is_connected():
                logger.error("Not connected to IB for price fetch")
                return None
                
            ib = self.ib_manager.ib
            if not ib:
                logger.error("IB client not available")
                return None
                
            logger.info(f"Fetching latest price for {symbol}")
            
            # Create and qualify contract
            contract = Stock(symbol, 'SMART', 'USD')
            ib.qualifyContracts(contract)
            
            # Request market data
            ticker = ib.reqMktData(contract, '', False, False)
            
            # Wait for data to populate using async sleep
            await asyncio.sleep(0.5)  # Non-blocking wait
            
            # Extract price information
            price_data = {
                'symbol': symbol,
                'last': ticker.last if ticker.last else None,
                'bid': ticker.bid if ticker.bid else None,
                'ask': ticker.ask if ticker.ask else None,
                'close': ticker.close if ticker.close else None,
                'timestamp': datetime.now()
            }
            
            # Use the best available price
            latest_price = None
            if ticker.last and ticker.last > 0:
                latest_price = ticker.last
            elif ticker.close and ticker.close > 0:
                latest_price = ticker.close
            elif ticker.bid and ticker.ask:
                latest_price = (ticker.bid + ticker.ask) / 2
            
            price_data['latest_price'] = latest_price
            
            # Cancel market data to avoid accumulating subscriptions
            ib.cancelMktData(contract)
            
            if latest_price:
                logger.info(f"Latest price for {symbol}: ${latest_price:.2f}")
                return price_data
            else:
                logger.warning(f"No valid price data received for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching latest price for {symbol}: {str(e)}")
            return None
            
    async def get_historical_bars_async(self, symbol: str, duration: str = '1 D', 
                           bar_size: str = '5 mins', num_bars: int = 100) -> Optional[List[BarData]]:
        """
        Get historical bar data for a symbol
        
        Args:
            symbol: Stock symbol
            duration: Duration string (e.g., '1 D', '2 H')
            bar_size: Bar size (e.g., '1 min', '5 mins')
            num_bars: Maximum number of bars to return
            
        Returns:
            List of BarData objects or None if failed
        """
        try:
            if not self.ib_manager.is_connected():
                logger.error("Not connected to IB for historical data")
                return None
                
            ib = self.ib_manager.ib
            if not ib:
                logger.error("IB client not available")
                return None
                
            logger.info(f"Fetching historical bars for {symbol} ({duration}, {bar_size})")
            
            # Create and qualify contract
            contract = Stock(symbol, 'SMART', 'USD')
            ib.qualifyContracts(contract)
            
            # Calculate end time (current time)
            end_time = datetime.now()
            
            # Request historical data using async method
            bars = await ib.reqHistoricalDataAsync(
                contract,
                endDateTime=end_time,
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow='TRADES',
                useRTH=True,  # Regular Trading Hours only
                formatDate=1
            )
            
            if bars:
                # Limit to requested number of bars
                limited_bars = bars[-num_bars:] if len(bars) > num_bars else bars
                logger.info(f"Retrieved {len(limited_bars)} bars for {symbol}")
                return limited_bars
            else:
                logger.warning(f"No historical data received for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return None
            
    async def calculate_stop_loss_levels_async(self, symbol: str, current_price: float, 
                                 direction: str = 'BUY') -> Dict[str, float]:
        """
        Calculate various stop loss levels based on historical data
        
        Args:
            symbol: Stock symbol
            current_price: Current market price
            direction: 'BUY' or 'SELL'
            
        Returns:
            Dict with different stop loss options
        """
        try:
            logger.info(f"Calculating stop loss levels for {symbol}")
            
            stop_levels = {}
            
            # Get 5-minute bars for prior bar analysis
            bars_5min = await self.get_historical_bars_async(symbol, '1 D', '5 mins', 50)
            if bars_5min and len(bars_5min) >= 2:
                # Low of prior 5-min bar (most recent completed bar)
                prior_bar = bars_5min[-2]  # -1 is current incomplete bar, -2 is prior completed
                prior_low = prior_bar.low
                stop_levels['prior_5min_low'] = prior_low
                logger.info(f"Prior 5min bar low: ${prior_low:.2f}")
            
            # Get 1-day bars for day low analysis
            bars_1day = await self.get_historical_bars_async(symbol, '2 D', '1 day', 10)
            if bars_1day and len(bars_1day) >= 2:
                # Low of current day
                current_day = bars_1day[-1]
                day_low = current_day.low
                stop_levels['day_low'] = day_low
                logger.info(f"Day low: ${day_low:.2f}")
                
                # Low of prior day
                if len(bars_1day) >= 2:
                    prior_day = bars_1day[-2]
                    prior_day_low = prior_day.low
                    stop_levels['prior_day_low'] = prior_day_low
                    logger.info(f"Prior day low: ${prior_day_low:.2f}")
            
            # Calculate percentage-based stops
            if direction == 'BUY':
                stop_levels['2_percent'] = current_price * 0.98
                stop_levels['3_percent'] = current_price * 0.97
                stop_levels['5_percent'] = current_price * 0.95
            else:  # SELL
                stop_levels['2_percent'] = current_price * 1.02
                stop_levels['3_percent'] = current_price * 1.03
                stop_levels['5_percent'] = current_price * 1.05
            
            logger.info(f"Calculated {len(stop_levels)} stop loss levels for {symbol}")
            return stop_levels
            
        except Exception as e:
            logger.error(f"Error calculating stop loss levels for {symbol}: {str(e)}")
            return {}
            
    async def get_price_and_stops_async(self, symbol: str, direction: str = 'BUY') -> Optional[Dict[str, Any]]:
        """
        Get current price and calculate stop loss options in one call
        
        Args:
            symbol: Stock symbol
            direction: 'BUY' or 'SELL'
            
        Returns:
            Dict with price data and stop loss options
        """
        try:
            logger.info(f"Fetching price and stop levels for {symbol}")
            
            # Get current price
            price_data = await self.get_latest_price_async(symbol)
            if not price_data or not price_data.get('latest_price'):
                logger.error(f"Failed to get current price for {symbol}")
                return None
                
            current_price = price_data['latest_price']
            
            # Calculate stop loss levels
            stop_levels = await self.calculate_stop_loss_levels_async(symbol, current_price, direction)
            
            # Combine data
            result = {
                'symbol': symbol,
                'current_price': current_price,
                'price_data': price_data,
                'stop_levels': stop_levels,
                'direction': direction,
                'timestamp': datetime.now()
            }
            
            logger.info(f"Successfully fetched price and stops for {symbol}: ${current_price:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting price and stops for {symbol}: {str(e)}")
            return None
            
    def cleanup_subscriptions(self):
        """Clean up any active market data subscriptions"""
        try:
            if self.ib_manager.is_connected() and self.active_subscriptions:
                ib = self.ib_manager.ib
                for symbol, ticker in self.active_subscriptions.items():
                    try:
                        ib.cancelMktData(ticker.contract)
                        logger.info(f"Cancelled market data subscription for {symbol}")
                    except Exception as e:
                        logger.warning(f"Error cancelling subscription for {symbol}: {str(e)}")
                
                self.active_subscriptions.clear()
                
        except Exception as e:
            logger.error(f"Error cleaning up subscriptions: {str(e)}")
            
    # Synchronous wrapper methods for backwards compatibility
    def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for get_latest_price_async"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.get_latest_price_async(symbol))
        except Exception as e:
            logger.error(f"Error in sync price fetch: {str(e)}")
            return None
            
    def get_price_and_stops(self, symbol: str, direction: str = 'BUY') -> Optional[Dict[str, Any]]:
        """Get price and stops using synchronous method (works better with Qt)"""
        try:
            return self._get_price_and_stops_sync(symbol, direction)
                    
        except Exception as e:
            logger.error(f"Error in sync price and stops fetch: {str(e)}")
            logger.exception("Full traceback:")
            return None
            
            
    def _get_price_and_stops_sync(self, symbol: str, direction: str = 'BUY') -> Optional[Dict[str, Any]]:
        """Synchronous method for price and stops - works well with Qt"""
        try:
            if not self.ib_manager.is_connected():
                logger.error("Not connected to IB for price fetch")
                return None
                
            ib = self.ib_manager.ib
            if not ib:
                logger.error("IB client not available")
                return None
                
            # Get current price synchronously
            contract = Stock(symbol, 'SMART', 'USD')
            try:
                ib.qualifyContracts(contract)
            except Exception as e:
                logger.error(f"Error qualifying contract for {symbol}: {str(e)}")
                return None
            
            ticker = ib.reqMktData(contract, '', False, False)
            logger.info(f"Requested market data for {symbol}, waiting for data...")
            # Use incremental waiting for faster response
            ib.sleep(0.3)  # Initial short wait
            
            # Check if we have data
            if not (ticker.last or ticker.bid or ticker.ask or ticker.close):
                ib.sleep(0.3)  # Wait a bit more if no data
                
            # Final check
            if not (ticker.last or ticker.bid or ticker.ask or ticker.close):
                ib.sleep(0.2)  # Final wait - total 0.8s instead of 1.0s
            
            # Log ticker data
            logger.info(f"Ticker data for {symbol}: last={ticker.last}, bid={ticker.bid}, ask={ticker.ask}, close={ticker.close}")
            
            # Extract price
            current_price = None
            if ticker.last and ticker.last > 0:
                current_price = ticker.last
            elif ticker.close and ticker.close > 0:
                current_price = ticker.close
            elif ticker.bid and ticker.ask and ticker.bid > 0 and ticker.ask > 0:
                current_price = (ticker.bid + ticker.ask) / 2
                
            ib.cancelMktData(contract)
            
            if not current_price:
                logger.error(f"No valid price data for {symbol}")
                return None
                
            # Get historical bars synchronously for stop loss calculations
            stop_levels = {}
            
            try:
                # Get 5-minute bars for prior bar analysis
                logger.info(f"Fetching 5-minute bars for {symbol}")
                
                # Request bars up to current time to ensure we get the most recent data
                bars_5min = ib.reqHistoricalData(
                    contract,
                    endDateTime='',  # Empty string means "up to now"
                    durationStr='1 D',  # Get 1 day of data
                    barSizeSetting='5 mins',
                    whatToShow='TRADES',
                    useRTH=True,  # Regular trading hours only
                    formatDate=1,
                    keepUpToDate=False
                )
                
                logger.info(f"Received {len(bars_5min) if bars_5min else 0} 5-minute bars for {symbol}")
                
                if bars_5min and len(bars_5min) >= 1:
                    # Debug: Log ALL the bars to understand the data
                    logger.info("=== ALL 5-MINUTE BARS (last 10) ===")
                    logger.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Show the last 10 bars for debugging
                    start_idx = max(0, len(bars_5min) - 10)
                    for i, bar in enumerate(bars_5min[start_idx:]):
                        logger.info(f"Bar[{i}] Time: {bar.date} | O: {bar.open:.2f} | H: {bar.high:.2f} | L: {bar.low:.2f} | C: {bar.close:.2f} | V: {bar.volume}")
                    
                    # IMPORTANT: IB's historical data behavior:
                    # - If market is OPEN: Last bar may be incomplete (still forming)
                    # - If market is CLOSED: All bars are complete
                    # - The bars are ordered chronologically (oldest first, newest last)
                    
                    # For day trading, "prior 5-minute bar low" typically means:
                    # - During market hours: The low of the most recently COMPLETED 5-minute bar
                    # - After market close: The low of the last 5-minute bar of the trading day
                    
                    # Simple approach: Always use the second-to-last bar if we have at least 2 bars
                    # This ensures we're using a completed bar during market hours
                    if len(bars_5min) >= 2:
                        # Use -2 (second to last) as the "prior" completed bar
                        prior_bar = bars_5min[-2]
                        current_bar = bars_5min[-1]
                        
                        logger.info(f"Prior bar[-2]: {prior_bar.date} Low: ${prior_bar.low:.2f}")
                        logger.info(f"Current bar[-1] (may be incomplete): {current_bar.date} Low: ${current_bar.low:.2f}")
                        
                        # Store both prior and current 5min bar lows
                        stop_levels['prior_5min_low'] = prior_bar.low
                        stop_levels['current_5min_low'] = current_bar.low
                        
                        # Also store the absolute lowest of the last few bars as an option
                        recent_bars = bars_5min[-5:]  # Last 5 bars
                        lowest_recent = min(bar.low for bar in recent_bars)
                        stop_levels['recent_5min_low'] = lowest_recent
                        logger.info(f"Lowest of last 5 bars: ${lowest_recent:.2f}")
                        
                    else:
                        # Only 1 bar available
                        current_bar = bars_5min[-1]
                        stop_levels['current_5min_low'] = current_bar.low
                        stop_levels['prior_5min_low'] = current_bar.low  # Use same value
                        logger.warning(f"Only 1 bar available, using it: {current_bar.date} Low: ${current_bar.low:.2f}")
                    
                    logger.info(f"Prior 5min bar low set to: ${stop_levels['prior_5min_low']:.2f}")
                    
                else:
                    logger.warning(f"❌ No 5-min bar data received for {symbol}")
                    
            except Exception as hist_error:
                logger.error(f"❌ Error getting 5-min historical data for {symbol}: {hist_error}")
                logger.exception("Full traceback:")
                
            try:
                # Get daily bars for day low analysis
                logger.info(f"Fetching daily bars for {symbol}")
                bars_daily = ib.reqHistoricalData(
                    contract,
                    endDateTime='',
                    durationStr='5 D',  # Get 5 days to ensure we have current and prior day
                    barSizeSetting='1 day',
                    whatToShow='TRADES',
                    useRTH=True,
                    formatDate=1
                )
                
                logger.info(f"Received {len(bars_daily) if bars_daily else 0} daily bars for {symbol}")
                
                if bars_daily and len(bars_daily) >= 1:
                    # Debug: Log the daily bars
                    for i, bar in enumerate(bars_daily[-3:]):
                        logger.info(f"Daily Bar {len(bars_daily)-3+i}: {bar.date} O:{bar.open} H:{bar.high} L:{bar.low} C:{bar.close}")
                    
                    # Current day low
                    current_day = bars_daily[-1]
                    stop_levels['day_low'] = current_day.low
                    logger.info(f"Day low: ${current_day.low:.2f} (from {current_day.date})")
                    
                    # Prior day low
                    if len(bars_daily) >= 2:
                        prior_day = bars_daily[-2]
                        stop_levels['prior_day_low'] = prior_day.low
                        logger.info(f"Prior day low: ${prior_day.low:.2f} (from {prior_day.date})")
                else:
                    logger.warning(f"❌ Insufficient daily bar data for {symbol}: {len(bars_daily) if bars_daily else 0} bars")
                    
            except Exception as hist_error:
                logger.error(f"❌ Error getting daily historical data for {symbol}: {hist_error}")
                logger.exception("Full traceback:")
            
            # Add 2% percentage stop (for reference, but percentage is now adjustable in UI)
            if direction == 'BUY':
                stop_levels['2_percent'] = current_price * 0.98
            else:
                stop_levels['2_percent'] = current_price * 1.02
                
            # If no historical stop levels were calculated, add estimated ones as fallback
            if 'prior_5min_low' not in stop_levels and 'day_low' not in stop_levels:
                logger.warning(f"No historical data available for {symbol}, using estimated stop levels")
                if direction == 'BUY':
                    # Estimate reasonable stops below current price
                    stop_levels['estimated_5min_low'] = current_price * 0.995  # 0.5% below
                    stop_levels['estimated_day_low'] = current_price * 0.98    # 2% below
                else:
                    # For shorts, stops go above current price
                    stop_levels['estimated_5min_high'] = current_price * 1.005  # 0.5% above
                    stop_levels['estimated_day_high'] = current_price * 1.02    # 2% above
                
            # Log final stop levels calculated
            logger.info(f"Final stop levels for {symbol}: {list(stop_levels.keys())}")
            for level_name, level_price in stop_levels.items():
                logger.info(f"   {level_name}: ${level_price:.2f}")
                
            # Prepare result
            result = {
                'symbol': symbol,
                'current_price': current_price,
                'price_data': {
                    'symbol': symbol,
                    'last': ticker.last,
                    'bid': ticker.bid,
                    'ask': ticker.ask,
                    'close': ticker.close,
                    'latest_price': current_price,
                    'timestamp': datetime.now()
                },
                'stop_levels': stop_levels,
                'direction': direction,
                'timestamp': datetime.now()
            }
            
            logger.info(f"Successfully fetched price and stops for {symbol}: ${current_price:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching price and stops for {symbol}: {str(e)}")
            return None


# Create singleton instance
data_fetcher = DataFetcher()