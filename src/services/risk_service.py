"""
Risk Service
Centralized risk management service for position sizing and trade validation
"""

from typing import Dict, Tuple, Optional, List
from decimal import Decimal, ROUND_DOWN
import math

from src.services.base_service import BaseService
from src.core.risk_calculator import RiskCalculator
from src.services.account_manager_service import AccountManagerService
from src.services.service_registry import get_service_registry
from src.utils.logger import logger
from config import TRADING_CONFIG


class RiskService(BaseService):
    """Service for managing trading risk calculations and validations"""
    
    def __init__(self):
        super().__init__("RiskService")
        self.risk_calculator: Optional[RiskCalculator] = None
        self.account_manager: Optional[AccountManagerService] = None
        
    def initialize(self) -> bool:
        """Initialize the risk service"""
        try:
            if not super().initialize():
                return False
                
            logger.info("Initializing RiskService...")
            
            # Risk calculator will be set when account manager is available
            self.risk_calculator = None
            
            self._initialized = True
            logger.info("RiskService initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize RiskService: {str(e)}")
            self._initialized = False
            return False
            
    def cleanup(self) -> bool:
        """Cleanup risk service resources"""
        try:
            logger.info("Cleaning up RiskService...")
            
            self.risk_calculator = None
            self.account_manager = None
            
            self._initialized = False
            logger.info("RiskService cleaned up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up RiskService: {str(e)}")
            return False
            
    def set_account_manager(self, account_manager: AccountManagerService):
        """Set account manager and initialize risk calculator"""
        try:
            self.account_manager = account_manager
            self.risk_calculator = RiskCalculator(account_manager)
            logger.info("Risk calculator initialized in RiskService")
        except Exception as e:
            logger.error(f"Error setting account manager in RiskService: {str(e)}")
    
    def _ensure_risk_calculator(self) -> bool:
        """Ensure risk calculator is available, auto-initialize if possible"""
        if self.risk_calculator:
            return True
            
        # Try to get account manager from service registry as fallback
        try:
            from src.services import get_account_service
            account_service = get_account_service()
            if account_service and hasattr(account_service, '_service'):
                self.set_account_manager(account_service._service)
                logger.info("Risk calculator auto-initialized from account service")
                return True
            else:
                logger.warning("Risk calculator not available - account service not ready")
                return False
        except Exception as e:
            logger.error(f"Risk calculator auto-init failed: {e}")
            return False
            
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
            Dictionary with position sizing information
        """
        if not self._check_initialized():
            return self._empty_result()
            
        if not self._ensure_risk_calculator():
            return self._empty_result()
            
        try:
            return self.risk_calculator.calculate_position_size(
                entry_price=entry_price,
                stop_loss=stop_loss,
                risk_percent=risk_percent,
                account=account,
                order_type=order_type,
                limit_price=limit_price
            )
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return self._empty_result()
            
    def validate_trade(self,
                      symbol: str,
                      entry_price: float,
                      stop_loss: float,
                      take_profit: float,
                      shares: int,
                      direction: str,
                      account: Optional[str] = None,
                      order_type: str = 'LMT',
                      limit_price: Optional[float] = None) -> Tuple[bool, List[str]]:
        """
        Validate a trade against risk parameters
        
        Returns:
            Tuple of (is_valid, list_of_messages)
        """
        if not self._check_initialized():
            return False, ["Risk service not initialized"]
            
        if not self._ensure_risk_calculator():
            return False, ["Risk calculator not available"]
            
        try:
            return self.risk_calculator.validate_trade(
                symbol=symbol,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                shares=shares,
                direction=direction,
                account=account,
                order_type=order_type,
                limit_price=limit_price
            )
        except Exception as e:
            logger.error(f"Error validating trade: {str(e)}")
            return False, [f"Error validating trade: {str(e)}"]
            
    def calculate_r_multiple(self,
                           entry_price: float,
                           stop_loss: float,
                           target_price: float,
                           order_type: str = 'LMT',
                           limit_price: Optional[float] = None) -> float:
        """
        Calculate R-multiple for a trade
        
        Returns:
            R-multiple value
        """
        if not self._check_initialized():
            return 0.0
            
        if not self._ensure_risk_calculator():
            return 0.0
            
        try:
            return self.risk_calculator.calculate_r_multiple(
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_price=target_price,
                order_type=order_type,
                limit_price=limit_price
            )
        except Exception as e:
            logger.error(f"Error calculating R-multiple: {str(e)}")
            return 0.0
            
    def suggest_targets(self,
                       entry_price: float,
                       stop_loss: float,
                       r_multiples: Optional[List[float]] = None,
                       direction: str = 'BUY') -> List[Dict[str, float]]:
        """
        Suggest profit targets based on R-multiples
        
        Returns:
            List of target dictionaries with price and R-multiple
        """
        if not self._check_initialized():
            return []
            
        if not self._ensure_risk_calculator():
            return []
            
        try:
            return self.risk_calculator.suggest_targets(
                entry_price=entry_price,
                stop_loss=stop_loss,
                r_multiples=r_multiples,
                direction=direction
            )
        except Exception as e:
            logger.error(f"Error suggesting targets: {str(e)}")
            return []
            
    def _empty_result(self) -> Dict[str, float]:
        """Return empty result dictionary"""
        return {
            'shares': 0,
            'dollar_risk': 0,
            'dollar_risk_per_share': 0,
            'position_value': 0,
            'percent_of_account': 0,
            'percent_of_buying_power': 0,
            'net_liquidation': 0,
            'buying_power': 0,
            'messages': ['Risk calculation not available']
        }
        
    def get_default_risk_percent(self) -> float:
        """Get default risk percentage from config"""
        return TRADING_CONFIG.get('default_risk_percent', 0.3)
        
    def get_max_risk_percent(self) -> float:
        """Get maximum risk percentage from config"""
        return TRADING_CONFIG.get('max_risk_percent', 2.0)