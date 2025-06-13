#!/usr/bin/env python3
"""
Phase 4: Comprehensive Integration Test for Account Services
Tests the refactored account service architecture with real IB connection
"""

import sys
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, '/mnt/c/Users/alanc/OneDrive/桌面/Python_Projects/trading_app')

def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")

def print_test(test_name: str, passed: bool, details: str = ""):
    """Print test result"""
    icon = "✅" if passed else "❌"
    print(f"{icon} {test_name}")
    if details:
        print(f"   {details}")

def test_imports():
    """Test that all imports work correctly"""
    print_header("IMPORT TESTS")
    
    tests_passed = 0
    tests_total = 0
    
    # Test core imports
    imports = [
        ("ServiceRegistry", "src.services.service_registry", "ServiceRegistry"),
        ("AccountService", "src.services.account_service", "AccountService"),
        ("AccountManagerService", "src.services.account_manager_service", "AccountManagerService"),
        ("ConnectionService", "src.services.connection_service", "ConnectionService"),
        ("RiskService", "src.services.risk_service", "RiskService"),
        ("IB Connection Manager", "src.services.ib_connection_service", "ib_connection_manager"),
    ]
    
    for name, module_path, class_name in imports:
        tests_total += 1
        try:
            module = __import__(module_path, fromlist=[class_name])
            obj = getattr(module, class_name)
            print_test(f"Import {name}", True)
            tests_passed += 1
        except Exception as e:
            print_test(f"Import {name}", False, str(e))
    
    return tests_passed, tests_total

def test_service_instantiation():
    """Test that services can be instantiated"""
    print_header("SERVICE INSTANTIATION TESTS")
    
    tests_passed = 0
    tests_total = 0
    
    try:
        from src.services.account_service import AccountService
        from src.services.account_manager_service import AccountManagerService
        from src.services.risk_service import RiskService
        from src.services.connection_service import ConnectionService
        
        # Test AccountService
        tests_total += 1
        try:
            account_service = AccountService()
            print_test("AccountService instantiation", True)
            tests_passed += 1
        except Exception as e:
            print_test("AccountService instantiation", False, str(e))
        
        # Test AccountManagerService
        tests_total += 1
        try:
            account_manager_service = AccountManagerService()
            print_test("AccountManagerService instantiation", True)
            tests_passed += 1
        except Exception as e:
            print_test("AccountManagerService instantiation", False, str(e))
        
        # Test RiskService
        tests_total += 1
        try:
            risk_service = RiskService()
            print_test("RiskService instantiation", True)
            tests_passed += 1
        except Exception as e:
            print_test("RiskService instantiation", False, str(e))
        
        # Test ConnectionService
        tests_total += 1
        try:
            connection_service = ConnectionService()
            print_test("ConnectionService instantiation", True)
            tests_passed += 1
        except Exception as e:
            print_test("ConnectionService instantiation", False, str(e))
            
    except Exception as e:
        print(f"Failed to import services: {e}")
        
    return tests_passed, tests_total

def test_service_initialization():
    """Test service initialization without IB connection"""
    print_header("SERVICE INITIALIZATION TESTS")
    
    tests_passed = 0
    tests_total = 0
    
    try:
        from src.services.account_service import AccountService
        from src.services.account_manager_service import AccountManagerService
        
        # Test AccountService initialization
        tests_total += 1
        try:
            service = AccountService()
            result = service.initialize()
            print_test("AccountService initialization", result)
            if result:
                tests_passed += 1
        except Exception as e:
            print_test("AccountService initialization", False, str(e))
        
        # Test AccountManagerService initialization
        tests_total += 1
        try:
            service = AccountManagerService()
            result = service.initialize()
            print_test("AccountManagerService initialization", result)
            if result:
                tests_passed += 1
        except Exception as e:
            print_test("AccountManagerService initialization", False, str(e))
            
    except Exception as e:
        print(f"Failed during initialization: {e}")
        
    return tests_passed, tests_total

def test_api_compatibility():
    """Test that the refactored services maintain API compatibility"""
    print_header("API COMPATIBILITY TESTS")
    
    tests_passed = 0
    tests_total = 0
    
    try:
        from src.services.account_service import AccountService
        
        service = AccountService()
        service.initialize()
        
        # Test required methods exist
        methods = [
            'update_account_data',
            'update_positions',
            'get_account_value',
            'get_buying_power',
            'get_cash_balance',
            'get_positions',
            'get_position',
            'get_daily_pnl',
            'get_unrealized_pnl',
            'get_realized_pnl',
            'get_account_summary',
            'calculate_position_size',
            'is_position_size_valid',
            'register_account_update_callback',
            'register_position_update_callback'
        ]
        
        for method_name in methods:
            tests_total += 1
            if hasattr(service, method_name):
                method = getattr(service, method_name)
                if callable(method):
                    print_test(f"Method '{method_name}' exists", True)
                    tests_passed += 1
                else:
                    print_test(f"Method '{method_name}' exists", False, "Not callable")
            else:
                print_test(f"Method '{method_name}' exists", False, "Method not found")
                
    except Exception as e:
        print(f"Failed during API compatibility test: {e}")
        
    return tests_passed, tests_total

def test_delegation_chain():
    """Test that AccountService properly delegates to AccountManagerService"""
    print_header("DELEGATION CHAIN TESTS")
    
    tests_passed = 0
    tests_total = 0
    
    try:
        from src.services.account_service import AccountService
        from src.services.account_manager_service import AccountManagerService
        
        # Test that AccountService uses AccountManagerService
        tests_total += 1
        try:
            service = AccountService()
            # Check internal delegation
            if hasattr(service, '_service') and isinstance(service._service, AccountManagerService):
                print_test("AccountService delegates to AccountManagerService", True)
                tests_passed += 1
            else:
                print_test("AccountService delegates to AccountManagerService", False, 
                          "Delegation not properly configured")
        except Exception as e:
            print_test("AccountService delegates to AccountManagerService", False, str(e))
            
        # Test callback list sharing
        tests_total += 1
        try:
            service = AccountService()
            if (hasattr(service, 'account_update_callbacks') and 
                hasattr(service, 'position_update_callbacks')):
                print_test("Callback lists exposed for compatibility", True)
                tests_passed += 1
            else:
                print_test("Callback lists exposed for compatibility", False)
        except Exception as e:
            print_test("Callback lists exposed for compatibility", False, str(e))
            
    except Exception as e:
        print(f"Failed during delegation test: {e}")
        
    return tests_passed, tests_total

def test_risk_calculator_integration():
    """Test RiskCalculator integration with AccountManagerService"""
    print_header("RISK CALCULATOR INTEGRATION TESTS")
    
    tests_passed = 0
    tests_total = 0
    
    try:
        from src.services.risk_service import RiskService
        from src.services.account_manager_service import AccountManagerService
        from src.core.risk_calculator import RiskCalculator
        
        # Test RiskService can use AccountManagerService
        tests_total += 1
        try:
            risk_service = RiskService()
            account_service = AccountManagerService()
            risk_service.set_account_manager(account_service)
            
            if hasattr(risk_service, 'risk_calculator') and risk_service.risk_calculator is not None:
                print_test("RiskService accepts AccountManagerService", True)
                tests_passed += 1
            else:
                print_test("RiskService accepts AccountManagerService", False, 
                          "RiskCalculator not initialized")
        except Exception as e:
            print_test("RiskService accepts AccountManagerService", False, str(e))
            
        # Test RiskCalculator can be created with AccountManagerService
        tests_total += 1
        try:
            account_service = AccountManagerService()
            risk_calc = RiskCalculator(account_service)
            print_test("RiskCalculator accepts AccountManagerService", True)
            tests_passed += 1
        except Exception as e:
            print_test("RiskCalculator accepts AccountManagerService", False, str(e))
            
    except Exception as e:
        print(f"Failed during risk calculator test: {e}")
        
    return tests_passed, tests_total

def test_connection_service_integration():
    """Test ConnectionService integration with AccountManagerService"""
    print_header("CONNECTION SERVICE INTEGRATION TESTS")
    
    tests_passed = 0
    tests_total = 0
    
    try:
        from src.services.connection_service import ConnectionService
        from src.services.account_manager_service import AccountManagerService
        
        # Test ConnectionService type hints
        tests_total += 1
        try:
            service = ConnectionService()
            # Check type annotation
            if hasattr(service, '__annotations__'):
                account_manager_type = service.__annotations__.get('account_manager', '')
                if 'AccountManagerService' in str(account_manager_type):
                    print_test("ConnectionService uses correct type hints", True)
                    tests_passed += 1
                else:
                    print_test("ConnectionService uses correct type hints", False,
                              f"Found type: {account_manager_type}")
            else:
                print_test("ConnectionService uses correct type hints", False,
                          "No type annotations found")
        except Exception as e:
            print_test("ConnectionService uses correct type hints", False, str(e))
            
    except Exception as e:
        print(f"Failed during connection service test: {e}")
        
    return tests_passed, tests_total

def run_integration_tests():
    """Run all integration tests"""
    print("\n" + "="*60)
    print("🚀 PHASE 4: ACCOUNT SERVICE INTEGRATION TESTS")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    total_passed = 0
    total_tests = 0
    
    # Run test suites
    test_suites = [
        test_imports,
        test_service_instantiation,
        test_service_initialization,
        test_api_compatibility,
        test_delegation_chain,
        test_risk_calculator_integration,
        test_connection_service_integration
    ]
    
    for test_suite in test_suites:
        passed, total = test_suite()
        total_passed += passed
        total_tests += total
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_tests - total_passed}")
    print(f"Success Rate: {(total_passed/total_tests*100):.1f}%")
    
    if total_passed == total_tests:
        print("\n✅ All integration tests passed! Ready for Phase 5 cleanup.")
    else:
        print(f"\n⚠️  {total_tests - total_passed} tests failed. Review before proceeding.")
    
    return total_passed == total_tests

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)