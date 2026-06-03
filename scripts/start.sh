#!/usr/bin/env bash
# careerfit-ai — Docker build + startup validation script
# Run this from the project root: ./scripts/start.sh
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
fail() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo ""
echo "  ██████╗ ███████╗███████╗██╗   ██╗███╗   ███╗███████╗"
echo "  ██╔══██╗██╔════╝██╔════╝██║   ██║████╗ ████║██╔════╝"
echo "  ██████╔╝█████╗  ███████╗██║   ██║██╔████╔██║█████╗  "
echo "  ██╔══██╗██╔══╝  ╚════██║██║   ██║██║╚██╔╝██║██╔══╝  "
echo "  ██║  ██║███████╗███████║╚██████╔╝██║ ╚═╝ ██║███████╗"
echo "  ╚═╝  ╚═╝╚══════╝╚══════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝"
echo "  ██████╗  ██████╗ ██████╗  ██████╗ ███████╗"
echo "  ██╔══██╗██╔═══██╗██╔══██╗██╔════╝ ██╔════╝"
echo "  ██████╔╝██║   ██║██████╔╝██║  ███╗█████╗  "
echo "  ██╔══██╗██║   ██║██╔══██╗██║   ██║██╔══╝  "
echo "  ██║  ██║╚██████╔╝██║  ██║╚██████╔╝███████╗"
echo "  ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝"
echo ""

# -----------------------------------------------------------------------
# Pre-flight checks
# -----------------------------------------------------------------------
log "Checking prerequisites..."

command -v docker >/dev/null 2>&1 || fail "Docker not found. Install: https://docs.docker.com/get-docker/"
command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1 || \
  docker-compose version >/dev/null 2>&1 || fail "Docker Compose not found."

GPU_MODE=false
if docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu20.04 nvidia-smi >/dev/null 2>&1; then
  GPU_MODE=true
  log "NVIDIA GPU detected — enabling GPU mode"
else
  warn "No GPU detected — running in CPU mode (slower inference)"
  warn "CPU model: qwen2.5:3b will be used instead of llama3.1:8b"
fi

# -----------------------------------------------------------------------
# Setup .env
# -----------------------------------------------------------------------
if [ ! -f .env ]; then
  cp .env.example .env
  if [ "$GPU_MODE" = false ]; then
    sed -i 's/OLLAMA_MODEL=llama3.1:8b/OLLAMA_MODEL=qwen2.5:3b/' .env
  fi
  log ".env created from .env.example"
fi

# -----------------------------------------------------------------------
# Start services
# -----------------------------------------------------------------------
log "Starting Docker Compose stack..."

if [ "$GPU_MODE" = true ]; then
  COMPOSE_CMD="docker compose -f docker-compose.yml -f docker-compose.gpu.yml"
else
  COMPOSE_CMD="docker compose -f docker-compose.yml"
fi

$COMPOSE_CMD up -d --build

# -----------------------------------------------------------------------
# Pull Ollama model
# -----------------------------------------------------------------------
MODEL=$(grep OLLAMA_MODEL .env | cut -d= -f2 | tr -d '"' | tr -d "'")
MODEL=${MODEL:-llama3.1:8b}

log "Waiting for Ollama to start..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
    break
  fi
  sleep 2
  if [ $i -eq 30 ]; then
    fail "Ollama didn't start in 60s. Check: docker logs careerfit-ai-ollama"
  fi
done

log "Pulling model: $MODEL (this may take a few minutes on first run)..."
docker exec careerfit-ai-ollama ollama pull "$MODEL"
log "Model $MODEL ready"

# -----------------------------------------------------------------------
# Health check
# -----------------------------------------------------------------------
log "Waiting for API to start..."
for i in $(seq 1 20); do
  if curl -sf http://localhost:8000/api/v1/health >/dev/null 2>&1; then
    break
  fi
  sleep 3
  if [ $i -eq 20 ]; then
    fail "API didn't start in 60s. Check: docker logs careerfit-ai-api"
  fi
done

HEALTH=$(curl -s http://localhost:8000/api/v1/health)
log "API healthy: $HEALTH"

# -----------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  careerfit-ai is running!${NC}"
echo ""
echo -e "  🌐 Web UI:  ${YELLOW}http://localhost:3000${NC}"
echo -e "  🔧 API:     ${YELLOW}http://localhost:8000${NC}"
echo -e "  📚 Docs:    ${YELLOW}http://localhost:8000/docs${NC}"
echo ""
echo -e "  Stop:  docker compose down"
echo -e "  Logs:  docker compose logs -f"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
