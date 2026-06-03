"""
Gap analyzer: scores each resume section against the JD using embeddings,
identifies missing skills and weak sections.
"""
from __future__ import annotations

import structlog

from core.config import get_settings
from core.models import GapReport, ParsedJD, ParsedResume, SectionGapScore
from nlp.embedder import batch_cosine_similarity, cosine_similarity, embed

logger = structlog.get_logger(__name__)
settings = get_settings()


class GapAnalyzer:
    def analyze(self, resume: ParsedResume, jd: ParsedJD) -> GapReport:
        logger.info("gap_analysis_start")

        # Embed JD full text for overall comparison
        jd_embedding = embed([jd.full_text])[0]

        # Per-section scoring
        section_scores: list[SectionGapScore] = []

        for section in resume.sections:
            if not section.raw_text.strip():
                continue

            section_embedding = embed([section.raw_text])[0]
            score = cosine_similarity(section_embedding, jd_embedding)

            # Find which required skills are missing from this section
            missing_skills = self._find_missing_skills(
                section_text=section.raw_text,
                required_skills=jd.required_skills,
            )

            suggestions = self._generate_suggestions(
                section_name=section.name,
                score=score,
                missing_skills=missing_skills,
                jd=jd,
            )

            section_scores.append(SectionGapScore(
                section_name=section.name,
                score=round(score, 3),
                missing_skills=missing_skills[:5],
                suggestions=suggestions,
            ))

        overall_score = (
            sum(s.score for s in section_scores) / len(section_scores)
            if section_scores else 0.0
        )

        # Identify all missing skills across the resume
        all_resume_text = resume.full_text.lower()
        all_missing = [
            skill for skill in jd.required_skills
            if skill.lower() not in all_resume_text
        ]

        strong = [s.section_name for s in section_scores if s.score >= settings.strong_section_threshold]
        weak = [s.section_name for s in section_scores if s.score < settings.weak_section_threshold]

        report = GapReport(
            overall_score=round(overall_score, 3),
            section_scores=section_scores,
            missing_skills=all_missing[:15],
            strong_sections=strong,
            weak_sections=weak,
        )

        logger.info(
            "gap_analysis_done",
            overall=overall_score,
            weak=weak,
            missing_count=len(all_missing),
        )
        return report

    def _find_missing_skills(self, section_text: str, required_skills: list[str]) -> list[str]:
        text_lower = section_text.lower()
        return [skill for skill in required_skills if skill.lower() not in text_lower]

    def _generate_suggestions(
        self,
        section_name: str,
        score: float,
        missing_skills: list[str],
        jd: ParsedJD,
    ) -> list[str]:
        suggestions: list[str] = []

        if score < settings.weak_section_threshold:
            suggestions.append(f"This section has low alignment ({score:.0%}). Consider restructuring to highlight JD-relevant accomplishments.")

        if missing_skills:
            skills_str = ", ".join(missing_skills[:3])
            suggestions.append(f"Incorporate these required skills if applicable: {skills_str}")

        if section_name == "experience" and score < 0.65:
            suggestions.append("Quantify achievements with metrics (%, $, throughput, scale) that match JD expectations.")

        if section_name == "skills" and missing_skills:
            suggestions.append("Add a dedicated subsection for the missing technical skills you do possess.")

        return suggestions
