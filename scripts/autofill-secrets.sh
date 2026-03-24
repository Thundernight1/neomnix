#!/bin/bash
# Auto-fill secrets from docker-compose and .env files
# Interactive helper to populate secrets.env

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔍 Auto-detecting Secrets from Project${NC}"
echo "==========================================="
echo ""

# Initialize secrets.env if not exists
if [ ! -f "secrets.env" ]; then
    cp secrets.env.example secrets.env
    echo -e "${GREEN}✅${NC} Created secrets.env"
fi

# Function to prompt user
prompt_value() {
    local var=$1
    local description=$2
    local default=$3
    local suggested=$4
    
    echo -n -e "${BLUE}$var${NC}"
    echo -n ": $description"
    
    if [ -n "$default" ]; then
        echo -n " (current: $default)"
    elif [ -n "$suggested" ]; then
        echo -n " (suggested: $suggested)"
    fi
    
    echo ""
    echo -n "> "
    read -r value
    
    # Use default if empty
    if [ -z "$value" ] && [ -n "$default" ]; then
        value="$default"
    fi
    
    if [ -n "$value" ]; then
        # Escape special characters for sed
        value_escaped=$(printf '%s\n' "$value" | sed -e 's/[\/&]/\\&/g')
        sed -i.bak "s/^${var}=.*/${var}=${value_escaped}/" secrets.env
        echo -e "${GREEN}✅${NC} Set"
    else
        echo -e "${YELLOW}⏭️  Skipped${NC}"
    fi
    echo ""
}

# Try to auto-detect values from project files
echo -e "${BLUE}🔎 Auto-detecting values...${NC}"
echo ""

# 1. Look for JWT_SECRET_KEY
if grep -q "JWT_SECRET_KEY" docker-compose.yml 2>/dev/null; then
    JWT_FROM_COMPOSE=$(grep "JWT_SECRET_KEY" docker-compose.yml | head -1 | cut -d'=' -f2 | xargs)
    echo -e "${GREEN}Found JWT_SECRET_KEY in docker-compose${NC}"
    echo "  Value: $JWT_FROM_COMPOSE"
fi

# 2. Look for OLLAMA_API_KEY
if grep -q "OLLAMA_API_KEY" docker-compose.yml 2>/dev/null; then
    OLLAMA_FROM_COMPOSE=$(grep "OLLAMA_API_KEY" docker-compose.yml | head -1 | cut -d'=' -f2 | xargs)
    echo -e "${GREEN}Found OLLAMA_API_KEY in docker-compose${NC}"
    echo "  Value: $OLLAMA_FROM_COMPOSE"
fi

# 3. Look for ZAP_API_KEY
if grep -q "ZAP_API_KEY" docker-compose.yml 2>/dev/null; then
    ZAP_FROM_COMPOSE=$(grep "ZAP_API_KEY" docker-compose.yml | head -1 | sed 's/.*ZAP_API_KEY.*-//' | xargs)
    echo -e "${GREEN}Found ZAP_API_KEY in docker-compose${NC}"
    echo "  Value: $ZAP_FROM_COMPOSE"
fi

# 4. Look for DATABASE_URL
if [ -f ".env" ]; then
    if grep -q "DATABASE_URL" .env 2>/dev/null; then
        DB_FROM_ENV=$(grep "DATABASE_URL" .env | cut -d'=' -f2 | xargs)
        echo -e "${GREEN}Found DATABASE_URL in .env${NC}"
        echo "  Value: ***hidden***"
    fi
fi

echo ""
echo -e "${BLUE}📝 Interactive Setup${NC}"
echo "=================="
echo ""

# REQUIRED SECRETS
echo -e "${YELLOW}⭐ REQUIRED SECRETS (Must Fill)${NC}"
echo ""

# 1. JWT_SECRET_KEY
echo "1️⃣  JWT Secret Key"
echo "   Generate new: openssl rand -hex 32"
echo ""
prompt_value "JWT_SECRET_KEY" "Random 32+ character secret" "" "$JWT_FROM_COMPOSE"

# 2. OLLAMA_API_KEY
echo "2️⃣  Ollama API Key"
echo "   Check: docker-compose.yml"
echo ""
prompt_value "OLLAMA_API_KEY" "Your Ollama API key" "" "$OLLAMA_FROM_COMPOSE"

# 3. ZAP_API_KEY
echo "3️⃣  OWASP ZAP API Key"
echo "   Check: docker-compose.yml"
echo ""
prompt_value "ZAP_API_KEY" "ZAP security scanner key" "" "$ZAP_FROM_COMPOSE"

echo ""
echo -e "${YELLOW}📍 STAGING ENVIRONMENT (Optional)${NC}"
echo ""

prompt_value "STAGING_HOST" "Staging server hostname/IP" ""
prompt_value "STAGING_USER" "Staging SSH username" "" "deploy"
prompt_value "STAGING_SSH_KEY" "Staging SSH key (base64)" ""

echo ""
echo -e "${YELLOW}🏢 PRODUCTION ENVIRONMENT${NC}"
echo ""

prompt_value "PROD_HOST" "Production server hostname/IP" ""
prompt_value "PROD_USER" "Production SSH username" "" "deploy"
prompt_value "PROD_SSH_KEY" "Production SSH key (base64)" ""
prompt_value "ADMIN_EMAIL" "Admin email address" "" "admin@cybersurx.io"
prompt_value "ADMIN_DEFAULT_PASSWORD" "Admin password (will be changed)" ""
prompt_value "DATABASE_URL" "PostgreSQL connection URL" "" "$DB_FROM_ENV"
prompt_value "REDIS_PASSWORD" "Redis password" ""

echo ""
echo -e "${YELLOW}🔍 OPTIONAL - ERROR TRACKING${NC}"
echo ""

prompt_value "SENTRY_DSN_STAGING" "Sentry DSN for staging" ""
prompt_value "SENTRY_DSN_PRODUCTION" "Sentry DSN for production" ""

echo ""
echo -e "${YELLOW}📢 OPTIONAL - NOTIFICATIONS${NC}"
echo ""

prompt_value "SLACK_WEBHOOK" "Slack webhook URL" ""

echo ""
echo -e "${YELLOW}☁️  OPTIONAL - KUBERNETES${NC}"
echo ""

prompt_value "K8S_KUBECONFIG" "Kubeconfig (base64)" ""

echo ""
echo -e "${YELLOW}🌐 OPTIONAL - AWS${NC}"
echo ""

prompt_value "AWS_ACCESS_KEY_ID" "AWS access key" ""
prompt_value "AWS_SECRET_ACCESS_KEY" "AWS secret key" ""
prompt_value "AWS_REGION" "AWS region" "" "us-east-1"

# Summary
echo ""
echo -e "${GREEN}======================================"
echo "✅ SETUP COMPLETE"
echo "======================================${NC}"
echo ""

# Show filled values (masked)
echo "📋 Filled secrets:"
echo ""
cat secrets.env | grep -v "^#" | grep -v "^$" | sed 's/=.*/=***/' 

echo ""
echo "📝 Next steps:"
echo "1. Review secrets.env (nano secrets.env)"
echo "2. Upload to GitHub:"
echo "   ./scripts/setup-deployment-env.sh --org YOUR_ORG --repo cybersurx --file secrets.env"
echo "3. Delete local copy: rm secrets.env"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: Never commit secrets.env to git!${NC}"
