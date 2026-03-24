#!/usr/bin/env bash
# =============================================================================
#   AegisLoop GRC — One-Click Deployment Script (Linux / macOS)
#   Version: 2.0.0
#   Usage:  chmod +x setup.sh && ./setup.sh
# =============================================================================

set -euo pipefail

# ── Colors & Formatting ───────────────────────────────────────────────────────
BOLD='\033[1m'
DIM='\033[2m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
RESET='\033[0m'

# ── Banner ────────────────────────────────────────────────────────────────────
clear
echo ""
echo -e "${BLUE}${BOLD}"
echo "  ╔══════════════════════════════════════════════════════════╗"
echo "  ║                                                          ║"
echo "  ║          ██╗   ██╗  ██████╗  ██████╗                    ║"
echo "  ║          ██║   ██║ ██╔════╝ ██╔════╝                    ║"
echo "  ║          ███████║ ██║  ███╗ ██║                         ║"
echo "  ║          ██╔══██║ ██║   ██║ ██║                         ║"
echo "  ║          ██║  ██║ ╚██████╔╝ ╚██████╗                    ║"
echo "  ║          ╚═╝  ╚═╝  ╚═════╝   ╚═════╝                    ║"
echo "  ║                                                          ║"
echo "  ║    AegisLoop GRC — Enterprise Compliance Platform        ║"
echo "  ║    HIPAA · SOC 2 · NIST · ISO 27001                     ║"
echo "  ║                                                          ║"
echo "  ╚══════════════════════════════════════════════════════════╝"
echo -e "${RESET}"
echo -e "  ${DIM}Setup Script v2.0.0${RESET}"
echo ""

# ── Helper Functions ──────────────────────────────────────────────────────────
info()    { echo -e "  ${CYAN}ℹ${RESET}  $*"; }
success() { echo -e "  ${GREEN}✔${RESET}  $*"; }
warn()    { echo -e "  ${YELLOW}⚠${RESET}  $*"; }
error()   { echo -e "  ${RED}✘${RESET}  $*" >&2; }
section() { echo ""; echo -e "  ${WHITE}${BOLD}▶  $*${RESET}"; echo "  $(printf '─%.0s' {1..55})"; }

prompt_value() {
    local label="$1"
    local default_val="$2"
    local is_secret="${3:-false}"
    local result

    if [[ "$is_secret" == "true" ]]; then
        read -rsp "    ${label} [leave blank to use default]: " result
        echo ""
    else
        read -rp "    ${label} [default: ${default_val}]: " result
    fi

    if [[ -z "$result" ]]; then
        echo "$default_val"
    else
        echo "$result"
    fi
}

generate_secret() {
    # Generate a 48-character cryptographically random hex secret
    if command -v openssl &>/dev/null; then
        openssl rand -hex 24
    else
        # Fallback for systems without openssl
        cat /dev/urandom | tr -dc 'a-zA-Z0-9' | head -c 48 || true
    fi
}

# ── Step 1: Check Prerequisites ───────────────────────────────────────────────
section "Checking Prerequisites"

# Check Docker
if ! command -v docker &>/dev/null; then
    error "Docker is not installed or not in PATH."
    echo ""
    echo -e "  ${DIM}Install Docker Desktop from: https://www.docker.com/products/docker-desktop${RESET}"
    echo ""
    exit 1
fi
DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
success "Docker found (${DOCKER_VERSION})"

# Check Docker daemon is running
if ! docker info &>/dev/null 2>&1; then
    error "Docker daemon is not running. Please start Docker Desktop and try again."
    exit 1
fi
success "Docker daemon is running"

# Check Docker Compose (v2 plugin preferred, v1 as fallback)
COMPOSE_CMD=""
if docker compose version &>/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
    COMPOSE_VERSION=$(docker compose version --short 2>/dev/null || echo "v2")
    success "Docker Compose found (${COMPOSE_VERSION})"
elif command -v docker-compose &>/dev/null; then
    COMPOSE_CMD="docker-compose"
    COMPOSE_VERSION=$(docker-compose --version | awk '{print $3}' | tr -d ',')
    success "Docker Compose (standalone) found (${COMPOSE_VERSION})"
    warn "Consider upgrading to Docker Compose v2 (integrated with Docker CLI)."
else
    error "Docker Compose is not available."
    echo ""
    echo -e "  ${DIM}Install it via: https://docs.docker.com/compose/install/${RESET}"
    exit 1
fi

# ── Step 2: Interactive Configuration ─────────────────────────────────────────
section "Platform Configuration"
echo ""
echo -e "  ${DIM}You will be prompted to configure your AegisLoop GRC installation."
echo -e "  Press ENTER to accept the default value shown in brackets.${RESET}"
echo ""

ADMIN_EMAIL=$(prompt_value "Admin Email Address" "admin@aegisloop.io")
ADMIN_DEFAULT_PASSWORD=$(prompt_value "Admin Password (temporary — you will be prompted to change it on first login)" "AegisLoop2026!" "true")

echo ""
info "Generating a cryptographically secure JWT secret key..."
AUTO_JWT_SECRET=$(generate_secret)
JWT_SECRET_KEY=$(prompt_value "JWT Secret Key (auto-generated; press ENTER to use)" "$AUTO_JWT_SECRET" "true")

echo ""
echo -e "  ${DIM}LLM Model Selection:${RESET}"
echo -e "  ${DIM}  [1] qwen3-coder-next:cloud  (default, cloud-based)${RESET}"
echo -e "  ${DIM}  [2] ollama/codellama         (local Ollama server)${RESET}"
echo -e "  ${DIM}  [3] Enter a custom model name${RESET}"
echo ""
read -rp "    LLM Model choice [1/2/3, default: 1]: " LLM_CHOICE
case "${LLM_CHOICE:-1}" in
    2)  LLM_MODEL="ollama/codellama" ;;
    3)  read -rp "    Custom model name: " LLM_MODEL ;;
    *)  LLM_MODEL="qwen3-coder-next:cloud" ;;
esac
success "LLM Model: ${LLM_MODEL}"

echo ""
OLLAMA_API_KEY=$(prompt_value "LLM API Key (if required)" "" "true")

# ── Step 3: Generate .env File ────────────────────────────────────────────────
section "Writing Configuration"

ENV_FILE=".env"

cat > "$ENV_FILE" << EOF
# =============================================================================
# AegisLoop GRC — Runtime Configuration
# Generated by setup.sh on $(date -u "+%Y-%m-%d %H:%M:%S UTC")
# =============================================================================
# SECURITY: Do not commit this file to version control.

# Admin Account (used for initial database seed on first boot)
ADMIN_EMAIL=${ADMIN_EMAIL}
ADMIN_DEFAULT_PASSWORD=${ADMIN_DEFAULT_PASSWORD}

# JWT Authentication
# IMPORTANT: This secret signs all authentication tokens. Never expose it.
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_EXPIRE_MINUTES=480

# LLM Integration
OLLAMA_API_KEY=${OLLAMA_API_KEY}
LLM_MODEL=${LLM_MODEL}

# Database (SQLite default; replace with postgresql://... for production)
DATABASE_URL=sqlite:///./ralph_loop.db

# OWASP ZAP (internal security scanner)
ZAP_API_KEY=aegis-zap-internal-$(generate_secret | head -c 16)

# CORS — tighten to your domain in production
ALLOWED_ORIGINS=http://localhost:3000
EOF

success ".env configuration file written"

# ── Step 4: Build & Launch ────────────────────────────────────────────────────
section "Building & Launching AegisLoop GRC"
echo ""
info "This will pull Docker images and build the application. This may take 3-8 minutes on first run."
echo ""

# Bring down any previous instance cleanly
$COMPOSE_CMD down --remove-orphans 2>/dev/null || true

# Build and start in detached mode
$COMPOSE_CMD up -d --build

# ── Step 5: Health Check Wait ─────────────────────────────────────────────────
section "Waiting for Services to Become Ready"
echo ""

MAX_WAIT=120
WAITED=0
API_HEALTHY=false

while [[ $WAITED -lt $MAX_WAIT ]]; do
    if curl -sf "http://localhost:8000/health" &>/dev/null; then
        API_HEALTHY=true
        break
    fi
    printf "  ${DIM}Waiting for API service... (%ds)${RESET}\r" "$WAITED"
    sleep 3
    WAITED=$((WAITED + 3))
done

echo ""

if [[ "$API_HEALTHY" == "true" ]]; then
    success "API service is healthy"
else
    warn "API health check timed out after ${MAX_WAIT}s."
    warn "The application may still be starting. Check logs with: ${COMPOSE_CMD} logs api"
fi

# ── Step 6: Success Banner ─────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}"
echo "  ╔══════════════════════════════════════════════════════════╗"
echo "  ║                                                          ║"
echo "  ║       ✔  AegisLoop GRC is Ready!                         ║"
echo "  ║                                                          ║"
echo "  ╚══════════════════════════════════════════════════════════╝"
echo -e "${RESET}"

echo -e "  ${WHITE}${BOLD}Access the Platform${RESET}"
echo ""
echo -e "  ${CYAN}  Dashboard:${RESET}  http://localhost:3000"
echo -e "  ${CYAN}  API Docs:  ${RESET}  http://localhost:8000/docs"
echo ""
echo -e "  ${WHITE}${BOLD}Login Credentials${RESET}"
echo ""
echo -e "  ${CYAN}  Email:    ${RESET}  ${ADMIN_EMAIL}"
echo -e "  ${CYAN}  Password: ${RESET}  ${ADMIN_DEFAULT_PASSWORD}"
echo ""
echo -e "  ${YELLOW}  ⚠  You will be required to change this password on first login.${RESET}"
echo ""
echo -e "  ${WHITE}${BOLD}Useful Commands${RESET}"
echo ""
echo -e "  ${DIM}  View logs:       ${COMPOSE_CMD} logs -f${RESET}"
echo -e "  ${DIM}  Stop platform:   ${COMPOSE_CMD} down${RESET}"
echo -e "  ${DIM}  Restart:         ${COMPOSE_CMD} restart${RESET}"
echo -e "  ${DIM}  Apply branding:  edit theme.json, then ${COMPOSE_CMD} restart frontend${RESET}"
echo ""
echo -e "  ${DIM}  Full documentation: COMMERCIAL_QUICK_START.md${RESET}"
echo ""
