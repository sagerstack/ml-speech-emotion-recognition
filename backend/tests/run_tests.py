#!/usr/bin/env python3
"""
Test runner script for ML Speech Emotion Recognition API.

This script provides a convenient way to run tests with different configurations
and generate coverage reports.
"""

import argparse
import sys
import subprocess
from pathlib import Path


def run_command(cmd: list[str], check: bool = True) -> int:
    """Run a command and return the exit code."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    if check and result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    return result.returncode


def run_unit_tests(coverage: bool = True, verbose: bool = False) -> int:
    """Run unit tests only."""
    cmd = ["poetry", "run", "pytest", "-m", "unit"]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/unit",
            "--cov-report=xml:coverage-unit.xml",
            "--cov-fail-under=80"
        ])

    return run_command(cmd)


def run_integration_tests(coverage: bool = True, verbose: bool = False) -> int:
    """Run integration tests only."""
    cmd = ["poetry", "run", "pytest", "-m", "integration"]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/integration",
            "--cov-report=xml:coverage-integration.xml"
        ])

    return run_command(cmd)


def run_all_tests(coverage: bool = True, verbose: bool = False) -> int:
    """Run all tests."""
    cmd = ["poetry", "run", "pytest"]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml",
            "--cov-fail-under=90"
        ])

    return run_command(cmd)


def run_specific_tests(test_path: str, coverage: bool = False, verbose: bool = False) -> int:
    """Run specific tests."""
    cmd = ["poetry", "run", "pytest", test_path]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])

    return run_command(cmd)


def run_performance_tests(verbose: bool = False) -> int:
    """Run performance tests."""
    cmd = ["poetry", "run", "pytest", "-m", "slow"]

    if verbose:
        cmd.append("-v")

    return run_command(cmd)


def generate_coverage_report() -> int:
    """Generate detailed coverage report."""
    cmd = [
        "poetry", "run", "pytest",
        "--cov=app",
        "--cov-report=html:htmlcov",
        "--cov-report=xml",
        "--cov-report=term-missing"
    ]

    return run_command(cmd)


def check_coverage_threshold(threshold: float = 90.0) -> int:
    """Check if coverage meets threshold."""
    cmd = [
        "poetry", "run", "pytest",
        "--cov=app",
        "--cov-fail-under", str(threshold)
    ]

    return run_command(cmd)


def clean_coverage() -> int:
    """Clean coverage files."""
    import shutil

    dirs_to_clean = ["htmlcov", ".coverage"]
    files_to_clean = ["coverage.xml", ".coverage.*"]

    for dir_name in dirs_to_clean:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"Removed {dir_name}")

    for pattern in files_to_clean:
        for file_path in Path(".").glob(pattern):
            file_path.unlink()
            print(f"Removed {file_path}")

    return 0


def main() -> int:
    """Main function."""
    parser = argparse.ArgumentParser(description="Test runner for ML Speech Emotion Recognition API")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Unit tests
    unit_parser = subparsers.add_parser("unit", help="Run unit tests")
    unit_parser.add_argument("--no-coverage", action="store_true", help="Disable coverage")
    unit_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    # Integration tests
    integration_parser = subparsers.add_parser("integration", help="Run integration tests")
    integration_parser.add_argument("--no-coverage", action="store_true", help="Disable coverage")
    integration_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    # All tests
    all_parser = subparsers.add_parser("all", help="Run all tests")
    all_parser.add_argument("--no-coverage", action="store_true", help="Disable coverage")
    all_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    # Specific tests
    specific_parser = subparsers.add_parser("specific", help="Run specific tests")
    specific_parser.add_argument("path", help="Test path (e.g., tests/unit/utils/test_config.py)")
    specific_parser.add_argument("--no-coverage", action="store_true", help="Disable coverage")
    specific_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    # Performance tests
    perf_parser = subparsers.add_parser("performance", help="Run performance tests")
    perf_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    # Coverage commands
    coverage_parser = subparsers.add_parser("coverage", help="Generate coverage report")

    check_parser = subparsers.add_parser("check-coverage", help="Check coverage threshold")
    check_parser.add_argument("--threshold", type=float, default=90.0, help="Coverage threshold")

    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean coverage files")

    args = parser.parse_args()

    # Change to backend directory if not already there
    backend_dir = Path(__file__).parent.parent
    if not Path.cwd().samefile(backend_dir):
        import os
        os.chdir(backend_dir)
        print(f"Changed to directory: {backend_dir}")

    # Execute command
    if args.command == "unit":
        return run_unit_tests(coverage=not args.no_coverage, verbose=args.verbose)
    elif args.command == "integration":
        return run_integration_tests(coverage=not args.no_coverage, verbose=args.verbose)
    elif args.command == "all":
        return run_all_tests(coverage=not args.no_coverage, verbose=args.verbose)
    elif args.command == "specific":
        return run_specific_tests(args.path, coverage=not args.no_coverage, verbose=args.verbose)
    elif args.command == "performance":
        return run_performance_tests(verbose=args.verbose)
    elif args.command == "coverage":
        return generate_coverage_report()
    elif args.command == "check-coverage":
        return check_coverage_threshold(args.threshold)
    elif args.command == "clean":
        return clean_coverage()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())