"""The orchestrator reports a typed failure category and the model evidence.

`error_type` stays the coarse compatibility code ("llm_error" or
"llm_not_configured") that hosts already branch on; the category, retry
hints and charged usage are added beside it in the result metadata.
"""

import asyncio
import json

import pytest
from conftest import FakeProvider
from provider_transport import RecordingHandler, chat_body, provider_over, respond

from plutus import PlutusOrchestrator
from plutus.core.config import PlutusConfig, get_config, set_config
from plutus.llm import (
    LLMAuthenticationError,
    LLMCompletion,
    LLMContentFilteredError,
    LLMEmptyCompletionError,
    LLMInvalidRequestError,
    LLMModelNotFoundError,
    LLMProviderUnavailableError,
    LLMQuotaExhaustedError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    LLMTruncatedCompletionError,
)
from plutus.llm.headers import RateLimitSnapshot

CONTEXT = {"user_id": "person", "accounts": [], "goals": []}


async def ask(provider, **kwargs):
    return await PlutusOrchestrator(provider=provider).process_message(
        "How am I doing?", "person", user_context=dict(CONTEXT), **kwargs)


@pytest.fixture
def restore_config():
    original = get_config()
    yield
    set_config(original)


class TestFailureCategories:
    @pytest.mark.parametrize("error_class", [
        LLMAuthenticationError, LLMQuotaExhaustedError, LLMRateLimitError,
        LLMProviderUnavailableError, LLMTimeoutError, LLMModelNotFoundError,
        LLMInvalidRequestError, LLMEmptyCompletionError, LLMTruncatedCompletionError,
        LLMContentFilteredError,
    ])
    async def test_each_typed_error_keeps_llm_error_and_adds_its_category(self, error_class):
        result = await ask(FakeProvider(error=error_class("synthetic-secret-detail")))

        assert result["success"] is False
        assert result["error_type"] == "llm_error"
        metadata = result["metadata"]
        assert metadata["error_type"] == "llm_error"
        assert metadata["error_category"] == error_class.category
        assert metadata["retryable"] is error_class.retryable
        assert "retry_after_seconds" not in metadata
        assert "synthetic-secret-detail" not in json.dumps(result)

    async def test_an_untyped_provider_error_is_a_generic_provider_error(self):
        result = await ask(FakeProvider(error=LLMResponseError("upstream 500")))
        assert result["metadata"]["error_category"] == "provider_error"
        assert result["metadata"]["retryable"] is False

    async def test_retry_after_and_refusal_headers_reach_the_metadata(self):
        snapshot = RateLimitSnapshot(limit_requests=500, remaining_requests=0,
                                     reset_requests_seconds=2.5)
        error = LLMRateLimitError("limited", retry_after=2.5, rate_limit=snapshot)
        result = await ask(FakeProvider(error=error))

        assert result["metadata"]["retry_after_seconds"] == 2.5
        assert result["metadata"]["rate_limit"]["remaining_requests"] == 0
        assert result["metadata"]["rate_limit"]["limit_requests"] == 500
        # A refused request was never charged, so no usage is reported.
        assert "llm" not in result["metadata"]

    async def test_no_provider_reports_not_configured(self):
        result = await PlutusOrchestrator().process_message("hello", "person", user_context={})
        assert result["error_type"] == "llm_not_configured"
        assert result["metadata"]["error_category"] == "not_configured"
        assert result["metadata"]["retryable"] is False

    async def test_an_unpriced_model_is_refused_without_a_request(self):
        handler = RecordingHandler()
        provider = provider_over(handler, model="gpt-7-ultra")
        result = await ask(provider)
        await provider.aclose()

        assert handler.requests == []
        assert result["error_type"] == "llm_not_configured"
        assert result["metadata"]["error_category"] == "model_not_priced"

    async def test_a_missed_deadline_is_a_timeout(self, restore_config):
        set_config(PlutusConfig(request_timeout=0.05, max_retries=0))

        class Hanging(FakeProvider):
            async def complete(self, messages, **kwargs):
                await asyncio.sleep(5)

        result = await asyncio.wait_for(ask(Hanging()), timeout=2)
        assert result["error_type"] == "llm_error"
        assert result["metadata"]["error_category"] == "timeout"
        assert result["metadata"]["retryable"] is True

    async def test_a_blank_chat_answer_is_an_empty_completion(self):
        result = await ask(FakeProvider(raw_text="   "))
        assert result["metadata"]["error_category"] == "empty_completion"

    @pytest.mark.parametrize("text", ["{}", '{"insights": []}', "[]",
                                      '{"response":"text","insights":"bad"}'])
    async def test_a_broken_chat_contract_is_a_malformed_completion(self, text):
        result = await ask(FakeProvider(raw_text=text))
        assert result["error_type"] == "llm_error"
        assert result["metadata"]["error_category"] == "malformed_completion"


class TestChargedFailures:
    async def test_a_truncated_answer_still_settles_its_usage(self):
        provider = provider_over(respond(200, chat_body("cut-off-sentinel-91c", finish_reason="length")))
        result = await ask(provider)
        await provider.aclose()

        assert result["error_type"] == "llm_error"
        assert result["metadata"]["error_category"] == "truncated_completion"
        llm = result["metadata"]["llm"]
        # 10 x $0.25/M + 4 x $2.00/M
        assert llm["api_cost"] == pytest.approx(0.0000105)
        assert llm["cost_status"] == "known"
        assert llm["requested_model"] == "gpt-5-mini"
        assert llm["model"] == "gpt-5-mini-2025-08-07"
        assert "cut-off-sentinel-91c" not in json.dumps(result)

    async def test_an_empty_answer_still_settles_its_usage(self):
        provider = provider_over(respond(200, chat_body("")))
        result = await ask(provider)
        await provider.aclose()

        assert result["metadata"]["error_category"] == "empty_completion"
        assert result["metadata"]["llm"]["api_cost"] == pytest.approx(0.0000105)


class TestSuccessEvidence:
    async def test_requested_and_returned_models_and_headers_are_recorded(self):
        handler = RecordingHandler(
            body=chat_body(json.dumps({"response": "A grounded answer.", "insights": [],
                                       "recommendations": [], "confidence": 0.7}),
                           model="gpt-5-mini-2025-08-07"),
            headers={"x-ratelimit-remaining-requests": "41", "x-ratelimit-limit-requests": "50"},
        )
        provider = provider_over(handler)
        result = await ask(provider)
        await provider.aclose()

        assert result["success"] is True
        llm = result["metadata"]["llm"]
        assert llm["model"] == "gpt-5-mini-2025-08-07"
        assert llm["requested_model"] == "gpt-5-mini"
        assert llm["rate_limit"]["remaining_requests"] == 41
        assert llm["rate_limit"]["limit_requests"] == 50
        assert llm["pricing_version"].endswith("-standard-2026-10-04")
        assert "error_category" not in result["metadata"]

    async def test_a_provider_without_evidence_reports_unknowns(self, fake_provider):
        result = await ask(fake_provider)
        llm = result["metadata"]["llm"]
        assert llm["model"] == "fake-model"
        assert llm["requested_model"] is None
        assert llm["rate_limit"] is None

    async def test_the_provider_model_attribute_names_the_request(self):
        class Named(FakeProvider):
            model = "gpt-6-luna"

        result = await ask(Named())
        assert result["metadata"]["llm"]["requested_model"] == "gpt-6-luna"

    async def test_a_completion_names_its_own_request_first(self):
        class Reporting(FakeProvider):
            model = "configured-name"

            async def complete(self, messages, **kwargs):
                return LLMCompletion(
                    text=json.dumps({"response": "ok", "insights": [], "recommendations": []}),
                    model="served", requested_model="requested", cost=0.0)

        result = await ask(Reporting())
        assert result["metadata"]["llm"]["requested_model"] == "requested"
        assert result["metadata"]["llm"]["model"] == "served"

    async def test_a_completion_object_without_the_new_fields_still_works(self):
        """Host providers may return their own objects with only the 1.1.0 fields."""
        from types import SimpleNamespace

        class Legacy:
            model = "configured-name"

            async def complete(self, messages, *, system=None, max_output_tokens=None,
                               temperature=None):
                return SimpleNamespace(
                    text=json.dumps({"response": "ok", "insights": [], "recommendations": []}),
                    model="served", input_tokens=3, output_tokens=2, cost=0.0,
                    pricing_version="host-pricing")

        result = await ask(Legacy())
        assert result["success"] is True
        llm = result["metadata"]["llm"]
        assert (llm["model"], llm["requested_model"], llm["rate_limit"]) == (
            "served", "configured-name", None)

    async def test_brief_results_carry_the_same_evidence(self):
        handler = RecordingHandler(body=chat_body("[]"))
        provider = provider_over(handler, model="gpt-6-luna")
        result = await ask(provider, output_contract="brief")
        await provider.aclose()

        assert result["success"] is True
        assert result["metadata"]["llm"]["requested_model"] == "gpt-6-luna"
        assert result["metadata"]["llm"]["api_cost"] is not None
