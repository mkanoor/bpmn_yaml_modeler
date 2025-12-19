#!/bin/bash
# Start HTTP-based MCP Servers

echo "=================================================="
echo "  Red Hat MCP Servers - HTTP Mode"
echo "=================================================="
echo ""

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    set -a
    source .env
    set +a
    echo "✓ Environment loaded"
    echo ""
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Create logs directory
mkdir -p logs

echo "Starting MCP servers..."
echo ""

# Start Security Server (port 8001)
echo "1. Starting Security Server on port 8001..."
python3 mcp_servers/security_http_server.py > logs/security_server.log 2>&1 &
SECURITY_PID=$!
echo "   PID: $SECURITY_PID"

sleep 2

# Check if security server is running
if curl -s http://localhost:8001 > /dev/null 2>&1; then
    echo "   ✓ Security server running"
else
    echo "   ❌ Security server failed to start"
    echo "   Check logs/security_server.log for details"
fi

# Start KB Server (port 8002)
echo "2. Starting KB Server on port 8002..."
python3 mcp_servers/kb_http_server.py > logs/kb_server.log 2>&1 &
KB_PID=$!
echo "   PID: $KB_PID"

sleep 2

# Check if KB server is running
if curl -s http://localhost:8002 > /dev/null 2>&1; then
    echo "   ✓ KB server running"
else
    echo "   ❌ KB server failed to start"
    echo "   Check logs/kb_server.log for details"
fi

echo ""
echo "=================================================="
echo "  MCP Servers Started"
echo "=================================================="
echo ""
echo "Server Status:"
echo "  - Security: http://localhost:8001 (PID: $SECURITY_PID)"
echo "  - KB:       http://localhost:8002 (PID: $KB_PID)"
echo ""
echo "API Documentation:"
echo "  - Security: http://localhost:8001/docs"
echo "  - KB:       http://localhost:8002/docs"
echo ""
echo "Logs:"
echo "  - Security: logs/security_server.log"
echo "  - KB:       logs/kb_server.log"
echo ""
echo "To stop servers:"
echo "  ./stop-mcp-servers.sh"
echo "  or: kill $SECURITY_PID $KB_PID"
echo ""

# Save PIDs to file for stop script
echo "$SECURITY_PID" > logs/security_server.pid
echo "$KB_PID" > logs/kb_server.pid

echo "✓ All servers started successfully!"
echo ""
