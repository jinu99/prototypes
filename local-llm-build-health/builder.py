"""Download and build llama.cpp by release tag."""

import subprocess
import shutil
import os
from pathlib import Path

WORK_DIR = Path(__file__).parent / ".work"
CMAKE_BIN = "/tmp/cmake-3.31.6-linux-x86_64/bin/cmake"
REPO_URL = "https://github.com/ggml-org/llama.cpp.git"


def ensure_cmake() -> str:
    """Return path to cmake binary, downloading if needed."""
    if Path(CMAKE_BIN).exists():
        return CMAKE_BIN
    # Try system cmake
    if shutil.which("cmake"):
        return "cmake"
    # Download cmake
    print("[builder] Downloading cmake...")
    subprocess.run(
        "curl -sL https://github.com/Kitware/CMake/releases/download/v3.31.6/"
        "cmake-3.31.6-linux-x86_64.tar.gz | tar xz -C /tmp/",
        shell=True, check=True,
    )
    if Path(CMAKE_BIN).exists():
        return CMAKE_BIN
    raise RuntimeError("Failed to install cmake")


def clone_tag(tag: str) -> Path | None:
    """Shallow-clone a specific tag of llama.cpp. Returns source dir or None on failure."""
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    src_dir = WORK_DIR / f"llama-{tag}"
    if src_dir.exists():
        print(f"[builder] Source for {tag} already exists, reusing")
        return src_dir
    print(f"[builder] Cloning llama.cpp tag {tag}...")
    try:
        proc = subprocess.run(
            ["git", "clone", "--depth=1", "--branch", tag, REPO_URL, str(src_dir)],
            capture_output=True, text=True, timeout=120,
        )
        if proc.returncode != 0:
            return None
    except (subprocess.TimeoutExpired, Exception):
        return None
    return src_dir


def build_tag(tag: str) -> dict:
    """Build llama.cpp for a given tag. Returns dict with status info."""
    result = {
        "tag": tag,
        "src_dir": "",
        "build_dir": "",
        "success": False,
        "error": None,
        "binaries": {},
    }

    cmake = ensure_cmake()
    src_dir = clone_tag(tag)
    if src_dir is None:
        result["error"] = f"Failed to clone tag '{tag}' — tag may not exist"
        return result

    result["src_dir"] = str(src_dir)
    build_dir = src_dir / "build"
    result["build_dir"] = str(build_dir)

    # Check if already built (llama-bench exists)
    bench_bin = build_dir / "bin" / "llama-bench"
    if bench_bin.exists():
        print(f"[builder] Build for {tag} already exists, reusing")
        result["success"] = True
        for name in ["llama-bench", "llama-cli", "llama-server"]:
            for candidate in [build_dir / "bin" / name, build_dir / name]:
                if candidate.exists():
                    result["binaries"][name] = str(candidate)
                    break
        return result

    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir()

    # Configure
    print(f"[builder] Configuring {tag} with cmake...")
    try:
        proc = subprocess.run(
            [cmake, "-B", str(build_dir), "-S", str(src_dir),
             "-DCMAKE_BUILD_TYPE=Release",
             "-DGGML_CPU=ON", "-DGGML_CUDA=OFF"],
            capture_output=True, text=True, timeout=120,
        )
        if proc.returncode != 0:
            result["error"] = f"cmake configure failed:\n{proc.stderr[-1000:]}"
            return result
    except subprocess.TimeoutExpired:
        result["error"] = "cmake configure timed out (120s)"
        return result
    except Exception as e:
        result["error"] = f"cmake configure error: {e}"
        return result

    # Build
    ncpu = os.cpu_count() or 2
    print(f"[builder] Building {tag} (using {ncpu} cores)...")
    try:
        proc = subprocess.run(
            [cmake, "--build", str(build_dir), "--config", "Release",
             "-j", str(ncpu)],
            capture_output=True, text=True, timeout=600,
        )
        if proc.returncode != 0:
            result["error"] = f"build failed:\n{proc.stderr[-2000:]}"
            return result
    except subprocess.TimeoutExpired:
        result["error"] = "build timed out (600s)"
        return result
    except Exception as e:
        result["error"] = f"build error: {e}"
        return result

    # Find key binaries
    for name in ["llama-bench", "llama-cli", "llama-server"]:
        for candidate in [build_dir / "bin" / name, build_dir / name]:
            if candidate.exists():
                result["binaries"][name] = str(candidate)
                break

    result["success"] = True
    print(f"[builder] Build {tag} successful. Binaries: {list(result['binaries'].keys())}")
    return result
