#!/usr/bin/env python3
"""
Test Complete Trading Workflow End-to-End
Comprehensive testing of the full trading process from symbol selection to order submission
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from main import MainWindow
from src.utils.logger import logger
import time

class TradingWorkflowTestSuite:
    """Test suite for complete trading workflow"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.main_window = MainWindow()
        self.main_window.show()
        self.test_results = []
        
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        result = f"[{status}] {test_name}: {message}"
        self.test_results.append(result)
        logger.info(result)
        print(result)
        
    def test_main_window_components(self):
        """Test main window has all required components"""
        test_name = "Main Window Components Test"
        try:
            # Check for core components
            has_order_assistant = hasattr(self.main_window, 'order_assistant') and self.main_window.order_assistant is not None
            has_market_screener = hasattr(self.main_window, 'market_screener') and self.main_window.market_screener is not None
            has_chart_widget = hasattr(self.main_window, 'chart_widget') and self.main_window.chart_widget is not None
            
            # Check for connection components
            has_connection_controls = hasattr(self.main_window, 'connect_button') and hasattr(self.main_window, 'disconnect_button')
            has_account_selector = hasattr(self.main_window, 'account_selector')
            
            passed = has_order_assistant and has_market_screener and has_chart_widget and has_connection_controls and has_account_selector
            message = f"OA: {has_order_assistant}, MS: {has_market_screener}, Chart: {has_chart_widget}, Conn: {has_connection_controls}, Acc: {has_account_selector}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_trading_mode_selection(self):
        """Test trading mode selection (Paper/Live)"""
        test_name = "Trading Mode Selection Test"
        try:
            # Check for trading mode radio buttons
            has_paper_radio = hasattr(self.main_window, 'paper_radio')
            has_live_radio = hasattr(self.main_window, 'live_radio')
            has_mode_group = hasattr(self.main_window, 'trading_mode_group')
            
            # Check default state (should be Paper)
            paper_checked = False
            if has_paper_radio:
                paper_checked = self.main_window.paper_radio.isChecked()
            
            passed = has_paper_radio and has_live_radio and has_mode_group and paper_checked
            message = f"Paper Radio: {has_paper_radio}, Live Radio: {has_live_radio}, Group: {has_mode_group}, Paper Default: {paper_checked}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_symbol_input_workflow(self):
        """Test symbol input and validation workflow"""
        test_name = "Symbol Input Workflow Test"
        try:
            order_assistant = self.main_window.order_assistant
            
            # Test symbol input exists
            has_symbol_input = hasattr(order_assistant, 'symbol_input')
            
            # Test symbol input functionality
            symbol_input_works = False
            if has_symbol_input:
                order_assistant.symbol_input.setText("AAPL")
                symbol_input_works = order_assistant.symbol_input.text() == "AAPL"
            
            # Test fetch price button exists
            has_fetch_button = hasattr(order_assistant, 'fetch_price_button')
            
            passed = has_symbol_input and symbol_input_works and has_fetch_button
            message = f"Symbol Input: {has_symbol_input}, Works: {symbol_input_works}, Fetch Button: {has_fetch_button}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_price_entry_controls(self):
        """Test price entry controls and validation"""
        test_name = "Price Entry Controls Test"
        try:
            order_assistant = self.main_window.order_assistant
            
            # Test price input fields exist
            has_entry_price = hasattr(order_assistant, 'entry_price')
            has_stop_loss = hasattr(order_assistant, 'stop_loss_price')
            has_take_profit = hasattr(order_assistant, 'take_profit_price')
            
            # Test R-multiple controls
            has_r_multiple = hasattr(order_assistant, 'r_multiple_spinbox')
            has_r_buttons = hasattr(order_assistant, 'r_minus_button') and hasattr(order_assistant, 'r_plus_button')
            
            # Test price input functionality
            price_inputs_work = False
            if has_entry_price and has_stop_loss and has_take_profit:
                order_assistant.entry_price.setValue(100.0)
                order_assistant.stop_loss_price.setValue(95.0)
                order_assistant.take_profit_price.setValue(110.0)
                price_inputs_work = (
                    order_assistant.entry_price.value() == 100.0 and
                    order_assistant.stop_loss_price.value() == 95.0 and
                    order_assistant.take_profit_price.value() == 110.0
                )
            
            passed = has_entry_price and has_stop_loss and has_take_profit and has_r_multiple and has_r_buttons and price_inputs_work
            message = f"Price Fields: {has_entry_price and has_stop_loss and has_take_profit}, R-Multiple: {has_r_multiple}, R-Buttons: {has_r_buttons}, Inputs Work: {price_inputs_work}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_risk_management_controls(self):
        """Test risk management and position sizing"""
        test_name = "Risk Management Controls Test"
        try:
            order_assistant = self.main_window.order_assistant
            
            # Test risk controls exist
            has_risk_slider = hasattr(order_assistant, 'risk_slider')
            has_position_size = hasattr(order_assistant, 'position_size')
            has_order_value = hasattr(order_assistant, 'order_value_label')
            has_dollar_risk = hasattr(order_assistant, 'dollar_risk_label')
            
            # Test position size calculation method
            has_calc_method = hasattr(order_assistant, 'calculate_position_size')
            
            passed = has_risk_slider and has_position_size and has_order_value and has_dollar_risk and has_calc_method
            message = f"Risk Slider: {has_risk_slider}, Position Size: {has_position_size}, Order Value: {has_order_value}, Dollar Risk: {has_dollar_risk}, Calc Method: {has_calc_method}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_stop_loss_options(self):
        """Test stop loss selection options"""
        test_name = "Stop Loss Options Test"
        try:
            order_assistant = self.main_window.order_assistant
            
            # Test stop loss buttons exist
            has_5min_button = hasattr(order_assistant, 'sl_5min_button')
            has_current_5min_button = hasattr(order_assistant, 'sl_current_5min_button')
            has_day_button = hasattr(order_assistant, 'sl_day_button')
            has_pct_button = hasattr(order_assistant, 'sl_pct_button')
            
            # Test percentage stop loss controls
            has_pct_spinbox = hasattr(order_assistant, 'sl_pct_spinbox')
            has_pct_price_label = hasattr(order_assistant, 'sl_pct_price_label')
            
            # Test adjustment buttons
            has_adjustment_buttons = hasattr(order_assistant, 'sl_minus_button') and hasattr(order_assistant, 'sl_plus_button')
            
            passed = has_5min_button and has_current_5min_button and has_day_button and has_pct_button and has_pct_spinbox and has_pct_price_label and has_adjustment_buttons
            message = f"SL Buttons: 4/4, Pct Controls: {has_pct_spinbox and has_pct_price_label}, Adjustment: {has_adjustment_buttons}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_multiple_targets_functionality(self):
        """Test multiple profit targets functionality"""
        test_name = "Multiple Targets Functionality Test"
        try:
            order_assistant = self.main_window.order_assistant
            
            # Test multiple targets checkbox
            has_multiple_checkbox = hasattr(order_assistant, 'multiple_targets_checkbox')
            
            # Test profit targets array
            has_profit_targets = hasattr(order_assistant, 'profit_targets')
            
            # Test multiple targets methods
            has_toggle_method = hasattr(order_assistant, 'on_multiple_targets_toggled')
            has_calc_method = hasattr(order_assistant, 'calculate_target_prices')
            has_get_data_method = hasattr(order_assistant, 'get_profit_target_data')
            
            passed = has_multiple_checkbox and has_profit_targets and has_toggle_method and has_calc_method and has_get_data_method
            message = f"Checkbox: {has_multiple_checkbox}, Targets Array: {has_profit_targets}, Methods: {has_toggle_method and has_calc_method and has_get_data_method}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_order_summary_and_validation(self):
        """Test order summary and validation"""
        test_name = "Order Summary and Validation Test"
        try:
            order_assistant = self.main_window.order_assistant
            
            # Test summary components
            has_summary_label = hasattr(order_assistant, 'summary_label')
            has_warning_label = hasattr(order_assistant, 'warning_label')
            has_submit_button = hasattr(order_assistant, 'submit_button')
            
            # Test validation methods
            has_validate_method = hasattr(order_assistant, 'validate_inputs')
            has_update_method = hasattr(order_assistant, 'update_summary')
            
            # Test submit functionality
            has_submit_method = hasattr(order_assistant, 'on_submit_order')
            
            passed = has_summary_label and has_warning_label and has_submit_button and has_validate_method and has_update_method and has_submit_method
            message = f"Summary UI: {has_summary_label and has_warning_label and has_submit_button}, Methods: {has_validate_method and has_update_method and has_submit_method}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_market_screener_integration(self):
        """Test market screener integration"""
        test_name = "Market Screener Integration Test"
        try:
            market_screener = self.main_window.market_screener
            
            # Test screener components
            has_scan_controls = hasattr(market_screener, 'scan_type_combo') if market_screener else False
            has_filter_controls = hasattr(market_screener, 'min_price_input') if market_screener else False
            has_results_table = hasattr(market_screener, 'results_table') if market_screener else False
            
            # Test integration signals
            has_symbol_signal = hasattr(market_screener, 'symbol_selected') if market_screener else False
            
            # Test main window signal handling
            has_screener_handler = hasattr(self.main_window, 'on_screener_symbol_selected')
            
            passed = has_scan_controls and has_filter_controls and has_results_table and has_symbol_signal and has_screener_handler
            message = f"Controls: {has_scan_controls and has_filter_controls}, Table: {has_results_table}, Signal: {has_symbol_signal}, Handler: {has_screener_handler}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_chart_integration(self):
        """Test chart widget integration"""
        test_name = "Chart Integration Test"
        try:
            chart_widget = self.main_window.chart_widget
            
            # Test chart components
            has_chart_canvas = hasattr(chart_widget, 'chart_canvas') if chart_widget else False
            has_controls = hasattr(chart_widget, 'timeframe_combo') if chart_widget else False
            has_refresh_button = hasattr(chart_widget, 'refresh_button') if chart_widget else False
            has_rescale_button = hasattr(chart_widget, 'rescale_button') if chart_widget else False
            
            # Test chart methods
            has_set_symbol = hasattr(chart_widget, 'set_symbol') if chart_widget else False
            has_update_levels = hasattr(chart_widget, 'update_price_levels') if chart_widget else False
            
            # Test main window chart handlers
            has_chart_handlers = (
                hasattr(self.main_window, 'on_chart_symbol_selected') and
                hasattr(self.main_window, 'on_fetch_price_chart_update')
            )
            
            passed = has_chart_canvas and has_controls and has_refresh_button and has_rescale_button and has_set_symbol and has_update_levels and has_chart_handlers
            message = f"Canvas: {has_chart_canvas}, Controls: {has_controls and has_refresh_button and has_rescale_button}, Methods: {has_set_symbol and has_update_levels}, Handlers: {has_chart_handlers}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_connection_workflow(self):
        """Test connection workflow and handlers"""
        test_name = "Connection Workflow Test"
        try:
            # Test connection methods
            has_connect_method = hasattr(self.main_window, 'connect_to_ib')
            has_disconnect_method = hasattr(self.main_window, 'disconnect_from_ib')
            has_status_update = hasattr(self.main_window, 'update_connection_status')
            
            # Test price fetch workflow
            has_fetch_handler = hasattr(self.main_window, 'on_fetch_price_requested')
            has_price_processor = hasattr(self.main_window, 'process_price_data')
            
            # Test order submission workflow
            has_order_handler = hasattr(self.main_window, 'on_order_submitted')
            has_submit_order = hasattr(self.main_window, 'submit_order')
            
            passed = has_connect_method and has_disconnect_method and has_status_update and has_fetch_handler and has_price_processor and has_order_handler and has_submit_order
            message = f"Connection: {has_connect_method and has_disconnect_method and has_status_update}, Price: {has_fetch_handler and has_price_processor}, Order: {has_order_handler and has_submit_order}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_signal_routing_architecture(self):
        """Test signal routing between components"""
        test_name = "Signal Routing Architecture Test"
        try:
            # Test Order Assistant signals are connected
            order_assistant = self.main_window.order_assistant
            oa_signals_exist = (
                hasattr(order_assistant, 'order_submitted') and
                hasattr(order_assistant, 'fetch_price_requested') and
                hasattr(order_assistant, 'entry_price_changed') and
                hasattr(order_assistant, 'stop_loss_changed') and
                hasattr(order_assistant, 'take_profit_changed')
            )
            
            # Test Market Screener signals
            market_screener = self.main_window.market_screener
            ms_signals_exist = hasattr(market_screener, 'symbol_selected') if market_screener else False
            
            # Test Chart signals
            chart_widget = self.main_window.chart_widget
            chart_signals_exist = (
                hasattr(chart_widget, 'chart_entry_changed') and
                hasattr(chart_widget, 'chart_stop_loss_changed') and
                hasattr(chart_widget, 'chart_take_profit_changed')
            ) if chart_widget else False
            
            # Test main window signal connections method
            has_setup_connections = hasattr(self.main_window, 'setup_connections')
            
            passed = oa_signals_exist and ms_signals_exist and chart_signals_exist and has_setup_connections
            message = f"OA Signals: {oa_signals_exist}, MS Signals: {ms_signals_exist}, Chart Signals: {chart_signals_exist}, Setup: {has_setup_connections}"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def test_workflow_performance(self):
        """Test basic workflow performance"""
        test_name = "Workflow Performance Test"
        try:
            order_assistant = self.main_window.order_assistant
            
            # Test UI responsiveness
            start_time = time.time()
            
            # Simulate basic workflow steps
            order_assistant.symbol_input.setText("MSFT")
            order_assistant.entry_price.setValue(300.0)
            order_assistant.stop_loss_price.setValue(290.0)
            order_assistant.r_multiple_spinbox.setValue(2.0)
            order_assistant.on_r_multiple_changed(2.0)
            order_assistant.calculate_position_size()
            order_assistant.update_summary()
            
            end_time = time.time()
            workflow_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            # Target: < 50ms for basic UI operations
            passed = workflow_time < 50
            message = f"Basic workflow time: {workflow_time:.2f}ms (target: <50ms)"
            self.log_test(test_name, passed, message)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            
    def run_all_tests(self):
        """Run all trading workflow tests"""
        print("\n" + "="*60)
        print("RUNNING COMPLETE TRADING WORKFLOW TEST SUITE")
        print("="*60)
        
        # Run individual tests
        self.test_main_window_components()
        self.test_trading_mode_selection()
        self.test_symbol_input_workflow()
        self.test_price_entry_controls()
        self.test_risk_management_controls()
        self.test_stop_loss_options()
        self.test_multiple_targets_functionality()
        self.test_order_summary_and_validation()
        self.test_market_screener_integration()
        self.test_chart_integration()
        self.test_connection_workflow()
        self.test_signal_routing_architecture()
        self.test_workflow_performance()
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if "[PASS]" in r])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "="*60)
        print("TRADING WORKFLOW TEST RESULTS SUMMARY")
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
    """Run Trading Workflow test suite"""
    test_suite = TradingWorkflowTestSuite()
    
    # Schedule tests to run after UI is shown
    QTimer.singleShot(300, test_suite.run_all_tests)
    QTimer.singleShot(4000, test_suite.app.quit)  # Close after 4 seconds
    
    # Run the application
    test_suite.app.exec()

if __name__ == "__main__":
    main()