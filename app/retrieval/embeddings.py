"""
DriftGuard Embeddings
Sentence-transformers wrapper for generating embeddings.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)

_model_instance = None


def get_embedding_model(model_name: str = None):
    """
    Load and cache the sentence-transformers embedding model.
    Uses a global singleton to avoid reloading.
    """
    global _model_instance
    if _model_instance is not None:
        return _model_instance

    from app import config
    model_name = model_name or config.EMBEDDING_MODEL

    logger.info(f"Loading embedding model: {model_name}")
    from sentence_transformers import SentenceTransformer
    _model_instance = SentenceTransformer(model_name)
    logger.info(f"Embedding model loaded: {model_name}")
    return _model_instance


def embed_texts(texts: List[str], model_name: str = None,
                batch_size: int = 64, show_progress: bool = False) -> List[List[float]]:
    """
    Generate embeddings for a list of text strings.

    Args:
        texts: List of text strings to embed
        model_name: Override embedding model name
        batch_size: Batch size for encoding
        show_progress: Whether to show progress bar

    Returns:
        List of embedding vectors (as lists of floats)
    """
    if not texts:
        return []

    model = get_embedding_model(model_name)
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        normalize_embeddings=True,
    )
    return embeddings.tolist()


def embed_single(text: str, model_name: str = None) -> List[float]:
    """Embed a single text string."""
    result = embed_texts([text], model_name=model_name)
    return result[0] if result else []
