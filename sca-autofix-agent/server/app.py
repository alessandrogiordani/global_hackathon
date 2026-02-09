"""
FastAPI application configuration for the MCP vulnerability scanner server.

This module sets up the core application by:
1. Creating and configuring the FastMCP server instance
2. Loading and registering all MCP vulnerability scanning tools
3. Setting up CORS middleware for cross-origin requests
4. Using FastMCP's custom_route decorator for additional endpoints
5. Optionally serving static files for a web frontend
"""

from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse, FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastmcp import FastMCP

from .tools import load_tools
from .utils import header_store

# Create MCP server instance
mcp_server = FastMCP(name="mcp-sca-autofix-agent")

# Static files directory (for web UI if needed)
STATIC_DIR = Path(__file__).parent.parent / "static"

# Load and register all vulnerability scanning tools with the MCP server
# Tools are defined in server/tools.py
load_tools(mcp_server)


# ============================================================================
# Custom Routes using FastMCP's custom_route decorator
# ============================================================================

@mcp_server.custom_route("/", methods=["GET"])
async def serve_index(request: Request):
    """Serve the index page or health check."""
    if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
        return FileResponse(STATIC_DIR / "index.html")
    else:
        return JSONResponse({
            "message": "Vulnerability Scanner MCP Server is running",
            "status": "healthy",
            "version": "0.1.0",
            "endpoints": {
                "mcp": "/mcp",
                "health": "/health",
            },
        })


@mcp_server.custom_route("/health", methods=["GET"])
async def health_check(request: Request):
    """Health check endpoint."""
    return JSONResponse({
        "status": "healthy",
        "message": "Vulnerability Scanner MCP Server is operational",
    })


# ============================================================================
# Header Capture Middleware for Databricks Authentication
# ============================================================================

class HeaderCaptureMiddleware(BaseHTTPMiddleware):
    """
    Middleware to capture request headers for authentication.
    
    This is critical for user-level authentication when deployed as a
    Databricks App. The x-forwarded-access-token header contains the
    OAuth token for the end user.
    """
    async def dispatch(self, request: Request, call_next):
        header_store.set(dict(request.headers))
        return await call_next(request)


# ============================================================================
# Combined Application Setup
# ============================================================================

# Use http_app() which serves MCP at /mcp by default
# Custom routes (/, /health) are automatically included
_base_app = mcp_server.http_app()

# Wrap with middleware for header capture
combined_app = HeaderCaptureMiddleware(_base_app)

