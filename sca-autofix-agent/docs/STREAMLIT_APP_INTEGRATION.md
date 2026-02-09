# Streamlit App Integration Guide

Integration plan for connecting the [Databricks Streamlit App](https://github.com/alpaselle/vulnerability-scanner-app/) with our MCP server and agent.

---

## 🏗️ Current Architecture (From App Repo)

### **Streamlit App Structure:**
```
vulnerability-scanner-app/
├── app.py                    # Streamlit UI
├── demo_fixtures.py          # Mock data
├── config.env                # Configuration
├── app.yaml                  # Databricks App config
└── UC_INTEGRATION.md        # UC table schemas
```

### **App Capabilities:**
- ✅ Reads from UC `sca_findings` table
- ✅ Displays vulnerabilities with priority ranking
- ✅ Shows candidate upgrade versions
- ✅ Mock mode (demo_fixtures.py) and Production mode (UC)
- ✅ User can select repos and target versions

### **Mentioned Architecture (From App README):**
```
4 MCP Servers (localhost):
- Code Analyzer (port 8000)
- Compatibility Checker (port 8001)
- Patch Generator (port 8002)
- Patch Validator (port 8003)
```

**Our Reality:** We have **1 comprehensive MCP server** with **17 tools** that covers all these capabilities!

---

## 🔄 Integration Architecture

### **Complete Data Flow:**

```
┌─────────────────────────────────────────────────────────────┐
│         Checkmarx / Snyk / External Scanner                 │
│         Detects vulnerabilities in repos                    │
└────────────────────┬────────────────────────────────────────┘
                     │ Writes findings
                     ▼
┌─────────────────────────────────────────────────────────────┐
│    Unity Catalog: sca_findings (Delta Table)            │
│    Schema: repo_id, repo_name, repo_pointer, vuln_libs,    │
│            candidate_versions, priority, status, ...         │
└────────────────────┬────────────────────────────────────────┘
                     │ Query
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         Streamlit App (app.py)                              │
│         • Reads from UC sca_findings                    │
│         • Displays table to user                            │
│         • User selects: repo + library + target version     │
│         • Calls agent for analysis                          │
└────────────────────┬────────────────────────────────────────┘
                     │ User action: "Analyze Migration"
                     ▼
┌─────────────────────────────────────────────────────────────┐
│    UC Model: fix_advisor_agent (LLM Agent)                  │
│    • Orchestrates tool calls                                │
│    • Uses MCP tools for analysis                            │
│    • Generates migration recommendations                    │
└────────────────────┬────────────────────────────────────────┘
                     │ Uses MCP tools
                     ▼
┌─────────────────────────────────────────────────────────────┐
│    MCP Server: mcp-vulnerability-scanner                     │
│    (Our comprehensive server - port 8000)                   │
│                                                              │
│    Available Tools:                                         │
│    • scan_repo_dependencies                                 │
│    • check_vulnerabilities                                   │
│    • analyze_package_usage                                  │
│    • check_api_changes                                       │
│    • analyze_library_migration (NEW - Java)                 │
│    • generate_patch_preview                                 │
│    • validate_patch_with_tests                              │
│    • get_sca_findings_from_uc                           │
│    • write_analysis_to_uc                                    │
│    • record_user_decision_to_uc                             │
│    ... (17 tools total)                                     │
└────────────────────┬────────────────────────────────────────┘
                     │ Writes results
                     ▼
┌─────────────────────────────────────────────────────────────┐
│    Unity Catalog: agent_analysis_results                     │
│    Schema: analysis_id, repo_id, target_version,            │
│            breaking_changes, patches, confidence, ...        │
└────────────────────┬────────────────────────────────────────┘
                     │ Query
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         Streamlit App (app.py)                              │
│         • Reads from agent_analysis_results                 │
│         • Displays: breaking changes, patches, diff          │
│         • User approves/rejects                             │
│         • Records decision to user_decisions table          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔌 Integration Points

### **1. Streamlit App → MCP Server**

The Streamlit app needs to **call our MCP server** when user requests analysis.

#### **Option A: Direct HTTP Calls (Recommended)**

```python
# In app.py
import requests
import os

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")

def call_mcp_tool(tool_name: str, **kwargs) -> dict:
    """
    Call an MCP tool via HTTP.
    
    Args:
        tool_name: Name of the MCP tool
        **kwargs: Tool parameters
    
    Returns:
        Tool response as dict
    """
    response = requests.post(
        f"{MCP_SERVER_URL}/mcp/v1/tools/call",
        json={
            "name": tool_name,
            "arguments": kwargs
        },
        headers={"Content-Type": "application/json"}
    )
    response.raise_for_status()
    return response.json()

# Usage in Streamlit
if st.button("Analyze Migration"):
    with st.spinner("Analyzing library migration..."):
        result = call_mcp_tool(
            "analyze_library_migration",
            source_repo_url=selected_repo["repo_pointer"],
            library_name=selected_library["library"],
            current_version=selected_library["current_version"],
            target_version=selected_target_version
        )
        
        # Store in session state
        st.session_state["migration_analysis"] = result
```

#### **Option B: Via Agent (Production)**

```python
# In app.py
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import EndpointCoreConfigInput

def call_agent_for_analysis(repo_id: str, library: str, target_version: str):
    """
    Call the UC-registered agent model to analyze migration.
    
    The agent internally uses MCP tools.
    """
    w = WorkspaceClient()
    
    # Get agent model from UC
    agent_model = w.model_registry.get_model(
        name="ing_hackathon.sca_advisor.fix_advisor_agent"
    )
    
    # Call agent with user's selection
    response = w.serving.query(
        endpoint_name="fix_advisor_agent_endpoint",
        dataframe={
            "repo_id": repo_id,
            "library": library,
            "target_version": target_version
        }
    )
    
    return response
```

---

### **2. Agent → MCP Server**

The agent needs to be **configured to use our MCP server**.

#### **Agent Configuration (OpenAI SDK Example):**

```python
# Agent setup (in Databricks notebook or separate service)
from openai import OpenAI
from databricks_mcp import MCPClient

# Initialize MCP client
mcp_client = MCPClient(
    server_url="http://localhost:8000/mcp/v1",
    server_name="vulnerability-scanner"
)

# Initialize OpenAI client with MCP tools
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Get available tools from MCP server
tools = mcp_client.list_tools()

# Create agent with system prompt
system_prompt = """
You are a Java library migration expert. When a user requests migration analysis:

1. Use analyze_library_migration tool with:
   - source_repo_url (from user selection)
   - library_name (from sca_findings table)
   - current_version (from sca_findings table)
   - target_version (user selected)

2. Analyze the results:
   - Breaking changes count
   - Affected files
   - Migration complexity

3. Write results to UC using write_analysis_to_uc

4. Return summary to user
"""

# Agent function
def migration_agent(user_request: dict) -> dict:
    """
    Agent that orchestrates migration analysis.
    
    Args:
        user_request: {
            "repo_id": str,
            "library": str,
            "target_version": str
        }
    """
    # Read repo details from UC
    repo_info = mcp_client.call_tool(
        "get_sca_findings_from_uc",
        repo_id=user_request["repo_id"]
    )
    
    # Extract library info
    library_info = next(
        lib for lib in repo_info["vuln_libs"]
        if lib["library"] == user_request["library"]
    )
    
    # Call migration analysis
    analysis = mcp_client.call_tool(
        "analyze_library_migration",
        source_repo_url=repo_info["repo_pointer"],
        library_name=user_request["library"],
        current_version=library_info["current_version"],
        target_version=user_request["target_version"]
    )
    
    # Write to UC
    mcp_client.call_tool(
        "write_analysis_to_uc",
        repo_id=user_request["repo_id"],
        target_version=user_request["target_version"],
        analysis_result=analysis
    )
    
    return analysis
```

---

### **3. Streamlit App → UC Tables**

The app already reads from UC. We need to ensure it can also **read analysis results**.

#### **Update app.py to Read Analysis Results:**

```python
# In app.py
from pyspark.sql import SparkSession

def get_analysis_results(repo_id: str, library: str, target_version: str):
    """Read analysis results from UC."""
    spark = SparkSession.builder.getOrCreate()
    
    query = f"""
        SELECT *
        FROM ing_hackathon.sca_advisor.agent_analysis_results
        WHERE repo_id = '{repo_id}'
          AND library = '{library}'
          AND target_version = '{target_version}'
        ORDER BY analysis_ts DESC
        LIMIT 1
    """
    
    df = spark.sql(query)
    return df.toPandas().to_dict("records")[0] if df.count() > 0 else None

# Display in Streamlit
if st.session_state.get("migration_analysis"):
    analysis = st.session_state["migration_analysis"]
    
    st.subheader("Migration Analysis Results")
    
    # Summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Breaking Changes", analysis["summary"]["breaking_changes_count"])
    with col2:
        st.metric("Affected Files", analysis["summary"]["affected_files"])
    with col3:
        st.metric("Complexity", analysis["summary"]["migration_complexity"].upper())
    
    # Breaking Changes Table
    st.subheader("Breaking Changes")
    breaking_changes_df = pd.DataFrame(analysis["breaking_changes"])
    st.dataframe(breaking_changes_df)
    
    # Patches (Code Diff)
    st.subheader("Generated Patches")
    for patch in analysis["patches"]:
        with st.expander(f"{patch['file']}:{patch['line']} - {patch['confidence']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.code(patch["old_code"], language="java")
            with col2:
                st.code(patch["updated_code"], language="java")
            st.caption(patch["explanation"])
    
    # User Actions
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✅ Approve", type="primary"):
            # Record decision
            call_mcp_tool(
                "record_user_decision_to_uc",
                repo_id=selected_repo["repo_id"],
                target_version=selected_target_version,
                decision="approved",
                user_email=st.session_state.get("user_email", "user@company.com"),
                decision_reason="User approved migration"
            )
            st.success("Migration approved!")
    
    with col2:
        if st.button("❌ Reject"):
            call_mcp_tool(
                "record_user_decision_to_uc",
                repo_id=selected_repo["repo_id"],
                target_version=selected_target_version,
                decision="rejected",
                user_email=st.session_state.get("user_email", "user@company.com"),
                decision_reason="User rejected migration"
            )
            st.info("Migration rejected")
    
    with col3:
        if st.button("✏️ Edit Manually"):
            st.info("Manual editing not yet implemented")
```

---

## 📊 UC Table Integration

### **Tables Used:**

#### **1. `sca_findings` (Input)**
```sql
-- Already exists in app
SELECT 
    repo_id,
    repo_name,
    repo_pointer,  -- Git URL
    vuln_libs,     -- Array of {library, current_version, cve_ids, cvss_score}
    candidate_versions,
    priority,
    status
FROM ing_hackathon.sca_advisor.sca_findings
WHERE status = 'ready'
```

#### **2. `agent_analysis_results` (Output)**
```sql
-- Created by MCP tool: write_analysis_to_uc
CREATE TABLE IF NOT EXISTS ing_hackathon.sca_advisor.agent_analysis_results (
    analysis_id STRING NOT NULL,
    repo_id STRING NOT NULL,
    library STRING NOT NULL,
    target_version STRING NOT NULL,
    
    -- Analysis results
    breaking_changes_count INT,
    affected_files INT,
    affected_invocations INT,
    
    -- Detailed changes
    breaking_changes ARRAY<STRUCT<
        class: STRING,
        method: STRING,
        old_signature: STRING,
        new_signature: STRING,
        change_type: STRING,
        affected_locations: ARRAY<STRUCT<file: STRING, line: INT>>
    >>,
    
    -- Generated patches
    patches ARRAY<STRUCT<
        file: STRING,
        line: INT,
        old_code: STRING,
        new_code: STRING,
        confidence: STRING,
        explanation: STRING
    >>,
    
    -- Summary
    migration_complexity STRING,  -- "low", "medium", "high"
    estimated_effort_hours DOUBLE,
    auto_fixable_percent DOUBLE,
    
    -- Metadata
    analysis_ts TIMESTAMP,
    llm_model STRING,
    status STRING,
    
    CONSTRAINT pk_analysis PRIMARY KEY (analysis_id)
);
```

#### **3. `user_decisions` (Audit)**
```sql
-- Already exists in app
-- Updated by: record_user_decision_to_uc
```

---

## 🚀 Deployment Steps

### **Step 1: Deploy MCP Server**

```bash
# In vulnerability-scanner-mcp/
databricks apps create mcp-vulnerability-scanner
databricks apps deploy mcp-vulnerability-scanner --source-code-path /Workspace/Users/you@company.com/vulnerability-scanner-mcp
```

**App URL:** `https://mcp-vulnerability-scanner-{id}.aws.databricksapps.com`

### **Step 2: Update Streamlit App Config**

```bash
# In vulnerability-scanner-app/
# Edit config.env
MCP_SERVER_URL=http://localhost:8000  # Or use app URL if external
DATA_MODE=production
```

### **Step 3: Create UC Tables**

```sql
-- Run in Databricks SQL
-- agent_analysis_results table (if not exists)
CREATE TABLE IF NOT EXISTS ing_hackathon.sca_advisor.agent_analysis_results (
    -- ... schema from above
);
```

### **Step 4: Register Agent Model (Optional)**

```python
# In Databricks notebook
import mlflow
from your_agent_module import MigrationAgent

with mlflow.start_run():
    mlflow.pyfunc.log_model(
        artifact_path="fix_advisor_agent",
        registered_model_name="ing_hackathon.sca_advisor.fix_advisor_agent",
        python_model=MigrationAgent()
    )
```

### **Step 5: Update Streamlit App Code**

Add MCP integration code (see examples above) to `app.py`.

---

## 🔧 Code Examples

### **Complete Integration Example:**

```python
# app.py additions

import requests
import streamlit as st
from pyspark.sql import SparkSession

# Configuration
MCP_SERVER_URL = st.secrets.get("MCP_SERVER_URL", "http://localhost:8000")
CATALOG = "ing_hackathon"
SCHEMA = "sca_advisor"

def call_mcp_tool(tool_name: str, **kwargs):
    """Call MCP tool via HTTP."""
    try:
        response = requests.post(
            f"{MCP_SERVER_URL}/mcp/v1/tools/call",
            json={"name": tool_name, "arguments": kwargs},
            timeout=300  # 5 minutes for long-running operations
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"MCP tool call failed: {e}")
        return None

# In main app flow
def main():
    st.title("SCA Vulnerabilities Scanning App")
    
    # Read vulnerable repos from UC
    spark = SparkSession.builder.getOrCreate()
    repos_df = spark.sql(f"""
        SELECT * FROM {CATALOG}.{SCHEMA}.sca_findings
        WHERE status = 'ready'
        ORDER BY priority ASC
    """)
    
    # Display repos
    selected_repo = st.selectbox("Select Repository", repos_df.toPandas()["repo_name"])
    repo_data = repos_df.filter(f"repo_name = '{selected_repo}'").first()
    
    # Display vulnerable libraries
    vuln_libs = repo_data["vuln_libs"]
    selected_lib = st.selectbox("Select Library", [lib["library"] for lib in vuln_libs])
    lib_data = next(lib for lib in vuln_libs if lib["library"] == selected_lib)
    
    # Display candidate versions
    candidate_versions = repo_data["candidate_versions"]
    selected_version = st.selectbox("Select Target Version", candidate_versions)
    
    # Analyze button
    if st.button("🔍 Analyze Migration", type="primary"):
        with st.spinner("Analyzing migration (this may take 2-5 minutes)..."):
            result = call_mcp_tool(
                "analyze_library_migration",
                source_repo_url=repo_data["repo_pointer"],
                library_name=selected_lib,
                current_version=lib_data["current_version"],
                target_version=selected_version
            )
            
            if result and result.get("status") == "success":
                st.session_state["analysis"] = result
                st.rerun()
    
    # Display results
    if "analysis" in st.session_state:
        display_analysis_results(st.session_state["analysis"])

def display_analysis_results(analysis: dict):
    """Display migration analysis results."""
    st.header("Migration Analysis Results")
    
    summary = analysis["summary"]
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Breaking Changes", summary["breaking_changes_count"])
    with col2:
        st.metric("Affected Files", summary["affected_files"])
    with col3:
        st.metric("Complexity", summary["migration_complexity"].upper())
    with col4:
        st.metric("Est. Effort", f"{summary['estimated_effort_hours']:.1f} hrs")
    
    # Breaking Changes
    st.subheader("Breaking Changes")
    breaking_changes = analysis["breaking_changes"]
    for change in breaking_changes:
        with st.expander(f"{change['class']}.{change['method']} - {change['change_type']}"):
            st.code(f"Old: {change['old_signature']}", language="java")
            st.code(f"New: {change['new_signature']}", language="java")
            st.write(f"**Affected locations:** {len(change['affected_locations'])}")
    
    # Patches
    st.subheader("Generated Patches")
    patches = analysis["patches"]
    for patch in patches:
        with st.expander(f"{patch['file']}:{patch['line']} ({patch['confidence']})"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Before:**")
                st.code(patch["old_code"], language="java")
            with col2:
                st.write("**After:**")
                st.code(patch["updated_code"], language="java")
            st.caption(patch["explanation"])
    
    # Actions
    st.subheader("Actions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Approve Migration", type="primary"):
            # Record decision
            call_mcp_tool(
                "record_user_decision_to_uc",
                repo_id=st.session_state.get("selected_repo_id"),
                target_version=st.session_state.get("selected_version"),
                decision="approved",
                user_email=st.session_state.get("user_email", "user@company.com")
            )
            st.success("Migration approved and recorded!")
    
    with col2:
        if st.button("❌ Reject"):
            call_mcp_tool(
                "record_user_decision_to_uc",
                repo_id=st.session_state.get("selected_repo_id"),
                target_version=st.session_state.get("selected_version"),
                decision="rejected",
                user_email=st.session_state.get("user_email", "user@company.com")
            )
            st.info("Migration rejected")

if __name__ == "__main__":
    main()
```

---

## 🎯 Key Integration Points Summary

| Component | Integration Method | Example |
|-----------|-------------------|---------|
| **Streamlit → MCP** | HTTP POST to `/mcp/v1/tools/call` | `call_mcp_tool("analyze_library_migration", ...)` |
| **Agent → MCP** | MCP Client SDK | `mcp_client.call_tool(...)` |
| **MCP → UC** | PySpark SQL | `write_analysis_to_uc()` tool |
| **Streamlit → UC** | PySpark SQL | `spark.sql("SELECT * FROM ...")` |

---

## ✅ Next Steps

1. **Deploy MCP server** to Databricks Apps
2. **Update Streamlit app** with MCP integration code
3. **Create UC tables** (agent_analysis_results)
4. **Test end-to-end** with sample repo
5. **Register agent model** (optional, for production)

---

## 📚 References

- [MCP Server Repo](https://github.com/shyamDB16/vulnerability-scanner-mcp)
- [Streamlit App Repo](https://github.com/alpaselle/vulnerability-scanner-app/)
- [MCP Protocol Docs](https://modelcontextprotocol.io/)
- [Databricks Apps Docs](https://docs.databricks.com/en/dev-tools/databricks-apps/)

