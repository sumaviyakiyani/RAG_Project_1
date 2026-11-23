"""Tests for the OpenAI-compatible LLM client."""
import httpx
import pytest

from app.config import Settings
from app.errors import ExternalServiceError
from app.services import llm as llm_module
from app.services.llm import LLMClient


API_KEY = "test-api-key-secret"
MESSAGES = [{"role": "user", "content": "hello"}]


def make_client() -> LLMClient:
    settings = Settings(
        _env_file=None,
        llm_api_key=API_KEY,
        llm_max_retries=0,
        llm_min_request_interval_s=0,
    )
    return LLMClient(settings)


@pytest.mark.parametrize(
    ("status_code", "code", "message"),
    [
        (404, "model_not_found", "The requested model was not found."),
        (401, "invalid_api_key", "The API key is invalid."),
        (429, "rate_limit_exceeded", "Please retry later."),
    ],
)
def test_http_errors_include_provider_code_and_message(
    monkeypatch, status_code, code, message
):
    response = httpx.Response(
        status_code,
        json={"error": {"message": message, "type": "invalid_request_error", "code": code}},
        request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
    )
    monkeypatch.setattr(llm_module, "_wait_for_request_slot", lambda _: None)
    monkeypatch.setattr(llm_module.httpx, "post", lambda *args, **kwargs: response)

    with pytest.raises(ExternalServiceError) as exc_info:
        make_client().chat(MESSAGES)

    detail = str(exc_info.value)
    assert f"HTTP {status_code}" in detail
    assert f"code={code}" in detail
    assert message in detail
    assert API_KEY not in detail


def test_http_error_redacts_api_key_from_provider_message(monkeypatch):
    response = httpx.Response(
        404,
        json={"error": {"message": f"Invalid credential: {API_KEY}", "code": "not_found"}},
        request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
    )
    monkeypatch.setattr(llm_module, "_wait_for_request_slot", lambda _: None)
    monkeypatch.setattr(llm_module.httpx, "post", lambda *args, **kwargs: response)

    with pytest.raises(ExternalServiceError) as exc_info:
        make_client().chat(MESSAGES)

    assert API_KEY not in str(exc_info.value)
    assert "[REDACTED]" in str(exc_info.value)


def test_success_posts_compatible_chat_completion_request(monkeypatch):
    response = httpx.Response(
        200,
        json={"choices": [{"message": {"content": "Hello."}}]},
        request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
    )
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return response

    monkeypatch.setattr(llm_module, "_wait_for_request_slot", lambda _: None)
    monkeypatch.setattr(llm_module.httpx, "post", fake_post)

    assert make_client().chat(MESSAGES) == "Hello."
    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["headers"]["Authorization"] == f"Bearer {API_KEY}"
    assert captured["json"]["model"] == "openai/gpt-oss-20b"
    assert captured["json"]["messages"] == MESSAGES
