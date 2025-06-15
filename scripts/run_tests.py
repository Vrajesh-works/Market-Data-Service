#!/usr/bin/env python
"""
Test runner script for Market Data Service
"""
import os
import sys
import argparse
import subprocess


def run_tests(test_type=None, verbose=False):
    """Run the specified tests"""
    cmd = ["pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if test_type == "unit":
        cmd.append("tests/unit")
    elif test_type == "integration":
        cmd.append("tests/integration")
    elif test_type == "functional":
        os.environ["RUN_E2E_TESTS"] = "1"
        cmd.append("tests/functional")
    elif test_type == "all":
        cmd.append("tests")
    else:
        cmd.append("tests/unit")  # Default to unit tests
    
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Run Market Data Service tests")
    parser.add_argument(
        "--type",
        choices=["unit", "integration", "functional", "all"],
        default="unit",
        help="Type of tests to run (default: unit)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Increase verbosity"
    )
    
    args = parser.parse_args()
    
    return run_tests(args.type, args.verbose)


if __name__ == "__main__":
    sys.exit(main()) 