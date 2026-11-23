"""Pydantic models for API requests and responses."""
from pydantic import BaseModel, ConfigDict, Field


class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    file_hash: str = Field(description="SHA-256 of the file, used for duplicate detection")
    chunk_count: int
    page_count: int
    uploaded_at: str

    model_config = ConfigDict(json_schema_extra={"examples": [{
        "doc_id": "a1b2c3d4e5f6", "filename": "handbook.pdf", "file_hash": "9f86d0...",
        "chunk_count": 42, "page_count": 12, "uploaded_at": "2026-11-22T10:00:00+00:00"}]})


class AskRequest(BaseModel):
    question: str = Field(description="Question about the uploaded documents")
    top_k: int | None = Field(default=None, ge=1, le=20, description="How many chunks to retrieve")

    model_config = ConfigDict(json_schema_extra={"examples": [
        {"question": "What is the refund period?", "top_k": 5}]})


class RetrievedChunkOut(BaseModel):
    source_number: int | None = Field(description="Number used in citations like [1]; null if not sent to the LLM")
    chunk_id: str
    doc_id: str
    filename: str
    location: str
    page: int
    position: int
    score: float = Field(description="Cosine similarity from the vector database")
    text: str
    used_in_context: bool


class Citation(BaseModel):
    source_number: int
    chunk_id: str
    filename: str
    location: str


class AskResponse(BaseModel):
    answer: str
    answerable: bool
    refusal_reason: str | None = None
    citations: list[Citation]
    total_retrieved: int
    retrieved_chunks: list[RetrievedChunkOut]


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class HealthResponse(BaseModel):
    status: str
    documents: int
    chunks: int
