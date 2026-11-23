# AI usage

| Item | Details |
|---|---|
| AI tool used for building | Claude (Anthropic) in the Claude web/app chat |
| Model | Claude Sonnet 5.5 |
| Runtime LLM in the project | Groq-hosted open model set in `.env` (`LLM_MODEL`); fill in the exact name you used |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 (local) |
| Configuration | temperature 0, max_tokens 600, timeout 30 s, 2 retries |

## How AI assistance was used
Claude generated the initial project structure, code, tests, frontend and documentation from the instructor
requirements. The student must read and be able to explain every file, run the tests and evaluation themselves,
and record any changes they make.

## Prompts used
# MASTER PROMPT — Production RAG Service
## Agentic AI Portfolio Project 01

You are an expert AI/ML engineer, Python backend developer, RAG specialist, software architect, and patient programming instructor.

I am a complete beginner. I have almost no knowledge of how to build a RAG chatbot, FastAPI backend, vector database, embeddings, or AI evaluation.

Your task is to help me build my complete university portfolio project from absolute zero, according to the instructor's requirements below.

**Important:** Do not just give me a theoretical explanation or a small demo. Help me build a complete, functional, well-structured, tested, evaluated, documented, and demonstrable project.

I must understand the code because I will have to explain it in front of my instructor.

---

## 1. Project Information

Project name: Production RAG Service  
Project type: Own Corpus RAG Chatbot  
Instructor: Osama Izhar  
Deadline: 25 November 2026

The project is a document-based question-answering system.

Users should be able to upload their own PDF and DOCX documents, ask questions about them, and receive accurate answers grounded in the uploaded documents, with citations and source references.

The chatbot must retrieve relevant document chunks, generate an answer using an LLM, and refuse to answer when the documents do not contain sufficient information.

---

## 2. My Skill Level

Assume I am a complete beginner.

Explain everything in simple English. You may use Roman Urdu when explaining difficult concepts.

For every important concept, explain:

- What it is.
- Why we need it.
- How it works.
- Where it is used in this project.

Do not assume I know terminal commands, Python environments, APIs, Git, or project architecture.

Whenever you give me a command:

1. Tell me which terminal to open.
2. Tell me which folder I should be inside.
3. Give me the exact command.
4. Explain what the command does.
5. Tell me what successful output should look like.
6. Tell me how to fix common errors.

Do not overwhelm me with the entire project at once. Build it in manageable stages.

---

## 3. Technology Requirements

The project must use:

- Python
- FastAPI
- Embedding model
- Vector database
- LLM API or suitable LLM
- LangChain, LangGraph, or custom Python code
- Retrieval evaluation framework
- Guardrails
- pytest
- Git and GitHub
- Jupyter notebooks
- HTML and CSS frontend at minimum

React or another modern frontend technology may be used for bonus marks if it is practical within the deadline.

No-code or drag-and-drop RAG builders such as Flowise, Langflow, and Dify are prohibited.

You must build the actual RAG pipeline using code.

Choose beginner-friendly, affordable technologies. Prefer free or open-source components where practical.

Before selecting any technology, explain its advantages, disadvantages, alternatives, cost, latency, privacy, and suitability for this project.

Do not assume that a paid API is free. Tell me if I need an API key, where to obtain it, and whether it requires payment.

Keep all API keys in environment variables. Never hardcode secrets.

---

## 4. Required Architecture

Create a clean, layered project structure similar to:

project/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── guardrails.py
│   ├── retrieval.py
│   ├── generation.py
│   ├── ingestion/
│   └── services/
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── notebooks/
├── evals/
├── tests/
├── data/
├── DESIGN.md
├── EVAL.md
├── README.md
├── AI_USAGE.md
├── requirements.txt
├── .env.example
├── .gitignore
└── ...

You may improve this structure, but maintain separation of concerns.

Keep business logic out of API routes.

Use type hints, meaningful names, comments, docstrings, appropriate error handling, timeouts, retries, and logging.

---

## 5. Mandatory Ingestion Pipeline

Implement a complete document ingestion pipeline.

The system must:

1. Accept PDF and DOCX documents.
2. Validate uploaded files.
3. Extract text from documents.
4. Handle empty documents and PDFs without extractable text.
5. Split text into chunks.
6. Generate embeddings.
7. Store embeddings in a vector database.
8. Store metadata with every chunk.

Every chunk must include:

- Document ID
- File name
- Page or section
- Chunk position
- Chunk text
- Any additional useful metadata

Implement duplicate detection using a file hash.

If the same document is uploaded twice, return an appropriate error instead of storing it again.

Implement document deletion. Deleting a document must remove all its associated vectors and metadata so its content cannot appear in future answers.

---

## 6. RAG Question-Answering Pipeline

Implement the complete pipeline:

User question → Input validation → Query embedding → Vector retrieval → Context selection → LLM generation → Citation validation → Final answer

The chatbot must:

- Retrieve relevant chunks from uploaded documents.
- Generate answers grounded in retrieved context.
- Provide citations that point to actual retrieved chunks.
- Show document name and page or section.
- Refuse when the documents do not contain enough information.
- Never invent citations.
- Never cite a chunk that was not retrieved.
- Handle conflicting information from different documents appropriately.

Do not allow the LLM to answer from general knowledge when the question requires information from the user's documents.

---

## 7. Frontend Requirements

Build a proper user interface.

The frontend must allow users to:

- Upload PDF files.
- Upload DOCX files.
- View uploaded documents.
- Delete uploaded documents.
- Ask questions.
- View chatbot answers.
- View citations and sources.

For every answer, display a separate retrieved-chunks section showing:

- Total number of chunks retrieved.
- Actual retrieved chunk text.
- Similarity score of each chunk.
- Document name.
- Page or section.
- Chunk ID or position.

Do not display fake scores or placeholder chunks.

The scores must come from the actual retrieval process.

Make the UI clean, professional, responsive, and suitable for a university project demonstration.

---

## 8. API Requirements

Create suitable FastAPI endpoints.

At minimum, implement endpoints for:

- Uploading documents
- Listing uploaded documents
- Deleting documents
- Asking questions
- Health checking

Use appropriate HTTP status codes.

Examples:

200 — Successful request  
201 — Document created  
204 — Document deleted  
400 — Empty file or no extractable text  
404 — Document not found  
409 — Duplicate document  
415 — Unsupported file type  
422 — Invalid request  
429 — Rate limit exceeded  
503 — External service unavailable

Return consistent JSON error responses.

Use Pydantic schemas for request and response validation.

Add clear descriptions and examples to FastAPI's automatic Swagger documentation.

Swagger must be accessible at:

http://127.0.0.1:8000/docs

---

## 9. Retrieval Evaluation — Very Important

A working chatbot without measured evaluation will not pass.

Build a reproducible evaluation system.

### Golden dataset

Create at least 25 questions from the selected document corpus.

Include:

- Answerable questions
- At least 5 unanswerable questions
- Reworded questions
- Multi-part questions

Each question must include:

- Question
- Reference answer
- Correct source document
- Correct page or chunk
- Whether the question is answerable

Do not invent evaluation results.

Use actual documents to create the questions and reference answers.

### Retrieval metrics

Measure:

- Hit Rate@k
- Recall@k
- Mean Reciprocal Rank (MRR)

### Answer metrics

Evaluate:

- Faithfulness
- Answer correctness
- Context relevance
- Citation correctness
- Correct refusal for unanswerable questions

Use RAGAS, an LLM-as-a-judge, Langfuse, or suitable alternatives.

Explain the purpose of each metric and framework.

### Configuration comparison

Compare at least two real configurations.

For example:

- Different chunk sizes or overlap values.
- Different embedding models.
- Retrieval with and without reranking.

Run both configurations on the same golden dataset.

Save the actual results and select the best configuration based on measured performance.

Create EVAL.md containing:

- Golden dataset
- Evaluation methodology
- Metrics
- Configuration comparison
- Actual results
- Failure analysis
- Selected configuration and justification

One command must run the evaluation and save the results.

Never fabricate scores or claim an evaluation passed without actually running it.

---

## 10. Guardrails and Security

Implement input and output guardrails.

Input protection must cover:

- Empty questions
- Extremely long questions
- Prompt injection
- Jailbreak attempts
- Requests to reveal system prompts
- Off-topic requests, where appropriate

Output protection must cover:

- Unsupported claims
- Invented citations
- Invalid source references
- System prompt leakage
- API key leakage

Treat instructions inside uploaded documents as untrusted data.

The model must not follow malicious instructions contained in documents.

Implement document validation and reject corrupt or unsupported files.

Create tests demonstrating that the guardrails work.

Do not rely only on a prompt saying "ignore prompt injection." Use appropriate validation, context isolation, output checks, and tests.

---

## 11. Testing Requirements

Testing is mandatory.

Start with Jupyter notebooks before implementing the complete API.

Create notebooks that demonstrate:

1. PDF text extraction
2. DOCX text extraction
3. Chunking
4. Embedding generation
5. Vector storage
6. Retrieval
7. Answer generation
8. Citation handling

After the basic pipeline works, implement API-based tests using pytest and FastAPI's TestClient or suitable tools.

Test both successful operations and expected failures.

Include tests for:

- Valid document upload
- Invalid file type
- Duplicate upload
- Empty document
- Document deletion
- Question answering
- Unanswerable questions
- Prompt injection
- Invalid citations
- Missing documents
- External API failure

Actually execute the tests and show me their results.

Submit all notebooks.

---

## 12. Git and GitHub

Help me create a public GitHub repository.

Use main as the stable branch.

Create feature branches such as:

- feature/ingestion
- feature/retrieval
- feature/ask-endpoint
- feature/frontend
- feature/evals
- feature/guardrails

Explain how to commit and merge changes.

Never commit API keys.

Create a .gitignore and .env.example.

Use meaningful commit messages.

---

## 13. Documentation

Create all required documentation.

### README.md

Include:

- Project overview
- Features
- Architecture
- Installation instructions
- Environment setup
- How to run the backend
- How to run the frontend
- How to run tests
- How to run evaluation
- API documentation
- Deployment information

### DESIGN.md

Explain and justify:

- Corpus selection
- Text extraction
- Chunking strategy
- Embedding model
- Vector database
- Retrieval settings
- LLM selection
- Prompt design
- API design
- Architecture
- Testing approach

For each decision, compare alternatives and discuss quality, cost, speed, latency, privacy, and trade-offs.

### EVAL.md

Include the golden dataset, evaluation methodology, metrics, configuration comparison, real results, and failure analysis.

### AI_USAGE.md

Document:

- AI tools used
- AI models used
- Prompts used
- Relevant configurations
- How AI assistance was used

Help me maintain a list of prompts and preserve the project-related conversation history as required by the instructor.

---

## 14. Bonus Features

First complete all mandatory requirements.

Then, if time allows, implement bonus features in this order:

1. JWT signup and login
2. User-specific document isolation
3. Multilingual questions and answers
4. Additional file formats such as TXT and Markdown
5. Monitoring and observability
6. Deployment to a public URL

Do not sacrifice mandatory features or evaluation quality to implement unnecessary bonus features.

---

## 15. Demo Video Requirements

Help me prepare a complete demo video.

The video must demonstrate:

1. Introduction and selected corpus
2. Architecture and project structure
3. Design decisions and their justifications
4. Uploading a PDF
5. Uploading a DOCX
6. At least three questions with citations
7. Retrieved chunks, count, and scores
8. An unanswerable question
9. Document deletion and proof that deleted content is no longer retrieved
10. Prompt injection and jailbreak protection
11. At least two error cases with status codes
12. Edge cases handled
13. Evaluation execution and actual results
14. Configuration comparison
15. Test execution
16. Swagger documentation
17. Any implemented bonus features

Prepare a simple speaking script so I can explain the project confidently.

---

## 16. How You Must Work With Me

Follow these rules throughout the project.

**Rule 1:** Start by helping me install the required software and set up my development environment.

**Rule 2:** Ask only essential questions. Do not overwhelm me with a long questionnaire.

**Rule 3:** Work in small stages. Finish one stage before moving to the next.

**Rule 4:** Give complete code for each file, not incomplete snippets that require me to guess missing parts.

**Rule 5:** Tell me exactly where each file should be created.

**Rule 6:** Explain the code in beginner-friendly language.

**Rule 7:** After each stage, tell me how to run and verify it.

**Rule 8:** If an error occurs, help me debug the actual error instead of restarting the project unnecessarily.

**Rule 9:** Do not claim something works unless it has been tested or clearly state that it has not been tested.

**Rule 10:** Do not make up evaluation metrics, citations, test results, or deployment status.

**Rule 11:** Keep track of completed and remaining requirements.

**Rule 12:** Maintain a practical plan based on the 25 November 2026 deadline.

**Rule 13:** Help me understand every important design decision so I can explain it to my instructor.

**Rule 14:** Use simple, reliable solutions rather than unnecessarily complicated enterprise architecture.

**Rule 15:** Keep the code production-minded but beginner-friendly.

---

## 17. Start Now

Begin with Stage 1.

First, briefly explain the overall project workflow in simple language.

Then help me check my operating system and development environment.

Tell me exactly which software I need to install, provide official download links, and guide me through installation one step at a time.

Do not generate the entire project immediately.

Start with environment setup, then proceed through the project step by step until the complete project is implemented, tested, evaluated, documented, and ready for submission.

Remember: I am a beginner, and I need both a working project and the ability to explain it confidently.
### AI Tool Usage and Debugging

The master project prompt, containing the complete project requirements and instructions, was submitted to **Claude (Anthropic)** to generate the initial project structure, implementation, frontend, backend, tests, and documentation.

For further debugging and code assistance, **GitHub Copilot**, available within Visual Studio Code, was used. It helped identify errors, investigate issues, and suggest code fixes during development. The suggested changes were reviewed and tested to ensure the project continued to work correctly.

Both AI tools supported the development process, while the project was tested and evaluated by the student.
