"""
Utility functions for Databricks authentication and workspace access.
"""

import contextvars
import os
from pathlib import Path
from typing import Optional

from databricks.sdk import WorkspaceClient

# Context variable to store request headers (for user authentication)
header_store = contextvars.ContextVar("header_store")

# Load config.env if it exists
_config_loaded = False


def _load_config():
    """Load configuration from config.env file."""
    global _config_loaded
    if _config_loaded:
        return

    config_path = Path(__file__).parent.parent / "config.env"
    if config_path.exists():
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value.strip('"').strip("'")
    _config_loaded = True


# Load config on module import
_load_config()


def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get a configuration value.

    Checks environment variables first, then config.env.

    Args:
        key: Configuration key (e.g., "DATA_MODE", "UC_CATALOG")
        default: Default value if key not found

    Returns:
        Configuration value or default
    """
    return os.environ.get(key, default)


def is_production_mode() -> bool:
    """Check if running in production mode (using Unity Catalog)."""
    return get_config("DATA_MODE", "mock") == "production"


def is_databricks_environment() -> bool:
    """Check if running on Databricks."""
    return "DATABRICKS_RUNTIME_VERSION" in os.environ


def get_uc_config() -> dict:
    """
    Get Unity Catalog configuration.

    Returns:
        dict with catalog, schema, and table names
    """
    return {
        "catalog": get_config("UC_CATALOG", "main"),
        "schema": get_config("UC_SCHEMA", "sca_autofix"),
        "sca_findings_table": "sca_findings",
        "migration_analysis_table": "migration_analysis",
        "user_decisions_table": "user_decisions",
    }


def get_llm_config() -> dict:
    """Get LLM configuration."""
    return {
        "endpoint": get_config("LLM_ENDPOINT", "databricks-meta-llama-3-1-70b-instruct"),
        "max_tokens": int(get_config("LLM_MAX_TOKENS", "4096")),
    }


def get_workspace_client() -> WorkspaceClient:
    """
    Get a WorkspaceClient with app service principal authentication.

    When deployed as a Databricks App, this returns a client authenticated
    as the service principal associated with the app.

    When running locally, this returns a client authenticated as the current
    developer (using Databricks CLI authentication).

    Returns:
        WorkspaceClient: Authenticated workspace client
    """
    return WorkspaceClient()


def get_user_authenticated_workspace_client() -> WorkspaceClient:
    """
    Get a WorkspaceClient with end-user authentication.

    When deployed as a Databricks App, this returns a client authenticated
    as the end user making the request (using the OAuth token from headers).

    When running locally, this returns a client authenticated as the current
    developer (using Databricks CLI authentication).

    Returns:
        WorkspaceClient: Authenticated workspace client

    Raises:
        ValueError: If running in Databricks App environment but no user token found
    """
    # Check if running in a Databricks App environment
    is_databricks_app = "DATABRICKS_APP_NAME" in os.environ

    if not is_databricks_app:
        # Running locally, use default authentication
        return WorkspaceClient()

    # Running in Databricks App, require user authentication token
    headers = header_store.get({})
    token = headers.get("x-forwarded-access-token")

    if not token:
        raise ValueError(
            "Authentication token not found in request headers (x-forwarded-access-token). "
            "User authentication is required for this operation."
        )

    return WorkspaceClient(token=token, auth_type="pat")
