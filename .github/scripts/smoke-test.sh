#!/usr/bin/env bash
# Neomnix Beta Demo Smoke Tests
# Exits non-zero if any health check fails

set -euo pipefail

API_URL="http://localhost:8000"
FE_URL="http://localhost:3000"
TIMEOUT=180
INTERVAL=5
CURL_OPTS="-s -o /dev/null -w %{http_code} --connect-timeout 5 --max-time 8"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "  Neomnix Beta Demo Smoke Tests"
echo "  Timeout: ${TIMEOUT}s per service"
echo "========================================"
echo ""

attempt=0
max_attempts=$((TIMEOUT / INTERVAL))

# ─────────────────────────────────────────────────────────────────────────────
# Helper: wait_for
# ─────────────────────────────────────────────────────────────────────────────
wait_for() {
    local url=$1
    local name=$2
    local expect_code=${3:-200}
    local attempt=0

    echo -n "  🔍 $name ... "

    while [ $attempt -lt $max_attempts ]; do
        local code
        code=$(curl ${CURL_OPTS} "$url" 2>/dev/null || true)
        if [ "$code" = "$expect_code" ]; then
            echo -e "${GREEN}✅ up${NC}"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep $INTERVAL
    done

    echo -e "${RED}❌ timeout${NC} (last status: ${code:-none})"
    return 1
}

echo "Stage 1: Container health checks"
echo "--------------------------------"

wait_for "$API_URL/health"     "API /health"      && api_ok=1 || api_ok=0
wait_for "$FE_URL"            "Frontend root"    && fe_ok=1    || fe_ok=0

echo ""
echo "Stage 2: API functional checks"
echo "--------------------------------"

login_err=""
if [ $api_ok -eq 1 ]; then
    # Test auth login returns 401 without credentials (endpoint reachable)
    resp=$(curl ${CURL_OPTS} -X POST "$API_URL/auth/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=test&password=test" 2>/dev/null || true)
    if [ "$resp" = "401" ] || [ "$resp" = "422" ]; then
        echo -e "  🔍 Auth login endpoint    ${GREEN}✅ reachable${NC}"
        login_ok=1
    else
        echo -e "  🔍 Auth login endpoint    ${RED}❌ unexpected status $resp${NC}"
        login_ok=0
    fi

    # Test billing/status (no auth required)
    bill=$(curl -s --connect-timeout 5 --max-time 8 "$API_URL/billing/status" 2>/dev/null || true)
    if echo "$bill" | grep -q '"enabled"'; then
        echo -e "  🔍 Billing status endpoint ${GREEN}✅ reachable${NC}"
        billing_ok=1
    else
        echo -e "  🔍 Billing status endpoint ${RED}❌ failed${NC}"
        billing_ok=0
    fi
else
    login_ok=0
    billing_ok=0
fi

echo ""
echo "Stage 3: Frontend content checks"
echo "--------------------------------"

if [ $fe_ok -eq 1 ]; then
    body=$(curl -s --connect-timeout 5 --max-time 8 "$FE_URL" 2>/dev/null || true)
    if echo "$body" | grep -qi "neomnix\|login\|sign in\|div"; then
        echo -e "  🔍 HTML body present       ${GREEN}✅ OK${NC}"
        content_ok=1
    else
        echo -e "  🔍 HTML body present       ${RED}❌ empty or unexpected${NC}"
        content_ok=0
    fi
else
    content_ok=0
fi

echo ""
echo "========================================"
echo "           SMOKE TEST SUMMARY"
echo "========================================"

total=0
pass=0

report() {
    local label=$1
    local ok=$2
    total=$((total + 1))
    if [ $ok -eq 1 ]; then
        pass=$((pass + 1))
        echo -e "  ${GREEN}PASS${NC}  $label"
    else
        echo -e "  ${RED}FAIL${NC}  $label"
    fi
}

report "API /health"                "$api_ok"
report "Frontend root"              "$fe_ok"
report "Auth endpoint reachable"    "$login_ok"
report "Billing endpoint"           "$billing_ok"
report "Frontend content"           "$content_ok"

echo ""
echo "Result: $pass/$total passed"

if [ $pass -ne $total ]; then
    echo ""
    echo "Fetching container logs (last 50 lines):"
    echo "----------------------------------------"
    docker compose -f docker-compose.beta.yml logs --tail=50 --no-color || true
    exit 1
fi

echo ""
echo -e "${GREEN}✅ All smoke tests passed!${NC}"
echo ""
echo "Service URLs:"
echo "  API:      $API_URL"
echo "  API Docs: $API_URL/docs"
echo "  Frontend: $FE_URL"
