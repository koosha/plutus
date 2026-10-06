"""Typed provider errors, unusable completions and rate-limit evidence.

Every case runs the real SDK client over an in-memory transport, so the
SDK's own status-to-exception mapping is what the provider classifies.
"""

import json
from datetime import datetime, timezone

import pytest

from plutus.llm import (
    ERROR_CATEGORIES,
    LLMAuthenticationError,
    LLMContentFilteredError,
    LLMEmptyCompletionError,
    LLMError,
    LLMInvalidRequestError,
    LLMModelNotFoundError,
    LLMProviderUnavailableError,
    LLMQuotaExhaustedError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    LLMTruncatedCompletionError,
)
from plutus.llm.headers import parse_duration, rate_limit_from_headers, retry_after_from_headers
from provider_transport import RecordingHandler, chat_body, provider_over, respond, sdk_http

MESSAGES = [{"role": "user", "content": "hello"}]


def error_body(code, error_type="invalid_request_error", message="synthetic provider message"):
    return {"error": {"message": message, "type": error_type, "param": None, "code": code}}


async def failure_from(handler):
    provider = provider_over(handler)
    try:
        with pytest.raises(LLMResponseError) as caught:
            await provider.complete(MESSAGES)
    finally:
        await provider.aclose()
    return caught.value


STATUS_CASES = [
    # (id, status, body, headers, expected class, category, retryable, retry_after)
    ("invalid_key", 401, error_body("invalid_api_key"), {}, LLMAuthenticationError,
     "authentication_failed", False, None),
    ("model_access_denied", 403, error_body("model_access_denied", "permission_error"), {},
     LLMAuthenticationError, "authentication_failed", False, None),
    ("model_not_found", 404, error_body("model_not_found"), {}, LLMModelNotFoundError,
     "model_not_found", False, None),
    ("quota", 429, error_body("insufficient_quota", "insufficient_quota"), {},
     LLMQuotaExhaustedError, "quota_exhausted", False, None),
    ("billing_inactive", 429, error_body("billing_not_active", "billing_not_active"), {},
     LLMQuotaExhaustedError, "quota_exhausted", False, None),
    ("rate_limited_ms", 429, error_body("rate_limit_exceeded", "requests"),
     {"retry-after-ms": "1500"}, LLMRateLimitError, "rate_limited", True, 1.5),
    ("rate_limited_seconds", 429, error_body("rate_limit_exceeded", "tokens"),
     {"retry-after": "7"}, LLMRateLimitError, "rate_limited", True, 7.0),
    ("rate_limited_no_header", 429, error_body("rate_limit_exceeded", "tokens"), {},
     LLMRateLimitError, "rate_limited", True, None),
    ("server_error", 500, error_body(None, "server_error"), {}, LLMProviderUnavailableError,
     "provider_unavailable", True, None),
    ("overloaded", 503, error_body(None, "server_error", "overloaded"), {},
     LLMProviderUnavailableError, "provider_unavailable", True, None),
    ("unsupported_parameter", 400, error_body("unsupported_parameter"), {},
     LLMInvalidRequestError, "invalid_request", False, None),
]


class TestStatusErrors:
    @pytest.mark.parametrize(
        "status,body,headers,expected,category,retryable,retry_after",
        [case[1:] for case in STATUS_CASES],
        ids=[case[0] for case in STATUS_CASES],
    )
    async def test_status_maps_to_a_typed_error(
        self, status, body, headers, expected, category, retryable, retry_after
    ):
        error = await failure_from(respond(status, body, headers))

        assert type(error) is expected
        assert isinstance(error, LLMResponseError) and isinstance(error, LLMError)
        assert error.category == category
        assert error.retryable is retryable
        assert error.retry_after == retry_after
        assert error.status_code == status
        assert error.completion is None

    async def test_provider_message_text_is_not_copied_into_the_error(self):
        error = await failure_from(respond(400, error_body("x", message="echo-of-synthetic-input")))
        assert "echo-of-synthetic-input" not in str(error)

    async def test_rate_limit_headers_on_a_refusal_are_kept(self):
        error = await failure_from(respond(429, error_body("rate_limit_exceeded", "tokens"), {
            "retry-after-ms": "250",
            "x-ratelimit-limit-tokens": "200000",
            "x-ratelimit-remaining-tokens": "0",
            "x-ratelimit-reset-tokens": "1m30s",
        }))
        assert error.rate_limit.limit_tokens == 200000
        assert error.rate_limit.remaining_tokens == 0
        assert error.rate_limit.reset_tokens_seconds == pytest.approx(90.0)
        assert error.rate_limit.remaining_requests is None


class TestTransportErrors:
    async def test_a_timeout_is_typed_and_retryable(self):
        http = sdk_http()

        def handler(request):
            raise http.ReadTimeout("synthetic timeout", request=request)

        error = await failure_from(handler)
        assert type(error) is LLMTimeoutError
        assert (error.category, error.retryable, error.status_code) == ("timeout", True, None)

    async def test_a_connection_failure_is_provider_unavailable(self):
        http = sdk_http()

        def handler(request):
            raise http.ConnectError("synthetic refusal", request=request)

        error = await failure_from(handler)
        assert type(error) is LLMProviderUnavailableError
        assert error.retryable is True


class TestUnusableCompletions:
    async def test_length_finish_is_truncation_even_with_partial_text(self):
        error = await failure_from(respond(200, chat_body("partial answ", finish_reason="length")))

        assert type(error) is LLMTruncatedCompletionError
        assert (error.category, error.retryable) == ("truncated_completion", False)
        # The paid usage survives for settlement; the partial text does not.
        # 10 x $0.25/M + 4 x $2.00/M = 0.0000025 + 0.000008
        assert error.completion.cost == pytest.approx(0.0000105)
        assert error.completion.input_tokens == 10
        assert error.completion.output_tokens == 4
        assert error.completion.text == ""
        assert error.completion.requested_model == "gpt-5-mini"
        assert error.completion.model == "gpt-5-mini-2025-08-07"

    async def test_length_finish_without_text_is_still_truncation(self):
        error = await failure_from(respond(200, chat_body(None, finish_reason="length")))
        assert type(error) is LLMTruncatedCompletionError

    @pytest.mark.parametrize("content", [None, "", "   \n\t"])
    async def test_empty_content_is_an_empty_completion(self, content):
        error = await failure_from(respond(200, chat_body(content)))

        assert type(error) is LLMEmptyCompletionError
        assert (error.category, error.retryable) == ("empty_completion", False)
        assert error.completion.cost == pytest.approx(0.0000105)

    async def test_no_choices_is_an_empty_completion(self):
        error = await failure_from(respond(200, chat_body(choices=[])))
        assert type(error) is LLMEmptyCompletionError

    async def test_a_filtered_finish_is_typed(self):
        error = await failure_from(respond(200, chat_body("cut", finish_reason="content_filter")))
        assert type(error) is LLMContentFilteredError
        assert (error.category, error.retryable) == ("content_filtered", False)

    async def test_a_refusal_without_content_is_typed_as_filtered(self):
        error = await failure_from(respond(200, chat_body(None, refusal="synthetic refusal")))
        assert type(error) is LLMContentFilteredError


class TestSuccessfulCompletionEvidence:
    async def test_requested_and_returned_models_are_both_recorded(self):
        handler = RecordingHandler(body=chat_body("fine", model="gpt-5-mini-2025-08-07"))
        provider = provider_over(handler)
        completion = await provider.complete(MESSAGES, system="policy")
        await provider.aclose()

        assert completion.text == "fine"
        assert completion.requested_model == "gpt-5-mini"
        assert completion.model == "gpt-5-mini-2025-08-07"
        assert completion.finish_reason == "stop"
        request = handler.requests[0]
        assert request["model"] == "gpt-5-mini"
        assert request["messages"][0] == {"role": "system", "content": "policy"}
        assert request["max_completion_tokens"] == 1024
        assert "temperature" not in request

    async def test_rate_limit_headers_are_read_from_the_same_response(self):
        handler = RecordingHandler(headers={
            "x-ratelimit-limit-requests": "5000",
            "x-ratelimit-remaining-requests": "4999",
            "x-ratelimit-reset-requests": "12ms",
            "x-ratelimit-limit-tokens": "4000000",
            "x-ratelimit-remaining-tokens": "3999000",
            "x-ratelimit-reset-tokens": "6m0s",
        })
        provider = provider_over(handler)
        completion = await provider.complete(MESSAGES)
        await provider.aclose()

        assert len(handler.requests) == 1  # no extra request for the headers
        assert completion.rate_limit.as_dict() == {
            "limit_requests": 5000,
            "remaining_requests": 4999,
            "reset_requests_seconds": pytest.approx(0.012),
            "limit_tokens": 4000000,
            "remaining_tokens": 3999000,
            "reset_tokens_seconds": pytest.approx(360.0),
        }

    async def test_absent_rate_limit_headers_leave_the_snapshot_unknown(self):
        provider = provider_over(RecordingHandler())
        completion = await provider.complete(MESSAGES)
        await provider.aclose()
        assert completion.rate_limit is None


class TestCategories:
    def test_categories_are_stable_strings(self):
        assert ERROR_CATEGORIES == frozenset({
            "provider_error", "not_configured", "model_not_priced",
            "authentication_failed", "quota_exhausted", "rate_limited",
            "provider_unavailable", "timeout", "model_not_found", "invalid_request",
            "empty_completion", "truncated_completion", "content_filtered",
            "malformed_completion",
        })

    def test_only_temporary_provider_conditions_are_retryable(self):
        retryable = {cls.category for cls in (LLMRateLimitError, LLMProviderUnavailableError,
                                              LLMTimeoutError)}
        assert retryable == {"rate_limited", "provider_unavailable", "timeout"}
        assert LLMResponseError.retryable is False
        assert LLMResponseError("legacy message").category == "provider_error"

    def test_legacy_construction_still_works(self):
        error = LLMResponseError("upstream 500")
        assert str(error) == "upstream 500"
        assert (error.retry_after, error.rate_limit, error.completion, error.status_code) == (
            None, None, None, None)

    def test_extra_positional_arguments_are_kept_as_in_1_1_0(self):
        """1.1.0 handed every positional argument to Exception."""
        error = LLMResponseError("upstream failed", 502)
        assert error.args == ("upstream failed", 502)
        assert str(error) == str(Exception("upstream failed", 502))
        assert error.retry_after is None

    def test_no_arguments_match_a_bare_exception(self):
        assert LLMResponseError().args == Exception().args == ()
        assert str(LLMResponseError()) == ""

    def test_a_subclass_takes_positional_arguments_beside_its_details(self):
        error = LLMRateLimitError("limited", "tokens", retry_after=2.0)
        assert error.args == ("limited", "tokens")
        assert (error.category, error.retry_after) == ("rate_limited", 2.0)

    def test_a_multi_argument_error_survives_pickling(self):
        import pickle

        copy = pickle.loads(pickle.dumps(LLMRateLimitError("limited", "tokens", retry_after=2.0)))
        assert type(copy) is LLMRateLimitError
        assert copy.args == ("limited", "tokens")
        assert copy.retry_after == 2.0


class TestHeaderParsing:
    @pytest.mark.parametrize("text,seconds", [
        ("1s", 1.0), ("6m0s", 360.0), ("20ms", 0.02), ("1h2m3.5s", 3723.5),
        ("5m", 300.0), ("0.5", 0.5), ("1.5s", 1.5),
    ])
    def test_durations(self, text, seconds):
        assert parse_duration(text) == pytest.approx(seconds)

    @pytest.mark.parametrize("text", ["", "soon", "-1s", "1x", "s", "nan", "inf", None, 5,
                                      "²s", "٣"])
    def test_unparseable_durations_are_unknown(self, text):
        assert parse_duration(text) is None

    def test_retry_after_prefers_milliseconds(self):
        assert retry_after_from_headers({"retry-after-ms": "250", "retry-after": "9"}) == 0.25

    @pytest.mark.parametrize("milliseconds", ["-1", "nan", "inf", "soon", "999999999999"])
    def test_an_unusable_millisecond_value_falls_back_to_seconds(self, milliseconds):
        headers = {"retry-after-ms": milliseconds, "retry-after": "4"}
        assert retry_after_from_headers(headers) == 4.0

    def test_retry_after_accepts_an_http_date(self):
        now = datetime(2026, 10, 21, 7, 27, 30, tzinfo=timezone.utc)
        headers = {"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}
        assert retry_after_from_headers(headers, now=now) == pytest.approx(30.0)

    def test_a_past_http_date_means_retry_now(self):
        now = datetime(2026, 10, 21, 8, 0, 0, tzinfo=timezone.utc)
        assert retry_after_from_headers({"retry-after": "Wed, 21 Oct 2026 07:28:00 GMT"}, now=now) == 0.0

    @pytest.mark.parametrize("headers", [
        {}, {"retry-after": "-3"}, {"retry-after": "nan"}, {"retry-after": "inf"},
        {"retry-after": "later"}, {"retry-after-ms": "-1"}, {"retry-after": "90000"},
    ])
    def test_invalid_retry_after_is_unknown(self, headers):
        assert retry_after_from_headers(headers) is None

    def test_unparseable_rate_limit_headers_leave_the_snapshot_unknown(self):
        assert rate_limit_from_headers({"x-ratelimit-remaining-requests": "lots"}) is None
        assert rate_limit_from_headers({"x-ratelimit-remaining-requests": "-4"}) is None
        assert rate_limit_from_headers({"x-ratelimit-remaining-requests": "²"}) is None
        assert rate_limit_from_headers(None) is None

    @pytest.mark.parametrize("digits", [19, 4301, 5000])
    def test_an_overlong_count_is_unknown_not_an_error(self, digits):
        """int() refuses digit strings longer than 4,300 characters."""
        headers = {"x-ratelimit-remaining-requests": "9" * digits}
        assert rate_limit_from_headers(headers) is None

    def test_the_longest_accepted_count_has_eighteen_digits(self):
        snapshot = rate_limit_from_headers({"x-ratelimit-limit-tokens": "9" * 18})
        assert snapshot.limit_tokens == 999_999_999_999_999_999

    @pytest.mark.parametrize("text", ["9" * 400, "9" * 400 + "s", "9" * 400 + "ms",
                                      "86400.5", "24h1s", "1441m"],
                             ids=["400-digit-bare", "400-digit-s", "400-digit-ms",
                                  "86400.5", "24h1s", "1441m"])
    def test_an_out_of_range_duration_is_unknown(self, text):
        """Above a day a reset is not a rate-limit window; inf is not JSON."""
        assert parse_duration(text) is None

    @pytest.mark.parametrize("text", ["86400", "24h", "1440m"])
    def test_a_reset_of_exactly_one_day_is_kept(self, text):
        assert parse_duration(text) == 86400.0

    def test_a_snapshot_is_always_standard_json(self):
        snapshot = rate_limit_from_headers({
            "x-ratelimit-limit-requests": "50",
            "x-ratelimit-reset-tokens": "9" * 400,
            "x-ratelimit-reset-requests": "9" * 400 + "s",
        })
        assert snapshot.as_dict()["limit_requests"] == 50
        assert snapshot.as_dict()["reset_tokens_seconds"] is None
        assert snapshot.as_dict()["reset_requests_seconds"] is None
        json.dumps(snapshot.as_dict(), allow_nan=False)

    @pytest.mark.parametrize("stated", [
        "Wed, 21 Oct 2026 99999999999999999999:28:00 GMT",
        "Wed, 99999999999999999999 Oct 2026 07:28:00 GMT",
        "Wed, 21 Oct 2026 07:28:999999999999999999999999999999 GMT",
    ], ids=["hour", "day", "second"])
    def test_an_http_date_with_an_overflowing_field_is_unknown(self, stated):
        """datetime() raises OverflowError, not ValueError, for these fields."""
        assert retry_after_from_headers({"retry-after": stated}) is None


RATE_LIMITED = error_body("rate_limit_exceeded", "tokens")


class TestMalformedHeadersThroughTheSdk:
    async def test_overlong_headers_never_break_a_completion(self):
        handler = RecordingHandler(headers={
            "x-ratelimit-limit-requests": "50",
            "x-ratelimit-remaining-requests": "9" * 5000,
            "x-ratelimit-reset-tokens": "9" * 400,
        })
        provider = provider_over(handler)
        completion = await provider.complete(MESSAGES)
        await provider.aclose()

        assert completion.text == "hello"
        assert completion.rate_limit.as_dict() == {
            "limit_requests": 50,
            "remaining_requests": None,
            "reset_requests_seconds": None,
            "limit_tokens": None,
            "remaining_tokens": None,
            "reset_tokens_seconds": None,
        }

    async def test_overlong_headers_on_a_refusal_keep_the_typed_error(self):
        error = await failure_from(respond(429, RATE_LIMITED, {
            "retry-after": "3",
            "x-ratelimit-remaining-tokens": "9" * 5000,
            "x-ratelimit-reset-tokens": "9" * 400,
        }))
        assert type(error) is LLMRateLimitError
        assert error.retry_after == 3.0
        assert error.rate_limit is None

    async def test_an_overflowing_retry_after_date_keeps_the_typed_error(self):
        error = await failure_from(respond(429, RATE_LIMITED, {
            "retry-after": "Wed, 21 Oct 2026 99999999999999999999:28:00 GMT",
            "x-ratelimit-remaining-tokens": "0",
        }))
        assert type(error) is LLMRateLimitError
        assert error.retry_after is None
        assert error.rate_limit.remaining_tokens == 0
