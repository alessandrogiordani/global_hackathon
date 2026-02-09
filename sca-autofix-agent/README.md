# Vulnerability Scanner MCP Server

A production-ready Model Context Protocol (MCP) server for scanning code repositories for dependency vulnerabilities. Built with FastMCP and FastAPI, deployable as a Databricks App.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.0-green.svg)](https://modelcontextprotocol.io)

## 🔒 Overview

This MCP server provides AI agents with powerful tools to:

- 🔍 **Scan repositories** for dependencies across multiple languages (Python, JavaScript, Java, R)
- 🛡️ **Check vulnerabilities** using OSV.dev API (no downloads required!)
- 🔬 **Analyze code usage** with AST parsing to understand package impact (Python + Java)
- ☕ **Java code analysis** with javalang: parse AST, extract method calls, find API usage
- ⚠️ **Detect breaking changes** using changelog analysis and curated databases
- 📊 **Visualize patches** with color-coded diffs before applying
- 🔧 **Apply security patches** automatically with Git integration
- 📈 **Monitor repositories** continuously for new vulnerabilities
- 🗄️ **Integrate with Unity Catalog** for production workflows and audit trails

### Why Use This Tool?

✅ **API-First Approach**: No package downloads - uses registry APIs for instant metadata  
✅ **Multi-Language Support**: Python, JavaScript, Java, R ecosystems  
✅ **Breaking Change Detection**: Automated analysis of API changes between versions  
✅ **Visual Diffs**: See exactly what will change before applying patches  
✅ **Databricks Native**: Seamless integration with Databricks Repos and Unity Catalog  
✅ **Agent-Ready**: Designed for AI agent orchestration via MCP protocol  
✅ **Production-Grade**: Includes audit trails, UC integration, and test validation  

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Databricks workspace (for deployment)

### Installation

```bash
# Clone or navigate to the project
cd vulnerability-scanner-mcp

# Install dependencies with uv
uv sync

# Or with pip
pip install -r requirements.txt
```

### Run Locally

```bash
# Start the server (port 8000)
./scripts/dev/start_server.sh

# Or manually
uv run python -m server.main

# Or with custom port
uv run python -m server.main --port 8080
```

The server will be available at:
- **MCP Endpoint**: `http://localhost:8000/mcp/v1/`
- **Health Check**: `http://localhost:8000/health`
- **Web Interface**: `http://localhost:8000/`

### Test the Server

```bash
# Run local test (checks tools without authentication)
python scripts/dev/test_local.py

# Run full integration tests (requires Databricks auth)
uv run pytest tests/
```

## 🏗️ Architecture

```
vulnerability-scanner-mcp/
├── server/              # MCP server core
│   ├── app.py          # FastAPI + FastMCP setup
│   ├── main.py         # Entry point
│   ├── tools.py        # 15 MCP tools
│   └── utils.py        # Databricks authentication
├── services/           # Business logic
│   ├── code_analyzer.py          # Parse dependencies from manifests
│   ├── vulnerability_scanner.py  # OSV.dev API client
│   ├── package_registry.py       # PyPI/npm/Maven APIs
│   ├── static_analyzer.py        # AST parsing for code analysis
│   ├── changelog_fetcher.py      # Fetch changelogs from GitHub/PyPI
│   ├── api_changelog_analyzer.py # Breaking change detection
│   ├── llm_analyzer.py           # LLM-enhanced changelog analysis
│   ├── diff_generator.py         # Patch visualization
│   ├── git_client.py             # Databricks Repos API
│   └── uc_integration.py         # Unity Catalog integration
├── models/             # Pydantic data models
│   ├── package.py      # Package and dependency models
│   ├── vulnerability.py # Vulnerability and report models
│   └── usage.py        # Usage analysis and API change models
├── tests/              # Integration tests
├── static/             # Web interface
└── docs/               # Detailed documentation
    ├── AGENT_CONFIGURATION.md
    ├── AGENT_MCP_TOOLS.md
    ├── AGENT_TOOL_ORGANIZATION.md
    ├── CHANGELOG.md
    ├── CONTRIBUTING.md
    ├── DEPLOYMENT.md
    ├── JAVA_ANALYSIS.md
    ├── LANGGRAPH_ARCHITECTURE.md
    ├── MCP_TOOLS_FOR_AGENT.md
    ├── STREAMLIT_APP_INTEGRATION.md
    ├── TOOL_EXCLUSION_STRATEGY.md
    ├── TOOL_FLOWS.md
    ├── TOOL_REQUIREMENTS.md
    ├── TROUBLESHOOTING.md
    └── UC_INTEGRATION.md
```

## 🔧 Available Tools (17 Total)

### 📦 Git Repository Management (1 tool)

#### 1. `clone_github_repo` 🆕

**Clone any GitHub repository to Databricks /Repos/ for analysis**

Use this to bring remote repositories into your Databricks workspace. After cloning, use other tools to scan, analyze, or patch the code.

**Args:**
- `git_url` (str): GitHub repository URL (e.g., "https://github.com/org/repo.git")
- `provider` (str): Git provider - "github", "gitLab", "bitbucketCloud", or "azureDevOpsServices" (default: "github")
- `branch` (str): Branch to checkout (default: "main")
- `user_email` (str): User email for repo path (default: "adminuser4510846@vocareum.com")
- `destination_folder` (str): Folder name under /Repos/{user_email}/ (default: "repos")

**Returns:**
Repository information including path, commit hash, and branch.

**Example:**
```python
# Clone a repository
result = clone_github_repo(
    git_url="https://github.com/databricks/databricks-sdk-py.git",
    destination_folder="hackathon_databricks"
)
# Returns: {"repo_path": "/Repos/user@company.com/hackathon_databricks/databricks-sdk-py", ...}

# Then scan it separately
scan_result = scan_repo_dependencies(repo_path=result["repo_path"])
```

**What it does:**
1. ✅ Clones the repository to `/Repos/{user}/{folder}/{repo_name}`
2. ✅ Supports multiple Git providers
3. ✅ Returns repository information for further analysis

**Workflow:**
1. Use `clone_github_repo` to bring code into workspace
2. Use `scan_repo_dependencies` to find dependencies
3. Use `check_vulnerabilities` to identify security issues
4. Use `generate_patch_preview` to see fixes
5. Use `apply_security_patches` to apply them

---

### 🔍 Discovery & Scanning (2 tools)

#### 2. `scan_repo_dependencies`
Scan a Databricks Repo to extract all library dependencies from manifest files.

**Args:**
- `repo_path` (str): Path to Databricks Repo or Workspace folder
- `branch` (str): Git branch to scan (default: "main")

**Returns:**
```json
{
  "packages": {
    "python": {"requests": "2.28.0", "pandas": "1.5.3"},
    "javascript": {"react": "18.2.0"}
  },
  "manifest_files": ["requirements.txt", "package.json"],
  "total_packages": 15
}
```

**Supported Manifests:**
- Python: `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile`
- JavaScript: `package.json`, `package-lock.json`
- Java: `pom.xml`, `build.gradle`
- R: `DESCRIPTION`

#### 3. `list_directory_contents`
Explore repository structure and verify file access (useful for debugging).

### 🛡️ Vulnerability Analysis (2 tools)

#### 4. `check_vulnerabilities`
Check dependencies against OSV.dev vulnerability database (aggregates NVD, GitHub Security, and more).

**Args:**
- `dependencies` (dict): Output from `scan_repo_dependencies`
- `severity_threshold` (str): "low" | "medium" | "high" | "critical"

**Returns:**
```json
{
  "vulnerable_packages_count": 2,
  "vulnerable_packages": [
    {
      "name": "requests",
      "current_version": "2.28.0",
      "recommended_version": "2.31.0",
      "vulnerabilities": [
        {
          "cve_id": "CVE-2023-32681",
          "severity": "high",
          "cvss_score": 7.5,
          "description": "Proxy-Authorization header leak",
          "fixed_versions": ["2.31.0"]
        }
      ]
    }
  ]
}
```

#### 5. `monitor_repo_security`
Full security audit - scans dependencies AND checks vulnerabilities in one step.

### 🔬 Code Impact Analysis (3 tools)

#### 6. `analyze_package_usage`
Analyze how a package is used in the codebase using AST parsing.

**Args:**
- `repo_path` (str): Path to repository
- `package_name` (str): Package to analyze (e.g., "pandas", "requests")
- `specific_file` (str, optional): Analyze only one file

**Returns:**
```json
{
  "package_name": "pandas",
  "imported_as": {"pd": "pandas"},
  "methods_used": ["DataFrame", "read_csv", "concat"],
  "files_with_usage": ["analysis.py", "preprocessing.py"],
  "usage_count": 47
}
```

#### 7. `check_api_changes`
Detect breaking API changes between package versions.

**Args:**
- `package_name` (str): Package name
- `current_version` (str): Current version
- `target_version` (str): Target upgrade version
- `methods_used` (list, optional): Methods to check (from `analyze_package_usage`)

**Returns:**
```json
{
  "package_name": "pandas",
  "current_version": "1.5.3",
  "target_version": "2.0.0",
  "is_breaking": true,
  "breaking_changes": [
    {
      "method": "DataFrame.append",
      "change_type": "removed",
      "description": "Deprecated and removed. Use concat() instead.",
      "severity": "high",
      "migration_guide": "Replace df.append(other) with pd.concat([df, other])"
    }
  ],
  "confidence": 0.92
}
```

**Detection Strategy:**
1. **Curated Database**: Checks known breaking changes for popular packages (pandas, numpy, tensorflow, requests, etc.)
2. **Changelog Analysis**: Fetches and analyzes changelogs from GitHub Releases and PyPI
3. **Semantic Versioning**: Flags major version bumps as potentially breaking

#### 8. `fetch_and_analyze_changelog`
Fetch and analyze package changelogs for breaking changes.

**Sources:**
- GitHub Releases API
- PyPI metadata
- Common changelog files (CHANGELOG.md, HISTORY.md, CHANGES.md)

### 🔧 Patch Generation & Validation (3 tools)

#### 9. `generate_patch_preview`
Generate visual diff preview before applying patches.

**Args:**
- `repo_path` (str): Path to Databricks Repo
- `upgrade_plan` (dict): Packages to upgrade with versions

**Returns:**
```json
{
  "files_to_modify": ["requirements.txt"],
  "file_diffs": [
    {
      "file_path": "requirements.txt",
      "diff_text": "--- a/requirements.txt\n+++ b/requirements.txt\n...",
      "lines_added": 3,
      "lines_removed": 3
    }
  ],
  "visual_diff_html": "<html>...",
  "impact_summary": {
    "total_changes": 6,
    "breaking_changes": 0
  }
}
```

#### 10. `apply_security_patches`
Apply approved security patches to the repository.

**Args:**
- `repo_path` (str): Path to Databricks Repo
- `upgrade_plan` (dict): Approved upgrade plan
- `create_branch` (bool): Create new branch (default: true)
- `branch_name` (str): Branch name (default: "security-patches-{timestamp}")

**Returns:**
```json
{
  "status": "success",
  "branch_name": "security-patches-20260203",
  "files_modified": ["requirements.txt"],
  "packages_upgraded": 3,
  "commit_message": "Security: Upgrade vulnerable packages"
}
```

**Safety Features:**
- ✅ Never modifies main/master branch directly
- ✅ Always creates a new branch
- ✅ Includes descriptive commit messages
- ✅ Preserves original manifest formatting

#### 11. `validate_patch_with_tests`
Apply patch to test branch and run test suite.

**Args:**
- `repo_path` (str): Path to repository
- `branch_name` (str): Branch with patches to test

**Returns:**
```json
{
  "is_valid": true,
  "tests_pass": true,
  "test_summary": "47 passed, 0 failed",
  "errors": []
}
```

### ☕ Java Code Analysis (1 tool)

#### 12. `analyze_java_repos_from_uc` 🆕

**Analyze Java repositories using temporary cloning and javalang AST parsing**

Reads repo URLs from Unity Catalog, clones them to temporary directories (auto-cleanup), parses Java code with `javalang` to extract method calls and structure, then writes comprehensive analysis back to UC.

**What it finds:**
- Class/interface/enum structures
- Method invocations (API calls) with caller context
- Package organization
- Line-by-line usage tracking

**Args:**
- `catalog` (str): UC catalog name (default: "main")
- `schema` (str): UC schema name (default: "security")
- `table` (str): UC table with repos to scan (default: "java_repos_to_scan")

**UC Table Schema Required:**
```sql
CREATE TABLE {catalog}.{schema}.{table} (
  repo_url STRING,     -- Git URL
  ref STRING,          -- Branch/tag/commit
  repo_name STRING     -- Human-readable name
);
```

**Returns:**
```json
{
  "status": "success",
  "repos_analyzed": 5,
  "total_java_files": 2847,
  "total_method_calls": 45632,
  "results": [...]
}
```

**Use cases:**
- 🔒 **Security audits**: Find which vulnerable APIs are actually used (e.g., Log4j)
- 📊 **Migration planning**: Identify method usage before library upgrades
- 🔍 **Dependency analysis**: Map API usage across Java codebase

**Example:**
```python
# Agent workflow
result = analyze_java_repos_from_uc(
    catalog="production",
    schema="security_audit",
    table="vulnerable_java_apps"
)

# Results written to: production.security_audit.java_analysis_results
# Query: Which repos use javax.servlet?
```

**Key Features:**
- ✅ **Temporary cloning**: No workspace pollution, automatic cleanup
- ✅ **No JVM required**: Pure Python `javalang` parser
- ✅ **AST-based**: Accurate method call extraction
- ✅ **UC integration**: Read repos from table, write results back

**See also:** [docs/JAVA_ANALYSIS.md](./docs/JAVA_ANALYSIS.md) for complete documentation

---

### 🗄️ Unity Catalog Integration (3 tools)

For production deployments with centralized tracking and audit trails.

#### 13. `get_sca_findings_from_uc`
Fetch vulnerable repositories from Unity Catalog table.

**Args:**
- `catalog` (str): UC catalog name (default: from config)
- `schema` (str): UC schema name (default: from config)
- `table` (str): UC table name (default: from config)
- `priority` (int, optional): Filter by priority (1=Critical, 2=High, 3=Medium)

**Returns:** List of vulnerable repositories with package details.

#### 14. `write_analysis_to_uc`
Write analysis results to Unity Catalog for tracking.

**Args:**
- `repo_id` (str): Repository identifier
- `analysis_results` (dict): Results from code analysis and API checks

**Returns:** Confirmation with analysis ID.

#### 15. `record_user_decision_to_uc`
Record user approval/rejection decisions for audit trail.

**Args:**
- `repo_id` (str): Repository identifier
- `decision` (str): "approved" or "rejected"
- `target_version` (str): Version being upgraded to
- `reason` (str, optional): Decision reasoning

**Returns:** Confirmation with decision ID.

### 📊 Additional Utilities (2 tools)

#### 16. `get_vulnerability_details`
Fetch detailed information about a specific CVE.

#### 17. `suggest_upgrades`
Recommend safe upgrade paths based on vulnerability report (internal use by agents).

---

## 📖 Example Workflows

### ⚡ NEW: Clone and Scan Remote Repository

```
User: "Scan this repo for vulnerabilities: https://github.com/databricks-industry-solutions/ray-framework-on-databricks"

Agent:
  → clone_github_repo(git_url, destination_folder="security_scans")
  → scan_repo_dependencies(repo_path)
  → check_vulnerabilities(dependencies)
  
Response: "✅ Cloned ray-framework-on-databricks to /Repos/user@company.com/security_scans/ray-framework-on-databricks
           
           Scan results: Found 15 packages, 2 with vulnerabilities:
           - ray 2.0.0 → CVE-2023-xxxxx (HIGH)
           - requests 2.28.0 → CVE-2023-32681 (HIGH)
           
           Would you like me to analyze the code impact?"
```

**Workflow benefits:**
- ✅ Separate concerns: clone once, analyze multiple times
- ✅ Keep repositories for manual inspection
- ✅ Flexibility in choosing which analyses to run

---

### Quick Security Scan (Existing Repo)

```
User: "Check /Workspace/Users/me/my-project for vulnerabilities"

Agent:
  → scan_repo_dependencies(repo_path)
  → check_vulnerabilities(dependencies)
  
Response: "Found 2 HIGH severity vulnerabilities in requests and urllib3.
           Would you like me to analyze the code impact?"
```

### Deep Analysis with Breaking Change Detection

```
User: "Analyze impact of upgrading pandas"

Agent:
  → scan_repo_dependencies(repo_path)
  → check_vulnerabilities(dependencies)
  → analyze_package_usage(repo_path, "pandas")
  → check_api_changes("pandas", "1.5.3", "2.0.0", methods_used)
  
Response: "Upgrade to pandas 2.0.0 fixes 1 vulnerability but has 2 breaking changes:
           - DataFrame.append() removed (use concat())
           - Used in 5 files, 23 call sites affected
           Would you like to see the patch preview?"
```

### Full Remediation with Testing

```
User: "Fix all vulnerabilities and test"

Agent:
  → scan_repo_dependencies(repo_path)
  → check_vulnerabilities(dependencies)
  → analyze_package_usage(...) for each vulnerable package
  → check_api_changes(...) for each upgrade
  → generate_patch_preview(repo_path, upgrade_plan)
  → [User approves]
  → apply_security_patches(repo_path, upgrade_plan)
  → validate_patch_with_tests(repo_path, branch_name)
  
Response: "✅ Applied patches to branch 'security-patches-20260203'
           ✅ All 47 tests passed
           Ready to merge to main!"
```

### Production UC Workflow

```
Agent (automated):
  → get_sca_findings_from_uc(priority=1)  # Critical only
  → For each repo:
      - scan_repo_dependencies(repo_path)
      - analyze_package_usage(...) for each vulnerable package
      - check_api_changes(...) for each upgrade
      - write_analysis_to_uc(repo_id, results)
  
User reviews in Databricks App UI, approves fix

Agent:
  → record_user_decision_to_uc(repo_id, "approved")
  → apply_security_patches(repo_path, upgrade_plan)
  → validate_patch_with_tests(repo_path, branch_name)
```

---

## 🌐 Deployment to Databricks

### Deploy as Databricks App

```bash
# Navigate to project directory
cd /path/to/vulnerability-scanner-mcp

# Authenticate with Databricks (use valid profile)
databricks auth login --profile your-profile

# Create the app (requires 'mcp-' prefix for AI Playground discovery)
databricks apps create mcp-vulnerability-scanner --profile your-profile

# Upload source code to Workspace
databricks workspace import-dir . /Workspace/Users/you@company.com/mcp-vulnerability-scanner --profile your-profile

# Deploy the app
databricks apps deploy mcp-vulnerability-scanner \
  --source-code-path /Workspace/Users/you@company.com/mcp-vulnerability-scanner \
  --profile your-profile

# Check status
databricks apps get mcp-vulnerability-scanner --profile your-profile

# View logs
databricks apps logs mcp-vulnerability-scanner --profile your-profile
```

See **[docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md)** for detailed deployment options and troubleshooting.

### Configure in AI Playground

1. Navigate to **AI Playground** in Databricks
2. Select a model with **Tools enabled**
3. Click **Tools > + Add tool**
4. Select your deployed MCP server: `mcp-vulnerability-scanner`
5. Start chatting - the agent will automatically use your tools!

### MCP Endpoint

Once deployed, your MCP endpoint will be:
```
https://<workspace>.databricks.com/serving-endpoints/mcp-vulnerability-scanner/mcp/v1/
```

---

## 🤖 Agent Configuration

For comprehensive guidance on configuring AI agents to work with this MCP server, including:

- ✨ Best practices for agent-friendly tool descriptions
- 🎤 Complete system prompts for OpenAI SDK agents
- 🔄 4 execution flow patterns (quick scan → full UC integration)
- ✅ Testing and validation guidelines

See **[docs/AGENT_CONFIGURATION.md](./docs/AGENT_CONFIGURATION.md)**

---

## 🔐 Authentication

### Local Development
- Uses Databricks CLI authentication from `~/.databrickscfg`
- Set profile with `DATABRICKS_CONFIG_PROFILE` environment variable
- Default profile is used if not specified

```bash
# Configure auth
databricks auth login --profile your-profile

# Use profile
export DATABRICKS_CONFIG_PROFILE=your-profile
./scripts/dev/start_server.sh
```

### Deployed as Databricks App
- **App Authentication** (`get_workspace_client()`): Service principal with app-level access
- **User Authentication** (`get_user_authenticated_workspace_client()`): End user OAuth token for user-specific operations
- User token extracted from `x-forwarded-access-token` header

Most tools use app-level authentication for reliability and consistency.

---

## 🗄️ Unity Catalog Integration

For production deployments, integrate with Unity Catalog for:

- 📊 Centralized vulnerability tracking
- 🔄 Automated scanning workflows
- ✅ Audit trails for all decisions
- 📈 Reporting and compliance

See **[docs/UC_INTEGRATION.md](./docs/UC_INTEGRATION.md)** for complete setup guide including:
- Unity Catalog table schemas
- Agent model registration
- Production workflow examples

---

## 📦 Key Dependencies

- **fastmcp**: MCP server framework
- **fastapi**: Async web framework
- **uvicorn**: ASGI server with uvloop
- **databricks-sdk**: Databricks API client
- **pyspark**: Unity Catalog integration
- **aiohttp**: Async HTTP for API calls (OSV.dev, PyPI, npm, Maven)
- **pygments**: Syntax highlighting for diffs
- **packaging**: Semantic version comparison
- **tomli**: TOML parser for pyproject.toml

---

## 🧪 Development

### Run Tests

```bash
# All tests
uv run pytest tests/

# Specific test
uv run pytest tests/test_integration.py::test_list_tools -v

# With coverage
uv run pytest tests/ --cov=server --cov=services
```

### Code Formatting

```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .
```

### Local Testing Without Databricks

```bash
# Test server health and tool listing (no auth required)
python scripts/dev/test_local.py
```

---

## 🎯 Why API-First Approach?

**Traditional Approach (❌):**
- Download full package files (MB/GB)
- Store packages locally
- Slow comparisons
- Storage management overhead
- Stale data

**Our Approach (✅):**
- Query package registry APIs (PyPI, npm, Maven)
- Fetch only metadata (KB)
- Instant lookups
- No storage needed
- Always up-to-date
- Changelog analysis from source

**APIs Used:**
- **OSV.dev**: Vulnerability database (aggregates NVD, GitHub Security Advisory, etc.)
- **PyPI JSON API**: Python package metadata and changelogs
- **npm Registry**: JavaScript package metadata
- **Maven Central**: Java package metadata
- **GitHub Releases API**: Release notes and changelogs
- **Databricks Repos API**: Git operations in Databricks

---

## 📚 Resources

- [Databricks Custom MCP Documentation](https://docs.databricks.com/aws/en/generative-ai/mcp/custom-mcp)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Model Context Protocol Specification](https://modelcontextprotocol.io)
- [OSV.dev API Documentation](https://osv.dev/docs/)
- [Databricks Apps](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/)
- [Unity Catalog](https://docs.databricks.com/data-governance/unity-catalog/index.html)

---

## 🤝 Contributing

We welcome contributions! See [docs/CONTRIBUTING.md](./docs/CONTRIBUTING.md) for:

- Development setup
- Code style guidelines
- Testing requirements
- Pull request process
- Areas for contribution

**Ideas for contributions:**
- Support for additional ecosystems (Go, Rust, PHP, Ruby)
- Integration with Snyk, GitHub Advisory Database
- Automated PR creation via Git provider APIs
- SBOM generation
- Compliance reporting (SOC2, HIPAA)

---

## 🆘 Troubleshooting

### Common Issues

**Port Already in Use:**
```bash
uv run python -m server.main --port 8080
```

**Import Errors:**
```bash
uv sync --reinstall
```

**Authentication Errors (Local):**
```bash
databricks auth login --profile your-profile
export DATABRICKS_CONFIG_PROFILE=your-profile
```

**Deployment Errors:**
```bash
# Check app logs
databricks apps logs mcp-vulnerability-scanner --profile your-profile

# Check app status
databricks apps get mcp-vulnerability-scanner --profile your-profile
```

See **[docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md)** for comprehensive troubleshooting guide.

---

## 📄 License

Licensed under the Apache License 2.0. See [LICENSE](./LICENSE) for details.

---

## 📝 Changelog

See [docs/CHANGELOG.md](./docs/CHANGELOG.md) for version history and release notes.

---

**Built with ❤️ for secure software supply chains**

**Current Version**: 1.0.0 | **MCP Protocol**: 1.0 | **Python**: 3.11+
