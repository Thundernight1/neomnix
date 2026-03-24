#!/bin/bash
# Interactive deployment secrets setup
# Non-interactive alternative to setup-deployment.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🚀 CyberSurX Deployment Setup (Interactive)"
echo "==========================================="
echo ""

# Get organization and repo
read -p "📦 GitHub Organization (e.g., your-org): " ORG
read -p "📦 GitHub Repository name: " REPO_NAME

FULL_REPO="$ORG/$REPO_NAME"
echo ""
echo "Target: $FULL_REPO"
echo ""

# Check gh CLI
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI (gh) not found${NC}"
    echo "Install from: https://cli.github.com"
    exit 1
fi

# Verify authentication
if ! gh auth status > /dev/null 2>&1; then
    echo -e "${RED}❌ Not authenticated with GitHub${NC}"
    echo "Run: gh auth login"
    exit 1
fi

echo -e "${GREEN}✅ Authenticated${NC}"
echo ""

# Function to set secret with validation
set_secret() {
    local name=$1
    local prompt=$2
    local required=${3:-false}
    
    echo -n "$prompt"
    if [ "$required" = "true" ]; then
        echo -n " (required): "
    else
        echo -n " (or press Enter to skip): "
    fi
    
    read -rs value
    echo ""
    
    if [ -z "$value" ]; then
        if [ "$required" = "true" ]; then
            echo -e "${RED}❌ This field is required${NC}"
            set_secret "$name" "$prompt" "$required"
            return
        else
            echo -e "${YELLOW}⏭️  Skipped${NC}"
            return
        fi
    fi
    
    if echo "$value" | gh secret set -a "$FULL_REPO" "$name" 2>/dev/null; then
        echo -e "${GREEN}✅ Secret set: $name${NC}"
    else
        echo -e "${RED}❌ Failed to set secret: $name${NC}"
        echo "Make sure you have push access to $FULL_REPO"
    fi
}

# Clear prompts
echo ""
echo "======================================"
echo "🔐 REQUIRED SECRETS"
echo "======================================"
echo ""

set_secret "JWT_SECRET_KEY" "JWT Secret Key (min 32 random chars)" "true"
set_secret "OLLAMA_API_KEY" "Ollama API Key" "true"
set_secret "ZAP_API_KEY" "OWASP ZAP API Key" "true"

echo ""
echo "======================================"
echo "📍 STAGING ENVIRONMENT"
echo "======================================"
echo ""

set_secret "STAGING_HOST" "Staging server hostname/IP"
set_secret "STAGING_USER" "Staging SSH username"
set_secret "STAGING_SSH_KEY" "Staging SSH private key (base64 encoded)"

echo ""
echo "======================================"
echo "🏢 PRODUCTION ENVIRONMENT"
echo "======================================"
echo ""

set_secret "PROD_HOST" "Production server hostname/IP"
set_secret "PROD_USER" "Production SSH username"
set_secret "PROD_SSH_KEY" "Production SSH private key (base64 encoded)"
set_secret "ADMIN_EMAIL" "Admin email address"
set_secret "ADMIN_DEFAULT_PASSWORD" "Admin initial password"
set_secret "DATABASE_URL" "Production database URL"
set_secret "REDIS_PASSWORD" "Redis password"

echo ""
echo "======================================"
echo "🔍 OPTIONAL: ERROR TRACKING"
echo "======================================"
echo ""

set_secret "SENTRY_DSN_STAGING" "Sentry DSN (Staging)"
set_secret "SENTRY_DSN_PRODUCTION" "Sentry DSN (Production)"

echo ""
echo "======================================"
echo "📢 OPTIONAL: NOTIFICATIONS"
echo "======================================"
echo ""

set_secret "SLACK_WEBHOOK" "Slack webhook URL"

echo ""
echo "======================================"
echo "☁️  OPTIONAL: KUBERNETES"
echo "======================================"
echo ""

set_secret "K8S_KUBECONFIG" "Kubeconfig file (base64 encoded)"

echo ""
echo "======================================"
echo "🌐 OPTIONAL: AWS (ECS DEPLOYMENTS)"
echo "======================================"
echo ""

set_secret "AWS_ACCESS_KEY_ID" "AWS Access Key ID"
set_secret "AWS_SECRET_ACCESS_KEY" "AWS Secret Access Key"
set_secret "AWS_REGION" "AWS Region (e.g., us-east-1)"

echo ""
echo "======================================"
echo "✅ SETUP COMPLETE"
echo "======================================"
echo ""

# List secrets
echo "📝 Configured secrets:"
if gh secret list -a "$FULL_REPO" 2>/dev/null | head -10; then
    true
else
    echo "Could not list secrets. Verify manually in GitHub repository settings."
fi

echo ""
echo "📋 Next steps:"
echo "1. Go to: https://github.com/$FULL_REPO/settings/environments"
echo "2. Create 'staging' and 'production' environments"
echo "3. Add environment-specific secrets as needed"
echo "4. Setup branch protection for 'main' branch"
echo "5. Test: gh workflow run deploy-staging.yml"
echo ""
