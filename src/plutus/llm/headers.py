"""Rate-limit evidence read from provider response headers.

Values are parsed strictly. A header that is absent or does not parse is
unknown (None), never zero: "0 remaining" and "not reported" lead to
different decisions. A malformed header never raises: every parsed value is
a bounded int or a finite float, so it serializes as standard JSON.
"""

import dataclasses
import math
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Mapping, Optional

# A provider asking callers to wait longer than a day, or reporting a reset
# more than a day away, is not describing a rate-limit window; such values
# are treated as unknown.
MAX_RETRY_AFTER_SECONDS = 86400.0

# The longest request or token count read, in digits. No rate-limit budget
# comes near it, an 18-digit count fits in 64 bits, and int() refuses digit
# strings longer than 4,300 characters.
MAX_COUNT_DIGITS = 18

# ASCII digits only: \d and str.isdigit() also accept characters such as "²"
# that float() and int() then reject.
_COUNT = re.compile(r"[0-9]{1,%d}" % MAX_COUNT_DIGITS)
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


def _bounded_seconds(seconds: float) -> Optional[float]:
    """A finite wait of at most a day, or None (float() of a long digit string is inf)."""
    if not math.isfinite(seconds) or seconds < 0 or seconds > MAX_RETRY_AFTER_SECONDS:
        return None
    return seconds


def parse_duration(text: Any) -> Optional[float]:
    """Seconds in a duration such as "6m0s" or "20ms".

    None when the text does not parse or is not a rate-limit window (not
    finite, or more than a day).
    """
    if not isinstance(text, str) or not text:
        return None
    if _BARE_SECONDS.fullmatch(text):
        return _bounded_seconds(float(text))
    match = _DURATION.fullmatch(text)
    if match is None or not any(match.groupdict().values()):
        return None
    return _bounded_seconds(sum(float(value) * _UNIT_SECONDS[unit]
                                for unit, value in match.groupdict().items()
                                if value is not None))


def _count(text: Optional[str]) -> Optional[int]:
    if text is None or not _COUNT.fullmatch(text):
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


def _numeric_wait(text: Optional[str], scale: float) -> Optional[float]:
    if text is None:
        return None
    try:
        return _bounded_seconds(float(text) * scale)
    except ValueError:
        return None


def retry_after_from_headers(
    headers: Any, *, now: Optional[datetime] = None
) -> Optional[float]:
    """Seconds to wait before retrying, from retry-after-ms or retry-after.

    The first usable value wins: milliseconds, then seconds, then an HTTP
    date in retry-after, where a date in the past means "now" (0 seconds).
    """
    values: Optional[Mapping[str, str]] = _lowercased(headers)
    if not values:
        return None
    for name, scale in (("retry-after-ms", 0.001), ("retry-after", 1.0)):
        wait = _numeric_wait(values.get(name), scale)
        if wait is not None:
            return wait
    stated = values.get("retry-after")
    if stated is None:
        return None
    try:
        moment = parsedate_to_datetime(stated)
    except (TypeError, ValueError, IndexError, OverflowError):
        # datetime() raises OverflowError for a field too large for a C long.
        return None
    if moment is None:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    return _bounded_seconds(max(0.0, (moment - current).total_seconds()))
