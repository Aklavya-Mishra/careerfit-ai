"""
LLM rewriter: uses Ollama to rewrite resume sections guided by gap analysis.
"""
from __future__ import annotations

import asyncio
import json
import re

import httpx
import structlog

from core.config import get_settings
from core.models import ParsedJD, ResumeSection, SectionGapScore

logger = structlog.get_logger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """You are an expert resume writer enhancing resume content to better match a job description.

Your job is to enhance existing resume bullet points by naturally weaving in JD keywords — NOT to replace or skip any original content.

Rules you MUST follow:
1. Keep EVERY original bullet point — do not remove, skip, merge, or drastically shorten any
2. Enhance each bullet by naturally adding 1–2 relevant JD keywords or technologies where contextually appropriate
3. For JD requirements not yet mentioned, create a brief plausible addition grounded in the candidate's existing work context
4. Never invent metrics, change company names, job titles, dates, or locations
5. Output the SAME NUMBER of lines as the input — one bullet per line, no extra lines added
6. Keep structural lines (company, title, date, location) EXACTLY as they appear — do not modify them
7. Return ONLY the enhanced section text, nothing else — no preamble, no explanation
8. Do NOT use any markdown formatting — no **, ##, *, [], or similar. Plain text only.
9. Do NOT include any notes, disclaimers, or meta-commentary about your changes.
10. For experience/work history, write natural action statements that show how the JD technology was used in the work.
11. Do not dump JD technologies into the skills section unless they are truthful and supported by the resume context."""


def _clean_markdown(text: str) -> str:
    """Strip markdown artifacts that LLMs sometimes inject into plain-text output."""
    text = re.sub(r'\*{1,3}([^*\n]*)\*{1,3}', r'\1', text)   # **bold** / *italic*
    text = re.sub(r'_{1,2}([^_\n]+)_{1,2}', r'\1', text)       # __underline__
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)  # ## headings
    text = re.sub(r'^\s*[\*\-]\s+', '', text, flags=re.MULTILINE)  # * / - bullets
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)       # [text](url)
    # Remove LLM meta-commentary lines
    text = re.sub(r'^(?:\*{0,2})?Note[:\s*].*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    lines = []
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned and not re.fullmatch(r'[\u2022\-\*\s]+', cleaned):
            lines.append(cleaned)
    return "\n".join(lines).strip()


def _build_user_prompt(
    section: ResumeSection,
    gap_score: SectionGapScore | None,
    jd: ParsedJD,
) -> str:
    parts = [
        f"## Section to enhance: {section.name.upper()}",
        "",
        "### Original section content (keep ALL lines, only enhance bullet points):",
        section.raw_text,
        "",
        "### JD keywords and skills to naturally weave in:",
        f"Title: {jd.job_title or 'Not specified'}",
        f"Required skills: {', '.join(jd.required_skills[:12]) if jd.required_skills else 'Not specified'}",
        f"Important keywords: {', '.join(jd.keywords[:10]) if jd.keywords else 'Not specified'}",
    ]

    if gap_score and gap_score.missing_skills:
        parts.append(f"Missing skills to incorporate contextually: {', '.join(gap_score.missing_skills[:5])}")

    if section.name in {"experience", "work experience", "work history"}:
        parts += [
            "",
            "For work history, avoid keyword lists. Show the JD stack inside natural work statements, only where the candidate's role makes it plausible.",
        ]
    elif section.name == "skills":
        parts += [
            "",
            "For skills, keep the list concise. Do not add a large pile of JD keywords that are not supported elsewhere in the resume.",
        ]

    parts += [
        "",
        "### Output the enhanced section (same structure, same number of lines):",
    ]

    return "\n".join(parts)


class LLMRewriter:
    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=httpx.Timeout(settings.ollama_timeout),
        )

    async def rewrite_section(
        self,
        section: ResumeSection,
        gap_score: SectionGapScore | None,
        jd: ParsedJD,
    ) -> str:
        """Rewrite a single resume section, with retry on failure."""
        # Skip sections that already score high and have no missing skills
        if (
            gap_score
            and gap_score.score >= settings.strong_section_threshold
            and not gap_score.missing_skills
        ):
            logger.info("section_skipped_high_score", section=section.name, score=gap_score.score)
            return section.raw_text

        for attempt in range(settings.max_rewrite_retries + 1):
            try:
                result = await self._call_ollama(
                    system=SYSTEM_PROMPT,
                    user=_build_user_prompt(section, gap_score, jd),
                )
                result = _clean_markdown(result)
                if self._is_valid(result, section.raw_text):
                    return result
                logger.warning("rewrite_validation_failed", section=section.name, attempt=attempt)
            except Exception as e:
                logger.warning("rewrite_attempt_failed", section=section.name, attempt=attempt, error=str(e))
                if attempt == settings.max_rewrite_retries:
                    logger.error("rewrite_all_attempts_failed_using_original", section=section.name)
                    return section.raw_text
                await asyncio.sleep(1)

        return section.raw_text

    async def _call_ollama(self, system: str, user: str) -> str:
        payload = {
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "num_predict": 1024,
            },
        }

        response = await self.client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

        return data["message"]["content"]

    def _is_valid(self, text: str, original: str) -> bool:
        if not text or len(text.strip()) < 20:
            return False
        # Reject if output is way too long compared to original
        if len(text) > len(original) * 3 + 500:
            return False
        # Reject if it looks like it includes the prompt
        if "Section to enhance:" in text or "Gap analysis:" in text:
            return False
        return True

    async def aclose(self):
        await self.client.aclose()
