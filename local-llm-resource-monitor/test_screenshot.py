"""Validate dashboard by fetching HTML and checking key elements."""

import httpx
import sys

BASE_URL = "http://127.0.0.1:8899"


def check_html():
    """Verify the dashboard HTML contains all expected sections."""
    resp = httpx.get(f"{BASE_URL}/")
    assert resp.status_code == 200, f"Dashboard returned {resp.status_code}"
    html = resp.text
    checks = [
        ("title", "Local LLM Resource Monitor" in html),
        ("gpu-content div", 'id="gpu-content"' in html),
        ("running-content div", 'id="running-content"' in html),
        ("models-content div", 'id="models-content"' in html),
        ("estimator form", 'id="est-params"' in html),
        ("preset chips", 'id="presets"' in html),
        ("result panel", 'id="result-panel"' in html),
        ("verdict box", 'id="verdict-box"' in html),
    ]
    all_pass = True
    for name, ok in checks:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] HTML contains {name}")
        if not ok:
            all_pass = False
    return all_pass


def check_apis():
    """Verify all API endpoints return valid JSON."""
    endpoints = [
        ("/api/gpu", ["mock", "gpus"]),
        ("/api/ollama/models", ["mock", "models"]),
        ("/api/ollama/running", ["mock", "models"]),
        ("/api/presets", ["presets"]),
        ("/api/meta", ["architectures", "quantizations"]),
        ("/api/estimate?params_b=8.03&quant=Q4_K_M&context_length=4096&model_name=llama-8b",
         ["model_name", "weights_mb", "kv_cache_mb", "total_gb"]),
        ("/api/check-load?params_b=8.03&quant=Q4_K_M&context_length=4096&model_name=llama-8b",
         ["estimate", "feasibility"]),
    ]
    all_pass = True
    for path, expected_keys in endpoints:
        resp = httpx.get(f"{BASE_URL}{path}")
        data = resp.json()
        ok = all(k in data for k in expected_keys)
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {path.split('?')[0]}")
        if not ok:
            missing = [k for k in expected_keys if k not in data]
            print(f"         Missing keys: {missing}")
            all_pass = False
    return all_pass


def check_estimates():
    """Verify VRAM estimates for 7B/13B/70B models."""
    models = [
        ("llama-8b", 8.03, "Q4_K_M", 4096),
        ("llama-13b", 13.02, "Q4_K_M", 4096),
        ("llama-70b", 70.6, "Q4_K_M", 4096),
    ]
    all_pass = True
    for name, params, quant, ctx in models:
        resp = httpx.get(f"{BASE_URL}/api/estimate?params_b={params}&quant={quant}&context_length={ctx}&model_name={name}")
        data = resp.json()
        total_gb = data["total_gb"]
        print(f"  [INFO] {name}: weights={data['weights_mb']:.0f}MB, kv_cache={data['kv_cache_mb']:.0f}MB, total={total_gb}GB")
        if total_gb <= 0:
            print(f"  [FAIL] {name}: invalid total")
            all_pass = False
        else:
            print(f"  [PASS] {name}: estimate looks reasonable")
    return all_pass


def check_load_feasibility():
    """Verify Go/No-Go logic works correctly."""
    # 8B should fit in 24GB mock GPU
    resp = httpx.get(f"{BASE_URL}/api/check-load?params_b=8.03&quant=Q4_K_M&context_length=4096&model_name=llama-8b")
    data = resp.json()
    verdict_8b = data["feasibility"]["verdict"]
    print(f"  [{'PASS' if verdict_8b == 'GO' else 'FAIL'}] 8B Q4_K_M → {verdict_8b} (expected GO)")

    # 70B F16 should NOT fit in 24GB
    resp = httpx.get(f"{BASE_URL}/api/check-load?params_b=70.6&quant=F16&context_length=8192&model_name=llama-70b")
    data = resp.json()
    verdict_70b = data["feasibility"]["verdict"]
    print(f"  [{'PASS' if verdict_70b == 'NO-GO' else 'FAIL'}] 70B F16 8K → {verdict_70b} (expected NO-GO)")

    return verdict_8b == "GO" and verdict_70b == "NO-GO"


if __name__ == "__main__":
    print("\n=== Dashboard HTML Check ===")
    html_ok = check_html()
    print("\n=== API Endpoint Check ===")
    api_ok = check_apis()
    print("\n=== VRAM Estimates Check ===")
    est_ok = check_estimates()
    print("\n=== Load Feasibility Check ===")
    feas_ok = check_load_feasibility()

    print("\n" + "=" * 40)
    all_ok = html_ok and api_ok and est_ok and feas_ok
    print(f"Overall: {'ALL PASS' if all_ok else 'SOME FAILURES'}")
    sys.exit(0 if all_ok else 1)
