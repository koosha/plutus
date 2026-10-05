"""Typed provider-layer errors with stable categories.

Every error exposes two class-level facts a host can act on:

- ``category``: a stable string for metrics, user-facing states and runbooks.
- ``retryable``: True only for temporary provider conditions (rate limiting,
  unavailability, timeouts), where an identical request may succeed later
  without operator or configuration changes. Output failures (empty,
  truncated, filtered, malformed) are not retryable: an identical request is
  likely to fail the same way and is charged again.

Messages are fixed text. Provider error bodies can echo request details, so
they are never copied into these errors; the original SDK exception stays
available as ``__cause__`` for local debugging only.
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .headers import RateLimitSnapshot
    from .provider import LLMCompletion


class LLMError(Exception):
    """Base class for every provider-layer error."""

    category = "provider_error"
    retryable = False


class LLMNotConfiguredError(LLMError):
    """No API key (or no SDK) — the provider cannot make real calls."""

    category = "not_configured"


class LLMModelNotPricedError(LLMNotConfiguredError):
    """The configured model has no reviewed price, so no request is sent."""

    category = "model_not_priced"


class LLMResponseError(LLMError):
    """The upstream API call failed or returned an unusable response.

    Attributes:
        retry_after: seconds the provider asked callers to wait, when stated.
        rate_limit: the provider's rate-limit headers on the failed response.
        completion: usage of a charged but unusable completion (text removed),
            so the host can settle what was actually spent.
        status_code: the HTTP status of a refused request, when there was one.
    """

    def __init__(
        self,
        message: str = "",
        *,
        retry_after: Optional[float] = None,
        rate_limit: "Optional[RateLimitSnapshot]" = None,
        completion: "Optional[LLMCompletion]" = None,
        status_code: Optional[int] = None,
    ):
        super().__init__(message)
        self.retry_after = retry_after
        self.rate_limit = rate_limit
        self.completion = completion
        self.status_code = status_code


class LLMAuthenticationError(LLMResponseError):
    """Invalid or revoked key, or the key may not use the requested model."""

    category = "authentication_failed"


class LLMQuotaExhaustedError(LLMResponseError):
    """The account's quota or billing does not allow more requests."""

    category = "quota_exhausted"


class LLMRateLimitError(LLMResponseError):
    """Too many requests or tokens right now; ``retry_after`` says when."""

    category = "rate_limited"
    retryable = True


class LLMProviderUnavailableError(LLMResponseError):
    """Provider-side failure, overload, or no connection could be made."""

    category = "provider_unavailable"
    retryable = True


class LLMTimeoutError(LLMResponseError):
    """No complete response arrived within the configured time."""

    category = "timeout"
    retryable = True


class LLMModelNotFoundError(LLMResponseError):
    """The requested model does not exist or is not served on this endpoint."""

    category = "model_not_found"


class LLMInvalidRequestError(LLMResponseError):
    """The provider rejected the request itself (for example a parameter)."""

    category = "invalid_request"


class LLMEmptyCompletionError(LLMResponseError):
    """The provider returned no usable text."""

    category = "empty_completion"


class LLMTruncatedCompletionError(LLMResponseError):
    """The output budget ran out before the answer finished."""

    category = "truncated_completion"


class LLMContentFilteredError(LLMResponseError):
    """The provider filtered the output or the model refused to answer."""

    category = "content_filtered"


class LLMMalformedCompletionError(LLMResponseError):
    """The text arrived but does not satisfy the requested output contract."""

    category = "malformed_completion"


_ALL_ERRORS = (
    LLMError, LLMNotConfiguredError, LLMModelNotPricedError, LLMResponseError,
    LLMAuthenticationError, LLMQuotaExhaustedError, LLMRateLimitError,
    LLMProviderUnavailableError, LLMTimeoutError, LLMModelNotFoundError,
    LLMInvalidRequestError, LLMEmptyCompletionError, LLMTruncatedCompletionError,
    LLMContentFilteredError, LLMMalformedCompletionError,
)

ERROR_CATEGORIES = frozenset(error.category for error in _ALL_ERRORS)
