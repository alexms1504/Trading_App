"""
Market Screener Widget
UI component for real-time stock screening and selection
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QAbstractTableModel, QModelIndex
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QColor, QBrush

from src.utils.logger import logger
from src.core.market_screener import market_screener, ScreeningCriteria
from src.core.simple_threaded_fetcher import simple_threaded_market_screener


class ScreenerResultsModel(QAbstractTableModel):
    """Table model for screener results"""
    
    def __init__(self):
        super().__init__()
        self.headers = ['Symbol', 'Price', '% Change', 'Volume $']
        self.results = []
        
    def update_results(self, results: List[Dict[str, Any]]):
        """Update the results data"""
        self.beginResetModel()
        self.results = results
        self.endResetModel()
        
    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.results)
        
    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.headers)
        
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self.results):
            return None
            
        result = self.results[index.row()]
        col = index.column()
        
        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:  # Symbol
                return result.get('symbol', '')
            elif col == 1:  # Price
                price = result.get('latest_price', '')
                try:
                    return f"${float(price):.2f}" if price else 'N/A'
                except (ValueError, TypeError):
                    return 'N/A'
            elif col == 2:  # % Change
                distance = result.get('distance', '')
                try:
                    return f"{float(distance):.2f}%" if distance else ''
                except (ValueError, TypeError):
                    return str(distance)
            elif col == 3:  # Volume $
                volume = result.get('volume_usd', '')
                try:
                    if volume:
                        vol_float = float(volume)
                        if vol_float >= 1000000000:  # Billions
                            return f"${vol_float/1000000000:.1f}B"
                        elif vol_float >= 1000000:  # Millions
                            return f"${vol_float/1000000:.1f}M"
                        else:
                            return f"${vol_float/1000:.0f}K"
                    else:
                        return 'N/A'
                except (ValueError, TypeError):
                    return 'N/A'
                
        elif role == Qt.ItemDataRole.BackgroundRole:
            # Highlight rows based on % change
            if col == 2:  # % Change column
                try:
                    change = float(result.get('distance', 0))
                    if change >= 15:
                        return QBrush(QColor(0, 255, 0, 30))  # Light green for high gainers
                    elif change >= 10:
                        return QBrush(QColor(255, 255, 0, 30))  # Light yellow for good gainers
                except (ValueError, TypeError):
                    pass
                    
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [0, 1, 2, 3]:  # All columns center-aligned
                return Qt.AlignmentFlag.AlignCenter
                
        return None
        
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return None
        
    def get_result_at_row(self, row: int) -> Optional[Dict[str, Any]]:
        """Get the result data at a specific row"""
        if 0 <= row < len(self.results):
            return self.results[row]
        return None


class MarketScreenerWidget(QWidget):
    """Market screener widget for finding high-momentum stocks"""
    
    # Signals
    symbol_selected = pyqtSignal(str)  # Emitted when a symbol is selected for trading
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.screener = market_screener
        self.threaded_screener = simple_threaded_market_screener
        self.results_model = ScreenerResultsModel()
        self.update_timer = QTimer()
        self.is_screening = False
        self.current_results = []
        
        self.init_ui()
        self.setup_connections()
        self.setup_threaded_connections()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)  # Reduced spacing
        
        # Title (smaller)
        title_label = QLabel("Market Screener")
        title_font = QFont()
        title_font.setPointSize(12)  # Smaller title
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Controls section
        layout.addWidget(self.create_controls_section())
        
        # Results section
        layout.addWidget(self.create_results_section())
        
        # Status section
        layout.addWidget(self.create_status_section())
        
    def create_controls_section(self) -> QGroupBox:
        """Create the screening controls section"""
        group = QGroupBox("Screening Criteria")
        layout = QGridLayout()
        
        # Scan type
        layout.addWidget(QLabel("Scan Type:"), 0, 0)
        self.scan_type_combo = QComboBox()
        self.scan_type_combo.addItems([
            "TOP_PERC_GAIN",
            "MOST_ACTIVE",
            "HOT_BY_VOLUME",
            "TOP_PERC_LOSE",
            "MOST_ACTIVE_AVG_USD"
        ])
        self.scan_type_combo.setCurrentText("TOP_PERC_GAIN")
        layout.addWidget(self.scan_type_combo, 0, 1)
        
        # Minimum price
        layout.addWidget(QLabel("Min Price:"), 0, 2)
        self.min_price_spin = QDoubleSpinBox()
        self.min_price_spin.setRange(0.01, 1000.0)
        self.min_price_spin.setValue(0.4)
        self.min_price_spin.setPrefix("$")
        self.min_price_spin.setDecimals(2)
        layout.addWidget(self.min_price_spin, 0, 3)
        
        # Maximum price
        layout.addWidget(QLabel("Max Price:"), 1, 0)
        self.max_price_spin = QDoubleSpinBox()
        self.max_price_spin.setRange(1.0, 10000.0)
        self.max_price_spin.setValue(500.0)
        self.max_price_spin.setPrefix("$")
        self.max_price_spin.setDecimals(2)
        layout.addWidget(self.max_price_spin, 1, 1)
        
        # Minimum volume (in millions)
        layout.addWidget(QLabel("Min Volume:"), 1, 2)
        self.min_volume_spin = QSpinBox()
        self.min_volume_spin.setRange(1, 1000)
        self.min_volume_spin.setValue(8)
        self.min_volume_spin.setSuffix("M $")
        layout.addWidget(self.min_volume_spin, 1, 3)
        
        # Control buttons (smaller and more compact)
        self.start_button = QPushButton("Start")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 4px 6px;
                min-width: 60px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        layout.addWidget(self.start_button, 2, 0)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 4px 6px;
                min-width: 60px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.stop_button.setEnabled(False)
        layout.addWidget(self.stop_button, 2, 1)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 4px 6px;
                min-width: 60px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        layout.addWidget(self.refresh_button, 2, 2)
        
        # Add separate button for real market data (will not freeze UI)
        self.real_prices_button = QPushButton("Real $")
        self.real_prices_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 4px 6px;
                min-width: 50px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
        """)
        self.real_prices_button.setToolTip("Fetch real market prices (optimized for speed)")
        layout.addWidget(self.real_prices_button, 2, 3)
        
        # Auto-refresh checkbox (smaller) - moved to row 3
        self.auto_refresh_checkbox = QCheckBox("Auto (5s)")
        self.auto_refresh_checkbox.setChecked(True)
        self.auto_refresh_checkbox.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.auto_refresh_checkbox, 3, 0)
        
        group.setLayout(layout)
        return group
        
    def create_results_section(self) -> QGroupBox:
        """Create the results display section"""
        group = QGroupBox("Screening Results")
        layout = QVBoxLayout()
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(['Symbol', 'Price', '% Change', 'Volume $'])
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        
        # Set column widths
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Symbol
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Price
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # % Change
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Volume $
        
        layout.addWidget(self.results_table)
        
        # Action buttons for selected stock
        button_layout = QHBoxLayout()
        
        self.select_symbol_button = QPushButton("Use Symbol")
        self.select_symbol_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 4px 8px;
                min-width: 80px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.select_symbol_button.setEnabled(False)
        button_layout.addWidget(self.select_symbol_button)
        
        button_layout.addStretch()
        
        self.results_count_label = QLabel("No results")
        button_layout.addWidget(self.results_count_label)
        
        layout.addLayout(button_layout)
        
        group.setLayout(layout)
        return group
        
    def create_status_section(self) -> QWidget:
        """Create the status section"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        self.status_label = QLabel("Ready to screen")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        self.last_update_label = QLabel("Never updated")
        self.last_update_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.last_update_label)
        
        return widget
        
    def setup_connections(self):
        """Setup signal connections"""
        # Control buttons
        self.start_button.clicked.connect(self.start_screening)
        self.stop_button.clicked.connect(self.stop_screening)
        self.refresh_button.clicked.connect(self.refresh_results)
        self.real_prices_button.clicked.connect(self.fetch_real_prices)
        
        # Table selection
        self.results_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.results_table.itemDoubleClicked.connect(self.on_symbol_double_clicked)
        self.select_symbol_button.clicked.connect(self.on_select_symbol)
        
        # Auto-refresh timer
        self.update_timer.timeout.connect(self.refresh_results)
        
        # Auto-refresh checkbox - CRITICAL FIX for "Real $" button disappearing
        self.auto_refresh_checkbox.toggled.connect(self.on_auto_refresh_toggled)
        
        # Screener callbacks
        self.screener.add_update_callback(self.on_screener_update)
        
    def setup_threaded_connections(self):
        """Setup connections for threaded screener operations"""
        # Connect threaded screener signals
        self.threaded_screener.operation_started.connect(self.on_operation_started)
        self.threaded_screener.operation_completed.connect(self.on_operation_completed)
        self.threaded_screener.screening_started.connect(self.on_threaded_screening_started)
        self.threaded_screener.screening_stopped.connect(self.on_threaded_screening_stopped)
        self.threaded_screener.results_updated.connect(self.on_threaded_results_updated)
        self.threaded_screener.real_prices_updated.connect(self.on_threaded_real_prices_updated)
        self.threaded_screener.screening_error.connect(self.on_threaded_screening_error)
        self.threaded_screener.price_fetch_progress.connect(self.on_price_fetch_progress)
        logger.info("Threaded screener connections established")
        
    def start_screening(self):
        """Start market screening using threaded approach"""
        try:
            # Update UI immediately
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.status_label.setText("Starting screening...")
            self.status_label.setStyleSheet("color: blue; font-weight: bold;")
            
            # Update criteria from UI
            criteria = ScreeningCriteria(
                scan_code=self.scan_type_combo.currentText(),
                above_price=self.min_price_spin.value(),
                below_price=self.max_price_spin.value(),
                above_volume=self.min_volume_spin.value() * 1000000  # Convert to actual dollars
            )
            
            # Start screening using threaded approach (non-blocking)
            self.threaded_screener.start_screening_async(criteria)
                
        except Exception as e:
            logger.error(f"Error starting screening: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
    def stop_screening(self):
        """Stop market screening using threaded approach"""
        try:
            # Stop auto-refresh timer immediately
            self.update_timer.stop()
            
            # Update UI
            self.stop_button.setEnabled(False)
            self.status_label.setText("Stopping screening...")
            self.status_label.setStyleSheet("color: orange; font-weight: bold;")
            
            # Stop screening using threaded approach
            self.threaded_screener.stop_screening_async()
            
            logger.info("Stopping market screening...")
            
        except Exception as e:
            logger.error(f"Error stopping screening: {str(e)}")
            
    def refresh_results(self):
        """Manually refresh results using threaded approach"""
        if self.is_screening:
            # Show refreshing status
            self.status_label.setText("Refreshing...")
            self.status_label.setStyleSheet("color: blue; font-weight: bold;")
            
            # Refresh using threaded approach (non-blocking)
            self.threaded_screener.refresh_results_async()
            
    def fetch_real_prices(self):
        """Fetch real market prices using threaded approach"""
        if not self.is_screening:
            self.status_label.setText("Start screening first")
            self.status_label.setStyleSheet("color: orange; font-weight: bold;")
            return
            
        # Show user feedback
        self.real_prices_button.setText("Fetching...")
        self.real_prices_button.setEnabled(False)
        self.status_label.setText("Fetching real prices...")
        self.status_label.setStyleSheet("color: blue; font-weight: bold;")
        
        # Fetch real prices using threaded approach (non-blocking)
        self.threaded_screener.fetch_real_prices_async()
        
    def on_operation_started(self, operation: str):
        """Handle threaded operation started signal"""
        logger.info(f"Threaded screener operation started: {operation}")
        
    def on_operation_completed(self, operation: str):
        """Handle threaded operation completed signal"""
        logger.info(f"Threaded screener operation completed: {operation}")
        
        # Reset real prices button if that operation completed
        if operation == "fetch_real_prices":
            self.real_prices_button.setText("Real $")
            self.real_prices_button.setEnabled(True)
            
    def on_threaded_screening_started(self, result_count: int):
        """Handle threaded screening started signal"""
        self.is_screening = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText(f"Screening active ({result_count} results)...")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        
        # Start auto-refresh if enabled
        if self.auto_refresh_checkbox.isChecked():
            self.update_timer.start(5000)  # 5 seconds
            
        logger.info(f"Market screening started with {result_count} results")
        
    def on_threaded_screening_stopped(self):
        """Handle threaded screening stopped signal"""
        self.is_screening = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Screening stopped")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        logger.info("Market screening stopped")
        
    def on_threaded_results_updated(self, results: list):
        """Handle threaded results updated signal"""
        logger.info(f"on_threaded_results_updated called with {len(results)} results")
        self.update_results_display(results)
        self.status_label.setText("Screening active...")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        
    def on_threaded_real_prices_updated(self, results: list):
        """Handle threaded real prices updated signal"""
        self.update_results_display(results)
        self.status_label.setText("Real prices fetched!")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        
        # Auto-reset status after 3 seconds
        QTimer.singleShot(3000, lambda: self.status_label.setText("Screening active..."))
        
    def on_threaded_screening_error(self, error_msg: str):
        """Handle threaded screening error signal"""
        logger.error(f"Threaded screening error: {error_msg}")
        self.status_label.setText(f"Error: {error_msg}")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        
        # Reset UI state
        if not self.is_screening:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
        # Reset real prices button if it was fetching
        if self.real_prices_button.text() == "Fetching...":
            self.real_prices_button.setText("Real $")
            self.real_prices_button.setEnabled(True)
            
    def on_price_fetch_progress(self, current: int, total: int):
        """Handle price fetch progress signal"""
        progress_text = f"Fetching... {current}/{total}"
        self.real_prices_button.setText(progress_text)
        
    def on_screener_update(self, results):
        """Handle screener results update"""
        try:
            # For auto-updates, use fast mode without real market data to prevent freezing
            formatted_results = self.screener.get_formatted_results(fetch_real_data=False)
            self.update_results_display(formatted_results)
        except Exception as e:
            logger.error(f"Error handling screener update: {str(e)}")
            
    def update_results_display(self, results: List[Dict[str, Any]]):
        """Update the results table display"""
        try:
            # Clear existing results
            self.results_table.setRowCount(0)
            self.current_results = results
            
            # Populate table
            self.results_table.setRowCount(len(results))
            
            for row, result in enumerate(results):
                # Symbol
                symbol_item = QTableWidgetItem(result.get('symbol', ''))
                symbol_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                symbol_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                self.results_table.setItem(row, 0, symbol_item)
                
                # Price
                price = result.get('latest_price', '')
                try:
                    price_val = float(price) if price else 0.0
                    price_text = f"${price_val:.2f}"
                    price_item = QTableWidgetItem(price_text)
                except (ValueError, TypeError):
                    price_item = QTableWidgetItem("N/A")
                    
                price_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.results_table.setItem(row, 1, price_item)
                
                # % Change
                distance = result.get('distance', '')
                try:
                    change_val = float(distance) if distance else 0.0
                    change_text = f"{change_val:.2f}%"
                    change_item = QTableWidgetItem(change_text)
                    change_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    # Color coding
                    if change_val >= 15:
                        change_item.setBackground(QColor(0, 255, 0, 30))  # Light green
                    elif change_val >= 10:
                        change_item.setBackground(QColor(255, 255, 0, 30))  # Light yellow
                        
                except (ValueError, TypeError):
                    change_item = QTableWidgetItem(str(distance))
                    change_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                self.results_table.setItem(row, 2, change_item)
                
                # Volume $
                volume = result.get('volume_usd', '')
                try:
                    if volume:
                        vol_float = float(volume)
                        if vol_float >= 1000000000:  # Billions
                            vol_text = f"${vol_float/1000000000:.1f}B"
                        elif vol_float >= 1000000:  # Millions
                            vol_text = f"${vol_float/1000000:.1f}M"
                        else:
                            vol_text = f"${vol_float/1000:.0f}K"
                        volume_item = QTableWidgetItem(vol_text)
                    else:
                        volume_item = QTableWidgetItem("N/A")
                except (ValueError, TypeError):
                    volume_item = QTableWidgetItem("N/A")
                    
                volume_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.results_table.setItem(row, 3, volume_item)
            
            # Update status
            count = len(results)
            self.results_count_label.setText(f"{count} results")
            self.last_update_label.setText(f"Updated: {datetime.now().strftime('%H:%M:%S')}")
            
            if count > 0:
                self.status_label.setText(f"Found {count} stocks")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.status_label.setText("No results found")
                self.status_label.setStyleSheet("color: orange; font-weight: bold;")
                
        except Exception as e:
            logger.error(f"Error updating results display: {str(e)}")
            
    def on_selection_changed(self):
        """Handle table selection change"""
        selected_rows = self.results_table.selectionModel().selectedRows()
        self.select_symbol_button.setEnabled(len(selected_rows) > 0)
        
    def on_symbol_double_clicked(self, item):
        """Handle double-click on symbol"""
        row = item.row()
        if 0 <= row < len(self.current_results):
            result = self.current_results[row]
            symbol = result.get('symbol', '')
            if symbol:
                self.symbol_selected.emit(symbol)
                logger.info(f"Double-clicked symbol: {symbol}")
                
    def on_select_symbol(self):
        """Handle select symbol button click"""
        current_row = self.results_table.currentRow()
        if current_row >= 0 and current_row < len(self.current_results):
            result = self.current_results[current_row]
            symbol = result.get('symbol', '')
            if symbol:
                self.symbol_selected.emit(symbol)
                logger.info(f"Selected symbol: {symbol}")
                    
    def get_selected_symbol(self) -> Optional[str]:
        """Get currently selected symbol"""
        current_row = self.results_table.currentRow()
        if current_row >= 0 and current_row < len(self.current_results):
            result = self.current_results[current_row]
            return result.get('symbol', '')
        return None
        
    def on_auto_refresh_toggled(self, checked: bool):
        """Handle auto-refresh checkbox toggle - CRITICAL FIX for Real $ button issue"""
        try:
            if checked:
                # Start auto-refresh if screening is active
                if self.is_screening:
                    self.update_timer.start(5000)  # 5 seconds
                    logger.info("Auto-refresh enabled (5 seconds)")
            else:
                # Stop auto-refresh timer - this was the missing piece!
                self.update_timer.stop()
                logger.info("Auto-refresh disabled - timer stopped")
                
        except Exception as e:
            logger.error(f"Error toggling auto-refresh: {str(e)}")
        
    def cleanup(self):
        """Cleanup resources when widget is destroyed"""
        try:
            # Stop any active screening
            if self.is_screening:
                self.threaded_screener.stop_screening_async()
                
            # Cleanup threaded screener
            self.threaded_screener.cleanup()
            
            # Remove callbacks
            self.screener.remove_update_callback(self.on_screener_update)
        except Exception as e:
            logger.error(f"Error during screener cleanup: {str(e)}")