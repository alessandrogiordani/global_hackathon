# Contributing to Vulnerability Scanner MCP

Thank you for your interest in contributing to the Vulnerability Scanner MCP Server! This guide will help you get started.

## 🛠️ Development Setup

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Git
- Databricks workspace (for testing deployment)

### Local Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd vulnerability-scanner-mcp
   ```

2. **Install dependencies**
   ```bash
   uv sync
   # or with pip
   pip install -r requirements.txt
   ```

3. **Start the development server**
   ```bash
   ./scripts/dev/start_server.sh
   # or
   uv run python -m server.main
   ```

4. **Run tests**
   ```bash
   uv run pytest tests/
   ```

## 📝 Code Style

We follow Python best practices and use automated formatting:

### Formatting

```bash
# Format all code
uv run ruff format .

# Check for issues
uv run ruff check .

# Auto-fix issues where possible
uv run ruff check --fix .
```

### Code Guidelines

- **Type hints**: Use type hints for function parameters and return values
- **Docstrings**: Write clear docstrings for all public functions and classes
- **Error handling**: Handle errors gracefully with descriptive messages
- **Async/await**: Use async functions for I/O operations (API calls, file operations)
- **Logging**: Use structured logging with appropriate levels (DEBUG, INFO, WARNING, ERROR)

## 🧪 Testing

### Running Tests

```bash
# All tests
uv run pytest tests/

# Specific test file
uv run pytest tests/test_integration.py

# Specific test with verbose output
uv run pytest tests/test_integration.py::test_list_tools -v

# Local server test
python scripts/dev/test_local.py
```

### Writing Tests

- Add tests for new features in `tests/`
- Test both success and error cases
- Mock external API calls (OSV.dev, PyPI, npm, etc.)
- Use pytest fixtures for common setup

## 🔧 Project Structure

```
vulnerability-scanner-mcp/
├── server/              # MCP server core
│   ├── app.py          # FastAPI + FastMCP setup
│   ├── main.py         # Entry point
│   ├── tools.py        # MCP tool definitions
│   └── utils.py        # Auth & helpers
├── services/           # Business logic
│   ├── code_analyzer.py          # Dependency extraction
│   ├── vulnerability_scanner.py  # OSV.dev API client
│   ├── package_registry.py       # PyPI/npm/Maven APIs
│   ├── static_analyzer.py        # AST parsing
│   ├── changelog_fetcher.py      # Changelog retrieval
│   ├── api_changelog_analyzer.py # Breaking change detection
│   ├── diff_generator.py         # Patch visualization
│   ├── git_client.py             # Databricks Repos API
│   ├── llm_analyzer.py           # LLM-based analysis
│   └── uc_integration.py         # Unity Catalog integration
├── models/             # Pydantic models
│   ├── package.py      # Package-related models
│   ├── vulnerability.py # Vulnerability models
│   └── usage.py        # Usage analysis models
└── tests/              # Test suite
```

## 🎯 Making Changes

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

- Follow the code style guidelines
- Add tests for new functionality
- Update documentation if needed
- Keep commits focused and descriptive

### 3. Test Your Changes

```bash
# Run tests
uv run pytest tests/

# Test locally
./scripts/dev/start_server.sh
python scripts/dev/test_local.py
```

### 4. Format and Lint

```bash
uv run ruff format .
uv run ruff check --fix .
```

### 5. Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature description"
```

Use conventional commit messages:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test changes
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear description of changes
- Reference to any related issues
- Screenshots/examples if applicable

## 🐛 Reporting Issues

When reporting issues, please include:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**: Exact steps to reproduce the problem
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Environment**: Python version, OS, Databricks workspace details
6. **Logs**: Relevant error messages or logs

## 💡 Feature Requests

We welcome feature requests! Please:

1. Check existing issues first
2. Provide a clear use case
3. Explain the expected behavior
4. Consider implementation complexity

## 🌟 Areas for Contribution

Here are some areas where we'd love contributions:

### New Features
- Support for additional ecosystems (Go, Rust, PHP, Ruby)
- Integration with additional vulnerability databases (Snyk, GitHub Advisory)
- Custom notification channels (Slack, Microsoft Teams, PagerDuty)
- Automated PR creation via Git provider APIs (GitHub, GitLab, Bitbucket)
- SBOM (Software Bill of Materials) generation
- Compliance reporting (SOC2, HIPAA, etc.)

### Improvements
- Enhanced breaking change detection with more heuristics
- Better changelog parsing for complex formats
- Performance optimizations for large repositories
- More comprehensive test coverage
- Documentation improvements

### Bug Fixes
- Check the issue tracker for known bugs
- Test edge cases and error scenarios

## 📚 Resources

- **Databricks Custom MCP**: https://docs.databricks.com/aws/en/generative-ai/mcp/custom-mcp
- **FastMCP Documentation**: https://github.com/jlowin/fastmcp
- **MCP Specification**: https://modelcontextprotocol.io
- **OSV.dev API**: https://osv.dev/docs/
- **Databricks Apps**: https://docs.databricks.com/aws/en/dev-tools/databricks-apps/

## ❓ Questions?

- Check the [README.md](../README.md) for general information
- See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues
- Open an issue for specific questions

## 📄 License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

---

Thank you for contributing! 🎉

