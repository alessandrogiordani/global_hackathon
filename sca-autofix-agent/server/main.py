"""
Entry point for running the MCP vulnerability scanner server.

This module provides the command-line interface for starting the server.
It's configured in pyproject.toml as the 'vulnerability-scanner-mcp' command.
"""

import argparse
import sys

import uvicorn


def main():
    """
    Main entry point for the MCP server.

    Parses command-line arguments and starts the uvicorn server.
    """
    parser = argparse.ArgumentParser(
        description="Vulnerability Scanner MCP Server - Scan code repositories for security issues"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    args = parser.parse_args()

    print(f"🔒 Starting Vulnerability Scanner MCP Server...")
    print(f"📍 Server will be available at: http://{args.host}:{args.port}")
    print(f"🔧 MCP endpoint: http://{args.host}:{args.port}/mcp")
    print(f"❤️  Health check: http://{args.host}:{args.port}/health")
    print()

    try:
        uvicorn.run(
            "server.app:combined_app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

