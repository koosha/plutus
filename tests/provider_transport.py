"""Drive the real model-provider SDK over an in-memory transport.

The SDK's own status mapping, retries, raw-response access and parsing run
unchanged; only the network is replaced. No request leaves the process.
"""

import importlib
import json
from typing import Any, Callable, Dict, List, Optional

import openai

from plutus.llm import OpenAIProvider

TEST_KEY = "synthetic-test-key-not-real"


def sdk_http():
    """The HTTP library the installed SDK is built on (it changed in 3.x)."""
    major = int(openai.__version__.split(".")[0])
    return importlib.import_module("httpx2" if major >= 3 else "httpx")


def chat_body(
    content: Optional[str] = "hello",
    *,
    finish_reason: Optional[str] = "stop",
    model: str = "gpt-5-mini-2025-08-07",
    prompt_tokens: int = 10,
    completion_tokens: int = 4,
    refusal: Optional[str] = None,
    choices: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    message: Dict[str, Any] = {"role": "assistant", "content": content}
    if refusal is not None:
        message["refusal"] = refusal
    return {
        "id": "chatcmpl-synthetic",
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": choices if choices is not None else [
            {"index": 0, "message": message, "finish_reason": finish_reason}
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def respond(status: int, body: Any = None, headers: Optional[Dict[str, str]] = None):
    """A handler that answers every request with one canned response."""
    http = sdk_http()

    def handler(request):
        return http.Response(status, json=body if body is not None else {}, headers=headers or {})

    return handler


def provider_over(handler: Callable, *, model: str = "gpt-5-mini") -> OpenAIProvider:
    """A real OpenAIProvider whose SDK client talks to `handler` instead of a socket."""
    http = sdk_http()
    provider = OpenAIProvider(api_key=TEST_KEY, model=model, max_retries=0)
    provider._client = openai.AsyncOpenAI(
        api_key=TEST_KEY,
        max_retries=0,
        http_client=http.AsyncClient(transport=http.MockTransport(handler)),
    )
    return provider


class RecordingHandler:
    """Records request bodies; answers with a canned response."""

    def __init__(self, status: int = 200, body: Any = None, headers: Optional[Dict[str, str]] = None):
        self.requests: List[Dict[str, Any]] = []
        self._respond = respond(status, body if body is not None else chat_body(), headers)

    def __call__(self, request):
        self.requests.append(json.loads(request.content.decode("utf-8")))
        return self._respond(request)
