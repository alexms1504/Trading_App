"""
Trading Controller
Handles all trading-related business logic
"""

from typing import Optional, Dict, List, Tuple, Any
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from .base_controller import BaseController
from src.services import get_order_service, get_risk_service, get_account_service
from src.utils.logger import logger
import config


class TradingController(BaseController):
    """Controller for trading operations"""
    
    # Trading-specific signals
    order_submitted = pyqtSignal(dict)
    order_validated = pyqtSignal(bool, list)  # is_valid, messages
    order_confirmed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def validate_order(self, order_data: dict) -> Tuple[bool, List[str]]:
        """
        Validate order data
        
        Returns:
            Tuple of (is_valid, list_of_messages)
        """
        try:
            # First validate with OrderService
            order_service = get_order_service()
            if not order_service:
                return False, ["Order service not available"]
                
            is_valid, errors = order_service.validate_order(order_data)
            
            if not is_valid:
                self.order_validated.emit(False, errors)
                return False, errors
                
            # Additional risk validation
            risk_messages = self._validate_risk(order_data)
            
            # Combine all messages
            all_messages = errors + risk_messages
            
            # Check for warnings
            has_warnings = any("Warning" in msg or "Large" in msg or "High" in msg 
                             for msg in all_messages)
            
            self.order_validated.emit(True, all_messages)
            return True, all_messages
            
        except Exception as e:
            error_msg = f"Error validating order: {str(e)}"
            logger.error(error_msg)
            return False, [error_msg]
            
    def _validate_risk(self, order_data: dict) -> List[str]:
        """Validate order against risk rules"""
        messages = []
        
        order_service = get_order_service()
        if not order_service:
            return ["Risk validation unavailable"]
            
        is_valid, risk_messages = order_service.validate_trade(
            symbol=order_data.get('symbol'),
            entry_price=order_data.get('entry_price'),
            stop_loss=order_data.get('stop_loss'),
            take_profit=order_data.get('take_profit', 0),
            shares=order_data.get('quantity'),
            direction=order_data.get('direction')
        )
        
        messages.extend(risk_messages)
        return messages
        
    def show_order_confirmation(self, order_data: dict) -> bool:
        """
        Show order confirmation dialog
        
        Returns:
            True if user confirms, False otherwise
        """
        try:
            # Calculate order metrics
            metrics = self._calculate_order_metrics(order_data)
            
            # Build confirmation message
            message = self._build_confirmation_message(order_data, metrics)
            
            # Show dialog
            reply = QMessageBox.question(
                self._parent_widget, 
                "Confirm Order", 
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            confirmed = reply == QMessageBox.StandardButton.Yes
            if confirmed:
                self.order_confirmed.emit(order_data)
                
            return confirmed
            
        except Exception as e:
            logger.error(f"Error showing order confirmation: {str(e)}")
            return False
            
    def _calculate_order_metrics(self, order_data: dict) -> Dict[str, Any]:
        """Calculate order metrics for display"""
        # Calculate R-multiple
        order_service = get_order_service()
        r_multiple = 0
        if order_service and not order_data.get('use_multiple_targets', False):
            r_multiple = order_service.calculate_r_multiple(
                order_data['entry_price'],
                order_data['stop_loss'],
                order_data.get('take_profit', 0)
            )
            
        # Calculate position values
        price = (order_data.get('limit_price') if order_data.get('order_type') == 'STOPLMT' 
                else order_data['entry_price'])
        order_value = order_data['quantity'] * price
        dollar_risk = order_data['quantity'] * abs(price - order_data['stop_loss'])
        
        # Get account values
        account_service = get_account_service()
        net_liq = 100000  # Default
        buying_power = 100000  # Default
        
        if account_service:
            net_liq = account_service.get_account_value() or net_liq
            buying_power = account_service.get_buying_power() or buying_power
            
        portfolio_pct = (order_value / net_liq * 100) if net_liq > 0 else 0
        bp_pct = (order_value / buying_power * 100) if buying_power > 0 else 0
        
        return {
            'r_multiple': r_multiple,
            'order_value': order_value,
            'dollar_risk': dollar_risk,
            'portfolio_pct': portfolio_pct,
            'bp_pct': bp_pct,
            'net_liq': net_liq,
            'buying_power': buying_power
        }
        
    def _build_confirmation_message(self, order_data: dict, metrics: dict) -> str:
        """Build order confirmation message"""
        # Build profit targets text
        if order_data.get('use_multiple_targets', False):
            targets_text = ""
            for i, target in enumerate(order_data['profit_targets'], 1):
                if target['price'] > 0:
                    # Use the corrected quantity from order assistant (handles rounding properly)
                    target_qty = target.get('quantity', int(order_data['quantity'] * target['percent'] / 100))
                    targets_text += f"\nTarget {i}: ${target['price']:.2f} ({target['percent']}% = {target_qty} shares)"
        else:
            targets_text = f"\nTake Profit: ${order_data['take_profit']:.2f} (R={metrics['r_multiple']:.1f})"
        
        message = f"""
Order Preview:
{order_data['direction']} {order_data['quantity']} shares of {order_data['symbol']}
Entry: ${order_data['entry_price']:.2f} ({order_data['order_type']})
Stop Loss: ${order_data['stop_loss']:.2f}{targets_text}

Position Value: ${metrics['order_value']:,.2f} ({metrics['portfolio_pct']:.1f}% of Portfolio, {metrics['bp_pct']:.1f}% of BP)
Dollar Risk: ${metrics['dollar_risk']:,.2f}
Risk: {order_data['risk_percent']:.2f}%

Submit this order?
        """
        
        return message.strip()
        
    def submit_order(self, order_data: dict) -> Tuple[bool, str, Optional[List]]:
        """
        Submit order to broker
        
        Returns:
            Tuple of (success, message, trades)
        """
        try:
            order_service = get_order_service()
            if not order_service:
                return False, "Order service not available", None
                
            # Show progress
            self.update_status("Submitting order...")
            
            # Submit order
            success, message, trades = order_service.create_order(order_data)
            
            if success:
                self._handle_order_success(order_data, message, trades)
            else:
                self._handle_order_failure(order_data, message)
                
            return success, message, trades
            
        except Exception as e:
            error_msg = f"Error submitting order: {str(e)}"
            logger.error(error_msg)
            self.show_error(error_msg)
            return False, error_msg, None
            
    def _handle_order_success(self, order_data: dict, message: str, trades: List):
        """Handle successful order submission"""
        # Extract order IDs
        order_ids = [t.order.orderId for t in trades] if trades else []
        
        # Check if orders need TWS confirmation
        needs_confirmation = self._check_needs_confirmation(trades)
        
        if needs_confirmation:
            success_msg = self._build_tws_confirmation_message(order_ids)
        else:
            success_msg = f"Order submitted successfully!\n\nOrder IDs: {order_ids}\n\nBracket orders are active in TWS."
            
        self.show_info(success_msg, "Order Submitted")
        
        # Update status
        self.update_status(f"Order submitted: {order_data['symbol']} - {message}", 5000)
        logger.info(f"Order submitted successfully: {order_ids}")
        
        # Check API configuration
        self._check_api_configuration()
        
        # Emit signal
        self.order_submitted.emit(order_data)
        
    def _handle_order_failure(self, order_data: dict, message: str):
        """Handle failed order submission"""
        error_msg = f"Order submission failed:\n\n{message}"
        
        # Add configuration guidance for common issues
        if "cancelled" in message.lower() or "confirmation" in message.lower():
            error_msg += self._get_configuration_guidance(order_data['symbol'])
            
        self.show_error(error_msg)
        self.update_status("Order submission failed", 5000)
        
    def _check_needs_confirmation(self, trades: List) -> bool:
        """Check if orders need manual TWS confirmation"""
        if not trades:
            return False
            
        for trade in trades:
            if (hasattr(trade, 'orderStatus') and trade.orderStatus and 
                hasattr(trade.orderStatus, 'status')):
                if trade.orderStatus.status in ['PreSubmitted', 'Inactive']:
                    return True
        return False
        
    def _build_tws_confirmation_message(self, order_ids: List) -> str:
        """Build TWS confirmation warning message"""
        return f"""Order submitted successfully!
                    
Order IDs: {order_ids}

⚠️  IMPORTANT: Your orders may require manual confirmation in TWS.

If orders are not executing automatically:
1. Check TWS for pending orders requiring confirmation
2. Go to TWS → File → Global Configuration → API → Settings
3. Enable "Bypass Order Precautions for API Orders"
4. Restart TWS after making changes

Check the TWS Order Management window for your bracket orders."""
        
    def _get_configuration_guidance(self, symbol: str) -> str:
        """Get configuration guidance for common issues"""
        return f"""\n\nConfig - Common Solutions:

1. TWS Configuration:
   • File → Global Configuration → API → Settings
   • Enable "Bypass Order Precautions for API Orders"
   • Uncheck "Read-Only API" if checked
   • Restart TWS after changes

2. Check TWS Order Management for any pending confirmations

3. Verify account has sufficient buying power

4. Ensure market is open for {symbol}"""
        
    def _check_api_configuration(self):
        """Check API configuration and warn if needed"""
        order_service = get_order_service()
        if not order_service:
            return
            
        is_configured, config_issues = order_service.check_api_configuration()
        if not is_configured and config_issues:
            config_msg = "API Configuration Issues Detected:\n\n" + "\n".join(config_issues)
            self.show_warning(config_msg, "API Configuration")