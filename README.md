# Own Corpus RAG Chatbot

An application for uploading your own PDF and DOCX documents, asking questions about their contents, and receiving
answers grounded in those documents. Answers include source citations; when the available context is insufficient,
the chatbot refuses rather than relying on outside knowledge.

## Features

- Upload, list, and delete PDF and DOCX documents.
- Extract document text, split it into overlapping chunks, embed the chunks, and search them by similarity.
- Return cited answers, retrieved chunks, and their similarity scores.
- Refuse questions when no relevant context is available.
- Detect duplicate uploads using SHA-256 and limit uploads to 10 MB.
- Apply input, document-context, and answer guardrails.
- Serve a browser-based chat interface from the FastAPI application.
- Compare retrieval and answer metrics using a reproducible evaluation runner.

## Architecture and RAG pipeline

```text
PDF/DOCX upload
  -> validate file type, size, content, and duplicate hash
  -> extract text (PDF pages or DOCX sections)
  -> split text into overlapping chunks
  -> create local sentence-transformer embeddings
  -> store vectors and metadata in ChromaDB

Question
  -> input guardrail
  -> embed question and retrieve top-k chunks
  -> filter chunks by similarity threshold and context budget
  -> generate an answer using the retrieved document text
  -> validate citations, grounding, and output
  -> return the answer, citations, and retrieved chunks
```

The application code is organized as follows:

| Path | Responsibility |
|---|---|
| `app/main.py` | FastAPI routes, error handling, and static frontend hosting |
| `app/ingestion/` | PDF/DOCX parsing and text chunking |
| `app/services/embeddings.py` | Local sentence-transformer and test-only hash embeddings |
| `app/services/vector_store.py` | ChromaDB persistence and similarity search |
| `app/services/llm.py` | OpenAI-compatible chat-completion client |
| `app/retrieval.py`, `app/generation.py`, `app/guardrails.py` | Retrieval, prompt construction, and answer checks |
| `frontend/` | HTML, CSS, and JavaScript chat interface |
| `evals/` | Golden dataset, configurations, evaluation runner, and results |
| `tests/` | Automated pytest suite |

## Technologies

| Technology | Why it is used |
|---|---|
| Python 3.12 | Application and evaluation runtime |
| FastAPI and Uvicorn | HTTP API, request validation, and local development server |
| Pydantic and Pydantic Settings | Typed API schemas and environment-based configuration |
| pypdf and python-docx | Text extraction from PDF pages and DOCX sections |
| Sentence Transformers (`all-MiniLM-L6-v2`) | Local dense embeddings for documents and questions |
| ChromaDB | Persistent vector storage and cosine-similarity search |
| httpx | Calls to the configured OpenAI-compatible LLM endpoint |
| HTML, CSS, and vanilla JavaScript | Lightweight browser UI served by FastAPI |
| pytest | Automated tests using a fake LLM and test embedding backend |

## Windows setup (PowerShell)

Run these commands from the project root—the directory containing `README.md`, `app\`, and `requirements.txt`.
The project targets Python 3.12. On Windows, confirm that the Python launcher can find Python 3.12:

```powershell
py -3.12 --version
```

Create the virtual environment only if it does not already exist, then activate it and install the development
requirements. `requirements-dev.txt` includes `requirements.txt` and adds test/notebook dependencies.

```powershell
if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    py -3.12 -m venv .venv
}
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Confirm `python --version` reports Python 3.12. If the existing `.venv` was created with another Python version,
create a Python 3.12 environment before continuing.

## Environment configuration

Create a local `.env` from the supplied example without overwriting an existing file:

```powershell
if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
}
```

Edit `.env` and set `LLM_API_KEY` to your own provider key. Do not put credentials in this README, source code, or
commits. `.env` is listed in `.gitignore`; keep it local.

The supplied `.env.example` documents these settings:

| Variable | Purpose |
|---|---|
| `LLM_BASE_URL` | OpenAI-compatible chat API URL (the example uses Groq) |
| `LLM_API_KEY` | Your private provider key; replace the example placeholder |
| `LLM_MODEL` | Chat model name |
| `EMBEDDING_BACKEND` | `sentence-transformers` for normal use; `hash` is for tests only |
| `EMBEDDING_MODEL` | Local embedding model |
| `CHUNK_SIZE`, `CHUNK_OVERLAP` | Chunking parameters |
| `TOP_K` | Number of top-ranked chunks to retrieve per question |
| `MIN_SCORE` | Similarity threshold for selecting context |

The application also supports environment settings such as `LLM_MIN_REQUEST_INTERVAL_S`; its default request
spacing is two seconds. The first use of the sentence-transformer model may download model files.

## Run the application

From the project root, with the virtual environment active and `.env` configured:

```powershell
python -m uvicorn app.main:app --reload
```

Keep the server running. Open `http://127.0.0.1:8000/` for the chatbot; the root URL redirects to the UI at
`/app/`. The interactive API documentation is at `http://127.0.0.1:8000/docs`. No separate frontend server is
required.

## Upload documents and ask questions

1. Open the chatbot UI and choose a PDF or DOCX file. The file is uploaded to the running backend and indexed.
2. The document appears in the Documents list. Use its Delete button to remove it and its stored chunks.
3. Enter a question in the chat box and select **Ask**.
4. The response includes citations when the answer passes the citation and grounding checks. If documents do not
   provide sufficient relevant context, the chatbot returns a refusal.

The API routes used by the UI are:

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/health` | Report service status and indexed document/chunk counts |
| `POST` | `/documents` | Upload a PDF or DOCX file |
| `GET` | `/documents` | List indexed documents |
| `DELETE` | `/documents/{doc_id}` | Delete a document and its chunks |
| `POST` | `/ask` | Ask a question; optional `top_k` is between 1 and 20 |

## Citations and retrieved chunks

Answer citations use numbered markers such as `[1]`; the citation list maps each number to a filename and page or
DOCX section. Expand **Retrieved chunks** to see how many chunks were retrieved and how many passed the context
selection checks and were sent to the model. Each chunk card shows its source number (or that it was not used),
filename, location, chunk ID, text, and similarity score.

The displayed score is the vector store's cosine similarity, formatted to three decimal places by the UI. A
retrieved chunk below the configured threshold may be shown but not supplied to the model. Similarity is a retrieval
signal, not a guarantee that an answer is correct.

## Tests and evaluation

Run the automated tests from the project root with the virtual environment active:

```powershell
python -m pytest -v
```

The tests use a fake LLM and the hash embedding backend; they do not require a live provider key.

The evaluation runner uses `data\corpus` and `evals\golden_dataset.json` by default. Review the golden questions
and their source pages for your corpus before relying on the results. Run both retrieval and LLM evaluation with:

```powershell
python -m evals.run_eval
```

For retrieval metrics without LLM calls:

```powershell
python -m evals.run_eval --skip-llm
```

Results are written under `evals\results`. The current measured comparison selects
`A_chunk500_overlap50`: both configurations reached hit rate@k and recall@k of 1.0, while A had a higher MRR
(0.7857 versus 0.7143). **LLM-based results are partial:** HTTP 429 rate-limit responses meant only 20 questions
for A and 17 for B were judged, not all 26. Treat these values as incomplete pending a further evaluation with
successful LLM requests. See [EVAL.md](EVAL.md) for the full metrics, selection evidence, and limitations.

## Security guardrails and limitations

- Questions matching the input checks for prompt injection, jailbreaks, or requests to reveal hidden instructions
  are rejected.
- Retrieved document text is treated as untrusted data; instruction-like text is sanitized before prompting.
- Generated answers are checked for valid citations and a grounding heuristic; detected secret-like strings and
  the configured API key are redacted.
- Upload and question routes have an in-memory per-client limit of 30 requests per minute. LLM requests are spaced
  and transient failures are retried, but provider HTTP 429 responses can still occur; the current evaluation
  demonstrates this limitation.
- Scanned/image-only PDFs are not OCR-processed and may be rejected as containing no extractable text.
- Retrieval quality depends on the corpus, chunking, similarity threshold, and embedding model. Grounding and
  citation checks are heuristics, not formal proof of correctness.
- This project is intended to run locally; it has not been deployed as a hosted service.
