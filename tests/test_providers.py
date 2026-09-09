from typing import Any

import pytest

from part_catalog_bench import providers
from part_catalog_bench.providers import (
    IncompleteResponseError,
    OpenAICompatibleProvider,
    build_completion_payload,
)


class _FakeResponse:
    def __init__(self, body: dict[str, Any]) -> None:
        self.body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.body


def _install_fake_client(
    monkeypatch: pytest.MonkeyPatch,
    body: dict[str, Any],
    captured: dict[str, Any],
) -> None:
    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            captured["timeout"] = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, url: str, *, headers: dict[str, str], json: dict[str, Any]) -> _FakeResponse:
            captured.update(url=url, headers=headers, payload=json)
            return _FakeResponse(body)

    monkeypatch.setattr(providers.httpx, "Client", FakeClient)


def test_compatible_provider_sends_reasoning_effort(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    _install_fake_client(
        monkeypatch,
        {
            "model": "openai/gpt-5.6-sol",
            "choices": [{"finish_reason": "stop", "message": {"content": '{"answer": 1}'}}],
            "usage": {"total_tokens": 10},
        },
        captured,
    )
    provider = OpenAICompatibleProvider(base_url="https://example.test/v1", api_key="secret")

    response = provider.complete(
        model="openai/gpt-5.6-sol",
        messages=[{"role": "user", "content": "question"}],
        temperature=0.0,
        max_tokens=8192,
        reasoning_effort="low",
        timeout=30.0,
    )

    assert response.text == '{"answer": 1}'
    assert captured["payload"]["max_tokens"] == 8192
    assert captured["payload"]["reasoning_effort"] == "low"


def test_request_preview_payload_matches_provider_payload_shape() -> None:
    messages = [{"role": "user", "content": "question"}]

    payload = build_completion_payload(
        model="openai/gpt-5.6-sol",
        messages=messages,
        temperature=0.0,
        max_tokens=8192,
        reasoning_effort=None,
    )

    assert payload == {
        "model": "openai/gpt-5.6-sol",
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": 8192,
        "stream": False,
    }


def test_openrouter_model_list_only_includes_image_capable_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            assert timeout == 30.0

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def get(self, url: str, *, headers: dict[str, str]) -> _FakeResponse:
            assert url == "https://openrouter.ai/api/v1/models/user"
            assert headers["Authorization"] == "Bearer secret"
            return _FakeResponse(
                {
                    "data": [
                        {
                            "id": "vision/model",
                            "name": "Vision Model",
                            "created": 100,
                            "architecture": {"input_modalities": ["text", "image"]},
                        },
                        {
                            "id": "new-vision/model",
                            "name": "New Vision Model",
                            "created": 200,
                            "architecture": {"input_modalities": ["text", "image"]},
                        },
                        {
                            "id": "text/model",
                            "name": "Text Model",
                            "architecture": {"input_modalities": ["text"]},
                        },
                    ]
                }
            )

    monkeypatch.setenv("OPENROUTER_API_KEY", "secret")
    monkeypatch.setattr(providers.httpx, "Client", FakeClient)

    assert providers.OpenRouterProvider().list_models() == [
        {
            "id": "new-vision/model",
            "name": "New Vision Model",
            "input_modalities": ["text", "image"],
            "context_length": None,
            "created": 200,
        },
        {
            "id": "vision/model",
            "name": "Vision Model",
            "input_modalities": ["text", "image"],
            "context_length": None,
            "created": 100,
        }
    ]


def test_compatible_provider_rejects_truncated_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    raw = {
        "model": "openai/gpt-5.6-sol",
        "choices": [
            {
                "finish_reason": "length",
                "native_finish_reason": "max_output_tokens",
                "message": {"content": '{"answer":', "reasoning": "still working"},
            }
        ],
        "usage": {"completion_tokens": 2048, "reasoning_tokens": 2048, "cost": 0.09},
    }
    _install_fake_client(monkeypatch, raw, captured)
    provider = OpenAICompatibleProvider(base_url="https://example.test/v1", api_key="secret")

    with pytest.raises(IncompleteResponseError, match="2,048-token output allowance") as exc_info:
        provider.complete(
            model="openai/gpt-5.6-sol",
            messages=[{"role": "user", "content": "question"}],
            temperature=0.0,
            max_tokens=2048,
            reasoning_effort="medium",
            timeout=30.0,
        )

    assert exc_info.value.raw == raw
    assert exc_info.value.usage["cost"] == 0.09
    assert "complete final answer" in str(exc_info.value)
    assert "lower reasoning effort" in str(exc_info.value)
