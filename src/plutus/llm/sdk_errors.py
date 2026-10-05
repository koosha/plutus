"""Map model-provider SDK exceptions onto the typed error hierarchy.

Classification uses the HTTP status and the provider's error code, which are
stable across SDK major versions; exception classes are used only for the
two failures that have no status (timeouts and connection errors).
"""

from typing import Any, Type

from .errors import (
    LLMAuthenticationError,
    LLMInvalidRequestError,
    LLMModelNotFoundError,
    LLMProviderUnavailableError,
    LLMQuotaExhaustedError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)
from .headers import rate_limit_from_headers, retry_after_from_headers

# Provider error codes meaning the account cannot pay for more requests, as
# opposed to a temporary request or token rate limit.
QUOTA_CODES = frozenset({"insufficient_quota", "billing_hard_limit_reached", "billing_not_active"})


def _is_quota(*values: Any) -> bool:
    return any(isinstance(value, str) and value in QUOTA_CODES for value in values)


def _class_for_status(status: int, code: Any, kind: Any) -> Type[LLMResponseError]:
    if status in (401, 403):
        return LLMAuthenticationError
    if status == 404:
        return LLMModelNotFoundError
    if status == 408:
        return LLMTimeoutError
    if status == 429:
        return LLMQuotaExhaustedError if _is_quota(code, kind) else LLMRateLimitError
    if status == 409 or status >= 500:
        return LLMProviderUnavailableError
    if status in (400, 413, 422):
        return LLMInvalidRequestError
    return LLMResponseError


def typed_provider_error(exc: BaseException) -> LLMResponseError:
    """The typed error for an exception raised by the provider SDK call."""
    import openai

    if isinstance(exc, openai.APITimeoutError):
        return LLMTimeoutError("Provider request timed out")
    if isinstance(exc, openai.APIConnectionError):
        return LLMProviderUnavailableError("Provider could not be reached")
    status = getattr(exc, "status_code", None)
    if isinstance(exc, openai.APIStatusError) and isinstance(status, int):
        error_class = _class_for_status(status, getattr(exc, "code", None),
                                        getattr(exc, "type", None))
        headers = getattr(getattr(exc, "response", None), "headers", None)
        return error_class(
            f"Provider refused the request (category={error_class.category})",
            retry_after=retry_after_from_headers(headers),
            rate_limit=rate_limit_from_headers(headers),
            status_code=status,
        )
    return LLMResponseError("Provider request failed")
