"""
Plain text parser: used for JD text input and text-based document fallback.
Extracts structured fields from free-form job description text.
"""
from __future__ import annotations

import re

import structlog

from core.models import ParsedJD

logger = structlog.get_logger(__name__)

_SKILL_KEYWORDS = [
    "python", "java", "javascript", "typescript", "go", "rust", "c++", "c#",
    "react", "vue", "angular", "node", "fastapi", "django", "flask", "spring",
    "kubernetes", "docker", "terraform", "aws", "gcp", "azure", "git",
    "postgresql", "mysql", "mongodb", "redis", "kafka", "rabbitmq",
    "machine learning", "deep learning", "nlp", "llm", "pytorch", "tensorflow",
    "spark", "hadoop", "airflow", "dbt", "sql", "rest", "graphql", "grpc",
    "ci/cd", "devops", "agile", "scrum", "microservices", "api",
    "linux", "bash", "shell", "ansible", "jenkins", "github actions",
]

_TITLE_PATTERNS = [
    r"(?:position|role|job title|title)\s*[:\-]\s*(.+)",
    r"(?:we are (?:looking|hiring|seeking) (?:for )?a[n]? )(.+?)(?:\.|,|to)",
]


def _extract_job_title(text: str) -> str:
    for pattern in _TITLE_PATTERNS:
        m = re.search(pattern, text, re.I)
        if m:
            return m.group(1).strip()[:80]
    # Fallback: first meaningful line
    for line in text.splitlines():
        line = line.strip()
        if 5 < len(line) < 80 and not line.startswith("•"):
            return line
    return ""


def _extract_skills_from_text(text: str) -> list[str]:
    text_lower = text.lower()
    found = []
    for skill in _SKILL_KEYWORDS:
        if skill in text_lower:
            found.append(skill)
    return found


def _extract_responsibilities(text: str) -> list[str]:
    responsibilities = []
    lines = text.splitlines()
    in_resp_section = False

    for line in lines:
        line = line.strip()
        lower = line.lower()

        if any(kw in lower for kw in ["responsibilit", "you will", "what you'll do", "duties", "role involves"]):
            in_resp_section = True
            continue

        if in_resp_section:
            if any(kw in lower for kw in ["requirement", "qualif", "what you bring", "skills needed", "you have"]):
                in_resp_section = False
                continue
            if line and (line.startswith("•") or line.startswith("-") or line.startswith("*") or
                         (len(line) > 20 and line[0].isupper())):
                clean = line.lstrip("•-* ").strip()
                if clean:
                    responsibilities.append(clean)

    return responsibilities[:15]


def _extract_required_skills(text: str) -> list[str]:
    skills = []
    lines = text.splitlines()
    in_section = False

    for line in lines:
        line = line.strip()
        lower = line.lower()

        if any(kw in lower for kw in ["required", "requirement", "qualif", "must have", "you have", "what you bring"]):
            in_section = True
            continue

        if in_section:
            if any(kw in lower for kw in ["preferred", "nice to have", "bonus", "responsibilit", "about us"]):
                in_section = False
                continue
            if line and (line.startswith("•") or line.startswith("-") or line.startswith("*")):
                clean = line.lstrip("•-* ").strip()
                if clean:
                    skills.append(clean)

    # Also grab inline skill matches
    inline = _extract_skills_from_text(text)
    all_skills = list(dict.fromkeys(skills + inline))
    return all_skills[:20]


def _extract_keywords(text: str) -> list[str]:
    """Extract important multi-word phrases and tech terms."""
    text_lower = text.lower()
    keywords: set[str] = set()

    # Tech stack patterns
    tech_patterns = [
        r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b",  # CamelCase multi-word
        r"\b(?:RESTful?|GraphQL|gRPC|OAuth|JWT|RBAC|SAML|OIDC)\b",
        r"\b(?:CI/CD|DevOps|MLOps|DataOps|GitOps)\b",
    ]
    for pat in tech_patterns:
        for m in re.finditer(pat, text):
            term = m.group().strip()
            if 3 < len(term) < 40:
                keywords.add(term)

    keywords.update(_extract_skills_from_text(text))
    return list(keywords)[:30]


class TextParser:
    def parse(self, text: str) -> ParsedJD:
        logger.info("text_parse_start", chars=len(text))

        job_title = _extract_job_title(text)
        required_skills = _extract_required_skills(text)
        responsibilities = _extract_responsibilities(text)
        keywords = _extract_keywords(text)

        # Preferred skills: lines with "preferred" / "nice to have"
        preferred: list[str] = []
        lines = text.splitlines()
        in_preferred = False
        for line in lines:
            lower = line.strip().lower()
            if "preferred" in lower or "nice to have" in lower or "bonus" in lower:
                in_preferred = True
                continue
            if in_preferred:
                if any(kw in lower for kw in ["required", "responsibilit", "about"]):
                    in_preferred = False
                    continue
                clean = line.strip().lstrip("•-* ").strip()
                if clean and len(clean) > 5:
                    preferred.append(clean)

        jd = ParsedJD(
            full_text=text,
            required_skills=required_skills,
            preferred_skills=preferred[:10],
            responsibilities=responsibilities,
            keywords=keywords,
            job_title=job_title,
        )
        logger.info("text_parse_complete", title=job_title, skills=len(required_skills))
        return jd
