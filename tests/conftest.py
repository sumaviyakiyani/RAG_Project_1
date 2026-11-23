"""Shared fixtures. Tests use a fake embedder (hash) and a FakeLLM: fast, offline, no API key."""
import io

import pytest
from docx import Document
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from app.config import Settings
from app.errors import ExternalServiceError
from app.main import app, get_services
from app.services.container import build_services


class FakeLLM:
    """Stands in for the real LLM. Records every prompt it receives."""

    def __init__(self):
        self.reply = "Refunds are available within 30 days of purchase [1]."
        self.fail = False
        self.calls: list[list[dict]] = []

    def chat(self, messages):
        self.calls.append(messages)
        if self.fail:
            raise ExternalServiceError("The LLM service is unavailable (test).")
        return self.reply


def make_pdf(pages: list[str]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for text in pages:
        if text:
            c.drawString(50, 750, text)
        c.showPage()
    c.save()
    return buf.getvalue()


def make_docx(blocks: list[tuple[str, str]]) -> bytes:
    """blocks = [("heading"|"text", content), ...]"""
    doc = Document()
    for kind, content in blocks:
        doc.add_heading(content, level=1) if kind == "heading" else doc.add_paragraph(content)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


REFUND_PDF = make_pdf(["Refunds are available within 30 days of purchase. A receipt is required.",
                       "Shipping takes five business days for domestic orders."])
SHIPPING_DOCX = make_docx([("heading", "Warranty"),
                           ("text", "The warranty covers manufacturing defects for twelve months.")])


@pytest.fixture
def llm():
    return FakeLLM()


@pytest.fixture
def make_client(tmp_path, llm):
    def _make(**overrides):
        opts = dict(embedding_backend="hash", chroma_dir=str(tmp_path / "chroma"),
                    min_score=0.2, rate_limit_per_min=1000)
        opts.update(overrides)
        settings = Settings(_env_file=None, **opts)
        services = build_services(settings, llm=llm)
        app.dependency_overrides[get_services] = lambda: services
        return TestClient(app)
    yield _make
    app.dependency_overrides.clear()


@pytest.fixture
def client(make_client):
    return make_client()


def upload(client, name, data, content_type="application/octet-stream"):
    return client.post("/documents", files={"file": (name, data, content_type)})
