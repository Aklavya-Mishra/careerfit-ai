"""
Pipeline orchestrator: coordinates all stages of resume tailoring.
Called as a FastAPI background task.
"""
from __future__ import annotations

import structlog

from core.config import get_settings
from core.job_manager import Job, job_manager
from core.models import GapReport, JobResult, JobStatus, ParsedJD, ParsedResume
from generators.docx_generator import DocxGenerator
from generators.llm_rewriter import LLMRewriter
from generators.pdf_generator import PdfGenerator
from nlp.gap_analyzer import GapAnalyzer
from nlp.jd_extractor import JDExtractor
from parsers.docx_parser import DocxParser
from parsers.pdf_parser import PdfParser
from parsers.text_parser import TextParser

logger = structlog.get_logger(__name__)
settings = get_settings()


def _build_diff(original: ParsedResume, tailored: ParsedResume) -> list[dict]:
    diff = []
    orig_map = {s.name: s.raw_text for s in original.sections}
    for section in tailored.sections:
        orig_text = orig_map.get(section.name, "")
        new_text = section.rewritten_text or section.raw_text
        if orig_text.strip() != new_text.strip():
            diff.append({
                "section": section.name,
                "original": orig_text,
                "tailored": new_text,
            })
    return diff


async def run_pipeline(job: Job) -> None:
    log = logger.bind(job_id=job.job_id)
    try:
        # ------------------------------------------------------------------
        # Stage 1: Parse resume
        # ------------------------------------------------------------------
        await job_manager.push_event(job, "parsing_resume", {"progress": 10})
        log.info("parsing_resume")

        resume_suffix = job.resume_path.suffix.lower()
        if resume_suffix == ".docx":
            parsed_resume: ParsedResume = DocxParser().parse(job.resume_path)
        elif resume_suffix == ".pdf":
            parsed_resume = PdfParser().parse(job.resume_path)
        else:
            raise ValueError(f"Unsupported resume type: {resume_suffix}")

        log.info("resume_parsed", sections=len(parsed_resume.sections))

        # ------------------------------------------------------------------
        # Stage 2: Parse job description
        # ------------------------------------------------------------------
        await job_manager.push_event(job, "parsing_jd", {"progress": 20})
        log.info("parsing_jd")

        if job.jd_text:
            parsed_jd: ParsedJD = TextParser().parse(job.jd_text)
        elif job.jd_path:
            jd_suffix = job.jd_path.suffix.lower()
            if jd_suffix == ".docx":
                parsed_jd = TextParser().parse(DocxParser().extract_text(job.jd_path))
            else:
                parsed_jd = TextParser().parse(PdfParser().extract_text(job.jd_path))
        else:
            raise ValueError("No job description provided")

        log.info("jd_parsed", skills=len(parsed_jd.required_skills))

        # ------------------------------------------------------------------
        # Stage 3: Extract JD entities + semantic gap analysis
        # ------------------------------------------------------------------
        await job_manager.push_event(job, "analyzing_gaps", {"progress": 35})
        log.info("analyzing_gaps")

        extractor = JDExtractor()
        enriched_jd = extractor.enrich(parsed_jd)

        gap_analyzer = GapAnalyzer()
        gap_report: GapReport = gap_analyzer.analyze(parsed_resume, enriched_jd)

        log.info(
            "gap_analysis_complete",
            overall_score=gap_report.overall_score,
            weak_sections=gap_report.weak_sections,
        )

        # ------------------------------------------------------------------
        # Stage 4: LLM rewriting per section
        # ------------------------------------------------------------------
        rewriter = LLMRewriter()
        total_sections = len(parsed_resume.sections)
        progress_start = 40
        progress_per_section = 35 // max(total_sections, 1)

        tailored_resume = parsed_resume.model_copy(deep=True)

        for idx, section in enumerate(tailored_resume.sections):
            progress = progress_start + idx * progress_per_section
            await job_manager.push_event(
                job,
                "rewriting",
                {"progress": progress, "section": section.name, "step": f"{idx+1}/{total_sections}"},
            )
            log.info("rewriting_section", section=section.name)

            section_gap = next(
                (s for s in gap_report.section_scores if s.section_name == section.name),
                None,
            )

            rewritten = await rewriter.rewrite_section(
                section=section,
                gap_score=section_gap,
                jd=enriched_jd,
            )
            section.rewritten_text = rewritten

        # ------------------------------------------------------------------
        # Stage 5: Generate DOCX
        # ------------------------------------------------------------------
        await job_manager.push_event(job, "generating_docx", {"progress": 85})
        log.info("generating_docx")

        docx_gen = DocxGenerator()
        docx_path = docx_gen.generate(
            tailored_resume=tailored_resume,
            original_path=job.resume_path if job.resume_path.suffix.lower() == ".docx" else None,
            output_dir=settings.output_dir,
            job_id=job.job_id,
        )

        # ------------------------------------------------------------------
        # Stage 6: Generate PDF
        # ------------------------------------------------------------------
        await job_manager.push_event(job, "generating_pdf", {"progress": 93})
        log.info("generating_pdf")

        pdf_gen = PdfGenerator()
        pdf_path = pdf_gen.generate(
            tailored_resume=tailored_resume,
            output_dir=settings.output_dir,
            job_id=job.job_id,
        )

        # ------------------------------------------------------------------
        # Stage 7: Build diff + complete
        # ------------------------------------------------------------------
        diff = _build_diff(parsed_resume, tailored_resume)

        job.result = JobResult(
            job_id=job.job_id,
            status=JobStatus.COMPLETE,
            docx_url=f"/api/v1/jobs/{job.job_id}/download/docx",
            pdf_url=f"/api/v1/jobs/{job.job_id}/download/pdf",
            diff=diff,
            gap_report=gap_report,
        )
        job.status = JobStatus.COMPLETE

        await job_manager.push_event(
            job,
            "complete",
            {
                "progress": 100,
                "docx_url": job.result.docx_url,
                "pdf_url": job.result.pdf_url,
                "diff_count": len(diff),
                "overall_score": gap_report.overall_score,
            },
        )
        log.info("pipeline_complete", diff_sections=len(diff))

    except Exception as exc:
        log.exception("pipeline_failed", error=str(exc))
        job.status = JobStatus.FAILED
        job.result = JobResult(
            job_id=job.job_id,
            status=JobStatus.FAILED,
            error=str(exc),
        )
        await job_manager.push_event(job, "error", {"message": str(exc), "progress": 0})

    finally:
        await job_manager.push_complete(job)
