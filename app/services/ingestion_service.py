"""Ingestion pipeline: validate -> hash -> parse -> chunk -> embed -> store."""
import hashlib
import logging
import uuid
from pathlib import Path

from app.config import Settings
from app.errors import (CorruptFileError, DuplicateDocumentError, EmptyDocumentError,
                        FileTooLargeError, UnsupportedFileTypeError)
from app.ingestion.chunking import chunk_sections
from app.ingestion.parsers import parse_docx, parse_pdf

logger = logging.getLogger(__name__)

PARSERS = {".pdf": (parse_pdf, b"%PDF"), ".docx": (parse_docx, b"PK")}  # (parser, magic bytes)


class IngestionService:
    def __init__(self, embedder, store, settings: Settings):
        self.embedder, self.store, self.s = embedder, store, settings

    def ingest(self, filename: str | None, data: bytes) -> dict:
        name = Path(filename or "").name
        ext = Path(name).suffix.lower()
        if ext not in PARSERS:
            raise UnsupportedFileTypeError("Only PDF and DOCX files are supported.")
        if not data:
            raise EmptyDocumentError("The uploaded file is empty.")
        if len(data) > self.s.max_upload_mb * 1024 * 1024:
            raise FileTooLargeError(f"File is larger than {self.s.max_upload_mb} MB.")

        parser, magic = PARSERS[ext]
        if not data.startswith(magic):
            raise CorruptFileError(f"The file content does not look like a real {ext[1:].upper()}.")

        file_hash = hashlib.sha256(data).hexdigest()
        if self.store.find_by_hash(file_hash):
            raise DuplicateDocumentError("This document has already been uploaded.")

        sections = [s for s in parser(data) if s.text.strip()]
        if not sections:
            raise EmptyDocumentError(
                "No extractable text found (empty file, or a scanned PDF that needs OCR).")

        doc_id = uuid.uuid4().hex[:12]
        chunks = chunk_sections(sections, doc_id, name, self.s.chunk_size, self.s.chunk_overlap)
        embeddings = self.embedder.embed([c.text for c in chunks])
        self.store.add_chunks(chunks, embeddings, file_hash)
        logger.info("Ingested %s as %s (%d chunks)", name, doc_id, len(chunks))
        return next(d for d in self.store.list_documents() if d["doc_id"] == doc_id)
