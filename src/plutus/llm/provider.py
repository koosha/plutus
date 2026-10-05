"""LLM provider abstraction and the production implementation.

Design contract (kept deliberately small):

- `LLMProvider.complete(messages, ...)` is the ONLY seam the rest of Plutus
  talks to. Tests inject a fake provider; production uses `OpenAIProvider`.
- No API key ever appears in code. `OpenAIProvider` reads `OPENAI_API_KEY`
  from the environment (or an explicitly-injected key) and raises the typed
  `LLMNotConfiguredError` when absent so callers can degrade gracefully.
- Model comes from `PLUTUS_MODEL` (default: gpt-5-mini). Only models with a
  reviewed price (see `plutus.llm.pricing`) are dispatched; any other name is
  refused before a request is sent.
- Temperature is only sent when explicitly configured: the gpt-5 reasoning
  family rejects non-default temperatures, so the safe default is "omit".
- Every failure is a typed `LLMResponseError` subclass with a stable
  `category` and `retryable` flag (see `plutus.llm.errors`). A completion cut
  off at the output limit, filtered, or without text is a failure, never a
  partial success.
"""

import dataclasses
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .errors import (
    LLMContentFilteredError,
    LLMEmptyCompletionError,
    LLMError,
    LLMModelNotPricedError,
    LLMNotConfiguredError,
    LLMResponseError,
    LLMTruncatedCompletionError,
)
from .headers import RateLimitSnapshot, rate_limit_from_headers
from .pricing import MODEL_COST_RATES, PRICING_VERSION, cost_for, is_priced
from .sdk_errors import typed_provider_error

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-5-mini"
DEFAULT_MAX_OUTPUT_TOKENS = 1024
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RETRIES = 2

__all__ = [
    "DEFAULT_MAX_OUTPUT_TOKENS",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_MODEL",
    "DEFAULT_TIMEOUT_SECONDS",
    "LLMCompletion",
    "LLMError",
    "LLMNotConfiguredError",
    "LLMProvider",
    "LLMResponseError",
    "MODEL_COST_RATES",
    "OpenAIProvider",
    "PRICING_VERSION",
    "cost_for",
]


@dataclass(frozen=True)
class LLMCompletion:
    """Normalized completion result independent of the backing vendor.

    `model` is the model the provider reports having served; `requested_model`
    is the name that was asked for. They differ when an alias resolves to a
    dated snapshot, and evaluation evidence needs both.
    """

    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost: Optional[float] = None
    pricing_version: Optional[str] = None
    requested_model: Optional[str] = None
    finish_reason: Optional[str] = None
    rate_limit: Optional[RateLimitSnapshot] = None


class LLMProvider(ABC):
    """Async completion interface every backing implementation satisfies."""

    def maximum_cost(self, input_tokens: int, max_output_tokens: int,
                     max_attempts: int = 1) -> Optional[float]:
        """A provider must declare a supported upper bound before paid work."""
        return None

    async def aclose(self) -> None:
        """Release provider-owned clients; stateless implementations need no work."""

    @abstractmethod
    async def complete(
        self,
        messages: List[Dict[str, str]],
        *,
        system: Optional[str] = None,
        max_output_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMCompletion:
        """Run one chat completion.

        Args:
            messages: [{"role": "user"|"assistant", "content": str}, ...]
            system: optional system prompt, prepended by the implementation.
            max_output_tokens: response-token cap (implementation default
                applies when None).
            temperature: sampling temperature; None means "provider default"
                and MUST be omitted from the upstream request.

        Raises:
            LLMNotConfiguredError: provider has no credentials or no priced model.
            LLMResponseError: upstream call failed or response unusable; the
                subclass names the category (see plutus.llm.errors).
        """


def _text(message: Any) -> str:
    content = getattr(message, "content", None)
    return content if isinstance(content, str) else ""


def _optional_str(value: Any) -> Optional[str]:
    return value if isinstance(value, str) else None


def _require_usable(completion: LLMCompletion, *, has_choice: bool,
                    refusal: Optional[str]) -> LLMCompletion:
    """Unusable output raises a typed error that still carries paid usage."""
    usage_only = dataclasses.replace(completion, text="")
    if not has_choice:
        raise LLMEmptyCompletionError("Provider response had no choices", completion=usage_only)
    if completion.finish_reason == "length":
        raise LLMTruncatedCompletionError(
            "Provider output stopped at the output-token limit", completion=usage_only)
    if completion.finish_reason == "content_filter" or (
            refusal and refusal.strip() and not completion.text.strip()):
        raise LLMContentFilteredError("Provider filtered or refused the output",
                                      completion=usage_only)
    if not completion.text.strip():
        raise LLMEmptyCompletionError("Provider returned no text", completion=usage_only)
    return completion


class OpenAIProvider(LLMProvider):
    """LLMProvider backed by the official `openai` async SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        from ..core.config import validate_limit
        validate_limit("request_timeout", timeout)
        validate_limit("max_retries", max_retries)
        key = api_key or os.getenv("OPENAI_API_KEY") or ""
        if not key:
            raise LLMNotConfiguredError(
                "OPENAI_API_KEY is not set — OpenAIProvider cannot run. "
                "Export the key or inject a provider explicitly."
            )
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise LLMNotConfiguredError(
                "The `openai` package is not installed (pip install openai)."
            ) from exc

        self.model = model or os.getenv("PLUTUS_MODEL", DEFAULT_MODEL)
        self._client = AsyncOpenAI(
            api_key=key, timeout=timeout, max_retries=max_retries
        )

    def maximum_cost(self, input_tokens, max_output_tokens, max_attempts=1):
        estimate = cost_for(self.model, input_tokens, max_output_tokens)
        return estimate * max_attempts if estimate is not None else None

    async def aclose(self):
        await self._client.close()

    @staticmethod
    def is_configured() -> bool:
        """True when a real call could be attempted (key present, SDK importable)."""
        if not os.getenv("OPENAI_API_KEY"):
            return False
        try:
            import openai  # noqa: F401
        except ImportError:
            return False
        return True

    async def complete(
        self,
        messages: List[Dict[str, str]],
        *,
        system: Optional[str] = None,
        max_output_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMCompletion:
        from ..core.config import validate_limit
        validate_limit("max_output_tokens", max_output_tokens if max_output_tokens is not None else DEFAULT_MAX_OUTPUT_TOKENS)
        validate_limit("llm_temperature", temperature)
        if not is_priced(self.model):
            # Paid work needs a reviewed price. The name is not repeated in
            # the message; the host already knows what it configured.
            raise LLMModelNotPricedError(
                "The configured model has no reviewed price; no request was sent")
        payload: List[Dict[str, str]] = []
        if system:
            payload.append({"role": "system", "content": system})
        payload.extend(messages)

        request: Dict[str, Any] = {
            "model": self.model,
            "messages": payload,
            "max_completion_tokens": max_output_tokens
            or DEFAULT_MAX_OUTPUT_TOKENS,
        }
        if temperature is not None:
            request["temperature"] = temperature

        # The raw response exposes the rate-limit headers of this same call,
        # so no second request is needed to observe them.
        try:
            raw = await self._client.chat.completions.with_raw_response.create(**request)
            response = raw.parse()
        except Exception as exc:  # SDK errors normalize to typed errors
            raise typed_provider_error(exc) from exc

        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", 0) or 0
        output_tokens = getattr(usage, "completion_tokens", 0) or 0
        cost = cost_for(self.model, input_tokens, output_tokens) if usage is not None else None
        try:
            choice = response.choices[0]
        except (AttributeError, IndexError, TypeError):
            choice = None
        message = getattr(choice, "message", None)

        completion = LLMCompletion(
            text=_text(message),
            model=getattr(response, "model", self.model) or self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            pricing_version=PRICING_VERSION if cost is not None else None,
            requested_model=self.model,
            finish_reason=_optional_str(getattr(choice, "finish_reason", None)),
            rate_limit=rate_limit_from_headers(getattr(raw, "headers", None)),
        )
        return _require_usable(completion, has_choice=choice is not None,
                               refusal=_optional_str(getattr(message, "refusal", None)))
