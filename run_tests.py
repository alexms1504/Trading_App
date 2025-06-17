#!/usr/bin/env python
"""
Test runner for the trading application.
Provides convenient test execution with various options.
"""

import sys
import os
import subprocess
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def run_tests(test_type="all", extra_args=None):
    """
    Run test suite with proper configuration.
    
    Args:
        test_type: Type of tests to run (all, critical, unit, integration, performance, stress)
        extra_args: Additional pytest arguments
    """
    # Set up test environment
    os.environ['TESTING'] = 'true'
    os.environ['PYTHONPATH'] = str(PROJECT_ROOT)
    
    # Base pytest command
    python_exe = sys.executable
    cmd = [python_exe, "-m", "pytest"]
    
    # Configure pytest args
    base_args = [
        '-v',                    # verbose
        '--tb=short',           # short traceback format
        '--strict-markers',     # strict marker usage
        '-p', 'no:warnings',    # disable warnings
    ]
    
    # Add test type specific args
    if test_type == "critical":
        base_args.extend(['tests/critical/', '-m', 'critical'])
        print("Running CRITICAL financial safety tests...")
    elif test_type == "unit":
        base_args.extend(['tests/unit/', '-m', 'not integration'])
        print("Running unit tests...")
    elif test_type == "integration":
        base_args.extend(['tests/integration/', '-m', 'integration'])
        print("Running integration tests...")
    elif test_type == "performance":
        base_args.extend(['tests/performance/', '-m', 'performance', '--benchmark-only'])
        print("Running performance benchmarks...")
    elif test_type == "stress":
        base_args.extend(['tests/stress/', '-m', 'stress', '-n', 'auto'])
        print("Running stress tests...")
    elif test_type == "coverage":
        base_args.extend([
            '--cov=src',
            '--cov-report=html',
            '--cov-report=term-missing',
            '--cov-fail-under=80'  # Fail if coverage < 80% for critical paths
        ])
        print("Running tests with coverage...")
    elif test_type == "quick":
        base_args.extend(['-x', '--ff'])  # Stop on first failure, run failed first
        print("Running quick test suite...")
    else:
        print("Running all tests...")
    
    # Add extra arguments if provided
    if extra_args:
        base_args.extend(extra_args)
    
    # Combine command and arguments
    cmd.extend(base_args)
    
    # Print command for debugging
    print(f"Command: {' '.join(cmd)}")
    print("-" * 80)
    
    # Run tests
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

def print_usage():
    """Print usage information."""
    print("""
Trading App Test Runner

Usage: python run_tests.py [test_type] [extra_args]

Test Types:
  all         - Run all tests (default)
  critical    - Run critical financial safety tests only
  unit        - Run unit tests only
  integration - Run integration tests only
  performance - Run performance benchmarks only
  stress      - Run stress tests only
  coverage    - Run all tests with coverage report
  quick       - Run tests stopping on first failure

Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py critical           # Run critical tests only
  python run_tests.py unit -k risk       # Run unit tests matching 'risk'
  python run_tests.py coverage           # Run with coverage report
  python run_tests.py all -x             # Stop on first failure

Environment:
  Using Python: {}
  Project root: {}
""".format(sys.executable, PROJECT_ROOT))

def check_pytest_installed():
    """Check if pytest is installed."""
    try:
        import pytest
        return True
    except ImportError:
        print("ERROR: pytest is not installed!")
        print("Please install test dependencies:")
        print(f"  {sys.executable} -m pip install pytest pytest-cov pytest-mock pytest-asyncio")
        return False

def main():
    """Main entry point."""
    if not check_pytest_installed():
        return 1
    
    # Parse command line arguments
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        print_usage()
        return 0
    
    test_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    extra_args = sys.argv[2:] if len(sys.argv) > 2 else None
    
    # Validate test type
    valid_types = ["all", "critical", "unit", "integration", "performance", "stress", "coverage", "quick"]
    if test_type not in valid_types:
        print(f"Error: Unknown test type '{test_type}'")
        print(f"Valid types: {', '.join(valid_types)}")
        return 1
    
    # Run tests
    return run_tests(test_type, extra_args)

if __name__ == "__main__":
    sys.exit(main())