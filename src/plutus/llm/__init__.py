"""Pluggable LLM provider layer for Plutus.

Public names:
    LLMProvider            abstract async completion interface
    OpenAIProvider         the production implementation, on the openai SDK
    LLMCompletion          normalized completion result
    LLMError               base class for all provider errors
    LLMNotConfiguredError  no API key or no SDK; typed and catchable
    LLMModelNotPricedError the configured model has no reviewed price
    LLMResponseError       the upstream API call failed or returned unusable
                           output; its subclasses name the category
                           (ERROR_CATEGORIES)
    RateLimitSnapshot      request and token budgets reported by the provider
"""

from .errors import (
    ERROR_CATEGORIES,
    LLMAuthenticationError,
    LLMContentFilteredError,
    LLMEmptyCompletionError,
    LLMError,
    LLMInvalidRequestError,
    LLMMalformedCompletionError,
    LLMModelNotFoundError,
    LLMModelNotPricedError,
    LLMNotConfiguredError,
    LLMProviderUnavailableError,
    LLMQuotaExhaustedError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    LLMTruncatedCompletionError,
)
from .headers import RateLimitSnapshot
from .provider import (
    DEFAULT_MODEL,
    LLMCompletion,
    LLMProvider,
    OpenAIProvider,
)

__all__ = [
    "DEFAULT_MODEL",
    "ERROR_CATEGORIES",
    "LLMAuthenticationError",
    "LLMCompletion",
    "LLMContentFilteredError",
    "LLMEmptyCompletionError",
    "LLMError",
    "LLMInvalidRequestError",
    "LLMMalformedCompletionError",
    "LLMModelNotFoundError",
    "LLMModelNotPricedError",
    "LLMNotConfiguredError",
    "LLMProvider",
    "LLMProviderUnavailableError",
    "LLMQuotaExhaustedError",
    "LLMRateLimitError",
    "LLMResponseError",
    "LLMTimeoutError",
    "LLMTruncatedCompletionError",
    "OpenAIProvider",
    "RateLimitSnapshot",
]
