"""CLI entry point for lora-merge.

Usage:
  lora-merge run      --base <path> --adapter <path> --output <path>
  lora-merge estimate  --base <path> --adapter <path>
  lora-merge verify   --base <path> --adapter <path> --output <path>
"""

import argparse
import sys
from pathlib import Path


def cmd_run(args: argparse.Namespace) -> None:
    from .merge import streaming_merge

    stats = streaming_merge(
        base_dir=args.base,
        adapter_dir=args.adapter,
        output_dir=args.output,
        batch_size=args.batch_size,
        verbose=True,
    )

    if args.verify:
        _do_verify(args.base, args.adapter, args.output)


def cmd_estimate(args: argparse.Namespace) -> None:
    from .estimate import estimate_merge, format_report

    est = estimate_merge(base_dir=args.base, adapter_dir=args.adapter)
    print(format_report(est))


def cmd_verify(args: argparse.Namespace) -> None:
    _do_verify(args.base, args.adapter, args.output)


def _do_verify(base: Path, adapter: Path, output: Path) -> None:
    from .verify import naive_merge, verify_merge

    print("\nRunning precision verification (naive merge vs streaming)...")
    reference = naive_merge(base, adapter)
    passed, failures = verify_merge(output, reference)

    if passed:
        print("✓ All tensors match (rtol=1e-5)")
    else:
        print(f"✗ {len(failures)} failure(s):")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lora-merge",
        description="Streaming LoRA merge for safetensors models",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Merge LoRA adapter into base model")
    p_run.add_argument("--base", type=Path, required=True, help="Base model directory")
    p_run.add_argument("--adapter", type=Path, required=True, help="LoRA adapter directory")
    p_run.add_argument("--output", type=Path, required=True, help="Output directory")
    p_run.add_argument("--batch-size", type=int, default=1, help="Tensors per output shard (default: 1)")
    p_run.add_argument("--verify", action="store_true", help="Verify after merge")
    p_run.set_defaults(func=cmd_run)

    # estimate
    p_est = sub.add_parser("estimate", help="Estimate merge resource requirements")
    p_est.add_argument("--base", type=Path, required=True, help="Base model directory")
    p_est.add_argument("--adapter", type=Path, required=True, help="LoRA adapter directory")
    p_est.set_defaults(func=cmd_estimate)

    # verify
    p_ver = sub.add_parser("verify", help="Verify merge output against naive merge")
    p_ver.add_argument("--base", type=Path, required=True, help="Base model directory")
    p_ver.add_argument("--adapter", type=Path, required=True, help="LoRA adapter directory")
    p_ver.add_argument("--output", type=Path, required=True, help="Merged output directory")
    p_ver.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    try:
        args.func(args)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
