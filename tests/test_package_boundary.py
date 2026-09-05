"""Package-boundary contract: importing plutus never requires sample data,
a .env file, or an LLM key — and the public surface actually resolves."""

from datetime import datetime


def test_top_level_imports_resolve():
    import plutus
    from plutus import (  # noqa: F401
        AdvancedOrchestrator,
        ContextService,
        ConversationState,
        LLMNotConfiguredError,
        PlutusConfig,
        PlutusOrchestrator,
    )

    assert plutus.PlutusOrchestrator is plutus.AdvancedOrchestrator


def test_legacy_orchestrator_import_path_still_works():
    from plutus.agents.orchestrator import PlutusOrchestrator
    from plutus.agents.advanced_orchestrator import AdvancedOrchestrator

    assert PlutusOrchestrator is AdvancedOrchestrator


def test_models_state_symbols_exist():
    from plutus.models.state import (
        AgentResult,
        ConversationState,
        UserContext,
        create_conversation_state,
    )

    state = create_conversation_state("hello", "user-1")
    assert state["user_message"] == "hello"
    assert state["user_id"] == "user-1"
    assert state["agents_to_invoke"] == []

    result = AgentResult(agent_name="x", success=True, execution_time=0.0)
    assert result.recommendations == []

    assert ConversationState is not None
    assert UserContext is not None


def test_user_context_to_dict_is_json_safe():
    from plutus.models.state import UserContext, create_conversation_state

    ctx = UserContext(user_id="user-1", name="Kay")
    data = ctx.to_dict()
    assert data["user_id"] == "user-1"
    assert isinstance(data["last_updated"], str)
    # ISO-8601 round-trips
    datetime.fromisoformat(data["last_updated"])

    state = create_conversation_state("q", "user-1", user_context=ctx)
    assert state["user_context"]["name"] == "Kay"


def test_config_never_raises_without_files_or_key():
    from plutus.core.config import PlutusConfig, get_config

    cfg = PlutusConfig()  # must not raise, print, or need data files
    assert cfg.model
    assert get_config() is not None


def test_config_reads_model_from_env(monkeypatch):
    monkeypatch.setenv("PLUTUS_MODEL", "test-model-override")
    from plutus.core.config import PlutusConfig

    cfg = PlutusConfig()
    assert cfg.model == "test-model-override"


def test_orchestrator_instantiable_without_key():
    from plutus import PlutusOrchestrator

    orchestrator = PlutusOrchestrator()
    assert orchestrator.llm is None
