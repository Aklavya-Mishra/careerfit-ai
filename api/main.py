"""
careerfit-ai FastAPI application entrypoint.
"""
import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.job_manager import job_manager
from routes.health import router as health_router
from routes.jobs import router as jobs_router
from routes.tailor import router as tailor_router
from utils.logger import configure_logging

configure_logging()
logger = structlog.get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("careerfit-ai_starting", version=settings.app_version)

    # Pre-load embedding model at startup to avoid cold start on first request
    try:
        from nlp.embedder import get_embedder
        get_embedder()
        logger.info("embedding_model_preloaded")
    except Exception as e:
        logger.warning("embedding_model_preload_failed", error=str(e))

    # Start periodic job cleanup task
    async def cleanup_loop():
        while True:
            await asyncio.sleep(300)  # every 5 minutes
            job_manager.cleanup_expired()

    cleanup_task = asyncio.create_task(cleanup_loop())

    yield

    cleanup_task.cancel()
    logger.info("careerfit-ai_shutdown")


app = FastAPI(
    title="careerfit-ai API",
    description="LLM-powered resume tailoring engine",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(tailor_router)
app.include_router(jobs_router)


@app.get("/")
async def root():
    return {"service": "careerfit-ai", "version": settings.app_version, "docs": "/docs"}
