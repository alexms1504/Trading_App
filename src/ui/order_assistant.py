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
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.account_value = 100000.0  # Default value, will be updated when connected
        self.buying_power = 100000.0  # Default buying power, will be updated when connected
        self.risk_calculator = None  # Will be set when connected
        self.stop_loss_data = {}  # Store calculated stop loss levels
        self.use_multiple_targets = False  # Track if using multiple targets
        self.profit_targets = []  # Store multiple profit target widgets
        self._updating_from_risk = False  # Flag to prevent circular updates
        self._updating_take_profit = False  # Flag to prevent circular take profit updates
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
        
        order_type_layout = QHBoxLayout()
        order_type_layout.addWidget(self.limit_button)
        order_type_layout.addWidget(self.market_button)
        order_type_layout.addStretch()
        layout.addLayout(order_type_layout, 2, 1, 1, 2)
        
        group.setLayout(layout)
        return group
        
    def create_price_section(self) -> QGroupBox:
        """Create price entry section"""
        group = QGroupBox("Price Levels")
        layout = QGridLayout()
        
        # Entry price with adjustment buttons
        layout.addWidget(QLabel("Entry Price:"), 0, 0)
        
        # Create horizontal layout for entry price input and adjustment buttons
        entry_input_layout = QHBoxLayout()
        
        self.entry_price = QDoubleSpinBox()
        self.entry_price.setRange(0.0001, 5000.0)  # Max $5,000 per share
        self.entry_price.setDecimals(4)  # 4 decimal places for entry price
        self.entry_price.setSingleStep(0.01)
        self.entry_price.setPrefix("$")
        self.entry_price.setValue(1.0000)  # Default entry price: $1.0000
        self.entry_price.setMinimumWidth(120)  # Wider for 4 decimals
        entry_input_layout.addWidget(self.entry_price)
        
        # Add more spacing before adjustment buttons
        entry_input_layout.addSpacing(20)
        
        # Add adjustment buttons
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
        
        entry_input_layout.addStretch()
        layout.addLayout(entry_input_layout, 0, 1)
        
        # Stop loss price with adjustment buttons
        layout.addWidget(QLabel("Stop Loss:"), 1, 0)
        
        # Create horizontal layout for stop loss input and adjustment buttons
        sl_input_layout = QHBoxLayout()
        
        self.stop_loss_price = QDoubleSpinBox()
        self.stop_loss_price.setRange(0.01, 5000.0)  # Max $5,000 per share
        self.stop_loss_price.setDecimals(4)  # Support both penny and sub-penny stocks
        self.stop_loss_price.setSingleStep(0.01)
        self.stop_loss_price.setPrefix("$")
        self.stop_loss_price.setValue(0.01)  # Default stop loss: $0.01
        self.stop_loss_price.setMinimumWidth(120)  # Ensure adequate width
        sl_input_layout.addWidget(self.stop_loss_price)
        
        # Add more spacing before adjustment buttons
        sl_input_layout.addSpacing(20)
        
        # Add adjustment buttons
        self.sl_minus_button = QPushButton("-0.01")
        self.sl_minus_button.setMaximumWidth(50)
        self.sl_minus_button.setToolTip("Decrease stop loss by $0.01 (or $0.0001 for stocks < $1)")
        sl_input_layout.addWidget(self.sl_minus_button)
        
        self.sl_plus_button = QPushButton("+0.01")
        self.sl_plus_button.setMaximumWidth(50)
        self.sl_plus_button.setToolTip("Increase stop loss by $0.01 (or $0.0001 for stocks < $1)")
        sl_input_layout.addWidget(self.sl_plus_button)
        
        layout.addLayout(sl_input_layout, 1, 1)
        
        # Take profit price with R-multiple controls (single target)
        layout.addWidget(QLabel("Take Profit:"), 2, 0)
        
        # Create horizontal layout for take profit controls
        tp_input_layout = QHBoxLayout()
        
        self.take_profit_price = QDoubleSpinBox()
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
        layout.addLayout(tp_input_layout, 2, 1)
        
        # Multiple targets toggle
        self.multiple_targets_checkbox = QCheckBox("Multiple Targets")
        self.multiple_targets_checkbox.setToolTip("Enable 2-4 profit targets with partial scaling")
        layout.addWidget(self.multiple_targets_checkbox, 2, 2)
        
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
        
        self.sl_pct_spinbox = QDoubleSpinBox()
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
        layout.addWidget(sl_buttons_widget, 7, 0, 1, 4)  # Add it after other rows
        
        # Multiple profit targets section (initially hidden)
        self.create_multiple_targets_section(layout)
        
        # Price info labels
        self.price_info_label = QLabel("Last: N/A | Bid: N/A | Ask: N/A")
        self.price_info_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.price_info_label, 8, 0, 1, 4)  # Moved down after SL buttons
        
        group.setLayout(layout)
        return group
        
    def create_multiple_targets_section(self, layout):
        """Create multiple profit targets section with separate % and R-multiple controls"""
        # Multiple targets widgets (initially hidden)
        self.targets_widgets = []
        
        # Target 1
        layout.addWidget(QLabel("Target 1:"), 3, 0)
        
        # Price field
        target1_price = ImprovedDoubleSpinBox()
        target1_price.setRange(0.01, 5000.0)
        target1_price.setDecimals(2)
        target1_price.setSingleStep(0.01)
        target1_price.setPrefix("$")
        target1_price.setMaximumWidth(100)
        target1_price.hide()
        layout.addWidget(target1_price, 3, 1)
        
        # Percentage field
        target1_percent = ImprovedSpinBox()
        target1_percent.setRange(10, 100)
        target1_percent.setValue(50)
        target1_percent.setSuffix("%")
        target1_percent.setMaximumWidth(60)
        target1_percent.setToolTip("Percentage of position to close at this target")
        target1_percent.hide()
        layout.addWidget(target1_percent, 3, 2)
        
        # R-multiple field
        target1_r_multiple = ImprovedDoubleSpinBox()
        target1_r_multiple.setRange(0.1, 10.0)
        target1_r_multiple.setValue(1.0)
        target1_r_multiple.setSuffix("R")
        target1_r_multiple.setDecimals(1)
        target1_r_multiple.setMaximumWidth(60)
        target1_r_multiple.setToolTip("Risk/reward ratio for this target")
        target1_r_multiple.hide()
        layout.addWidget(target1_r_multiple, 3, 3)
        
        # Target 2
        layout.addWidget(QLabel("Target 2:"), 4, 0)
        
        # Price field
        target2_price = ImprovedDoubleSpinBox()
        target2_price.setRange(0.01, 5000.0)
        target2_price.setDecimals(2)
        target2_price.setSingleStep(0.01)
        target2_price.setPrefix("$")
        target2_price.setMaximumWidth(100)
        target2_price.hide()
        layout.addWidget(target2_price, 4, 1)
        
        # Percentage field
        target2_percent = ImprovedSpinBox()
        target2_percent.setRange(10, 100)
        target2_percent.setValue(30)
        target2_percent.setSuffix("%")
        target2_percent.setMaximumWidth(60)
        target2_percent.setToolTip("Percentage of position to close at this target")
        target2_percent.hide()
        layout.addWidget(target2_percent, 4, 2)
        
        # R-multiple field
        target2_r_multiple = ImprovedDoubleSpinBox()
        target2_r_multiple.setRange(0.1, 10.0)
        target2_r_multiple.setValue(2.0)
        target2_r_multiple.setSuffix("R")
        target2_r_multiple.setDecimals(1)
        target2_r_multiple.setMaximumWidth(60)
        target2_r_multiple.setToolTip("Risk/reward ratio for this target")
        target2_r_multiple.hide()
        layout.addWidget(target2_r_multiple, 4, 3)
        
        # Target 3
        layout.addWidget(QLabel("Target 3:"), 5, 0)
        
        # Price field
        target3_price = ImprovedDoubleSpinBox()
        target3_price.setRange(0.01, 5000.0)
        target3_price.setDecimals(2)
        target3_price.setSingleStep(0.01)
        target3_price.setPrefix("$")
        target3_price.setMaximumWidth(100)
        target3_price.hide()
        layout.addWidget(target3_price, 5, 1)
        
        # Percentage field
        target3_percent = QSpinBox()
        target3_percent.setRange(10, 100)
        target3_percent.setValue(20)
        target3_percent.setSuffix("%")
        target3_percent.setMaximumWidth(60)
        target3_percent.setToolTip("Percentage of position to close at this target")
        target3_percent.hide()
        layout.addWidget(target3_percent, 5, 2)
        
        # R-multiple field
        target3_r_multiple = ImprovedDoubleSpinBox()
        target3_r_multiple.setRange(0.1, 10.0)
        target3_r_multiple.setValue(3.0)
        target3_r_multiple.setSuffix("R")
        target3_r_multiple.setDecimals(1)
        target3_r_multiple.setMaximumWidth(60)
        target3_r_multiple.setToolTip("Risk/reward ratio for this target")
        target3_r_multiple.hide()
        layout.addWidget(target3_r_multiple, 5, 3)
        
        # Store references to all target widgets
        self.profit_targets = [
            {
                'price': target1_price, 
                'percent': target1_percent, 
                'r_multiple': target1_r_multiple,
                'label': layout.itemAtPosition(3, 0).widget()
            },
            {
                'price': target2_price, 
                'percent': target2_percent, 
                'r_multiple': target2_r_multiple,
                'label': layout.itemAtPosition(4, 0).widget()
            },
            {
                'price': target3_price, 
                'percent': target3_percent, 
                'r_multiple': target3_r_multiple,
                'label': layout.itemAtPosition(5, 0).widget()
            }
        ]
        
        # Hide all target labels initially
        for target in self.profit_targets:
            target['label'].hide()
        
    def create_risk_section(self) -> QGroupBox:
        """Create risk management section"""
        group = QGroupBox("Risk Management")
        layout = QGridLayout()
        
        # Risk percentage slider (full row)
        layout.addWidget(QLabel("Risk %:"), 0, 0)
        self.risk_slider = QSlider(Qt.Orientation.Horizontal)
        self.risk_slider.setRange(10, 1000)  # 0.1% to 10%
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
        
        self.position_size = QSpinBox()
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
        self.stop_loss_price.valueChanged.connect(self.calculate_position_size)
        self.stop_loss_price.valueChanged.connect(self.calculate_target_prices)
        self.stop_loss_price.valueChanged.connect(self.auto_adjust_take_profit)  # Auto-adjust take profit to maintain R-multiple
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
        self.sl_minus_button.clicked.connect(self.on_sl_minus_clicked)
        self.sl_plus_button.clicked.connect(self.on_sl_plus_clicked)
        
        # Entry price adjustment buttons
        self.entry_minus_button.clicked.connect(self.on_entry_minus_clicked)
        self.entry_plus_button.clicked.connect(self.on_entry_plus_clicked)
        self.entry_plus_ten_button.clicked.connect(self.on_entry_plus_ten_clicked)
        
        # R-multiple controls
        self.r_minus_button.clicked.connect(self.on_r_minus_clicked)
        self.r_plus_button.clicked.connect(self.on_r_plus_clicked)
        self.r_multiple_spinbox.valueChanged.connect(self.on_r_multiple_changed)
        self.take_profit_price.valueChanged.connect(self.on_take_profit_price_manual_changed)
        
        # Multiple targets checkbox
        self.multiple_targets_checkbox.toggled.connect(self.on_multiple_targets_toggled)
        
        # Connect target widget changes
        for target in self.profit_targets:
            target['price'].valueChanged.connect(self.update_summary)
            target['price'].valueChanged.connect(self.on_target_price_changed)
            target['percent'].valueChanged.connect(self.calculate_target_percentages)
            target['r_multiple'].valueChanged.connect(self.on_target_r_multiple_changed)
        
        # Connect price changes for chart synchronization
        self.entry_price.valueChanged.connect(self.on_entry_price_changed)
        self.stop_loss_price.valueChanged.connect(self.on_stop_loss_price_changed)
        self.take_profit_price.valueChanged.connect(self.on_take_profit_price_changed)
        
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
        
    def on_take_profit_price_changed(self, value: float):
        """Handle take profit price change and emit signal"""
        self.take_profit_changed.emit(value)
        
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
                risk_percent_clamped = max(0.1, min(10.0, risk_percent))
                slider_value = int(risk_percent_clamped * 100)
                
                self.risk_slider.setValue(slider_value)
                self.risk_label.setText(f"{risk_percent:.2f}%")
                
                # Update order value and dollar risk displays
                order_value = shares * entry
                self.order_value_label.setText(f"${order_value:,.2f}")
                self.dollar_risk_label.setText(f"${dollar_risk:,.2f}")
                
                # Update summary
                self.update_summary()
                
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
            new_value = max(10, current_value - 1)  # 0.01% decrease, minimum 0.1%
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
            
            # Use risk calculator if available
            if self.risk_calculator:
                result = self.risk_calculator.calculate_position_size(
                    entry_price=entry,
                    stop_loss=stop_loss,
                    risk_percent=risk_percent
                )
                
                shares = result['shares']
                order_value = result['position_value']
                dollar_risk = result['dollar_risk']
            else:
                # Fallback calculation
                dollar_risk = self.account_value * (risk_percent / 100.0)
                risk_per_share = abs(entry - stop_loss)
                if risk_per_share > 0:
                    shares = int(dollar_risk / risk_per_share)
                else:
                    shares = 0
                order_value = shares * entry
                
            # Update displays
            self.position_size.setValue(shares)
            self.order_value_label.setText(f"${order_value:,.2f}")
            self.dollar_risk_label.setText(f"${dollar_risk:,.2f}")
            
            # Reset flag
            self._updating_from_risk = False
            
            self.update_summary()
            
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
            # Show multiple targets summary with R-multiples
            targets_text = ""
            for i, target in enumerate(self.profit_targets, 1):
                price = target['price'].value()
                percent = target['percent'].value()
                r_multiple = target['r_multiple'].value()
                if price > 0:
                    targets_text += f"<br>        Target {i}: ${price:.2f} ({percent}%, {r_multiple:.1f}R)"
            
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
            
            for i, target in enumerate(self.profit_targets, 1):
                price = target['price'].value()
                percent = target['percent'].value()
                
                if price > 0:
                    target_count += 1
                    total_percent += percent
                    
                    # Direction-specific target validation
                    if self.long_button.isChecked():
                        if price <= entry:
                            valid = False
                            warnings.append(f"Target {i} must be above entry for LONG")
                    else:  # SHORT
                        if price >= entry:
                            valid = False
                            warnings.append(f"Target {i} must be below entry for SHORT")
            
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
            
        # Gather order data
        order_data = {
            'symbol': self.symbol_input.text(),
            'direction': 'BUY' if self.long_button.isChecked() else 'SELL',
            'order_type': 'LMT' if self.limit_button.isChecked() else 'MKT',
            'quantity': self.position_size.value(),
            'entry_price': self.entry_price.value(),
            'stop_loss': self.stop_loss_price.value(),
            'take_profit': self.take_profit_price.value(),
            'risk_percent': self.risk_slider.value() / 100.0,
            'use_multiple_targets': self.use_multiple_targets,
            'profit_targets': self.get_profit_target_data(),
        }
        
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
        for i, target in enumerate(self.profit_targets):
            target['price'].setValue(0)
            target['percent'].setValue(50 if i == 0 else 30 if i == 1 else 20)
            target['r_multiple'].setValue(float(i + 1))  # Reset to 1R, 2R, 3R
        
    def set_account_value(self, value: float):
        """Set account value for position sizing calculations"""
        self.account_value = value
        self.calculate_position_size()
        
    def set_buying_power(self, buying_power: float):
        """Set buying power for position validation"""
        self.buying_power = buying_power
        self.update_summary()
        
    def set_risk_calculator(self, risk_calculator):
        """Set the risk calculator instance"""
        self.risk_calculator = risk_calculator
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
        
    def on_entry_plus_ten_clicked(self):
        """Handle entry price plus 0.10 button click"""
        current = self.entry_price.value()
        new_value = current + 0.10
        new_value = self.round_to_tick_size(new_value)
        self.entry_price.setValue(new_value)
        logger.info(f"Increased entry price by $0.10 to ${new_value:.2f}")
        
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
                
            # Update take profit price (temporarily disconnect to avoid loop)
            self.take_profit_price.valueChanged.disconnect()
            self.take_profit_price.setValue(take_profit)
            self.take_profit_price.valueChanged.connect(self.on_take_profit_price_manual_changed)
            
            # Manually emit chart synchronization signal
            self.on_take_profit_price_changed(take_profit)
            
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
            
            # Update R-multiple spinbox (temporarily disconnect to avoid loop)
            self.r_multiple_spinbox.valueChanged.disconnect()
            self.r_multiple_spinbox.setValue(max(0.1, r_multiple))
            self.r_multiple_spinbox.valueChanged.connect(self.on_r_multiple_changed)
            
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
            
            # Update R-multiple spinbox (temporarily disconnect to avoid loop)
            self.r_multiple_spinbox.valueChanged.disconnect()
            self.r_multiple_spinbox.setValue(max(0.1, r_multiple))
            self.r_multiple_spinbox.valueChanged.connect(self.on_r_multiple_changed)
            
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
            # Show multiple targets and hide single target
            self.take_profit_price.hide()
            for target in self.profit_targets:
                target['label'].show()
                target['price'].show()
                target['percent'].show()
                target['r_multiple'].show()
            
            # Calculate initial target prices based on R-multiples
            self.calculate_target_prices()
            logger.info("Enabled multiple profit targets")
        else:
            # Hide multiple targets and show single target
            for target in self.profit_targets:
                target['label'].hide()
                target['price'].hide()
                target['percent'].hide()
                target['r_multiple'].hide()
            self.take_profit_price.show()
            logger.info("Disabled multiple profit targets")
            
        self.update_summary()
        
    def calculate_target_prices(self):
        """Calculate target prices based on individual R-multiples"""
        try:
            entry = self.entry_price.value()
            stop_loss = self.stop_loss_price.value()
            
            if entry <= 0 or stop_loss <= 0:
                return
                
            # Calculate risk distance
            risk_distance = abs(entry - stop_loss)
            direction = "BUY" if self.long_button.isChecked() else "SELL"
            
            # Calculate target prices based on individual R-multiples
            for target in self.profit_targets:
                r_multiple = target['r_multiple'].value()
                
                if direction == "BUY":
                    target_price = entry + (r_multiple * risk_distance)
                else:
                    target_price = entry - (r_multiple * risk_distance)
                    
                # Update price field (temporarily disconnect to avoid loops)
                target['price'].valueChanged.disconnect()
                target['price'].setValue(target_price)
                target['price'].valueChanged.connect(self.update_summary)
                
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
                
            # Calculate risk distance
            risk_distance = abs(entry - stop_loss)
            direction = "BUY" if self.long_button.isChecked() else "SELL"
            
            # Find which R-multiple field changed and update its corresponding price
            sender = self.sender()
            for target in self.profit_targets:
                if target['r_multiple'] == sender:
                    r_multiple = target['r_multiple'].value()
                    
                    if direction == "BUY":
                        target_price = entry + (r_multiple * risk_distance)
                    else:
                        target_price = entry - (r_multiple * risk_distance)
                    
                    # Validate and set price
                    target_price = max(0.01, min(5000.0, target_price))
                    
                    # Update price field (temporarily disconnect to avoid loops)
                    target['price'].valueChanged.disconnect()
                    target['price'].setValue(target_price)
                    target['price'].valueChanged.connect(self.update_summary)
                    
                    logger.info(f"Updated target price to ${target_price:.2f} for {r_multiple:.1f}R")
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
                
            # Calculate risk distance
            risk_distance = abs(entry - stop_loss)
            direction = "BUY" if self.long_button.isChecked() else "SELL"
            
            if risk_distance <= 0:
                return
            
            # Find which price field changed and update its corresponding R-multiple
            sender = self.sender()
            for target in self.profit_targets:
                if target['price'] == sender:
                    target_price = target['price'].value()
                    
                    # Calculate R-multiple based on price
                    if direction == "BUY":
                        reward_distance = target_price - entry
                    else:
                        reward_distance = entry - target_price
                    
                    r_multiple = max(0.1, reward_distance / risk_distance)
                    
                    # Update R-multiple field (temporarily disconnect to avoid loops)
                    target['r_multiple'].valueChanged.disconnect()
                    target['r_multiple'].setValue(r_multiple)
                    target['r_multiple'].valueChanged.connect(self.on_target_r_multiple_changed)
                    
                    logger.info(f"Updated R-multiple to {r_multiple:.1f}R for target price ${target_price:.2f}")
                    break
                    
        except Exception as e:
            logger.error(f"Error updating R-multiple from target price: {str(e)}")
    
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