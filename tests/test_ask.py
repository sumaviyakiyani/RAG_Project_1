"""Question answering, refusals, citations, external failure, rate limit."""
from tests.conftest import REFUND_PDF, SHIPPING_DOCX, upload

Q = {"question": "Are refunds available within 30 days?"}


def test_answer_has_valid_citation_and_real_scores(client):
    upload(client, "refunds.pdf", REFUND_PDF)
    r = client.post("/ask", json=Q)
    assert r.status_code == 200
    body = r.json()
    assert body["answerable"] is True
    assert body["citations"][0]["filename"] == "refunds.pdf"
    assert body["citations"][0]["location"] == "Page 1"
    assert body["total_retrieved"] == len(body["retrieved_chunks"]) >= 1
    top = body["retrieved_chunks"][0]
    assert 0.2 < top["score"] <= 1.0 and top["used_in_context"] and "Refunds" in top["text"]


def test_every_citation_points_to_a_retrieved_chunk(client):
    upload(client, "refunds.pdf", REFUND_PDF)
    upload(client, "warranty.docx", SHIPPING_DOCX)
    body = client.post("/ask", json=Q).json()
    retrieved_ids = {c["chunk_id"] for c in body["retrieved_chunks"]}
    assert {c["chunk_id"] for c in body["citations"]} <= retrieved_ids


def test_unanswerable_question_refused_without_calling_llm(client, llm):
    upload(client, "refunds.pdf", REFUND_PDF)
    body = client.post("/ask", json={"question": "What is the capital of France?"}).json()
    assert body["answerable"] is False and body["refusal_reason"] == "low_relevance"
    assert body["citations"] == [] and llm.calls == []


def test_no_documents_uploaded(client):
    body = client.post("/ask", json=Q).json()
    assert body["answerable"] is False and body["refusal_reason"] == "no_documents"


def test_model_declining_becomes_refusal(client, llm):
    upload(client, "refunds.pdf", REFUND_PDF)
    llm.reply = "INSUFFICIENT_INFORMATION"
    body = client.post("/ask", json=Q).json()
    assert body["answerable"] is False and body["refusal_reason"] == "model_declined"


def test_invented_citation_is_removed(client, llm):
    upload(client, "refunds.pdf", REFUND_PDF)
    llm.reply = "Refunds are available within 30 days of purchase [1][7]."
    body = client.post("/ask", json=Q).json()
    assert body["answerable"] and "[7]" not in body["answer"]
    assert [c["source_number"] for c in body["citations"]] == [1]


def test_answer_with_only_invalid_citations_is_refused(client, llm):
    upload(client, "refunds.pdf", REFUND_PDF)
    llm.reply = "Refunds are available within 30 days of purchase [9]."
    body = client.post("/ask", json=Q).json()
    assert body["answerable"] is False and body["refusal_reason"] == "no_valid_citation"


def test_answer_without_citation_is_refused(client, llm):
    upload(client, "refunds.pdf", REFUND_PDF)
    llm.reply = "Refunds are available within 30 days of purchase."
    assert client.post("/ask", json=Q).json()["refusal_reason"] == "no_valid_citation"


def test_missing_citation_gets_one_retry_and_is_still_validated(client, llm, monkeypatch):
    upload(client, "refunds.pdf", REFUND_PDF)
    replies = iter([
        "Refunds are available within 30 days of purchase.",
        "Refunds are available within 30 days of purchase [1].",
    ])

    def reply(messages):
        llm.calls.append(messages)
        return next(replies)

    monkeypatch.setattr(llm, "chat", reply)
    response = client.post("/ask", json=Q)

    assert response.status_code == 200
    body = response.json()
    assert body["answerable"] is True
    assert [citation["source_number"] for citation in body["citations"]] == [1]
    assert len(llm.calls) == 2
    assert "previous answer did not include a valid source marker" in llm.calls[1][0]["content"]


def test_unsupported_claims_are_refused(client, llm):
    upload(client, "refunds.pdf", REFUND_PDF)
    llm.reply = "Quantum physics describes subatomic particles using wavefunctions and probability amplitudes [1]."
    assert client.post("/ask", json=Q).json()["refusal_reason"] == "unsupported_claims"


def test_llm_failure_returns_503(client, llm):
    upload(client, "refunds.pdf", REFUND_PDF)
    llm.fail = True
    r = client.post("/ask", json=Q)
    assert r.status_code == 503 and r.json()["error"]["code"] == "external_service_unavailable"


def test_invalid_request_422_consistent_json(client):
    r = client.post("/ask", json={"top_k": 3})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_request"


def test_rate_limit_429(make_client):
    c = make_client(rate_limit_per_min=2)
    codes = [c.post("/ask", json=Q).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
