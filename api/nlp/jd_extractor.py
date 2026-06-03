"""
JD extractor: enriches a ParsedJD with additional entity extraction
using regex patterns and keyword matching.
"""
from __future__ import annotations

import re

import structlog

from core.models import ParsedJD

logger = structlog.get_logger(__name__)

_YEARS_PATTERN = re.compile(r"(\d+)\+?\s*years?\s+(?:of\s+)?experience", re.I)
_DEGREE_PATTERN = re.compile(
    r"\b(?:bachelor(?:'s)?|master(?:'s)?|phd|b\.?s\.?|m\.?s\.?|b\.?e\.?|m\.?tech|doctorate|degree)\b",
    re.I,
)


class JDExtractor:
    def enrich(self, jd: ParsedJD) -> ParsedJD:
        text = jd.full_text

        # Extract years of experience expectations
        years_matches = _YEARS_PATTERN.findall(text)
        years_required = max((int(y) for y in years_matches), default=0)

        # Extract degree requirements
        degree_required = bool(_DEGREE_PATTERN.search(text))

        # Augment keywords with any missed patterns
        extra_keywords = self._extract_tech_terms(text)
        combined_keywords = list(dict.fromkeys(jd.keywords + extra_keywords))[:40]

        # Augment skills: pull from responsibilities too
        resp_skills = self._extract_skills_from_responsibilities(jd.responsibilities)
        combined_skills = list(dict.fromkeys(jd.required_skills + resp_skills))[:25]

        enriched = jd.model_copy(update={
            "keywords": combined_keywords,
            "required_skills": combined_skills,
            "extra": {
                "years_required": years_required,
                "degree_required": degree_required,
            },
        })

        logger.info(
            "jd_enriched",
            skills=len(combined_skills),
            keywords=len(combined_keywords),
            years_required=years_required,
        )
        return enriched

    def _extract_tech_terms(self, text: str) -> list[str]:
        """Extract capitalized tech acronyms and version-specific terms."""
        terms: set[str] = set()

        # Acronyms: 2-6 capital letters
        for m in re.finditer(r"\b[A-Z]{2,6}\b", text):
            term = m.group()
            if term not in {"THE", "AND", "FOR", "WITH", "YOU", "OUR", "WHO", "WILL", "MUST", "CAN"}:
                terms.add(term)

        # Version-tagged terms: Python 3, Java 17, etc.
        for m in re.finditer(r"\b([A-Za-z]+)\s+(\d+(?:\.\d+)?)\b", text):
            terms.add(f"{m.group(1)} {m.group(2)}")

        return list(terms)[:15]

    def _extract_skills_from_responsibilities(self, responsibilities: list[str]) -> list[str]:
        from parsers.text_parser import _SKILL_KEYWORDS
        skills: set[str] = set()
        combined = " ".join(responsibilities).lower()
        for skill in _SKILL_KEYWORDS:
            if skill in combined:
                skills.add(skill)
        return list(skills)
