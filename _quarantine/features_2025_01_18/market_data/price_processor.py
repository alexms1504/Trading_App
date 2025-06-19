"""
Price Processor
Processes raw price data into actionable trading information
"""

from typing import Dict, Optional, List
from datetime import datetime

from src.utils.logger import logger
from config import TRADING_CONFIG


class PriceProcessor:
    """Processes raw price data for trading decisions"""
    
    def __init__(self):
        self.stop_loss_buffer = TRADING_CONFIG.get('stop_loss_buffer_percent', 0.2) / 100
        
    def process_price_data(self, raw_data: dict, direction: str = 'BUY') -> dict:
        """
        Process raw price data into trading-ready format
        
        Args:
            raw_data: Raw price data from fetcher
            direction: Trade direction for calculations
            
        Returns:
            Processed price data dictionary
        """
        try:
            symbol = raw_data.get('symbol', '')
            price_data = raw_data.get('price_data', {})
            stop_levels = raw_data.get('stop_levels', {})
            
            # Extract current price
            current_price = self._extract_current_price(price_data)
            
            # Calculate entry price based on direction
            entry_price = self._calculate_entry_price(price_data, current_price, direction)
            
            # Calculate stop loss
            stop_loss = self._calculate_stop_loss(stop_levels, entry_price, direction)
            
            # Calculate take profit (2:1 risk/reward)
            take_profit = self._calculate_take_profit(entry_price, stop_loss, direction)
            
            # Build processed data
            processed = {
                'symbol': symbol,
                'current_price': current_price,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'direction': direction,
                'stop_levels': stop_levels,
                'bid': price_data.get('bid', current_price - 0.01),
                'ask': price_data.get('ask', current_price + 0.01),
                'last': price_data.get('last', current_price),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Processed price data for {symbol}: Entry=${entry_price:.2f}, "
                       f"Stop=${stop_loss:.2f}, Target=${take_profit:.2f}")
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing price data: {str(e)}")
            raise
            
    def _extract_current_price(self, price_data: dict) -> float:
        """Extract current price from price data"""
        # Priority: last > mid > average of bid/ask
        if 'last' in price_data and price_data['last'] > 0:
            return price_data['last']
        elif 'mid' in price_data and price_data['mid'] > 0:
            return price_data['mid']
        elif 'bid' in price_data and 'ask' in price_data:
            bid = price_data['bid']
            ask = price_data['ask']
            if bid > 0 and ask > 0:
                return (bid + ask) / 2
        
        # Fallback
        return price_data.get('close', 0)
        
    def _calculate_entry_price(self, price_data: dict, current_price: float, 
                              direction: str) -> float:
        """Calculate entry price based on direction"""
        if direction == 'BUY':
            # For buying, use ask if available
            if 'ask' in price_data and price_data['ask'] > 0:
                return price_data['ask']
        else:  # SELL
            # For selling, use bid if available
            if 'bid' in price_data and price_data['bid'] > 0:
                return price_data['bid']
                
        # Fallback to current price
        return current_price
        
    def _calculate_stop_loss(self, stop_levels: dict, entry_price: float, 
                           direction: str) -> float:
        """Calculate stop loss with smart adjustments"""
        if direction == 'BUY':
            # For LONG: use lower of prior and current 5min lows
            prior_5min = stop_levels.get('prior_5min_low')
            current_5min = stop_levels.get('current_5min_low')
            
            if prior_5min and current_5min:
                raw_stop = min(prior_5min, current_5min)
            elif prior_5min:
                raw_stop = prior_5min
            elif current_5min:
                raw_stop = current_5min
            else:
                # 2% stop fallback
                raw_stop = stop_levels.get('2_percent', entry_price * 0.98)
                
            # Apply smart adjustment
            adjusted_stop = self._apply_smart_stop_adjustment(raw_stop, entry_price, 'BUY')
            
        else:  # SELL
            # For SHORT: use higher of prior and current 5min highs
            prior_5min = stop_levels.get('prior_5min_high')
            current_5min = stop_levels.get('current_5min_high')
            
            if prior_5min and current_5min:
                raw_stop = max(prior_5min, current_5min)
            elif prior_5min:
                raw_stop = prior_5min
            elif current_5min:
                raw_stop = current_5min
            else:
                # 2% stop fallback
                raw_stop = stop_levels.get('2_percent', entry_price * 1.02)
                
            # Apply smart adjustment
            adjusted_stop = self._apply_smart_stop_adjustment(raw_stop, entry_price, 'SELL')
            
        return adjusted_stop
        
    def _apply_smart_stop_adjustment(self, stop_price: float, entry_price: float, 
                                   direction: str) -> float:
        """Apply smart stop loss adjustments"""
        try:
            # Calculate stop distance percentage
            stop_distance_pct = abs(stop_price - entry_price) / entry_price
            
            # If stop is too tight (< 0.3%), add buffer
            if stop_distance_pct < 0.003:
                buffer_amount = entry_price * self.stop_loss_buffer
                if direction == 'BUY':
                    adjusted = stop_price - buffer_amount
                else:  # SELL
                    adjusted = stop_price + buffer_amount
                    
                logger.info(f"Stop too tight ({stop_distance_pct:.2%}), "
                          f"adjusted from ${stop_price:.4f} to ${adjusted:.4f}")
                return adjusted
                
            # If stop is reasonable, return as-is
            return stop_price
            
        except Exception as e:
            logger.error(f"Error in stop adjustment: {str(e)}")
            return stop_price
            
    def _calculate_take_profit(self, entry_price: float, stop_loss: float, 
                             direction: str, risk_reward: float = 2.0) -> float:
        """Calculate take profit based on risk/reward ratio"""
        risk_distance = abs(entry_price - stop_loss)
        
        if direction == 'BUY':
            take_profit = entry_price + (risk_distance * risk_reward)
        else:  # SELL
            take_profit = entry_price - (risk_distance * risk_reward)
            
        # Ensure reasonable bounds
        return max(0.01, min(10000.0, take_profit))
        
    def calculate_price_levels(self, entry: float, risk_percent: float = 2.0) -> dict:
        """Calculate standard price levels for a given entry"""
        return {
            'entry': entry,
            'stop_2_percent': entry * (1 - risk_percent / 100),
            'target_2_1': entry * (1 + (risk_percent * 2) / 100),
            'target_3_1': entry * (1 + (risk_percent * 3) / 100),
            'target_5_1': entry * (1 + (risk_percent * 5) / 100)
        }