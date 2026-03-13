"""Benchmark functions by running existing tests and measuring time/memory."""

import importlib
import importlib.util
import sys
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path

from perf_verify.ast_analyzer import FunctionInfo

WARMUP_RUNS = 1
BENCH_RUNS = 5


@dataclass
class BenchResult:
    func_name: str
    avg_time_ms: float
    peak_memory_kb: float
    runs: int
    error: str | None = None


def _load_module_from_source(source: str, module_name: str):
    """Load a Python module from source string."""
    spec = importlib.util.spec_from_loader(
        module_name,
        loader=None,
        origin=f"<{module_name}>",
    )
    module = importlib.util.module_from_spec(spec)
    exec(compile(source, f"<{module_name}>", "exec"), module.__dict__)
    return module


def _find_test_functions(filepath: str) -> list[tuple[str, str]]:
    """Find test files and test functions that import from the given module.

    Returns list of (test_filepath, test_function_name).
    """
    module_name = Path(filepath).stem
    test_pairs = []

    # Search for test files in common locations
    search_dirs = [Path("."), Path("tests"), Path("test")]
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for test_file in search_dir.glob("test_*.py"):
            try:
                source = test_file.read_text()
            except (OSError, UnicodeDecodeError):
                continue
            # Check if this test file references our module
            if module_name in source:
                import ast
                try:
                    tree = ast.parse(source)
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                        test_pairs.append((str(test_file), node.name))

    return test_pairs


def benchmark_function(
    func_info: FunctionInfo,
    source: str,
    runs: int = BENCH_RUNS,
) -> BenchResult:
    """Benchmark a function by finding and running its tests."""
    # Load the module from source
    module_name = f"_bench_{func_info.module}"
    try:
        module = _load_module_from_source(source, module_name)
    except Exception as e:
        return BenchResult(
            func_name=func_info.name,
            avg_time_ms=0, peak_memory_kb=0, runs=0,
            error=f"Failed to load module: {e}",
        )

    # Find the actual function in the module
    func = _resolve_function(module, func_info.name)
    if func is None:
        return BenchResult(
            func_name=func_info.name,
            avg_time_ms=0, peak_memory_kb=0, runs=0,
            error=f"Function {func_info.name} not found in module",
        )

    # Try to find and run test functions
    test_pairs = _find_test_functions(func_info.filepath)
    if test_pairs:
        return _bench_via_tests(func_info, test_pairs, source, runs)

    # Fallback: benchmark the function directly (if callable with no args)
    return _bench_direct(func_info, func, runs)


def _resolve_function(module, name: str):
    """Resolve 'ClassName.method' or 'func_name' from module."""
    parts = name.split(".")
    obj = module
    for part in parts:
        obj = getattr(obj, part, None)
        if obj is None:
            return None
    # If it's a class method, we need an instance
    if len(parts) == 2:
        cls = getattr(module, parts[0], None)
        if cls:
            try:
                instance = cls()
                return getattr(instance, parts[1], None)
            except Exception:
                return None
    return obj


def _bench_via_tests(
    func_info: FunctionInfo,
    test_pairs: list[tuple[str, str]],
    module_source: str,
    runs: int,
) -> BenchResult:
    """Run test functions as benchmarks."""
    times = []
    peak_mem = 0

    # Load the module so tests can import it
    module_name = func_info.module
    temp_module = _load_module_from_source(module_source, module_name)
    old_module = sys.modules.get(module_name)
    sys.modules[module_name] = temp_module

    try:
        for test_file, test_func_name in test_pairs[:3]:  # limit to 3 tests
            test_source = Path(test_file).read_text()
            test_module = _load_module_from_source(
                test_source, f"_test_{Path(test_file).stem}"
            )
            test_fn = getattr(test_module, test_func_name, None)
            if test_fn is None:
                continue

            # Warmup
            for _ in range(WARMUP_RUNS):
                try:
                    test_fn()
                except Exception:
                    pass

            # Timed runs
            for _ in range(runs):
                tracemalloc.start()
                start = time.perf_counter()
                try:
                    test_fn()
                except Exception:
                    pass
                elapsed = time.perf_counter() - start
                _, mem_peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                times.append(elapsed * 1000)  # ms
                peak_mem = max(peak_mem, mem_peak / 1024)  # KB
    finally:
        if old_module is not None:
            sys.modules[module_name] = old_module
        else:
            sys.modules.pop(module_name, None)

    if not times:
        return BenchResult(
            func_name=func_info.name,
            avg_time_ms=0, peak_memory_kb=0, runs=0,
            error="No tests executed successfully",
        )

    return BenchResult(
        func_name=func_info.name,
        avg_time_ms=sum(times) / len(times),
        peak_memory_kb=peak_mem,
        runs=len(times),
    )


def _bench_direct(
    func_info: FunctionInfo,
    func,
    runs: int,
) -> BenchResult:
    """Benchmark a function by calling it directly (no-arg only)."""
    times = []
    peak_mem = 0

    # Warmup
    for _ in range(WARMUP_RUNS):
        try:
            func()
        except TypeError:
            return BenchResult(
                func_name=func_info.name,
                avg_time_ms=0, peak_memory_kb=0, runs=0,
                error="Function requires arguments; no test found",
            )
        except Exception:
            pass

    for _ in range(runs):
        tracemalloc.start()
        start = time.perf_counter()
        try:
            func()
        except Exception:
            pass
        elapsed = time.perf_counter() - start
        _, mem_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        times.append(elapsed * 1000)
        peak_mem = max(peak_mem, mem_peak / 1024)

    return BenchResult(
        func_name=func_info.name,
        avg_time_ms=sum(times) / len(times),
        peak_memory_kb=peak_mem,
        runs=len(times),
    )
