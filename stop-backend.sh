#!/bin/bash

# Stop BPMN Backend Server
# This script stops the backend/main.py server and all associated MCP servers

echo "🛑 Stopping BPMN Backend Server..."

# Find and kill the main backend process
MAIN_PID=$(lsof -ti:8000 2>/dev/null)

if [ -n "$MAIN_PID" ]; then
    echo "📍 Found backend server on port 8000 (PID: $MAIN_PID)"
    kill -TERM $MAIN_PID 2>/dev/null

    # Wait for graceful shutdown
    sleep 2

    # Check if still running
    if lsof -ti:8000 >/dev/null 2>&1; then
        echo "⚠️  Server still running, forcing shutdown..."
        kill -9 $MAIN_PID 2>/dev/null
    fi

    echo "✅ Backend server stopped"
else
    echo "ℹ️  No backend server running on port 8000"
fi

# Kill any remaining MCP server processes
MCP_PIDS=$(ps aux | grep -E "redhat_(security|kb)_server.py" | grep -v grep | awk '{print $2}')

if [ -n "$MCP_PIDS" ]; then
    echo "🔧 Stopping MCP servers..."
    echo "$MCP_PIDS" | xargs kill -TERM 2>/dev/null
    sleep 1

    # Force kill if still running
    MCP_PIDS=$(ps aux | grep -E "redhat_(security|kb)_server.py" | grep -v grep | awk '{print $2}')
    if [ -n "$MCP_PIDS" ]; then
        echo "$MCP_PIDS" | xargs kill -9 2>/dev/null
    fi

    echo "✅ MCP servers stopped"
fi

# Clean up log file
if [ -f "/tmp/bpmn_server.log" ]; then
    echo "🧹 Cleaning up log file..."
    rm -f /tmp/bpmn_server.log
fi

echo "🎉 All backend services stopped successfully"
