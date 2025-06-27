#!/usr/bin/env python3
"""
Test runner for dazzlesum tests.
"""

import unittest
import sys
import argparse
from pathlib import Path


def run_unit_tests(coverage=False):
    """Run unit tests."""
    print("Running unit tests...")

    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent
    suite = loader.discover(start_dir, pattern='test_*.py')

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if coverage:
        print("Note: Coverage reporting not implemented yet")

    return result.wasSuccessful()


def run_integration_tests():
    """Run integration tests."""
    print("Running integration tests...")
    print("Note: Integration tests not implemented yet")
    return True


def run_cli_tests():
    """Run CLI tests."""
    print("Running CLI tests...")

    # Test basic CLI functionality
    try:
        import subprocess
        import sys

        # Test help command
        result = subprocess.run([
            sys.executable, 'dazzlesum.py', '--help'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)

        if result.returncode != 0:
            print(f"CLI help test failed: {result.stderr}")
            return False

        if 'usage:' not in result.stdout.lower():
            print("CLI help output doesn't contain usage information")
            return False

        print("CLI tests passed")
        return True

    except Exception as e:
        print(f"CLI tests failed: {e}")
        return False


def run_github_tests():
    """Run GitHub API tests."""
    print("Running GitHub API tests...")
    print("Note: GitHub API tests not applicable for dazzlesum")
    return True


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description='Run dazzlesum tests')
    parser.add_argument('--unit', action='store_true', help='Run unit tests')
    parser.add_argument('--integration', action='store_true', help='Run integration tests')
    parser.add_argument('--cli', action='store_true', help='Run CLI tests')
    parser.add_argument('--github', action='store_true', help='Run GitHub tests')
    parser.add_argument('--coverage', action='store_true', help='Run with coverage')
    parser.add_argument('--all', action='store_true', help='Run all tests')

    args = parser.parse_args()

    # If no specific test type is requested, run all
    if not any([args.unit, args.integration, args.cli, args.github]):
        args.all = True

    success = True

    if args.unit or args.all:
        success &= run_unit_tests(coverage=args.coverage)

    if args.integration or args.all:
        success &= run_integration_tests()

    if args.cli or args.all:
        success &= run_cli_tests()

    if args.github:
        success &= run_github_tests()

    if success:
        print("\nAll tests passed!")
        sys.exit(0)
    else:
        print("\nSome tests failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
