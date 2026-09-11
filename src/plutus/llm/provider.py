"""LLM provider abstraction + OpenAI implementation.

Design contract (kept deliberately small):

- `LLMProvider.complete(messages, ...)` is the ONLY seam the rest of Plutus
  talks to. Tests inject a fake provider; production uses `OpenAIProvider`.
- No API key ever appears in code. `OpenAIProvider` reads `OPENAI_API_KEY`
  from the environment (or an explicitly-injected key) and raises the typed
  `LLMNotConfiguredError` when absent so callers can degrade gracefully.
- Model comes from `PLUTUS_MODEL` (default: gpt-5-mini — OpenAI's current
  cost-effective tier at $0.25/M input, $2.00/M output tokens as of 2026-08).
- Temperature is only sent when explicitly configured: the gpt-5 reasoning
  family rejects non-default temperatures, so the safe default is "omit".
"""

import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-5-mini"
DEFAULT_MAX_OUTPUT_TOKENS = 1024
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RETRIES = 2

# USD per single token (input, output), keyed by model prefix. Longest prefix
# wins so dated snapshots ("gpt-5-mini-2026-01-01") price like their family.
# Source: OpenAI pricing, 2026-08 — gpt-5 $1.25/$10, gpt-5-mini $0.25/$2.00,
# gpt-5-nano $0.05/$0.40 per million tokens.
MODEL_COST_RATES: Dict[str, Tuple[float, float]] = {
    "gpt-5-nano": (0.05e-6, 0.40e-6),
    "gpt-5-mini": (0.25e-6, 2.00e-6),
    "gpt-5": (1.25e-6, 10.00e-6),
}
# Standard API text rates verified against the official model documentation.
# https://developers.openai.com/api/docs/models/gpt-5-mini
PRICING_VERSION = "openai-standard-2026-09-10"
_MODEL_SNAPSHOT = re.compile(r"^(gpt-5(?:-mini|-nano)?)(?:-\d{4}-\d{2}-\d{2})?$")


class LLMError(Exception):
    """Base class for every provider-layer error."""


class LLMNotConfiguredError(LLMError):
    """No API key (or no SDK) — the provider cannot make real calls."""


class LLMResponseError(LLMError):
    """The upstream API call failed or returned an unusable response."""


@dataclass(frozen=True)
class LLMCompletion:
    """Normalized completion result independent of the backing vendor."""

    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost: Optional[float] = None
    pricing_version: Optional[str] = None


def cost_for(model: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    """Versioned text pricing; unrecognized models have explicitly unknown cost."""
    match = _MODEL_SNAPSHOT.fullmatch(model)
    if not match:
        return None
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0
           for value in (input_tokens, output_tokens)):
        return None
    rates = MODEL_COST_RATES[match.group(1)]
    return input_tokens * rates[0] + output_tokens * rates[1]


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
            LLMNotConfiguredError: provider has no credentials.
            LLMResponseError: upstream call failed or response unusable.
        """


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

        try:
            response = await self._client.chat.completions.create(**request)
        except Exception as exc:  # SDK errors normalize to one typed error
            raise LLMResponseError("OpenAI completion failed") from exc

        try:
            text = response.choices[0].message.content or ""
        except (AttributeError, IndexError) as exc:
            raise LLMResponseError(
                "OpenAI response had no message content"
            ) from exc

        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", 0) or 0
        output_tokens = getattr(usage, "completion_tokens", 0) or 0

        return LLMCompletion(
            text=text,
            model=getattr(response, "model", self.model) or self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost_for(self.model, input_tokens, output_tokens) if usage is not None else None,
            pricing_version=PRICING_VERSION if usage is not None and cost_for(self.model, input_tokens, output_tokens) is not None else None,
        )
