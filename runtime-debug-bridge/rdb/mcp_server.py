"""MCP server exposing runtime debug tools."""

import json
from pathlib import Path
from mcp.server.fastmcp import FastMCP

from rdb.storage import get_db, get_recent_logs, get_recent_http, get_latest_session
from rdb.procinfo import get_process_state as _get_proc_state

mcp = FastMCP("runtime-debug-bridge")


@mcp.tool()
def get_recent_logs_tool(
    n: int = 50,
    session_id: str | None = None,
    stream: str | None = None,
) -> str:
    """Get recent stdout/stderr log lines captured from the wrapped process.

    Args:
        n: Number of recent lines to return (default 50)
        session_id: Filter by session ID (default: latest session)
        stream: Filter by 'stdout' or 'stderr' (default: both)
    """
    conn = get_db()
    if not session_id:
        session_id = get_latest_session(conn)
    if not session_id:
        return json.dumps({"error": "No sessions found. Run `rdb wrap -- <command>` first."})

    logs = get_recent_logs(conn, n=n, session_id=session_id, stream=stream)
    conn.close()
    return json.dumps({
        "session_id": session_id,
        "count": len(logs),
        "logs": [
            {"stream": l["stream"], "line": l["line"], "ts": l["ts"]}
            for l in logs
        ],
    }, indent=2)


@mcp.tool()
def get_http_traffic_tool(
    n: int = 20,
    session_id: str | None = None,
) -> str:
    """Get captured HTTP traffic (requests/responses) from the wrapped process.

    Args:
        n: Number of recent HTTP exchanges to return (default 20)
        session_id: Filter by session ID (default: latest session)
    """
    conn = get_db()
    if not session_id:
        session_id = get_latest_session(conn)
    if not session_id:
        return json.dumps({"error": "No sessions found. Run `rdb wrap -- <command>` first."})

    traffic = get_recent_http(conn, n=n, session_id=session_id)
    conn.close()
    return json.dumps({
        "session_id": session_id,
        "count": len(traffic),
        "traffic": [
            {
                "method": t["method"],
                "url": t["url"],
                "status_code": t["status_code"],
                "request_headers": t["request_headers"],
                "response_headers": t["response_headers"],
                "response_body_preview": (t["response_body"] or "")[:512],
                "ts": t["ts"],
            }
            for t in traffic
        ],
    }, indent=2)


@mcp.tool()
def get_process_state_tool(pid: int) -> str:
    """Get process state from /proc: open FDs, memory usage, environment variables.

    Args:
        pid: Process ID to inspect
    """
    state = _get_proc_state(pid)
    return json.dumps(state, indent=2, default=str)


def run_mcp_server():
    """Run the MCP server with stdio transport."""
    mcp.run(transport="stdio")
