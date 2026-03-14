#!/usr/bin/env bash
# Demo: Run the stabilizer proxy and test all detection scenarios
#
# Usage:
#   ./demo.sh          — Run in mock mode (no Ollama needed)
#   ./demo.sh live     — Run with Ollama backend (requires Ollama running)
#
# For Aider integration:
#   1. Start proxy:  uv run python proxy.py --mock   (or without --mock if Ollama is running)
#   2. Point Aider:  OPENAI_API_BASE=http://localhost:8400/v1 aider --model ollama/codellama
#   3. Ask Aider to do something destructive (e.g., "delete all files in src/")
#   4. Check dashboard: http://localhost:8400/

set -e
cd "$(dirname "$0")"

MODE="${1:-mock}"

echo "================================================"
echo "  Agent Stabilizer — Demo"
echo "================================================"
echo ""

if [ "$MODE" = "live" ]; then
    echo "Starting proxy in LIVE mode (Ollama backend expected at localhost:11434)..."
    uv run python proxy.py &
else
    echo "Starting proxy in MOCK mode (no backend needed)..."
    uv run python proxy.py --mock &
fi

PROXY_PID=$!
sleep 2

echo ""
echo "Running test scenarios..."
echo ""
uv run python test_scenarios.py

echo ""
echo "================================================"
echo "  Dashboard: http://localhost:8400/"
echo "  Press Ctrl+C to stop"
echo "================================================"

wait $PROXY_PID
