"""Rate-limit evidence read from provider response headers.

Values are parsed strictly. A header that is absent or does not parse is
unknown (None), never zero: "0 remaining" and "not reported" lead to
different decisions.
"""

import dataclasses
import math
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Mapping, Optional

# A provider asking callers to wait longer than a day is not describing a
# rate-limit window; such values are treated as unknown.
MAX_RETRY_AFTER_SECONDS = 86400.0

# ASCII digits only: \d and str.isdigit() also accept characters such as "²"
# that float() and int() then reject.
_DIGITS = re.compile(r"[0-9]+")
_NUMBER = r"[0-9]+(?:\.[0-9]+)?"
# Duration text in the provider's format: "6m0s", "1.5s", "20ms", "1h2m3s".
_DURATION = re.compile(
    rf"(?:(?P<h>{_NUMBER})h)?(?:(?P<m>{_NUMBER})m(?!s))?"
    rf"(?:(?P<s>{_NUMBER})s)?(?:(?P<ms>{_NUMBER})ms)?"
)
_BARE_SECONDS = re.compile(_NUMBER)
_UNIT_SECONDS = {"h": 3600.0, "m": 60.0, "s": 1.0, "ms": 0.001}

_COUNT_HEADERS = {
    "limit_requests": "x-ratelimit-limit-requests",
    "remaining_requests": "x-ratelimit-remaining-requests",
    "limit_tokens": "x-ratelimit-limit-tokens",
    "remaining_tokens": "x-ratelimit-remaining-tokens",
}
_RESET_HEADERS = {
    "reset_requests_seconds": "x-ratelimit-reset-requests",
    "reset_tokens_seconds": "x-ratelimit-reset-tokens",
}


@dataclasses.dataclass(frozen=True)
class RateLimitSnapshot:
    """The provider's request and token budgets as reported on one response."""

    limit_requests: Optional[int] = None
    remaining_requests: Optional[int] = None
    reset_requests_seconds: Optional[float] = None
    limit_tokens: Optional[int] = None
    remaining_tokens: Optional[int] = None
    reset_tokens_seconds: Optional[float] = None

    def as_dict(self) -> Dict[str, Optional[float]]:
        return dataclasses.asdict(self)


def _lowercased(headers: Any) -> Optional[Dict[str, str]]:
    items = getattr(headers, "items", None)
    if items is None:
        return None
    return {str(key).lower(): str(value) for key, value in items()}


def parse_duration(text: Any) -> Optional[float]:
    """Seconds in a duration such as "6m0s" or "20ms"; None if unparseable."""
    if not isinstance(text, str) or not text:
        return None
    if _BARE_SECONDS.fullmatch(text):
        return float(text)
    match = _DURATION.fullmatch(text)
    if match is None or not any(match.groupdict().values()):
        return None
    return sum(float(value) * _UNIT_SECONDS[unit]
               for unit, value in match.groupdict().items() if value is not None)


def _count(text: Optional[str]) -> Optional[int]:
    if text is None or not _DIGITS.fullmatch(text):
        return None
    return int(text)


def rate_limit_from_headers(headers: Any) -> Optional[RateLimitSnapshot]:
    """Read the request/token budget headers; None when none is reported."""
    values = _lowercased(headers)
    if not values:
        return None
    fields: Dict[str, Any] = {name: _count(values.get(header))
                              for name, header in _COUNT_HEADERS.items()}
    fields.update({name: parse_duration(values.get(header))
                   for name, header in _RESET_HEADERS.items()})
    if all(value is None for value in fields.values()):
        return None
    return RateLimitSnapshot(**fields)


def _bounded_wait(seconds: float) -> Optional[float]:
    if not math.isfinite(seconds) or seconds < 0 or seconds > MAX_RETRY_AFTER_SECONDS:
        return None
    return seconds


def retry_after_from_headers(
    headers: Any, *, now: Optional[datetime] = None
) -> Optional[float]:
    """Seconds to wait before retrying, from retry-after-ms or retry-after.

    Milliseconds win when both are present. retry-after may be a number of
    seconds or an HTTP date; a date in the past means "now" (0 seconds).
    """
    values: Optional[Mapping[str, str]] = _lowercased(headers)
    if not values:
        return None
    milliseconds = values.get("retry-after-ms")
    if milliseconds is not None:
        try:
            return _bounded_wait(float(milliseconds) / 1000)
        except ValueError:
            pass
    stated = values.get("retry-after")
    if stated is None:
        return None
    try:
        return _bounded_wait(float(stated))
    except ValueError:
        pass
    try:
        moment = parsedate_to_datetime(stated)
    except (TypeError, ValueError, IndexError):
        return None
    if moment is None:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    return _bounded_wait(max(0.0, (moment - current).total_seconds()))
