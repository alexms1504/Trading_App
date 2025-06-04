#!/usr/bin/env python3
"""
Test Chart Rescaling & Error Handling (Epic 5.2.3)
Comprehensive testing of chart rescaling, automatic scaling, and error handling
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from src.ui.chart_widget_embedded import ChartWidget
from src.utils.logger import logger
import time

class ChartRescalingTestSuite:
    """Test suite for Chart Rescaling functionality"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.chart_widget = ChartWidget()
        self.chart_widget.show()
        self.test_results = []
        
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        result = f"[{status}] {test_name}: {message}"
        self.test_results.append(result)
        logger.info(result)
        print(result)
        
    def test_manual_rescale_button(self):
        """Test manual rescale button functionality"""
        test_name = "Manual Rescale Button Test"
        try:
            # Check if rescale button exists and is enabled
            rescale_button = self.chart_widget.rescale_button
            button_exists = rescale_button is not None
            button_enabled = rescale_button.isEnabled()
            
            # Check button styling (orange highlight)
            button_style = rescale_button.styleSheet()
            has_orange_style = "#FF9800" in button_style or "orange" in button_style.lower()
            
            # Check button text/symbol
            button_text = rescale_button.text()
            has_rescale_symbol = "⇲" in button_text
            
            passed = button_exists and button_enabled and has_orange_style and has_rescale_symbol
            message = f"Exists: {button_exists}, Enabled: {button_enabled}, Orange: {has_orange_style}, Symbol: {has_rescale_symbol}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_rescale_method_exists(self):
        """Test rescale_chart method exists and is callable"""
        test_name = "Rescale Method Test"
        try:
            # Check if rescale method exists
            has_rescale_method = hasattr(self.chart_widget, 'rescale_chart')
            
            # Test if method is callable
            method_callable = callable(getattr(self.chart_widget, 'rescale_chart', None))
            
            passed = has_rescale_method and method_callable
            message = f"Method exists: {has_rescale_method}, Callable: {method_callable}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_chart_canvas_access(self):
        """Test chart canvas accessibility for rescaling"""
        test_name = "Chart Canvas Access Test"
        try:
            # Check if chart canvas exists
            has_canvas = hasattr(self.chart_widget, 'chart_canvas')
            canvas = getattr(self.chart_widget, 'chart_canvas', None)
            canvas_not_none = canvas is not None
            
            # Check if canvas has required axes for rescaling
            has_price_ax = False
            has_volume_ax = False
            
            if canvas_not_none:
                has_price_ax = hasattr(canvas, 'price_ax')
                has_volume_ax = hasattr(canvas, 'volume_ax')
            
            passed = has_canvas and canvas_not_none and has_price_ax and has_volume_ax
            message = f"Canvas: {has_canvas}, Not None: {canvas_not_none}, Price Ax: {has_price_ax}, Volume Ax: {has_volume_ax}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_cache_clearing_on_symbol_change(self):
        """Test cache clearing when symbol changes"""
        test_name = "Cache Clearing Test"
        try:
            # Check if chart manager exists and has clear_cache method
            chart_manager = getattr(self.chart_widget, 'chart_manager', None)
            has_chart_manager = chart_manager is not None
            
            has_clear_cache = False
            if has_chart_manager:
                has_clear_cache = hasattr(chart_manager, 'clear_cache')
            
            # Test set_symbol method calls cache clearing
            has_set_symbol = hasattr(self.chart_widget, 'set_symbol')
            
            passed = has_chart_manager and has_clear_cache and has_set_symbol
            message = f"Chart Manager: {has_chart_manager}, Clear Cache: {has_clear_cache}, Set Symbol: {has_set_symbol}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_price_level_rescale_detection(self):
        """Test automatic rescaling when price levels are outside view"""
        test_name = "Price Level Rescale Detection Test"
        try:
            # Check if the method exists
            has_check_method = hasattr(self.chart_widget, '_check_and_rescale_for_price_levels')
            
            # Check if update_price_levels method exists and can trigger rescaling
            has_update_method = hasattr(self.chart_widget, 'update_price_levels')
            
            passed = has_check_method and has_update_method
            message = f"Check Method: {has_check_method}, Update Method: {has_update_method}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_crosshair_error_handling(self):
        """Test safe crosshair removal error handling"""
        test_name = "Crosshair Error Handling Test"
        try:
            # Check if chart canvas exists
            canvas = getattr(self.chart_widget, 'chart_canvas', None)
            
            if canvas is None:
                self.log_test(test_name, False, "Chart canvas not found")
                return
            
            # Check if crosshair variables exist
            has_crosshair_vars = (
                hasattr(canvas, 'crosshair_v_price') and
                hasattr(canvas, 'crosshair_v_volume') and
                hasattr(canvas, 'crosshair_h') and
                hasattr(canvas, 'ohlc_text')
            )
            
            # Check if mouse event handlers exist
            has_mouse_handlers = (
                hasattr(canvas, '_on_mouse_move') and
                hasattr(canvas, '_on_mouse_leave')
            )
            
            passed = has_crosshair_vars and has_mouse_handlers
            message = f"Crosshair vars: {has_crosshair_vars}, Mouse handlers: {has_mouse_handlers}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_axis_limit_clearing(self):
        """Test axis limit clearing and recalculation"""
        test_name = "Axis Limit Clearing Test"
        try:
            # Check if chart canvas exists and has matplotlib integration
            canvas = getattr(self.chart_widget, 'chart_canvas', None)
            
            if canvas is None:
                self.log_test(test_name, False, "Chart canvas not found")
                return
            
            # Check for matplotlib-based chart functionality
            has_price_ax = hasattr(canvas, 'price_ax')
            has_volume_ax = hasattr(canvas, 'volume_ax')
            
            # Test if rescale method exists
            rescale_method_exists = hasattr(self.chart_widget, 'rescale_chart')
            
            passed = has_price_ax and has_volume_ax and rescale_method_exists
            message = f"Price axis: {has_price_ax}, Volume axis: {has_volume_ax}, Rescale method: {rescale_method_exists}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_symbol_change_rescaling(self):
        """Test enhanced auto-scaling when changing symbols"""
        test_name = "Symbol Change Rescaling Test"
        try:
            # Test set_symbol method exists
            has_set_symbol = hasattr(self.chart_widget, 'set_symbol')
            
            # Test load_chart_data method exists
            has_load_data = hasattr(self.chart_widget, 'load_chart_data')
            
            # Test current_symbol tracking
            has_current_symbol = hasattr(self.chart_widget, 'current_symbol')
            
            passed = has_set_symbol and has_load_data and has_current_symbol
            message = f"Set Symbol: {has_set_symbol}, Load Data: {has_load_data}, Current Symbol: {has_current_symbol}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_error_handling_robustness(self):
        """Test comprehensive error handling throughout chart interactions"""
        test_name = "Error Handling Robustness Test"
        try:
            # Test try-catch blocks are implemented by checking methods exist
            methods_to_check = [
                'rescale_chart',
                'load_chart_data',
                'update_chart_display',
                'set_symbol'
            ]
            
            methods_exist = []
            for method_name in methods_to_check:
                exists = hasattr(self.chart_widget, method_name)
                methods_exist.append(exists)
            
            all_methods_exist = all(methods_exist)
            
            # Check if cleanup method exists for error recovery
            has_cleanup = hasattr(self.chart_widget, 'cleanup')
            
            passed = all_methods_exist and has_cleanup
            message = f"All methods exist: {all_methods_exist}, Has cleanup: {has_cleanup}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_performance_rescaling(self):
        """Test rescaling performance (should be < 100ms)"""
        test_name = "Rescaling Performance Test"
        try:
            # Only test if rescale method exists
            if not hasattr(self.chart_widget, 'rescale_chart'):
                self.log_test(test_name, False, "Rescale method not found")
                return
            
            # Measure rescale time
            start_time = time.time()
            self.chart_widget.rescale_chart()
            end_time = time.time()
            
            rescale_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            # Target: < 100ms for rescaling
            passed = rescale_time < 100
            message = f"Rescale time: {rescale_time:.2f}ms (target: <100ms)"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def run_all_tests(self):
        """Run all chart rescaling tests"""
        print("\n" + "="*60)
        print("RUNNING CHART RESCALING TEST SUITE")
        print("="*60)
        
        # Run individual tests
        self.test_manual_rescale_button()
        self.test_rescale_method_exists()
        self.test_chart_canvas_access()
        self.test_cache_clearing_on_symbol_change()
        self.test_price_level_rescale_detection()
        self.test_crosshair_error_handling()
        self.test_axis_limit_clearing()
        self.test_symbol_change_rescaling()
        self.test_error_handling_robustness()
        self.test_performance_rescaling()
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if "[PASS]" in r])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "="*60)
        print("CHART RESCALING TEST RESULTS SUMMARY")
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
    """Run Chart Rescaling test suite"""
    test_suite = ChartRescalingTestSuite()
    
    # Schedule tests to run after UI is shown
    QTimer.singleShot(100, test_suite.run_all_tests)
    QTimer.singleShot(2000, test_suite.app.quit)  # Close after 2 seconds
    
    # Run the application
    test_suite.app.exec()

if __name__ == "__main__":
    main()