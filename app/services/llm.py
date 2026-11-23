"""LLM client for any OpenAI-compatible chat endpoint, with timeout and retries."""
import logging
import re
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from app.config import Settings
from app.errors import ExternalServiceError

logger = logging.getLogger(__name__)
_rate_limit_lock = threading.Lock()
_next_request_at = 0.0
_SECRET_PATTERN = re.compile(r"\b(?:gsk_[A-Za-z0-9]{16,}|sk-[A-Za-z0-9_-]{16,}|AIza[0-9A-Za-z_-]{20,})\b")
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+\S+")


def _safe_error_detail(value: object, api_key: str) -> str:
    detail = " ".join(str(value).split())
    if api_key:
        detail = detail.replace(api_key, "[REDACTED]")
    detail = _BEARER_PATTERN.sub("Bearer [REDACTED]", detail)
    detail = _SECRET_PATTERN.sub("[REDACTED]", detail)
    return detail[:500]


def _http_error_detail(response: httpx.Response, api_key: str) -> str:
    try:
        body = response.json()
    except ValueError:
        body = None

    error = body.get("error") if isinstance(body, dict) else None
    if not isinstance(error, dict):
        detail = _safe_error_detail(response.text, api_key)
        return f"HTTP {response.status_code}: {detail}" if detail else f"HTTP {response.status_code}"

    parts = []
    for field in ("code", "type"):
        value = error.get(field)
        if isinstance(value, (str, int)) and str(value).strip():
            parts.append(f"{field}={_safe_error_detail(value, api_key)}")
    message = error.get("message")
    if isinstance(message, str) and message.strip():
        parts.append(_safe_error_detail(message, api_key))
    detail = ": ".join(parts)
    return f"HTTP {response.status_code}: {detail}" if detail else f"HTTP {response.status_code}"


def _wait_for_request_slot(min_interval_s: float) -> None:
    global _next_request_at
    with _rate_limit_lock:
        now = time.monotonic()
        delay = max(0.0, _next_request_at - now)
        if delay:
            time.sleep(delay)
        _next_request_at = time.monotonic() + min_interval_s


def _retry_after_seconds(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


class LLMClient:
    def __init__(self, settings: Settings):
        self.s = settings

    def chat(self, messages: list[dict]) -> str:
        local = "localhost" in self.s.llm_base_url or "127.0.0.1" in self.s.llm_base_url
        if not self.s.llm_api_key and not local:
            raise ExternalServiceError("LLM_API_KEY is not set. Add it to your .env file.")
        headers = {"Authorization": f"Bearer {self.s.llm_api_key}"}
        payload = {"model": self.s.llm_model, "messages": messages,
                   "temperature": 0, "max_tokens": 600}
        url = self.s.llm_base_url.rstrip("/") + "/chat/completions"

        last_error = "unknown error"
        for attempt in range(self.s.llm_max_retries + 1):
            _wait_for_request_slot(self.s.llm_min_request_interval_s)
            retry_after = None
            try:
                r = httpx.post(url, json=payload, headers=headers, timeout=self.s.llm_timeout_s)
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"] or ""
                last_error = _http_error_detail(r, self.s.llm_api_key)
                if r.status_code not in (429, 500, 502, 503, 504):
                    break  # retrying will not help (e.g. 401 bad key)
                retry_after = _retry_after_seconds(r) if r.status_code == 429 else None
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                last_error = type(exc).__name__
            logger.warning("LLM call failed (%s), attempt %s", last_error, attempt + 1)
            if attempt < self.s.llm_max_retries:
                backoff = 2 ** attempt
                time.sleep(max(backoff, retry_after or 0.0))
        raise ExternalServiceError(f"The LLM service is unavailable ({last_error}).")
