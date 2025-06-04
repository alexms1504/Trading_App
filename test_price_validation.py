#!/usr/bin/env python3
"""
Test price validation fixes
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from src.ui.order_assistant import OrderAssistantWidget

def test_price_validation():
    """Test that extreme price values are properly handled"""
    app = QApplication([])
    
    # Create Order Assistant widget
    order_assistant = OrderAssistantWidget()
    
    print("Testing price validation...")
    
    # Test 1: Normal values should work
    print("Test 1: Normal values")
    order_assistant.entry_price.setValue(100.0)
    order_assistant.stop_loss_price.setValue(95.0)
    order_assistant.take_profit_price.setValue(110.0)
    
    print(f"Entry: ${order_assistant.entry_price.value():.2f}")
    print(f"Stop Loss: ${order_assistant.stop_loss_price.value():.2f}")
    print(f"Take Profit: ${order_assistant.take_profit_price.value():.2f}")
    
    # Test 2: Try to set extreme values (should be blocked)
    print("\nTest 2: Extreme values (should be blocked)")
    try:
        order_assistant.entry_price.setValue(10000.0)  # Should be clamped to 5000
        print(f"Entry after setting to 10000: ${order_assistant.entry_price.value():.2f}")
    except Exception as e:
        print(f"Entry price validation error: {e}")
    
    try:
        order_assistant.stop_loss_price.setValue(10000.0)  # Should be clamped to 5000
        print(f"Stop Loss after setting to 10000: ${order_assistant.stop_loss_price.value():.2f}")
    except Exception as e:
        print(f"Stop loss validation error: {e}")
    
    try:
        order_assistant.take_profit_price.setValue(10000.0)  # Should be clamped to 5000
        print(f"Take Profit after setting to 10000: ${order_assistant.take_profit_price.value():.2f}")
    except Exception as e:
        print(f"Take profit validation error: {e}")
    
    # Test 3: Test auto adjustment with extreme values
    print("\nTest 3: Auto adjustment with extreme entry price")
    order_assistant.entry_price.setValue(4999.0)  # Close to max
    order_assistant.stop_loss_price.setValue(0.01)  # Min value
    order_assistant.r_multiple_spinbox.setValue(2.0)
    
    # This should be caught by validation
    order_assistant.auto_adjust_take_profit()
    
    print(f"Final Entry: ${order_assistant.entry_price.value():.2f}")
    print(f"Final Stop Loss: ${order_assistant.stop_loss_price.value():.2f}")
    print(f"Final Take Profit: ${order_assistant.take_profit_price.value():.2f}")
    
    print("\nValidation tests completed!")

if __name__ == "__main__":
    test_price_validation()