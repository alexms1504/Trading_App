#!/usr/bin/env python3
"""
Test Performance Metrics and Benchmarks
Validate performance targets and measure actual system performance
"""

import sys
import os
import time
import psutil
import gc
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from src.ui.order_assistant import OrderAssistantWidget
from src.ui.chart_widget_embedded import ChartWidget
from src.ui.market_screener import MarketScreenerWidget
from main import MainWindow
from src.utils.logger import logger

class PerformanceTestSuite:
    """Test suite for performance validation"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.test_results = []
        self.performance_targets = {
            'ui_responsiveness': 50,      # < 50ms for UI interactions
            'r_multiple_calc': 5,         # < 5ms for R-multiple calculations
            'chart_rescaling': 100,       # < 100ms for chart rescaling
            'position_calc': 10,          # < 10ms for position calculations
            'summary_update': 25,         # < 25ms for summary updates
            'memory_usage': 150,          # < 150MB total memory
            'widget_creation': 200,       # < 200ms for widget creation
        }
        
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        result = f"[{status}] {test_name}: {message}"
        self.test_results.append(result)
        logger.info(result)
        print(result)
        
    def measure_time(self, func, *args, **kwargs):
        """Measure execution time of a function"""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000
        return result, duration_ms
        
    def get_memory_usage(self):
        """Get current memory usage in MB"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
        
    def test_ui_responsiveness(self):
        """Test UI responsiveness for basic interactions"""
        test_name = "UI Responsiveness Test"
        try:
            order_assistant = OrderAssistantWidget()
            order_assistant.show()
            QApplication.processEvents()
            
            # Test multiple UI interactions
            ui_times = []
            
            # Test symbol input
            _, time_ms = self.measure_time(order_assistant.symbol_input.setText, "AAPL")
            ui_times.append(time_ms)
            
            # Test price input
            _, time_ms = self.measure_time(order_assistant.entry_price.setValue, 150.0)
            ui_times.append(time_ms)
            
            # Test button clicks
            _, time_ms = self.measure_time(order_assistant.r_plus_button.click)
            ui_times.append(time_ms)
            
            # Test checkbox toggle
            _, time_ms = self.measure_time(order_assistant.multiple_targets_checkbox.setChecked, True)
            ui_times.append(time_ms)
            
            # Test slider movement
            _, time_ms = self.measure_time(order_assistant.risk_slider.setValue, 300)
            ui_times.append(time_ms)
            
            # Calculate average
            avg_time = sum(ui_times) / len(ui_times)
            max_time = max(ui_times)
            
            target = self.performance_targets['ui_responsiveness']
            passed = avg_time < target and max_time < target * 2
            
            message = f"Avg: {avg_time:.2f}ms, Max: {max_time:.2f}ms (target: <{target}ms)"
            self.log_test(test_name, passed, message)
            
            order_assistant.close()
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_r_multiple_calculation_performance(self):
        """Test R-multiple calculation performance"""
        test_name = "R-Multiple Calculation Performance Test"
        try:
            order_assistant = OrderAssistantWidget()
            
            # Setup test conditions
            order_assistant.entry_price.setValue(100.0)
            order_assistant.stop_loss_price.setValue(95.0)
            
            # Test R-multiple to price calculation
            r_to_price_times = []
            for r_val in [1.0, 1.5, 2.0, 2.5, 3.0]:
                _, time_ms = self.measure_time(order_assistant.on_r_multiple_changed, r_val)
                r_to_price_times.append(time_ms)
            
            # Test price to R-multiple calculation
            price_to_r_times = []
            for price in [105.0, 110.0, 115.0, 120.0, 125.0]:
                _, time_ms = self.measure_time(order_assistant.on_take_profit_price_manual_changed, price)
                price_to_r_times.append(time_ms)
            
            # Test R-multiple update from price changes
            update_times = []
            for _ in range(5):
                _, time_ms = self.measure_time(order_assistant.update_r_multiple_from_prices)
                update_times.append(time_ms)
            
            # Calculate averages
            avg_r_to_price = sum(r_to_price_times) / len(r_to_price_times)
            avg_price_to_r = sum(price_to_r_times) / len(price_to_r_times)
            avg_update = sum(update_times) / len(update_times)
            
            overall_avg = (avg_r_to_price + avg_price_to_r + avg_update) / 3
            
            target = self.performance_targets['r_multiple_calc']
            passed = overall_avg < target
            
            message = f"R→Price: {avg_r_to_price:.2f}ms, Price→R: {avg_price_to_r:.2f}ms, Update: {avg_update:.2f}ms (target: <{target}ms)"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_chart_rescaling_performance(self):
        """Test chart rescaling performance"""
        test_name = "Chart Rescaling Performance Test"
        try:
            chart_widget = ChartWidget()
            chart_widget.show()
            QApplication.processEvents()
            
            # Test manual rescaling
            rescale_times = []
            for _ in range(5):
                _, time_ms = self.measure_time(chart_widget.rescale_chart)
                rescale_times.append(time_ms)
            
            # Test price level updates (triggers auto-rescaling check)
            update_times = []
            for i in range(5):
                entry = 100.0 + i
                stop = 95.0 + i
                tp = 110.0 + i * 2
                _, time_ms = self.measure_time(chart_widget.update_price_levels, entry, stop, tp)
                update_times.append(time_ms)
            
            avg_rescale = sum(rescale_times) / len(rescale_times)
            avg_update = sum(update_times) / len(update_times)
            
            target = self.performance_targets['chart_rescaling']
            passed = avg_rescale < target and avg_update < target
            
            message = f"Manual rescale: {avg_rescale:.2f}ms, Price update: {avg_update:.2f}ms (target: <{target}ms)"
            self.log_test(test_name, passed, message)
            
            chart_widget.close()
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_position_calculation_performance(self):
        """Test position size calculation performance"""
        test_name = "Position Calculation Performance Test"
        try:
            order_assistant = OrderAssistantWidget()
            
            # Set up risk calculator (mock)
            order_assistant.account_value = 100000.0
            order_assistant.buying_power = 200000.0
            
            # Test position calculations with different values
            calc_times = []
            test_values = [
                (100.0, 95.0, 300),    # $100 entry, $95 stop, 3% risk
                (50.0, 47.5, 150),     # $50 entry, $47.50 stop, 1.5% risk
                (200.0, 195.0, 500),   # $200 entry, $195 stop, 5% risk
                (1.50, 1.45, 200),     # $1.50 entry, $1.45 stop, 2% risk
                (1000.0, 990.0, 100), # $1000 entry, $990 stop, 1% risk
            ]
            
            for entry, stop, risk_slider_val in test_values:
                order_assistant.entry_price.setValue(entry)
                order_assistant.stop_loss_price.setValue(stop)
                order_assistant.risk_slider.setValue(risk_slider_val)
                
                _, time_ms = self.measure_time(order_assistant.calculate_position_size)
                calc_times.append(time_ms)
            
            avg_time = sum(calc_times) / len(calc_times)
            max_time = max(calc_times)
            
            target = self.performance_targets['position_calc']
            passed = avg_time < target and max_time < target * 2
            
            message = f"Avg: {avg_time:.2f}ms, Max: {max_time:.2f}ms (target: <{target}ms)"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_summary_update_performance(self):
        """Test order summary update performance"""
        test_name = "Summary Update Performance Test"
        try:
            order_assistant = OrderAssistantWidget()
            
            # Set up complete order data
            order_assistant.symbol_input.setText("AAPL")
            order_assistant.account_value = 100000.0
            order_assistant.buying_power = 200000.0
            
            # Test summary updates with different configurations
            update_times = []
            
            # Single target updates
            for i in range(5):
                order_assistant.entry_price.setValue(100.0 + i)
                order_assistant.stop_loss_price.setValue(95.0 + i)
                order_assistant.take_profit_price.setValue(110.0 + i * 2)
                order_assistant.position_size.setValue(100 + i * 10)
                
                _, time_ms = self.measure_time(order_assistant.update_summary)
                update_times.append(time_ms)
            
            # Multiple targets updates
            order_assistant.multiple_targets_checkbox.setChecked(True)
            order_assistant.on_multiple_targets_toggled(True)
            
            for i in range(3):
                if len(order_assistant.profit_targets) > i:
                    order_assistant.profit_targets[i]['price'].setValue(105.0 + i * 5)
                    order_assistant.profit_targets[i]['percent'].setValue(30 + i * 10)
                
                _, time_ms = self.measure_time(order_assistant.update_summary)
                update_times.append(time_ms)
            
            avg_time = sum(update_times) / len(update_times)
            max_time = max(update_times)
            
            target = self.performance_targets['summary_update']
            passed = avg_time < target and max_time < target * 2
            
            message = f"Avg: {avg_time:.2f}ms, Max: {max_time:.2f}ms (target: <{target}ms)"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_memory_usage(self):
        """Test memory usage of components"""
        test_name = "Memory Usage Test"
        try:
            # Get baseline memory
            gc.collect()
            baseline_memory = self.get_memory_usage()
            
            # Create main components
            main_window = MainWindow()
            main_window.show()
            QApplication.processEvents()
            
            # Let everything initialize
            time.sleep(1)
            QApplication.processEvents()
            
            # Measure memory after initialization
            current_memory = self.get_memory_usage()
            memory_used = current_memory - baseline_memory
            
            # Test with some activity
            if main_window.order_assistant:
                for i in range(10):
                    main_window.order_assistant.entry_price.setValue(100.0 + i)
                    main_window.order_assistant.calculate_position_size()
                    main_window.order_assistant.update_summary()
                    QApplication.processEvents()
            
            # Measure memory after activity
            active_memory = self.get_memory_usage()
            activity_memory = active_memory - current_memory
            
            main_window.close()
            
            target = self.performance_targets['memory_usage']
            passed = current_memory < target
            
            message = f"Baseline: {baseline_memory:.1f}MB, Current: {current_memory:.1f}MB, Used: {memory_used:.1f}MB, Activity: {activity_memory:.1f}MB (target: <{target}MB)"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_widget_creation_performance(self):
        """Test widget creation performance"""
        test_name = "Widget Creation Performance Test"
        try:
            creation_times = {}
            
            # Test Order Assistant creation
            _, time_ms = self.measure_time(OrderAssistantWidget)
            creation_times['OrderAssistant'] = time_ms
            
            # Test Chart Widget creation
            _, time_ms = self.measure_time(ChartWidget)
            creation_times['ChartWidget'] = time_ms
            
            # Test Market Screener creation
            _, time_ms = self.measure_time(MarketScreenerWidget)
            creation_times['MarketScreener'] = time_ms
            
            # Test Main Window creation
            _, time_ms = self.measure_time(MainWindow)
            creation_times['MainWindow'] = time_ms
            
            avg_time = sum(creation_times.values()) / len(creation_times)
            max_time = max(creation_times.values())
            
            target = self.performance_targets['widget_creation']
            passed = avg_time < target and max_time < target * 2
            
            message = f"Avg: {avg_time:.2f}ms, Max: {max_time:.2f}ms"
            for widget, time_val in creation_times.items():
                message += f", {widget}: {time_val:.2f}ms"
            message += f" (target: <{target}ms)"
            
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_concurrent_operations(self):
        """Test performance under concurrent operations"""
        test_name = "Concurrent Operations Performance Test"
        try:
            order_assistant = OrderAssistantWidget()
            chart_widget = ChartWidget()
            
            # Simulate concurrent operations
            start_time = time.perf_counter()
            
            # Perform multiple operations simultaneously
            for i in range(5):
                # Update prices
                order_assistant.entry_price.setValue(100.0 + i)
                order_assistant.stop_loss_price.setValue(95.0 + i)
                
                # Calculate R-multiple
                order_assistant.r_multiple_spinbox.setValue(2.0 + i * 0.2)
                order_assistant.on_r_multiple_changed(2.0 + i * 0.2)
                
                # Update chart
                chart_widget.update_price_levels(100.0 + i, 95.0 + i, 110.0 + i * 2)
                
                # Calculate position
                order_assistant.calculate_position_size()
                
                # Update summary
                order_assistant.update_summary()
                
                # Process events
                QApplication.processEvents()
            
            end_time = time.perf_counter()
            total_time = (end_time - start_time) * 1000
            
            # Target: < 500ms for 5 concurrent operation cycles
            target = 500
            passed = total_time < target
            
            message = f"5 concurrent cycles: {total_time:.2f}ms (target: <{target}ms)"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_performance_consistency(self):
        """Test performance consistency over multiple runs"""
        test_name = "Performance Consistency Test"
        try:
            order_assistant = OrderAssistantWidget()
            
            # Test the same operation multiple times
            times = []
            for i in range(20):
                start_time = time.perf_counter()
                
                # Perform standard operations
                order_assistant.entry_price.setValue(100.0 + i)
                order_assistant.r_multiple_spinbox.setValue(2.0)
                order_assistant.on_r_multiple_changed(2.0)
                order_assistant.calculate_position_size()
                order_assistant.update_summary()
                
                end_time = time.perf_counter()
                times.append((end_time - start_time) * 1000)
            
            # Calculate statistics
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            variance = sum((t - avg_time) ** 2 for t in times) / len(times)
            std_dev = variance ** 0.5
            
            # Check consistency (standard deviation should be small)
            consistency_ok = std_dev < avg_time * 0.5  # Std dev < 50% of average
            performance_ok = avg_time < 30  # Average should be reasonable
            
            passed = consistency_ok and performance_ok
            
            message = f"Avg: {avg_time:.2f}ms, Min: {min_time:.2f}ms, Max: {max_time:.2f}ms, StdDev: {std_dev:.2f}ms"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def run_all_tests(self):
        """Run all performance tests"""
        print("\n" + "="*60)
        print("RUNNING PERFORMANCE VALIDATION TEST SUITE")
        print("="*60)
        print("Performance Targets:")
        for metric, target in self.performance_targets.items():
            print(f"  {metric}: <{target}{'ms' if 'memory' not in metric else 'MB'}")
        print()
        
        # Run individual tests
        self.test_ui_responsiveness()
        self.test_r_multiple_calculation_performance()
        self.test_chart_rescaling_performance()
        self.test_position_calculation_performance()
        self.test_summary_update_performance()
        self.test_memory_usage()
        self.test_widget_creation_performance()
        self.test_concurrent_operations()
        self.test_performance_consistency()
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if "[PASS]" in r])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "="*60)
        print("PERFORMANCE VALIDATION RESULTS SUMMARY")
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
        else:
            print("\n🎯 ALL PERFORMANCE TARGETS MET!")
            print("The trading platform meets professional performance standards.")
        
        return failed_tests == 0

def main():
    """Run Performance Validation test suite"""
    test_suite = PerformanceTestSuite()
    
    # Schedule tests to run after brief startup
    QTimer.singleShot(200, test_suite.run_all_tests)
    QTimer.singleShot(5000, test_suite.app.quit)  # Close after 5 seconds
    
    # Run the application
    test_suite.app.exec()

if __name__ == "__main__":
    main()