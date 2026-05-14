#!/bin/bash
# OSBC One-Shot Runner
# This script starts the MCP server and ensures the environment is ready.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"

echo "Initializing OSBC..."

# 1. Stop any old processes
python3 "$ROOT_DIR/src/launcher.py" stop

# 2. Start Display
python3 "$ROOT_DIR/src/launcher.py" start

# 3. Start MCP Server (background)
echo "Starting OSBC MCP Server..."
python3 "$ROOT_DIR/osbc_mcp_server.py" > "$LOG_DIR/mcp_server.log" 2>&1 &
MCP_PID=$!
echo $MCP_PID > "$LOG_DIR/mcp.pid"

echo "OSBC is running."
echo "MCP Server Log: $LOG_DIR/mcp_server.log"
echo "Display: $DISPLAY (Resolution: 800x600)"
