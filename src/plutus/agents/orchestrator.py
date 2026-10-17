"""
Plutus orchestrator compatibility module
========================================

The original `OrchestratorAgent`/`PlutusOrchestrator` pair that lived here
simulated agent execution with asyncio.sleep and hardcoded analyses. It was
written against a pre-Phase-3 BaseAgent API (`execute`/`_execute_core_logic`)
that no longer exists, so it could neither be instantiated nor produce a real
answer.

`AdvancedOrchestrator` is the real orchestration path. It routes, runs the
specialized agents and synthesizes through the pluggable provider. This module
keeps the long-standing import path

    from plutus.agents.orchestrator import PlutusOrchestrator

working for integrators, and delegates everything to the real implementation.
Wealthify's integration service imports it.
"""

from .advanced_orchestrator import AdvancedOrchestrator

# Historical name used by integrators.
PlutusOrchestrator = AdvancedOrchestrator

__all__ = ["PlutusOrchestrator", "AdvancedOrchestrator"]
