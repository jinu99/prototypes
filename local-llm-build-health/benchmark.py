"""Run llama-bench and parse results."""

import subprocess
import json
import signal
from pathlib import Path

# Tiny GGUF model for benchmarking (TinyLlama 1.1B Q4_0 — ~600MB)
DEFAULT_MODEL_URL = (
    "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/"
    "resolve/main/tinyllama-1.1b-chat-v1.0.Q4_0.gguf"
)
MODEL_DIR = Path(__file__).parent / ".work" / "models"


def ensure_model(model_url: str = DEFAULT_MODEL_URL) -> Path:
    """Download a GGUF model if not present. Returns path to model file."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    filename = model_url.split("/")[-1]
    model_path = MODEL_DIR / filename
    if model_path.exists():
        print(f"[bench] Model already downloaded: {filename}")
        return model_path
    print(f"[bench] Downloading model: {filename}...")
    subprocess.run(
        ["curl", "-L", "-o", str(model_path), model_url],
        check=True, timeout=300,
    )
    print(f"[bench] Model ready: {model_path}")
    return model_path


def run_bench(bench_binary: str, model_path: str,
              n_prompt: int = 128, n_gen: int = 64,
              timeout: int = 120) -> dict:
    """Run llama-bench and return parsed results.

    Returns dict with:
        success: bool
        results: list of dicts with tok/s etc.
        error: str if failed
        crash: bool if segfault/signal
        returncode: int
    """
    cmd = [
        bench_binary,
        "-m", str(model_path),
        "-p", str(n_prompt),
        "-n", str(n_gen),
        "-o", "json",
    ]

    output = {"success": False, "results": [], "error": None,
              "crash": False, "returncode": None, "raw_output": ""}

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        output["returncode"] = proc.returncode
        output["raw_output"] = proc.stdout + proc.stderr

        # Detect crash signals
        if proc.returncode < 0:
            sig = -proc.returncode
            sig_name = signal.Signals(sig).name if sig in signal.Signals._value2member_map_ else f"signal {sig}"
            output["crash"] = True
            output["error"] = f"Process killed by {sig_name} (exit code {proc.returncode})"
            return output

        if proc.returncode != 0:
            output["error"] = f"llama-bench exited with code {proc.returncode}\n{proc.stderr[-500:]}"
            return output

        # Parse JSON output
        results = _parse_bench_output(proc.stdout)
        if results:
            output["results"] = results
            output["success"] = True
        else:
            output["error"] = "No benchmark results parsed from output"
            output["raw_output"] = proc.stdout[:2000]

    except subprocess.TimeoutExpired:
        output["error"] = f"llama-bench timed out after {timeout}s"
    except FileNotFoundError:
        output["error"] = f"llama-bench binary not found: {bench_binary}"
    except Exception as e:
        output["error"] = f"Unexpected error: {e}"

    return output


def _parse_bench_output(stdout: str) -> list[dict]:
    """Parse llama-bench JSON output into normalized results."""
    results = []
    # llama-bench with -o json outputs one JSON array
    try:
        data = json.loads(stdout)
        if isinstance(data, list):
            for entry in data:
                results.append(_normalize_entry(entry))
            return results
    except json.JSONDecodeError:
        pass

    # Try line-by-line JSON (some versions output JSONL)
    for line in stdout.strip().split("\n"):
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            entry = json.loads(line)
            results.append(_normalize_entry(entry))
        except json.JSONDecodeError:
            continue

    return results


def _normalize_entry(entry: dict) -> dict:
    """Normalize a bench entry to our standard schema."""
    return {
        "model": entry.get("model_type", entry.get("model_filename", entry.get("model", "unknown"))),
        "test": entry.get("test", "default"),
        "n_prompt": entry.get("n_prompt", 0),
        "n_gen": entry.get("n_gen", 0),
        "tok_s_prompt": entry.get("avg_ts", entry.get("t/s", 0.0))
            if entry.get("n_gen", 0) == 0
            else 0.0,
        "tok_s_gen": entry.get("avg_ts", entry.get("t/s", 0.0))
            if entry.get("n_gen", 0) > 0
            else 0.0,
        "mem_mb": entry.get("mem", entry.get("model_size", 0)) / (1024 * 1024)
            if entry.get("mem", entry.get("model_size", 0)) > 10000
            else entry.get("mem", entry.get("model_size", 0)),
        "raw": entry,
    }
