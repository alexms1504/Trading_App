#!/usr/bin/env python3
"""
Phase 4: Syntax and Structure Validation Tests
Tests syntax, imports, and basic structure without requiring IB dependencies
"""

import sys
import os
import ast
import subprocess
from pathlib import Path

def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

def print_test(test_name: str, passed: bool, details: str = ""):
    """Print test result"""
    icon = "✅" if passed else "❌"
    print(f"{icon} {test_name}")
    if details:
        print(f"   {details}")

def test_python_syntax():
    """Test Python syntax of all modified files"""
    print_header("PYTHON SYNTAX VALIDATION")
    
    files_to_check = [
        "src/services/account_service.py",
        "src/services/account_manager_service.py", 
        "src/services/risk_service.py",
        "src/services/connection_service.py",
        "src/features/connection/connection_manager.py"
    ]
    
    passed = 0
    total = len(files_to_check)
    
    for file_path in files_to_check:
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                print_test(f"Syntax check: {file_path}", False, "File not found")
                continue
                
            # Check syntax using python compile
            result = subprocess.run([
                'python3', '-m', 'py_compile', file_path
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print_test(f"Syntax check: {file_path}", True)
                passed += 1
            else:
                print_test(f"Syntax check: {file_path}", False, result.stderr.strip())
                
        except Exception as e:
            print_test(f"Syntax check: {file_path}", False, str(e))
    
    return passed, total

def test_ast_parsing():
    """Test AST parsing to validate Python structure"""
    print_header("AST STRUCTURE VALIDATION")
    
    files_to_check = [
        "src/services/account_service.py",
        "src/services/account_manager_service.py"
    ]
    
    passed = 0
    total = len(files_to_check)
    
    for file_path in files_to_check:
        try:
            with open(file_path, 'r') as f:
                source = f.read()
            
            # Parse AST
            tree = ast.parse(source, filename=file_path)
            print_test(f"AST parsing: {file_path}", True)
            passed += 1
            
        except SyntaxError as e:
            print_test(f"AST parsing: {file_path}", False, f"Syntax error: {e}")
        except Exception as e:
            print_test(f"AST parsing: {file_path}", False, str(e))
    
    return passed, total

def test_import_structure():
    """Test import structure and dependencies"""
    print_header("IMPORT STRUCTURE ANALYSIS")
    
    passed = 0
    total = 0
    
    # Test AccountService structure
    total += 1
    try:
        with open("src/services/account_service.py", 'r') as f:
            content = f.read()
        
        # Check for correct imports
        if "from src.services.account_manager_service import AccountManagerService" in content:
            print_test("AccountService imports AccountManagerService", True)
            passed += 1
        else:
            print_test("AccountService imports AccountManagerService", False,
                      "Import not found")
    except Exception as e:
        print_test("AccountService imports AccountManagerService", False, str(e))
    
    # Test RiskService structure
    total += 1
    try:
        with open("src/services/risk_service.py", 'r') as f:
            content = f.read()
        
        if "from src.services.account_manager_service import AccountManagerService" in content:
            print_test("RiskService imports AccountManagerService", True)
            passed += 1
        else:
            print_test("RiskService imports AccountManagerService", False,
                      "Import not found")
    except Exception as e:
        print_test("RiskService imports AccountManagerService", False, str(e))
    
    # Test ConnectionService structure  
    total += 1
    try:
        with open("src/services/connection_service.py", 'r') as f:
            content = f.read()
        
        if "from src.services.account_manager_service import AccountManagerService" in content:
            print_test("ConnectionService imports AccountManagerService", True)
            passed += 1
        else:
            print_test("ConnectionService imports AccountManagerService", False,
                      "Import not found")
    except Exception as e:
        print_test("ConnectionService imports AccountManagerService", False, str(e))
    
    return passed, total

def test_class_structure():
    """Test class structure and method presence"""
    print_header("CLASS STRUCTURE VALIDATION")
    
    passed = 0
    total = 0
    
    # Test AccountService class structure
    total += 1
    try:
        with open("src/services/account_service.py", 'r') as f:
            source = f.read()
        
        tree = ast.parse(source)
        
        # Find AccountService class
        account_service_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "AccountService":
                account_service_class = node
                break
        
        if account_service_class:
            # Check for required methods
            method_names = [method.name for method in account_service_class.body 
                          if isinstance(method, ast.FunctionDef)]
            
            required_methods = [
                '__init__', 'initialize', 'cleanup', 'get_account_value',
                'get_buying_power', 'update_account_data', 'get_positions'
            ]
            
            missing_methods = [m for m in required_methods if m not in method_names]
            
            if not missing_methods:
                print_test("AccountService has required methods", True)
                passed += 1
            else:
                print_test("AccountService has required methods", False,
                          f"Missing: {missing_methods}")
        else:
            print_test("AccountService has required methods", False,
                      "AccountService class not found")
            
    except Exception as e:
        print_test("AccountService has required methods", False, str(e))
    
    return passed, total

def test_delegation_pattern():
    """Test that AccountService uses delegation pattern"""
    print_header("DELEGATION PATTERN VALIDATION")
    
    passed = 0
    total = 0
    
    total += 1
    try:
        with open("src/services/account_service.py", 'r') as f:
            content = f.read()
        
        # Check for delegation pattern
        checks = [
            "self._service = AccountManagerService()",
            "return self._service.",
            "self._service.initialize()",
            "self._service.cleanup()"
        ]
        
        delegation_found = all(check in content for check in checks)
        
        if delegation_found:
            print_test("AccountService uses delegation pattern", True)
            passed += 1
        else:
            missing = [check for check in checks if check not in content]
            print_test("AccountService uses delegation pattern", False,
                      f"Missing patterns: {missing}")
            
    except Exception as e:
        print_test("AccountService uses delegation pattern", False, str(e))
    
    return passed, total

def test_code_metrics():
    """Test code metrics and improvements"""
    print_header("CODE METRICS ANALYSIS")
    
    passed = 0
    total = 0
    
    # Check AccountService line count
    total += 1
    try:
        with open("src/services/account_service.py", 'r') as f:
            lines = len(f.readlines())
        
        # Should be around 220 lines (much less than original 336)
        if lines < 250:
            print_test(f"AccountService reduced size ({lines} lines)", True)
            passed += 1
        else:
            print_test(f"AccountService reduced size ({lines} lines)", False,
                      "Still quite large")
            
    except Exception as e:
        print_test("AccountService reduced size", False, str(e))
    
    return passed, total

def run_validation_tests():
    """Run all validation tests"""
    print("\n" + "="*60)
    print("🔍 PHASE 4: SYNTAX & STRUCTURE VALIDATION")
    print("="*60)
    
    total_passed = 0
    total_tests = 0
    
    # Run test suites
    test_suites = [
        test_python_syntax,
        test_ast_parsing,
        test_import_structure,
        test_class_structure,
        test_delegation_pattern,
        test_code_metrics
    ]
    
    for test_suite in test_suites:
        passed, total = test_suite()
        total_passed += passed
        total_tests += total
    
    # Summary
    print("\n" + "="*60)
    print("📊 VALIDATION SUMMARY")
    print("="*60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_tests - total_passed}")
    print(f"Success Rate: {(total_passed/total_tests*100):.1f}%")
    
    if total_passed == total_tests:
        print("\n✅ All validation tests passed!")
        print("✅ Code structure is correct and ready for Phase 5")
    else:
        print(f"\n⚠️  {total_tests - total_passed} tests failed.")
    
    return total_passed == total_tests

if __name__ == "__main__":
    success = run_validation_tests()
    sys.exit(0 if success else 1)