#!/bin/bash

# Account Service Refactoring Safety Check Script
# Run this before and after each refactoring phase

echo "🛡️ ACCOUNT SERVICE SAFETY CHECK"
echo "==============================="
echo "Timestamp: $(date)"
echo ""

# Function to check Python syntax
check_syntax() {
    echo "1. Checking Python syntax..."
    python3 -m py_compile src/services/account_service.py 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "   ✅ account_service.py syntax OK"
    else
        echo "   ❌ account_service.py has syntax errors"
        return 1
    fi
    
    python3 -m py_compile src/services/account_manager_service.py 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "   ✅ account_manager_service.py syntax OK"
    else
        echo "   ❌ account_manager_service.py has syntax errors"
        return 1
    fi
    echo ""
}

# Function to check imports
check_imports() {
    echo "2. Checking critical imports..."
    
    # Test that services can be imported
    python3 -c "
try:
    from src.services.account_service import AccountService
    print('   ✅ AccountService imports successfully')
except Exception as e:
    print(f'   ❌ AccountService import failed: {e}')
    exit(1)

try:
    from src.services.account_manager_service import AccountManagerService
    print('   ✅ AccountManagerService imports successfully')
except Exception as e:
    print(f'   ❌ AccountManagerService import failed: {e}')
    exit(1)
"
    echo ""
}

# Function to check service instantiation
check_instantiation() {
    echo "3. Checking service instantiation..."
    
    python3 -c "
try:
    from src.services.account_service import AccountService
    service = AccountService()
    print('   ✅ AccountService instantiates successfully')
except Exception as e:
    print(f'   ❌ AccountService instantiation failed: {e}')
"
    echo ""
}

# Function to count lines of code
count_lines() {
    echo "4. Code metrics..."
    
    lines1=$(wc -l < src/services/account_service.py)
    lines2=$(wc -l < src/services/account_manager_service.py 2>/dev/null || echo "0")
    total=$((lines1 + lines2))
    
    echo "   📊 account_service.py: $lines1 lines"
    echo "   📊 account_manager_service.py: $lines2 lines"
    echo "   📊 Total: $total lines"
    echo ""
}

# Function to check for common issues
check_common_issues() {
    echo "5. Checking for common refactoring issues..."
    
    # Check for duplicate class definitions
    duplicates=$(grep -h "^class Account" src/services/account*.py | sort | uniq -d)
    if [ -z "$duplicates" ]; then
        echo "   ✅ No duplicate class definitions"
    else
        echo "   ❌ Duplicate class definitions found: $duplicates"
    fi
    
    # Check for missing methods
    if grep -q "positions" src/services/account_service.py; then
        echo "   ✅ 'positions' property/method found"
    else
        echo "   ⚠️  'positions' property/method not found"
    fi
    
    echo ""
}

# Run all checks
echo "Running safety checks..."
echo ""

check_syntax || exit 1
check_imports || exit 1
check_instantiation
count_lines
check_common_issues

echo "==============================="
echo "✅ Safety check complete"
echo ""
echo "Next steps:"
echo "1. Run test_account_services.py for detailed testing"
echo "2. Make refactoring changes"
echo "3. Run this script again to verify"