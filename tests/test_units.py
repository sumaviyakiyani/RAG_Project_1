"""Unit tests for chunking and the extractors."""
from app.ingestion.chunking import chunk_sections, split_text
from app.ingestion.parsers import parse_docx, parse_pdf
from tests.conftest import REFUND_PDF, make_docx


def test_chunks_respect_size_and_cover_all_text():
    text = " ".join(f"Sentence number {i} is here." for i in range(100))
    chunks = split_text(text, size=200, overlap=40)
    assert len(chunks) > 5 and all(len(c) <= 260 for c in chunks)
    assert "Sentence number 0" in chunks[0] and "Sentence number 99" in chunks[-1]


def test_overlap_repeats_text_between_neighbours():
    text = " ".join(f"Sentence number {i} is here." for i in range(30))
    chunks = split_text(text, size=150, overlap=50)
    assert any(w in chunks[1] for w in chunks[0].split()[-3:])


def test_chunk_metadata_is_complete():
    sections = parse_pdf(REFUND_PDF)
    chunks = chunk_sections(sections, "doc1", "x.pdf", 800, 100)
    c = chunks[0]
    assert (c.doc_id, c.filename, c.page, c.position) == ("doc1", "x.pdf", 1, 0) and c.text
    assert [c.position for c in chunks] == list(range(len(chunks)))


def test_pdf_extraction_gives_one_section_per_page():
    sections = parse_pdf(REFUND_PDF)
    assert [s.page for s in sections] == [1, 2] and "Refunds" in sections[0].text


def test_docx_extraction_splits_on_headings():
    data = make_docx([("heading", "Intro"), ("text", "Hello"), ("heading", "Terms"), ("text", "World")])
    sections = parse_docx(data)
    assert len(sections) == 2 and sections[1].location.startswith("Section 2: Terms")
