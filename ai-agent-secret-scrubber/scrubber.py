"""Shell wrapper that intercepts stdout/stderr and masks secrets."""

from __future__ import annotations

import json
import selectors
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from detector import SecretDetector
from registry import SecretRegistry

MASK = "***"


def mask_line(line: str, detector: SecretDetector) -> tuple[str, list[str]]:
    """Mask all detected secrets in a line. Returns (masked_line, list of masked keys)."""
    detections = detector.detect_in_line(line)
    masked_keys = []
    for det in sorted(detections, key=lambda d: len(d.original), reverse=True):
        line = line.replace(det.original, MASK)
        masked_keys.append(f"{det.source}:{det.original[:4]}...")
    return line, masked_keys


def run_wrapped(
    command: list[str],
    registry: SecretRegistry,
    detector: SecretDetector,
    log_path: str | None = None,
) -> int:
    """Run a command, masking secrets in its stdout/stderr.

    Uses selectors to interleave stdout/stderr processing in real-time.
    Returns the command's exit code.
    """
    log_entries: list[dict] = []

    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ, ("stdout", sys.stdout))
    sel.register(proc.stderr, selectors.EVENT_READ, ("stderr", sys.stderr))

    buffers = {"stdout": b"", "stderr": b""}
    open_streams = 2

    while open_streams > 0:
        for key, _ in sel.select():
            stream_name, output_target = key.data
            chunk = key.fileobj.read1(4096) if hasattr(key.fileobj, 'read1') else key.fileobj.read(4096)

            if not chunk:
                # Flush remaining buffer
                if buffers[stream_name]:
                    line = buffers[stream_name].decode("utf-8", errors="replace")
                    masked, keys = mask_line(line, detector)
                    output_target.write(masked)
                    output_target.flush()
                    if keys:
                        log_entries.append({
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "stream": stream_name,
                            "masked_count": len(keys),
                            "sources": keys,
                        })
                sel.unregister(key.fileobj)
                open_streams -= 1
                continue

            buffers[stream_name] += chunk
            # Process complete lines
            while b"\n" in buffers[stream_name]:
                line_bytes, buffers[stream_name] = buffers[stream_name].split(b"\n", 1)
                line = line_bytes.decode("utf-8", errors="replace") + "\n"
                masked, keys = mask_line(line, detector)
                output_target.write(masked)
                output_target.flush()
                if keys:
                    log_entries.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "stream": stream_name,
                        "masked_count": len(keys),
                        "sources": keys,
                    })

    sel.close()
    proc.wait()

    # Write log if path specified
    if log_path and log_entries:
        log_file = Path(log_path)
        existing = []
        if log_file.exists():
            try:
                existing = json.loads(log_file.read_text())
            except (json.JSONDecodeError, OSError):
                existing = []
        existing.extend(log_entries)
        log_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False))

    return proc.returncode
