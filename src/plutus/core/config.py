"""
Plutus Configuration Management
==============================

Centralized configuration for the Plutus AI system including API keys,
model settings, database connections, and operational parameters.

Every setting here is applied by code somewhere in this package. That is a
rule, not a description: a config field that names a control nobody enforces
is worse than no field at all, because it reads like a guarantee. Several
fields were removed for exactly that reason — see the "Deliberately absent"
note below — and anything added back has to come with the code that honours
it.

Deliberately absent
-------------------
- ``daily_cost_limit`` — Plutus has no meter, no store and no notion of a
  user beyond an id string, so it could never enforce a budget. Cost control
  belongs to the host application, which has all three; in Wealthify that is
  ``services/plutus_integration/budget.py``.
- ``enable_pii_scrubbing`` / ``encrypt_sensitive_data`` — no scrubbing or
  encryption exists in this package. Both read as security guarantees and
  neither was one. Data minimisation and consent are enforced by the host
  when it builds the context it passes in.
- ``enable_agent_caching``, ``enable_metrics``, ``enable_tracing``,
  ``max_conversation_length``, ``memory_database_path`` — declared, never
  read.
"""

import dataclasses
import logging
import math
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


# Limits bound work even when configuration is supplied directly by a host.
_LIMITS = {
    "request_timeout": (float, 0, 3600),
    "agent_timeout_seconds": (float, 0, 3600),
    "max_retries": (int, 0, 10),
    "max_parallel_agents": (int, 1, 64),
    "max_output_tokens": (int, 1, 16384),
    "context_ttl_seconds": (int, 1, 604800),
    "llm_temperature": (float, 0, 2),
}


def validate_limit(name, value):
    """Reject invalid host settings without including their raw value."""
    kind, minimum, maximum = _LIMITS[name]
    if name == "llm_temperature" and value is None:
        return value
    valid_type = isinstance(value, (int, float)) if kind is float else isinstance(value, int)
    try:
        finite = math.isfinite(value) if valid_type else False
    except OverflowError:
        finite = False
    if isinstance(value, bool) or not valid_type or not finite:
        raise ValueError(f"{name} must be a finite {kind.__name__}")
    if value < minimum or value > maximum or (name.endswith('timeout') or name == 'agent_timeout_seconds') and value == 0:
        raise ValueError(f"{name} is outside its supported range")
    return value


def _from_env(env_name, name, current):
    raw = os.getenv(env_name)
    if raw is None or raw == "":
        return current
    try:
        value = _LIMITS[name][0](raw)
        return validate_limit(name, value)
    except (ValueError, OverflowError):
        # Malformed environment overrides retain a previously validated safe
        # default. Never log raw environment values (they may be secrets).
        logger.warning("Ignoring invalid operational setting %s", env_name)
        return current

# The host owns environment loading. Importing this library never discovers
# configuration files or mutates process settings from a repository-local file.

@dataclass
class PlutusConfig:
    """
    Central configuration for Plutus system
    """
    
    # LLM Provider Configuration (the plutus.llm package is the only caller).
    # The API key is only ever read from the environment — never hardcoded.
    openai_api_key: Optional[str] = None
    model: str = "gpt-5-mini"
    max_output_tokens: int = 1024
    # None = "use the provider's default"; omitted from requests entirely
    # (the current reasoning-model family rejects non-default temperatures).
    llm_temperature: Optional[float] = None
    # Per-attempt timeout and retry budget handed to the provider SDK
    # (plutus.llm.OpenAIProvider) by the orchestrator.
    request_timeout: float = 30.0
    max_retries: int = 3

    # Database Configuration
    database_url: Optional[str] = None
    redis_url: Optional[str] = None

    # Memory Management
    context_ttl_seconds: int = 3600

    # Agent Configuration — applied in AdvancedOrchestrator: a semaphore
    # bounds fan-out, and each specialist run is wrapped in a deadline.
    max_parallel_agents: int = 5
    agent_timeout_seconds: float = 30.0

    # Monitoring & Observability
    enable_logging: bool = True
    log_level: str = "INFO"

    # Integration Settings
    integration_mode: bool = True  # True when running inside Wealthify
    standalone_mode: bool = False  # True when running as standalone service

    # Test Data Paths (for standalone testing)
    sample_users_path: str = "data/sample_users.json"
    sample_questions_path: str = "data/sample_questions.json"

    @property
    def llm_deadline_seconds(self) -> float:
        """Wall-clock ceiling for one synthesis, including retries.

        `request_timeout` bounds a single attempt and the SDK may make
        `max_retries` more of them, so the honest ceiling for the caller is
        their product. Without this, a "30 second timeout" can hold a request
        open for two minutes.
        """
        return self.request_timeout * (self.max_retries + 1)

    def __post_init__(self):
        """Initialize configuration from environment variables"""
        
        for name in _LIMITS:
            validate_limit(name, getattr(self, name))
        self.openai_api_key = os.getenv("OPENAI_API_KEY", self.openai_api_key)
        self.model = os.getenv("PLUTUS_MODEL", self.model)
        env_limits = {
            "PLUTUS_TEMPERATURE": "llm_temperature",
            "PLUTUS_MAX_OUTPUT_TOKENS": "max_output_tokens",
            "PLUTUS_REQUEST_TIMEOUT": "request_timeout",
            "PLUTUS_MAX_RETRIES": "max_retries",
            "PLUTUS_AGENT_TIMEOUT": "agent_timeout_seconds",
            "PLUTUS_MAX_PARALLEL_AGENTS": "max_parallel_agents",
            "PLUTUS_CONTEXT_TTL": "context_ttl_seconds",
        }
        for env_name, name in env_limits.items():
            setattr(self, name, _from_env(env_name, name, getattr(self, name)))
        self.database_url = os.getenv("DATABASE_URL", self.database_url)
        self.redis_url = os.getenv("REDIS_URL", self.redis_url)

        # Integration mode detection
        self.integration_mode = os.getenv("PLUTUS_INTEGRATION_MODE", str(self.integration_mode)).lower() == "true"
        self.standalone_mode = not self.integration_mode
        
        # Validate required settings
        self.validate()
    
    def validate(self):
        """Log configuration warnings.

        Never raises: a missing key or sample-data file downgrades behavior
        (callers decide how), it must not make `import plutus` explode.
        """

        # Sample data files are only relevant in standalone mode, and even
        # there they are optional — data_service handles their absence.
        if self.standalone_mode:
            project_root = Path(__file__).parent.parent.parent.parent
            for rel_path in (self.sample_users_path, self.sample_questions_path):
                abs_path = project_root / rel_path
                if not abs_path.exists():
                    logger.warning("Sample data file not found: %s", abs_path)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary (never includes the API key)."""
        return {
            "model": self.model,
            "max_output_tokens": self.max_output_tokens,
            "llm_temperature": self.llm_temperature,
            "request_timeout": self.request_timeout,
            "max_retries": self.max_retries,
            "llm_deadline_seconds": self.llm_deadline_seconds,
            "context_ttl_seconds": self.context_ttl_seconds,
            "max_parallel_agents": self.max_parallel_agents,
            "agent_timeout_seconds": self.agent_timeout_seconds,
            "integration_mode": self.integration_mode,
            "standalone_mode": self.standalone_mode,
            "enable_logging": self.enable_logging,
            "log_level": self.log_level
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "PlutusConfig":
        """Create config from dictionary.

        Computed fields (`llm_deadline_seconds`) round-trip out of
        `to_dict` but are not constructor arguments, so they are dropped
        rather than raising.
        """
        fields = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in config_dict.items() if k in fields})

    @classmethod
    def development(cls) -> "PlutusConfig":
        """Development configuration preset"""
        return cls(
            context_ttl_seconds=1800,  # 30 minutes
            enable_logging=True,
            log_level="DEBUG",
        )

    @classmethod
    def production(cls) -> "PlutusConfig":
        """Production configuration preset"""
        return cls(
            context_ttl_seconds=3600,  # 1 hour
            enable_logging=True,
            log_level="INFO",
        )

# Global config instance
config = PlutusConfig.development()

def get_config() -> PlutusConfig:
    """Get the global configuration instance"""
    return config

def set_config(new_config: PlutusConfig):
    """Set the global configuration instance"""
    global config
    config = new_config
