"""
Simplified Chart Updater
Provides chart updating functionality with synchronous fallback for reliability
"""

from src.utils.logger import logger


class NonBlockingChartMixin:
    """Mixin to add chart updating to existing chart widgets"""
    
    def init_non_blocking_updates(self):
        """Initialize chart updates (simplified implementation)"""
        logger.info("Chart updater initialized with synchronous fallback")
        
    def update_chart_non_blocking(self, data, symbol, timeframe, **kwargs):
        """Update chart using reliable synchronous method"""
        logger.debug("Using synchronous chart update for reliability")
        self._fallback_to_sync_chart_update(data, **kwargs)
            
    def _fallback_to_sync_chart_update(self, data, **kwargs):
        """Fallback to synchronous chart update"""
        try:
            if hasattr(self, 'chart_canvas') and self.chart_canvas and data:
                logger.debug("Updating chart with synchronous plotting")
                
                # Get symbol and timeframe from widget attributes
                symbol = getattr(self, 'current_symbol', 'UNKNOWN')
                timeframe = getattr(self, 'current_timeframe', '5m')
                
                self.chart_canvas.plot_candlestick_data(
                    data,
                    symbol,
                    timeframe,
                    show_emas=kwargs.get('show_emas', True),
                    show_smas=kwargs.get('show_smas', True),
                    show_vwap=kwargs.get('show_vwap', True)
                )
                
                logger.debug(f"Successfully rendered chart for {symbol} {timeframe} with {len(data)} bars")
                
                # Trigger price level restoration
                if hasattr(self, 'on_non_blocking_chart_complete'):
                    self.on_non_blocking_chart_complete()
        except Exception as e:
            logger.error(f"Chart update failed: {e}")
                
    def cleanup_non_blocking(self):
        """Cleanup chart updater (simplified - no resources to clean)"""
        logger.debug("Chart updater cleanup completed")