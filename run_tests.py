#!/usr/bin/env python3
"""FitOS — Test Runner
Runs the full test suite with coverage reporting.
Usage:
    python run_tests.py              # Run all tests
    python run_tests.py -v           # Verbose
    python run_tests.py --coverage   # With coverage report
"""

import sys
import subprocess
from pathlib import Path


def main():
    project_root = Path(__file__).resolve().parent

    args = sys.argv[1:]
    verbose = "-v" in args or "--verbose" in args
    coverage = "--coverage" in args or "-c" in args

    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=app", "--cov-report=term-missing", "--cov-report=html"])
    
    # Add test directory
    cmd.append(str(project_root / "tests"))

    print("=" * 50)
    print("  FitOS — Test Suite Runner")
    print("=" * 50)
    print(f"  Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=project_root)
    
    if coverage:
        html_report = project_root / "htmlcov" / "index.html"
        if html_report.exists():
            print(f"\nCoverage HTML report: file://{html_report}")
    
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()