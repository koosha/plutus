"""
Plutus - AI-Powered Wealth Management Brain for Wealthify
========================================================

Plutus is a multi-agent system that provides personalized financial
guidance and insights through a pluggable LLM provider.

Core Components:
- Multi-agent conversation system with real LLM synthesis
- Pluggable LLM provider layer (plutus.llm)
- User context management
- Real-time financial analysis
- Goal tracking and recommendations
"""

__version__ = "1.0.0"
__author__ = "Wealthify Team"

from .core.config import PlutusConfig, set_config
from .agents.advanced_orchestrator import AdvancedOrchestrator
from .llm import (
    LLMError,
    LLMNotConfiguredError,
    LLMProvider,
    LLMResponseError,
    OpenAIProvider,
)
from .models.state import ConversationState
from .services.context_service import ContextService

# Main orchestrator class - use AdvancedOrchestrator as default
PlutusOrchestrator = AdvancedOrchestrator

__all__ = [
    "PlutusConfig",
    "PlutusOrchestrator",
    "AdvancedOrchestrator",
    "ConversationState",
    "ContextService",
    "LLMError",
    "LLMNotConfiguredError",
    "LLMProvider",
    "LLMResponseError",
    "OpenAIProvider",
    "set_config",
]
