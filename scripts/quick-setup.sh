#!/bin/bash
# ULTRA BASIT - Secrets'ı otomatik doldur ve yükle

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🚀 CYBERSURX DEPLOYMENT - ULTRA BASIT KURULUM"
echo "=============================================="
echo ""

# Step 1: Check prerequisites
echo "Step 1/4: Checking prerequisites..."
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI (gh) not found${NC}"
    echo "Install from: https://cli.github.com"
    exit 1
fi

if ! gh auth status > /dev/null 2>&1; then
    echo -e "${RED}❌ Not authenticated with GitHub${NC}"
    echo "Run: gh auth login"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites OK${NC}"
echo ""

# Step 2: Get org and repo
echo "Step 2/4: GitHub repository info"
read -p "GitHub organization: " ORG
read -p "GitHub repository: " REPO
FULL_REPO="$ORG/$REPO"
echo ""

# Step 3: Ask for minimal secrets
echo "Step 3/4: Essential secrets"
echo "Generate: openssl rand -hex 32"
read -sp "JWT_SECRET_KEY (paste and press Enter): " JWT_SECRET
echo ""

read -sp "OLLAMA_API_KEY: " OLLAMA_KEY
echo ""

read -sp "ZAP_API_KEY (or press Enter for default): " ZAP_KEY
ZAP_KEY=${ZAP_KEY:-aegis-zap-secret}
echo ""

# Optional: Production
read -p "Setup production env now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "PROD_HOST (e.g., prod.example.com): " PROD_HOST
    read -p "PROD_USER (e.g., deploy): " PROD_USER
    
    echo "For PROD_SSH_KEY, run this in another terminal:"
    echo "  base64 < ~/.ssh/id_rsa"
    read -sp "Then paste the output: " PROD_SSH_KEY
    echo ""
    
    read -p "ADMIN_EMAIL: " ADMIN_EMAIL
    read -sp "ADMIN_DEFAULT_PASSWORD: " ADMIN_PASSWORD
    echo ""
    
    read -p "DATABASE_URL (postgresql://...): " DATABASE_URL
fi

# Step 4: Upload secrets
echo ""
echo "Step 4/4: Uploading secrets to GitHub..."
echo ""

# Use -r flag for repository-specific secrets (not -a flag)
# Set required
echo "$JWT_SECRET" | gh secret set JWT_SECRET_KEY -r "$FULL_REPO" && echo -e "${GREEN}✅${NC} JWT_SECRET_KEY"
echo "$OLLAMA_KEY" | gh secret set OLLAMA_API_KEY -r "$FULL_REPO" && echo -e "${GREEN}✅${NC} OLLAMA_API_KEY"
echo "$ZAP_KEY" | gh secret set ZAP_API_KEY -r "$FULL_REPO" && echo -e "${GREEN}✅${NC} ZAP_API_KEY"

# Set production if provided
if [ -n "$PROD_HOST" ]; then
    echo "$PROD_HOST" | gh secret set PROD_HOST -r "$FULL_REPO" && echo -e "${GREEN}✅${NC} PROD_HOST"
    echo "$PROD_USER" | gh secret set PROD_USER -r "$FULL_REPO" && echo -e "${GREEN}✅${NC} PROD_USER"
    echo "$PROD_SSH_KEY" | gh secret set PROD_SSH_KEY -r "$FULL_REPO" && echo -e "${GREEN}✅${NC} PROD_SSH_KEY"
    echo "$ADMIN_EMAIL" | gh secret set ADMIN_EMAIL -r "$FULL_REPO" && echo -e "${GREEN}✅${NC} ADMIN_EMAIL"
    echo "$ADMIN_PASSWORD" | gh secret set ADMIN_DEFAULT_PASSWORD -r "$FULL_REPO" && echo -e "${GREEN}✅${NC} ADMIN_DEFAULT_PASSWORD"
    echo "$DATABASE_URL" | gh secret set DATABASE_URL -r "$FULL_REPO" && echo -e "${GREEN}✅${NC} DATABASE_URL"
fi

echo ""
echo -e "${GREEN}✅ SETUP COMPLETE!${NC}"
echo ""
echo "📋 Next steps:"
echo "1. Go to GitHub → Settings → Environments"
echo "   Create: 'staging' and 'production'"
echo ""
echo "2. Branch protection (Settings → Branches)"
echo "   For 'main': require review + status checks"
echo ""
echo "3. Test: push to develop branch"
echo "   git push origin develop"
echo ""
echo "4. Monitor: gh run watch"
echo ""
