#!/usr/bin/env python3
"""
Account Services Integration Test
Pre-refactoring baseline test to ensure we don't break functionality

This script tests all critical account service operations to establish
a baseline before service consolidation.
"""

import sys
import traceback
from datetime import datetime

def test_account_service_operations():
    """Test all critical account service operations"""
    
    print("🧪 ACCOUNT SERVICES INTEGRATION TEST")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    test_results = []
    
    # Test 1: Service Imports
    print("1. Testing service imports...")
    try:
        from src.services.account_service import AccountService
        from src.services.account_manager_service import AccountManagerService, AccountManager
        from src.services.service_registry import ServiceRegistry
        test_results.append(("Service imports", True, "All account services imported"))
        print("   ✅ All account services imported successfully")
    except Exception as e:
        test_results.append(("Service imports", False, str(e)))
        print(f"   ❌ Import failed: {e}")
        return test_results
    
    # Test 2: Service Instantiation
    print("\n2. Testing service instantiation...")
    try:
        # Direct instantiation
        account_service = AccountService()
        account_manager_service = AccountManagerService()
        account_manager = AccountManager()
        
        test_results.append(("Service instantiation", True, "All services created"))
        print("   ✅ All services instantiated successfully")
    except Exception as e:
        test_results.append(("Service instantiation", False, str(e)))
        print(f"   ❌ Instantiation failed: {e}")
    
    # Test 3: Service Registry Pattern
    print("\n3. Testing service registry patterns...")
    try:
        # Test registry access
        registry = ServiceRegistry()
        
        # Check if we can register services
        if hasattr(registry, 'register_service'):
            print("   ✅ Service registry has register_service method")
            test_results.append(("Registry pattern", True, "Registry accessible"))
        else:
            print("   ⚠️  Service registry missing register_service")
            test_results.append(("Registry pattern", False, "Missing method"))
            
    except Exception as e:
        test_results.append(("Registry pattern", False, str(e)))
        print(f"   ❌ Registry test failed: {e}")
    
    # Test 4: API Surface Check
    print("\n4. Testing API surface (methods and properties)...")
    api_tests = []
    
    # Expected AccountService methods
    expected_methods = [
        'initialize', 'cleanup', 'get_state', 'wait_for_ready',
        'update_account', 'get_account_value', 'get_positions',
        'get_buying_power', 'calculate_available_capital'
    ]
    
    # Check AccountService API
    for method in expected_methods:
        if hasattr(account_service, method):
            api_tests.append((f"AccountService.{method}", True))
        else:
            api_tests.append((f"AccountService.{method}", False))
            print(f"   ⚠️  Missing: AccountService.{method}")
    
    # Check for properties
    if hasattr(account_service, 'positions') or hasattr(account_service, 'get_positions'):
        api_tests.append(("positions access", True))
    else:
        api_tests.append(("positions access", False))
        print("   ⚠️  No positions property or get_positions method")
    
    # Report API test results
    passed = sum(1 for _, result in api_tests if result)
    total = len(api_tests)
    
    if passed == total:
        print(f"   ✅ All {total} API methods/properties found")
        test_results.append(("API surface", True, f"{passed}/{total} methods"))
    else:
        print(f"   ⚠️  Found {passed}/{total} expected methods")
        test_results.append(("API surface", False, f"{passed}/{total} methods"))
    
    # Test 5: Service State Management
    print("\n5. Testing service state management...")
    try:
        # Check initial state
        state = account_service.get_state() if hasattr(account_service, 'get_state') else None
        
        if state:
            print(f"   ✅ Service state: {state}")
            test_results.append(("State management", True, f"State: {state}"))
        else:
            print("   ⚠️  No state management found")
            test_results.append(("State management", False, "No state"))
            
    except Exception as e:
        test_results.append(("State management", False, str(e)))
        print(f"   ❌ State test failed: {e}")
    
    # Test 6: Event/Callback Pattern Check
    print("\n6. Testing event/callback patterns...")
    try:
        # Check for callbacks
        has_callbacks = hasattr(account_service, 'on_account_update') or \
                       hasattr(account_service, '_callbacks') or \
                       hasattr(account_service, 'subscribe')
        
        # Check for event bus integration
        has_events = 'event' in str(type(account_service).__dict__).lower()
        
        if has_callbacks or has_events:
            print(f"   ✅ Event patterns found (callbacks: {has_callbacks}, events: {has_events})")
            test_results.append(("Event patterns", True, "Found"))
        else:
            print("   ⚠️  No clear event/callback patterns")
            test_results.append(("Event patterns", False, "Not found"))
            
    except Exception as e:
        test_results.append(("Event patterns", False, str(e)))
        print(f"   ❌ Event test failed: {e}")
    
    # Test 7: Service Dependencies
    print("\n7. Checking service dependencies...")
    try:
        # Check what services AccountService depends on
        dependencies = []
        
        # Look for IB connection dependency
        if hasattr(account_service, 'ib') or hasattr(account_service, '_ib_connection'):
            dependencies.append("IB Connection")
        
        # Look for event bus dependency
        if hasattr(account_service, '_event_bus') or hasattr(account_service, 'event_bus'):
            dependencies.append("Event Bus")
            
        print(f"   ✅ Dependencies found: {dependencies if dependencies else 'None (self-contained)'}")
        test_results.append(("Dependencies", True, str(dependencies)))
        
    except Exception as e:
        test_results.append(("Dependencies", False, str(e)))
        print(f"   ❌ Dependency check failed: {e}")
    
    # Summary Report
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed_tests = sum(1 for _, result, _ in test_results if result)
    total_tests = len(test_results)
    
    for test_name, result, details in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {test_name:<25} | {details}")
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    # Save baseline results
    baseline_file = "account_service_baseline.txt"
    with open(baseline_file, 'w') as f:
        f.write(f"Account Service Baseline Test Results\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write(f"=" * 50 + "\n\n")
        
        for test_name, result, details in test_results:
            f.write(f"{test_name}: {'PASS' if result else 'FAIL'} - {details}\n")
        
        f.write(f"\nTotal: {passed_tests}/{total_tests} tests passed\n")
    
    print(f"\n💾 Baseline saved to: {baseline_file}")
    
    return test_results


def check_import_dependencies():
    """Check which files import account services"""
    
    print("\n\n🔍 IMPORT DEPENDENCY ANALYSIS")
    print("=" * 50)
    
    import os
    import re
    
    account_imports = {
        'account_service': [],
        'account_manager_service': [],
        'AccountManager': []
    }
    
    # Search for imports in src directory
    for root, dirs, files in os.walk('src'):
        # Skip __pycache__
        if '__pycache__' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                        
                    # Check for account_service imports
                    if re.search(r'from.*account_service import|import.*account_service', content):
                        account_imports['account_service'].append(filepath)
                    
                    # Check for account_manager_service imports
                    if re.search(r'from.*account_manager_service import|import.*account_manager_service', content):
                        account_imports['account_manager_service'].append(filepath)
                    
                    # Check for AccountManager class imports
                    if 'AccountManager' in content and 'class AccountManager' not in content:
                        account_imports['AccountManager'].append(filepath)
                        
                except Exception as e:
                    pass
    
    # Report findings
    for import_type, files in account_imports.items():
        print(f"\n{import_type} imported by {len(files)} files:")
        for file in files:
            print(f"   - {file}")
    
    return account_imports


if __name__ == '__main__':
    print("🚀 Running Account Services Pre-Refactoring Tests\n")
    
    # Run main tests
    test_results = test_account_service_operations()
    
    # Run import analysis
    import_deps = check_import_dependencies()
    
    print("\n✅ Pre-refactoring baseline complete!")
    print("Use this test after each phase to ensure functionality preserved.")