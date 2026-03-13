"""Sample algorithms for perf-verify demo."""


def fibonacci(n: int) -> int:
    """Compute the nth Fibonacci number."""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def sort_data(data: list) -> list:
    """Sort a list of numbers."""
    return sorted(data)


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
