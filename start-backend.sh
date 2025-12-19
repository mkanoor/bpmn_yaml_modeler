#!/bin/bash

# BPMN Workflow Execution Backend - Start Script
#
# Usage:
#   ./start-backend.sh          # Normal start
#   ./start-backend.sh --reauth # Delete Gmail token and re-authenticate

echo "========================================="
echo "  BPMN Workflow Execution Backend"
echo "========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "Please install Python 3.9 or higher"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Navigate to backend directory
cd backend

# Check for --reauth flag
if [ "$1" = "--reauth" ] || [ "$1" = "-r" ]; then
    if [ -f "token.json" ]; then
        echo "🔑 Deleting Gmail token (will re-authenticate on first email send)..."
        rm token.json
        echo "✅ Token deleted"
        echo ""
    else
        echo "ℹ️  No token.json to delete"
        echo ""
    fi
fi

# Check if requirements are installed
echo "📦 Checking dependencies..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "⚠️  Dependencies not installed. Installing..."
    pip3 install -r requirements.txt
    echo ""
fi

echo "✅ Dependencies ready"
echo ""

# Start the server
echo "🚀 Starting backend server on http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "========================================="
echo ""

python3 main.py
