"""Configured operational limits are applied, not just declared.

The review finding these answer is narrow and unglamorous: PlutusConfig
named a request timeout, a retry budget, an agent timeout, a parallelism cap
and a daily cost limit, and the code applied none of them. A config field
that names a control nobody enforces reads like a guarantee, which makes it
worse than no field.

So: the surviving fields are tested for enforcement, and the removed ones
are tested for absence — otherwise the next person re-adds a comforting
`enable_pii_scrubbing: bool = True` and nothing catches it.
"""

import asyncio
import dataclasses

import pytest

from plutus.core.config import PlutusConfig, get_config, set_config


# Fields deleted because nothing in this package enforced them. Cost control
# belongs to the host (it has the meter and the user identity); scrubbing and
# encryption never existed here at all.
REMOVED_FIELDS = (
    "daily_cost_limit",
    "enable_pii_scrubbing",
    "encrypt_sensitive_data",
    "enable_agent_caching",
    "enable_metrics",
    "enable_tracing",
    "max_conversation_length",
    "memory_database_path",
)


@pytest.fixture
def restore_config():
    original = get_config()
    yield
    set_config(original)


class TestConfigSurface:
    @pytest.mark.parametrize("field", REMOVED_FIELDS)
    def test_unenforced_settings_are_gone(self, field):
        names = {f.name for f in dataclasses.fields(PlutusConfig)}
        assert field not in names, (
            f"{field} is back. Either enforce it in this package or leave it "
            "out — a setting that claims a control it does not apply is the "
            "bug this removal fixed."
        )

    def test_the_llm_deadline_accounts_for_retries(self):
        """A 30s timeout with 3 retries is a 120s wall clock, not 30s."""
        config = PlutusConfig(request_timeout=30.0, max_retries=3)
        assert config.llm_deadline_seconds == 120.0

    def test_to_dict_publishes_the_enforced_limits(self):
        published = PlutusConfig().to_dict()
        for field in (
            "request_timeout",
            "max_retries",
            "llm_deadline_seconds",
            "agent_timeout_seconds",
            "max_parallel_agents",
        ):
            assert field in published
        assert "openai_api_key" not in published

    def test_from_dict_round_trips_through_to_dict(self):
        """to_dict exposes a computed field; from_dict must not choke on it."""
        original = PlutusConfig(request_timeout=12.0, max_retries=1)
        restored = PlutusConfig.from_dict(original.to_dict())
        assert restored.request_timeout == 12.0
        assert restored.max_retries == 1

    def test_a_malformed_limit_is_ignored_rather_than_applied(
        self, monkeypatch
    ):
        """A bad env value must not silently become a different limit."""
        monkeypatch.setenv("PLUTUS_REQUEST_TIMEOUT", "not-a-number")
        monkeypatch.setenv("PLUTUS_MAX_PARALLEL_AGENTS", "-4")
        config = PlutusConfig()
        assert config.request_timeout == 30.0
        assert config.max_parallel_agents == 5

    def test_limits_can_be_tuned_from_the_environment(self, monkeypatch):
        monkeypatch.setenv("PLUTUS_REQUEST_TIMEOUT", "5")
        monkeypatch.setenv("PLUTUS_MAX_RETRIES", "0")
        monkeypatch.setenv("PLUTUS_AGENT_TIMEOUT", "2.5")
        monkeypatch.setenv("PLUTUS_MAX_PARALLEL_AGENTS", "2")
        config = PlutusConfig()
        assert config.request_timeout == 5.0
        assert config.max_retries == 0
        assert config.agent_timeout_seconds == 2.5
        assert config.max_parallel_agents == 2
        assert config.llm_deadline_seconds == 5.0


class TestOrchestratorAppliesLimits:
    @pytest.mark.asyncio
    async def test_a_hung_synthesis_is_cancelled_at_the_deadline(
        self, restore_config
    ):
        """Without this, a stuck provider holds the caller's request open."""
        from plutus.agents.advanced_orchestrator import AdvancedOrchestrator
        from plutus.llm import LLMCompletion, LLMProvider

        set_config(PlutusConfig(request_timeout=0.05, max_retries=0))

        class HangingProvider(LLMProvider):
            async def complete(self, messages, **kwargs) -> LLMCompletion:
                await asyncio.sleep(5)
                raise AssertionError("should have been cancelled")

        orchestrator = AdvancedOrchestrator(provider=HangingProvider())
        result = await asyncio.wait_for(
            orchestrator.process_message("How am I doing?", "user-1"),
            timeout=2,
        )

        assert result["success"] is False
        assert result["error_type"] == "llm_error"
        assert "exceeded" in result["error"]

    @pytest.mark.asyncio
    async def test_a_hung_specialist_does_not_hang_the_conversation(
        self, restore_config, fake_provider
    ):
        from plutus.agents.advanced_orchestrator import AdvancedOrchestrator

        set_config(PlutusConfig(agent_timeout_seconds=0.05))
        orchestrator = AdvancedOrchestrator(provider=fake_provider)

        async def never_returns(state):
            await asyncio.sleep(5)

        orchestrator.financial_agent.process = never_returns
        orchestrator.goal_agent.process = never_returns
        orchestrator.recommendation_agent.process = never_returns
        orchestrator.risk_agent.process = never_returns

        result = await asyncio.wait_for(
            orchestrator.process_message("How am I doing?", "user-1"),
            timeout=3,
        )

        # The specialists timed out; synthesis still ran and answered.
        assert result["success"] is True
        assert len(fake_provider.calls) == 1

    @pytest.mark.asyncio
    async def test_parallel_fan_out_respects_the_configured_cap(
        self, restore_config, fake_provider
    ):
        from plutus.agents.advanced_orchestrator import AdvancedOrchestrator

        set_config(PlutusConfig(max_parallel_agents=1))
        orchestrator = AdvancedOrchestrator(provider=fake_provider)

        concurrent = 0
        peak = 0

        def _instrument(agent):
            original = agent.process

            async def tracked(state):
                nonlocal concurrent, peak
                concurrent += 1
                peak = max(peak, concurrent)
                try:
                    await asyncio.sleep(0.01)
                    return await original(state)
                finally:
                    concurrent -= 1

            agent.process = tracked

        for agent in (
            orchestrator.financial_agent,
            orchestrator.goal_agent,
            orchestrator.recommendation_agent,
            orchestrator.risk_agent,
        ):
            _instrument(agent)

        # "what should I do" routes to the comprehensive four-agent path.
        await orchestrator.process_message("what should I do", "user-1")

        assert peak == 1, f"cap of 1 was exceeded (peak {peak})"

    def test_the_provider_receives_the_configured_timeout_and_retries(
        self, restore_config, monkeypatch
    ):
        """The default provider must be built FROM the config, not defaults."""
        import plutus.agents.advanced_orchestrator as module

        set_config(PlutusConfig(request_timeout=7.0, max_retries=1))
        captured = {}

        class RecordingProvider:
            def __init__(self, *args, **kwargs):
                captured.update(kwargs)

        monkeypatch.setattr(module, "OpenAIProvider", RecordingProvider)
        module.AdvancedOrchestrator()

        assert captured == {"timeout": 7.0, "max_retries": 1}
