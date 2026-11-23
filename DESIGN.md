# Design decisions

Each decision lists what was chosen, alternatives, and trade-offs.

| Area | Chosen | Alternatives | Why chosen / trade-off |
|---|---|---|---|
| Language/API | Python + FastAPI | Flask, Django | Typed, automatic Swagger, Pydantic validation. Slightly more concepts than Flask. |
| Text extraction | pypdf, python-docx | PyMuPDF, pdfplumber, unstructured | Pure Python, easy install, free. Weaker on complex layouts/tables than PyMuPDF. No OCR: scanned PDFs are rejected with 400. |
| Chunking | Sentence-aware packing, 800 chars, 120 overlap (default; compared in EVAL.md) | Fixed windows, recursive splitter, semantic chunking | Keeps sentences intact, simple to explain. Overlap avoids cutting an answer in half; costs some duplicate storage. |
| Embeddings | `all-MiniLM-L6-v2` via sentence-transformers (local) | OpenAI/Cohere/Gemini embeddings, bge-small/large | Free, private (no text leaves the machine), fast on CPU, 384 dims. English-focused and a little less accurate than large paid models. |
| Vector DB | ChromaDB (persistent, local, cosine) | FAISS, Qdrant, Pinecone, pgvector | No server to run, stores metadata and supports delete-by-filter. Not meant for millions of chunks. |
| LLM | Any OpenAI-compatible endpoint; default Groq free tier | Gemini, Ollama (local), OpenAI, Anthropic | One code path covers all. Groq: free, very low latency; but rate limits and text goes to a third party. Ollama gives full privacy but needs a strong laptop. |
| Orchestration | Custom Python | LangChain, LangGraph | Fewer hidden layers, every step explainable. No ready-made integrations. |
| Retrieval | Top-k cosine + minimum score (0.30) | Hybrid BM25, reranker, MMR | Simple and measurable. Threshold gives cheap refusal before spending an LLM call. The value must be tuned on your data (see `mean_top_score_*` in eval output). |
| Prompt | Numbered `<document>` blocks, mandatory `[n]` citations, exact refusal token | Free-form answer, JSON output | Numbers can be machine-validated against what was retrieved. |
| Guardrails | Regex input checks, sentence-level removal of instruction-like text in documents, output validation (citation range, secrets, canary leak, grounding ratio) | LLM-based classifiers, NeMo Guardrails, Llama Guard | Deterministic, testable, free, no latency. Regex can be bypassed by paraphrase; grounding ratio is a lexical heuristic. Faithfulness is measured separately in evaluation. |
| Conflicting sources | Prompt rule 4: report both versions, cite each | Pick newest | Relies on the LLM following the rule; not separately tested yet. |
| API | REST, thin routes, errors via exception handlers | GraphQL | Matches the required status codes; logic lives in services. |
| Storage of doc list | Derived from Chroma metadata | Separate SQLite table | One source of truth: deleting chunks cannot leave stale records. Listing scans all metadata (fine at this scale). |
| Testing | pytest, FakeLLM, hash embedder | Real API in tests | Fast, free, deterministic. The hash embedder is NOT semantic, so tests prove plumbing and guardrails, not retrieval quality; quality is measured in `evals/`. |

## Known limitations
No OCR; DOCX "pages" are heading-based sections; in-memory rate limiter (one process); no authentication; the
off-topic guardrail is the similarity threshold only; paraphrased jailbreaks may pass the regex layer.
