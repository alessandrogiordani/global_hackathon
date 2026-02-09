#!/bin/bash
# ========================================================================
# SCA Vulnerabilities Scanning - One-Command Deploy
# ========================================================================
# USAGE: ./deploy.sh
# ========================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${BLUE}🚀 SCA Vulnerabilities Scanning - Deployment${NC}"
echo "================================================"
echo ""

# ========================================================================
# 1. LOAD CONFIGURATION
# ========================================================================
if [ ! -f "config.env" ]; then
    echo -e "${RED}❌ config.env not found${NC}"
    echo ""
    echo "Create config.env with your settings:"
    echo "  - WORKSPACE_HOST"
    echo "  - WORKSPACE_PATH"
    echo "  - APP_NAME"
    echo "  - UC_CATALOG, UC_SCHEMA, UC_TABLE"
    echo "  - AGENT_ENDPOINT"
    echo ""
    echo "See config.env.example for template"
    exit 1
fi

source config.env
echo -e "${GREEN}✓${NC} Config loaded"

# ========================================================================
# 2. VALIDATE CONFIGURATION
# ========================================================================
if [[ "$WORKSPACE_PATH" == *"YOUR_EMAIL"* ]] || [[ "$WORKSPACE_PATH" == *"your.email"* ]]; then
    echo -e "${RED}❌ Please edit config.env${NC}"
    echo "   Update WORKSPACE_PATH with your actual workspace path"
    exit 1
fi

if [ -z "$WORKSPACE_HOST" ] || [ -z "$WORKSPACE_PATH" ] || [ -z "$APP_NAME" ]; then
    echo -e "${RED}❌ Missing required config in config.env${NC}"
    exit 1
fi

# ========================================================================
# 3. CHECK PREREQUISITES
# ========================================================================
if [ ! -f "app.py" ]; then
    echo -e "${RED}❌ app.py not found. Run from project directory.${NC}"
    exit 1
fi

if ! command -v databricks &> /dev/null; then
    echo -e "${RED}❌ Databricks CLI not installed${NC}"
    echo ""
    echo "Install: curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh"
    exit 1
fi

echo -e "${GREEN}✓${NC} Databricks CLI installed"

# ========================================================================
# 4. AUTHENTICATE
# ========================================================================
echo ""
echo "🔐 Authenticating..."

if ! databricks auth env --host "$WORKSPACE_HOST" 2>/dev/null | grep -q "DATABRICKS_HOST"; then
    echo -e "${YELLOW}→ Authentication required${NC}"
    databricks auth login --host "$WORKSPACE_HOST"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Authentication failed${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓${NC} Authenticated to workspace"

# ========================================================================
# 5. SHOW DEPLOYMENT PLAN
# ========================================================================
echo ""
echo "📋 Deployment Plan:"
echo "   Workspace:  $WORKSPACE_HOST"
echo "   Path:       $WORKSPACE_PATH"
echo "   App Name:   $APP_NAME"
echo "   Data Mode:  $DATA_MODE"
if [ "$DATA_MODE" == "production" ]; then
    echo "   UC Table:   ${UC_CATALOG}.${UC_SCHEMA}.${UC_TABLE}"
    echo "   Agent:      $AGENT_ENDPOINT"
fi
echo ""

# ========================================================================
# 6. SYNC FILES
# ========================================================================
echo "📤 Syncing files..."

databricks sync . "$WORKSPACE_PATH" --full

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Sync failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Files synced"

# ========================================================================
# 7. DEPLOY APP
# ========================================================================
echo ""
echo "🚀 Deploying app..."

databricks apps deploy "$APP_NAME" --source-code-path "$WORKSPACE_PATH"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Deployment failed${NC}"
    echo ""
    echo "Check logs:"
    echo "  databricks apps logs $APP_NAME"
    echo ""
    echo "Or visit:"
    echo "  ${WORKSPACE_HOST}/apps/${APP_NAME}/logs"
    exit 1
fi

# ========================================================================
# 8. SUCCESS
# ========================================================================
echo ""
echo -e "${GREEN}✅ SUCCESS!${NC}"
echo ""
echo -e "${GREEN}🌐 Your app is live:${NC}"
echo -e "${BLUE}   ${WORKSPACE_HOST}/apps/${APP_NAME}${NC}"
echo ""
echo "📊 View logs:"
echo "   databricks apps logs $APP_NAME"
echo ""
echo "🔄 Redeploy anytime:"
echo "   ./deploy.sh"
echo ""
