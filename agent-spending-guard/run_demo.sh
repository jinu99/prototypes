#!/bin/bash
# Start mock server + proxy for interactive demo.
# Then run agent_sim.py in another terminal.

set -e
cd "$(dirname "$0")"

cleanup() {
    echo ""
    echo "Shutting down..."
    kill $MOCK_PID $PROXY_PID 2>/dev/null || true
    wait $MOCK_PID $PROXY_PID 2>/dev/null || true
    echo "Done."
}
trap cleanup EXIT INT TERM

# Remove old audit DB for clean demo
rm -f audit.db

echo "Starting mock payment server on :9000..."
uv run python mock_server.py &
MOCK_PID=$!

echo "Starting spending guard proxy on :8080..."
uv run mitmdump --mode regular --listen-port 8080 -s proxy_addon.py --quiet &
PROXY_PID=$!

sleep 2
echo ""
echo "============================================"
echo "  Agent Spending Guard — Interactive Demo"
echo "============================================"
echo ""
echo "Services running:"
echo "  Mock server: http://127.0.0.1:9000"
echo "  Proxy:       http://127.0.0.1:8080"
echo ""
echo "Run in another terminal:"
echo "  uv run python agent_sim.py"
echo ""
echo "Query audit log:"
echo "  uv run python audit_query.py"
echo ""
echo "Press Ctrl+C to stop."
echo ""

wait
