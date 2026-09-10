"""LLM provider layer: typed configuration errors, env resolution, pricing,
and the SDK-call plumbing (mocked — no network)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from plutus.llm import (
    LLMCompletion,
    LLMError,
    LLMNotConfiguredError,
    LLMResponseError,
    OpenAIProvider,
)
from plutus.llm.provider import DEFAULT_MODEL, cost_for


class TestNotConfigured:
    def test_missing_key_raises_typed_error(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(LLMNotConfiguredError):
            OpenAIProvider()

    def test_not_configured_is_an_llm_error(self):
        assert issubclass(LLMNotConfiguredError, LLMError)
        assert issubclass(LLMResponseError, LLMError)

    def test_is_configured_false_without_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert OpenAIProvider.is_configured() is False

    def test_is_configured_true_with_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
        assert OpenAIProvider.is_configured() is True


class TestModelResolution:
    def test_model_default(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
        monkeypatch.delenv("PLUTUS_MODEL", raising=False)
        provider = OpenAIProvider()
        assert provider.model == DEFAULT_MODEL

    def test_model_env_override(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
        monkeypatch.setenv("PLUTUS_MODEL", "custom-model")
        provider = OpenAIProvider()
        assert provider.model == "custom-model"

    def test_model_arg_beats_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
        monkeypatch.setenv("PLUTUS_MODEL", "env-model")
        provider = OpenAIProvider(model="arg-model")
        assert provider.model == "arg-model"


class TestCostTable:
    def test_known_models_price_exactly(self):
        assert cost_for("gpt-5-mini", 1_000_000, 1_000_000) == pytest.approx(2.25)
        assert cost_for("gpt-5", 1_000_000, 0) == pytest.approx(1.25)
        assert cost_for("gpt-5-nano", 0, 1_000_000) == pytest.approx(0.40)

    def test_dated_snapshot_prices_like_family(self):
        assert cost_for("gpt-5-mini-2026-01-01", 1_000_000, 0) == pytest.approx(0.25)

    def test_unknown_model_has_explicitly_unknown_cost(self):
        assert cost_for("some-future-model", 1_000_000, 1_000_000) is None
        assert cost_for("gpt-5-premium", 1_000_000, 1_000_000) is None


def _mock_sdk_response(content="hello", prompt_tokens=10, completion_tokens=4):
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    response.model = "fake-served-model"
    return response


class TestCompleteMockedSDK:
    @pytest.fixture
    def provider(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
        return OpenAIProvider()

    async def test_complete_normalizes_response(self, provider):
        mocked = AsyncMock(return_value=_mock_sdk_response())
        with patch.object(
            provider._client.chat.completions, "create", mocked
        ):
            completion = await provider.complete(
                [{"role": "user", "content": "hi"}], system="sys"
            )
        assert isinstance(completion, LLMCompletion)
        assert completion.text == "hello"
        assert completion.input_tokens == 10
        assert completion.output_tokens == 4
        assert completion.cost == pytest.approx(cost_for(provider.model, 10, 4))

        kwargs = mocked.call_args.kwargs
        assert kwargs["messages"][0] == {"role": "system", "content": "sys"}
        assert kwargs["messages"][1] == {"role": "user", "content": "hi"}
        assert "max_completion_tokens" in kwargs
        # temperature omitted unless explicitly configured
        assert "temperature" not in kwargs

    async def test_temperature_passed_only_when_set(self, provider):
        mocked = AsyncMock(return_value=_mock_sdk_response())
        with patch.object(
            provider._client.chat.completions, "create", mocked
        ):
            await provider.complete(
                [{"role": "user", "content": "hi"}], temperature=0.3
            )
        assert mocked.call_args.kwargs["temperature"] == 0.3

    async def test_sdk_failure_maps_to_typed_error(self, provider):
        mocked = AsyncMock(side_effect=RuntimeError("boom"))
        with patch.object(
            provider._client.chat.completions, "create", mocked
        ):
            with pytest.raises(LLMResponseError):
                await provider.complete([{"role": "user", "content": "hi"}])

    async def test_empty_choices_maps_to_typed_error(self, provider):
        response = MagicMock()
        response.choices = []
        mocked = AsyncMock(return_value=response)
        with patch.object(
            provider._client.chat.completions, "create", mocked
        ):
            with pytest.raises(LLMResponseError):
                await provider.complete([{"role": "user", "content": "hi"}])
