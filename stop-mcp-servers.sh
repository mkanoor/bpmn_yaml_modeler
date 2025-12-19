#!/bin/bash
# Stop HTTP-based MCP Servers

echo "=================================================="
echo "  Stopping MCP Servers"
echo "=================================================="
echo ""

# Stop security server
if [ -f logs/security_server.pid ]; then
    SECURITY_PID=$(cat logs/security_server.pid)
    echo "Stopping Security Server (PID: $SECURITY_PID)..."
    kill $SECURITY_PID 2>/dev/null && echo "  ✓ Stopped" || echo "  ⚠️  Already stopped"
    rm logs/security_server.pid
else
    echo "Security Server: No PID file found"
fi

# Stop KB server
if [ -f logs/kb_server.pid ]; then
    KB_PID=$(cat logs/kb_server.pid)
    echo "Stopping KB Server (PID: $KB_PID)..."
    kill $KB_PID 2>/dev/null && echo "  ✓ Stopped" || echo "  ⚠️  Already stopped"
    rm logs/kb_server.pid
else
    echo "KB Server: No PID file found"
fi

echo ""
echo "✓ MCP servers stopped"
echo ""
