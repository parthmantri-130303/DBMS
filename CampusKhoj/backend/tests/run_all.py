import sys
import unittest
from pathlib import Path

# Add project root and backend dir to sys.path
backend_dir = Path(__file__).resolve().parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

def run_all_tests():
    print("=" * 70)
    print("     CAMPUSKHOJ TEST SUITE — UNIT, API & WORKFLOW VALIDATION")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Discover and add all test files in backend/tests
    tests_dir = Path(__file__).parent
    discovered = loader.discover(start_dir=str(tests_dir), pattern="test_*.py")
    suite.addTests(discovered)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures:  {len(result.failures)}")
    print(f"Errors:    {len(result.errors)}")
    print("=" * 70)

    if result.wasSuccessful():
        print("ALL CAMPUSKHOJ BACKEND TESTS PASSED SUCCESSFULLY! (100% OK)")
        return 0
    else:
        print("SOME TESTS FAILED! Check error trace above.")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())

