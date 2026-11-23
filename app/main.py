"""FastAPI application. Routes stay thin: all logic lives in app/services."""
import logging
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.errors import AppError
from app.schemas import AskRequest, AskResponse, DocumentInfo, ErrorResponse, HealthResponse
from app.services.container import Services, build_services

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app")

app = FastAPI(
    title="Production RAG Service",
    version="1.0.0",
    description="Upload PDF/DOCX documents and ask questions. Answers are grounded in your "
                "documents, include citations, and the system refuses when documents lack the answer.",
)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
                   allow_methods=["*"], allow_headers=["*"])


@lru_cache
def get_services() -> Services:
    return build_services(get_settings())


def rate_limited(request: Request, services: Services = Depends(get_services)) -> None:
    services.limiter.check(request.client.host if request.client else "unknown")


ERRORS = {code: {"model": ErrorResponse} for code in (400, 404, 409, 413, 415, 422, 429, 500, 503)}


# ---- consistent JSON errors: {"error": {"code": ..., "message": ...}} ----
@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code,
                        content={"error": {"code": exc.code, "message": exc.message}})


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())
    return JSONResponse(status_code=422, content={"error": {"code": "invalid_request", "message": details}})


@app.exception_handler(Exception)
async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"error": {"code": "internal_error",
                                                            "message": "Unexpected server error."}})


# ---- routes ----
@app.get("/health", response_model=HealthResponse, tags=["System"], summary="Health check")
def health(services: Services = Depends(get_services)) -> HealthResponse:
    return HealthResponse(status="ok", documents=len(services.store.list_documents()),
                          chunks=services.store.count())


@app.post("/documents", status_code=201, response_model=DocumentInfo, responses=ERRORS,
          tags=["Documents"], summary="Upload a PDF or DOCX document",
          dependencies=[Depends(rate_limited)])
def upload_document(file: UploadFile = File(..., description="A .pdf or .docx file"),
                    services: Services = Depends(get_services)) -> dict:
    max_bytes = services.settings.max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)
    return services.ingestion.ingest(file.filename, data)


@app.get("/documents", response_model=list[DocumentInfo], tags=["Documents"],
         summary="List uploaded documents")
def list_documents(services: Services = Depends(get_services)) -> list[dict]:
    return services.store.list_documents()


@app.delete("/documents/{doc_id}", status_code=204, responses=ERRORS, tags=["Documents"],
            summary="Delete a document and all of its chunks")
def delete_document(doc_id: str, services: Services = Depends(get_services)) -> Response:
    from app.errors import DocumentNotFoundError
    if services.store.delete_document(doc_id) == 0:
        raise DocumentNotFoundError(f"No document with id '{doc_id}'.")
    return Response(status_code=204)


@app.post("/ask", response_model=AskResponse, responses=ERRORS, tags=["Question answering"],
          summary="Ask a question about the uploaded documents",
          dependencies=[Depends(rate_limited)])
def ask(body: AskRequest, services: Services = Depends(get_services)) -> AskResponse:
    return services.rag.ask(body.question, body.top_k)


# ---- frontend (same origin, so no CORS trouble) ----
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("/app/")


if FRONTEND.exists():
    app.mount("/app", StaticFiles(directory=FRONTEND, html=True), name="frontend")
