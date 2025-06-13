"""
Market Scanner
Scans markets for trading opportunities
"""

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from src.core.market_screener import MarketScreener as CoreScreener
from src.services.event_bus import EventType, Event, publish_event
from src.utils.logger import logger


class ScanType(Enum):
    """Types of market scans"""
    VOLUME_SPIKE = "volume_spike"
    PRICE_BREAKOUT = "price_breakout"
    GAP_UP = "gap_up"
    GAP_DOWN = "gap_down"
    NEW_HIGH = "new_high"
    NEW_LOW = "new_low"
    MOMENTUM = "momentum"
    

@dataclass
class ScanResult:
    """Result from a market scan"""
    symbol: str
    scan_type: ScanType
    score: float
    price: float
    volume: int
    change_percent: float
    details: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
            

class MarketScanner:
    """Enhanced market scanner with filtering and alerts"""
    
    def __init__(self):
        self.core_screener = CoreScreener()
        self.scan_callbacks: List[Callable[[List[ScanResult]], None]] = []
        self.active_scans: Dict[ScanType, bool] = {}
        self.last_results: Dict[ScanType, List[ScanResult]] = {}
        
    def add_scan_callback(self, callback: Callable[[List[ScanResult]], None]):
        """Add callback for scan results"""
        if callback not in self.scan_callbacks:
            self.scan_callbacks.append(callback)
            
    def remove_scan_callback(self, callback: Callable[[List[ScanResult]], None]):
        """Remove scan callback"""
        if callback in self.scan_callbacks:
            self.scan_callbacks.remove(callback)
            
    def start_scan(self, scan_type: ScanType, interval_seconds: int = 60):
        """Start a periodic scan"""
        if scan_type not in self.active_scans:
            self.active_scans[scan_type] = True
            logger.info(f"Started {scan_type.value} scan (interval: {interval_seconds}s)")
            # TODO: Implement periodic scanning with threading/async
            
    def stop_scan(self, scan_type: ScanType):
        """Stop a periodic scan"""
        if scan_type in self.active_scans:
            self.active_scans[scan_type] = False
            logger.info(f"Stopped {scan_type.value} scan")
            
    def scan_volume_spikes(self, min_volume: int = 1000000, 
                          volume_multiplier: float = 2.0) -> List[ScanResult]:
        """Scan for volume spikes"""
        try:
            # Use core screener to get stocks
            stocks = self.core_screener.find_stocks(
                min_volume=min_volume,
                sort_by='volume'
            )
            
            results = []
            for stock in stocks[:20]:  # Top 20 by volume
                # Check if volume is significantly above average
                if stock.get('avgVolume', 0) > 0:
                    volume_ratio = stock['volume'] / stock['avgVolume']
                    if volume_ratio >= volume_multiplier:
                        result = ScanResult(
                            symbol=stock['symbol'],
                            scan_type=ScanType.VOLUME_SPIKE,
                            score=volume_ratio,
                            price=stock.get('lastPrice', 0),
                            volume=stock['volume'],
                            change_percent=stock.get('changePercent', 0),
                            details={
                                'volume_ratio': volume_ratio,
                                'avg_volume': stock['avgVolume']
                            }
                        )
                        results.append(result)
                        
            # Store and notify
            self.last_results[ScanType.VOLUME_SPIKE] = results
            self._notify_scan_results(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error scanning volume spikes: {str(e)}")
            return []
            
    def scan_price_breakouts(self, min_price: float = 5.0, 
                           min_change: float = 3.0) -> List[ScanResult]:
        """Scan for price breakouts"""
        try:
            # Find stocks with significant price moves
            stocks = self.core_screener.find_stocks(
                min_price=min_price,
                min_change_percent=min_change,
                sort_by='changePercent'
            )
            
            results = []
            for stock in stocks[:20]:  # Top 20 movers
                change_pct = stock.get('changePercent', 0)
                if abs(change_pct) >= min_change:
                    result = ScanResult(
                        symbol=stock['symbol'],
                        scan_type=ScanType.PRICE_BREAKOUT,
                        score=abs(change_pct),
                        price=stock.get('lastPrice', 0),
                        volume=stock.get('volume', 0),
                        change_percent=change_pct,
                        details={
                            'day_high': stock.get('dayHigh', 0),
                            'day_low': stock.get('dayLow', 0),
                            'breakout_direction': 'UP' if change_pct > 0 else 'DOWN'
                        }
                    )
                    results.append(result)
                    
            # Store and notify
            self.last_results[ScanType.PRICE_BREAKOUT] = results
            self._notify_scan_results(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error scanning breakouts: {str(e)}")
            return []
            
    def scan_gaps(self, min_gap_percent: float = 2.0) -> List[ScanResult]:
        """Scan for gap ups and downs"""
        try:
            results = []
            
            # Get all active stocks
            stocks = self.core_screener.find_stocks(min_price=1.0)
            
            for stock in stocks:
                if 'previousClose' in stock and stock['previousClose'] > 0:
                    open_price = stock.get('open', 0)
                    prev_close = stock['previousClose']
                    
                    if open_price > 0:
                        gap_percent = ((open_price - prev_close) / prev_close) * 100
                        
                        if abs(gap_percent) >= min_gap_percent:
                            scan_type = ScanType.GAP_UP if gap_percent > 0 else ScanType.GAP_DOWN
                            
                            result = ScanResult(
                                symbol=stock['symbol'],
                                scan_type=scan_type,
                                score=abs(gap_percent),
                                price=stock.get('lastPrice', 0),
                                volume=stock.get('volume', 0),
                                change_percent=stock.get('changePercent', 0),
                                details={
                                    'gap_percent': gap_percent,
                                    'open': open_price,
                                    'previous_close': prev_close
                                }
                            )
                            results.append(result)
                            
            # Sort by gap size
            results.sort(key=lambda x: x.score, reverse=True)
            
            # Store results by type
            gap_ups = [r for r in results if r.scan_type == ScanType.GAP_UP]
            gap_downs = [r for r in results if r.scan_type == ScanType.GAP_DOWN]
            
            self.last_results[ScanType.GAP_UP] = gap_ups[:10]
            self.last_results[ScanType.GAP_DOWN] = gap_downs[:10]
            
            # Notify
            self._notify_scan_results(results[:20])
            
            return results[:20]
            
        except Exception as e:
            logger.error(f"Error scanning gaps: {str(e)}")
            return []
            
    def get_last_results(self, scan_type: Optional[ScanType] = None) -> List[ScanResult]:
        """Get last scan results"""
        if scan_type:
            return self.last_results.get(scan_type, [])
        else:
            # Return all results
            all_results = []
            for results in self.last_results.values():
                all_results.extend(results)
            return all_results
            
    def _notify_scan_results(self, results: List[ScanResult]):
        """Notify callbacks of scan results"""
        for callback in self.scan_callbacks:
            try:
                callback(results)
            except Exception as e:
                logger.error(f"Error in scan callback: {str(e)}")
                
        # Publish event
        if results:
            publish_event(Event(
                EventType.MARKET_SCAN_COMPLETE,
                {
                    'scan_count': len(results),
                    'top_symbols': [r.symbol for r in results[:5]],
                    'timestamp': datetime.now().isoformat()
                }
            ))