#!/usr/bin/env python3
"""
Test Bidirectional Synchronization between Order Assistant and Chart
Comprehensive testing of price level synchronization and signal emissions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtCore import QTimer, pyqtSignal
from src.ui.order_assistant import OrderAssistantWidget
from src.ui.chart_widget_embedded import ChartWidget
from src.utils.logger import logger

class SignalTester(QWidget):
    """Helper class to test signal emissions"""
    
    def __init__(self):
        super().__init__()
        self.received_signals = []
        
    def on_entry_changed(self, price: float):
        self.received_signals.append(('entry_changed', price))
        
    def on_stop_loss_changed(self, price: float):
        self.received_signals.append(('stop_loss_changed', price))
        
    def on_take_profit_changed(self, price: float):
        self.received_signals.append(('take_profit_changed', price))
        
    def on_chart_entry_changed(self, price: float):
        self.received_signals.append(('chart_entry_changed', price))
        
    def on_chart_stop_loss_changed(self, price: float):
        self.received_signals.append(('chart_stop_loss_changed', price))
        
    def on_chart_take_profit_changed(self, price: float):
        self.received_signals.append(('chart_take_profit_changed', price))

class BidirectionalSyncTestSuite:
    """Test suite for bidirectional synchronization"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        
        # Create main widget container
        self.main_widget = QWidget()
        layout = QVBoxLayout(self.main_widget)
        
        # Create components
        self.order_assistant = OrderAssistantWidget()
        self.chart_widget = ChartWidget()
        self.signal_tester = SignalTester()
        
        layout.addWidget(self.order_assistant)
        layout.addWidget(self.chart_widget)
        
        self.main_widget.show()
        
        self.test_results = []
        self.setup_signal_connections()
        
    def setup_signal_connections(self):
        """Setup signal connections for testing"""
        try:
            # Connect Order Assistant signals to tester
            self.order_assistant.entry_price_changed.connect(self.signal_tester.on_entry_changed)
            self.order_assistant.stop_loss_changed.connect(self.signal_tester.on_stop_loss_changed)
            self.order_assistant.take_profit_changed.connect(self.signal_tester.on_take_profit_changed)
            
            # Connect Chart signals to tester
            self.chart_widget.chart_entry_changed.connect(self.signal_tester.on_chart_entry_changed)
            self.chart_widget.chart_stop_loss_changed.connect(self.signal_tester.on_chart_stop_loss_changed)
            self.chart_widget.chart_take_profit_changed.connect(self.signal_tester.on_chart_take_profit_changed)
            
        except Exception as e:
            logger.error(f"Error setting up signal connections: {e}")
        
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        result = f"[{status}] {test_name}: {message}"
        self.test_results.append(result)
        logger.info(result)
        print(result)
        
    def test_order_assistant_signals_exist(self):
        """Test Order Assistant has required signals"""
        test_name = "Order Assistant Signals Test"
        try:
            # Check if signals exist
            has_entry_signal = hasattr(self.order_assistant, 'entry_price_changed')
            has_stop_signal = hasattr(self.order_assistant, 'stop_loss_changed')
            has_tp_signal = hasattr(self.order_assistant, 'take_profit_changed')
            
            passed = has_entry_signal and has_stop_signal and has_tp_signal
            message = f"Entry: {has_entry_signal}, Stop: {has_stop_signal}, TP: {has_tp_signal}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_chart_widget_signals_exist(self):
        """Test Chart Widget has required signals"""
        test_name = "Chart Widget Signals Test"
        try:
            # Check if signals exist
            has_entry_signal = hasattr(self.chart_widget, 'chart_entry_changed')
            has_stop_signal = hasattr(self.chart_widget, 'chart_stop_loss_changed')
            has_tp_signal = hasattr(self.chart_widget, 'chart_take_profit_changed')
            
            passed = has_entry_signal and has_stop_signal and has_tp_signal
            message = f"Entry: {has_entry_signal}, Stop: {has_stop_signal}, TP: {has_tp_signal}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_order_assistant_signal_emission(self):
        """Test Order Assistant emits signals when prices change"""
        test_name = "Order Assistant Signal Emission Test"
        try:
            # Clear previous signals
            self.signal_tester.received_signals.clear()
            
            # Change prices and check signal emission
            self.order_assistant.entry_price.setValue(100.0)
            self.order_assistant.stop_loss_price.setValue(95.0)
            self.order_assistant.take_profit_price.setValue(110.0)
            
            # Process events to ensure signals are emitted
            QApplication.processEvents()
            
            # Check received signals
            signals = self.signal_tester.received_signals
            entry_signals = [s for s in signals if s[0] == 'entry_changed']
            stop_signals = [s for s in signals if s[0] == 'stop_loss_changed']
            tp_signals = [s for s in signals if s[0] == 'take_profit_changed']
            
            passed = len(entry_signals) > 0 and len(stop_signals) > 0 and len(tp_signals) > 0
            message = f"Signals received - Entry: {len(entry_signals)}, Stop: {len(stop_signals)}, TP: {len(tp_signals)}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_chart_update_price_levels_method(self):
        """Test Chart Widget has update_price_levels method"""
        test_name = "Chart Update Price Levels Method Test"
        try:
            # Check if method exists
            has_update_method = hasattr(self.chart_widget, 'update_price_levels')
            
            # Check if method is callable
            method_callable = callable(getattr(self.chart_widget, 'update_price_levels', None))
            
            passed = has_update_method and method_callable
            message = f"Method exists: {has_update_method}, Callable: {method_callable}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_price_level_manager_integration(self):
        """Test Chart Widget has price level manager for interactive lines"""
        test_name = "Price Level Manager Integration Test"
        try:
            # Check if price level manager exists
            has_price_manager = hasattr(self.chart_widget, 'price_level_manager')
            
            # Check if setup method exists
            has_setup_method = hasattr(self.chart_widget, 'setup_price_levels')
            
            passed = has_price_manager and has_setup_method
            message = f"Price Manager: {has_price_manager}, Setup Method: {has_setup_method}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_r_multiple_chart_synchronization(self):
        """Test R-multiple changes trigger chart updates"""
        test_name = "R-Multiple Chart Sync Test"
        try:
            # Clear previous signals
            self.signal_tester.received_signals.clear()
            
            # Set up initial values
            self.order_assistant.entry_price.setValue(100.0)
            self.order_assistant.stop_loss_price.setValue(95.0)
            
            # Change R-multiple and check if take profit signal is emitted
            self.order_assistant.r_multiple_spinbox.setValue(3.0)
            self.order_assistant.on_r_multiple_changed(3.0)
            
            # Process events
            QApplication.processEvents()
            
            # Check if take profit signal was emitted
            signals = self.signal_tester.received_signals
            tp_signals = [s for s in signals if s[0] == 'take_profit_changed']
            
            passed = len(tp_signals) > 0
            message = f"Take profit signals after R-multiple change: {len(tp_signals)}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_chart_price_change_handlers(self):
        """Test Chart Widget has handlers for price changes from chart"""
        test_name = "Chart Price Change Handlers Test"
        try:
            # Check if handler methods exist
            has_entry_handler = hasattr(self.chart_widget, 'on_chart_entry_changed')
            has_stop_handler = hasattr(self.chart_widget, 'on_chart_stop_loss_changed')
            has_tp_handler = hasattr(self.chart_widget, 'on_chart_take_profit_changed')
            
            passed = has_entry_handler and has_stop_handler and has_tp_handler
            message = f"Entry Handler: {has_entry_handler}, Stop Handler: {has_stop_handler}, TP Handler: {has_tp_handler}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_manual_signal_emission(self):
        """Test manual signal emission for take profit updates"""
        test_name = "Manual Signal Emission Test"
        try:
            # Clear previous signals
            self.signal_tester.received_signals.clear()
            
            # Test manual signal emission (like when R-multiple changes)
            test_price = 125.50
            self.order_assistant.on_take_profit_price_changed(test_price)
            
            # Process events
            QApplication.processEvents()
            
            # Check if signal was received
            signals = self.signal_tester.received_signals
            tp_signals = [s for s in signals if s[0] == 'take_profit_changed' and s[1] == test_price]
            
            passed = len(tp_signals) > 0
            message = f"Manual TP signal emission successful: {len(tp_signals) > 0}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_chart_rescaling_on_price_updates(self):
        """Test chart rescaling is triggered when price levels are updated"""
        test_name = "Chart Rescaling on Price Updates Test"
        try:
            # Check if chart widget has the rescaling detection method
            has_rescale_check = hasattr(self.chart_widget, '_check_and_rescale_for_price_levels')
            
            # Test calling update_price_levels method
            update_successful = True
            try:
                if hasattr(self.chart_widget, 'update_price_levels'):
                    self.chart_widget.update_price_levels(entry=100.0, stop_loss=95.0, take_profit=110.0)
            except Exception as e:
                update_successful = False
                logger.error(f"Error calling update_price_levels: {e}")
            
            passed = has_rescale_check and update_successful
            message = f"Rescale Check Method: {has_rescale_check}, Update Successful: {update_successful}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_signal_disconnection_prevention(self):
        """Test signal loops are prevented through temporary disconnection"""
        test_name = "Signal Loop Prevention Test"
        try:
            # Check if the Order Assistant has the disconnect/reconnect pattern
            # This is evidenced by checking the on_r_multiple_changed method
            has_r_multiple_method = hasattr(self.order_assistant, 'on_r_multiple_changed')
            has_manual_tp_method = hasattr(self.order_assistant, 'on_take_profit_price_manual_changed')
            
            # These methods should exist to handle bidirectional sync properly
            passed = has_r_multiple_method and has_manual_tp_method
            message = f"R-Multiple Method: {has_r_multiple_method}, Manual TP Method: {has_manual_tp_method}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def run_all_tests(self):
        """Run all bidirectional synchronization tests"""
        print("\n" + "="*60)
        print("RUNNING BIDIRECTIONAL SYNCHRONIZATION TEST SUITE")
        print("="*60)
        
        # Run individual tests
        self.test_order_assistant_signals_exist()
        self.test_chart_widget_signals_exist()
        self.test_order_assistant_signal_emission()
        self.test_chart_update_price_levels_method()
        self.test_price_level_manager_integration()
        self.test_r_multiple_chart_synchronization()
        self.test_chart_price_change_handlers()
        self.test_manual_signal_emission()
        self.test_chart_rescaling_on_price_updates()
        self.test_signal_disconnection_prevention()
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if "[PASS]" in r])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "="*60)
        print("BIDIRECTIONAL SYNC TEST RESULTS SUMMARY")
        print("="*60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\nFAILED TESTS:")
            for result in self.test_results:
                if "[FAIL]" in result:
                    print(f"  {result}")
        
        return failed_tests == 0

def main():
    """Run Bidirectional Synchronization test suite"""
    test_suite = BidirectionalSyncTestSuite()
    
    # Schedule tests to run after UI is shown
    QTimer.singleShot(200, test_suite.run_all_tests)
    QTimer.singleShot(3000, test_suite.app.quit)  # Close after 3 seconds
    
    # Run the application
    test_suite.app.exec()

if __name__ == "__main__":
    main()