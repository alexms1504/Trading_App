"""
Trading Panel
Central panel containing order assistant, charts, and market screener
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import pyqtSignal

from src.ui.order_assistant import OrderAssistantWidget
from src.ui.market_screener import MarketScreenerWidget
from src.ui.chart_widget_embedded import ChartWidget
from src.utils.logger import logger
import config


class TradingPanel(QWidget):
    """Main trading interface panel"""
    
    # Forward signals from child widgets
    order_submitted = pyqtSignal(dict)
    fetch_price_requested = pyqtSignal(str)
    symbol_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create widgets
        self.order_assistant = OrderAssistantWidget()
        self.market_screener = MarketScreenerWidget()
        self.chart_widget = ChartWidget()
        
        # Set order assistant reference on chart widget for order type checking
        self.chart_widget.set_order_assistant_reference(self.order_assistant)
        
        self._init_ui()
        self._setup_connections()
        
    def _init_ui(self):
        """Initialize the UI"""
        layout = QHBoxLayout(self)
        
        # Left side - Order Assistant
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(self.order_assistant)
        left_widget.setMaximumWidth(config.WINDOW_CONFIG['widget_widths']['order_assistant_max'])
        
        # Center - Chart Widget
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.addWidget(self.chart_widget)
        
        # Right side - Market Screener
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.addWidget(self.market_screener)
        right_widget.setMaximumWidth(config.WINDOW_CONFIG['widget_widths']['market_screener_max'])
        
        # Add all three sections to layout
        layout.addWidget(left_widget, 1)  # Ratio 1
        layout.addWidget(center_widget, 2)  # Ratio 2 (larger for charts)
        layout.addWidget(right_widget, 1)  # Ratio 1
        
    def _setup_connections(self):
        """Setup internal widget connections"""
        # Forward signals
        self.order_assistant.order_submitted.connect(self.order_submitted.emit)
        self.order_assistant.fetch_price_requested.connect(self.fetch_price_requested.emit)
        self.market_screener.symbol_selected.connect(self.symbol_selected.emit)
        
        # Connect Order Assistant price changes to chart
        self.order_assistant.entry_price_changed.connect(self._on_entry_price_changed)
        self.order_assistant.stop_loss_changed.connect(self._on_stop_loss_changed)
        self.order_assistant.take_profit_changed.connect(self._on_take_profit_changed)
        self.order_assistant.limit_price_changed.connect(self._on_limit_price_changed)
        self.order_assistant.target_prices_changed.connect(self._on_target_prices_changed)
        
        # Connect chart price changes to Order Assistant
        self.chart_widget.chart_entry_changed.connect(self._on_chart_entry_changed)
        self.chart_widget.chart_stop_loss_changed.connect(self._on_chart_stop_loss_changed)
        self.chart_widget.chart_take_profit_changed.connect(self._on_chart_take_profit_changed)
        
        # Connect market screener to chart
        self.market_screener.symbol_selected.connect(self._on_screener_symbol_selected)
        
        # Connect fetch price to chart update
        self.order_assistant.fetch_price_requested.connect(self._on_fetch_price_requested)
        
    def _on_entry_price_changed(self, price: float):
        """Handle entry price change from Order Assistant"""
        try:
            # Update chart with all current price levels
            self._update_chart_price_levels()
            logger.info(f"Updated chart entry price: ${price:.2f}")
        except Exception as e:
            logger.error(f"Error updating chart entry price: {str(e)}")
            
    def _on_stop_loss_changed(self, price: float):
        """Handle stop loss change from Order Assistant"""
        try:
            self._update_chart_price_levels()
            logger.info(f"Updated chart stop loss: ${price:.2f}")
        except Exception as e:
            logger.error(f"Error updating chart stop loss: {str(e)}")
            
    def _on_take_profit_changed(self, price: float):
        """Handle take profit change from Order Assistant"""
        try:
            self._update_chart_price_levels()
            logger.info(f"Updated chart take profit: ${price:.2f}")
        except Exception as e:
            logger.error(f"Error updating chart take profit: {str(e)}")
            
    def _on_limit_price_changed(self, price: float):
        """Handle limit price change from Order Assistant"""
        try:
            self._update_chart_price_levels()
            logger.info(f"Updated chart limit price: ${price:.2f}")
        except Exception as e:
            logger.error(f"Error updating chart limit price: {str(e)}")
            
    def _on_target_prices_changed(self, target_prices: list):
        """Handle target prices change from Order Assistant"""
        try:
            self._update_chart_price_levels(target_prices=target_prices)
            logger.info(f"Updated chart target prices: {target_prices}")
        except Exception as e:
            logger.error(f"Error updating chart target prices: {str(e)}")
            
    def _update_chart_price_levels(self, target_prices: list = None):
        """Update all chart price levels"""
        entry = self.order_assistant.entry_price.value()
        stop_loss = self.order_assistant.stop_loss_price.value()
        take_profit = self.order_assistant.take_profit_price.value() if not self.order_assistant.use_multiple_targets else None
        # Only pass limit_price to chart if order type is STOP LIMIT
        # This prevents the limit price line from appearing for LIMIT and MARKET orders
        limit_price = (self.order_assistant.limit_price.value() 
                      if self.order_assistant.stop_limit_button.isChecked() 
                      else None)
        
        # Debug logging to understand why take profit line doesn't show
        logger.info(f"Updating chart price levels:")
        logger.info(f"  - Entry: ${entry:.2f}")
        logger.info(f"  - Stop Loss: ${stop_loss:.2f}")
        logger.info(f"  - Take Profit: ${take_profit:.2f}" if take_profit else "  - Take Profit: None (multiple targets enabled)")
        logger.info(f"  - Multiple targets enabled: {self.order_assistant.use_multiple_targets}")
        logger.info(f"  - Limit Price: {f'${limit_price:.2f}' if limit_price else 'None'} (STOP LIMIT: {self.order_assistant.stop_limit_button.isChecked()})")
        logger.info(f"  - Target Prices: {target_prices}")
        
        self.chart_widget.update_price_levels(
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            limit_price=limit_price,
            target_prices=target_prices,
            auto_rescale=True
        )
        
    def _on_chart_entry_changed(self, price: float):
        """Handle entry price change from chart"""
        try:
            # Validate and update Order Assistant
            price = max(0.0001, min(10000.0, price))
            self.order_assistant.entry_price.setValue(price)
            logger.info(f"Updated Order Assistant entry from chart: ${price:.2f}")
        except Exception as e:
            logger.error(f"Error updating entry price from chart: {str(e)}")
            
    def _on_chart_stop_loss_changed(self, price: float):
        """Handle stop loss change from chart"""
        try:
            self.order_assistant.stop_loss_price.setValue(price)
            logger.info(f"Updated Order Assistant stop loss from chart: ${price:.2f}")
        except Exception as e:
            logger.error(f"Error updating stop loss from chart: {str(e)}")
            
    def _on_chart_take_profit_changed(self, price: float):
        """Handle take profit change from chart"""
        try:
            self.order_assistant.take_profit_price.setValue(price)
            # Update R-multiple
            self.order_assistant.on_take_profit_price_manual_changed(price)
            logger.info(f"Updated Order Assistant take profit from chart: ${price:.2f}")
        except Exception as e:
            logger.error(f"Error updating take profit from chart: {str(e)}")
            
    def _on_screener_symbol_selected(self, symbol: str):
        """Handle symbol selection from market screener"""
        try:
            logger.info(f"Symbol selected from screener: {symbol}")
            
            # Update Order Assistant
            self.order_assistant.symbol_input.setText(symbol)
            
            # Update Chart
            self.chart_widget.set_symbol(symbol)
            
        except Exception as e:
            logger.error(f"Error handling screener symbol selection: {str(e)}")
            
    def _on_fetch_price_requested(self, symbol: str):
        """Handle fetch price request"""
        try:
            # Update chart when fetching price
            if symbol:
                self.chart_widget.set_symbol(symbol.upper())
                logger.info(f"Chart updated with symbol from Fetch Price: {symbol}")
        except Exception as e:
            logger.error(f"Error updating chart from Fetch Price: {str(e)}")
            
    def update_price_data(self, price_data: dict):
        """Update widgets with price data"""
        try:
            # Update Order Assistant prices
            self.order_assistant.entry_price.setValue(price_data.get('entry_price', 0))
            self.order_assistant.stop_loss_price.setValue(price_data.get('stop_loss', 0))
            self.order_assistant.take_profit_price.setValue(price_data.get('take_profit', 0))
            
            # Manually trigger chart update for take profit
            self.order_assistant.on_take_profit_price_changed(price_data.get('take_profit', 0))
            
            # Update price info display
            last = price_data.get('last', price_data.get('current_price', 0))
            bid = price_data.get('bid', 0)
            ask = price_data.get('ask', 0)
            self.order_assistant.update_price_info(last, bid, ask)
            
            # Update stop loss options
            stop_levels = price_data.get('stop_levels', {})
            self.order_assistant.update_stop_loss_options(stop_levels)
            
        except Exception as e:
            logger.error(f"Error updating price data: {str(e)}")
            
    def cleanup(self):
        """Cleanup resources"""
        try:
            # Cleanup child widgets
            if self.market_screener:
                self.market_screener.cleanup()
            if self.chart_widget:
                self.chart_widget.cleanup()
                
            logger.info("TradingPanel cleaned up")
            
        except Exception as e:
            logger.error(f"Error cleaning up TradingPanel: {str(e)}")