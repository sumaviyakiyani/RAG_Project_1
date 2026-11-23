"""ChromaDB wrapper. All chunk text, vectors and metadata live here (single source of truth)."""
from datetime import datetime, timezone

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.errors import DocumentDeletionError
from app.models import Chunk, RetrievedChunk


class VectorStore:
    def __init__(self, path: str, collection: str = "chunks"):
        self._client = chromadb.PersistentClient(
            path=path, settings=ChromaSettings(anonymized_telemetry=False))
        # cosine space: distance = 1 - cosine similarity
        self.col = self._client.get_or_create_collection(collection, metadata={"hnsw:space": "cosine"})

    def close(self) -> None:
        self._client.close()

    def add_chunks(self, chunks: list[Chunk], embeddings: list[list[float]], file_hash: str) -> None:
        uploaded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for i in range(0, len(chunks), 500):
            batch = chunks[i:i + 500]
            self.col.add(
                ids=[c.chunk_id for c in batch],
                documents=[c.text for c in batch],
                embeddings=embeddings[i:i + 500],
                metadatas=[{
                    "doc_id": c.doc_id, "filename": c.filename, "file_hash": file_hash,
                    "page": c.page, "location": c.location, "position": c.position,
                    "char_count": len(c.text), "uploaded_at": uploaded_at,
                } for c in batch],
            )

    def query(self, embedding: list[float], k: int) -> list[RetrievedChunk]:
        total = self.col.count()
        if total == 0:
            return []
        res = self.col.query(query_embeddings=[embedding], n_results=min(k, total),
                             include=["documents", "metadatas", "distances"])
        out = []
        for cid, text, meta, dist in zip(res["ids"][0], res["documents"][0],
                                         res["metadatas"][0], res["distances"][0]):
            out.append(RetrievedChunk(cid, meta["doc_id"], meta["filename"], meta["page"],
                                      meta["location"], meta["position"], text,
                                      round(1.0 - float(dist), 4)))
        return out

    def find_by_hash(self, file_hash: str) -> bool:
        return bool(self.col.get(where={"file_hash": file_hash}, limit=1, include=[])["ids"])

    def list_documents(self) -> list[dict]:
        metas = self.col.get(include=["metadatas"])["metadatas"] or []
        docs: dict[str, dict] = {}
        for m in metas:
            d = docs.setdefault(m["doc_id"], {
                "doc_id": m["doc_id"], "filename": m["filename"], "file_hash": m["file_hash"],
                "uploaded_at": m["uploaded_at"], "chunk_count": 0, "pages": set()})
            d["chunk_count"] += 1
            d["pages"].add(m["page"])
        result = []
        for d in docs.values():
            d["page_count"] = len(d.pop("pages"))
            result.append(d)
        return sorted(result, key=lambda d: d["uploaded_at"])

    def delete_document(self, doc_id: str) -> int:
        """Remove every chunk (vector + text + metadata) of a document. Returns chunks removed."""
        ids = self.col.get(where={"doc_id": doc_id}, include=[])["ids"]
        if ids:
            self.col.delete(ids=ids)
            remaining = self.col.get(where={"doc_id": doc_id}, include=[])["ids"]
            if remaining:
                raise DocumentDeletionError(
                    "Document deletion could not be verified in the vector store. Please retry.")
        return len(ids)

    def count(self) -> int:
        return self.col.count()
