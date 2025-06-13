#!/usr/bin/env python3
"""
Test runner for the trading app
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and print results"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, capture_output=False, text=True)
    return result.returncode == 0


def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description='Run trading app tests')
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--performance', action='store_true', help='Run performance tests only')
    parser.add_argument('--coverage', action='store_true', help='Run with coverage report')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-k', '--filter', help='Filter tests by keyword')
    args = parser.parse_args()
    
    # Base pytest command
    base_cmd = [sys.executable, '-m', 'pytest']
    
    if args.verbose:
        base_cmd.append('-v')
    else:
        base_cmd.append('-q')
        
    if args.filter:
        base_cmd.extend(['-k', args.filter])
    
    # Determine which tests to run
    all_tests = not (args.unit or args.integration or args.performance)
    
    success = True
    
    # Run unit tests
    if args.unit or all_tests:
        cmd = base_cmd + ['tests/unit/']
        if args.coverage:
            cmd = [sys.executable, '-m', 'pytest', '--cov=src', '--cov-report=html', '--cov-report=term'] + cmd[3:]
        success &= run_command(cmd, "Unit Tests")
    
    # Run integration tests
    if args.integration or all_tests:
        cmd = base_cmd + ['tests/integration/']
        success &= run_command(cmd, "Integration Tests")
    
    # Run performance tests
    if args.performance or all_tests:
        cmd = base_cmd + ['tests/performance/', '-s']  # -s to see print statements
        success &= run_command(cmd, "Performance Benchmarks")
    
    # Summary
    print(f"\n{'='*60}")
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    print(f"{'='*60}")
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())