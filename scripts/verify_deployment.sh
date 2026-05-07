#!/bin/bash
# Deployment verification script
# Checks health of all services post-deployment

set -e

TIMEOUT=300
INTERVAL=5
START_TIME=$(date +%s)

echo "🔍 Starting deployment verification..."
echo "⏱️  Timeout: ${TIMEOUT}s"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check endpoint
check_endpoint() {
    local url=$1
    local name=$2
    local max_attempts=$((TIMEOUT / INTERVAL))
    local attempt=0
    
    echo -n "🔗 Checking $name... "
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ OK${NC}"
            return 0
        fi
        
        attempt=$((attempt + 1))
        if [ $((attempt % 6)) -eq 0 ]; then
            echo -n "."
        fi
        sleep $INTERVAL
    done
    
    echo -e "${RED}❌ FAILED (timeout)${NC}"
    return 1
}

# Function to check container
check_container() {
    local container=$1
    local name=$2
    
    echo -n "📦 Checking $name container... "
    
    if docker ps | grep -q "$container"; then
        echo -e "${GREEN}✅ Running${NC}"
        return 0
    else
        echo -e "${RED}❌ Not running${NC}"
        docker compose logs "$container" 2>/dev/null || true
        return 1
    fi
}

# Check if docker compose is available
if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}❌ docker compose not found${NC}"
    exit 1
fi

echo "📊 Deployment Status"
echo "===================="
echo ""

# Determine environment
if [ -f "docker-compose.prod.yml" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    ENV="production"
elif [ -f "docker-compose.staging.yml" ]; then
    COMPOSE_FILE="docker-compose.staging.yml"
    ENV="staging"
else
    COMPOSE_FILE="docker-compose.yml"
    ENV="development"
fi

echo "Environment: $ENV"
echo "Compose file: $COMPOSE_FILE"
echo ""

# Run checks
FAILED=0

# Check containers
echo "Container Status:"
echo "-----------------"
check_container "api" "Backend API" || FAILED=$((FAILED + 1))
check_container "frontend" "Frontend" || FAILED=$((FAILED + 1))
check_container "redis" "Redis Cache" || FAILED=$((FAILED + 1))
check_container "worker" "Celery Worker" || FAILED=$((FAILED + 1))
echo ""

# Check services
echo "Service Health:"
echo "---------------"
check_endpoint "http://localhost:8000/health" "API Health" || FAILED=$((FAILED + 1))
check_endpoint "http://localhost:3000" "Frontend" || FAILED=$((FAILED + 1))
echo ""

# Check Redis
echo -n "🔗 Checking Redis... "
if docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
    FAILED=$((FAILED + 1))
fi
echo ""

# Get stats
echo "Resource Usage:"
echo "---------------"
docker compose stats --no-stream 2>/dev/null || true
echo ""

# Final status
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "📍 Service URLs:"
    echo "   API: http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
    echo "   Frontend: http://localhost:3000"
    exit 0
else
    echo -e "${RED}❌ $FAILED checks failed${NC}"
    echo ""
    echo "Debug information:"
    docker compose ps
    docker compose logs --tail=50
    exit 1
fi
