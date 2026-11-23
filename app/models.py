"""Plain data classes passed between layers (not API schemas)."""
from dataclasses import dataclass


@dataclass
class Section:
    """A piece of extracted text: one PDF page or one DOCX section."""
    text: str
    page: int        # PDF page number, or DOCX section number (1-based)
    location: str    # human readable, e.g. "Page 3" or "Section 2: Refunds"


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    filename: str
    page: int
    location: str
    position: int    # position of the chunk inside the document (0-based)
    text: str


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    filename: str
    page: int
    location: str
    position: int
    text: str
    score: float     # cosine similarity from the vector DB (1.0 = identical)
