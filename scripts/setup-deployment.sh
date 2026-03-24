#!/bin/bash
# Setup deployment infrastructure
# Configures GitHub Secrets, SSH keys, and environment files

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🚀 CyberSurX Deployment Setup"
echo "============================="
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI (gh) not found${NC}"
    echo "Install from: https://cli.github.com"
    exit 1
fi

# Check if already authenticated
if ! gh auth status > /dev/null 2>&1; then
    echo "🔐 GitHub authentication required"
    gh auth login
else
    echo -e "${GREEN}✅ Already authenticated with GitHub${NC}"
fi
echo ""

# Get repository info
echo "📦 Getting repository information..."
if ! REPO=$(gh repo view --json nameWithOwner -q 2>/dev/null); then
    echo -e "${RED}❌ Could not get repository info${NC}"
    echo "Make sure you're in a git repository or specify GITHUB_REPOSITORY"
    exit 1
fi
echo "📦 Repository: $REPO"
echo ""

# Function to set secret
set_secret() {
    local name=$1
    local prompt=$2
    
    echo -n "$prompt: "
    read -rs value
    echo ""
    
    if [ -z "$value" ]; then
        echo -e "${YELLOW}⚠️  Skipped${NC}"
        return
    fi
    
    echo "$value" | gh secret set "$name"
    echo -e "${GREEN}✅ Set$NC"
}

# Staging Secrets
echo "📍 Staging Environment Secrets"
echo "-------------------------------"
set_secret "STAGING_HOST" "Staging server hostname"
set_secret "STAGING_USER" "Staging SSH user"
set_secret "STAGING_SSH_KEY" "Staging SSH private key (base64 encoded)"
echo ""

# Production Secrets
echo "📍 Production Environment Secrets"
echo "---------------------------------"
set_secret "PROD_HOST" "Production server hostname"
set_secret "PROD_USER" "Production SSH user"
set_secret "PROD_SSH_KEY" "Production SSH private key (base64 encoded)"
echo ""

# API Secrets
echo "🔑 API & Service Keys"
echo "---------------------"
set_secret "OLLAMA_API_KEY" "Ollama API key"
set_secret "ZAP_API_KEY" "OWASP ZAP API key"
set_secret "JWT_SECRET_KEY" "JWT secret key (min 32 chars)"
echo ""

# Optional: Production DB & Admin
read -p "Configure production database settings? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    set_secret "DATABASE_URL" "Production database URL"
    set_secret "ADMIN_EMAIL" "Admin email"
    set_secret "ADMIN_DEFAULT_PASSWORD" "Admin initial password"
    set_secret "REDIS_PASSWORD" "Redis password"
fi
echo ""

# Optional: Error tracking
read -p "Configure Sentry error tracking? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    set_secret "SENTRY_DSN_STAGING" "Sentry DSN (Staging)"
    set_secret "SENTRY_DSN_PRODUCTION" "Sentry DSN (Production)"
fi
echo ""

# Optional: Slack notifications
read -p "Configure Slack notifications? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    set_secret "SLACK_WEBHOOK" "Slack webhook URL"
fi
echo ""

# Optional: AWS
read -p "Configure AWS for ECS deployments? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    set_secret "AWS_ACCESS_KEY_ID" "AWS access key"
    set_secret "AWS_SECRET_ACCESS_KEY" "AWS secret key"
    set_secret "AWS_REGION" "AWS region"
fi
echo ""

# Setup Kubernetes config
read -p "Configure Kubernetes deployment? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔐 Base64 encode your kubeconfig file:"
    echo "   base64 -i ~/.kube/config"
    set_secret "K8S_KUBECONFIG" "Kubeconfig (base64 encoded)"
fi
echo ""

# Verify secrets
echo "✅ Verifying secrets..."
echo ""
gh secret list | head -20
echo ""

echo -e "${GREEN}✅ Deployment setup complete!${NC}"
echo ""
echo "📝 Next steps:"
echo "1. Create GitHub environments (Settings → Environments)"
echo "2. Create staging and production environment secrets"
echo "3. Configure branch protection rules"
echo "4. Setup production domain SSL certificates"
echo "5. Run: docker compose -f docker-compose.staging.yml up -d"
