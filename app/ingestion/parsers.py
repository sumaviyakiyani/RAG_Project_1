"""Text extraction from PDF and DOCX files."""
import io
import logging

from docx import Document
from pypdf import PdfReader

from app.errors import CorruptFileError
from app.models import Section

logger = logging.getLogger(__name__)


def parse_pdf(data: bytes) -> list[Section]:
    """Return one Section per PDF page that has text."""
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise CorruptFileError("The PDF is password-protected.")
        sections = []
        for number, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:  # one bad page should not kill the whole file
                logger.warning("Could not extract text from page %s", number)
                text = ""
            if text.strip():
                sections.append(Section(text=text, page=number, location=f"Page {number}"))
        return sections
    except CorruptFileError:
        raise
    except Exception as exc:
        raise CorruptFileError("The PDF file is corrupt or unreadable.") from exc


def parse_docx(data: bytes) -> list[Section]:
    """Return one Section per heading. DOCX has no real pages, so sections are numbered."""
    try:
        doc = Document(io.BytesIO(data))
    except Exception as exc:
        raise CorruptFileError("The DOCX file is corrupt or unreadable.") from exc

    sections: list[Section] = []
    heading, buffer = "Start of document", []

    def flush() -> None:
        text = "\n".join(buffer).strip()
        if text:
            number = len(sections) + 1
            sections.append(Section(text, number, f"Section {number}: {heading[:60]}"))
        buffer.clear()

    for para in doc.paragraphs:
        style = (para.style.name or "") if para.style is not None else ""
        if style.startswith("Heading") or style == "Title":
            flush()
            heading = para.text.strip() or heading
            buffer.append(para.text)
        elif para.text.strip():
            buffer.append(para.text)
    flush()

    table_rows = [
        " | ".join(cell.text.strip() for cell in row.cells)
        for table in doc.tables for row in table.rows
    ]
    if any(r.strip(" |") for r in table_rows):
        heading = "Tables"
        buffer.extend(table_rows)
        flush()
    return sections
