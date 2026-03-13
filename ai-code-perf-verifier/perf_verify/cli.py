"""CLI entry point for perf-verify."""

import argparse
import sys

from perf_verify.diff_parser import get_changed_files
from perf_verify.ast_analyzer import (
    find_changed_functions,
    read_current_file,
    read_file_at_ref,
)
from perf_verify.benchmarker import benchmark_function
from perf_verify.reporter import print_changed_functions, print_comparison_report


def main():
    parser = argparse.ArgumentParser(
        prog="perf-verify",
        description="Detect performance regressions in changed Python functions",
    )
    parser.add_argument(
        "--ref", default="HEAD~1",
        help="Git ref to compare against (default: HEAD~1)",
    )
    parser.add_argument(
        "--threshold", type=float, default=2.0,
        help="Slowdown ratio threshold for warnings (default: 2.0)",
    )
    parser.add_argument(
        "--runs", type=int, default=5,
        help="Number of benchmark runs per function (default: 5)",
    )
    parser.add_argument(
        "--list-only", action="store_true",
        help="Only list changed functions, don't benchmark",
    )
    args = parser.parse_args()

    # Step 1: Find changed files
    try:
        changed_files = get_changed_files(args.ref)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    if not changed_files:
        print("No changed Python files found.")
        sys.exit(0)

    # Step 2: Find changed functions via AST
    all_changed_funcs = []
    for cf in changed_files:
        current_source = read_current_file(cf.path)
        if current_source is None:
            continue
        funcs = find_changed_functions(current_source, cf.path, cf.changed_lines)
        all_changed_funcs.extend(funcs)

    if not all_changed_funcs:
        print("No changed functions found in modified Python files.")
        sys.exit(0)

    # Print changed functions list
    func_dicts = [
        {"name": f.name, "filepath": f.filepath,
         "start_line": f.start_line, "end_line": f.end_line}
        for f in all_changed_funcs
    ]
    print_changed_functions(func_dicts)

    if args.list_only:
        sys.exit(0)

    # Step 3: Benchmark before and after
    comparisons = []
    for func in all_changed_funcs:
        # Before (at ref)
        before_source = read_file_at_ref(func.filepath, args.ref)
        if before_source is None:
            from perf_verify.benchmarker import BenchResult
            before_result = BenchResult(
                func_name=func.name,
                avg_time_ms=0, peak_memory_kb=0, runs=0,
                error="File not found at ref (new file?)",
            )
        else:
            before_result = benchmark_function(func, before_source, args.runs)

        # After (current)
        after_source = read_current_file(func.filepath)
        if after_source is None:
            from perf_verify.benchmarker import BenchResult
            after_result = BenchResult(
                func_name=func.name,
                avg_time_ms=0, peak_memory_kb=0, runs=0,
                error="File not found (deleted?)",
            )
        else:
            after_result = benchmark_function(func, after_source, args.runs)

        comparisons.append({
            "name": func.name,
            "before": before_result,
            "after": after_result,
        })

    # Step 4: Print report
    has_regression = print_comparison_report(comparisons, args.threshold)

    sys.exit(1 if has_regression else 0)


if __name__ == "__main__":
    main()
