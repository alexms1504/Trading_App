"""
Order Assistant Widget
Core trading interface for entering and submitting orders
"""

from typing import Optional, Dict, Any
from decimal import Decimal
import math

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QDoubleSpinBox, QSpinBox,
    QSlider, QButtonGroup, QRadioButton, QFrame, QCheckBox,
    QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QDoubleValidator, QIntValidator, QKeyEvent

from src.utils.logger import logger
from src.services import get_risk_service
from config import TRADING_CONFIG


class ImprovedDoubleSpinBox(QDoubleSpinBox):
    """Custom QDoubleSpinBox that properly handles selection replacement"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._select_all_on_focus = True
        
    def focusInEvent(self, event):
        """Select all text when gaining focus"""
        super().focusInEvent(event)
        if self._select_all_on_focus:
            # Use a timer to ensure the selection happens after focus
            QTimer.singleShot(0, self.selectAll)
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events to fix selection replacement"""
        # Get the line edit widget
        line_edit = self.lineEdit()
        
        # If there's a selection and user types a number or decimal point
        if line_edit and line_edit.hasSelectedText() and event.text() and (event.text().isdigit() or event.text() == '.'):
            # Clear the selected text first, then let normal input handling proceed
            line_edit.clear()
        
        # Call parent implementation
        super().keyPressEvent(event)
        
    def mousePressEvent(self, event):
        """Handle mouse press to allow proper selection"""
        super().mousePressEvent(event)
        # If clicking on the spinbox, select all after a short delay
        if event.button() == Qt.MouseButton.LeftButton:
            QTimer.singleShot(100, self.selectAll)


class ImprovedSpinBox(QSpinBox):
    """Custom QSpinBox that properly handles selection replacement"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._select_all_on_focus = True
        
    def focusInEvent(self, event):
        """Select all text when gaining focus"""
        super().focusInEvent(event)
        if self._select_all_on_focus:
            # Use a timer to ensure the selection happens after focus
            QTimer.singleShot(0, self.selectAll)
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events to fix selection replacement"""
        # Get the line edit widget
        line_edit = self.lineEdit()
        
        # If there's a selection and user types a number
        if line_edit and line_edit.hasSelectedText() and event.text() and event.text().isdigit():
            # Clear the selected text first, then let normal input handling proceed
            line_edit.clear()
        
        # Call parent implementation
        super().keyPressEvent(event)
        
    def mousePressEvent(self, event):
        """Handle mouse press to allow proper selection"""
        super().mousePressEvent(event)
        # If clicking on the spinbox, select all after a short delay
        if event.button() == Qt.MouseButton.LeftButton:
            QTimer.singleShot(100, self.selectAll)


class OrderAssistantWidget(QWidget):
    """Main order entry widget for trading"""
    
    # Signals
    order_submitted = pyqtSignal(dict)  # Emitted when order is ready to submit
    fetch_price_requested = pyqtSignal(str)  # Emitted when price fetch is requested
    
    # Price change signals for chart synchronization
    entry_price_changed = pyqtSignal(float)  # Emitted when entry price changes
    stop_loss_changed = pyqtSignal(float)  # Emitted when stop loss changes
    take_profit_changed = pyqtSignal(float)  # Emitted when take profit changes
    limit_price_changed = pyqtSignal(float)  # Emitted when limit price changes
    target_prices_changed = pyqtSignal(list)  # Emitted when multiple target prices change
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.account_value = 100000.0  # Default value, will be updated when connected
        self.buying_power = 100000.0  # Default buying power, will be updated when connected
        # Risk calculations now handled through RiskService
        self.stop_loss_data = {}  # Store calculated stop loss levels
        self.use_multiple_targets = False  # Track if using multiple targets
        self.profit_targets = []  # Store multiple profit target widgets
        self.active_target_count = 2  # Default to 2 targets when enabled
        self._updating_from_risk = False  # Flag to prevent circular updates
        self._updating_take_profit = False  # Flag to prevent circular take profit updates
        self._limit_price_manually_adjusted = False  # Flag to track manual limit price adjustments
        self._limit_price_offset = None  # Store the absolute dollar difference between entry and limit price
        self.init_ui()
        self.setup_connections()
        
    def round_to_tick_size(self, price: float) -> float:
        """Round price to appropriate tick size for IB orders"""
        try:
            if price >= 1.0:
                # Stocks >= $1: Round to nearest penny (0.01)
                return round(price, 2)
            else:
                # Stocks < $1: Round to nearest 0.0001 (sub-penny)
                return round(price, 4)
        except:
            return round(price, 2)  # Default to 2 decimal places
    
    def update_decimal_places_for_all_prices(self):
        """Update decimal places for all price fields based on entry price"""
        try:
            entry_price = self.entry_price.value()
            
            # Determine decimal places based on entry price
            if entry_price >= 1.0:
                decimals = 2  # Penny stocks
            else:
                decimals = 4  # Sub-penny stocks
            
            # Update all price fields
            price_fields = [
                self.entry_price,
                self.stop_loss_price,
                self.take_profit_price,
                self.limit_price
            ]
            
            for field in price_fields:
                field.setDecimals(decimals)
            
            # Update multiple target price fields
            for target in self.profit_targets:
                target['price'].setDecimals(decimals)
            
            logger.info(f"Updated decimal places to {decimals} for entry price ${entry_price:.4f}")
            
        except Exception as e:
            logger.error(f"Error updating decimal places: {e}")
    
    def update_limit_price_for_stop_limit(self):
        """Update limit price when entry price changes for STOP LIMIT orders"""
        try:
            if not (self.stop_limit_button.isChecked() and self.limit_price.isVisible()):
                return
                
            entry_price = self.entry_price.value()
            
            # If user has manually adjusted limit price, maintain the absolute dollar difference
            if self._limit_price_manually_adjusted and self._limit_price_offset is not None:
                # Maintain absolute dollar difference
                new_limit = entry_price + self._limit_price_offset
                new_limit = self.round_to_tick_size(new_limit)
                self.limit_price.setValue(new_limit)
                logger.info(f"Maintained limit price offset: Entry ${entry_price:.4f} + ${self._limit_price_offset:.4f} = ${new_limit:.4f}")
                
            elif not self._limit_price_manually_adjusted:
                # Initial automatic calculation: 0.1% larger than entry price (stop price)
                new_limit = entry_price * 1.001  # 0.1% larger
                new_limit = self.round_to_tick_size(new_limit)
                self.limit_price.setValue(new_limit)
                
                # Store the initial offset for future maintenance
                self._limit_price_offset = new_limit - entry_price
                logger.info(f"Set initial limit price: ${new_limit:.4f} (0.1% above entry ${entry_price:.4f}), offset stored: ${self._limit_price_offset:.4f}")
                
            else:
                logger.debug("Skipping limit price update - manual adjustment flag set but no offset stored")
                
        except Exception as e:
            logger.error(f"Error updating limit price: {e}")
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Symbol and Direction Section
        layout.addWidget(self.create_symbol_section())
        
        # Price Entry Section
        layout.addWidget(self.create_price_section())
        
        # Risk Management Section
        layout.addWidget(self.create_risk_section())
        
        # Order Summary Section
        layout.addWidget(self.create_summary_section())
        
        # Action Buttons
        layout.addWidget(self.create_action_buttons())
        
        # Add stretch to push everything to top
        layout.addStretch()
        
    def create_symbol_section(self) -> QGroupBox:
        """Create symbol and direction input section"""
        group = QGroupBox("Symbol & Direction")
        layout = QGridLayout()
        
        # Symbol input with fetch button
        layout.addWidget(QLabel("Symbol:"), 0, 0)
        
        # Create horizontal layout for symbol input and fetch button
        symbol_layout = QHBoxLayout()
        
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Enter stock symbol (e.g., AAPL)")
        self.symbol_input.setMaxLength(10)
        self.symbol_input.setStyleSheet("font-size: 14px; font-weight: bold;")
        symbol_layout.addWidget(self.symbol_input)
        
        # Fetch price button
        self.fetch_price_button = QPushButton("Fetch")
        self.fetch_price_button.setToolTip("Fetch current market price and stop loss levels (Enter)")
        self.fetch_price_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 5px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        symbol_layout.addWidget(self.fetch_price_button)
        
        layout.addLayout(symbol_layout, 0, 1, 1, 2)
        
        # Add progress bar below symbol input (spans full width)
        self.fetch_progress = QProgressBar()
        self.fetch_progress.setMaximumHeight(3)  # Thin progress bar
        self.fetch_progress.setTextVisible(False)
        self.fetch_progress.setRange(0, 0)  # Indeterminate mode
        self.fetch_progress.hide()  # Hidden by default
        self.fetch_progress.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #e0e0e0;
                border-radius: 1px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 1px;
            }
        """)
        layout.addWidget(self.fetch_progress, 1, 0, 1, 3)  # Span all columns
        
        # Direction buttons (moved down 1 row due to progress bar)
        layout.addWidget(QLabel("Direction:"), 2, 0)
        self.direction_group = QButtonGroup()
        
        self.long_button = QRadioButton("LONG")
        self.long_button.setChecked(True)
        self.long_button.setStyleSheet("QRadioButton { color: green; font-weight: bold; }")
        self.direction_group.addButton(self.long_button, 0)
        
        self.short_button = QRadioButton("SHORT")
        self.short_button.setStyleSheet("QRadioButton { color: red; font-weight: bold; }")
        self.direction_group.addButton(self.short_button, 1)
        
        direction_layout = QHBoxLayout()
        direction_layout.addWidget(self.long_button)
        direction_layout.addWidget(self.short_button)
        direction_layout.addStretch()
        layout.addLayout(direction_layout, 1, 1, 1, 2)
        
        # Order type buttons
        layout.addWidget(QLabel("Order Type:"), 2, 0)
        self.order_type_group = QButtonGroup()
        
        self.limit_button = QRadioButton("LIMIT")
        self.limit_button.setChecked(True)
        self.order_type_group.addButton(self.limit_button, 0)
        
        self.market_button = QRadioButton("MARKET")
        self.order_type_group.addButton(self.market_button, 1)
        
        self.stop_limit_button = QRadioButton("STOP LIMIT")
        self.order_type_group.addButton(self.stop_limit_button, 2)
        
        order_type_layout = QHBoxLayout()
        order_type_layout.addWidget(self.limit_button)
        order_type_layout.addWidget(self.market_button)
        order_type_layout.addWidget(self.stop_limit_button)
        order_type_layout.addStretch()
        layout.addLayout(order_type_layout, 2, 1, 1, 2)
        
        group.setLayout(layout)
        return group
        
    def create_price_section(self) -> QGroupBox:
        """Create price entry section"""
        group = QGroupBox("Price Levels")
        layout = QGridLayout()
        layout.setVerticalSpacing(5)  # Reduce vertical spacing between rows
        
        # Entry price with adjustment buttons
        layout.addWidget(QLabel("Entry Price:"), 0, 0)
        
        # Create horizontal layout for entry price input and adjustment buttons
        entry_input_layout = QHBoxLayout()
        
        self.entry_price = ImprovedDoubleSpinBox()
        self.entry_price.setRange(0.0001, 5000.0)  # Max $5,000 per share
        self.entry_price.setDecimals(4)  # 4 decimal places for entry price
        self.entry_price.setSingleStep(0.01)
        self.entry_price.setPrefix("$")
        self.entry_price.setValue(1.0000)  # Default entry price: $1.0000
        self.entry_price.setMinimumWidth(120)  # Wider for 4 decimals
        entry_input_layout.addWidget(self.entry_price)
        
        # Add more spacing before buttons
        entry_input_layout.addSpacing(30)
        
        # Add adjustment buttons
        self.entry_minus_ten_button = QPushButton("-0.1")
        self.entry_minus_ten_button.setMaximumWidth(45)
        self.entry_minus_ten_button.setToolTip("Decrease entry by $0.10")
        entry_input_layout.addWidget(self.entry_minus_ten_button)
        
        self.entry_minus_button = QPushButton("-0.01")
        self.entry_minus_button.setMaximumWidth(45)
        self.entry_minus_button.setToolTip("Decrease entry by $0.01")
        entry_input_layout.addWidget(self.entry_minus_button)
        
        self.entry_plus_button = QPushButton("+0.01")
        self.entry_plus_button.setMaximumWidth(45)
        self.entry_plus_button.setToolTip("Increase entry by $0.01")
        entry_input_layout.addWidget(self.entry_plus_button)
        
        self.entry_plus_ten_button = QPushButton("+0.1")
        self.entry_plus_ten_button.setMaximumWidth(45)
        self.entry_plus_ten_button.setToolTip("Increase entry by $0.10")
        entry_input_layout.addWidget(self.entry_plus_ten_button)
        
        # Add final stretch
        entry_input_layout.addStretch()
        
        layout.addLayout(entry_input_layout, 0, 1)
        
        # Limit price for STOP LIMIT orders (initially hidden) - Row 1
        self.limit_price_label = QLabel("Limit Price:")
        self.limit_price_label.hide()
        layout.addWidget(self.limit_price_label, 1, 0)
        
        limit_price_layout = QHBoxLayout()
        self.limit_price = ImprovedDoubleSpinBox()
        self.limit_price.setRange(0.0001, 5000.0)
        self.limit_price.setDecimals(4)
        self.limit_price.setSingleStep(0.01)
        self.limit_price.setPrefix("$")
        self.limit_price.setValue(1.0000)
        self.limit_price.setMinimumWidth(120)
        self.limit_price.setToolTip("Maximum price willing to pay (BUY) or minimum price willing to accept (SELL)")
        self.limit_price.hide()
        limit_price_layout.addWidget(self.limit_price)
        
        # Add spacing before buttons
        limit_price_layout.addSpacing(30)
        
        # Add adjustment buttons for limit price
        self.limit_minus_ten_button = QPushButton("-0.1")
        self.limit_minus_ten_button.setMaximumWidth(45)
        self.limit_minus_ten_button.setToolTip("Decrease limit price by $0.10")
        self.limit_minus_ten_button.hide()
        limit_price_layout.addWidget(self.limit_minus_ten_button)
        
        self.limit_minus_button = QPushButton("-0.01")
        self.limit_minus_button.setMaximumWidth(50)
        self.limit_minus_button.setToolTip("Decrease limit price by $0.01")
        self.limit_minus_button.hide()
        limit_price_layout.addWidget(self.limit_minus_button)
        
        self.limit_plus_button = QPushButton("+0.01")
        self.limit_plus_button.setMaximumWidth(50)
        self.limit_plus_button.setToolTip("Increase limit price by $0.01")
        self.limit_plus_button.hide()
        limit_price_layout.addWidget(self.limit_plus_button)
        
        self.limit_plus_ten_button = QPushButton("+0.1")
        self.limit_plus_ten_button.setMaximumWidth(45)
        self.limit_plus_ten_button.setToolTip("Increase limit price by $0.10")
        self.limit_plus_ten_button.hide()
        limit_price_layout.addWidget(self.limit_plus_ten_button)
        
        # Add final stretch
        limit_price_layout.addStretch()
        layout.addLayout(limit_price_layout, 1, 1)
        
        # Stop loss price with adjustment buttons - Row 2  
        layout.addWidget(QLabel("Stop Loss:"), 2, 0)
        
        # Create horizontal layout for stop loss input and adjustment buttons
        sl_input_layout = QHBoxLayout()
        
        self.stop_loss_price = ImprovedDoubleSpinBox()
        self.stop_loss_price.setRange(0.01, 5000.0)  # Max $5,000 per share
        self.stop_loss_price.setDecimals(4)  # Support both penny and sub-penny stocks
        self.stop_loss_price.setSingleStep(0.01)
        self.stop_loss_price.setPrefix("$")
        self.stop_loss_price.setValue(0.01)  # Default stop loss: $0.01
        self.stop_loss_price.setMinimumWidth(120)  # Ensure adequate width
        sl_input_layout.addWidget(self.stop_loss_price)
        
        # Add more spacing before buttons
        sl_input_layout.addSpacing(30)
        
        # Add adjustment buttons
        self.sl_minus_ten_button = QPushButton("-0.1")
        self.sl_minus_ten_button.setMaximumWidth(45)
        self.sl_minus_ten_button.setToolTip("Decrease stop loss by $0.10")
        sl_input_layout.addWidget(self.sl_minus_ten_button)
        
        self.sl_minus_button = QPushButton("-0.01")
        self.sl_minus_button.setMaximumWidth(50)
        self.sl_minus_button.setToolTip("Decrease stop loss by $0.01 (or $0.0001 for stocks < $1)")
        sl_input_layout.addWidget(self.sl_minus_button)
        
        self.sl_plus_button = QPushButton("+0.01")
        self.sl_plus_button.setMaximumWidth(50)
        self.sl_plus_button.setToolTip("Increase stop loss by $0.01 (or $0.0001 for stocks < $1)")
        sl_input_layout.addWidget(self.sl_plus_button)
        
        self.sl_plus_ten_button = QPushButton("+0.1")
        self.sl_plus_ten_button.setMaximumWidth(45)
        self.sl_plus_ten_button.setToolTip("Increase stop loss by $0.10")
        sl_input_layout.addWidget(self.sl_plus_ten_button)
        
        # Add final stretch
        sl_input_layout.addStretch()
        
        layout.addLayout(sl_input_layout, 2, 1)
        
        # Take profit price with R-multiple controls (single target)
        self.take_profit_label = QLabel("Take Profit:")
        layout.addWidget(self.take_profit_label, 3, 0)
        
        # Create horizontal layout for take profit controls
        tp_input_layout = QHBoxLayout()
        
        self.take_profit_price = ImprovedDoubleSpinBox()
        self.take_profit_price.setRange(0.01, 5000.0)  # Max $5,000 per share
        self.take_profit_price.setDecimals(2)
        self.take_profit_price.setSingleStep(0.01)
        self.take_profit_price.setPrefix("$")
        self.take_profit_price.setValue(2.00)  # Default take profit: $2.00
        self.take_profit_price.setMinimumWidth(100)
        tp_input_layout.addWidget(self.take_profit_price)
        
        # Add more spacing before R-multiple controls
        tp_input_layout.addSpacing(20)
        
        # R-multiple controls
        self.r_minus_button = QPushButton("-1R")
        self.r_minus_button.setMaximumWidth(40)
        self.r_minus_button.setToolTip("Decrease take profit by 1R")
        tp_input_layout.addWidget(self.r_minus_button)
        
        self.r_multiple_spinbox = ImprovedDoubleSpinBox()
        self.r_multiple_spinbox.setRange(0.1, 10.0)
        self.r_multiple_spinbox.setValue(2.0)  # Default 2R
        self.r_multiple_spinbox.setSuffix("R")
        self.r_multiple_spinbox.setDecimals(1)
        self.r_multiple_spinbox.setMaximumWidth(60)
        self.r_multiple_spinbox.setToolTip("Risk/Reward ratio (R-multiple)")
        tp_input_layout.addWidget(self.r_multiple_spinbox)
        
        self.r_plus_button = QPushButton("+1R")
        self.r_plus_button.setMaximumWidth(40)
        self.r_plus_button.setToolTip("Increase take profit by 1R")
        tp_input_layout.addWidget(self.r_plus_button)
        
        tp_input_layout.addStretch()
        
        # Create widget to hold the take profit layout so we can hide it
        self.take_profit_widget = QWidget()
        self.take_profit_widget.setLayout(tp_input_layout)
        layout.addWidget(self.take_profit_widget, 3, 1)
        
        # Multiple targets toggle with target count buttons (moved to next row)
        targets_control_layout = QHBoxLayout()
        self.multiple_targets_checkbox = QCheckBox("Multiple Targets")
        self.multiple_targets_checkbox.setToolTip("Enable 2-4 profit targets with partial scaling")
        targets_control_layout.addWidget(self.multiple_targets_checkbox)
        
        # Add target count controls
        self.target_count_label = QLabel("2 targets")
        self.target_count_label.hide()
        targets_control_layout.addWidget(self.target_count_label)
        
        self.decrease_targets_button = QPushButton("-")
        self.decrease_targets_button.setMaximumWidth(25)
        self.decrease_targets_button.setToolTip("Decrease number of targets")
        self.decrease_targets_button.hide()
        targets_control_layout.addWidget(self.decrease_targets_button)
        
        self.increase_targets_button = QPushButton("+")
        self.increase_targets_button.setMaximumWidth(25)
        self.increase_targets_button.setToolTip("Increase number of targets")
        self.increase_targets_button.hide()
        targets_control_layout.addWidget(self.increase_targets_button)
        
        targets_control_layout.addStretch()
        layout.addLayout(targets_control_layout, 4, 0, 1, 4)  # New row spanning all columns
        
        # Add empty label for better spacing
        layout.addWidget(QLabel(""), 1, 3)
        
        # Stop loss quick buttons - create a separate widget below the main inputs
        sl_buttons_widget = QWidget()
        sl_buttons_main_layout = QVBoxLayout(sl_buttons_widget)
        sl_buttons_main_layout.setContentsMargins(0, 5, 0, 0)
        
        # Add a small label
        sl_label = QLabel("Stop Loss Quick Select:")
        sl_label.setStyleSheet("font-size: 11px; color: #666; font-weight: bold;")
        sl_buttons_main_layout.addWidget(sl_label)
        
        # Create the button grid
        sl_buttons_layout = QVBoxLayout()
        
        # First row of SL buttons  
        sl_row1 = QHBoxLayout()
        self.sl_5min_button = QPushButton("Prior 5min")
        self.sl_5min_button.setEnabled(False)  # Will enable when we have data
        self.sl_5min_button.setToolTip("Prior 5-minute bar low")
        self.sl_5min_button.setMaximumHeight(28)  # Make buttons more compact
        sl_row1.addWidget(self.sl_5min_button)
        
        self.sl_current_5min_button = QPushButton("Current 5min")
        self.sl_current_5min_button.setEnabled(False)  # Will enable when we have data
        self.sl_current_5min_button.setToolTip("Current 5-minute bar low")
        self.sl_current_5min_button.setMaximumHeight(28)
        sl_row1.addWidget(self.sl_current_5min_button)
        
        sl_buttons_layout.addLayout(sl_row1)
        
        # Second row of SL buttons
        sl_row2 = QHBoxLayout()
        self.sl_day_button = QPushButton("Day Low")
        self.sl_day_button.setEnabled(False)  # Will enable when we have data
        self.sl_day_button.setToolTip("Current day low")
        self.sl_day_button.setMaximumHeight(28)
        sl_row2.addWidget(self.sl_day_button)
        
        # Percentage stop loss with adjustable value
        pct_layout = QHBoxLayout()
        pct_layout.addWidget(QLabel("Pct:"))
        
        self.sl_pct_spinbox = ImprovedDoubleSpinBox()
        self.sl_pct_spinbox.setRange(0.1, 20.0)
        self.sl_pct_spinbox.setValue(2.0)  # Default 2%
        self.sl_pct_spinbox.setSuffix("%")
        self.sl_pct_spinbox.setDecimals(1)
        self.sl_pct_spinbox.setMaximumWidth(80)
        self.sl_pct_spinbox.setMaximumHeight(28)
        self.sl_pct_spinbox.setToolTip("Percentage below entry price for stop loss")
        pct_layout.addWidget(self.sl_pct_spinbox)
        
        # Price display label
        self.sl_pct_price_label = QLabel("$0.00")
        self.sl_pct_price_label.setStyleSheet("font-size: 10px; color: gray;")
        self.sl_pct_price_label.setMaximumHeight(28)
        self.sl_pct_price_label.setToolTip("Calculated stop loss price")
        pct_layout.addWidget(self.sl_pct_price_label)
        
        self.sl_pct_button = QPushButton("Apply")
        self.sl_pct_button.setToolTip("Apply percentage stop loss")
        self.sl_pct_button.setMaximumHeight(28)
        self.sl_pct_button.setMaximumWidth(60)
        pct_layout.addWidget(self.sl_pct_button)
        
        sl_row2.addLayout(pct_layout)
        
        sl_buttons_layout.addLayout(sl_row2)
        
        sl_buttons_main_layout.addLayout(sl_buttons_layout)
        
        # Add the SL buttons widget spanning across columns
        layout.addWidget(sl_buttons_widget, 9, 0, 1, 4)  # Updated row number
        
        # Multiple profit targets section (initially hidden)
        self.create_multiple_targets_section(layout)
        
        # Price info labels
        self.price_info_label = QLabel("Last: N/A | Bid: N/A | Ask: N/A")
        self.price_info_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.price_info_label, 10, 0, 1, 4)  # Updated row number
        
        group.setLayout(layout)
        return group
        
    def create_multiple_targets_section(self, layout):
        """Create multiple profit targets section with separate % and R-multiple controls"""
        # Multiple targets widgets (initially hidden)
        self.targets_widgets = []
        
        # Target 1
        target1_label = QLabel("Target 1:")
        target1_label.hide()
        layout.addWidget(target1_label, 5, 0)
        
        # Create horizontal layout for target 1 controls with proper spacing
        target1_layout = QHBoxLayout()
        
        # Price field
        target1_price = ImprovedDoubleSpinBox()
        target1_price.setRange(0.01, 5000.0)
        target1_price.setDecimals(2)
        target1_price.setSingleStep(0.01)
        target1_price.setPrefix("$")
        target1_price.setMaximumWidth(100)
        target1_price.hide()
        target1_layout.addWidget(target1_price)
        
        # Add spacing to separate from adjustment buttons
        target1_layout.addSpacing(15)
        
        # Percentage field
        target1_percent = ImprovedSpinBox()
        target1_percent.setRange(10, 100)
        target1_percent.setValue(50)
        target1_percent.setSuffix("%")
        target1_percent.setMaximumWidth(60)
        target1_percent.setToolTip("Percentage of position to close at this target")
        target1_percent.hide()
        target1_layout.addWidget(target1_percent)
        
        # R-multiple field
        target1_r_multiple = ImprovedDoubleSpinBox()
        target1_r_multiple.setRange(0.1, 10.0)
        target1_r_multiple.setValue(2.0)
        target1_r_multiple.setSuffix("R")
        target1_r_multiple.setDecimals(1)
        target1_r_multiple.setMaximumWidth(60)
        target1_r_multiple.setToolTip("Risk/reward ratio for this target")
        target1_r_multiple.hide()
        target1_layout.addWidget(target1_r_multiple)
        
        # Share quantity display
        target1_shares = QLabel("0 shs")
        target1_shares.setMinimumWidth(50)
        target1_shares.setAlignment(Qt.AlignmentFlag.AlignCenter)
        target1_shares.setStyleSheet("font-size: 10px; color: #888888; font-weight: bold;")
        target1_shares.setToolTip("Number of shares allocated to this target")
        target1_shares.hide()
        target1_layout.addWidget(target1_shares)
        
        # Add stretch to align with other rows
        target1_layout.addStretch()
        
        # Create widget to hold the layout and hide it
        target1_widget = QWidget()
        target1_widget.setLayout(target1_layout)
        target1_widget.hide()
        layout.addWidget(target1_widget, 5, 1)
        
        # Target 2
        target2_label = QLabel("Target 2:")
        target2_label.hide()
        layout.addWidget(target2_label, 6, 0)
        
        # Create horizontal layout for target 2 controls with proper spacing
        target2_layout = QHBoxLayout()
        
        # Price field
        target2_price = ImprovedDoubleSpinBox()
        target2_price.setRange(0.01, 5000.0)
        target2_price.setDecimals(2)
        target2_price.setSingleStep(0.01)
        target2_price.setPrefix("$")
        target2_price.setMaximumWidth(100)
        target2_price.hide()
        target2_layout.addWidget(target2_price)
        
        # Add spacing to separate from adjustment buttons
        target2_layout.addSpacing(15)
        
        # Percentage field
        target2_percent = ImprovedSpinBox()
        target2_percent.setRange(10, 100)
        target2_percent.setValue(30)
        target2_percent.setSuffix("%")
        target2_percent.setMaximumWidth(60)
        target2_percent.setToolTip("Percentage of position to close at this target")
        target2_percent.hide()
        target2_layout.addWidget(target2_percent)
        
        # R-multiple field
        target2_r_multiple = ImprovedDoubleSpinBox()
        target2_r_multiple.setRange(0.1, 10.0)
        target2_r_multiple.setValue(4.0)
        target2_r_multiple.setSuffix("R")
        target2_r_multiple.setDecimals(1)
        target2_r_multiple.setMaximumWidth(60)
        target2_r_multiple.setToolTip("Risk/reward ratio for this target")
        target2_r_multiple.hide()
        target2_layout.addWidget(target2_r_multiple)
        
        # Share quantity display
        target2_shares = QLabel("0 shs")
        target2_shares.setMinimumWidth(50)
        target2_shares.setAlignment(Qt.AlignmentFlag.AlignCenter)
        target2_shares.setStyleSheet("font-size: 10px; color: #888888; font-weight: bold;")
        target2_shares.setToolTip("Number of shares allocated to this target")
        target2_shares.hide()
        target2_layout.addWidget(target2_shares)
        
        # Add stretch to align with other rows
        target2_layout.addStretch()
        
        # Create widget to hold the layout and hide it
        target2_widget = QWidget()
        target2_widget.setLayout(target2_layout)
        target2_widget.hide()
        layout.addWidget(target2_widget, 6, 1)
        
        # Target 3
        target3_label = QLabel("Target 3:")
        target3_label.hide()
        layout.addWidget(target3_label, 7, 0)
        
        # Create horizontal layout for target 3 controls with proper spacing
        target3_layout = QHBoxLayout()
        
        # Price field
        target3_price = ImprovedDoubleSpinBox()
        target3_price.setRange(0.01, 5000.0)
        target3_price.setDecimals(2)
        target3_price.setSingleStep(0.01)
        target3_price.setPrefix("$")
        target3_price.setMaximumWidth(100)
        target3_price.hide()
        target3_layout.addWidget(target3_price)
        
        # Add spacing to separate from adjustment buttons
        target3_layout.addSpacing(15)
        
        # Percentage field
        target3_percent = ImprovedSpinBox()
        target3_percent.setRange(10, 100)
        target3_percent.setValue(20)
        target3_percent.setSuffix("%")
        target3_percent.setMaximumWidth(60)
        target3_percent.setToolTip("Percentage of position to close at this target")
        target3_percent.hide()
        target3_layout.addWidget(target3_percent)
        
        # R-multiple field
        target3_r_multiple = ImprovedDoubleSpinBox()
        target3_r_multiple.setRange(0.1, 10.0)
        target3_r_multiple.setValue(3.0)
        target3_r_multiple.setSuffix("R")
        target3_r_multiple.setDecimals(1)
        target3_r_multiple.setMaximumWidth(60)
        target3_r_multiple.setToolTip("Risk/reward ratio for this target")
        target3_r_multiple.hide()
        target3_layout.addWidget(target3_r_multiple)
        
        # Share quantity display
        target3_shares = QLabel("0 shs")
        target3_shares.setMinimumWidth(50)
        target3_shares.setAlignment(Qt.AlignmentFlag.AlignCenter)
        target3_shares.setStyleSheet("font-size: 10px; color: #888888; font-weight: bold;")
        target3_shares.setToolTip("Number of shares allocated to this target")
        target3_shares.hide()
        target3_layout.addWidget(target3_shares)
        
        # Add stretch to align with other rows
        target3_layout.addStretch()
        
        # Create widget to hold the layout and hide it
        target3_widget = QWidget()
        target3_widget.setLayout(target3_layout)
        target3_widget.hide()
        layout.addWidget(target3_widget, 7, 1)
        
        # Store references to all target widgets
        self.profit_targets = [
            {
                'price': target1_price, 
                'percent': target1_percent, 
                'r_multiple': target1_r_multiple,
                'shares': target1_shares,
                'label': target1_label,
                'widget': target1_widget
            },
            {
                'price': target2_price, 
                'percent': target2_percent, 
                'r_multiple': target2_r_multiple,
                'shares': target2_shares,
                'label': target2_label,
                'widget': target2_widget
            },
            {
                'price': target3_price, 
                'percent': target3_percent, 
                'r_multiple': target3_r_multiple,
                'shares': target3_shares,
                'label': target3_label,
                'widget': target3_widget
            }
        ]
        
    def create_risk_section(self) -> QGroupBox:
        """Create risk management section"""
        group = QGroupBox("Risk Management")
        layout = QGridLayout()
        
        # Risk percentage slider (full row)
        layout.addWidget(QLabel("Risk %:"), 0, 0)
        self.risk_slider = QSlider(Qt.Orientation.Horizontal)
        self.risk_slider.setRange(1, 1000)  # 0.01% to 10%
        self.risk_slider.setValue(int(TRADING_CONFIG['default_risk_percent'] * 100))
        self.risk_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.risk_slider.setTickInterval(10)
        layout.addWidget(self.risk_slider, 0, 1)
        
        self.risk_label = QLabel(f"{TRADING_CONFIG['default_risk_percent']:.2f}%")
        self.risk_label.setMinimumWidth(50)
        self.risk_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.risk_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.risk_label, 0, 2)
        
        # Position size with risk adjustment buttons
        layout.addWidget(QLabel("Position Size:"), 1, 0)
        
        # Position size controls layout
        position_controls_layout = QHBoxLayout()
        
        self.risk_minus_button = QPushButton("-0.01%")
        self.risk_minus_button.setMaximumWidth(50)
        self.risk_minus_button.setToolTip("Decrease risk by 0.01%")
        position_controls_layout.addWidget(self.risk_minus_button)
        
        self.position_size = ImprovedSpinBox()
        self.position_size.setRange(1, 999999)
        self.position_size.setSuffix(" shares")
        self.position_size.setToolTip("Enter shares manually or use risk % slider to auto-calculate")
        self.position_size.setStyleSheet("font-weight: bold;")  # Make it look editable
        position_controls_layout.addWidget(self.position_size)
        
        self.risk_plus_button = QPushButton("+0.01%")
        self.risk_plus_button.setMaximumWidth(50)
        self.risk_plus_button.setToolTip("Increase risk by 0.01%")
        position_controls_layout.addWidget(self.risk_plus_button)
        
        layout.addLayout(position_controls_layout, 1, 1, 1, 2)
        
        # Order value
        layout.addWidget(QLabel("Order Value:"), 2, 0)
        self.order_value_label = QLabel("$0.00")
        self.order_value_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.order_value_label, 2, 1, 1, 2)
        
        # Dollar risk
        layout.addWidget(QLabel("$ Risk:"), 3, 0)
        self.dollar_risk_label = QLabel("$0.00")
        self.dollar_risk_label.setStyleSheet("color: red;")
        layout.addWidget(self.dollar_risk_label, 3, 1, 1, 2)
        
        group.setLayout(layout)
        return group
        
    def create_summary_section(self) -> QGroupBox:
        """Create order summary section"""
        group = QGroupBox("Order Summary")
        layout = QVBoxLayout()
        
        self.summary_label = QLabel("Please enter order details...")
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextFormat(Qt.TextFormat.RichText)  # Enable HTML formatting
        self.summary_label.setStyleSheet("""
            QLabel {
                background-color: #f8f8f8;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.summary_label)
        
        # Warning label
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: orange; font-weight: bold;")
        self.warning_label.setWordWrap(True)
        self.warning_label.hide()
        layout.addWidget(self.warning_label)
        
        group.setLayout(layout)
        return group
        
    def create_action_buttons(self) -> QWidget:
        """Create action buttons"""
        widget = QWidget()
        layout = QHBoxLayout()
        
        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 10px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        layout.addWidget(self.clear_button)
        
        layout.addStretch()
        
        # Submit button
        self.submit_button = QPushButton("Submit Order")
        self.submit_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 10px;
                min-width: 150px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.submit_button.setEnabled(False)  # Disabled until valid input
        layout.addWidget(self.submit_button)
        
        widget.setLayout(layout)
        return widget
        
    def setup_connections(self):
        """Setup signal connections"""
        # Price changes trigger calculations
        self.entry_price.valueChanged.connect(self.calculate_position_size)
        self.entry_price.valueChanged.connect(self.calculate_target_prices)
        self.entry_price.valueChanged.connect(self.update_sl_pct_price_display)  # Update pct price display
        self.entry_price.valueChanged.connect(self.auto_adjust_take_profit)  # Auto-adjust take profit to maintain R-multiple
        self.entry_price.valueChanged.connect(self.update_decimal_places_for_all_prices)  # Update decimal places based on entry price
        self.entry_price.valueChanged.connect(self.update_limit_price_for_stop_limit)  # Update limit price for STOP LIMIT orders
        self.entry_price.valueChanged.connect(self.validate_inputs)  # Validate when entry price changes
        self.stop_loss_price.valueChanged.connect(self.calculate_position_size)
        self.stop_loss_price.valueChanged.connect(self.calculate_target_prices)
        self.stop_loss_price.valueChanged.connect(self.auto_adjust_take_profit)  # Auto-adjust take profit to maintain R-multiple
        self.stop_loss_price.valueChanged.connect(self.validate_inputs)  # Validate when stop loss changes
        self.take_profit_price.valueChanged.connect(self.update_summary)
        
        # Risk slider and adjustment buttons
        self.risk_slider.valueChanged.connect(self.on_risk_changed)
        self.risk_minus_button.clicked.connect(self.on_risk_minus_clicked)
        self.risk_plus_button.clicked.connect(self.on_risk_plus_clicked)
        
        # Position size changes
        self.position_size.valueChanged.connect(self.on_position_size_changed)
        
        # Symbol input
        self.symbol_input.textChanged.connect(self.on_symbol_changed)
        self.symbol_input.returnPressed.connect(self.on_fetch_price)  # Enter key triggers fetch
        
        # Direction/Order type changes
        self.direction_group.buttonClicked.connect(self.update_summary)
        self.direction_group.buttonClicked.connect(self.update_sl_pct_price_display)  # Update pct price when direction changes
        self.order_type_group.buttonClicked.connect(self.update_summary)
        self.order_type_group.buttonClicked.connect(self.on_order_type_changed)
        
        # Buttons
        self.fetch_price_button.clicked.connect(self.on_fetch_price)
        self.clear_button.clicked.connect(self.clear_form)
        self.submit_button.clicked.connect(self.on_submit_order)
        
        # Stop loss quick buttons
        self.sl_5min_button.clicked.connect(self.on_sl_5min_clicked)
        self.sl_current_5min_button.clicked.connect(self.on_sl_current_5min_clicked)
        self.sl_day_button.clicked.connect(self.on_sl_day_clicked)
        self.sl_pct_button.clicked.connect(self.on_sl_pct_clicked)
        self.sl_pct_spinbox.valueChanged.connect(self.update_sl_pct_price_display)
        
        # Stop loss adjustment buttons
        self.sl_minus_ten_button.clicked.connect(self.on_sl_minus_ten_clicked)
        self.sl_minus_button.clicked.connect(self.on_sl_minus_clicked)
        self.sl_plus_button.clicked.connect(self.on_sl_plus_clicked)
        self.sl_plus_ten_button.clicked.connect(self.on_sl_plus_ten_clicked)
        
        # Entry price adjustment buttons
        self.entry_minus_ten_button.clicked.connect(self.on_entry_minus_ten_clicked)
        self.entry_minus_button.clicked.connect(self.on_entry_minus_clicked)
        self.entry_plus_button.clicked.connect(self.on_entry_plus_clicked)
        self.entry_plus_ten_button.clicked.connect(self.on_entry_plus_ten_clicked)
        
        # Limit price adjustment buttons
        self.limit_minus_ten_button.clicked.connect(self.on_limit_minus_ten_clicked)
        self.limit_minus_button.clicked.connect(self.on_limit_minus_clicked)
        self.limit_plus_button.clicked.connect(self.on_limit_plus_clicked)
        self.limit_plus_ten_button.clicked.connect(self.on_limit_plus_ten_clicked)
        
        # R-multiple controls
        self.r_minus_button.clicked.connect(self.on_r_minus_clicked)
        self.r_plus_button.clicked.connect(self.on_r_plus_clicked)
        self.r_multiple_spinbox.valueChanged.connect(self.on_r_multiple_changed)
        self.take_profit_price.valueChanged.connect(self.on_take_profit_price_manual_changed)
        
        # Multiple targets checkbox
        self.multiple_targets_checkbox.toggled.connect(self.on_multiple_targets_toggled)
        
        # Target count buttons
        self.increase_targets_button.clicked.connect(self.on_increase_targets_clicked)
        self.decrease_targets_button.clicked.connect(self.on_decrease_targets_clicked)
        
        # Connect target widget changes
        for target in self.profit_targets:
            target['price'].valueChanged.connect(self.update_summary)
            target['price'].valueChanged.connect(self.on_target_price_changed)
            target['price'].valueChanged.connect(self.on_target_prices_changed)  # For chart lines
            target['percent'].valueChanged.connect(self.calculate_target_percentages)
            target['r_multiple'].valueChanged.connect(self.on_target_r_multiple_changed)
        
        # Connect price changes for chart synchronization
        self.entry_price.valueChanged.connect(self.on_entry_price_changed)
        self.stop_loss_price.valueChanged.connect(self.on_stop_loss_price_changed)
        self.take_profit_price.valueChanged.connect(self.on_take_profit_price_changed)
        self.limit_price.valueChanged.connect(self.on_limit_price_changed)
        
    def _validate_price(self, price: float, price_type: str) -> bool:
        """Validate that a price is within reasonable bounds"""
        if price < 0.01 or price > 5000.0:
            logger.error(f"Invalid {price_type} price: ${price:.2f} (must be between $0.01 and $5000)")
            return False
        return True
        
    def on_entry_price_changed(self, value: float):
        """Handle entry price change and emit signal"""
        # Validate and block extreme values
        if not self._validate_price(value, "entry"):
            logger.error(f"Extreme entry price detected: ${value:.2f}, blocking update")
            import traceback
            traceback.print_stack()
            # Reset to a reasonable value
            self.entry_price.valueChanged.disconnect()
            self.entry_price.setValue(1.00)  # Reset to default
            self.entry_price.valueChanged.connect(self.on_entry_price_changed)
            return
        self.entry_price_changed.emit(value)
        
    def on_stop_loss_price_changed(self, value: float):
        """Handle stop loss price change and emit signal"""
        self.stop_loss_changed.emit(value)
        
        # When stop loss changes, recalculate take profit based on current R-multiple
        # This ensures the take profit is updated automatically when stop loss is adjusted
        if not self._updating_take_profit and not self.use_multiple_targets:
            try:
                entry = self.entry_price.value()
                r_multiple = self.r_multiple_spinbox.value()
                
                if entry > 0 and value > 0 and r_multiple > 0:
                    # Calculate risk distance
                    risk_distance = abs(entry - value)
                    direction = "BUY" if self.long_button.isChecked() else "SELL"
                    
                    # Calculate take profit based on R-multiple
                    if direction == "BUY":
                        take_profit = entry + (r_multiple * risk_distance)
                    else:
                        take_profit = entry - (r_multiple * risk_distance)
                    
                    # Validate take profit is within reasonable bounds
                    if take_profit > 10000.0:
                        take_profit = 10000.0
                    elif take_profit < 0.01:
                        take_profit = 0.01
                    
                    # Round to proper tick size
                    take_profit = self.round_to_tick_size(take_profit)
                    
                    # Update take profit price (block signals to avoid loops)
                    self._updating_take_profit = True
                    self.take_profit_price.blockSignals(True)
                    self.take_profit_price.setValue(take_profit)
                    self.take_profit_price.blockSignals(False)
                    self._updating_take_profit = False
                    
                    # Manually emit chart synchronization signal
                    self.on_take_profit_price_changed(take_profit)
                    
                    # Re-validate inputs and update summary
                    self.update_summary()
                    
                    logger.info(f"Auto-updated take profit to ${take_profit:.2f} based on {r_multiple:.1f}R and new stop loss ${value:.2f}")
                    
            except Exception as e:
                logger.error(f"Error updating take profit on stop loss change: {str(e)}")
                self._updating_take_profit = False
        
    def on_take_profit_price_changed(self, value: float):
        """Handle take profit price change and emit signal"""
        self.take_profit_changed.emit(value)
        
    def on_limit_price_changed(self, value: float):
        """Handle limit price change and emit signal"""
        # Mark that the user has manually adjusted the limit price
        self._limit_price_manually_adjusted = True
        
        # Calculate and store the new absolute offset
        entry_price = self.entry_price.value()
        if entry_price > 0:
            self._limit_price_offset = value - entry_price
            logger.debug(f"User manually adjusted limit price to ${value:.4f}, new offset: ${self._limit_price_offset:.4f}")
        else:
            logger.debug(f"User manually adjusted limit price to ${value:.4f}, but entry price is 0")
            
        self.limit_price_changed.emit(value)
        
    def on_target_prices_changed(self):
        """Handle multiple target prices change and emit signal"""
        if self.use_multiple_targets:
            target_prices = []
            for i in range(self.active_target_count):
                target = self.profit_targets[i]
                price = target['price'].value()
                if price > 0.01:  # Valid price
                    target_prices.append(price)
            self.target_prices_changed.emit(target_prices)
        
    def on_risk_changed(self, value: int):
        """Handle risk slider change"""
        risk_percent = value / 100.0
        self.risk_label.setText(f"{risk_percent:.2f}%")
        self.calculate_position_size()
    
    def on_position_size_changed(self, shares: int):
        """Handle manual position size change - calculate risk % accordingly"""
        try:
            # Skip if this change came from risk slider calculation
            if self._updating_from_risk:
                return
                
            # Temporarily disconnect to avoid circular updates
            self.risk_slider.valueChanged.disconnect()
            
            entry = self.entry_price.value()
            stop_loss = self.stop_loss_price.value()
            
            if entry > 0 and stop_loss > 0 and shares > 0 and self.account_value > 0:
                # Calculate dollar risk
                risk_per_share = abs(entry - stop_loss)
                dollar_risk = shares * risk_per_share
                
                # Calculate risk percentage
                risk_percent = (dollar_risk / self.account_value) * 100
                
                # Update slider and label (clamped to slider range)
                risk_percent_clamped = max(0.01, min(10.0, risk_percent))
                slider_value = int(risk_percent_clamped * 100)
                
                self.risk_slider.setValue(slider_value)
                self.risk_label.setText(f"{risk_percent:.2f}%")
                
                # Update order value and dollar risk displays
                order_value = shares * entry
                self.order_value_label.setText(f"${order_value:,.2f}")
                self.dollar_risk_label.setText(f"${dollar_risk:,.2f}")
                
                # Update summary
                self.update_summary()
                
                # Update target share quantities when position size is manually changed
                self.update_target_share_quantities()
                
                logger.info(f"Manual position size: {shares} shares → {risk_percent:.2f}% risk")
            
            # Reconnect the signal
            self.risk_slider.valueChanged.connect(self.on_risk_changed)
            
        except Exception as e:
            logger.error(f"Error calculating risk from position size: {str(e)}")
            # Reconnect even if there was an error
            self.risk_slider.valueChanged.connect(self.on_risk_changed)
            
    def on_risk_minus_clicked(self):
        """Handle risk percentage decrease button click"""
        try:
            current_value = self.risk_slider.value()
            new_value = max(1, current_value - 1)  # 0.01% decrease, minimum 0.01%
            self.risk_slider.setValue(new_value)
            logger.info(f"Decreased risk to {new_value/100:.2f}%")
        except Exception as e:
            logger.error(f"Error decreasing risk: {str(e)}")
            
    def on_risk_plus_clicked(self):
        """Handle risk percentage increase button click"""
        try:
            current_value = self.risk_slider.value()
            new_value = min(1000, current_value + 1)  # 0.01% increase, maximum 10%
            self.risk_slider.setValue(new_value)
            logger.info(f"Increased risk to {new_value/100:.2f}%")
        except Exception as e:
            logger.error(f"Error increasing risk: {str(e)}")
        
    def on_symbol_changed(self, text: str):
        """Handle symbol input change"""
        # Convert to uppercase
        self.symbol_input.setText(text.upper())
        self.validate_inputs()
        
    def calculate_position_size(self):
        """Calculate position size based on risk"""
        try:
            entry = self.entry_price.value()
            stop_loss = self.stop_loss_price.value()
            
            if entry <= 0 or stop_loss <= 0:
                self.position_size.setValue(0)
                self.order_value_label.setText("$0.00")
                self.dollar_risk_label.setText("$0.00")
                return
                
            # Get risk percentage
            risk_percent = self.risk_slider.value() / 100.0
            
            # Set flag to prevent circular updates
            self._updating_from_risk = True
            
            # Use RiskService for calculations
            risk_service = get_risk_service()
            if risk_service and risk_service.is_initialized():
                # Determine order type and limit price
                order_type = 'STOPLMT' if self.stop_limit_button.isChecked() else 'LMT'
                limit_price = self.limit_price.value() if order_type == 'STOPLMT' else None
                
                result = risk_service.calculate_position_size(
                    entry_price=entry,
                    stop_loss=stop_loss,
                    risk_percent=risk_percent,
                    order_type=order_type,
                    limit_price=limit_price
                )
                
                shares = result['shares']
                order_value = result['position_value']
                dollar_risk = result['dollar_risk']
            else:
                # Fallback calculation
                # Determine which price to use for calculations
                order_type = 'STOPLMT' if self.stop_limit_button.isChecked() else 'LMT'
                if order_type == 'STOPLMT':
                    price_for_calculations = self.limit_price.value()
                else:
                    price_for_calculations = entry
                
                dollar_risk = self.account_value * (risk_percent / 100.0)
                risk_per_share = abs(price_for_calculations - stop_loss)
                if risk_per_share > 0:
                    shares = int(dollar_risk / risk_per_share)
                else:
                    shares = 0
                order_value = shares * price_for_calculations
                
            # Update displays
            self.position_size.setValue(shares)
            self.order_value_label.setText(f"${order_value:,.2f}")
            self.dollar_risk_label.setText(f"${dollar_risk:,.2f}")
            
            # Reset flag
            self._updating_from_risk = False
            
            self.update_summary()
            
            # Update target share quantities when position size changes
            self.update_target_share_quantities()
            
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            # Reset flag even on error
            self._updating_from_risk = False
            
    def update_summary(self):
        """Update order summary"""
        symbol = self.symbol_input.text()
        if not symbol:
            self.summary_label.setText("Please enter order details...")
            self.submit_button.setEnabled(False)
            return
            
        direction = "LONG" if self.long_button.isChecked() else "SHORT"
        order_type = "LIMIT" if self.limit_button.isChecked() else "MARKET"
        shares = self.position_size.value()
        entry = self.entry_price.value()
        stop_loss = self.stop_loss_price.value()
        
        # Calculate order value and percentages
        order_value = shares * entry
        portfolio_pct = (order_value / self.account_value * 100) if self.account_value > 0 else 0
        bp_pct = (order_value / self.buying_power * 100) if self.buying_power > 0 else 0
        
        if self.use_multiple_targets:
            # Show multiple targets summary with R-multiples (only active targets)
            targets_text = ""
            for i in range(self.active_target_count):
                target = self.profit_targets[i]
                price = target['price'].value()
                percent = target['percent'].value()
                r_multiple = target['r_multiple'].value()
                if price > 0:
                    targets_text += f"<br>        Target {i+1}: ${price:.2f} ({percent}%, {r_multiple:.1f}R)"
            
            summary = f"""
        <b>{direction}</b> {shares} shares of <b>{symbol}</b><br>
        Entry: ${entry:.2f} ({order_type})<br>
        Stop Loss: ${stop_loss:.2f}{targets_text}<br>
        Total Value: ${order_value:,.2f} (<span style="color: red;">{portfolio_pct:.1f}% of Portfolio</span>, {bp_pct:.1f}% of BP)
        """
        else:
            # Show single target summary
            take_profit = self.take_profit_price.value()
            r_multiple = self.r_multiple_spinbox.value()
            summary = f"""
        <b>{direction}</b> {shares} shares of <b>{symbol}</b><br>
        Entry: ${entry:.2f} ({order_type})<br>
        Stop Loss: ${stop_loss:.2f}<br>
        Take Profit: ${take_profit:.2f} ({r_multiple:.1f}R)<br>
        Total Value: ${order_value:,.2f} (<span style="color: red;">{portfolio_pct:.1f}% of Portfolio</span>, {bp_pct:.1f}% of BP)
        """
        
        self.summary_label.setText(summary.strip())
        self.validate_inputs()
        
    def validate_inputs(self) -> bool:
        """Validate all inputs and enable/disable submit button"""
        valid = True
        warnings = []
        
        # Check symbol
        if not self.symbol_input.text():
            valid = False
            
        # Check prices
        entry = self.entry_price.value()
        stop_loss = self.stop_loss_price.value()
        
        if entry <= 0 or stop_loss <= 0:
            valid = False
            
        # Check profit targets based on mode
        if self.use_multiple_targets:
            # Validate multiple targets
            target_count = 0
            total_percent = 0
            
            # Only validate active targets (not hidden ones)
            for i in range(self.active_target_count):
                target = self.profit_targets[i]
                price = target['price'].value()
                percent = target['percent'].value()
                
                if price > 0.01:  # Valid price threshold
                    target_count += 1
                    total_percent += percent
                    
                    # Direction-specific target validation
                    if self.long_button.isChecked():
                        if price <= entry:
                            valid = False
                            warnings.append(f"Target {i+1} must be above entry for LONG")
                    else:  # SHORT
                        if price >= entry:
                            valid = False
                            warnings.append(f"Target {i+1} must be below entry for SHORT")
            
            if target_count == 0:
                valid = False
                warnings.append("At least one profit target required")
            
            if total_percent != 100:
                warnings.append(f"Target percentages total {total_percent}% (should be 100%)")
                
        else:
            # Validate single target
            take_profit = self.take_profit_price.value()
            if take_profit <= 0:
                valid = False
                
            # Direction-specific validation
            if self.long_button.isChecked():
                if take_profit <= entry:
                    valid = False
                    warnings.append("Take profit must be above entry for LONG")
            else:  # SHORT
                if take_profit >= entry:
                    valid = False
                    warnings.append("Take profit must be below entry for SHORT")
            
        # Check position size
        if self.position_size.value() <= 0:
            valid = False
            warnings.append("Position size is 0 - adjust risk or stop loss")
            
        # Direction-specific stop loss validation
        if self.long_button.isChecked():
            if stop_loss >= entry:
                valid = False
                warnings.append("Stop loss must be below entry for LONG")
        else:  # SHORT
            if stop_loss <= entry:
                valid = False
                warnings.append("Stop loss must be above entry for SHORT")
        
        # STOP LIMIT order validation
        if self.stop_limit_button.isChecked():
            limit_price = self.limit_price.value()
            if limit_price <= 0:
                valid = False
                warnings.append("Limit price must be set for STOP LIMIT orders")
            else:
                # For STOP LIMIT BUY: entry (stop) < limit price
                # For STOP LIMIT SELL: entry (stop) > limit price
                if self.long_button.isChecked():
                    if limit_price < entry:
                        warnings.append("For STOP LIMIT BUY: Limit price should be >= stop price")
                else:  # SHORT/SELL
                    if limit_price > entry:
                        warnings.append("For STOP LIMIT SELL: Limit price should be <= stop price")
                
        # Update UI
        self.submit_button.setEnabled(valid)
        
        if warnings:
            self.warning_label.setText("\n".join(warnings))
            self.warning_label.show()
        else:
            self.warning_label.hide()
            
        return valid
        
    def on_fetch_price(self):
        """Handle fetch price button click"""
        symbol = self.symbol_input.text()
        if symbol:
            self.fetch_price_button.setText("Fetching...")
            self.fetch_price_button.setEnabled(False)
            self.fetch_price_requested.emit(symbol)
            
    def on_submit_order(self):
        """Handle submit order button click"""
        if not self.validate_inputs():
            return
            
        # Determine order type
        if self.limit_button.isChecked():
            order_type = 'LMT'
        elif self.market_button.isChecked():
            order_type = 'MKT'
        else:  # STOP LIMIT
            order_type = 'STOPLMT'
        
        # Ensure target share quantities are up to date before submission
        self.update_target_share_quantities()
        
        # Gather order data
        order_data = {
            'symbol': self.symbol_input.text(),
            'direction': 'BUY' if self.long_button.isChecked() else 'SELL',
            'order_type': order_type,
            'quantity': self.position_size.value(),
            'entry_price': self.entry_price.value(),
            'stop_loss': self.stop_loss_price.value(),
            'take_profit': self.take_profit_price.value(),
            'risk_percent': self.risk_slider.value() / 100.0,
            'use_multiple_targets': self.use_multiple_targets,
            'profit_targets': self.get_adjusted_profit_target_data(),  # Use adjusted targets
        }
        
        # Add limit price if STOP LIMIT order
        if order_type == 'STOPLMT':
            order_data['limit_price'] = self.limit_price.value()
        
        self.order_submitted.emit(order_data)
        
    def clear_form(self):
        """Clear all form inputs"""
        self.symbol_input.clear()
        self.entry_price.setValue(1.00)  # Reset to default $1.00
        self.stop_loss_price.setValue(0.01)  # Reset to default $0.01
        self.take_profit_price.setValue(2.00)  # Reset to default $2.00
        self.position_size.setValue(0)
        self.risk_slider.setValue(int(TRADING_CONFIG['default_risk_percent'] * 100))
        self.long_button.setChecked(True)
        self.limit_button.setChecked(True)
        self.order_value_label.setText("$0.00")
        self.dollar_risk_label.setText("$0.00")
        self.summary_label.setText("Please enter order details...")
        self.price_info_label.setText("Last: N/A | Bid: N/A | Ask: N/A")
        self.warning_label.hide()
        self.submit_button.setEnabled(False)
        
        # Reset multiple targets
        self.multiple_targets_checkbox.setChecked(False)
        self.active_target_count = 2  # Reset to default 2 targets
        for i, target in enumerate(self.profit_targets):
            target['price'].setValue(0)
            target['percent'].setValue(50 if i == 0 else 50 if i == 1 else 0)  # Default 50/50 for 2 targets
            target['r_multiple'].setValue(2.0 if i == 0 else 5.0 if i == 1 else 3.0)  # Reset to 2R, 5R, 3R
        
        # Reset limit price
        self.limit_price.setValue(1.00)
        self.limit_price_label.hide()
        self.limit_price.hide()
        
    def set_account_value(self, value: float):
        """Set account value for position sizing calculations"""
        self.account_value = value
        self.calculate_position_size()
        
    def set_buying_power(self, buying_power: float):
        """Set buying power for position validation"""
        self.buying_power = buying_power
        self.update_summary()
        
    def set_risk_calculator(self, risk_calculator):
        """Legacy method - risk calculations now handled through RiskService"""
        # Kept for compatibility, but no longer stores the calculator
        self.calculate_position_size()
        
    def on_sl_5min_clicked(self):
        """Handle 5min low stop loss button click"""
        if 'prior_5min_low' in self.stop_loss_data:
            # Apply smart adjustment based on stock price
            price = self.stop_loss_data['prior_5min_low']
            adjusted_price = self.apply_smart_sl_adjustment(price)
            adjusted_price = self.round_to_tick_size(adjusted_price)  # Round to proper tick size
            self.stop_loss_price.setValue(adjusted_price)
            logger.info(f"Set stop loss to prior 5min low: ${adjusted_price:.4f}")
        elif 'estimated_5min_low' in self.stop_loss_data:
            price = self.stop_loss_data['estimated_5min_low']
            adjusted_price = self.apply_smart_sl_adjustment(price)
            adjusted_price = self.round_to_tick_size(adjusted_price)  # Round to proper tick size
            self.stop_loss_price.setValue(adjusted_price)
            logger.info(f"Set stop loss to estimated 5min low: ${adjusted_price:.4f}")
            
    def on_sl_current_5min_clicked(self):
        """Handle current 5min low stop loss button click"""
        if 'current_5min_low' in self.stop_loss_data:
            # Apply smart adjustment based on stock price
            price = self.stop_loss_data['current_5min_low']
            adjusted_price = self.apply_smart_sl_adjustment(price)
            adjusted_price = self.round_to_tick_size(adjusted_price)  # Round to proper tick size
            self.stop_loss_price.setValue(adjusted_price)
            logger.info(f"Set stop loss to current 5min low: ${adjusted_price:.4f}")
        
    def on_sl_day_clicked(self):
        """Handle day low stop loss button click"""
        if 'day_low' in self.stop_loss_data:
            price = self.round_to_tick_size(self.stop_loss_data['day_low'])
            self.stop_loss_price.setValue(price)
            logger.info(f"Set stop loss to day low: ${price:.2f}")
        elif 'estimated_day_low' in self.stop_loss_data:
            price = self.round_to_tick_size(self.stop_loss_data['estimated_day_low'])
            self.stop_loss_price.setValue(price)
            logger.info(f"Set stop loss to estimated day low: ${price:.2f}")
            
    def on_sl_pct_clicked(self):
        """Handle percentage stop loss button click"""
        try:
            entry_price = self.entry_price.value()
            if entry_price <= 0:
                self.show_warning("Please set entry price first")
                return
                
            pct = self.sl_pct_spinbox.value()
            direction = 'BUY' if self.long_button.isChecked() else 'SELL'
            
            if direction == 'BUY':
                stop_price = entry_price * (1 - pct / 100)
            else:
                stop_price = entry_price * (1 + pct / 100)
                
            # Round to proper tick size to avoid IB errors
            stop_price = self.round_to_tick_size(stop_price)
            self.stop_loss_price.setValue(stop_price)
            logger.info(f"Set stop loss to {pct}%: ${stop_price:.2f}")
            
        except Exception as e:
            logger.error(f"Error calculating percentage stop loss: {str(e)}")
            self.show_warning("Error calculating percentage stop loss")
            
    def on_sl_minus_clicked(self):
        """Handle -0.01 stop loss adjustment"""
        current_sl = self.stop_loss_price.value()
        entry_price = self.entry_price.value()
        
        # Determine adjustment based on stock price
        if entry_price >= 1.0:
            adjustment = 0.01
        else:
            adjustment = 0.0001
            
        new_sl = current_sl - adjustment
        self.stop_loss_price.setValue(max(0.0001, new_sl))  # Ensure positive value
        logger.info(f"Adjusted stop loss by -${adjustment:.4f} to ${new_sl:.4f}")
        
    def on_sl_plus_clicked(self):
        """Handle +0.01 stop loss adjustment"""
        current_sl = self.stop_loss_price.value()
        entry_price = self.entry_price.value()
        
        # Determine adjustment based on stock price
        if entry_price >= 1.0:
            adjustment = 0.01
        else:
            adjustment = 0.0001
            
        new_sl = current_sl + adjustment
        self.stop_loss_price.setValue(new_sl)
        logger.info(f"Adjusted stop loss by +${adjustment:.4f} to ${new_sl:.4f}")
        
    def on_sl_minus_ten_clicked(self):
        """Handle -0.10 stop loss adjustment"""
        current_sl = self.stop_loss_price.value()
        new_sl = current_sl - 0.10
        new_sl = max(0.01, new_sl)  # Ensure minimum price
        new_sl = self.round_to_tick_size(new_sl)
        self.stop_loss_price.setValue(new_sl)
        logger.info(f"Decreased stop loss by $0.10 to ${new_sl:.2f}")
        
    def on_sl_plus_ten_clicked(self):
        """Handle +0.10 stop loss adjustment"""
        current_sl = self.stop_loss_price.value()
        new_sl = current_sl + 0.10
        new_sl = self.round_to_tick_size(new_sl)
        self.stop_loss_price.setValue(new_sl)
        logger.info(f"Increased stop loss by $0.10 to ${new_sl:.2f}")
        
    def on_entry_minus_clicked(self):
        """Handle entry price minus button click"""
        current = self.entry_price.value()
        new_value = current - 0.01
        new_value = max(0.01, new_value)  # Ensure minimum price
        new_value = self.round_to_tick_size(new_value)
        self.entry_price.setValue(new_value)
        logger.info(f"Decreased entry price to ${new_value:.2f}")
        
    def on_entry_plus_clicked(self):
        """Handle entry price plus button click"""
        current = self.entry_price.value()
        new_value = current + 0.01
        new_value = self.round_to_tick_size(new_value)
        self.entry_price.setValue(new_value)
        logger.info(f"Increased entry price to ${new_value:.2f}")
        
    def on_entry_minus_ten_clicked(self):
        """Handle entry price minus 0.10 button click"""
        current = self.entry_price.value()
        new_value = current - 0.10
        new_value = max(0.01, new_value)  # Ensure minimum price
        new_value = self.round_to_tick_size(new_value)
        self.entry_price.setValue(new_value)
        logger.info(f"Decreased entry price by $0.10 to ${new_value:.2f}")
        
    def on_entry_plus_ten_clicked(self):
        """Handle entry price plus 0.10 button click"""
        current = self.entry_price.value()
        new_value = current + 0.10
        new_value = self.round_to_tick_size(new_value)
        self.entry_price.setValue(new_value)
        logger.info(f"Increased entry price by $0.10 to ${new_value:.2f}")
        
    def on_limit_minus_ten_clicked(self):
        """Handle limit price minus 0.10 button click"""
        current = self.limit_price.value()
        new_value = current - 0.10
        new_value = max(0.01, new_value)  # Ensure minimum price
        new_value = self.round_to_tick_size(new_value)
        self._limit_price_manually_adjusted = True  # Mark as manually adjusted
        
        # Calculate and store the new offset from entry price
        entry_price = self.entry_price.value()
        if entry_price > 0:
            self._limit_price_offset = new_value - entry_price
            logger.debug(f"Manual adjustment: new offset ${self._limit_price_offset:.4f}")
        
        self.limit_price.setValue(new_value)
        logger.info(f"Decreased limit price by $0.10 to ${new_value:.2f}")
        
    def on_limit_minus_clicked(self):
        """Handle limit price minus 0.01 button click"""
        current = self.limit_price.value()
        new_value = current - 0.01
        new_value = max(0.01, new_value)  # Ensure minimum price
        new_value = self.round_to_tick_size(new_value)
        self._limit_price_manually_adjusted = True  # Mark as manually adjusted
        
        # Calculate and store the new offset from entry price
        entry_price = self.entry_price.value()
        if entry_price > 0:
            self._limit_price_offset = new_value - entry_price
            logger.debug(f"Manual adjustment: new offset ${self._limit_price_offset:.4f}")
        
        self.limit_price.setValue(new_value)
        logger.info(f"Decreased limit price by $0.01 to ${new_value:.2f}")
        
    def on_limit_plus_clicked(self):
        """Handle limit price plus 0.01 button click"""
        current = self.limit_price.value()
        new_value = current + 0.01
        new_value = self.round_to_tick_size(new_value)
        self._limit_price_manually_adjusted = True  # Mark as manually adjusted
        
        # Calculate and store the new offset from entry price
        entry_price = self.entry_price.value()
        if entry_price > 0:
            self._limit_price_offset = new_value - entry_price
            logger.debug(f"Manual adjustment: new offset ${self._limit_price_offset:.4f}")
        
        self.limit_price.setValue(new_value)
        logger.info(f"Increased limit price by $0.01 to ${new_value:.2f}")
        
    def on_limit_plus_ten_clicked(self):
        """Handle limit price plus 0.10 button click"""
        current = self.limit_price.value()
        new_value = current + 0.10
        new_value = self.round_to_tick_size(new_value)
        self._limit_price_manually_adjusted = True  # Mark as manually adjusted
        
        # Calculate and store the new offset from entry price
        entry_price = self.entry_price.value()
        if entry_price > 0:
            self._limit_price_offset = new_value - entry_price
            logger.debug(f"Manual adjustment: new offset ${self._limit_price_offset:.4f}")
        
        self.limit_price.setValue(new_value)
        logger.info(f"Increased limit price by $0.10 to ${new_value:.2f}")
        
    def on_r_minus_clicked(self):
        """Handle R-multiple minus button click"""
        current_r = self.r_multiple_spinbox.value()
        new_r = max(0.1, current_r - 1.0)  # Minimum 0.1R
        self.r_multiple_spinbox.setValue(new_r)
        logger.info(f"Decreased R-multiple to {new_r:.1f}R")
        
    def on_r_plus_clicked(self):
        """Handle R-multiple plus button click"""
        current_r = self.r_multiple_spinbox.value()
        new_r = min(10.0, current_r + 1.0)  # Maximum 10.0R
        self.r_multiple_spinbox.setValue(new_r)
        logger.info(f"Increased R-multiple to {new_r:.1f}R")
        
    def on_r_multiple_changed(self, r_value: float):
        """Handle R-multiple spinbox change - update take profit price"""
        try:
            entry = self.entry_price.value()
            stop_loss = self.stop_loss_price.value()
            
            if entry <= 0 or stop_loss <= 0:
                return
                
            # Calculate risk distance
            risk_distance = abs(entry - stop_loss)
            direction = "BUY" if self.long_button.isChecked() else "SELL"
            
            # Calculate take profit based on R-multiple
            if direction == "BUY":
                take_profit = entry + (r_value * risk_distance)
            else:
                take_profit = entry - (r_value * risk_distance)
            
            # Validate take profit is within reasonable bounds
            if take_profit > 10000.0:
                take_profit = 10000.0
                logger.warning(f"Take profit clamped to maximum: ${take_profit:.2f}")
            elif take_profit < 0.01:
                take_profit = 0.01
                logger.warning(f"Take profit clamped to minimum: ${take_profit:.2f}")
                
            # Update take profit price (block signals to avoid loops)
            self.take_profit_price.blockSignals(True)
            self.take_profit_price.setValue(take_profit)
            self.take_profit_price.blockSignals(False)
            
            # Manually emit chart synchronization signal
            self.on_take_profit_price_changed(take_profit)
            
            # Re-validate inputs and update summary
            self.update_summary()
            
            logger.info(f"Updated take profit to ${take_profit:.2f} for {r_value:.1f}R")
            
        except Exception as e:
            logger.error(f"Error calculating R-multiple: {str(e)}")
            
    def on_take_profit_price_manual_changed(self, price: float):
        """Handle manual take profit price change - update R-multiple"""
        try:
            entry = self.entry_price.value()
            stop_loss = self.stop_loss_price.value()
            
            if entry <= 0 or stop_loss <= 0 or price <= 0:
                return
                
            # Calculate risk distance
            risk_distance = abs(entry - stop_loss)
            
            if risk_distance <= 0:
                return
                
            # Calculate R-multiple based on take profit price
            direction = "BUY" if self.long_button.isChecked() else "SELL"
            
            if direction == "BUY":
                reward_distance = price - entry
            else:
                reward_distance = entry - price
                
            r_multiple = reward_distance / risk_distance
            
            # Update R-multiple spinbox (block signals to avoid loops)
            self.r_multiple_spinbox.blockSignals(True)
            self.r_multiple_spinbox.setValue(max(0.1, r_multiple))
            self.r_multiple_spinbox.blockSignals(False)
            
            logger.info(f"Updated R-multiple to {r_multiple:.1f}R for take profit ${price:.2f}")
            
        except Exception as e:
            logger.error(f"Error calculating R-multiple from price: {str(e)}")
            
    def update_r_multiple_from_prices(self):
        """Update R-multiple when entry or stop loss changes"""
        try:
            entry = self.entry_price.value()
            stop_loss = self.stop_loss_price.value()
            take_profit = self.take_profit_price.value()
            
            if entry <= 0 or stop_loss <= 0 or take_profit <= 0:
                return
                
            # Calculate risk distance
            risk_distance = abs(entry - stop_loss)
            
            if risk_distance <= 0:
                return
                
            # Calculate R-multiple based on current take profit
            direction = "BUY" if self.long_button.isChecked() else "SELL"
            
            if direction == "BUY":
                reward_distance = take_profit - entry
            else:
                reward_distance = entry - take_profit
                
            r_multiple = reward_distance / risk_distance
            
            # Update R-multiple spinbox (block signals to avoid loops)
            self.r_multiple_spinbox.blockSignals(True)
            self.r_multiple_spinbox.setValue(max(0.1, r_multiple))
            self.r_multiple_spinbox.blockSignals(False)
            
        except Exception as e:
            logger.error(f"Error updating R-multiple from prices: {str(e)}")
        
    def apply_smart_sl_adjustment(self, price: float) -> float:
        """Apply smart stop loss adjustment based on stock price"""
        entry_price = self.entry_price.value()
        
        # Only adjust for LONG positions (stop should be below the low)
        if self.long_button.isChecked():
            if entry_price >= 1.0:
                return price - 0.01  # Subtract 1 cent for stocks >= $1
            else:
                return price - 0.0001  # Subtract 0.01 cent for stocks < $1
        else:
            # For SHORT positions, add the adjustment (stop should be above the high)
            if entry_price >= 1.0:
                return price + 0.01
            else:
                return price + 0.0001
            
    def update_stop_loss_options(self, stop_levels: Dict[str, float]):
        """Update available stop loss options"""
        self.stop_loss_data = stop_levels
        
        # Enable buttons based on available data
        has_prior_5min = 'prior_5min_low' in stop_levels or 'estimated_5min_low' in stop_levels
        has_current_5min = 'current_5min_low' in stop_levels
        has_day = 'day_low' in stop_levels or 'estimated_day_low' in stop_levels
        
        self.sl_5min_button.setEnabled(has_prior_5min)
        self.sl_current_5min_button.setEnabled(has_current_5min)
        self.sl_day_button.setEnabled(has_day)
        self.sl_pct_button.setEnabled(self.entry_price.value() > 0)
        
        # Always enable adjustment buttons if we have an entry price
        adjustment_enabled = self.entry_price.value() > 0
        self.sl_minus_button.setEnabled(adjustment_enabled)
        self.sl_plus_button.setEnabled(adjustment_enabled)
        
        # Update button text with values
        if 'prior_5min_low' in stop_levels:
            adjusted = self.apply_smart_sl_adjustment(stop_levels['prior_5min_low'])
            pct_text = self._calculate_percentage_text(self.entry_price.value(), adjusted)
            self.sl_5min_button.setText(f"Prior 5min\n${adjusted:.4f}{pct_text}")
            self.sl_5min_button.setStyleSheet("QPushButton { color: green; font-weight: bold; font-size: 10px; }")
        elif 'estimated_5min_low' in stop_levels:
            adjusted = self.apply_smart_sl_adjustment(stop_levels['estimated_5min_low'])
            pct_text = self._calculate_percentage_text(self.entry_price.value(), adjusted)
            self.sl_5min_button.setText(f"Prior Est.\n${adjusted:.4f}{pct_text}")
            self.sl_5min_button.setStyleSheet("QPushButton { color: orange; font-style: italic; font-size: 10px; }")
        else:
            self.sl_5min_button.setText("Prior 5min")
            self.sl_5min_button.setStyleSheet("")
            
        # Update current 5min button
        if 'current_5min_low' in stop_levels:
            adjusted = self.apply_smart_sl_adjustment(stop_levels['current_5min_low'])
            pct_text = self._calculate_percentage_text(self.entry_price.value(), adjusted)
            self.sl_current_5min_button.setText(f"Current 5min\n${adjusted:.4f}{pct_text}")
            self.sl_current_5min_button.setStyleSheet("QPushButton { color: green; font-weight: bold; font-size: 10px; }")
        else:
            self.sl_current_5min_button.setText("Current 5min")
            self.sl_current_5min_button.setStyleSheet("")
            
        if 'day_low' in stop_levels:
            price = stop_levels['day_low']
            pct_text = self._calculate_percentage_text(self.entry_price.value(), price)
            self.sl_day_button.setText(f"Day Low\n${price:.2f}{pct_text}")
            self.sl_day_button.setStyleSheet("QPushButton { color: green; font-weight: bold; font-size: 10px; }")
        elif 'estimated_day_low' in stop_levels:
            price = stop_levels['estimated_day_low']
            pct_text = self._calculate_percentage_text(self.entry_price.value(), price)
            self.sl_day_button.setText(f"Day Est.\n${price:.2f}{pct_text}")
            self.sl_day_button.setStyleSheet("QPushButton { color: orange; font-style: italic; font-size: 10px; }")
        else:
            self.sl_day_button.setText("Day Low")
            self.sl_day_button.setStyleSheet("")
            
        # Percentage button is always available when entry price is set
            
        # Log what's available
        available_levels = [k for k in stop_levels.keys() if k.endswith('_low') or k.endswith('percent')]
        logger.info(f"Updated stop loss buttons with levels: {available_levels}")
        
    def _calculate_percentage_text(self, entry_price: float, stop_price: float) -> str:
        """Calculate percentage difference between entry and stop price"""
        if entry_price <= 0:
            return ""
        
        try:
            percentage = ((stop_price - entry_price) / entry_price) * 100
            return f"({percentage:+.2f}%)"
        except (ValueError, ZeroDivisionError):
            return ""
    
    def update_sl_pct_price_display(self):
        """Update the percentage stop loss price display"""
        try:
            entry_price = self.entry_price.value()
            if entry_price <= 0:
                self.sl_pct_price_label.setText("$0.00")
                return
                
            pct = self.sl_pct_spinbox.value()
            direction = 'BUY' if self.long_button.isChecked() else 'SELL'
            
            if direction == 'BUY':
                stop_price = entry_price * (1 - pct / 100)
            else:
                stop_price = entry_price * (1 + pct / 100)
                
            self.sl_pct_price_label.setText(f"${stop_price:.2f}")
            
        except Exception as e:
            logger.error(f"Error updating percentage price display: {str(e)}")
            self.sl_pct_price_label.setText("$0.00")
        
    def update_price_info(self, last: float, bid: float, ask: float):
        """Update price information display"""
        self.price_info_label.setText(f"Last: ${last:.2f} | Bid: ${bid:.2f} | Ask: ${ask:.2f}")
        self.fetch_price_button.setText("Fetch")
        self.fetch_price_button.setEnabled(True)
        # Return focus to symbol input so Enter key continues to work
        self.symbol_input.setFocus()
        
    def on_multiple_targets_toggled(self, checked: bool):
        """Handle multiple targets checkbox toggle"""
        self.use_multiple_targets = checked
        
        if checked:
            # Hide single target take profit row
            self.take_profit_label.hide()
            self.take_profit_widget.hide()
            
            # Show target count controls
            self.target_count_label.show()
            self.increase_targets_button.show()
            self.decrease_targets_button.show()
            
            # Update visible targets based on active count
            self.update_visible_targets()
            
            # Calculate initial target prices based on R-multiples
            self.calculate_target_prices()
            
            # Auto-balance percentages
            self.auto_balance_target_percentages()
            
            # Emit target prices for chart lines
            self.on_target_prices_changed()
            
            logger.info(f"Enabled multiple profit targets with {self.active_target_count} targets")
        else:
            # Hide multiple targets and show single target
            for target in self.profit_targets:
                target['label'].hide()
                target['widget'].hide()  # Hide the wrapper widget
                target['price'].hide()
                target['percent'].hide()
                target['r_multiple'].hide()
                target['shares'].hide()
            
            # Hide target count controls
            self.target_count_label.hide()
            self.increase_targets_button.hide()
            self.decrease_targets_button.hide()
            
            # Show single target take profit row
            self.take_profit_label.show()
            self.take_profit_widget.show()
            
            # Clear multiple target lines from chart
            self.target_prices_changed.emit([])
            
            # Emit the current take profit price to update chart
            current_take_profit = self.take_profit_price.value()
            if current_take_profit > 0:
                self.take_profit_changed.emit(current_take_profit)
                logger.info(f"Re-emitted take profit price: ${current_take_profit:.2f}")
            
            logger.info("Disabled multiple profit targets")
            
        self.update_summary()
        
    def calculate_target_prices(self):
        """Calculate target prices based on individual R-multiples"""
        try:
            entry = self.entry_price.value()
            stop_loss = self.stop_loss_price.value()
            
            if entry <= 0 or stop_loss <= 0:
                return
            
            # Determine which price to use for risk calculation based on order type
            order_type = self.get_order_type()
            if order_type == 'STOPLMT':
                # For STOP LIMIT orders, use limit price for risk calculation
                limit_price = self.limit_price.value()
                if limit_price <= 0:
                    return
                price_for_calculation = limit_price
                logger.debug(f"calculate_target_prices: Using limit price ${limit_price:.4f} for STOP LIMIT")
            else:
                # For LMT and MKT orders, use entry price
                price_for_calculation = entry
                logger.debug(f"calculate_target_prices: Using entry price ${entry:.4f} for {order_type}")
                
            # Calculate risk distance using appropriate price
            risk_distance = abs(price_for_calculation - stop_loss)
            direction = "BUY" if self.long_button.isChecked() else "SELL"
            
            # Calculate target prices based on individual R-multiples
            for target in self.profit_targets:
                r_multiple = target['r_multiple'].value()
                
                if direction == "BUY":
                    target_price = price_for_calculation + (r_multiple * risk_distance)
                else:
                    target_price = price_for_calculation - (r_multiple * risk_distance)
                    
                # Update price field (temporarily disconnect to avoid loops)
                target['price'].valueChanged.disconnect()
                target['price'].setValue(target_price)
                target['price'].valueChanged.connect(self.update_summary)
                target['price'].valueChanged.connect(self.on_target_price_changed)
                target['price'].valueChanged.connect(self.on_target_prices_changed)
                
            # Emit target prices for chart lines
            self.on_target_prices_changed()
            logger.info(f"Calculated target prices for {direction} trade")
            
        except Exception as e:
            logger.error(f"Error calculating target prices: {str(e)}")
    
    def auto_adjust_take_profit(self):
        """Automatically adjust take profit to maintain current R-multiple when entry/stop loss changes"""
        try:
            # Skip if we're already updating take profit to avoid circular updates
            if self._updating_take_profit:
                return
                
            entry = self.entry_price.value()
            stop_loss = self.stop_loss_price.value()
            current_r_multiple = self.r_multiple_spinbox.value()
            
            # Enhanced validation to prevent corruption
            if entry <= 0 or entry > 5000 or stop_loss <= 0 or stop_loss > 5000 or current_r_multiple <= 0:
                logger.warning(f"Invalid values for auto-adjustment - Entry: ${entry:.2f}, SL: ${stop_loss:.2f}, R: {current_r_multiple:.1f}")
                return
                
            # Calculate risk distance
            risk_distance = abs(entry - stop_loss)
            direction = "BUY" if self.long_button.isChecked() else "SELL"
            
            # Validate risk distance is reasonable
            if risk_distance > entry * 0.5:  # Stop loss more than 50% away from entry
                logger.warning(f"Risk distance too large: ${risk_distance:.2f} (entry: ${entry:.2f}), skipping auto-adjustment")
                return
            
            # Calculate new take profit based on current R-multiple
            if direction == "BUY":
                new_take_profit = entry + (current_r_multiple * risk_distance)
            else:
                new_take_profit = entry - (current_r_multiple * risk_distance)
            
            # Enhanced validation - prevent extreme values
            if new_take_profit > 5000.0:
                logger.warning(f"Calculated take profit too high: ${new_take_profit:.2f}, clamping to $5000")
                new_take_profit = 5000.0
            elif new_take_profit < 0.01:
                logger.warning(f"Calculated take profit too low: ${new_take_profit:.2f}, clamping to $0.01")
                new_take_profit = 0.01
            
            # Set flag to prevent circular updates
            self._updating_take_profit = True
            
            # Temporarily disconnect to avoid circular updates
            self.take_profit_price.valueChanged.disconnect()
            
            # Update take profit price
            self.take_profit_price.setValue(new_take_profit)
            
            # Reconnect and emit chart sync signal
            self.take_profit_price.valueChanged.connect(self.update_summary)
            self.on_take_profit_price_changed(new_take_profit)
            
            # Reset flag
            self._updating_take_profit = False
            
            logger.info(f"Auto-adjusted take profit to ${new_take_profit:.2f} to maintain {current_r_multiple:.1f}R")
            
        except Exception as e:
            logger.error(f"Error auto-adjusting take profit: {str(e)}")
            # Reset flag and reconnect even if there was an error
            self._updating_take_profit = False
            try:
                self.take_profit_price.valueChanged.connect(self.update_summary)
            except:
                pass
            
    def calculate_target_percentages(self):
        """Ensure target percentages add up to 100%"""
        try:
            total_percent = sum(target['percent'].value() for target in self.profit_targets)
            
            # If total doesn't equal 100%, show warning
            if total_percent != 100:
                logger.warning(f"Target percentages total {total_percent}% (should be 100%)")
            
            # Update target share quantities when percentages change
            self.update_target_share_quantities()
                
        except Exception as e:
            logger.error(f"Error calculating target percentages: {str(e)}")
            
    def get_profit_target_data(self) -> list:
        """Get profit target data for order submission"""
        if not self.use_multiple_targets:
            return [{
                'price': self.take_profit_price.value(),
                'percent': 100
            }]
        else:
            return [{
                'price': target['price'].value(),
                'percent': target['percent'].value()
            } for target in self.profit_targets if target['price'].value() > 0]
    
    def on_target_r_multiple_changed(self):
        """Handle R-multiple change in multiple targets - update corresponding price"""
        try:
            entry = self.entry_price.value()
            stop_loss = self.stop_loss_price.value()
            
            if entry <= 0 or stop_loss <= 0:
                return
            
            # Determine which price to use for risk calculation based on order type
            order_type = self.get_order_type()
            if order_type == 'STOPLMT':
                # For STOP LIMIT orders, use limit price for risk calculation
                limit_price = self.limit_price.value()
                if limit_price <= 0:
                    return
                price_for_calculation = limit_price
                logger.debug(f"Using limit price ${limit_price:.4f} for STOP LIMIT target calculation")
            else:
                # For LMT and MKT orders, use entry price
                price_for_calculation = entry
                logger.debug(f"Using entry price ${entry:.4f} for {order_type} target calculation")
                
            # Calculate risk distance using appropriate price
            risk_distance = abs(price_for_calculation - stop_loss)
            direction = "BUY" if self.long_button.isChecked() else "SELL"
            
            # Find which R-multiple field changed and update its corresponding price
            sender = self.sender()
            for target in self.profit_targets:
                if target['r_multiple'] == sender:
                    r_multiple = target['r_multiple'].value()
                    
                    if direction == "BUY":
                        target_price = price_for_calculation + (r_multiple * risk_distance)
                    else:
                        target_price = price_for_calculation - (r_multiple * risk_distance)
                    
                    # Validate and set price
                    target_price = max(0.01, min(5000.0, target_price))
                    
                    # Update price field (temporarily disconnect to avoid loops)
                    target['price'].valueChanged.disconnect()
                    target['price'].setValue(target_price)
                    target['price'].valueChanged.connect(self.update_summary)
                    
                    logger.info(f"Updated target price to ${target_price:.2f} for {r_multiple:.1f}R (using {order_type} price ${price_for_calculation:.2f})")
                    break
                    
            self.update_summary()
            
        except Exception as e:
            logger.error(f"Error updating target price from R-multiple: {str(e)}")
    
    def on_target_price_changed(self):
        """Handle manual target price change - update corresponding R-multiple"""
        try:
            entry = self.entry_price.value()
            stop_loss = self.stop_loss_price.value()
            
            if entry <= 0 or stop_loss <= 0:
                return
            
            # Determine which price to use for risk calculation based on order type
            order_type = self.get_order_type()
            if order_type == 'STOPLMT':
                # For STOP LIMIT orders, use limit price for risk calculation
                limit_price = self.limit_price.value()
                if limit_price <= 0:
                    return
                price_for_calculation = limit_price
                logger.debug(f"Using limit price ${limit_price:.4f} for STOP LIMIT R-multiple calculation")
            else:
                # For LMT and MKT orders, use entry price
                price_for_calculation = entry
                logger.debug(f"Using entry price ${entry:.4f} for {order_type} R-multiple calculation")
                
            # Calculate risk distance using appropriate price
            risk_distance = abs(price_for_calculation - stop_loss)
            direction = "BUY" if self.long_button.isChecked() else "SELL"
            
            if risk_distance <= 0:
                return
            
            # Find which price field changed and update its corresponding R-multiple
            sender = self.sender()
            for target in self.profit_targets:
                if target['price'] == sender:
                    target_price = target['price'].value()
                    
                    # Calculate R-multiple based on price using appropriate base price
                    if direction == "BUY":
                        reward_distance = target_price - price_for_calculation
                    else:
                        reward_distance = price_for_calculation - target_price
                    
                    r_multiple = max(0.1, reward_distance / risk_distance)
                    
                    # Update R-multiple field (temporarily disconnect to avoid loops)
                    target['r_multiple'].valueChanged.disconnect()
                    target['r_multiple'].setValue(r_multiple)
                    target['r_multiple'].valueChanged.connect(self.on_target_r_multiple_changed)
                    
                    logger.info(f"Updated R-multiple to {r_multiple:.1f}R for target price ${target_price:.2f} (using {order_type} price ${price_for_calculation:.2f})")
                    break
                    
        except Exception as e:
            logger.error(f"Error updating R-multiple from target price: {str(e)}")
    
    def get_order_type(self) -> str:
        """Get the currently selected order type"""
        if self.limit_button.isChecked():
            return 'LMT'
        elif self.market_button.isChecked():
            return 'MKT'
        elif self.stop_limit_button.isChecked():
            return 'STOPLMT'
        else:
            return 'LMT'  # Default fallback
    
    def show_fetch_progress(self):
        """Show the fetch progress indicator"""
        self.fetch_progress.show()
        self.fetch_price_button.setText("Fetching...")
        self.fetch_price_button.setEnabled(False)
        
    def hide_fetch_progress(self):
        """Hide the fetch progress indicator"""
        self.fetch_progress.hide()
        self.fetch_price_button.setText("Fetch")
        self.fetch_price_button.setEnabled(True)
        # Return focus to symbol input
        self.symbol_input.setFocus()
    
    def on_order_type_changed(self):
        """Handle order type change - show/hide limit price for STOP LIMIT orders"""
        if self.stop_limit_button.isChecked():
            # Show limit price field and buttons
            self.limit_price_label.show()
            self.limit_price.show()
            self.limit_minus_ten_button.show()
            self.limit_minus_button.show()
            self.limit_plus_button.show()
            self.limit_plus_ten_button.show()
            # Reset the manual adjustment flag when switching to STOP LIMIT
            self._limit_price_manually_adjusted = False
            # Set default limit price to 0.1% larger than entry price (stop price)
            entry_price = self.entry_price.value()
            default_limit = entry_price * 1.001  # 0.1% larger
            default_limit = self.round_to_tick_size(default_limit)
            self.limit_price.setValue(default_limit)
            logger.info(f"Set limit price to ${default_limit:.4f} (0.1% above entry price ${entry_price:.4f})")
        else:
            # Hide limit price field and buttons
            self.limit_price_label.hide()
            self.limit_price.hide()
            self.limit_minus_ten_button.hide()
            self.limit_minus_button.hide()
            self.limit_plus_button.hide()
            self.limit_plus_ten_button.hide()
            
            # Reset limit price adjustment tracking when switching away from STOP LIMIT
            self._limit_price_manually_adjusted = False
            self._limit_price_offset = None
        
        # Recalculate position size when order type changes (affects risk calculation for STOP LIMIT)
        self.calculate_position_size()
        
        self.update_summary()
        
        # Clear limit price from chart AFTER all other updates when switching away from STOP LIMIT
        if not self.stop_limit_button.isChecked():
            # Temporarily disconnect signal to avoid double emission
            self.limit_price.valueChanged.disconnect(self.on_limit_price_changed)
            
            # Set spinbox value to 0 and emit clear signal
            self.limit_price.setValue(0.0)
            self.limit_price_changed.emit(0.0)
            
            # Reconnect signal
            self.limit_price.valueChanged.connect(self.on_limit_price_changed)
            
            logger.info("Cleared limit price from chart when switching away from STOP LIMIT")
    
    def on_increase_targets_clicked(self):
        """Increase the number of active targets (max 3)"""
        if self.active_target_count < 3:
            self.active_target_count += 1
            # Set R-multiple based price for the new target
            self.calculate_new_target_price()
            self.update_visible_targets()
            self.auto_balance_target_percentages()
            logger.info(f"Increased targets to {self.active_target_count}")
    
    def on_decrease_targets_clicked(self):
        """Decrease the number of active targets (min 2)"""
        if self.active_target_count > 2:
            self.active_target_count -= 1
            self.update_visible_targets()  # This will reset hidden targets
            self.auto_balance_target_percentages()
            self.update_summary()  # Refresh validation
            logger.info(f"Decreased targets to {self.active_target_count}")
    
    def update_visible_targets(self):
        """Show/hide targets based on active count"""
        self.target_count_label.setText(f"{self.active_target_count} targets")
        
        # Show/hide targets based on count
        for i, target in enumerate(self.profit_targets):
            if i < self.active_target_count:
                target['label'].show()
                target['widget'].show()  # Show the wrapper widget
                target['price'].show()
                target['percent'].show()
                target['r_multiple'].show()
                target['shares'].show()
            else:
                target['label'].hide()
                target['widget'].hide()  # Hide the wrapper widget
                target['price'].hide()
                target['percent'].hide()
                target['r_multiple'].hide()
                target['shares'].hide()
                # Reset hidden target values to safe defaults
                target['price'].setValue(0.01)  # Safe default price
                target['percent'].setValue(0)  # Zero percent
                target['r_multiple'].setValue(1.0)  # Default R-multiple
        
        # Update button states
        self.decrease_targets_button.setEnabled(self.active_target_count > 2)
        self.increase_targets_button.setEnabled(self.active_target_count < 3)
        
        # Update share quantities when visibility changes
        self.update_target_share_quantities()
    
    def update_target_share_quantities(self):
        """Update share quantity displays for each profit target"""
        if not self.use_multiple_targets:
            return
            
        total_shares = self.position_size.value()
        if total_shares <= 0:
            # Reset all share displays to 0 when no position
            for target in self.profit_targets:
                target['shares'].setText("0 shs")
            return
        
        # Calculate shares using the same logic as get_adjusted_profit_target_data
        allocated_shares = 0
        active_targets = []
        
        # Get active targets (only visible ones with valid prices)
        for i in range(self.active_target_count):
            target = self.profit_targets[i]
            if target['widget'].isVisible() and target['price'].value() > 0.01:
                active_targets.append((i, target))
        
        # Log active targets for debugging
        logger.debug(f"Active targets for display: {[(i, t['price'].value(), t['percent'].value()) for i, t in active_targets]}")
        
        # Find the target with the smallest R-multiple to absorb remaining shares
        smallest_r_target_idx = None
        smallest_r_value = float('inf')
        
        for idx, (i, target) in enumerate(active_targets):
            r_multiple = target['r_multiple'].value()
            if r_multiple < smallest_r_value:
                smallest_r_value = r_multiple
                smallest_r_target_idx = idx
        
        # First pass: calculate shares for all non-smallest targets
        target_share_amounts = {}
        
        for idx, (i, target) in enumerate(active_targets):
            percentage = target['percent'].value()
            
            if idx != smallest_r_target_idx:
                # Calculate shares for non-smallest targets
                target_shares = int(total_shares * percentage / 100.0)
                allocated_shares += target_shares
                target_share_amounts[idx] = target_shares
            else:
                # Placeholder for smallest target - will be calculated after
                target_share_amounts[idx] = 0
        
        # Second pass: assign remaining shares to smallest target and update displays
        for idx, (i, target) in enumerate(active_targets):
            if idx == smallest_r_target_idx and smallest_r_target_idx is not None:
                # Smallest R-multiple target gets remaining shares (prevents rounding errors)
                target_shares = total_shares - allocated_shares
                logger.debug(f"Display: Target {i+1} ({smallest_r_value:.1f}R) absorbing remaining {target_shares} shares")
            else:
                # Use pre-calculated shares
                target_shares = target_share_amounts[idx]
            
            # Update the display
            target['shares'].setText(f"{target_shares} shs")
        
        # Reset inactive targets to 0 shares
        for i in range(len(self.profit_targets)):
            if i >= self.active_target_count or not self.profit_targets[i]['widget'].isVisible():
                self.profit_targets[i]['shares'].setText("0 shs")
    
    def auto_balance_target_percentages(self):
        """Automatically balance target percentages to sum to 100%"""
        if self.active_target_count == 2:
            # For 2 targets: 50/50
            self.profit_targets[0]['percent'].setValue(50)
            self.profit_targets[1]['percent'].setValue(50)
        elif self.active_target_count == 3:
            # For 3 targets: 40/40/20
            self.profit_targets[0]['percent'].setValue(40)
            self.profit_targets[1]['percent'].setValue(40)
            self.profit_targets[2]['percent'].setValue(20)
        
        # Update share quantities after auto-balancing percentages
        self.update_target_share_quantities()
    
    def calculate_new_target_price(self):
        """Calculate price for newly added target based on R-multiple"""
        try:
            entry_price = self.entry_price.value()
            stop_loss = self.stop_loss_price.value()
            
            if entry_price <= 0 or stop_loss <= 0:
                return
            
            # Determine which price to use for risk calculation based on order type
            order_type = self.get_order_type()
            if order_type == 'STOPLMT':
                # For STOP LIMIT orders, use limit price for risk calculation
                limit_price = self.limit_price.value()
                if limit_price <= 0:
                    return
                price_for_calculation = limit_price
                logger.debug(f"calculate_new_target_price: Using limit price ${limit_price:.4f} for STOP LIMIT")
            else:
                # For LMT and MKT orders, use entry price
                price_for_calculation = entry_price
                logger.debug(f"calculate_new_target_price: Using entry price ${entry_price:.4f} for {order_type}")
            
            # Calculate risk per share using appropriate price
            direction = 'BUY' if self.long_button.isChecked() else 'SELL'
            if direction == 'BUY':
                risk_per_share = price_for_calculation - stop_loss
            else:
                risk_per_share = stop_loss - price_for_calculation
            
            if risk_per_share <= 0:
                return
            
            # Set price for the newly activated target based on its R-multiple
            new_target_index = self.active_target_count - 1
            if new_target_index < len(self.profit_targets):
                target = self.profit_targets[new_target_index]
                r_multiple = target['r_multiple'].value()
                
                if direction == 'BUY':
                    target_price = price_for_calculation + (risk_per_share * r_multiple)
                else:
                    target_price = price_for_calculation - (risk_per_share * r_multiple)
                
                # Round to proper tick size
                target_price = self.round_to_tick_size(target_price)
                target['price'].setValue(target_price)
                
                logger.info(f"Set new target {new_target_index + 1} price to ${target_price:.2f} ({r_multiple}R)")
                
        except Exception as e:
            logger.error(f"Error calculating new target price: {e}")
    
    def get_adjusted_profit_target_data(self) -> list:
        """Get profit target data with smallest R-multiple target absorbing remaining shares"""
        if not self.use_multiple_targets:
            return [{
                'price': self.take_profit_price.value(),
                'percent': 100,
                'quantity': self.position_size.value()
            }]
        else:
            # Ensure display is synced before reading data
            self.update_target_share_quantities()
            
            total_position = self.position_size.value()
            logger.debug(f"get_adjusted_profit_target_data: Using position size {total_position} shares")
            targets_data = []
            allocated_shares = 0
            
            # Get active targets - match the exact logic from update_target_share_quantities
            active_targets = []
            for i in range(self.active_target_count):
                target = self.profit_targets[i]
                # Match the display logic exactly: check visibility AND price
                if target['widget'].isVisible() and target['price'].value() > 0.01:
                    active_targets.append((i, target))
                else:
                    # For inactive targets, reset them to default values
                    target['price'].setValue(0.01)
                    target['percent'].setValue(0)
            
            # Log active targets for debugging
            logger.debug(f"Active targets for order: {[(i, t['price'].value(), t['percent'].value()) for i, t in active_targets]}")
            
            # Find the target with the smallest R-multiple to absorb remaining shares
            smallest_r_target_idx = None
            smallest_r_value = float('inf')
            
            for idx, (i, target) in enumerate(active_targets):
                r_multiple = target['r_multiple'].value()
                if r_multiple < smallest_r_value:
                    smallest_r_value = r_multiple
                    smallest_r_target_idx = idx
            
            # First pass: calculate shares for all non-smallest targets
            target_quantities = {}
            
            for idx, (i, target) in enumerate(active_targets):
                percent = target['percent'].value()
                
                if idx != smallest_r_target_idx:
                    # Calculate shares for non-smallest targets
                    quantity = int(total_position * percent / 100)
                    allocated_shares += quantity
                    target_quantities[idx] = quantity
                else:
                    # Placeholder for smallest target - will be calculated after
                    target_quantities[idx] = 0
            
            # Second pass: assign remaining shares to smallest target and build final data
            for idx, (i, target) in enumerate(active_targets):
                percent = target['percent'].value()
                
                if idx == smallest_r_target_idx and smallest_r_target_idx is not None:
                    # Smallest R-multiple target gets remaining shares (prevents rounding errors)
                    quantity = total_position - allocated_shares
                    logger.debug(f"Order data: Target {i+1} ({smallest_r_value:.1f}R) gets remaining {quantity} shares")
                else:
                    # Use pre-calculated quantity
                    quantity = target_quantities[idx]
                
                targets_data.append({
                    'price': target['price'].value(),
                    'percent': percent,
                    'quantity': quantity
                })
            
            return targets_data