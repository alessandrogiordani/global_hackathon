"""
FastAPI application configuration for the MCP vulnerability scanner server.

This module sets up the core application by:
1. Creating and configuring the FastMCP server instance
2. Loading and registering all MCP vulnerability scanning tools
3. Setting up CORS middleware for cross-origin requests
4. Combining MCP routes with standard FastAPI routes
5. Optionally serving static files for a web frontend
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastmcp import FastMCP

from .tools import load_tools
from .utils import header_store

# Create MCP server instance
mcp_server = FastMCP(name="vulnerability-scanner-mcp")

# Static files directory (for web UI if needed)
STATIC_DIR = Path(__file__).parent / "../static"

# Load and register all vulnerability scanning tools with the MCP server
# Tools are defined in server/tools.py
load_tools(mcp_server)

# Convert the MCP server to a streamable HTTP application
# This creates a FastAPI app that implements the MCP protocol over HTTP
mcp_app = mcp_server.http_app()

# ============================================================================
# FastAPI Application Setup
# ============================================================================

# Create a separate FastAPI instance for additional API endpoints
# This allows you to add custom routes alongside the MCP endpoints
app = FastAPI(
    title="Vulnerability Scanner MCP Server",
    description="MCP server for scanning code repositories for dependency vulnerabilities",
    version="0.1.0",
    lifespan=mcp_app.lifespan,  # Share the lifespan context with MCP app
)


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve the index page or health check."""
    if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
        return FileResponse(STATIC_DIR / "index.html")
    else:
        return {
            "message": "Vulnerability Scanner MCP Server is running",
            "status": "healthy",
            "version": "0.1.0",
            "endpoints": {
                "mcp": "/mcp",
                "health": "/health",
            },
        }


@app.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Vulnerability Scanner MCP Server is operational",
    }


# Create the final application by combining MCP routes with custom API routes
combined_app = FastAPI(
    title="Vulnerability Scanner MCP Server",
    routes=[
        *mcp_app.routes,  # MCP protocol routes (tools, resources, etc.)
        *app.routes,  # Your custom API routes
    ],
    lifespan=mcp_app.lifespan,  # Use MCP's lifespan for proper startup/shutdown
)


# Middleware to capture request headers for user authentication
@combined_app.middleware("http")
async def capture_headers(request: Request, call_next):
    """
    Middleware to capture request headers for authentication.

    This is critical for user-level authentication when deployed as a
    Databricks App. The x-forwarded-access-token header contains the
    OAuth token for the end user.
    """
    header_store.set(dict(request.headers))
    return await call_next(request)

