"""Read process state from /proc filesystem."""

import os
from pathlib import Path


def get_process_state(pid: int) -> dict:
    proc = Path(f"/proc/{pid}")
    if not proc.exists():
        return {"error": f"Process {pid} not found", "pid": pid}

    result: dict = {"pid": pid}
    result["open_fds"] = _read_fds(proc)
    result["memory"] = _read_memory(proc)
    result["environ"] = _read_environ(proc)
    result["cmdline"] = _read_cmdline(proc)
    result["status"] = _read_status(proc)
    return result


def _read_fds(proc: Path) -> list[dict]:
    fd_dir = proc / "fd"
    fds = []
    try:
        for entry in sorted(fd_dir.iterdir(), key=lambda e: int(e.name)):
            try:
                target = os.readlink(str(entry))
                fds.append({"fd": int(entry.name), "target": target})
            except (OSError, ValueError):
                continue
    except PermissionError:
        return [{"error": "permission denied"}]
    return fds


def _read_memory(proc: Path) -> dict:
    try:
        status_text = (proc / "status").read_text()
    except (OSError, PermissionError):
        return {"error": "cannot read memory info"}

    mem = {}
    for line in status_text.splitlines():
        if line.startswith("VmRSS:"):
            mem["rss_kb"] = int(line.split()[1])
        elif line.startswith("VmSize:"):
            mem["vsize_kb"] = int(line.split()[1])
        elif line.startswith("VmPeak:"):
            mem["peak_kb"] = int(line.split()[1])
    return mem


def _read_environ(proc: Path) -> dict:
    try:
        data = (proc / "environ").read_bytes()
        pairs = data.split(b"\x00")
        env = {}
        for pair in pairs:
            if b"=" in pair:
                k, v = pair.split(b"=", 1)
                env[k.decode("utf-8", errors="replace")] = v.decode("utf-8", errors="replace")
        return env
    except (OSError, PermissionError):
        return {"error": "cannot read environ"}


def _read_cmdline(proc: Path) -> str:
    try:
        data = (proc / "cmdline").read_bytes()
        parts = [p.decode("utf-8", errors="replace") for p in data.split(b"\x00") if p]
        return " ".join(parts)
    except (OSError, PermissionError):
        return ""


def _read_status(proc: Path) -> dict:
    try:
        text = (proc / "status").read_text()
    except (OSError, PermissionError):
        return {"error": "cannot read status"}

    info = {}
    for line in text.splitlines():
        if line.startswith("State:"):
            info["state"] = line.split(":", 1)[1].strip()
        elif line.startswith("Threads:"):
            info["threads"] = int(line.split()[1])
        elif line.startswith("PPid:"):
            info["ppid"] = int(line.split()[1])
    return info
