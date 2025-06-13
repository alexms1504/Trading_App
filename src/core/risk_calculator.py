"""
Risk Calculator
Handles position sizing, risk calculations, and trade validation
"""

from typing import Dict, Tuple, Optional
from decimal import Decimal, ROUND_DOWN
import math

from src.utils.logger import logger
from config import TRADING_CONFIG


class RiskCalculator:
    """
    Calculates position sizes and validates trades based on risk parameters
    """
    
    def __init__(self, account_manager):
        """
        Initialize risk calculator
        
        Args:
            account_manager: AccountManager instance for account data
        """
        self.account_manager = account_manager
        self.default_risk_percent = TRADING_CONFIG['default_risk_percent']
        self.max_risk_percent = TRADING_CONFIG['max_risk_percent']
        self.min_stop_distance = TRADING_CONFIG['min_stop_distance']
        self.max_position_percent = TRADING_CONFIG['max_position_percent']
        
    def calculate_position_size(self, 
                              entry_price: float,
                              stop_loss: float,
                              risk_percent: float,
                              account: Optional[str] = None,
                              order_type: str = 'LMT',
                              limit_price: Optional[float] = None) -> Dict[str, float]:
        """
        Calculate position size based on risk parameters
        
        Args:
            entry_price: Entry price per share (stop price for STOP LIMIT)
            stop_loss: Stop loss price per share
            risk_percent: Risk percentage of account (e.g., 0.3 for 0.3%)
            account: Account ID (uses active if None)
            order_type: Order type ('LMT', 'MKT', 'STOPLMT')
            limit_price: Limit price for STOP LIMIT orders
            
        Returns:
            Dictionary with calculation results:
            - shares: Number of shares
            - position_value: Total position value
            - dollar_risk: Dollar amount at risk
            - risk_per_share: Risk per share
            - account_value: Account value used
            - margin_required: Estimated margin requirement
        """
        # Get account value
        account_value = self.account_manager.get_net_liquidation(account) if self.account_manager else 0
        if account_value <= 0:
            logger.warning("Account value is 0 or negative")
            return self._empty_result()
            
        # Determine which price to use for risk calculations
        # For STOP LIMIT orders, use limit price for safer position sizing; otherwise use entry price
        if order_type == 'STOPLMT' and limit_price is not None and limit_price > 0:
            price_for_calculations = limit_price
            logger.info(f"Using limit price ${limit_price:.4f} for STOP LIMIT risk calculation (safer sizing)")
        else:
            price_for_calculations = entry_price
            logger.info(f"Using entry price ${entry_price:.4f} for {order_type} risk calculation")
            
        # Validate inputs
        if entry_price <= 0 or stop_loss <= 0:
            logger.warning("Invalid price inputs")
            return self._empty_result()
            
        if order_type == 'STOPLMT' and (limit_price is None or limit_price <= 0):
            logger.warning("Invalid limit price for STOP LIMIT order")
            return self._empty_result()
            
        # Calculate risk per share using appropriate price
        risk_per_share = abs(price_for_calculations - stop_loss)
        if risk_per_share == 0:
            logger.warning("Stop loss equals entry price")
            return self._empty_result()
            
        # Calculate dollar risk
        dollar_risk = account_value * (risk_percent / 100.0)
        
        # Calculate position size (round down for safety)
        shares_exact = dollar_risk / risk_per_share
        shares = int(shares_exact)  # Round down to whole shares
        
        # Calculate position value using appropriate price
        position_value = shares * price_for_calculations
        
        # Calculate margin requirement using appropriate price
        margin_required = 0
        if self.account_manager:
            margin_required = self.account_manager.calculate_margin_requirement(
                symbol='',  # Symbol not needed for calculation
                quantity=shares,
                price=price_for_calculations,
                account=account
            )
        
        # Actual dollar risk with rounded shares
        actual_dollar_risk = shares * risk_per_share
        
        return {
            'shares': shares,
            'position_value': position_value,
            'dollar_risk': actual_dollar_risk,
            'risk_per_share': risk_per_share,
            'account_value': account_value,
            'margin_required': margin_required,
            'risk_percent': risk_percent
        }
        
    def validate_trade(self,
                      symbol: str,
                      entry_price: float,
                      stop_loss: float,
                      take_profit: float,
                      shares: int,
                      direction: str,
                      account: Optional[str] = None,
                      order_type: str = 'LMT',
                      limit_price: Optional[float] = None) -> Tuple[bool, list]:
        """
        Validate a trade against risk rules
        
        Args:
            symbol: Stock symbol
            entry_price: Entry price (stop price for STOP LIMIT)
            stop_loss: Stop loss price
            take_profit: Take profit price
            shares: Number of shares
            direction: 'BUY' or 'SELL'
            account: Account ID
            order_type: Order type ('LMT', 'MKT', 'STOPLMT')
            limit_price: Limit price for STOP LIMIT orders
            
        Returns:
            Tuple of (is_valid, list_of_errors/warnings)
        """
        errors = []
        warnings = []
        
        # Determine which price to use for risk calculations
        if order_type == 'STOPLMT' and limit_price is not None and limit_price > 0:
            price_for_calculations = limit_price
        else:
            price_for_calculations = entry_price
        
        # Basic price validation
        if entry_price <= 0 or stop_loss <= 0 or take_profit <= 0:
            errors.append("All prices must be positive")
            
        if shares <= 0:
            errors.append("Position size must be positive")
            
        # Direction-specific validation
        if direction == 'BUY':
            if stop_loss >= entry_price:
                errors.append("Stop loss must be below entry for LONG positions")
            if take_profit <= entry_price:
                errors.append("Take profit must be above entry for LONG positions")
        else:  # SELL
            if stop_loss <= entry_price:
                errors.append("Stop loss must be above entry for SHORT positions")
            if take_profit >= entry_price:
                errors.append("Take profit must be below entry for SHORT positions")
                
        # Check minimum stop distance
        stop_distance_percent = abs(entry_price - stop_loss) / entry_price * 100
        if stop_distance_percent < self.min_stop_distance:
            warnings.append(f"Stop loss is very tight ({stop_distance_percent:.1f}% < {self.min_stop_distance}% minimum)")
            
        # Get account values
        buying_power = self.account_manager.get_buying_power(account) if self.account_manager else 0
        net_liq = self.account_manager.get_net_liquidation(account) if self.account_manager else 0
        
        # Check position value using appropriate price
        position_value = shares * price_for_calculations
        
        # Validate against buying power
        is_valid = True
        bp_message = ""
        if self.account_manager:
            is_valid, bp_message = self.account_manager.validate_order_buying_power(
                position_value, account
            )
        if not is_valid:
            errors.append(bp_message)
        elif "Warning" in bp_message:
            warnings.append(bp_message)
            
        # Check position concentration
        position_percent = (position_value / net_liq * 100) if net_liq > 0 else 0
        if position_percent > self.max_position_percent:
            errors.append(f"Position too large: {position_percent:.1f}% of account (max {self.max_position_percent}%)")
        elif position_percent > self.max_position_percent * 0.8:
            warnings.append(f"Large position: {position_percent:.1f}% of account")
            
        # Calculate actual risk using appropriate price
        risk_per_share = abs(price_for_calculations - stop_loss)
        dollar_risk = shares * risk_per_share
        risk_percent = (dollar_risk / net_liq * 100) if net_liq > 0 else 0
        
        if risk_percent > self.max_risk_percent:
            errors.append(f"Risk too high: {risk_percent:.1f}% (max {self.max_risk_percent}%)")
        elif risk_percent > self.max_risk_percent * 0.8:
            warnings.append(f"High risk: {risk_percent:.1f}%")
            
        # Return results
        is_valid = len(errors) == 0
        messages = errors + warnings
        
        return is_valid, messages
        
    def calculate_r_multiple(self,
                           entry_price: float,
                           stop_loss: float,
                           target_price: float,
                           order_type: str = 'LMT',
                           limit_price: Optional[float] = None) -> float:
        """
        Calculate R-multiple for a target price
        
        Args:
            entry_price: Entry price (stop price for STOP LIMIT)
            stop_loss: Stop loss price
            target_price: Target price
            order_type: Order type ('LMT', 'MKT', 'STOPLMT')
            limit_price: Limit price for STOP LIMIT orders
            
        Returns:
            R-multiple (reward/risk ratio)
        """
        # Determine which price to use for risk calculations
        if order_type == 'STOPLMT' and limit_price is not None and limit_price > 0:
            price_for_calculations = limit_price
        else:
            price_for_calculations = entry_price
            
        risk = abs(price_for_calculations - stop_loss)
        if risk == 0:
            return 0
            
        reward = abs(target_price - price_for_calculations)
        return reward / risk
        
    def suggest_targets(self,
                       entry_price: float,
                       stop_loss: float,
                       r_multiples: list = None,
                       order_type: str = 'LMT',
                       limit_price: Optional[float] = None) -> list:
        """
        Suggest target prices based on R-multiples
        
        Args:
            entry_price: Entry price (stop price for STOP LIMIT)
            stop_loss: Stop loss price
            r_multiples: List of R-multiples (default: [1, 2, 3, 5])
            order_type: Order type ('LMT', 'MKT', 'STOPLMT')
            limit_price: Limit price for STOP LIMIT orders
            
        Returns:
            List of suggested target prices
        """
        if r_multiples is None:
            r_multiples = [1, 2, 3, 5]
        
        # Determine which price to use for calculations
        if order_type == 'STOPLMT' and limit_price is not None and limit_price > 0:
            price_for_calculations = limit_price
        else:
            price_for_calculations = entry_price
            
        risk = abs(price_for_calculations - stop_loss)
        targets = []
        
        # Determine direction based on appropriate price
        is_long = stop_loss < price_for_calculations
        
        for r in r_multiples:
            if is_long:
                target = price_for_calculations + (risk * r)
            else:
                target = price_for_calculations - (risk * r)
            targets.append(round(target, 2))
            
        return targets
        
    def _empty_result(self) -> Dict[str, float]:
        """Return empty result dictionary"""
        return {
            'shares': 0,
            'position_value': 0,
            'dollar_risk': 0,
            'risk_per_share': 0,
            'account_value': 0,
            'margin_required': 0,
            'risk_percent': 0
        }