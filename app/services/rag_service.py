"""The full question-answering pipeline.

question -> input guardrail -> retrieve -> select context -> LLM -> output guardrail -> response
"""
import logging

from app.config import Settings
from app.generation import generate
from app.guardrails import check_question, validate_answer
from app.retrieval import Retriever
from app.schemas import AskResponse, Citation, RetrievedChunkOut

logger = logging.getLogger(__name__)

REFUSALS = {
    "no_documents": "No documents have been uploaded yet. Please upload a PDF or DOCX first.",
    "low_relevance": "I could not find enough relevant information in the uploaded documents to answer this.",
    "model_declined": "The documents do not contain enough information to answer this question.",
    "no_valid_citation": "I could not produce an answer that is backed by a valid citation.",
    "unsupported_claims": "I could not verify the answer against the documents, so I will not give it.",
    "system_prompt_leak": "I could not produce a safe answer to this question.",
    "empty_answer": "The model returned no answer. Please try again.",
}


class RagService:
    def __init__(self, retriever: Retriever, llm, settings: Settings):
        self.retriever, self.llm, self.s = retriever, llm, settings

    def ask(self, question: str, top_k: int | None = None) -> AskResponse:
        question = check_question(question, self.s)                       # input guardrail
        retrieved = self.retriever.retrieve(question, top_k)              # embed + vector search
        context = self.retriever.select_context(retrieved)                # score threshold
        numbering = {c.chunk_id: i for i, c in enumerate(context, start=1)}

        def refuse(reason: str, cited: list[int] | None = None) -> AskResponse:
            logger.info("Refusing question (%s)", reason)
            return self._response(REFUSALS[reason], False, reason, retrieved, numbering, [])

        if not retrieved:
            return refuse("no_documents")
        if not context:
            return refuse("low_relevance")                                # LLM is never called

        raw = generate(self.llm, question, context)                       # may raise 503
        checked = validate_answer(raw, [c.text for c in context], self.s)  # output guardrail
        if not checked.ok and checked.reason == "no_valid_citation":
            raw = generate(self.llm, question, context, citation_retry=True)
            checked = validate_answer(raw, [c.text for c in context], self.s)
        if not checked.ok:
            return refuse(checked.reason)
        cited = [context[n - 1] for n in checked.cited]
        return self._response(checked.text, True, None, retrieved, numbering, cited)

    @staticmethod
    def _response(answer, answerable, reason, retrieved, numbering, cited) -> AskResponse:
        return AskResponse(
            answer=answer, answerable=answerable, refusal_reason=reason,
            citations=[Citation(source_number=numbering[c.chunk_id], chunk_id=c.chunk_id,
                                filename=c.filename, location=c.location) for c in cited],
            total_retrieved=len(retrieved),
            retrieved_chunks=[RetrievedChunkOut(
                source_number=numbering.get(c.chunk_id), chunk_id=c.chunk_id, doc_id=c.doc_id,
                filename=c.filename, location=c.location, page=c.page, position=c.position,
                score=c.score, text=c.text, used_in_context=c.chunk_id in numbering)
                for c in retrieved])
