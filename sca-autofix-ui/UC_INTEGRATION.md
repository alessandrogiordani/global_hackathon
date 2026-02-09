# 🔗 Unity Catalog Integration Guide

Production setup guide for integrating the SCA Vulnerabilities Scanning app with Unity Catalog and MCP tools.

---

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Checkmarx SCA Scanner (External)                │
│            Detects vulnerable libraries in repos             │
└────────────────────────┬────────────────────────────────────┘
                         │ Findings
                         ▼
┌─────────────────────────────────────────────────────────────┐
│        Unity Catalog: sca_findings (Delta Table)         │
│   One row per repo with vuln libs & candidate versions      │
└────────────────────────┬────────────────────────────────────┘
                         │ Query
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            SCA Vulnerabilities Scanning App                  │
│              (Streamlit UI - this project)                   │
└────────────────────────┬────────────────────────────────────┘
                         │ Call agent
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         UC Model: fix_advisor_agent (Claude)                 │
│    Analyzes code changes for each candidate version         │
└────────────────────────┬────────────────────────────────────┘
                         │ Uses MCP tools (automatically)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Custom MCP Servers (Tools)                      │
│  - Code Analyzer MCP     - Compatibility Checker MCP        │
│  - Patch Generator MCP   - Patch Validator MCP              │
└────────────────────────┬────────────────────────────────────┘
                         │ Check vulnerabilities
                         ▼
┌─────────────────────────────────────────────────────────────┐
│      CVE: Common Vulnerabilities and Exposures              │
│         (Open source vulnerability database)                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗄️ Step 1: Create Unity Catalog Structure

### 1.1 Create Catalog and Schema

```sql
-- Create catalog
CREATE CATALOG IF NOT EXISTS ing_hackathon;
USE CATALOG ing_hackathon;

-- Create schema
CREATE SCHEMA IF NOT EXISTS ing_hackathon
  COMMENT 'SCA Vulnerabilities Scanning - Automated vulnerability remediation';
```

### 1.2 Create Main Table (Vulnerable Repos)

```sql
```sql
CREATE TABLE IF NOT EXISTS ing_hackathon.ing_hackathon.sca_findings (
  repo_path STRING NOT NULL,
  library STRING NOT NULL,
  current_version STRING NOT NULL,
  repo_name STRING NOT NULL,
  repo_url STRING NOT NULL,
  priority STRING NOT NULL,        -- 'Critical', 'High', 'Medium', 'Low', 'Informational'
  cve_ids ARRAY<STRING>,
  cvss_score DOUBLE,
  candidate_versions ARRAY<STRUCT<
    version: STRING,
    release_date: TIMESTAMP,           -- When this version was released
    vulnerability_count: INT,          -- Number of known vulnerabilities in this version from Checkmarx
    detected_ts: TIMESTAMP             -- When this candidate version was detected/added
  >>,
  last_detected_ts TIMESTAMP,
  status STRING,                   -- 'ready', 'analyzing', 'approved', 'rejected'
  checkmarx_finding_id STRING,
  owner_team STRING,
  CONSTRAINT pk_repos PRIMARY KEY (repo_path, library)
)
COMMENT 'Vulnerable libraries (one row per repo + library)'
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');
```

### 1.3 Create Results Table (Agent Analysis)

```sql
CREATE TABLE IF NOT EXISTS ing_hackathon.ing_hackathon.agent_analysis_results (
  analysis_id STRING NOT NULL,
  repo_path STRING NOT NULL,
  library STRING NOT NULL,
  target_version STRING NOT NULL,
  code_changes_files INT,
  code_changes_lines INT,
  impacted_files ARRAY<STRING>,
  analysis_ts TIMESTAMP,
  patch_content STRING,
  CONSTRAINT pk_analysis PRIMARY KEY (analysis_id)
)
COMMENT 'Agent analysis results for library upgrades';
```

### 1.4 Create Audit Table (User Decisions)

```sql
CREATE TABLE IF NOT EXISTS ing_hackathon.ing_hackathon.user_decisions (
  decision_id STRING NOT NULL,
  repo_id STRING NOT NULL,
  library STRING NOT NULL,         -- Which library the decision is for
  target_version STRING NOT NULL,
  decision STRING NOT NULL,        -- 'approved', 'rejected'
  user_email STRING NOT NULL,
  decision_reason STRING,
  decision_ts TIMESTAMP,
  CONSTRAINT pk_decisions PRIMARY KEY (decision_id)
)
COMMENT 'Audit log of user decisions per library';
```

---

## 🤖 Step 2: Register Agent Model

### 2.1 Develop Agent with MCP Tools in Playground

**Note:** Agent model choice is TBD. This example shows the general pattern.

```python
# In Databricks Playground

# MCP servers will run on the same cluster (localhost)
# Databricks automatically handles internal networking
mcp_servers = {
    "code_analyzer": "http://localhost:8000",
    "compatibility_checker": "http://localhost:8001",
    "patch_generator": "http://localhost:8002",
    "patch_validator": "http://localhost:8003"
}

# Initialize your chosen LLM (model TBD - could be Claude, GPT-4, etc.)
# Example with generic pattern:

system_prompt = """
You are a code vulnerability remediation expert.

Available tools (via MCP):
- analyze_code_changes: Analyze code impact of library upgrades
- check_compatibility: Check if library version is safe (uses CVE database)
- generate_patch: Create patches for code changes
- validate_patch: Test if patches apply cleanly

Goal: Recommend the best upgrade path with minimal code changes.
"""

# Test agent with a query
# Specific implementation depends on chosen model
test_input = {
    "repo_id": "payment-gateway-api",
    "library": "requests",
    "current_version": "2.6.0",
    "candidate_versions": ["2.31.0", "2.28.0"]
}

# Agent will call MCP tools automatically based on the task
```

### 2.2 Register Model in UC

```python
import mlflow

# Register your trained agent model
# Model framework depends on your choice (LangChain, custom, etc.)

with mlflow.start_run():
    logged_agent_info = mlflow.pyfunc.log_model(
        artifact_path="fix_advisor_agent",
        registered_model_name="ing_hackathon.ing_hackathon.fix_advisor_agent",
        python_model=your_agent_model,  # Your agent implementation
        input_example={
            "repo_id": "repo_001",
            "library": "requests",
            "current_version": "2.6.0",
            "candidate_versions": ["2.31.0", "2.28.0"]
        }
    )

print(f"Agent registered: {logged_agent_info.model_uri}")
```

---

## 🔧 Step 3: Create & Deploy MCP Servers

**Why MCP?** Industry standard (Anthropic-backed), native Claude integration, flexible Python services.

### 3.0 Git Repository Access Setup

Before the MCP servers can analyze code, they need access to clone repositories:

```python
# mcp_git_utils.py - Shared utility for all MCP servers

import git
import os
import tempfile
from typing import Optional

class RepoManager:
    """Manages git repository cloning and access for MCP servers."""
    
    def __init__(self, clone_base_dir: str = "/tmp/mcp_repos"):
        self.clone_base_dir = clone_base_dir
        os.makedirs(clone_base_dir, exist_ok=True)
    
    def get_repo(self, repo_url: str, repo_id: str) -> str:
        """
        Clone or update repository and return local path.
        
        Args:
            repo_url: Git URL (e.g., https://github.com/ing/repo.git)
            repo_id: Unique repo identifier for caching
            
        Returns:
            Local path to cloned repository
        """
        repo_path = os.path.join(self.clone_base_dir, repo_id)
        
        if os.path.exists(repo_path):
            # Repo already cloned, pull latest
            repo = git.Repo(repo_path)
            repo.remotes.origin.pull()
            print(f"Updated existing repo: {repo_id}")
        else:
            # Clone fresh
            git.Repo.clone_from(repo_url, repo_path)
            print(f"Cloned new repo: {repo_id}")
        
        return repo_path
    
    def cleanup_repo(self, repo_id: str):
        """Remove cloned repository to save space."""
        repo_path = os.path.join(self.clone_base_dir, repo_id)
        if os.path.exists(repo_path):
            import shutil
            shutil.rmtree(repo_path)

# Git Authentication Options:
# 1. GitHub Token: export GIT_TOKEN="ghp_xxxxx"
#    Clone URL: https://token@github.com/org/repo.git
# 
# 2. SSH Key: Use SSH URLs with key-based auth
#    Clone URL: git@github.com:org/repo.git
#    Ensure SSH key is in ~/.ssh/
#
# 3. Databricks Repos: For repos already in Databricks
#    Access directly via /Workspace/Repos/user/repo_name
```

### 3.1 MCP Server: Code Analyzer

```python
# mcp_code_analyzer.py

from mcp.server import Server
from mcp_git_utils import RepoManager
import ast
import os

app = Server("code-analyzer")
repo_manager = RepoManager()

@app.tool()
def analyze_code_changes(
    repo_url: str,
    repo_id: str,
    library: str,
    current_version: str,
    target_version: str
) -> dict:
    """
    Analyzes code changes needed for library upgrade.
    
    Args:
        repo_url: Git repository URL
        repo_id: Unique repository identifier
        library: Library name (e.g., 'requests')
        current_version: Current library version
        target_version: Target upgrade version
    
    Returns:
        files_changed: Number of files to modify
        callsites_modified: Number of call sites
        breaking_changes: List of breaking changes
        confidence: Confidence score (0-1)
    """
    # Clone/update repository
    repo_path = repo_manager.get_repo(repo_url, repo_id)
    
    # Find library usage
    callsite_count = 0
    affected_files = []
    
    for root, dirs, files in os.walk(repo_path):
        # Skip virtual environments and dependencies
        dirs[:] = [d for d in dirs if d not in ['venv', '.venv', 'node_modules', '__pycache__']]
        
        for file in files:
            if file.endswith(('.py', '.js', '.java')):  # Support multiple languages
                file_path = os.path.join(root, file)
                # Parse and find library usages
                if library_used_in_file(file_path, library):
                    affected_files.append(file_path)
                    callsite_count += count_callsites(file_path, library)
    
    # Compare API changes between versions
    # Query package registry or use known breaking changes database
    breaking_changes = get_api_breaking_changes(library, current_version, target_version)
    
    # Calculate confidence
    confidence = 0.95 if len(breaking_changes) == 0 else 0.75
    
    return {
        "files_changed": len(affected_files),
        "callsites_modified": callsite_count,
        "breaking_changes": breaking_changes,
        "confidence": confidence,
        "affected_file_paths": affected_files
    }

def library_used_in_file(file_path: str, library: str) -> bool:
    """Check if library is imported/used in file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Python imports
        if file_path.endswith('.py'):
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if library in alias.name:
                                return True
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and library in node.module:
                            return True
            except SyntaxError:
                pass
        
        # JavaScript/Java - simple text search (can be improved with parsers)
        elif file_path.endswith(('.js', '.java')):
            return f"import {library}" in content or f"require('{library}')" in content
        
        return False
    except Exception:
        return False

def count_callsites(file_path: str, library: str) -> int:
    """Count number of times library functions are called."""
    # Simplified - count occurrences (can use AST for more accuracy)
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        return content.count(f"{library}.")
    except Exception:
        return 0

def get_api_breaking_changes(library: str, old_version: str, new_version: str) -> list:
    """
    Get breaking changes between versions.
    Could query:
    - Package changelog
    - Libraries.io API
    - GitHub releases
    - Known breaking changes database
    """
    # Placeholder - implement actual API or database lookup
    breaking_changes_db = {
        ('requests', '2.6.0', '2.31.0'): [
            'Session.request() now requires timeout parameter',
            'verify=False deprecated, use explicit SSL context'
        ],
        ('django', '2.2.10', '3.2.13'): [
            'django.conf.urls.url() removed, use django.urls.path()',
            'Signal.disconnect() requires sender parameter'
        ]
    }
    
    return breaking_changes_db.get((library, old_version, new_version), [])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

### 3.2 MCP Server: Compatibility Checker

```python
# mcp_compatibility_checker.py

from mcp.server import Server
import requests

app = Server("compatibility-checker")

@app.tool()
def check_compatibility(library: str, version: str) -> dict:
    """
    Checks if library version is safe using CVE database.
    
    Returns:
        has_vulnerabilities: Whether version has CVEs
        cve_ids: List of CVE IDs
        is_compatible: Overall safety verdict
    """
    # Check CVE database
    cve_response = requests.get(
        f"https://cve.mitre.org/cgi-bin/cvekey.cgi",
        params={"keyword": f"{library} {version}"}
    )
    
    # Parse CVE results
    cves = parse_cve_results(cve_response.text, library, version)
    
    # Check version age from package registry (PyPI, npm, etc.)
    release_info = get_package_info(library, version)
    is_too_old = check_if_deprecated(release_info)
    is_too_new = check_if_unstable(release_info)
    
    return {
        "has_vulnerabilities": len(cves) > 0,
        "cve_ids": cves,
        "is_too_old": is_too_old,
        "is_too_new": is_too_new,
        "is_compatible": len(cves) == 0 and not is_too_old and not is_too_new
    }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
```

### 3.3 MCP Server: Patch Generator

```python
# mcp_patch_generator.py

from mcp.server import Server
from mcp_git_utils import RepoManager
from difflib import unified_diff
import os

app = Server("patch-generator")
repo_manager = RepoManager()

@app.tool()
def generate_patch(
    repo_url: str,
    repo_id: str,
    library: str,
    old_version: str,
    new_version: str,
    changes: list[dict]
) -> str:
    """
    Generates unified diff patch file.
    
    Args:
        repo_url: Git repository URL
        repo_id: Unique repository identifier
        library: Library being upgraded
        changes: [{"file": "path", "old_content": "...", "new_content": "..."}]
    
    Returns:
        patch_content: Unified diff as string
    """
    # Clone/update repository (for context)
    repo_path = repo_manager.get_repo(repo_url, repo_id)
    
    patch_lines = []
    
    for change in changes:
        file_path = change['file']
        old_lines = change['old_content'].splitlines(keepends=True)
        new_lines = change['new_content'].splitlines(keepends=True)
        
        diff = unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm='\n'
        )
        patch_lines.extend(diff)
    
    return ''.join(patch_lines)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8002)
```

### 3.4 MCP Server: Patch Validator

```python
# mcp_patch_validator.py

from mcp.server import Server
from mcp_git_utils import RepoManager
import subprocess
import git
import tempfile
import os

app = Server("patch-validator")
repo_manager = RepoManager()

@app.tool()
def validate_patch(
    repo_url: str,
    repo_id: str,
    patch_content: str
) -> dict:
    """
    Validates that patch applies cleanly and tests pass.
    
    Args:
        repo_url: Git repository URL
        repo_id: Unique repository identifier
        patch_content: Patch to validate
    
    Returns:
        is_valid: Patch is valid
        applies_cleanly: No conflicts
        tests_pass: Tests pass after patch
        errors: List of errors
    """
    errors = []
    
    # Clone/update repository
    repo_path = repo_manager.get_repo(repo_url, repo_id)
    repo = git.Repo(repo_path)
    
    # Create test branch
    test_branch_name = f"test-patch-{os.getpid()}"
    test_branch = repo.create_head(test_branch_name)
    original_branch = repo.active_branch
    test_branch.checkout()
    
    # Try to apply patch
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
            f.write(patch_content)
            patch_file = f.name
        
        result = subprocess.run(
            ['git', 'apply', '--check', patch_file],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        applies_cleanly = result.returncode == 0
        
        if not applies_cleanly:
            errors.append(f"Conflicts: {result.stderr}")
        else:
            # Apply and test
            subprocess.run(['git', 'apply', patch_file], cwd=repo_path)
            
            # Run tests if they exist
            test_result = None
            if os.path.exists(os.path.join(repo_path, 'pytest.ini')):
                test_result = subprocess.run(
                    ['pytest', 'tests/'],
                    cwd=repo_path,
                    capture_output=True
                )
            elif os.path.exists(os.path.join(repo_path, 'package.json')):
                test_result = subprocess.run(
                    ['npm', 'test'],
                    cwd=repo_path,
                    capture_output=True
                )
            
            tests_pass = test_result.returncode == 0 if test_result else True
            if test_result and not tests_pass:
                errors.append("Tests failed")
        
        os.unlink(patch_file)
    except Exception as e:
        applies_cleanly = False
        tests_pass = False
        errors.append(str(e))
    finally:
        # Cleanup: restore original branch and delete test branch
        try:
            original_branch.checkout()
            repo.delete_head(test_branch, force=True)
        except:
            pass
    
    return {
        "is_valid": len(errors) == 0,
        "applies_cleanly": applies_cleanly,
        "tests_pass": tests_pass if applies_cleanly else False,
        "errors": errors
    }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8003)
```

### 3.5 Deploy MCP Servers on Databricks Cluster

**Note:** MCP servers run on the same cluster as your agent. Databricks handles internal networking automatically - servers communicate via `localhost`.

**Git Access Setup:**

```bash
# In a Databricks notebook on your cluster:

# Option 1: GitHub Personal Access Token (Recommended)
%sh
export GIT_TOKEN="ghp_your_token_here"
# Or set in cluster environment variables in Databricks UI

# Option 2: SSH Key
%sh
mkdir -p ~/.ssh
cat > ~/.ssh/id_rsa << 'EOF'
-----BEGIN OPENSSH PRIVATE KEY-----
your_private_key_here
-----END OPENSSH PRIVATE KEY-----
EOF
chmod 600 ~/.ssh/id_rsa
ssh-keyscan github.com >> ~/.ssh/known_hosts

# Option 3: Use Databricks Repos (if repos already synced)
# Access repos directly at /Workspace/Repos/user@email.com/repo_name
```

**Install Dependencies:**

```bash
%sh
# Install dependencies
pip install mcp fastapi uvicorn gitpython requests

# Create directory for MCP servers
mkdir -p /dbfs/mcp_servers/logs

# Upload your MCP server files to /dbfs/mcp_servers/
# - mcp_git_utils.py
# - mcp_code_analyzer.py
# - mcp_compatibility_checker.py
# - mcp_patch_generator.py
# - mcp_patch_validator.py
```

**Start MCP Servers:**

```bash
%sh
cd /dbfs/mcp_servers/

# Start servers (they'll run on localhost)
nohup python mcp_code_analyzer.py > logs/analyzer.log 2>&1 &
nohup python mcp_compatibility_checker.py > logs/compatibility.log 2>&1 &
nohup python mcp_patch_generator.py > logs/patch_gen.log 2>&1 &
nohup python mcp_patch_validator.py > logs/validator.log 2>&1 &

# Verify servers are running
ps aux | grep mcp

# Check logs
tail -f logs/*.log
```

**Git Authentication in RepoManager:**

Update `mcp_git_utils.py` to use token authentication:

```python
import os

class RepoManager:
    def __init__(self, clone_base_dir: str = "/tmp/mcp_repos"):
        self.clone_base_dir = clone_base_dir
        self.git_token = os.getenv("GIT_TOKEN")
        os.makedirs(clone_base_dir, exist_ok=True)
    
    def get_authenticated_url(self, repo_url: str) -> str:
        """Add authentication token to HTTPS URL."""
        if self.git_token and repo_url.startswith("https://"):
            # https://github.com/org/repo.git -> https://token@github.com/org/repo.git
            return repo_url.replace("https://", f"https://{self.git_token}@")
        return repo_url
    
    def get_repo(self, repo_url: str, repo_id: str) -> str:
        repo_path = os.path.join(self.clone_base_dir, repo_id)
        auth_url = self.get_authenticated_url(repo_url)
        
        if os.path.exists(repo_path):
            repo = git.Repo(repo_path)
            repo.remotes.origin.pull()
        else:
            git.Repo.clone_from(auth_url, repo_path)
        
        return repo_path
```

**Important:** 
- Servers run on `localhost:8000-8003` (same cluster)
- Git repos are cloned to `/tmp/mcp_repos/` (ephemeral storage)
- Use GitHub tokens or SSH keys for private repo access
- Agent and MCP servers communicate internally
- Databricks manages all networking automatically

---

## 🔌 Step 4: Integrate App with Production

### 4.1 Update config.env

```bash
# Switch to production mode
DATA_MODE="production"

# UC settings
UC_CATALOG="ing_hackathon"
UC_SCHEMA="ing_hackathon"
UC_TABLE="sca_findings"
UC_AGENT="ing_hackathon.ing_hackathon.fix_advisor_agent"

# Note: Databricks Apps use built-in Spark access
# No SQL Warehouse needed - app queries UC tables directly with Spark
```

### 4.2 Deploy App

```bash
./deploy.sh
```

App will now:
- Load repos from UC table (not mock data)
- Call agent which uses MCP tools
- Display real vulnerability analysis

---

## 📝 Step 5: Populate Data

### 5.1 Sample Insert

```sql
-- Example: Single vulnerable library with candidate versions showing vulnerability counts
INSERT INTO ing_hackathon.ing_hackathon.sca_findings VALUES (
  '/repos/payment-gateway-api',      -- repo_path
  'requests',                          -- library
  '2.6.0',                            -- current_version
  'payment-gateway-api',              -- repo_name
  'https://github.com/ing/payment-gateway-api',  -- repo_url
  'Critical',                          -- priority
  ARRAY('CVE-2023-32681'),            -- cve_ids
  7.5,                                 -- cvss_score
  ARRAY(
    STRUCT('2.31.0', 0),              -- Latest: 0 vulnerabilities
    STRUCT('2.28.2', 1),              -- 1 known vulnerability
    STRUCT('2.27.1', 2),              -- 2 known vulnerabilities
    STRUCT('2.26.0', 3)               -- 3 known vulnerabilities
  ),
  CURRENT_TIMESTAMP(),
  'ready',                             -- status
  'CHK-2026-001',                      -- checkmarx_finding_id
  'payments-team'                      -- owner_team
);
```

### 5.2 Bulk Import from Checkmarx

```python
# Run in Databricks notebook
import pandas as pd
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

# Read Checkmarx findings
findings_df = spark.read.csv("checkmarx_findings.csv", header=True, inferSchema=True)

# Transform and write to UC table
findings_df.write.mode("append").saveAsTable("ing_hackathon.ing_hackathon.sca_findings")

print(f"Imported {findings_df.count()} repos to UC")
```

---

## ✅ Step 6: Testing

### 6.1 Test UC Connection

```python
# Run in Databricks notebook
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

# Query UC table
df = spark.sql("SELECT COUNT(*) as count FROM ing_hackathon.ing_hackathon.sca_findings")
df.show()

print(f"Total repos: {df.collect()[0]['count']}")
```

### 6.2 Test Agent

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
result = w.serving_endpoints.query(
    name="ing_hackathon.ing_hackathon.fix_advisor_agent",
    inputs={"repo_id": "repo_001"}
)
print("Agent analysis:", result.predictions)
```

### 6.3 Test MCP Servers

```python
import requests

# Run this in a notebook on the same cluster where MCP servers are running

# Test Code Analyzer (localhost - same cluster)
response = requests.post(
    "http://localhost:8000/tools/analyze_code_changes",
    json={
        "repo_path": "/dbfs/repos/test-repo",
        "library": "requests",
        "current_version": "2.6.0",
        "target_version": "2.31.0"
    }
)
print("Analysis:", response.json())

# Test Compatibility Checker (uses CVE database)
response = requests.post(
    "http://localhost:8001/tools/check_compatibility",
    json={"library": "requests", "version": "2.31.0"}
)
print("Compatibility:", response.json())
```

---

## 📊 Monitoring

### Check Status

```sql
-- Repos by status
SELECT status, COUNT(*) as count
FROM ing_hackathon.ing_hackathon.sca_findings
GROUP BY status;

-- Agent performance
SELECT 
  AVG(confidence) as avg_confidence,
  AVG(code_changes_files) as avg_files_changed
FROM ing_hackathon.ing_hackathon.agent_analysis_results;

-- User decisions
SELECT decision, COUNT(*) as count
FROM ing_hackathon.ing_hackathon.user_decisions
GROUP BY decision;
```

---

## 🐛 Troubleshooting

### UC Connection Issues

```sql
-- Verify table exists
SHOW TABLES IN ing_hackathon.ing_hackathon;

-- Check permissions
SHOW GRANTS ON TABLE ing_hackathon.ing_hackathon.sca_findings;

-- Grant access to app
GRANT SELECT ON TABLE ing_hackathon.ing_hackathon.sca_findings 
TO `app-service-principal`;
```

### MCP Server Issues

```bash
# Check if servers are running
ps aux | grep mcp

# Check logs
tail -f /dbfs/mcp_servers/logs/*.log

# Restart servers
pkill -f mcp_
cd /dbfs/mcp_servers && sh start_mcp_servers.sh
```

### Agent Issues

```bash
# Check app logs
databricks apps logs ing-ai-hackathon-sca | grep -i agent

# Verify model exists
databricks models list --catalog ing_hackathon --schema ing_hackathon
```

---

## 🎯 Summary

**Current State:**
- ✅ Mock data mode working
- ✅ UI fully functional
- ✅ Ready for UC integration

**Production Setup:**
1. Create UC tables (Step 1)
2. Register agent with MCP tools (Step 2)
3. Deploy MCP servers on cluster (Step 3)
4. Configure `DATA_MODE="production"` (Step 4)
5. Populate data from Checkmarx (Step 5)
6. Test & deploy (Step 6)

**MCP Servers check vulnerabilities against CVE (Common Vulnerabilities and Exposures) database.**

---

**Ready for production deployment!** 🚀
