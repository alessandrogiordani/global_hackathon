# Deployment Guide

## Deploying to Databricks Apps

There are **two main approaches** to deploy your MCP server to Databricks:

---

## Method 1: Direct Deployment (Recommended for Quick Start)

### Step 1: Navigate to Project Directory

```bash
cd /Users/shyam.sankararaman/Libraries/app-templates/vulnerability-scanner-mcp
```

### Step 2: Authenticate

```bash
databricks auth login
```

### Step 3: Create the App

```bash
databricks apps create vulnerability-scanner
```

This will:
- Read your `app.yaml` configuration
- Upload your code automatically
- Create the app in your workspace

### Step 4: Deploy/Start the App

```bash
databricks apps deploy vulnerability-scanner
```

### Step 5: Check Status

```bash
databricks apps get vulnerability-scanner
```

Wait until `state` shows `RUNNING`.

---

## Method 2: Using Databricks Asset Bundles (DABs)

For more complex deployments with CI/CD pipelines.

### Step 1: Create `databricks.yml`

Create this file in your project root:

```yaml
bundle:
  name: vulnerability-scanner-mcp

resources:
  apps:
    vulnerability_scanner:
      name: vulnerability-scanner
      description: "AI-powered vulnerability scanner for code repositories"
      resources:
        - name: main
          description: "Main MCP server"
          serving_type: "serving"

targets:
  development:
    mode: development
    workspace:
      host: https://your-workspace.cloud.databricks.com

  production:
    mode: production
    workspace:
      host: https://your-workspace.cloud.databricks.com
```

### Step 2: Validate

```bash
databricks bundle validate
```

### Step 3: Deploy

```bash
databricks bundle deploy -t development
```

---

## Method 3: Using Databricks UI

### Step 1: Zip Your Project

```bash
cd /Users/shyam.sankararaman/Libraries/app-templates
zip -r vulnerability-scanner-mcp.zip vulnerability-scanner-mcp \
  -x "*.pyc" -x "*__pycache__*" -x "*.git*" -x ".venv/*"
```

### Step 2: Upload via UI

1. Go to your Databricks workspace
2. Navigate to **Apps** in the left sidebar
3. Click **Create App**
4. Upload `vulnerability-scanner-mcp.zip`
5. Wait for deployment to complete

---

## Verification Steps

### 1. Check App Status

```bash
databricks apps get vulnerability-scanner
```

Look for:
- `state: RUNNING`
- `url: https://...` (your app URL)

### 2. Test Health Endpoint

```bash
curl https://your-workspace.cloud.databricks.com/serving-endpoints/vulnerability-scanner/health
```

### 3. Check Logs

```bash
databricks apps logs vulnerability-scanner
```

---

## Common Issues & Solutions

### Issue: "App already exists"

**Solution:**
```bash
# Update existing app
databricks apps update vulnerability-scanner

# Or delete and recreate
databricks apps delete vulnerability-scanner
databricks apps create vulnerability-scanner
```

### Issue: "Invalid app.yaml"

**Solution:** Ensure your `app.yaml` is correct:
```yaml
command: ["uv", "run", "vulnerability-scanner-mcp"]
```

### Issue: "Build failed"

**Solution:** Check that all dependencies are in `pyproject.toml`:
```bash
# Test locally first
uv sync
uv run vulnerability-scanner-mcp
```

### Issue: "App not starting"

**Solution:** Check logs:
```bash
databricks apps logs vulnerability-scanner --follow
```

---

## Using the Deployed App

### Option 1: AI Playground

1. Go to **AI Playground** in Databricks
2. Select a model with **Tools enabled**
3. Click **Tools** → **+ Add tool**
4. Select `vulnerability-scanner`
5. Try a prompt:
   ```
   "Scan /Repos/myuser@company.com/my-project for vulnerabilities"
   ```

### Option 2: Programmatic Access

```python
from databricks_mcp import DatabricksMCPClient

# Your deployed app URL
app_url = "https://your-workspace.cloud.databricks.com/serving-endpoints/vulnerability-scanner"

# Connect with authentication
client = DatabricksMCPClient(
    server_url=app_url,
    token="your-oauth-token"
)

# List available tools
tools = client.list_tools()
print(tools)

# Call a tool
result = client.call_tool(
    "scan_repo_dependencies",
    {
        "repo_path": "/Repos/user@company.com/my-repo",
        "branch": "main"
    }
)
print(result)
```

### Option 3: Agent Framework

```python
from databricks.agents import Agent

agent = Agent.create(
    name="security-scanner-agent",
    tools=["vulnerability-scanner"],
    instructions="Help scan code repositories for security vulnerabilities"
)

response = agent.query(
    "Check my data-pipeline repo for security issues"
)
```

---

## Environment Variables

When deployed, your app automatically gets:

- `DATABRICKS_APP_NAME`: Your app name
- `DATABRICKS_HOST`: Workspace URL
- `DATABRICKS_TOKEN`: Service principal token

These are used by `utils.get_workspace_client()` and `utils.get_user_authenticated_workspace_client()`.

---

## Monitoring & Maintenance

### View Metrics

```bash
databricks apps get vulnerability-scanner --metrics
```

### Update App

After making code changes:

```bash
databricks apps update vulnerability-scanner
```

Or with bundles:

```bash
databricks bundle deploy -t production
```

### Scale App

Databricks Apps auto-scale, but you can configure:

1. Edit `app.yaml`:
```yaml
command: ["uv", "run", "vulnerability-scanner-mcp"]
resources:
  cpu: 2
  memory: 4Gi
```

2. Update:
```bash
databricks apps update vulnerability-scanner
```

---

## Security Best Practices

### 1. Use Service Scopes

When creating the app, specify required scopes:

```bash
databricks apps create vulnerability-scanner \
  --scopes "workspace.repos.read workspace.files.read"
```

### 2. Enable User Authorization

In your app settings, enable:
- User OAuth authentication
- Required scopes for end users

### 3. Audit Logging

All tool calls are automatically logged by Databricks.

View audit logs:
```bash
databricks workspace export-logs --app vulnerability-scanner
```

---

## Cleanup

### Delete App

```bash
databricks apps delete vulnerability-scanner
```

### Remove Bundle

```bash
databricks bundle destroy -t development
```

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `databricks apps create <name>` | Create new app |
| `databricks apps deploy <name>` | Deploy/start app |
| `databricks apps get <name>` | Check status |
| `databricks apps logs <name>` | View logs |
| `databricks apps update <name>` | Update app code |
| `databricks apps delete <name>` | Remove app |

---

## Next Steps

1. ✅ Deploy the app
2. ✅ Test in AI Playground
3. ✅ Integrate with your agents
4. ✅ Monitor and maintain

See [README.md](../README.md) for complete documentation!

