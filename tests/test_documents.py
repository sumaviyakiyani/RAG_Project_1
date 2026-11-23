"""Upload, list, duplicate, invalid, empty, corrupt, delete."""
from app.main import app, get_services
from tests.conftest import REFUND_PDF, SHIPPING_DOCX, make_docx, make_pdf, upload


def test_upload_pdf_returns_201_with_metadata(client):
    r = upload(client, "refunds.pdf", REFUND_PDF)
    assert r.status_code == 201
    body = r.json()
    assert body["filename"] == "refunds.pdf" and body["page_count"] == 2 and body["chunk_count"] >= 2


def test_upload_docx_returns_201(client):
    r = upload(client, "warranty.docx", SHIPPING_DOCX)
    assert r.status_code == 201 and r.json()["chunk_count"] >= 1


def test_list_documents(client):
    upload(client, "a.pdf", REFUND_PDF)
    upload(client, "b.docx", SHIPPING_DOCX)
    names = {d["filename"] for d in client.get("/documents").json()}
    assert names == {"a.pdf", "b.docx"}


def test_unsupported_file_type_415(client):
    r = upload(client, "notes.txt", b"hello")
    assert r.status_code == 415 and r.json()["error"]["code"] == "unsupported_file_type"


def test_duplicate_upload_409(client):
    assert upload(client, "a.pdf", REFUND_PDF).status_code == 201
    r = upload(client, "renamed.pdf", REFUND_PDF)  # same bytes, different name
    assert r.status_code == 409 and r.json()["error"]["code"] == "duplicate_document"
    assert len(client.get("/documents").json()) == 1


def test_empty_file_400(client):
    assert upload(client, "empty.pdf", b"").status_code == 400


def test_pdf_without_text_400(client):
    r = upload(client, "blank.pdf", make_pdf(["", ""]))
    assert r.status_code == 400 and r.json()["error"]["code"] == "empty_document"


def test_docx_without_text_400(client):
    assert upload(client, "blank.docx", make_docx([])).status_code == 400


def test_corrupt_pdf_400(client):
    r = upload(client, "bad.pdf", b"%PDF-1.4 this is not really a pdf")
    assert r.status_code == 400 and r.json()["error"]["code"] == "corrupt_file"


def test_fake_extension_rejected(client):
    r = upload(client, "virus.pdf", b"MZ\x90\x00 executable")
    assert r.status_code == 400


def test_delete_removes_document_and_its_chunks(client):
    doc_id = upload(client, "a.pdf", REFUND_PDF).json()["doc_id"]
    assert client.delete(f"/documents/{doc_id}").status_code == 204
    assert client.get("/documents").json() == []
    assert client.get("/health").json()["chunks"] == 0
    assert client.delete(f"/documents/{doc_id}").status_code == 404


def test_deleted_content_is_not_retrieved(client):
    doc_id = upload(client, "a.pdf", REFUND_PDF).json()["doc_id"]
    upload(client, "b.docx", SHIPPING_DOCX)
    client.delete(f"/documents/{doc_id}")
    body = client.post("/ask", json={"question": "Are refunds available within 30 days?"}).json()
    assert all(c["filename"] != "a.pdf" for c in body["retrieved_chunks"])


def test_same_document_can_be_reuploaded_after_delete(client):
    first = upload(client, "a.pdf", REFUND_PDF)
    assert first.status_code == 201
    doc = first.json()
    services = app.dependency_overrides[get_services]()
    assert any(d["doc_id"] == doc["doc_id"] for d in client.get("/documents").json())
    assert services.store.find_by_hash(doc["file_hash"])
    assert upload(client, "a.pdf", REFUND_PDF).status_code == 409

    deleted = client.delete(f"/documents/{doc['doc_id']}")
    assert deleted.status_code == 204
    assert client.get("/documents").json() == []
    assert services.store.count() == 0
    assert services.store.col.get(
        where={"doc_id": doc["doc_id"]}, include=["metadatas"])["ids"] == []
    assert not services.store.find_by_hash(doc["file_hash"])

    assert upload(client, "a.pdf", REFUND_PDF).status_code == 201
    assert upload(client, "a.pdf", REFUND_PDF).status_code == 409


def test_delete_does_not_succeed_if_chunks_remain(client, monkeypatch):
    uploaded = upload(client, "a.pdf", REFUND_PDF)
    doc_id = uploaded.json()["doc_id"]
    services = app.dependency_overrides[get_services]()
    monkeypatch.setattr(services.store.col, "delete", lambda **kwargs: None)

    response = client.delete(f"/documents/{doc_id}")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "document_deletion_failed"
    assert services.store.find_by_hash(uploaded.json()["file_hash"])
    assert len(client.get("/documents").json()) == 1
