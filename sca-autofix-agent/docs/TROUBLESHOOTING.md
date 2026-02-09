# Troubleshooting Guide

## Authentication Issues

### Error: "Credential was not sent or was of an unsupported type"

This error occurs when the Databricks CLI cannot authenticate with your workspace.

---

## Solution Steps

### Step 1: Check Current Authentication

```bash
# List configured profiles
databricks auth profiles

# Check current profile
databricks auth env
```

### Step 2: Clear Existing Authentication

```bash
# Remove potentially corrupted auth
rm -rf ~/.databrickscfg

# Or edit manually
vim ~/.databrickscfg
```

### Step 3: Re-authenticate

**Option A: OAuth (Recommended)**

```bash
databricks auth login --host https://your-workspace.cloud.databricks.com
```

This will:
1. Open your browser
2. Ask you to log in to Databricks
3. Save credentials automatically

**Option B: Personal Access Token**

```bash
# Generate token in Databricks UI:
# Settings → Developer → Access Tokens → Generate New Token

databricks auth login \
  --host https://your-workspace.cloud.databricks.com \
  --token
```

Paste your token when prompted.

**Option C: Manual Configuration**

Edit `~/.databrickscfg`:

```ini
[DEFAULT]
host = https://your-workspace.cloud.databricks.com
token = dapi1234567890abcdef

# Or for OAuth
[DEFAULT]
host = https://your-workspace.cloud.databricks.com
auth_type = oauth
```

### Step 4: Verify Authentication

```bash
# Test connection
databricks workspace list /

# Should return your workspace root folders
```

If this works, authentication is successful! ✅

### Step 5: Try Creating the App Again

```bash
cd /Users/shyam.sankararaman/Libraries/app-templates/vulnerability-scanner-mcp
databricks apps create vulnerability-scanner
```

---

## Common Issues

### Issue: "Host not configured"

**Error:**
```
Error: cannot configure default credentials
```

**Solution:**
```bash
# Specify host explicitly
databricks auth login --host https://your-workspace.cloud.databricks.com
```

### Issue: "Token expired"

**Error:**
```
Error: token is expired or invalid
```

**Solution:**
```bash
# Re-login to get fresh token
databricks auth login --host https://your-workspace.cloud.databricks.com
```

### Issue: "Permission denied"

**Error:**
```
Error: User does not have permission to create apps
```

**Solution:**
- Contact your Databricks workspace administrator
- You need `Workspace User` or `Admin` permissions
- Apps feature must be enabled in your workspace

### Issue: Multiple Profiles

**Error:**
```
Error: Multiple profiles found
```

**Solution:**
```bash
# List profiles
databricks auth profiles

# Use specific profile
databricks apps create vulnerability-scanner --profile my-profile

# Or set default profile
export DATABRICKS_CONFIG_PROFILE=my-profile
```

---

## Workspace Requirements

To create Databricks Apps, you need:

1. **Workspace Type**: Premium or Enterprise
2. **User Permissions**: 
   - `Can create apps` permission
   - `Workspace User` role or higher
3. **Features Enabled**:
   - Databricks Apps feature enabled
   - Serverless enabled (optional but recommended)

**Check with your admin if you're unsure!**

---

## Step-by-Step Authentication Guide

### For First-Time Users

```bash
# 1. Install Databricks CLI (if not already)
pip install databricks-cli

# Or with brew on macOS
brew tap databricks/tap
brew install databricks

# 2. Find your workspace URL
# Example: https://dbc-abc123-def456.cloud.databricks.com
# or: https://your-company.cloud.databricks.com

# 3. Authenticate
databricks auth login --host https://YOUR-WORKSPACE-URL

# 4. Test connection
databricks workspace list /

# 5. You should see folders like:
# /Users
# /Shared
# /Repos
```

### For Existing Users with Issues

```bash
# 1. Check what's wrong
databricks auth env

# 2. Clear and re-authenticate
rm ~/.databrickscfg
databricks auth login --host https://YOUR-WORKSPACE-URL

# 3. Verify
databricks workspace list /
```

---

## Environment Variables

You can also authenticate using environment variables:

```bash
# Set environment variables
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_TOKEN="dapi1234567890abcdef"

# Or for OAuth
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_AUTH_TYPE="oauth"

# Then create app
databricks apps create vulnerability-scanner
```

---

## Debugging Authentication

### View Current Configuration

```bash
# Show active profile
cat ~/.databrickscfg

# Check environment variables
env | grep DATABRICKS
```

### Test API Access

```bash
# Test with curl
curl -H "Authorization: Bearer $DATABRICKS_TOKEN" \
  https://your-workspace.cloud.databricks.com/api/2.0/clusters/list

# Should return cluster list (or empty array)
```

### Enable Debug Mode

```bash
# See detailed error messages
export DATABRICKS_DEBUG=true
databricks apps create vulnerability-scanner
```

---

## Getting Help

### 1. Check Databricks CLI Version

```bash
databricks --version

# Update if needed
pip install --upgrade databricks-cli
```

### 2. Review Databricks Documentation

- [Authentication Guide](https://docs.databricks.com/dev-tools/cli/authentication.html)
- [Databricks Apps Documentation](https://docs.databricks.com/dev-tools/databricks-apps/)

### 3. Contact Support

If you're still stuck:
- Check with your Databricks workspace administrator
- Verify you have the necessary permissions
- Ensure Databricks Apps is enabled in your workspace

---

## Quick Fix Checklist

- [ ] Run `databricks auth login --host https://YOUR-WORKSPACE-URL`
- [ ] Test with `databricks workspace list /`
- [ ] Verify you see workspace folders
- [ ] Try creating the app again
- [ ] Check that Apps feature is enabled in your workspace
- [ ] Verify you have permission to create apps

---

## Still Having Issues?

If authentication works but app creation fails, see:
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment troubleshooting
- [README.md](../README.md) - Full documentation

---

## Summary

**Most Common Solution:**

```bash
# 1. Re-authenticate
databricks auth login --host https://your-workspace.cloud.databricks.com

# 2. Test
databricks workspace list /

# 3. Try again
cd /Users/shyam.sankararaman/Libraries/app-templates/vulnerability-scanner-mcp
databricks apps create vulnerability-scanner
```

**Still not working?** Contact your Databricks administrator to:
- Enable Databricks Apps in your workspace
- Grant you app creation permissions
- Verify your workspace tier (Premium/Enterprise required)

