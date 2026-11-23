"""Split text into overlapping chunks that respect sentence boundaries where possible."""
import re

from app.models import Chunk, Section


def split_text(text: str, size: int, overlap: int) -> list[str]:
    """Greedy packing of sentences into chunks of about `size` characters."""
    if size <= overlap:
        raise ValueError("chunk size must be larger than overlap")
    text = re.sub(r"[ \t]+", " ", text).strip()
    units = [u.strip() for u in re.split(r"(?<=[.!?])\s+|\n{2,}", text) if u.strip()]

    chunks: list[str] = []
    current = ""

    def tail(s: str) -> str:
        """Last `overlap` characters, cut at a word boundary."""
        if overlap <= 0 or len(s) <= overlap:
            return s if overlap > 0 else ""
        piece = s[-overlap:]
        return piece.split(" ", 1)[1] if " " in piece else piece

    for unit in units:
        while len(unit) > size:  # a single huge sentence: hard split
            if current:
                chunks.append(current)
                current = ""
            chunks.append(unit[:size])
            unit = unit[size - overlap:]
        if not current:
            current = unit
        elif len(current) + 1 + len(unit) <= size:
            current = f"{current} {unit}"
        else:
            chunks.append(current)
            current = f"{tail(current)} {unit}".strip()
    if current.strip():
        chunks.append(current)
    return chunks


def chunk_sections(sections: list[Section], doc_id: str, filename: str,
                   size: int, overlap: int) -> list[Chunk]:
    """Chunk every section and attach metadata to each chunk."""
    result: list[Chunk] = []
    for section in sections:
        for piece in split_text(section.text, size, overlap):
            position = len(result)
            result.append(Chunk(f"{doc_id}:{position}", doc_id, filename,
                                section.page, section.location, position, piece))
    return result
