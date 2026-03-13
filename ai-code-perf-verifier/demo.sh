#!/bin/bash
# End-to-end demo of perf-verify
# This script:
# 1. Sets up a temp git repo with the sample project
# 2. Makes a "slow" change to a function
# 3. Runs perf-verify to detect the regression

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEMO_DIR=$(mktemp -d)
echo "=== Setting up demo in $DEMO_DIR ==="

# Copy sample project
cp -r "$SCRIPT_DIR/sample_project/"* "$DEMO_DIR/"
mkdir -p "$DEMO_DIR/tests"
cp -r "$SCRIPT_DIR/sample_project/tests/"* "$DEMO_DIR/tests/"

cd "$DEMO_DIR"
git init
git add -A
git commit -m "initial: fast implementations"

# Now make a "slow" change — replace fibonacci with naive recursive version
cat > algorithms.py << 'PYTHON'
"""Sample algorithms for perf-verify demo."""


def fibonacci(n: int) -> int:
    """Compute the nth Fibonacci number — intentionally slow recursive version."""
    if n <= 1:
        return n
    # Intentionally slow: O(2^n) instead of O(n)
    if n > 25:
        n = 25  # cap to avoid timeout
    return fibonacci(n - 1) + fibonacci(n - 2)


def sort_data(data: list) -> list:
    """Sort a list of numbers — intentionally slow bubble sort."""
    data = list(data)
    n = len(data)
    for i in range(min(n, 500)):
        for j in range(0, min(n - i - 1, 500)):
            if data[j] > data[j + 1]:
                data[j], data[j + 1] = data[j + 1], data[j]
    return data


def find_duplicates(items: list) -> list:
    """Find duplicate items in a list."""
    seen = set()
    duplicates = set()
    for item in items:
        if item in seen:
            duplicates.add(item)
        seen.add(item)
    return list(duplicates)


class DataProcessor:
    """Process data with various transformations."""

    def __init__(self):
        self.data = []

    def load(self, data: list):
        self.data = list(data)

    def normalize(self) -> list[float]:
        """Normalize data to 0-1 range."""
        if not self.data:
            return []
        min_val = min(self.data)
        max_val = max(self.data)
        if max_val == min_val:
            return [0.5] * len(self.data)
        return [(x - min_val) / (max_val - min_val) for x in self.data]
PYTHON

git add -A
git commit -m "refactor: update fibonacci and sort_data"

echo ""
echo "=== Running perf-verify ==="
echo ""

# Run perf-verify using the package
PYTHONPATH="$SCRIPT_DIR" python3 -m perf_verify.cli --ref HEAD~1 --runs 3
EXIT_CODE=$?

echo ""
echo "=== Exit code: $EXIT_CODE ==="

# Cleanup
cd /
rm -rf "$DEMO_DIR"

exit $EXIT_CODE
