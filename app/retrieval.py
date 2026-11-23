"""Retrieval: embed the question, search the vector DB, choose context."""
from app.config import Settings
from app.models import RetrievedChunk


class Retriever:
    def __init__(self, embedder, store, settings: Settings):
        self.embedder, self.store, self.s = embedder, store, settings

    def retrieve(self, question: str, top_k: int | None = None) -> list[RetrievedChunk]:
        """Top-k chunks, best first, each with its REAL cosine similarity."""
        vector = self.embedder.embed([question])[0]
        return self.store.query(vector, top_k or self.s.top_k)

    def select_context(self, retrieved: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """Keep chunks above the score threshold, within the context size budget."""
        selected, used = [], 0
        for chunk in retrieved:  # already sorted best-first
            if chunk.score < self.s.min_score:
                break
            if selected and used + len(chunk.text) > self.s.max_context_chars:
                break
            selected.append(chunk)
            used += len(chunk.text)
        return selected
