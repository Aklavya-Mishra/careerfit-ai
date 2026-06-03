"""
Embedder: wraps sentence-transformers for semantic similarity scoring.
Singleton pattern to avoid reloading the model on every request.
"""
from __future__ import annotations

import numpy as np
import structlog
from sentence_transformers import SentenceTransformer

from core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

_model_instance: SentenceTransformer | None = None


def get_embedder() -> SentenceTransformer:
    global _model_instance
    if _model_instance is None:
        logger.info("loading_embedding_model", model=settings.embedding_model)
        _model_instance = SentenceTransformer(
            settings.embedding_model,
            device=settings.embedding_device,
        )
        logger.info("embedding_model_loaded")
    return _model_instance


def embed(texts: list[str]) -> np.ndarray:
    model = get_embedder()
    return model.encode(texts, convert_to_numpy=True, show_progress_bar=False)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a_norm = a / (np.linalg.norm(a) + 1e-10)
    b_norm = b / (np.linalg.norm(b) + 1e-10)
    return float(np.dot(a_norm, b_norm))


def batch_cosine_similarity(queries: np.ndarray, keys: np.ndarray) -> np.ndarray:
    """Returns shape (len(queries), len(keys)) similarity matrix."""
    q_norm = queries / (np.linalg.norm(queries, axis=1, keepdims=True) + 1e-10)
    k_norm = keys / (np.linalg.norm(keys, axis=1, keepdims=True) + 1e-10)
    return q_norm @ k_norm.T
