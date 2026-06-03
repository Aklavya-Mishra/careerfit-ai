"""
Job management routes:
  GET  /api/v1/jobs/{id}/stream   — SSE progress stream
  GET  /api/v1/jobs/{id}/result   — final result JSON
  GET  /api/v1/jobs/{id}/download/docx
  GET  /api/v1/jobs/{id}/download/pdf
  DELETE /api/v1/jobs/{id}
"""
from __future__ import annotations

from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from core.config import get_settings
from core.job_manager import job_manager
from core.models import JobStatus

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])
logger = structlog.get_logger(__name__)
settings = get_settings()


def _get_job_or_404(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    return job


@router.get("/{job_id}/stream")
async def stream_job_events(job_id: str):
    job = _get_job_or_404(job_id)

    async def event_generator():
        async for chunk in job_manager.stream_events(job):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/{job_id}/result")
async def get_job_result(job_id: str):
    job = _get_job_or_404(job_id)
    if job.status == JobStatus.FAILED:
        raise HTTPException(500, job.result.error if job.result else "Pipeline failed")
    if job.status != JobStatus.COMPLETE:
        return {"job_id": job_id, "status": job.status, "result": None}
    return {"job_id": job_id, "status": job.status, "result": job.result}


@router.get("/{job_id}/download/docx")
async def download_docx(job_id: str):
    job = _get_job_or_404(job_id)
    if job.status != JobStatus.COMPLETE or not job.result:
        raise HTTPException(400, "Job not complete yet")
    path = settings.output_dir / f"{job_id}_tailored.docx"
    if not path.exists():
        raise HTTPException(404, "DOCX file not found")
    return FileResponse(
        path=str(path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="tailored_resume.docx",
    )


@router.get("/{job_id}/download/pdf")
async def download_pdf(job_id: str):
    job = _get_job_or_404(job_id)
    if job.status != JobStatus.COMPLETE or not job.result:
        raise HTTPException(400, "Job not complete yet")
    path = settings.output_dir / f"{job_id}_tailored.pdf"
    if not path.exists():
        raise HTTPException(404, "PDF file not found")
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename="tailored_resume.pdf",
    )


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    _get_job_or_404(job_id)
    job_manager.delete_job(job_id)
    return {"deleted": True, "job_id": job_id}
