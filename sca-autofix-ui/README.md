# 🦁 SCA Vulnerabilities Scanning

Enterprise security dashboard for identifying and remediating vulnerable dependencies in your repositories.

---

## 🚀 Quick Deploy (3 Steps)

### 1. Edit Configuration
Open `config.env` and update these 3 lines:
```bash
WORKSPACE_HOST="https://your-workspace.cloud.databricks.com"
WORKSPACE_PATH="/Workspace/Users/your.email@databricks.com/ing-ai-hackathon-sca"
APP_NAME="ing-ai-hackathon-sca"
```

### 2. Add Logo (Optional)
Place your `ing_logo.png` file in the project root directory.

### 3. Deploy
```bash
./deploy.sh
```

That's it! ✅

---

## 📂 Project Structure

```
ing_hackathon_code_vuneralability/
├── app.py                  # Main Streamlit app (838 lines)
├── demo_fixtures.py        # Mock data for development (606 lines)
├── requirements.txt        # Python dependencies
├── app.yaml               # App runtime config
├── ing_logo.png           # ING logo
├── config.env             # Deployment configuration
├── databricks.yml         # Databricks bundle config
├── deploy.sh              # One-command deployment script (179 lines)
├── .streamlit/
│   └── config.toml        # Streamlit configuration
├── README.md              # This file (comprehensive documentation)
├── DEMO_GUIDE.md          # Hackathon demo script
└── UC_INTEGRATION.md      # Production setup guide with MCP details
```

**Total Core Code:** ~1,600 lines (app + fixtures + deploy script)

---

## 🎯 Current State: Mock Data Mode

The app currently uses **sample data** (8 mock repositories):
- `demo_fixtures.py` - Code samples, patch suggestions, vulnerability details
- `app.py` - Repository metadata

**Works immediately with no setup!** Perfect for:
- Development and testing
- Demos and presentations
- UI/UX iteration

---

## 🔄 Switching to Production Mode

When ready to connect to real data:

### 1. Create UC Structure

```sql
-- Create catalog and schema
CREATE CATALOG IF NOT EXISTS ing_hackathon;
CREATE SCHEMA IF NOT EXISTS ing_hackathon.ing_hackathon;

-- Main table: Vulnerable repos (one row per repo + library)
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
    vulnerability_count: INT,          -- Number of known vulnerabilities in this version
    detected_ts: TIMESTAMP             -- When this candidate version was detected/added
  >>,
  last_detected_ts TIMESTAMP,
  status STRING,                   -- 'ready', 'analyzing', 'approved', 'rejected'
  checkmarx_finding_id STRING,
  owner_team STRING,
  CONSTRAINT pk_repos PRIMARY KEY (repo_path, library)
);

-- Results table: Agent analysis
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
);

-- Audit table: User decisions
CREATE TABLE IF NOT EXISTS ing_hackathon.ing_hackathon.user_decisions (
  decision_id STRING NOT NULL,
  repo_path STRING NOT NULL,
  library STRING NOT NULL,
  target_version STRING NOT NULL,
  decision STRING NOT NULL,        -- 'approved', 'rejected'
  user_email STRING NOT NULL,
  decision_reason STRING,
  decision_ts TIMESTAMP,
  CONSTRAINT pk_decisions PRIMARY KEY (decision_id)
);
```

### 2. Deploy MCP Servers

Set up 4 custom MCP servers on your Databricks cluster (localhost):
- **Code Analyzer** (port 8000) - Analyzes library usage patterns
- **Compatibility Checker** (port 8001) - Checks CVEs using Common Vulnerabilities and Exposures database
- **Patch Generator** (port 8002) - Creates code patches
- **Patch Validator** (port 8003) - Tests patches

MCP servers run on `localhost` - Databricks handles internal networking automatically.

### 3. Register AI Agent

Register agent model in Unity Catalog that uses MCP tools. Example:

```python
import mlflow

with mlflow.start_run():
    mlflow.pyfunc.log_model(
        artifact_path="fix_advisor_agent",
        registered_model_name="ing_hackathon.ing_hackathon.fix_advisor_agent",
        python_model=your_agent_model
    )
```

### 4. Switch Mode

Edit `config.env`:
```bash
DATA_MODE="production"  # Switch from "mock"
```

### 5. Redeploy

```bash
./deploy.sh
```

---

## 🛠️ Troubleshooting

### Authentication Issues
```bash
# Manually authenticate
databricks auth login --host https://your-workspace.cloud.databricks.com

# Then deploy
./deploy.sh
```

### App Crashed
Check logs:
```bash
databricks apps logs ing-ai-hackathon-sca
```

Or visit: `https://your-workspace.cloud.databricks.com/apps/ing-ai-hackathon-sca/logs`

### Sync Issues
Force full sync:
```bash
databricks sync . "$WORKSPACE_PATH" --full
```

---

## 🎨 Customizing Mock Data

### Add/Edit Repositories
Edit `app.py` lines 304-361:
```python
mock_data = {
    'repo_id': ['repo_001', 'repo_002', ...],
    'repo_name': ['payment-gateway-api', ...],
    'priority': [1, 1, 2, ...],  # 1=Critical, 2=High, 3=Medium
    ...
}
```

### Add/Edit Code Samples
Edit `demo_fixtures.py`:
```python
MOCK_AGENT_OUTPUTS = {
    "repo_001": {
        "old_code": "...",  # Vulnerable code
        "new_code": "...",  # Fixed code
        "recommended_version": "2.31.0",
        ...
    }
}
```

---

## 📊 Architecture

### Current (Mock Mode)
```
Streamlit App → demo_fixtures.py → Display in UI
```

### Production (Unity Catalog + MCP)
```
┌──────────────────────────────────────────────┐
│     Checkmarx SCA Scanner (External)         │
│   Detects vulnerable libraries in repos      │
└────────────────┬─────────────────────────────┘
                 │ Findings
                 ▼
┌──────────────────────────────────────────────┐
│  Unity Catalog: sca_findings (Delta)     │
│  One row per repo with vuln libs & versions  │
└────────────────┬─────────────────────────────┘
                 │ Query
                 ▼
┌──────────────────────────────────────────────┐
│    SCA Vulnerabilities Scanning App          │
│         (Streamlit UI - this project)        │
└────────────────┬─────────────────────────────┘
                 │ Call agent
                 ▼
┌──────────────────────────────────────────────┐
│    UC Model: fix_advisor_agent (TBD LLM)     │
│  Analyzes code changes for each version      │
└────────────────┬─────────────────────────────┘
                 │ Uses MCP tools
                 ▼
┌──────────────────────────────────────────────┐
│        Custom MCP Servers (localhost)        │
│  • Code Analyzer (port 8000)                 │
│  • Compatibility Checker (port 8001)         │
│  • Patch Generator (port 8002)               │
│  • Patch Validator (port 8003)               │
└────────────────┬─────────────────────────────┘
                 │ Check vulnerabilities
                 ▼
┌──────────────────────────────────────────────┐
│      CVE: Common Vulnerabilities and         │
│      Exposures (Open source database)        │
└──────────────────────────────────────────────┘
```

**MCP (Model Context Protocol)** = Industry standard for AI agent tools
- Better than UC Functions for complex AI workflows
- Native LLM integration (works with Claude, GPT-4, etc.)
- Flexible Python services
- **MCP servers run on localhost** - Databricks handles internal networking

**Agent Model:** Not yet selected - can use Claude, GPT-4, or other LLMs

---

## 🤝 Team Handover

### For New Developers
1. Clone repo
2. Edit `config.env` (3 lines)
3. Run `./deploy.sh`
4. App URL shown in terminal

### For DevOps/ML Engineers
- **Current**: Mock data mode, works immediately
- **Next Phase**: Implement MCP servers (see Architecture section above)
- **Production**: Switch `DATA_MODE="production"` in config

### For Hackathon Judges
- See `DEMO_GUIDE.md` for 60-second demo script
- App showcases: vulnerability prioritization, upgrade recommendations, code diff preview

---

## 📝 Key Commands

```bash
# Deploy or redeploy
./deploy.sh

# View logs
databricks apps logs ing-ai-hackathon-sca

# Manual sync
databricks sync . "$WORKSPACE_PATH" --full

# Authenticate to different workspace
databricks auth login --host https://workspace-url.cloud.databricks.com
```

---

## 🏆 Features

### Current (Mock Mode)
✅ **8 realistic vulnerability scenarios**  
✅ **Interactive UI for repo selection**  
✅ **Priority-based ranking**  
✅ **Version upgrade recommendations**  
✅ **Code diff preview**  
✅ **Patch export**  

### Production (After UC Integration)
✅ **Real Checkmarx findings**  
✅ **Live CVE vulnerability checks**  
✅ **AI-powered code analysis**  
✅ **Automated patch generation**  
✅ **Audit trail of decisions**  

---

## 📚 Additional Resources

- **Hackathon Demo**: See `DEMO_GUIDE.md`
- **Databricks Apps Docs**: https://docs.databricks.com/en/dev-tools/databricks-apps/
- **MCP Protocol**: https://modelcontextprotocol.io/
- **CVE Database**: https://cve.mitre.org/

---

**Built for ING AI Hackathon 2026** 🦁
