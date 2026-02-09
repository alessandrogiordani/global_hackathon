#!/bin/bash

# Start the MCP vulnerability scanner server locally

set -e

echo "🔒 Starting Vulnerability Scanner MCP Server..."
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed"
    echo "Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Sync dependencies
echo "📦 Syncing dependencies..."
uv sync

echo ""
echo "🚀 Starting server on http://localhost:8000"
echo "📍 MCP endpoint: http://localhost:8000/mcp"
echo "❤️  Health check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run the server
uv run vulnerability-scanner-mcp

