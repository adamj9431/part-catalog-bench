from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx

REASONING_EFFORTS = frozenset({"none", "low", "medium", "high", "xhigh", "max"})


@dataclass
class ProviderResponse:
    text: str
    raw: dict[str, Any]
    response_model: str | None
    usage: dict[str, Any]


class IncompleteResponseError(RuntimeError):
    """A successful provider call that ended without a complete final answer."""

    def __init__(self, message: str, raw: dict[str, Any]) -> None:
        super().__init__(message)
        self.raw = raw
        self.response_model = raw.get("model")
        self.usage = raw.get("usage") or {}


def incomplete_response_message(raw: dict[str, Any], max_tokens: int | None = None) -> str | None:
    """Explain empty or truncated Chat Completions responses."""
    try:
        choice = raw["choices"][0]
        message = choice["message"]
    except (KeyError, IndexError, TypeError):
        return None
    finish_reason = choice.get("finish_reason")
    native_finish_reason = choice.get("native_finish_reason")
    reasons = ", ".join(
        item
        for item in (
            f"finish_reason={finish_reason}" if finish_reason else None,
            (f"native_finish_reason={native_finish_reason}" if native_finish_reason else None),
        )
        if item
    )
    if finish_reason == "length" or native_finish_reason == "max_output_tokens":
        budget = f" after using the {max_tokens:,}-token output allowance" if max_tokens else ""
        detail = f" ({reasons})" if reasons else ""
        return (
            f"Output limit reached{budget} before the model produced a complete final answer"
            f"{detail}. Increase max output tokens or lower reasoning effort."
        )
    content = message.get("content")
    if isinstance(content, list):
        content = "".join(
            str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in content
        )
    if content is not None and str(content).strip():
        return None
    if message.get("refusal"):
        return None
    detail = f" ({reasons})" if reasons else ""
    return f"Provider returned no final answer content{detail}."


class Provider(Protocol):
    name: str

    def list_models(self) -> list[dict[str, Any]]: ...

    def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float,
        max_tokens: int,
        reasoning_effort: str | None,
        timeout: float,
    ) -> ProviderResponse: ...


class OpenAICompatibleProvider:
    name = "compatible"

    def __init__(self, *, base_url: str, api_key: str, headers: dict[str, str] | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = headers or {}

    def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float,
        max_tokens: int,
        reasoning_effort: str | None,
        timeout: float,
    ) -> ProviderResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.headers,
        }
        payload = build_completion_payload(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
        )
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{self.base_url}/chat/completions", headers=headers, json=payload
            )
            response.raise_for_status()
            raw = response.json()
        try:
            message = raw["choices"][0]["message"]
            text = message["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"unexpected provider response: {raw}") from exc
        if text is None and message.get("refusal"):
            text = message["refusal"]
        if isinstance(text, list):
            text = "".join(
                str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in text
            )
        if error := incomplete_response_message(raw, max_tokens):
            raise IncompleteResponseError(error, raw)
        return ProviderResponse(
            text=str(text),
            raw=raw,
            response_model=raw.get("model"),
            usage=raw.get("usage") or {},
        )

    def list_models(self) -> list[dict[str, Any]]:
        return self._list_models_from("/models")

    def _list_models_from(
        self, path: str, *, require_image_input: bool = False
    ) -> list[dict[str, Any]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.headers,
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{self.base_url}{path}", headers=headers)
            response.raise_for_status()
            raw = response.json()
        data = raw.get("data") if isinstance(raw, dict) else None
        if not isinstance(data, list):
            raise ValueError("provider model-list response did not contain a data array")
        models = []
        for item in data:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            architecture = item.get("architecture") or {}
            modalities = architecture.get("input_modalities") or []
            if require_image_input and "image" not in modalities:
                continue
            models.append(
                {
                    "id": str(item["id"]),
                    "name": str(item.get("name") or item["id"]),
                    "input_modalities": modalities,
                    "context_length": item.get("context_length"),
                    "created": item.get("created")
                    or item.get("creation_timestamp")
                    or item.get("created_at"),
                }
            )

        def sort_key(item: dict[str, Any]) -> tuple[bool, float, str, str]:
            try:
                created = float(item["created"])
            except (TypeError, ValueError):
                created = 0
            return (
                item["created"] is None,
                -created,
                item["name"].lower(),
                item["id"],
            )

        return sorted(models, key=sort_key)


def build_completion_payload(
    *,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float,
    max_tokens: int,
    reasoning_effort: str | None,
) -> dict[str, Any]:
    """Build the exact JSON body used by OpenAI-compatible providers."""
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if reasoning_effort is not None:
        payload["reasoning_effort"] = reasoning_effort
    return payload


class OpenRouterProvider(OpenAICompatibleProvider):
    name = "openrouter"

    def __init__(self) -> None:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
        headers = {}
        if site_url := os.environ.get("OPENROUTER_SITE_URL"):
            headers["HTTP-Referer"] = site_url
        if app_name := os.environ.get("OPENROUTER_APP_NAME"):
            headers["X-Title"] = app_name
        super().__init__(
            base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key=api_key,
            headers=headers,
        )

    def list_models(self) -> list[dict[str, Any]]:
        return self._list_models_from("/models/user", require_image_input=True)


class DatabricksProvider(OpenAICompatibleProvider):
    name = "databricks"

    def __init__(self) -> None:
        api_key = os.environ.get("DATABRICKS_TOKEN")
        base_url = os.environ.get("DATABRICKS_BASE_URL")
        if not api_key:
            raise ValueError("DATABRICKS_TOKEN is required")
        if not base_url:
            raise ValueError("DATABRICKS_BASE_URL is required")
        super().__init__(base_url=base_url, api_key=api_key)


def create_provider(name: str) -> Provider:
    normalized = name.strip().lower()
    if normalized == "openrouter":
        return OpenRouterProvider()
    if normalized == "databricks":
        return DatabricksProvider()
    raise ValueError(f"unsupported provider {name!r}; choose openrouter or databricks")


def image_content(path: Path, mime_type: str) -> dict[str, Any]:
    if not mime_type.startswith("image/"):
        raise ValueError(
            f"primary image-native mode accepts image assets only; got {mime_type} for {path}"
        )
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
    }
