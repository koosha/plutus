"""Result metadata describing the synthesis call: model, usage and failures.

Successful and charged calls report `metadata["llm"]`; failures add a typed
category beside the host-facing `error_type`. Nothing here contains prompt
text, model output or financial values.
"""

from typing import Any, Dict, Optional

from ..llm import LLMCompletion, LLMError, RateLimitSnapshot


def _name(value: Any) -> Optional[str]:
    return value if isinstance(value, str) else None


def _rate_limit(value: Any) -> Optional[Dict[str, Any]]:
    return value.as_dict() if isinstance(value, RateLimitSnapshot) else None


def completion_metadata(completion: LLMCompletion, provider: Any) -> Dict[str, Any]:
    """Usage and model evidence for one completion.

    `model` is the model the provider served. `requested_model` comes from
    the completion when the provider records it, otherwise from the
    provider's configured `model`; it is None when neither is known. Host
    providers may return completion objects predating these fields, so the
    new ones are read defensively.
    """
    requested = getattr(completion, "requested_model", None)
    return {
        "model": completion.model,
        "requested_model": _name(requested) or _name(getattr(provider, "model", None)),
        "input_tokens": completion.input_tokens,
        "output_tokens": completion.output_tokens,
        "api_cost": completion.cost,
        "cost_status": "known" if completion.cost is not None else "unknown",
        "pricing_version": completion.pricing_version,
        "rate_limit": _rate_limit(getattr(completion, "rate_limit", None)),
    }


def failure_metadata(error: LLMError) -> Dict[str, Any]:
    """The stable category and retry hints of a provider-layer failure.

    `rate_limit` here describes a refused request; a charged completion's
    headers are reported under `metadata["llm"]` instead.
    """
    details: Dict[str, Any] = {"error_category": error.category, "retryable": error.retryable}
    retry_after = getattr(error, "retry_after", None)
    if retry_after is not None:
        details["retry_after_seconds"] = retry_after
    rate_limit = _rate_limit(getattr(error, "rate_limit", None))
    if rate_limit is not None:
        details["rate_limit"] = rate_limit
    return details
