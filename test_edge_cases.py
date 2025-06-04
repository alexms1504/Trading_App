#!/usr/bin/env python3
"""
Test Edge Cases and Error Scenarios
Comprehensive testing of edge cases, error handling, and boundary conditions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from src.ui.order_assistant import OrderAssistantWidget
from src.ui.chart_widget_embedded import ChartWidget
from src.utils.logger import logger

class EdgeCasesTestSuite:
    """Test suite for edge cases and error scenarios"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.order_assistant = OrderAssistantWidget()
        self.chart_widget = ChartWidget()
        self.order_assistant.show()
        self.test_results = []
        
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        result = f"[{status}] {test_name}: {message}"
        self.test_results.append(result)
        logger.info(result)
        print(result)
        
    def test_extreme_price_values(self):
        """Test handling of extreme price values"""
        test_name = "Extreme Price Values Test"
        try:
            # Test very large values
            self.order_assistant.entry_price.setValue(999999.99)
            large_value_ok = self.order_assistant.entry_price.value() <= 999999.99
            
            # Test very small values
            self.order_assistant.entry_price.setValue(0.0001)
            small_value_ok = self.order_assistant.entry_price.value() >= 0.0001
            
            # Test negative values (should be rejected)
            self.order_assistant.entry_price.setValue(-10.0)
            negative_rejected = self.order_assistant.entry_price.value() >= 0
            
            # Test R-multiple extreme values
            self.order_assistant.r_multiple_spinbox.setValue(100.0)  # Above max
            r_max_ok = self.order_assistant.r_multiple_spinbox.value() <= 10.0
            
            self.order_assistant.r_multiple_spinbox.setValue(-1.0)  # Below min
            r_min_ok = self.order_assistant.r_multiple_spinbox.value() >= 0.1
            
            passed = large_value_ok and small_value_ok and negative_rejected and r_max_ok and r_min_ok
            message = f"Large: {large_value_ok}, Small: {small_value_ok}, Negative: {negative_rejected}, R-Max: {r_max_ok}, R-Min: {r_min_ok}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_zero_risk_distance(self):
        """Test handling when entry price equals stop loss"""
        test_name = "Zero Risk Distance Test"
        try:
            # Set entry and stop loss to same value
            self.order_assistant.entry_price.setValue(100.0)
            self.order_assistant.stop_loss_price.setValue(100.0)
            
            # Try to calculate position size
            position_before = self.order_assistant.position_size.value()
            self.order_assistant.calculate_position_size()
            position_after = self.order_assistant.position_size.value()
            
            # Position should be 0 or unchanged when risk distance is 0
            zero_risk_handled = position_after == 0
            
            # Try R-multiple calculation with zero risk
            self.order_assistant.take_profit_price.setValue(110.0)
            try:
                self.order_assistant.update_r_multiple_from_prices()
                r_calc_ok = True  # Should not crash
            except:
                r_calc_ok = False
            
            passed = zero_risk_handled and r_calc_ok
            message = f"Zero risk handled: {zero_risk_handled}, R-calc safe: {r_calc_ok}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_invalid_symbol_input(self):
        """Test handling of invalid symbol inputs"""
        test_name = "Invalid Symbol Input Test"
        try:
            invalid_symbols = ["", "   ", "123", "!@#$", "TOOLONGSYMBOL"]
            
            all_handled = True
            for symbol in invalid_symbols:
                try:
                    self.order_assistant.symbol_input.setText(symbol)
                    self.order_assistant.validate_inputs()
                    # Should not crash
                except Exception as e:
                    all_handled = False
                    logger.error(f"Symbol '{symbol}' caused error: {e}")
            
            # Test empty symbol validation
            self.order_assistant.symbol_input.setText("")
            validation_result = self.order_assistant.validate_inputs()
            empty_symbol_invalid = not validation_result  # Should return False for empty symbol
            
            passed = all_handled and empty_symbol_invalid
            message = f"Invalid symbols handled: {all_handled}, Empty validation: {empty_symbol_invalid}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_direction_mismatch_validation(self):
        """Test validation catches direction mismatches"""
        test_name = "Direction Mismatch Validation Test"
        try:
            # Test LONG position with stop above entry (invalid)
            self.order_assistant.long_button.setChecked(True)
            self.order_assistant.entry_price.setValue(100.0)
            self.order_assistant.stop_loss_price.setValue(105.0)  # Stop above entry for LONG
            self.order_assistant.take_profit_price.setValue(95.0)   # TP below entry for LONG
            
            long_validation = self.order_assistant.validate_inputs()
            long_invalid = not long_validation  # Should be invalid
            
            # Test SHORT position with stop below entry (invalid)
            self.order_assistant.short_button.setChecked(True)
            self.order_assistant.entry_price.setValue(100.0)
            self.order_assistant.stop_loss_price.setValue(95.0)   # Stop below entry for SHORT
            self.order_assistant.take_profit_price.setValue(105.0) # TP above entry for SHORT
            
            short_validation = self.order_assistant.validate_inputs()
            short_invalid = not short_validation  # Should be invalid
            
            passed = long_invalid and short_invalid
            message = f"LONG invalid detected: {long_invalid}, SHORT invalid detected: {short_invalid}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_multiple_targets_percentage_validation(self):
        """Test multiple targets percentage validation"""
        test_name = "Multiple Targets Percentage Validation Test"
        try:
            # Enable multiple targets
            self.order_assistant.multiple_targets_checkbox.setChecked(True)
            self.order_assistant.on_multiple_targets_toggled(True)
            
            # Set percentages that don't add to 100%
            if len(self.order_assistant.profit_targets) >= 3:
                self.order_assistant.profit_targets[0]['percent'].setValue(30)  # Total = 90%
                self.order_assistant.profit_targets[1]['percent'].setValue(30)
                self.order_assistant.profit_targets[2]['percent'].setValue(30)
                
                # Set valid prices
                self.order_assistant.entry_price.setValue(100.0)
                self.order_assistant.stop_loss_price.setValue(95.0)
                self.order_assistant.profit_targets[0]['price'].setValue(105.0)
                self.order_assistant.profit_targets[1]['price'].setValue(110.0)
                self.order_assistant.profit_targets[2]['price'].setValue(115.0)
                
                validation_90_percent = self.order_assistant.validate_inputs()
                invalid_percentage_detected = not validation_90_percent
                
                # Test percentages over 100%
                self.order_assistant.profit_targets[0]['percent'].setValue(50)  # Total = 130%
                self.order_assistant.profit_targets[1]['percent'].setValue(50)
                self.order_assistant.profit_targets[2]['percent'].setValue(30)
                
                validation_130_percent = self.order_assistant.validate_inputs()
                over_percentage_detected = not validation_130_percent
                
                passed = invalid_percentage_detected and over_percentage_detected
                message = f"90% invalid: {invalid_percentage_detected}, 130% invalid: {over_percentage_detected}"
            else:
                passed = False
                message = "Multiple targets not properly initialized"
                
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_chart_with_no_data(self):
        """Test chart behavior with no data"""
        test_name = "Chart No Data Test"
        try:
            # Test setting invalid symbol
            no_crash_1 = True
            try:
                self.chart_widget.set_symbol("")
            except Exception as e:
                no_crash_1 = False
                logger.error(f"Empty symbol crash: {e}")
            
            # Test updating chart with empty data
            no_crash_2 = True
            try:
                self.chart_widget.update_chart_display([])
            except Exception as e:
                no_crash_2 = False
                logger.error(f"Empty data crash: {e}")
            
            # Test rescaling with no chart data
            no_crash_3 = True
            try:
                self.chart_widget.rescale_chart()
            except Exception as e:
                no_crash_3 = False
                logger.error(f"Rescale with no data crash: {e}")
            
            passed = no_crash_1 and no_crash_2 and no_crash_3
            message = f"Empty symbol: {no_crash_1}, Empty data: {no_crash_2}, Rescale: {no_crash_3}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_price_level_edge_cases(self):
        """Test price level edge cases"""
        test_name = "Price Level Edge Cases Test"
        try:
            # Test updating price levels with None values
            no_crash_1 = True
            try:
                self.chart_widget.update_price_levels(entry=None, stop_loss=None, take_profit=None)
            except Exception as e:
                no_crash_1 = False
                logger.error(f"None price levels crash: {e}")
            
            # Test with extreme price values
            no_crash_2 = True
            try:
                self.chart_widget.update_price_levels(entry=999999.99, stop_loss=0.0001, take_profit=500000.0)
            except Exception as e:
                no_crash_2 = False
                logger.error(f"Extreme price levels crash: {e}")
            
            # Test price level manager with no chart
            no_crash_3 = True
            try:
                if hasattr(self.chart_widget, 'price_level_manager'):
                    manager = self.chart_widget.price_level_manager
                    if manager:
                        manager.update_price_levels(entry=100.0, stop_loss=95.0, take_profit=110.0)
            except Exception as e:
                no_crash_3 = False
                logger.error(f"Price level manager crash: {e}")
            
            passed = no_crash_1 and no_crash_2 and no_crash_3
            message = f"None values: {no_crash_1}, Extreme values: {no_crash_2}, Manager: {no_crash_3}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_rapid_input_changes(self):
        """Test rapid successive input changes"""
        test_name = "Rapid Input Changes Test"
        try:
            no_crash = True
            try:
                # Rapidly change values
                for i in range(10):
                    self.order_assistant.entry_price.setValue(100.0 + i)
                    self.order_assistant.stop_loss_price.setValue(95.0 + i * 0.5)
                    self.order_assistant.r_multiple_spinbox.setValue(1.0 + i * 0.1)
                    self.order_assistant.calculate_position_size()
                    self.order_assistant.update_summary()
                    
                    # Process events
                    QApplication.processEvents()
                    
            except Exception as e:
                no_crash = False
                logger.error(f"Rapid changes crash: {e}")
            
            # Test rapid R-multiple changes
            try:
                for r_val in [0.5, 1.0, 2.5, 5.0, 10.0, 0.1]:
                    self.order_assistant.r_multiple_spinbox.setValue(r_val)
                    self.order_assistant.on_r_multiple_changed(r_val)
                    QApplication.processEvents()
            except Exception as e:
                no_crash = False
                logger.error(f"Rapid R-multiple changes crash: {e}")
            
            passed = no_crash
            message = f"No crashes during rapid changes: {no_crash}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_memory_and_resource_cleanup(self):
        """Test memory and resource cleanup"""
        test_name = "Memory and Resource Cleanup Test"
        try:
            # Test chart cleanup
            cleanup_ok = True
            try:
                self.chart_widget.cleanup()
            except Exception as e:
                cleanup_ok = False
                logger.error(f"Chart cleanup error: {e}")
            
            # Test multiple chart widget creation/destruction
            widgets_ok = True
            try:
                temp_widgets = []
                for i in range(5):
                    widget = ChartWidget()
                    temp_widgets.append(widget)
                
                # Clean up
                for widget in temp_widgets:
                    widget.cleanup()
                    widget.deleteLater()
                    
            except Exception as e:
                widgets_ok = False
                logger.error(f"Widget creation/cleanup error: {e}")
            
            passed = cleanup_ok and widgets_ok
            message = f"Cleanup OK: {cleanup_ok}, Multiple widgets OK: {widgets_ok}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_input_field_boundaries(self):
        """Test input field boundary conditions"""
        test_name = "Input Field Boundaries Test"
        try:
            # Test decimal precision limits
            self.order_assistant.entry_price.setValue(123.123456789)
            entry_precision = len(str(self.order_assistant.entry_price.value()).split('.')[-1])
            precision_ok = entry_precision <= 4  # Should limit to 4 decimals
            
            # Test risk slider boundaries
            self.order_assistant.risk_slider.setValue(5)  # Below minimum
            risk_min = self.order_assistant.risk_slider.value() >= 10
            
            self.order_assistant.risk_slider.setValue(1500)  # Above maximum
            risk_max = self.order_assistant.risk_slider.value() <= 1000
            
            # Test percentage stop loss boundaries
            self.order_assistant.sl_pct_spinbox.setValue(-5.0)  # Negative
            pct_min = self.order_assistant.sl_pct_spinbox.value() >= 0.1
            
            self.order_assistant.sl_pct_spinbox.setValue(50.0)  # High value
            pct_max = self.order_assistant.sl_pct_spinbox.value() <= 20.0
            
            passed = precision_ok and risk_min and risk_max and pct_min and pct_max
            message = f"Precision: {precision_ok}, Risk boundaries: {risk_min and risk_max}, Pct boundaries: {pct_min and pct_max}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_calculation_robustness(self):
        """Test calculation robustness with edge values"""
        test_name = "Calculation Robustness Test"
        try:
            # Test with very small risk percentage
            self.order_assistant.risk_slider.setValue(10)  # 0.1%
            self.order_assistant.entry_price.setValue(1000.0)
            self.order_assistant.stop_loss_price.setValue(999.99)  # Tiny risk distance
            
            calc_small_ok = True
            try:
                self.order_assistant.calculate_position_size()
            except Exception as e:
                calc_small_ok = False
                logger.error(f"Small risk calculation error: {e}")
            
            # Test with very large risk percentage
            self.order_assistant.risk_slider.setValue(1000)  # 10%
            self.order_assistant.entry_price.setValue(1.0)
            self.order_assistant.stop_loss_price.setValue(0.5)  # Large risk distance
            
            calc_large_ok = True
            try:
                self.order_assistant.calculate_position_size()
            except Exception as e:
                calc_large_ok = False
                logger.error(f"Large risk calculation error: {e}")
            
            # Test R-multiple calculation edge cases
            r_calc_ok = True
            try:
                self.order_assistant.entry_price.setValue(100.0)
                self.order_assistant.stop_loss_price.setValue(99.9999)  # Tiny difference
                self.order_assistant.take_profit_price.setValue(100.0001)  # Tiny profit
                self.order_assistant.update_r_multiple_from_prices()
            except Exception as e:
                r_calc_ok = False
                logger.error(f"R-multiple edge calculation error: {e}")
            
            passed = calc_small_ok and calc_large_ok and r_calc_ok
            message = f"Small risk: {calc_small_ok}, Large risk: {calc_large_ok}, R-calc edge: {r_calc_ok}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def run_all_tests(self):
        """Run all edge cases tests"""
        print("\n" + "="*60)
        print("RUNNING EDGE CASES AND ERROR SCENARIOS TEST SUITE")
        print("="*60)
        
        # Run individual tests
        self.test_extreme_price_values()
        self.test_zero_risk_distance()
        self.test_invalid_symbol_input()
        self.test_direction_mismatch_validation()
        self.test_multiple_targets_percentage_validation()
        self.test_chart_with_no_data()
        self.test_price_level_edge_cases()
        self.test_rapid_input_changes()
        self.test_memory_and_resource_cleanup()
        self.test_input_field_boundaries()
        self.test_calculation_robustness()
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if "[PASS]" in r])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "="*60)
        print("EDGE CASES TEST RESULTS SUMMARY")
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
    """Run Edge Cases test suite"""
    test_suite = EdgeCasesTestSuite()
    
    # Schedule tests to run after UI is shown
    QTimer.singleShot(100, test_suite.run_all_tests)
    QTimer.singleShot(3000, test_suite.app.quit)  # Close after 3 seconds
    
    # Run the application
    test_suite.app.exec()

if __name__ == "__main__":
    main()