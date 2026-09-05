"""Real orchestration path with a mocked provider — no network anywhere.

Covers: structured output from mocked completions, the guardrail system
prompt, typed llm_not_configured / llm_error paths, and non-contract
completion degradation.
"""

import json

from conftest import FakeProvider

from plutus import PlutusOrchestrator
from plutus.agents.advanced_orchestrator import ADVISOR_SYSTEM_PROMPT


class TestNotConfiguredPath:
    async def test_no_provider_returns_typed_error(self):
        orchestrator = PlutusOrchestrator()  # env has no key (conftest)
        result = await orchestrator.process_message("Am I on track?", "user-1")

        assert result["success"] is False
        assert result["error_type"] == "llm_not_configured"
        assert result["agent_results"] == []
        # still a user-presentable message
        assert isinstance(result["response"], str) and result["response"]


class TestRealPathWithMockedProvider:
    async def test_structured_output_from_mocked_completion(self, fake_provider):
        orchestrator = PlutusOrchestrator(provider=fake_provider)
        result = await orchestrator.process_message(
            "How is my financial health?", "user-1"
        )

        assert result["success"] is True
        assert result["response"] == "A grounded educational answer."
        assert result["insights"] == ["insight-1"]
        assert result["recommendations"] == ["recommendation-1"]
        assert "llm_synthesis" in result["metadata"]["agents_used"]
        llm_meta = result["metadata"]["llm"]
        assert llm_meta["model"] == "fake-model"
        assert llm_meta["api_cost"] == fake_provider._cost
        assert llm_meta["parsed_contract"] is True
        assert result["metadata"]["confidence"] == 0.8

        synthesis = result["agent_results"][-1]
        assert synthesis["agent_name"] == "llm_synthesis"
        assert synthesis["success"] is True
        assert synthesis["tokens_used"] == 180

    async def test_exactly_one_completion_per_message(self, fake_provider):
        orchestrator = PlutusOrchestrator(provider=fake_provider)
        await orchestrator.process_message(
            "Should I invest more and how risky are my goals?", "user-1"
        )
        assert len(fake_provider.calls) == 1

    async def test_guardrail_system_prompt_is_sent(self, fake_provider):
        orchestrator = PlutusOrchestrator(provider=fake_provider)
        await orchestrator.process_message("What should I do?", "user-1")

        call = fake_provider.calls[0]
        assert call["system"] == ADVISOR_SYSTEM_PROMPT
        assert "individualized investment advice" in call["system"]
        assert "execute trades" in call["system"]

    async def test_prompt_carries_user_message_and_findings(self, fake_provider):
        orchestrator = PlutusOrchestrator(provider=fake_provider)
        await orchestrator.process_message("How is my financial health?", "user-9")

        payload = json.loads(fake_provider.calls[0]["messages"][0]["content"])
        assert payload["user_message"] == "How is my financial health?"
        assert "financial_context" in payload
        assert isinstance(payload["specialist_findings"], list)

    async def test_non_contract_completion_degrades_to_verbatim_text(self):
        provider = FakeProvider(raw_text="Plain prose, not JSON at all.")
        orchestrator = PlutusOrchestrator(provider=provider)
        result = await orchestrator.process_message("hello", "user-1")

        assert result["success"] is True
        assert result["response"] == "Plain prose, not JSON at all."
        assert result["metadata"]["llm"]["parsed_contract"] is False

    async def test_confidence_is_clamped(self):
        provider = FakeProvider(
            payload={"response": "r", "confidence": 7.5}
        )
        orchestrator = PlutusOrchestrator(provider=provider)
        result = await orchestrator.process_message("hello", "user-1")
        assert result["metadata"]["confidence"] == 1.0


class TestProviderFailurePath:
    async def test_provider_error_maps_to_llm_error(self, failing_provider):
        orchestrator = PlutusOrchestrator(provider=failing_provider)
        result = await orchestrator.process_message("hello", "user-1")

        assert result["success"] is False
        assert result["error_type"] == "llm_error"
        assert "upstream 500" in result["error"]

    async def test_empty_completion_maps_to_llm_error(self):
        provider = FakeProvider(raw_text="   ")
        orchestrator = PlutusOrchestrator(provider=provider)
        result = await orchestrator.process_message("hello", "user-1")

        assert result["success"] is False
        assert result["error_type"] == "llm_error"
