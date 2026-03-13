"""Simple HTTP server for the VRAM Resource Planner web UI.

Serves static HTML and provides JSON API endpoints for:
- Listing available models
- Single model VRAM estimation
- Multi-model planning
- Grid search for feasible combinations
- llama.cpp reference validation
- GGUF file upload and parsing
- MoE offloading options
"""

import json
import os
import tempfile
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from planner import (
    get_all_sample_models,
    plan_single_model,
    plan_multi_model,
    plan_grid_search,
    validate_against_llamacpp,
    plan_from_gguf,
    DEFAULT_QUANT_OPTIONS,
    DEFAULT_CONTEXT_OPTIONS,
)


class PlannerHandler(SimpleHTTPRequestHandler):
    """HTTP request handler with REST API endpoints."""

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/api/models":
            self._json_response(self._handle_models())
        elif path == "/api/estimate":
            self._json_response(self._handle_estimate(params))
        elif path == "/api/multi":
            self._json_response(self._handle_multi(params))
        elif path == "/api/grid":
            self._json_response(self._handle_grid(params))
        elif path == "/api/validate":
            self._json_response(self._handle_validate())
        elif path == "/api/quant-options":
            self._json_response({
                "quantizations": [{"name": q, "bpw": b} for q, b in DEFAULT_QUANT_OPTIONS],
                "context_lengths": DEFAULT_CONTEXT_OPTIONS,
            })
        elif path == "/" or path == "/index.html":
            self._serve_file("index.html", "text/html")
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/multi":
            body = self._read_json_body()
            if body:
                self._json_response(self._handle_multi_post(body))
            else:
                self._error_response(400, "Invalid JSON body")
        elif parsed.path == "/api/grid":
            body = self._read_json_body()
            if body:
                self._json_response(self._handle_grid_post(body))
            else:
                self._error_response(400, "Invalid JSON body")
        elif parsed.path == "/api/upload-gguf":
            self._json_response(self._handle_gguf_upload())
        else:
            self._error_response(404, "Not found")

    def _handle_models(self):
        models = get_all_sample_models()
        return {
            "models": [
                {
                    "key": key,
                    "name": info["name"],
                    "architecture": info["architecture"],
                    "params": f"{info.get('estimated_params', 0) / 1e9:.1f}B" if info.get('estimated_params', 0) > 0 else "N/A",
                    "block_count": info["block_count"],
                    "embedding_length": info["embedding_length"],
                    "head_count": info["head_count"],
                    "head_count_kv": info["head_count_kv"],
                    "expert_count": info.get("expert_count", 0),
                    "expert_used_count": info.get("expert_used_count", 0),
                    "context_length": info["context_length"],
                    "bits_per_weight": info["bits_per_weight"],
                    "file_type": info["file_type"],
                }
                for key, info in models
            ]
        }

    def _handle_estimate(self, params):
        model_key = params.get("model", [None])[0]
        ctx = params.get("context", [None])[0]
        if not model_key:
            return {"error": "Missing 'model' parameter"}
        ctx = int(ctx) if ctx else None
        try:
            return plan_single_model(model_key, ctx)
        except ValueError as e:
            return {"error": str(e)}

    def _handle_multi(self, params):
        models_str = params.get("models", [None])[0]
        budget = params.get("budget", [None])[0]
        if not models_str:
            return {"error": "Missing 'models' parameter"}

        configs = []
        for m in models_str.split(","):
            parts = m.strip().split(":")
            cfg = {"model_key": parts[0]}
            if len(parts) > 1:
                cfg["context_length"] = int(parts[1])
            configs.append(cfg)

        budget = float(budget) if budget else None
        try:
            return plan_multi_model(configs, budget)
        except ValueError as e:
            return {"error": str(e)}

    def _handle_multi_post(self, body):
        configs = body.get("models", [])
        budget = body.get("vram_budget_mb")
        try:
            return plan_multi_model(configs, budget)
        except ValueError as e:
            return {"error": str(e)}

    def _handle_grid(self, params):
        models_str = params.get("models", [""])[0]
        budget = params.get("budget", [None])[0]
        if not budget:
            return {"error": "Missing 'budget' parameter"}

        model_keys = [m.strip() for m in models_str.split(",") if m.strip()]
        if not model_keys:
            from gguf_parser import SAMPLE_PROFILES
            model_keys = list(SAMPLE_PROFILES.keys())

        return {"combinations": plan_grid_search(model_keys, float(budget))}

    def _handle_grid_post(self, body):
        model_keys = body.get("models", [])
        budget = body.get("vram_budget_mb")
        quant_options = body.get("quant_options")
        context_options = body.get("context_options")

        if not budget:
            return {"error": "Missing 'vram_budget_mb'"}
        if not model_keys:
            from gguf_parser import SAMPLE_PROFILES
            model_keys = list(SAMPLE_PROFILES.keys())

        quants = [(q["name"], q["bpw"]) for q in quant_options] if quant_options else None
        contexts = context_options if context_options else None

        return {"combinations": plan_grid_search(model_keys, float(budget), quants, contexts)}

    def _handle_validate(self):
        return {"validations": validate_against_llamacpp()}

    def _handle_gguf_upload(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {"error": "No file uploaded"}
        if content_length > 100 * 1024 * 1024:  # 100MB limit for headers
            return {"error": "File too large (we only parse headers, but limit upload size)"}

        # Parse context_length from query string
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        ctx = params.get("context", [None])[0]
        ctx = int(ctx) if ctx else None

        data = self.rfile.read(content_length)
        with tempfile.NamedTemporaryFile(suffix=".gguf", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        try:
            result = plan_from_gguf(tmp_path, ctx)
            return result
        except Exception as e:
            return {"error": f"Failed to parse GGUF: {str(e)}"}
        finally:
            os.unlink(tmp_path)

    def _json_response(self, data, status=200):
        body = json.dumps(data, indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _error_response(self, status, message):
        self._json_response({"error": message}, status)

    def _read_json_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return None
        try:
            return json.loads(self.rfile.read(content_length))
        except json.JSONDecodeError:
            return None

    def _serve_file(self, filename, content_type):
        filepath = os.path.join(os.path.dirname(__file__) or ".", filename)
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self._error_response(404, f"File not found: {filename}")

    def log_message(self, format, *args):
        """Quieter logging."""
        pass


def run_server(port=8000):
    server = HTTPServer(("0.0.0.0", port), PlannerHandler)
    print(f"VRAM Resource Planner running at http://localhost:{port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port)
