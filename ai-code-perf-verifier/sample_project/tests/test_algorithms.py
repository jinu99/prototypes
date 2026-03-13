"""Tests for algorithms module — also used as benchmarks by perf-verify."""

from algorithms import fibonacci, sort_data, find_duplicates, DataProcessor


def test_fibonacci():
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1
    assert fibonacci(10) == 55
    # Larger input for measurable benchmark time
    assert fibonacci(1000) > 0


def test_sort_data():
    import random
    data = list(range(5000))
    random.shuffle(data)
    result = sort_data(data)
    assert result == list(range(5000))


def test_find_duplicates():
    items = list(range(3000)) + list(range(1500))
    dupes = find_duplicates(items)
    assert len(dupes) == 1500


def test_data_processor_normalize():
    dp = DataProcessor()
    dp.load(list(range(10000)))
    result = dp.normalize()
    assert abs(result[0] - 0.0) < 1e-9
    assert abs(result[-1] - 1.0) < 1e-9
