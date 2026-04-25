import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_phase_subagents_base.py", "-v"],
    capture_output=True,
    text=True
)
print("STDOUT:")
print(result.stdout)
print("STDERR:")
print(result.stderr)
