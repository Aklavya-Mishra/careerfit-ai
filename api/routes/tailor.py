"""
POST /api/v1/tailor — accepts resume + JD, creates a job, starts pipeline.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import aiofiles
import structlog
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from core.config import get_settings
from core.job_manager import job_manager
from core.pipeline import run_pipeline

router = APIRouter(prefix="/api/v1", tags=["tailor"])
logger = structlog.get_logger(__name__)
settings = get_settings()

_ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",  # some browsers send this for docx
}
_ALLOWED_SUFFIXES = {".pdf", ".docx"}


async def _save_upload(upload: UploadFile, dest: Path) -> None:
    async with aiofiles.open(dest, "wb") as f:
        while chunk := await upload.read(1024 * 64):
            await f.write(chunk)


@router.post("/tailor")
async def tailor_resume(
    background_tasks: BackgroundTasks,
    resume: UploadFile = File(..., description="Resume file (PDF or DOCX)"),
    jd_file: UploadFile | None = File(default=None, description="JD file (PDF or DOCX), optional"),
    jd_text: str | None = Form(default=None, description="JD plain text, optional"),
):
    # Validate resume
    resume_suffix = Path(resume.filename or "").suffix.lower()
    if resume_suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(400, f"Resume must be PDF or DOCX, got: {resume_suffix or 'unknown'}")

    if not jd_file and not jd_text:
        raise HTTPException(400, "Provide either a JD file or JD text")

    # FastAPI may pass an UploadFile with empty filename when the field is omitted
    jd_file_valid = jd_file and jd_file.filename and jd_file.filename.strip()
    if not jd_file_valid and not (jd_text and jd_text.strip()):
        raise HTTPException(400, "Provide either a non-empty JD file or JD text")

    # Check file sizes
    file_id = str(uuid.uuid4())
    resume_path = settings.upload_dir / f"{file_id}_resume{resume_suffix}"

    await _save_upload(resume, resume_path)

    jd_path: Path | None = None
    if jd_file_valid:
        jd_suffix = Path(jd_file.filename or "").suffix.lower()
        if jd_suffix not in _ALLOWED_SUFFIXES:
            raise HTTPException(400, f"JD file must be PDF or DOCX, got: {jd_suffix}")
        jd_path = settings.upload_dir / f"{file_id}_jd{jd_suffix}"
        await _save_upload(jd_file, jd_path)

    job = job_manager.create_job(
        resume_path=resume_path,
        jd_path=jd_path,
        jd_text=jd_text,
    )

    background_tasks.add_task(run_pipeline, job)
    logger.info("tailor_job_created", job_id=job.job_id)

    return {"job_id": job.job_id, "status": "queued"}
