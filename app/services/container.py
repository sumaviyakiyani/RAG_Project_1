"""Builds and wires all services (simple dependency injection)."""
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from app.config import Settings
from app.errors import RateLimitError
from app.retrieval import Retriever
from app.services.embeddings import build_embedder
from app.services.ingestion_service import IngestionService
from app.services.llm import LLMClient
from app.services.rag_service import RagService
from app.services.vector_store import VectorStore


class RateLimiter:
    """Allow at most N requests per minute per client (in memory)."""

    def __init__(self, per_minute: int):
        self.per_minute, self.hits = per_minute, defaultdict(deque)

    def check(self, key: str) -> None:
        now, q = time.monotonic(), self.hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= self.per_minute:
            raise RateLimitError("Too many requests. Please wait a minute.")
        q.append(now)


@dataclass
class Services:
    settings: Settings
    store: VectorStore
    ingestion: IngestionService
    rag: RagService
    limiter: RateLimiter


def build_services(settings: Settings, llm=None) -> Services:
    embedder = build_embedder(settings)
    store = VectorStore(settings.chroma_dir)
    retriever = Retriever(embedder, store, settings)
    return Services(settings, store, IngestionService(embedder, store, settings),
                    RagService(retriever, llm or LLMClient(settings), settings),
                    RateLimiter(settings.rate_limit_per_min))
