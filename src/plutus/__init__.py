"""
Plutus - AI-Powered Wealth Management Brain for Wealthify
========================================================

Plutus is a sophisticated multi-agent system that provides personalized financial 
advice and insights using LangGraph and Claude API integration.

Core Components:
- Multi-agent conversation system
- User context management 
- Memory and profile persistence
- Real-time financial analysis
- Goal tracking and recommendations
"""

__version__ = "1.0.0"
__author__ = "Wealthify Team"

from .core.config import PlutusConfig
from .agents.orchestrator import PlutusOrchestrator  
from .models.state import ConversationState
from .services.context_service import ContextService

__all__ = [
    "PlutusConfig",
    "PlutusOrchestrator", 
    "ConversationState",
    "ContextService"
]