#!/bin/bash
# Non-interactive setup - read secrets from environment or file
# Usage:
#   ./setup-deployment-env.sh --org myorg --repo myrepo --file secrets.env
#   or set environment variables: GITHUB_ORG, GITHUB_REPO, etc.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --org) GITHUB_ORG="$2"; shift 2 ;;
        --repo) GITHUB_REPO="$2"; shift 2 ;;
        --file) SECRETS_FILE="$2"; shift 2 ;;
        --help) 
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --org ORG         GitHub organization"
            echo "  --repo REPO       GitHub repository"
            echo "  --file FILE       Secrets file (.env format)"
            echo "  --help           This help message"
            echo ""
            echo "Environment variables:"
            echo "  GITHUB_ORG       GitHub organization"
            echo "  GITHUB_REPO      GitHub repository"
            echo "  SECRETS_FILE     Path to secrets file"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Use environment variables as fallback
GITHUB_ORG=${GITHUB_ORG:-.}
GITHUB_REPO=${GITHUB_REPO:-.}

if [ "$GITHUB_ORG" = "." ] || [ "$GITHUB_REPO" = "." ]; then
    echo -e "${YELLOW}Reading from current git repository...${NC}"
    if ! REPO_INFO=$(gh repo view --json nameWithOwner -q 2>/dev/null); then
        echo -e "${RED}❌ Could not determine repository${NC}"
        echo "Provide: --org ORG --repo REPO"
        exit 1
    fi
    GITHUB_ORG=$(echo "$REPO_INFO" | cut -d'/' -f1)
    GITHUB_REPO=$(echo "$REPO_INFO" | cut -d'/' -f2)
fi

FULL_REPO="$GITHUB_ORG/$GITHUB_REPO"

echo "🚀 CyberSurX Deployment Setup (Non-Interactive)"
echo "==============================================="
echo "📦 Repository: $FULL_REPO"
echo ""

# Load secrets from file if provided
if [ -n "$SECRETS_FILE" ] && [ -f "$SECRETS_FILE" ]; then
    echo "📁 Loading secrets from: $SECRETS_FILE"
    source "$SECRETS_FILE"
fi

# Check gh CLI
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI (gh) not found${NC}"
    exit 1
fi

# Verify authentication
if ! gh auth status > /dev/null 2>&1; then
    echo -e "${RED}❌ Not authenticated${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Authenticated${NC}"
echo ""

# List of required secrets
declare -A REQUIRED_SECRETS=(
    ["JWT_SECRET_KEY"]="JWT secret key (min 32 chars)"
    ["OLLAMA_API_KEY"]="Ollama API key"
    ["ZAP_API_KEY"]="OWASP ZAP API key"
)

# List of optional secrets
declare -A OPTIONAL_SECRETS=(
    ["STAGING_HOST"]="Staging server hostname"
    ["STAGING_USER"]="Staging SSH user"
    ["STAGING_SSH_KEY"]="Staging SSH key"
    ["PROD_HOST"]="Production server hostname"
    ["PROD_USER"]="Production SSH user"
    ["PROD_SSH_KEY"]="Production SSH key"
    ["ADMIN_EMAIL"]="Admin email"
    ["ADMIN_DEFAULT_PASSWORD"]="Admin password"
    ["DATABASE_URL"]="Database URL"
    ["REDIS_PASSWORD"]="Redis password"
    ["SENTRY_DSN_STAGING"]="Sentry DSN (Staging)"
    ["SENTRY_DSN_PRODUCTION"]="Sentry DSN (Production)"
    ["SLACK_WEBHOOK"]="Slack webhook"
    ["K8S_KUBECONFIG"]="Kubeconfig"
    ["AWS_ACCESS_KEY_ID"]="AWS key ID"
    ["AWS_SECRET_ACCESS_KEY"]="AWS secret key"
    ["AWS_REGION"]="AWS region"
)

# Function to set secret
set_secret() {
    local name=$1
    local value=${!name}
    
    if [ -z "$value" ]; then
        return 1
    fi
    
    if echo "$value" | gh secret set -a "$FULL_REPO" "$name" 2>/dev/null; then
        echo -e "${GREEN}✅${NC} $name"
        return 0
    else
        echo -e "${RED}❌${NC} $name (failed)"
        return 1
    fi
}

# Set required secrets
echo "🔐 Required Secrets:"
MISSING=0
for secret in "${!REQUIRED_SECRETS[@]}"; do
    if ! set_secret "$secret"; then
        echo "   ${REQUIRED_SECRETS[$secret]}"
        MISSING=$((MISSING + 1))
    fi
done

if [ $MISSING -gt 0 ]; then
    echo ""
    echo -e "${RED}❌ Missing $MISSING required secrets${NC}"
    echo ""
    echo "Set environment variables:"
    for secret in "${!REQUIRED_SECRETS[@]}"; do
        echo "  export $secret='value'"
    done
    exit 1
fi

echo ""
echo "📍 Optional Secrets:"
for secret in "${!OPTIONAL_SECRETS[@]}"; do
    set_secret "$secret" || true
done

echo ""
echo "======================================"
echo -e "${GREEN}✅ Setup Complete${NC}"
echo "======================================"
echo ""
echo "📋 Next steps:"
echo "1. Create GitHub environments:"
echo "   https://github.com/$FULL_REPO/settings/environments"
echo "2. Setup branch protection for 'main'"
echo "3. Test deployment:"
echo "   gh workflow run deploy-staging.yml"
echo ""
