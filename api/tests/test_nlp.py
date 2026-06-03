"""
Unit tests for NLP components: embedder (math), gap_analyzer, jd_extractor.
Embedder network tests are mocked — model is downloaded in Docker at build time.
"""
import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from core.models import (
    DocumentType,
    GapReport,
    ParsedJD,
    ParsedResume,
    ResumeSection,
    StyleMetadata,
)
from nlp.embedder import batch_cosine_similarity, cosine_similarity
from nlp.gap_analyzer import GapAnalyzer
from nlp.jd_extractor import JDExtractor
from tests.conftest import SAMPLE_JD_TEXT, SAMPLE_RESUME_TEXT


# ---------------------------------------------------------------------------
# Embedder — math only (no model download)
# ---------------------------------------------------------------------------

class TestEmbedderMath:
    """Test the pure math functions without requiring the model."""

    def test_cosine_similarity_identical_vectors(self):
        vec = np.array([1.0, 2.0, 3.0])
        score = cosine_similarity(vec, vec)
        assert abs(score - 1.0) < 1e-5

    def test_cosine_similarity_orthogonal(self):
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([0.0, 1.0, 0.0])
        score = cosine_similarity(a, b)
        assert abs(score) < 1e-5

    def test_cosine_similarity_opposite(self):
        a = np.array([1.0, 0.0])
        b = np.array([-1.0, 0.0])
        score = cosine_similarity(a, b)
        assert abs(score - (-1.0)) < 1e-5

    def test_cosine_similarity_range(self):
        a = np.random.rand(384)
        b = np.random.rand(384)
        score = cosine_similarity(a, b)
        assert -1.0 <= score <= 1.0

    def test_batch_cosine_similarity_shape(self):
        queries = np.random.rand(2, 384)
        keys = np.random.rand(3, 384)
        matrix = batch_cosine_similarity(queries, keys)
        assert matrix.shape == (2, 3)

    def test_batch_cosine_similarity_diagonal_near_1(self):
        """Same vectors should produce near-1 similarity."""
        vecs = np.random.rand(3, 384)
        matrix = batch_cosine_similarity(vecs, vecs)
        for i in range(3):
            assert abs(matrix[i, i] - 1.0) < 1e-5

    def test_cosine_handles_zero_vector(self):
        """Zero vector shouldn't crash (epsilon prevents div-by-zero)."""
        a = np.zeros(384)
        b = np.ones(384)
        score = cosine_similarity(a, b)
        assert not np.isnan(score)


class TestEmbedderWithMock:
    """Test embed() function with mocked model."""

    def test_embed_returns_ndarray(self):
        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.rand(1, 384).astype("float32")
        with patch("nlp.embedder.get_embedder", return_value=mock_model):
            from nlp.embedder import embed
            vecs = embed(["hello world"])
            assert isinstance(vecs, np.ndarray)
            assert vecs.shape == (1, 384)

    def test_embed_multiple_texts(self):
        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.rand(3, 384).astype("float32")
        with patch("nlp.embedder.get_embedder", return_value=mock_model):
            from nlp.embedder import embed
            vecs = embed(["a", "b", "c"])
            assert vecs.shape[0] == 3


# ---------------------------------------------------------------------------
# JDExtractor
# ---------------------------------------------------------------------------

class TestJDExtractor:
    def _make_jd(self):
        from parsers.text_parser import TextParser
        return TextParser().parse(SAMPLE_JD_TEXT)

    def test_enrich_returns_parsed_jd(self):
        jd = self._make_jd()
        enriched = JDExtractor().enrich(jd)
        assert isinstance(enriched, ParsedJD)

    def test_enrich_expands_keywords(self):
        jd = self._make_jd()
        enriched = JDExtractor().enrich(jd)
        assert len(enriched.keywords) >= len(jd.keywords)

    def test_enrich_expands_skills(self):
        jd = self._make_jd()
        enriched = JDExtractor().enrich(jd)
        assert len(enriched.required_skills) >= len(jd.required_skills)

    def test_enrich_extracts_years(self):
        jd = self._make_jd()
        enriched = JDExtractor().enrich(jd)
        assert enriched.extra.get("years_required", 0) == 5

    def test_enrich_detects_degree(self):
        jd_with_degree = ParsedJD(
            full_text="Bachelor's degree in Computer Science required. 3+ years Python.",
            required_skills=["Python"],
        )
        enriched = JDExtractor().enrich(jd_with_degree)
        assert enriched.extra.get("degree_required") is True

    def test_enrich_no_degree_mentioned(self):
        jd_no_degree = ParsedJD(
            full_text="3+ years Python. Strong Kubernetes skills needed.",
            required_skills=["Python"],
        )
        enriched = JDExtractor().enrich(jd_no_degree)
        assert enriched.extra.get("degree_required") is False

    def test_enrich_years_pattern(self):
        jd = ParsedJD(full_text="You need 8+ years of experience in AI systems.")
        enriched = JDExtractor().enrich(jd)
        assert enriched.extra.get("years_required") == 8


# ---------------------------------------------------------------------------
# GapAnalyzer — mocked embedder
# ---------------------------------------------------------------------------

def _make_resume(sections_data: dict) -> ParsedResume:
    sections = [
        ResumeSection(name=name, raw_text=text)
        for name, text in sections_data.items()
    ]
    full_text = "\n".join(sections_data.values())
    return ParsedResume(
        source_type=DocumentType.DOCX,
        full_text=full_text,
        sections=sections,
        style_metadata=StyleMetadata(),
    )


def _make_jd(text: str = SAMPLE_JD_TEXT) -> ParsedJD:
    from parsers.text_parser import TextParser
    jd = TextParser().parse(text)
    return JDExtractor().enrich(jd)


def _mock_embed_fn(vecs_map: dict):
    """Returns a mock embed that returns preset vectors by text."""
    import numpy as np
    call_count = [0]
    def mock_embed(texts):
        result = []
        for t in texts:
            call_count[0] += 1
            if t in vecs_map:
                result.append(vecs_map[t])
            else:
                np.random.seed(hash(t) % (2**31))
                result.append(np.random.rand(384).astype("float32"))
        return np.array(result)
    return mock_embed


class TestGapAnalyzer:
    def test_analyze_returns_gap_report(self):
        resume = _make_resume({"skills": "Python, Docker, Kubernetes"})
        jd = _make_jd()
        with patch("nlp.gap_analyzer.embed") as mock_embed:
            mock_embed.return_value = np.random.rand(1, 384).astype("float32")
            report = GapAnalyzer().analyze(resume, jd)
        assert isinstance(report, GapReport)

    def test_overall_score_in_range(self):
        resume = _make_resume({"skills": "Python, Docker, Kubernetes, FastAPI, GCP"})
        jd = _make_jd()
        with patch("nlp.gap_analyzer.embed") as mock_embed:
            mock_embed.return_value = np.random.rand(1, 384).astype("float32")
            report = GapAnalyzer().analyze(resume, jd)
        assert 0.0 <= report.overall_score <= 1.0

    def test_section_scores_populated(self):
        resume = _make_resume({
            "summary": "Senior AI engineer",
            "experience": "Built AI pipelines",
            "skills": "Python, Kubernetes",
        })
        jd = _make_jd()
        with patch("nlp.gap_analyzer.embed") as mock_embed:
            mock_embed.return_value = np.random.rand(1, 384).astype("float32")
            report = GapAnalyzer().analyze(resume, jd)
        assert len(report.section_scores) == 3

    def test_relevant_resume_scores_higher(self):
        """Relevant resume should score higher than irrelevant — uses real cosine math."""
        # Give relevant resume a vector similar to JD, irrelevant a different one
        jd_vec = np.array([1.0, 0.0, 0.0] + [0.0] * 381, dtype="float32")
        rel_vec = np.array([0.95, 0.1, 0.0] + [0.0] * 381, dtype="float32")
        irrel_vec = np.array([0.0, 0.0, 1.0] + [0.0] * 381, dtype="float32")

        relevant_resume = _make_resume({"experience": "AI/ML engineer Python LLM"})
        irrelevant_resume = _make_resume({"experience": "Chef cooking restaurant"})
        jd = _make_jd()

        def mock_embed_relevant(texts):
            if texts[0] == jd.full_text:
                return jd_vec.reshape(1, -1)
            return rel_vec.reshape(1, -1)

        def mock_embed_irrelevant(texts):
            if texts[0] == jd.full_text:
                return jd_vec.reshape(1, -1)
            return irrel_vec.reshape(1, -1)

        with patch("nlp.gap_analyzer.embed", side_effect=mock_embed_relevant):
            rel_report = GapAnalyzer().analyze(relevant_resume, jd)

        with patch("nlp.gap_analyzer.embed", side_effect=mock_embed_irrelevant):
            irrel_report = GapAnalyzer().analyze(irrelevant_resume, jd)

        assert rel_report.overall_score > irrel_report.overall_score

    def test_missing_skills_identified(self):
        resume = _make_resume({"skills": "Python, Docker, Git"})
        jd = ParsedJD(
            full_text="Need Python, Kubernetes, Pinecone",
            required_skills=["Kubernetes", "Pinecone", "Python"],
        )
        with patch("nlp.gap_analyzer.embed") as mock_embed:
            mock_embed.return_value = np.random.rand(1, 384).astype("float32")
            report = GapAnalyzer().analyze(resume, jd)
        missing_lower = [s.lower() for s in report.missing_skills]
        assert "kubernetes" in missing_lower or "pinecone" in missing_lower

    def test_empty_sections_skipped(self):
        resume = _make_resume({"summary": "Senior engineer", "empty": ""})
        jd = _make_jd()
        with patch("nlp.gap_analyzer.embed") as mock_embed:
            mock_embed.return_value = np.random.rand(1, 384).astype("float32")
            report = GapAnalyzer().analyze(resume, jd)
        scored_names = [s.section_name for s in report.section_scores]
        assert "empty" not in scored_names



