import subprocess
import sys

# Get the test file from command line arguments if provided, else default to reliability patches
test_file = sys.argv[1] if len(sys.argv) > 1 else "tests/test_reliability_patches.py"

result = subprocess.run(
    [sys.executable, "-m", "pytest", test_file, "-v"],
    capture_output=True,
    text=True
)
print("STDOUT:")
print(result.stdout)
print("STDERR:")
print(result.stderr)
