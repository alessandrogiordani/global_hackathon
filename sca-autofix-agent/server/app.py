"""
FastAPI application configuration for the MCP vulnerability scanner server.

This module sets up the core application by:
1. Creating and configuring the FastMCP server instance
2. Loading and registering all MCP vulnerability scanning tools
3. Setting up CORS middleware for cross-origin requests
4. Combining MCP routes with standard FastAPI routes
5. Optionally serving static files for a web frontend
"""

import contextlib
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import JSONResponse, FileResponse
from starlette.routing import Route, Mount
from mcp.server.fastmcp import FastMCP

from .tools import load_tools
from .utils import header_store

# Create MCP server instance with stateless HTTP mode for scalability
mcp_server = FastMCP(
    name="vulnerability-scanner-mcp",
    stateless_http=True,
    json_response=True
)

# Static files directory (for web UI if needed)
STATIC_DIR = Path(__file__).parent.parent / "static"

# Load and register all vulnerability scanning tools with the MCP server
# Tools are defined in server/tools.py
load_tools(mcp_server)

# Configure the MCP server to mount at /mcp
mcp_server.settings.streamable_http_path = "/"


# ============================================================================
# Custom Routes
# ============================================================================

async def serve_index(request):
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


async def health_check(request):
    """Health check endpoint."""
    return JSONResponse({
        "status": "healthy",
        "message": "Vulnerability Scanner MCP Server is operational",
    })


# ============================================================================
# Combined Application Setup
# ============================================================================

# Create a lifespan context manager to run the session manager
@contextlib.asynccontextmanager
async def lifespan(app):
    async with mcp_server.session_manager.run():
        yield


# Create the final application by combining MCP routes with custom API routes
combined_app = Starlette(
    routes=[
        Route("/", serve_index),
        Route("/health", health_check),
        Mount("/mcp", app=mcp_server.streamable_http_app()),
    ],
    lifespan=lifespan,
)


# Middleware to capture request headers for user authentication
@combined_app.middleware("http")
async def capture_headers(request, call_next):
    """
    Middleware to capture request headers for authentication.

    This is critical for user-level authentication when deployed as a
    Databricks App. The x-forwarded-access-token header contains the
    OAuth token for the end user.
    """
    header_store.set(dict(request.headers))
    return await call_next(request)

