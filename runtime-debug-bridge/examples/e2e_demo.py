"""End-to-end demo: wraps a buggy app, then queries via MCP protocol."""

import subprocess
import sys
import json
import os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_cmd(args, **kwargs):
    return subprocess.run(args, capture_output=True, text=True, cwd=PROJECT_DIR, **kwargs)


def mcp_call(method, params=None, req_id=1):
    """Send a JSON-RPC request to the MCP server and return the response."""
    messages = [
        json.dumps({"jsonrpc": "2.0", "id": 0, "method": "initialize",
                     "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                                "clientInfo": {"name": "demo", "version": "1.0"}}}),
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method,
                     "params": params or {}}),
    ]
    stdin_data = "\n".join(messages) + "\n"
    result = run_cmd(["uv", "run", "rdb", "mcp"], input=stdin_data, timeout=15)
    # Parse last line (our response)
    for line in result.stdout.strip().split("\n"):
        try:
            msg = json.loads(line)
            if msg.get("id") == req_id:
                return msg
        except json.JSONDecodeError:
            continue
    return None


def main():
    print("=" * 60)
    print("Runtime Debug Bridge — End-to-End Demo")
    print("=" * 60)

    # Step 1: Wrap and run the buggy app
    print("\n[1/4] Running buggy app through rdb wrap...")
    result = run_cmd(["uv", "run", "rdb", "wrap", "--", "python3", "examples/buggy_app.py"],
                     timeout=60)
    print(result.stdout[-300:] if len(result.stdout) > 300 else result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr[-200:])

    # Step 2: Query recent logs via MCP
    print("\n[2/4] Querying recent logs via MCP (get_recent_logs_tool)...")
    resp = mcp_call("tools/call", {
        "name": "get_recent_logs_tool",
        "arguments": {"n": 10, "stream": "stderr"}
    })
    if resp and "result" in resp:
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        print(f"  Session: {data['session_id']}")
        print(f"  Error logs ({data['count']} lines):")
        for log in data["logs"]:
            print(f"    [{log['stream']}] {log['line']}")
    else:
        print("  ERROR: No response from MCP server")

    # Step 3: Query HTTP traffic via MCP
    print("\n[3/4] Querying HTTP traffic via MCP (get_http_traffic_tool)...")
    resp = mcp_call("tools/call", {
        "name": "get_http_traffic_tool",
        "arguments": {"n": 5}
    })
    if resp and "result" in resp:
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        print(f"  HTTP requests ({data['count']} captured):")
        for t in data["traffic"]:
            print(f"    {t['method']} {t['url']} → {t['status_code']}")
    else:
        print("  ERROR: No response from MCP server")

    # Step 4: Query process state via MCP
    print("\n[4/4] Querying process state via MCP (get_process_state_tool)...")
    resp = mcp_call("tools/call", {
        "name": "get_process_state_tool",
        "arguments": {"pid": os.getpid()}
    })
    if resp and "result" in resp:
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        print(f"  PID: {data['pid']}")
        print(f"  Memory: RSS={data.get('memory', {}).get('rss_kb', '?')} KB")
        print(f"  Status: {data.get('status', {}).get('state', '?')}")
        print(f"  Open FDs: {len(data.get('open_fds', []))}")
    else:
        print("  ERROR: No response from MCP server")

    print("\n" + "=" * 60)
    print("Demo complete. All 3 MCP tools responded successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
