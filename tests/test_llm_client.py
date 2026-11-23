from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import Mock

import httpx
import pytest

from app.config import Settings
from app.errors import ExternalServiceError
from app.services import llm as llm_module
from app.services.llm import LLMClient, _retry_after_seconds, _wait_for_request_slot


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(llm_module, "_wait_for_request_slot", Mock())
    return LLMClient(Settings(_env_file=None, llm_api_key="test-key", llm_max_retries=2))


def test_429_uses_retry_after_and_retries(client, monkeypatch):
    responses = [
        httpx.Response(429, headers={"Retry-After": "5"}),
        httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]}),
    ]
    sleeps = []
    monkeypatch.setattr(llm_module.httpx, "post", Mock(side_effect=responses))
    monkeypatch.setattr(llm_module.time, "sleep", sleeps.append)

    assert client.chat([{"role": "user", "content": "hello"}]) == "ok"
    assert sleeps == [5.0]


def test_429_uses_exponential_backoff_when_retry_after_is_missing(client, monkeypatch):
    responses = [
        httpx.Response(429),
        httpx.Response(429),
        httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]}),
    ]
    sleeps = []
    monkeypatch.setattr(llm_module.httpx, "post", Mock(side_effect=responses))
    monkeypatch.setattr(llm_module.time, "sleep", sleeps.append)

    assert client.chat([{"role": "user", "content": "hello"}]) == "ok"
    assert sleeps == [1, 2]


def test_429_exhaustion_raises_external_service_error(client, monkeypatch):
    monkeypatch.setattr(llm_module.httpx, "post", Mock(return_value=httpx.Response(429)))
    sleeps = []
    monkeypatch.setattr(llm_module.time, "sleep", sleeps.append)

    with pytest.raises(ExternalServiceError, match="HTTP 429"):
        client.chat([{"role": "user", "content": "hello"}])
    assert sleeps == [1, 2]


def test_retry_after_http_date_is_parsed():
    retry_at = datetime.now(timezone.utc) + timedelta(seconds=30)
    response = httpx.Response(429, headers={"Retry-After": format_datetime(retry_at)})

    delay = _retry_after_seconds(response)

    assert delay is not None
    assert 0 < delay <= 30


def test_request_slots_enforce_minimum_interval(monkeypatch):
    monkeypatch.setattr(llm_module, "_next_request_at", 0.0)
    monkeypatch.setattr(llm_module.time, "monotonic", lambda: 10.0)
    sleeps = []
    monkeypatch.setattr(llm_module.time, "sleep", sleeps.append)

    _wait_for_request_slot(1.0)
    _wait_for_request_slot(1.0)

    assert sleeps == [1.0]
