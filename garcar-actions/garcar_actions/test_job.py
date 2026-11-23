"""Fixed unittest action: discover tests and fail rather than certify an empty suite."""
from pathlib import Path
import sys
import unittest


def main():
    root = Path.cwd()
    sys.path.insert(0, str(root))
    start = "tests" if (root / "tests").is_dir() else "."
    suite = unittest.defaultTestLoader.discover(start)
    count = suite.countTestCases()
    if count == 0:
        print("NO_TESTS: unittest discovered zero tests", file=sys.stderr)
        return 5
    print(f"Discovered {count} tests", flush=True)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
