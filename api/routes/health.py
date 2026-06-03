"""
GET /api/v1/health — liveness + Ollama connectivity check.
"""
from __future__ import annotations

import httpx
import structlog
from fastapi import APIRouter

from core.config import get_settings
from core.models import HealthResponse

router = APIRouter(prefix="/api/v1", tags=["health"])
logger = structlog.get_logger(__name__)
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    ollama_connected = False
    model_available = False

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            if r.status_code == 200:
                ollama_connected = True
                tags = r.json().get("models", [])
                model_names = [t.get("name", "") for t in tags]
                model_available = any(settings.ollama_model in n for n in model_names)
    except Exception as e:
        logger.warning("ollama_health_check_failed", error=str(e))

    return HealthResponse(
        status="ok" if ollama_connected else "degraded",
        ollama_connected=ollama_connected,
        model_available=model_available,
        version=settings.app_version,
    )
