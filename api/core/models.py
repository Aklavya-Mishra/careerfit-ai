"""
Core Pydantic data models for careerfit-ai.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class JobStatus(str, Enum):
    QUEUED = "queued"
    PARSING_RESUME = "parsing_resume"
    PARSING_JD = "parsing_jd"
    ANALYZING_GAPS = "analyzing_gaps"
    REWRITING = "rewriting"
    GENERATING_DOCX = "generating_docx"
    GENERATING_PDF = "generating_pdf"
    COMPLETE = "complete"
    FAILED = "failed"


class DocumentType(str, Enum):
    DOCX = "docx"
    PDF = "pdf"
    TEXT = "text"


# ---------------------------------------------------------------------------
# Document models
# ---------------------------------------------------------------------------

class ResumeSection(BaseModel):
    name: str
    raw_text: str
    rewritten_text: str | None = None
    alignment_score: float | None = None


class StyleMetadata(BaseModel):
    """Captured style info from the original resume."""
    fonts: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    has_columns: bool = False
    has_tables: bool = False
    margins: dict[str, float] = Field(default_factory=dict)
    page_size: str = "A4"
    extra: dict[str, Any] = Field(default_factory=dict)


class ParsedResume(BaseModel):
    source_type: DocumentType
    full_text: str
    sections: list[ResumeSection]
    style_metadata: StyleMetadata
    contact_info: dict[str, str] = Field(default_factory=dict)
    raw_paragraphs: list[str] = Field(default_factory=list)


class ParsedJD(BaseModel):
    full_text: str
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    job_title: str = ""
    company: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Gap analysis
# ---------------------------------------------------------------------------

class SectionGapScore(BaseModel):
    section_name: str
    score: float
    missing_skills: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class GapReport(BaseModel):
    overall_score: float
    section_scores: list[SectionGapScore]
    missing_skills: list[str] = Field(default_factory=list)
    strong_sections: list[str] = Field(default_factory=list)
    weak_sections: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Job / API models
# ---------------------------------------------------------------------------

class TailorRequest(BaseModel):
    jd_text: str | None = None


class JobEvent(BaseModel):
    event: str
    data: dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class JobResult(BaseModel):
    job_id: str
    status: JobStatus
    docx_url: str | None = None
    pdf_url: str | None = None
    diff: list[dict[str, str]] = Field(default_factory=list)
    gap_report: GapReport | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    model_available: bool
    version: str = "1.0.0"
