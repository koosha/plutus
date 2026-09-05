"""Pluggable LLM provider layer for Plutus.

Public surface:
    LLMProvider           — abstract async completion interface
    OpenAIProvider        — the production implementation (openai SDK)
    LLMCompletion         — normalized completion result
    LLMError              — base class for all provider errors
    LLMNotConfiguredError — no API key / SDK missing (typed, catchable)
    LLMResponseError      — upstream API call failed or returned junk
"""

from .provider import (
    DEFAULT_MODEL,
    LLMCompletion,
    LLMError,
    LLMNotConfiguredError,
    LLMProvider,
    LLMResponseError,
    OpenAIProvider,
)

__all__ = [
    "DEFAULT_MODEL",
    "LLMCompletion",
    "LLMError",
    "LLMNotConfiguredError",
    "LLMProvider",
    "LLMResponseError",
    "OpenAIProvider",
]
