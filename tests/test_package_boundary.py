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


def test_configuration_import_uses_explicit_environment_without_dotenv(monkeypatch, tmp_path):
    """A fresh import cannot invoke dotenv or inspect/read an environment file."""
    import builtins
    import importlib.util
    from pathlib import Path
    import sys
    import plutus.core.config as config_module

    source = Path(config_module.__file__)
    original_import = builtins.__import__
    original_exists = Path.exists
    original_open = Path.open

    def guarded_import(name, *args, **kwargs):
        if name == "dotenv" or name.startswith("dotenv."):
            raise AssertionError("Configuration must not import an environment-file loader")
        return original_import(name, *args, **kwargs)

    def guarded_exists(path):
        if path.name.startswith(".env"):
            raise AssertionError("Configuration must not discover environment files")
        return original_exists(path)

    def guarded_open(path, *args, **kwargs):
        if path.name.startswith(".env"):
            raise AssertionError("Configuration must not read environment files")
        return original_open(path, *args, **kwargs)

    (tmp_path / ".env").write_text("PLUTUS_MODEL=unrequested-file-value\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PLUTUS_MODEL", "explicit-host-model")
    monkeypatch.setenv("PLUTUS_REQUEST_TIMEOUT", "17")
    monkeypatch.setenv("PLUTUS_MAX_RETRIES", "0")
    monkeypatch.setenv("PLUTUS_INTEGRATION_MODE", "true")
    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(Path, "open", guarded_open)

    spec = importlib.util.spec_from_file_location("plutus_config_import_check", source)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    settings = module.get_config()
    assert settings.model == "explicit-host-model"
    assert settings.request_timeout == 17
    assert settings.max_retries == 0


def test_orchestrator_instantiable_without_key():
    from plutus import PlutusOrchestrator

    orchestrator = PlutusOrchestrator()
    assert orchestrator.llm is None
