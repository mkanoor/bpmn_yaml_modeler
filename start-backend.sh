#!/bin/bash

# Start BPMN Backend Server
# This script starts the backend/main.py server with MCP integration

echo "🚀 Starting BPMN Backend Server..."

# Check if port 8000 is already in use
if lsof -ti:8000 >/dev/null 2>&1; then
    echo "⚠️  Port 8000 is already in use!"
    echo "    Run './stop-backend.sh' first to stop the existing server."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "    Please create it first: python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if backend/main.py exists
if [ ! -f "backend/main.py" ]; then
    echo "❌ backend/main.py not found!"
    exit 1
fi

# Create log directory if it doesn't exist
mkdir -p logs

# Start the server
LOG_FILE="logs/backend-$(date +%Y%m%d-%H%M%S).log"
echo "📝 Logging to: $LOG_FILE"

venv/bin/python3 backend/main.py > "$LOG_FILE" 2>&1 &
SERVER_PID=$!

echo "⏳ Waiting for server to start..."
sleep 3

# Check if server started successfully
if lsof -ti:8000 >/dev/null 2>&1; then
    echo "✅ Backend server started successfully!"
    echo "📍 Server PID: $SERVER_PID"
    echo "🌐 Server URL: http://localhost:8000"
    echo "📊 API Docs: http://localhost:8000/docs"
    echo "🔌 WebSocket: ws://localhost:8000/ws"
    echo ""
    echo "💡 Tips:"
    echo "   - View logs: tail -f $LOG_FILE"
    echo "   - Stop server: ./stop-backend.sh"
    echo "   - Test workflow: python3 test_simple.py workflows/[workflow].yaml context-examples/[context].json"
else
    echo "❌ Server failed to start!"
    echo "📋 Check logs: cat $LOG_FILE"
    exit 1
fi
