# Deployment Guide

## Quick Start

```bash
./deploy.sh
```

That's it! One command deployment.

---

## Configuration

All settings in **`config.env`**:

### Required Settings
```bash
WORKSPACE_HOST="https://your-workspace.cloud.databricks.com"
WORKSPACE_PATH="/Workspace/Users/your.email@company.com/app-folder"
APP_NAME="your-app-name"
```

### Data Source
```bash
DATA_MODE="mock"        # Use demo data (for testing)
DATA_MODE="production"  # Use Unity Catalog (for prod)
```

### Unity Catalog (only for production mode)
```bash
UC_CATALOG="your_catalog"
UC_SCHEMA="your_schema"
UC_TABLE="sca_findings"
```

### Agent Endpoint
```bash
AGENT_ENDPOINT="your_model_serving_endpoint"
```

---

## Environment Variables

The app reads these from `config.env` via Databricks Apps environment:

| Variable | Purpose | Example |
|----------|---------|---------|
| `DATA_MODE` | Switch between mock/production | `mock` or `production` |
| `UC_CATALOG` | Unity Catalog catalog name | `ing_hackathon` |
| `UC_SCHEMA` | Unity Catalog schema name | `ing_hackathon` |
| `UC_TABLE` | Table with vulnerabilities | `sca_findings` |
| `AGENT_ENDPOINT` | Model serving endpoint | `fix_advisor_agent_endpoint` |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     STREAMLIT APP                           │
│                                                             │
│  ┌──────────────┐         ┌─────────────────────────────┐  │
│  │   DATA MODE  │         │   IF production:            │  │
│  │              │────────▶│   - Read UC Table           │  │
│  │ mock / prod  │         │   - Call Agent Endpoint     │  │
│  └──────────────┘         │                             │  │
│                           │   IF mock:                  │  │
│                           │   - Use demo_fixtures.py    │  │
│                           └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
            ┌───────────────────────────────────────┐
            │       UNITY CATALOG                   │
            │                                       │
            │  catalog.schema.sca_findings      │
            │    - repo_path                        │
            │    - library                          │
            │    - candidate_versions[]             │
            │      ├─ version                       │
            │      ├─ release_date                  │
            │      ├─ vulnerability_count           │
            │      └─ detected_ts                   │
            └───────────────────────────────────────┘
                                │
                                ▼
            ┌───────────────────────────────────────┐
            │    MODEL SERVING ENDPOINT             │
            │                                       │
            │  AGENT_ENDPOINT                       │
            │    - Analyzes code changes            │
            │    - Generates patches                │
            │    - Returns file diffs               │
            └───────────────────────────────────────┘
```

---

## Data Flow

### Mock Mode (Demo)
```
User Request
    ↓
demo_fixtures.py (static data)
    ↓
Streamlit UI
```

### Production Mode
```
User Request
    ↓
Unity Catalog Table Query
    ↓
Streamlit UI Display
    ↓
User Clicks "Analyze"
    ↓
Call Model Serving Endpoint
    ↓
Display Analysis Results
```

---

## Files

| File | Purpose |
|------|---------|
| `config.env` | **Single source of truth** for all config |
| `app.py` | Main Streamlit application |
| `demo_fixtures.py` | Mock data for demo mode |
| `deploy.sh` | One-command deployment script |
| `databricks.yml` | Minimal Databricks App config |
| `requirements.txt` | Python dependencies |

---

## Deployment Process

When you run `./deploy.sh`:

1. ✅ **Load** `config.env`
2. ✅ **Validate** required settings
3. ✅ **Check** Databricks CLI installed
4. ✅ **Authenticate** to workspace
5. ✅ **Sync** files to workspace
6. ✅ **Deploy** as Databricks App
7. ✅ **Show** live app URL

---

## Switching Modes

### Demo Mode (Default)
```bash
# In config.env
DATA_MODE="mock"
```
Uses static data from `demo_fixtures.py`

### Production Mode
```bash
# In config.env
DATA_MODE="production"
UC_CATALOG="ing_hackathon"
UC_SCHEMA="ing_hackathon"
UC_TABLE="sca_findings"
AGENT_ENDPOINT="fix_advisor_agent_endpoint"
```
Reads live data from Unity Catalog and uses agent endpoint

---

## UC Table Schema

```sql
CREATE TABLE catalog.schema.sca_findings (
  repo_path STRING NOT NULL,
  library STRING NOT NULL,
  repo_name STRING NOT NULL,
  repo_pointer STRING NOT NULL,
  priority STRING NOT NULL,
  current_version STRING NOT NULL,
  cve_ids ARRAY<STRING>,
  cvss_score DOUBLE,
  candidate_versions ARRAY<STRUCT<
    version: STRING,
    release_date: TIMESTAMP,
    vulnerability_count: INT,
    detected_ts: TIMESTAMP
  >>,
  last_detected_ts TIMESTAMP,
  status STRING,
  checkmarx_finding_id STRING,
  owner_team STRING,
  CONSTRAINT pk_repos PRIMARY KEY (repo_path, library)
);
```

---

## Troubleshooting

### Issue: Authentication fails
```bash
databricks auth login --host "$WORKSPACE_HOST"
```

### Issue: Sync fails
Check `WORKSPACE_PATH` is correct:
```bash
databricks workspace list /Workspace/Users/
```

### Issue: App doesn't start
Check logs:
```bash
databricks apps logs $APP_NAME
```

### Issue: UC table not found
Verify table exists:
```bash
# In Databricks SQL
SELECT * FROM catalog.schema.sca_findings LIMIT 1;
```

---

## Best Practices

1. **Test in mock mode first** before production
2. **Keep config.env in .gitignore** (sensitive data)
3. **Use meaningful APP_NAME** for easy identification
4. **Monitor logs** after deployment
5. **Update UC table regularly** with fresh vulnerability data

---

## Summary

✅ **Single config file**: `config.env`  
✅ **One command deploy**: `./deploy.sh`  
✅ **Two modes**: mock (demo) / production (UC)  
✅ **Clean separation**: Config vs Code  
✅ **No redundancy**: Each setting defined once  

**Simple, clean, production-ready!** 🚀
