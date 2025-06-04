#!/usr/bin/env python3
"""
Comprehensive Test Suite Runner
Executes all test suites and provides a consolidated report
"""

import sys
import os
import subprocess
import time
from datetime import datetime

def run_test_script(script_name: str, description: str):
    """Run a test script and capture results"""
    print(f"\n{'='*60}")
    print(f"RUNNING: {description}")
    print(f"Script: {script_name}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # Run the test script
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout per test
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Print output
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        # Determine success
        success = result.returncode == 0
        
        return {
            'script': script_name,
            'description': description,
            'success': success,
            'duration': duration,
            'return_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
    except subprocess.TimeoutExpired:
        print(f"ERROR: Test script {script_name} timed out after 30 seconds")
        return {
            'script': script_name,
            'description': description,
            'success': False,
            'duration': 30.0,
            'return_code': -1,
            'stdout': "",
            'stderr': "Test timed out"
        }
        
    except Exception as e:
        print(f"ERROR: Failed to run {script_name}: {str(e)}")
        return {
            'script': script_name,
            'description': description,
            'success': False,
            'duration': 0.0,
            'return_code': -1,
            'stdout': "",
            'stderr': str(e)
        }

def generate_test_report(results: list):
    """Generate comprehensive test report"""
    
    print("\n" + "="*80)
    print("COMPREHENSIVE TEST RESULTS SUMMARY")
    print("="*80)
    print(f"Test Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Test Suites: {len(results)}")
    
    # Calculate overall statistics
    passed_suites = len([r for r in results if r['success']])
    failed_suites = len(results) - passed_suites
    total_duration = sum(r['duration'] for r in results)
    
    print(f"Passed Suites: {passed_suites}")
    print(f"Failed Suites: {failed_suites}")
    print(f"Success Rate: {(passed_suites/len(results)*100):.1f}%")
    print(f"Total Duration: {total_duration:.2f} seconds")
    
    # Detailed results
    print("\n" + "-"*80)
    print("DETAILED RESULTS")
    print("-"*80)
    
    for i, result in enumerate(results, 1):
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{i:2d}. {status} | {result['description']}")
        print(f"    Script: {result['script']}")
        print(f"    Duration: {result['duration']:.2f}s")
        print(f"    Return Code: {result['return_code']}")
        
        if not result['success']:
            print(f"    Error: {result['stderr']}")
        print()
    
    # Test Suite Analysis
    print("-"*80)
    print("TEST SUITE ANALYSIS")
    print("-"*80)
    
    # Extract test counts from stdout
    for result in results:
        if result['stdout']:
            lines = result['stdout'].split('\n')
            for line in lines:
                if 'Total Tests:' in line or 'Passed:' in line or 'Failed:' in line or 'Success Rate:' in line:
                    print(f"{result['script']}: {line.strip()}")
    
    # Recommendations
    print("\n" + "-"*80)
    print("RECOMMENDATIONS")
    print("-"*80)
    
    if failed_suites == 0:
        print("🎉 ALL TEST SUITES PASSED!")
        print("✓ R-Multiple controls are working correctly")
        print("✓ Chart rescaling is functioning properly")
        print("✓ Bidirectional synchronization is operational")
        print("✓ Trading workflow is complete and functional")
        print("\nRecommended next steps:")
        print("1. Proceed with real-world testing using paper trading")
        print("2. Test with live market data connections")
        print("3. Consider implementing next epic (Trailing Stops)")
    else:
        print(f"⚠️  {failed_suites} test suite(s) failed")
        print("Recommended actions:")
        print("1. Review failed test details above")
        print("2. Fix identified issues")
        print("3. Re-run tests to verify fixes")
        print("4. Consider adding additional error handling")
    
    return passed_suites == len(results)

def main():
    """Run comprehensive test suite"""
    
    print("TRADING APP - COMPREHENSIVE TEST SUITE")
    print("Version 2.4 - Testing R-Multiple Controls & Chart Rescaling")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Define test suites to run
    test_suites = [
        {
            'script': 'test_r_multiple_controls.py',
            'description': 'R-Multiple Risk/Reward Controls (Epic 3.1.3)'
        },
        {
            'script': 'test_chart_rescaling.py', 
            'description': 'Chart Rescaling & Error Handling (Epic 5.2.3)'
        },
        {
            'script': 'test_bidirectional_sync.py',
            'description': 'Bidirectional Order Assistant ↔ Chart Synchronization'
        },
        {
            'script': 'test_trading_workflow.py',
            'description': 'Complete Trading Workflow End-to-End'
        },
        {
            'script': 'test_edge_cases.py',
            'description': 'Edge Cases and Error Scenarios'
        },
        {
            'script': 'test_performance.py',
            'description': 'Performance Metrics and Benchmarks Validation'
        }
    ]
    
    # Check if test files exist
    missing_files = []
    for suite in test_suites:
        if not os.path.exists(suite['script']):
            missing_files.append(suite['script'])
    
    if missing_files:
        print(f"ERROR: Missing test files: {missing_files}")
        print("Please ensure all test scripts are in the current directory")
        return False
    
    # Run all test suites
    results = []
    for suite in test_suites:
        result = run_test_script(suite['script'], suite['description'])
        results.append(result)
        
        # Small delay between tests
        time.sleep(1)
    
    # Generate comprehensive report
    all_passed = generate_test_report(results)
    
    # Save detailed results to file
    try:
        report_filename = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_filename, 'w') as f:
            f.write("TRADING APP COMPREHENSIVE TEST RESULTS\n")
            f.write("="*50 + "\n")
            f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for result in results:
                f.write(f"Test Suite: {result['description']}\n")
                f.write(f"Script: {result['script']}\n")
                f.write(f"Success: {result['success']}\n")
                f.write(f"Duration: {result['duration']:.2f}s\n")
                f.write(f"Return Code: {result['return_code']}\n")
                f.write("STDOUT:\n")
                f.write(result['stdout'])
                f.write("\nSTDERR:\n")
                f.write(result['stderr'])
                f.write("\n" + "-"*50 + "\n")
        
        print(f"\nDetailed results saved to: {report_filename}")
        
    except Exception as e:
        print(f"Warning: Could not save results to file: {e}")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)