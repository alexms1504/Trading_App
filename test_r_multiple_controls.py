#!/usr/bin/env python3
"""
Test R-Multiple Risk/Reward Controls (Epic 3.1.3)
Comprehensive testing of R-multiple functionality and bidirectional synchronization
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from src.ui.order_assistant import OrderAssistantWidget
from src.utils.logger import logger

class RMultipleTestSuite:
    """Test suite for R-Multiple controls"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.order_assistant = OrderAssistantWidget()
        self.order_assistant.show()
        self.test_results = []
        
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        result = f"[{status}] {test_name}: {message}"
        self.test_results.append(result)
        logger.info(result)
        print(result)
        
    def test_r_multiple_range(self):
        """Test R-multiple spinbox range (0.1R to 10.0R)"""
        test_name = "R-Multiple Range Test"
        try:
            spinbox = self.order_assistant.r_multiple_spinbox
            
            # Test minimum value
            spinbox.setValue(0.05)  # Below minimum
            actual_min = spinbox.value()
            min_pass = actual_min >= 0.1
            
            # Test maximum value
            spinbox.setValue(15.0)  # Above maximum
            actual_max = spinbox.value()
            max_pass = actual_max <= 10.0
            
            # Test default value
            spinbox.setValue(2.0)
            default_pass = spinbox.value() == 2.0
            
            passed = min_pass and max_pass and default_pass
            message = f"Min: {actual_min}, Max: {actual_max}, Default: 2.0"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_r_multiple_buttons(self):
        """Test -1R and +1R adjustment buttons"""
        test_name = "R-Multiple Buttons Test"
        try:
            spinbox = self.order_assistant.r_multiple_spinbox
            
            # Set initial value
            spinbox.setValue(3.0)
            initial = spinbox.value()
            
            # Test +1R button
            self.order_assistant.on_r_plus_clicked()
            after_plus = spinbox.value()
            plus_pass = after_plus == (initial + 1.0)
            
            # Test -1R button
            self.order_assistant.on_r_minus_clicked()
            after_minus = spinbox.value()
            minus_pass = after_minus == (after_plus - 1.0)
            
            passed = plus_pass and minus_pass
            message = f"Initial: {initial}, After +1R: {after_plus}, After -1R: {after_minus}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_bidirectional_sync_r_to_price(self):
        """Test R-multiple to take profit price synchronization"""
        test_name = "R-Multiple to Price Sync Test"
        try:
            # Set up test conditions
            self.order_assistant.entry_price.setValue(100.0)
            self.order_assistant.stop_loss_price.setValue(95.0)
            
            # Test R-multiple change updates take profit
            self.order_assistant.r_multiple_spinbox.setValue(2.0)
            self.order_assistant.on_r_multiple_changed(2.0)
            
            take_profit = self.order_assistant.take_profit_price.value()
            
            # Expected: entry + (r_multiple * risk_distance)
            # Risk distance = |100 - 95| = 5
            # Expected TP = 100 + (2.0 * 5) = 110.0
            expected_tp = 110.0
            passed = abs(take_profit - expected_tp) < 0.01
            
            message = f"Entry: 100.0, SL: 95.0, 2R should give TP: {expected_tp}, Got: {take_profit}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_bidirectional_sync_price_to_r(self):
        """Test take profit price to R-multiple synchronization"""
        test_name = "Price to R-Multiple Sync Test"
        try:
            # Set up test conditions
            self.order_assistant.entry_price.setValue(50.0)
            self.order_assistant.stop_loss_price.setValue(48.0)
            
            # Set take profit manually and check R-multiple update
            self.order_assistant.take_profit_price.setValue(56.0)
            self.order_assistant.on_take_profit_price_manual_changed(56.0)
            
            r_multiple = self.order_assistant.r_multiple_spinbox.value()
            
            # Expected: reward_distance / risk_distance
            # Risk distance = |50 - 48| = 2
            # Reward distance = |56 - 50| = 6
            # Expected R = 6 / 2 = 3.0
            expected_r = 3.0
            passed = abs(r_multiple - expected_r) < 0.1
            
            message = f"Entry: 50.0, SL: 48.0, TP: 56.0 should give {expected_r}R, Got: {r_multiple}R"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_r_multiple_updates_on_price_changes(self):
        """Test R-multiple recalculates when entry/stop loss changes"""
        test_name = "R-Multiple Auto-Update Test"
        try:
            # Set initial values
            self.order_assistant.entry_price.setValue(100.0)
            self.order_assistant.stop_loss_price.setValue(90.0)
            self.order_assistant.take_profit_price.setValue(120.0)
            
            # Trigger price change update
            self.order_assistant.update_r_multiple_from_prices()
            initial_r = self.order_assistant.r_multiple_spinbox.value()
            
            # Change entry price and check R-multiple updates
            self.order_assistant.entry_price.setValue(110.0)
            self.order_assistant.update_r_multiple_from_prices()
            updated_r = self.order_assistant.r_multiple_spinbox.value()
            
            # R-multiple should change because entry price changed
            passed = abs(initial_r - updated_r) > 0.1
            
            message = f"Initial R: {initial_r}, After entry change R: {updated_r}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_order_summary_r_display(self):
        """Test R-multiple appears in order summary"""
        test_name = "Order Summary R-Multiple Display Test"
        try:
            # Set up order data
            self.order_assistant.symbol_input.setText("AAPL")
            self.order_assistant.entry_price.setValue(150.0)
            self.order_assistant.stop_loss_price.setValue(147.0)
            self.order_assistant.r_multiple_spinbox.setValue(2.5)
            self.order_assistant.on_r_multiple_changed(2.5)
            
            # Update summary
            self.order_assistant.update_summary()
            
            # Check if R-multiple appears in summary
            summary_text = self.order_assistant.summary_label.text()
            r_in_summary = "2.5R" in summary_text
            
            passed = r_in_summary
            message = f"R-multiple in summary: {r_in_summary}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_input_field_behavior(self):
        """Test ImprovedDoubleSpinBox behavior for R-multiple field"""
        test_name = "Input Field Behavior Test"
        try:
            spinbox = self.order_assistant.r_multiple_spinbox
            
            # Test if it's using ImprovedDoubleSpinBox
            class_name = spinbox.__class__.__name__
            is_improved = class_name == "ImprovedDoubleSpinBox"
            
            # Test basic functionality
            spinbox.setValue(1.5)
            value_set = spinbox.value() == 1.5
            
            passed = is_improved and value_set
            message = f"Class: {class_name}, Value set correctly: {value_set}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_short_position_r_multiple(self):
        """Test R-multiple calculations for SHORT positions"""
        test_name = "SHORT Position R-Multiple Test"
        try:
            # Set SHORT position
            self.order_assistant.short_button.setChecked(True)
            
            # Set prices for SHORT
            self.order_assistant.entry_price.setValue(100.0)
            self.order_assistant.stop_loss_price.setValue(105.0)  # Stop above entry for SHORT
            
            # Set R-multiple and check take profit
            self.order_assistant.r_multiple_spinbox.setValue(2.0)
            self.order_assistant.on_r_multiple_changed(2.0)
            
            take_profit = self.order_assistant.take_profit_price.value()
            
            # For SHORT: TP = entry - (r_multiple * risk_distance)
            # Risk distance = |100 - 105| = 5
            # Expected TP = 100 - (2.0 * 5) = 90.0
            expected_tp = 90.0
            passed = abs(take_profit - expected_tp) < 0.01
            
            message = f"SHORT: Entry: 100.0, SL: 105.0, 2R should give TP: {expected_tp}, Got: {take_profit}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def run_all_tests(self):
        """Run all R-multiple tests"""
        print("\n" + "="*60)
        print("RUNNING R-MULTIPLE CONTROLS TEST SUITE")
        print("="*60)
        
        # Run individual tests
        self.test_r_multiple_range()
        self.test_r_multiple_buttons()
        self.test_bidirectional_sync_r_to_price()
        self.test_bidirectional_sync_price_to_r()
        self.test_r_multiple_updates_on_price_changes()
        self.test_order_summary_r_display()
        self.test_input_field_behavior()
        self.test_short_position_r_multiple()
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if "[PASS]" in r])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "="*60)
        print("R-MULTIPLE TEST RESULTS SUMMARY")
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
    """Run R-Multiple test suite"""
    test_suite = RMultipleTestSuite()
    
    # Schedule tests to run after UI is shown
    QTimer.singleShot(100, test_suite.run_all_tests)
    QTimer.singleShot(2000, test_suite.app.quit)  # Close after 2 seconds
    
    # Run the application
    test_suite.app.exec()

if __name__ == "__main__":
    main()