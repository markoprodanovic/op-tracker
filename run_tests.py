#!/usr/bin/env python3
"""
Test runner for One Piece Tracker.

Runs all tests in the tests directory for easy validation.
"""

import sys
import asyncio
import subprocess
import os
from pathlib import Path

# Add src to Python path
sys.path.append(str(Path(__file__).parent))


def run_test_file(test_file: str) -> bool:
    """Run a specific test file."""
    try:
        # Set PYTHONPATH to include the project root
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).parent)

        result = subprocess.run([sys.executable, test_file],
                                capture_output=True, text=True,
                                cwd=Path.cwd(), env=env)

        if result.returncode == 0:
            print(f"✅ {test_file} - PASSED")
            return True
        else:
            print(f"❌ {test_file} - FAILED")
            if result.stdout:
                print("STDOUT:", result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            return False

    except Exception as e:
        print(f"❌ {test_file} - ERROR: {e}")
        return False


async def main():
    """Run all tests."""
    print("🧪 One Piece Tracker - Test Suite")
    print("=" * 50)

    # Define tests to run
    tests = [
        "tests/test_scraper.py",
        "tests/test_database.py",
        "tests/test_workflow.py"
    ]

    results = []
    for test in tests:
        test_path = Path(test)
        if test_path.exists():
            success = run_test_file(str(test_path))
            results.append(success)
        else:
            print(f"⚠️  {test} - FILE NOT FOUND")
            results.append(False)

    print("\n" + "=" * 50)

    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"🎉 All tests passed! ({passed}/{total})")
        return 0
    else:
        print(f"❌ Some tests failed: {passed}/{total} passed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
