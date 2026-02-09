# Changelog

All notable changes to the Vulnerability Scanner MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-03

### Added

#### Core Features
- **15 MCP tools** for comprehensive vulnerability scanning and remediation
- **Multi-ecosystem support**: Python, JavaScript, Java, and R package ecosystems
- **OSV.dev integration**: Real-time vulnerability checking against aggregated CVE databases
- **API-first approach**: No package downloads required, uses registry APIs (PyPI, npm, Maven)

#### Discovery & Scanning (2 tools)
- `scan_repo_dependencies`: Extract dependencies from manifest files (requirements.txt, pyproject.toml, package.json, pom.xml, DESCRIPTION)
- `list_directory_contents`: Explore repository structure for debugging

#### Vulnerability Analysis (2 tools)
- `check_vulnerabilities`: Check packages against OSV.dev vulnerability database
- `monitor_repo_security`: Full security audit with continuous monitoring setup

#### Code Impact Analysis (3 tools)
- `analyze_package_usage`: AST-based analysis to find how packages are used in source code
- `check_api_changes`: Detect breaking API changes in package upgrades using curated database
- `fetch_and_analyze_changelog`: Fetch and analyze changelogs from GitHub/PyPI for breaking changes

#### Patch Generation & Validation (3 tools)
- `generate_patch_preview`: Generate visual diffs showing required changes before applying
- `apply_security_patches`: Apply patches to new Git branches (never modifies main)
- `validate_patch_with_tests`: Apply patches to test branch and run test suite for validation

#### Unity Catalog Integration (3 tools)
- `get_sca_findings_from_uc`: Fetch vulnerable repositories from UC tables
- `write_analysis_to_uc`: Store analysis results for tracking and reporting
- `record_user_decision_to_uc`: Record approval/rejection decisions for audit trail

#### Additional Features
- **Breaking change detection**: Multi-tiered approach using curated database + changelog analysis
- **Smart changelog fetching**: Retrieves from GitHub Releases, PyPI, and common changelog files
- **LLM-enhanced analysis**: Optional LLM-based breaking change extraction from changelogs
- **Visual diff generation**: Color-coded HTML diffs for patch previews
- **Git integration**: Seamless Databricks Repos API integration
- **Authentication**: Dual authentication mode (app-level and user-level) for Databricks Apps

### Documentation
- Comprehensive `README.md` with quick start and tool reference
- **Agent Configuration Guide** (`AGENT_CONFIGURATION.md`) with:
  - Best practices for agent-friendly tool design
  - Complete system prompt for OpenAI SDK agents
  - 4 execution flow patterns (quick scan, deep analysis, full remediation, UC integration)
  - Testing and validation guidelines
- **Deployment Guide** (`docs/DEPLOYMENT.md`) for Databricks Apps
- **Troubleshooting Guide** (`docs/TROUBLESHOOTING.md`) for common issues
- **Unity Catalog Integration** (`docs/UC_INTEGRATION.md`) for production workflows
- `CONTRIBUTING.md` with development setup and contribution guidelines
- `LICENSE` (Apache 2.0)

### Technical Improvements
- **Async architecture**: Full async/await support for I/O operations
- **Pydantic v2**: Modern data validation with comprehensive models
- **ThreadPoolExecutor**: Resolved asyncio event loop conflicts in FastAPI/uvloop
- **Comprehensive error handling**: Graceful error messages for authentication, file access, and API failures
- **Extensive logging**: Debug-level logging for troubleshooting file access and parsing issues

### Deployment
- **Databricks Apps support**: Ready for deployment as a Databricks App
- **MCP protocol**: Full Model Context Protocol compliance for AI agent integration
- **FastMCP + FastAPI**: Modern async web framework with MCP capabilities
- **Health checks**: Built-in health endpoint for monitoring

### Testing
- Integration test suite with pytest
- Local testing script for development
- Mock data support for testing without Databricks workspace

## [Unreleased]

### Planned Features
- Support for additional ecosystems (Go, Rust, PHP, Ruby)
- Integration with Snyk and GitHub Advisory Database
- Automated PR creation via Git provider APIs
- SBOM (Software Bill of Materials) generation
- Custom notification channels (Slack, Teams, PagerDuty)
- Enhanced LLM-based changelog analysis with GPT-4/Claude integration
- Compliance reporting (SOC2, HIPAA, ISO 27001)

---

## Release Notes Format

Each release follows this structure:

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes

---

**Current Version**: 1.0.0  
**Last Updated**: 2026-02-03

