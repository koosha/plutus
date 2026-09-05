"""
Plutus Orchestrator — compatibility module
==========================================

The original `OrchestratorAgent`/`PlutusOrchestrator` pair that lived here
*simulated* agent execution (asyncio.sleep + hardcoded analyses) and was
written against a pre-Phase-3 BaseAgent API (`execute`/`_execute_core_logic`)
that no longer exists, so it could neither be instantiated nor produce a real
answer.

`AdvancedOrchestrator` is the real orchestration path (routing, specialized
agents, LLM synthesis through the pluggable provider). This module keeps the
long-standing import path

    from plutus.agents.orchestrator import PlutusOrchestrator

working for integrators (Wealthify's integration service imports it) while
delegating everything to the real implementation.
"""

from .advanced_orchestrator import AdvancedOrchestrator

# Historical name used by integrators.
PlutusOrchestrator = AdvancedOrchestrator

__all__ = ["PlutusOrchestrator", "AdvancedOrchestrator"]
