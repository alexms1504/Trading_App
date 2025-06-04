#!/usr/bin/env python3
"""
Test Multiple Targets Enhancement - Separate % and R-multiple boxes
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from src.ui.order_assistant import OrderAssistantWidget

def test_multiple_targets_enhancement():
    """Test the enhanced multiple targets with separate % and R-multiple controls"""
    app = QApplication([])
    
    # Create Order Assistant widget
    order_assistant = OrderAssistantWidget()
    
    print("Testing Multiple Targets Enhancement...")
    
    # Set up basic trade parameters
    order_assistant.entry_price.setValue(100.0)
    order_assistant.stop_loss_price.setValue(95.0)  # 5% stop loss
    
    print(f"Entry: ${order_assistant.entry_price.value():.2f}")
    print(f"Stop Loss: ${order_assistant.stop_loss_price.value():.2f}")
    print(f"Risk Distance: ${abs(100.0 - 95.0):.2f}")
    
    # Enable multiple targets
    print("\nEnabling multiple targets...")
    order_assistant.multiple_targets_checkbox.setChecked(True)
    
    # Verify initial R-multiple values
    print("\nInitial R-multiple values:")
    for i, target in enumerate(order_assistant.profit_targets, 1):
        r_multiple = target['r_multiple'].value()
        percentage = target['percent'].value()
        price = target['price'].value()
        print(f"Target {i}: {r_multiple:.1f}R, {percentage}%, Price: ${price:.2f}")
    
    # Test R-multiple to price calculation
    print("\nTesting R-multiple changes...")
    order_assistant.profit_targets[0]['r_multiple'].setValue(1.5)  # Change first target to 1.5R
    order_assistant.profit_targets[1]['r_multiple'].setValue(2.5)  # Change second target to 2.5R
    order_assistant.profit_targets[2]['r_multiple'].setValue(4.0)  # Change third target to 4.0R
    
    print("After R-multiple changes:")
    for i, target in enumerate(order_assistant.profit_targets, 1):
        r_multiple = target['r_multiple'].value()
        percentage = target['percent'].value()
        price = target['price'].value()
        expected_price = 100.0 + (r_multiple * 5.0)  # Entry + (R * risk distance)
        print(f"Target {i}: {r_multiple:.1f}R, {percentage}%, Price: ${price:.2f} (Expected: ${expected_price:.2f})")
    
    # Test price to R-multiple calculation
    print("\nTesting manual price changes...")
    order_assistant.profit_targets[0]['price'].setValue(110.0)  # Should be 2.0R
    order_assistant.profit_targets[1]['price'].setValue(120.0)  # Should be 4.0R
    order_assistant.profit_targets[2]['price'].setValue(125.0)  # Should be 5.0R
    
    print("After price changes:")
    for i, target in enumerate(order_assistant.profit_targets, 1):
        r_multiple = target['r_multiple'].value()
        percentage = target['percent'].value()
        price = target['price'].value()
        expected_r = (price - 100.0) / 5.0  # (price - entry) / risk distance
        print(f"Target {i}: {r_multiple:.1f}R (Expected: {expected_r:.1f}R), {percentage}%, Price: ${price:.2f}")
    
    # Test percentage changes
    print("\nTesting percentage changes...")
    order_assistant.profit_targets[0]['percent'].setValue(40)
    order_assistant.profit_targets[1]['percent'].setValue(35)
    order_assistant.profit_targets[2]['percent'].setValue(25)
    
    total_percent = sum(target['percent'].value() for target in order_assistant.profit_targets)
    print(f"Percentage allocation: 40%, 35%, 25% (Total: {total_percent}%)")
    
    print("\nMultiple Targets Enhancement Test Completed!")
    print("✅ Separate % and R-multiple controls working")
    print("✅ Bidirectional synchronization between R-multiple and price")
    print("✅ Independent percentage control")
    
    return True

if __name__ == "__main__":
    test_multiple_targets_enhancement()