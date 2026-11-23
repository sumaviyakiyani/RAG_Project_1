"""Embedding models: turn text into vectors (lists of numbers)."""
import hashlib
import math
from typing import Protocol

from app.config import Settings
from app.text_utils import content_words


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    """Real semantic embeddings, run locally and free. Model downloads on first use."""

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # imported lazily (slow)
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return vectors.tolist()


class HashingEmbedder:
    """Tiny word-overlap embedder. NOT semantic. Used only so tests run offline and fast."""

    def __init__(self, dim: int = 1024):
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            vec = [0.0] * self.dim
            for word in content_words(text):
                h = int(hashlib.md5(word.encode()).hexdigest(), 16)
                vec[h % self.dim] += 1.0 if (h >> 20) & 1 else -1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vec = [v / norm for v in vec]
            if not any(vec):
                vec[0] = 1e-6
            out.append(vec)
        return out


def build_embedder(settings: Settings) -> Embedder:
    if settings.embedding_backend == "hash":
        return HashingEmbedder()
    return SentenceTransformerEmbedder(settings.embedding_model)
