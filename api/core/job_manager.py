"""
Job manager: tracks job state and provides SSE event queues.
Each job gets an asyncio.Queue; the SSE route drains it.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import AsyncIterator

import structlog

from core.config import get_settings
from core.models import JobEvent, JobResult, JobStatus

logger = structlog.get_logger(__name__)
settings = get_settings()


class Job:
    def __init__(self, job_id: str, resume_path: Path, jd_path: Path | None, jd_text: str | None):
        self.job_id = job_id
        self.resume_path = resume_path
        self.jd_path = jd_path
        self.jd_text = jd_text
        self.status = JobStatus.QUEUED
        self.result: JobResult | None = None
        self.queue: asyncio.Queue[JobEvent | None] = asyncio.Queue()
        self.created_at = datetime.now(timezone.utc)
        self.expires_at = self.created_at + timedelta(seconds=settings.job_ttl_seconds)

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at


class JobManager:
    _jobs: dict[str, Job] = {}

    def create_job(
        self,
        resume_path: Path,
        jd_path: Path | None = None,
        jd_text: str | None = None,
    ) -> Job:
        job_id = str(uuid.uuid4())
        job = Job(job_id=job_id, resume_path=resume_path, jd_path=jd_path, jd_text=jd_text)
        self._jobs[job_id] = job
        logger.info("job_created", job_id=job_id)
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def delete_job(self, job_id: str) -> None:
        job = self._jobs.pop(job_id, None)
        if job:
            # Clean up files
            for p in [job.resume_path, job.jd_path]:
                if p and p.exists():
                    p.unlink(missing_ok=True)
            if job.result:
                for url_attr in ["docx_url", "pdf_url"]:
                    url = getattr(job.result, url_attr, None)
                    if url:
                        out_path = settings.output_dir / Path(url).name
                        out_path.unlink(missing_ok=True)
        logger.info("job_deleted", job_id=job_id)

    async def push_event(self, job: Job, event: str, data: dict) -> None:
        evt = JobEvent(event=event, data=data)
        job.status = JobStatus(event) if event in JobStatus._value2member_map_ else job.status
        await job.queue.put(evt)
        logger.debug("event_pushed", job_id=job.job_id, evt=event)

    async def push_complete(self, job: Job) -> None:
        """Signal end-of-stream."""
        await job.queue.put(None)

    async def stream_events(self, job: Job) -> AsyncIterator[str]:
        """Yields SSE-formatted strings for the FastAPI StreamingResponse.
        Sends a heartbeat comment every 15 seconds to keep the connection alive.
        """
        while True:
            try:
                evt = await asyncio.wait_for(job.queue.get(), timeout=15.0)
            except asyncio.TimeoutError:
                # Send SSE comment as keep-alive ping; client ignores comment lines
                yield ": heartbeat\n\n"
                continue
            if evt is None:
                yield "event: done\ndata: {}\n\n"
                break
            payload = json.dumps(evt.data)
            yield f"event: {evt.event}\ndata: {payload}\n\n"

    def cleanup_expired(self) -> None:
        expired = [jid for jid, job in self._jobs.items() if job.is_expired()]
        for jid in expired:
            self.delete_job(jid)
        if expired:
            logger.info("expired_jobs_cleaned", count=len(expired))


# Singleton
job_manager = JobManager()
