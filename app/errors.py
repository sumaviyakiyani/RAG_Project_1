"""Application errors. Each one maps to an HTTP status code and a stable error code."""


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class EmptyDocumentError(AppError):
    status_code, code = 400, "empty_document"


class CorruptFileError(AppError):
    status_code, code = 400, "corrupt_file"


class FileTooLargeError(AppError):
    status_code, code = 413, "file_too_large"


class UnsupportedFileTypeError(AppError):
    status_code, code = 415, "unsupported_file_type"


class DuplicateDocumentError(AppError):
    status_code, code = 409, "duplicate_document"


class DocumentNotFoundError(AppError):
    status_code, code = 404, "document_not_found"


class DocumentDeletionError(AppError):
    status_code, code = 500, "document_deletion_failed"


class QuestionBlockedError(AppError):
    status_code, code = 422, "question_blocked"


class RateLimitError(AppError):
    status_code, code = 429, "rate_limit_exceeded"


class ExternalServiceError(AppError):
    status_code, code = 503, "external_service_unavailable"
