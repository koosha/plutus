"""
Plutus Base Agent
================

Base class for all Plutus agents providing common functionality including
error handling, monitoring, LLM provider access, and result formatting.
"""

import time
import logging
from typing import Dict, List, Any, Optional
from .boundaries import failure, financial_amounts
from abc import ABC, abstractmethod

from ..core.config import get_config
from ..llm import LLMCompletion, LLMNotConfiguredError, LLMProvider
from ..models.state import ConversationState

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    Base class for all Plutus agents

    Provides:
    - LLM provider access (injected; None = agent runs deterministically)
    - Error handling and retries
    - Performance monitoring
    - Standardized result formatting
    - Logging and observability
    """

    def __init__(self, agent_name: str = None, provider: Optional[LLMProvider] = None):
        self.agent_name = agent_name or self.__class__.__name__
        self.config = get_config()
        self.logger = logging.getLogger(f"plutus.agents.{self.agent_name.replace(' ', '_').lower()}")

        # The LLM seam. Deterministic agents leave this as None; anything
        # that needs generation calls `call_llm` and gets a typed
        # LLMNotConfiguredError when no provider was injected.
        self.llm = provider

        # Performance tracking
        self.total_calls = 0
        self.total_errors = 0
        self.total_api_cost = 0.0
        self.total_execution_time = 0.0
    
    async def process(self, state: ConversationState) -> Dict[str, Any]:
        """
        Main execution method for the agent
        
        Handles error handling, monitoring, and result formatting
        """
        
        started = time.monotonic()
        self.total_calls += 1
        result = None
        try:
            result = await self._process_core_logic(state)
            if not isinstance(result, dict) or not result:
                result = failure("agent_contract_error")
            elif "success" in result and not isinstance(result["success"], bool):
                result = failure("agent_contract_error")
            elif result.get("success") is False:
                # Preserve structured findings/partial status, but exception
                # strings and failed prose must never become public advice.
                result = {**result, **failure(result.get("error_type", "agent_error"))}
                result.pop("error_message", None)
            else:
                result = {**result, "success": True}
        except Exception as exc:
            result = failure()
            self.logger.error("Analysis failed: category=%s request_id=%s",
                              type(exc).__name__, result["request_id"])
        finally:
            elapsed = time.monotonic() - started
            self.total_execution_time += elapsed
        if not result["success"]:
            self.total_errors += 1
        result.update(agent_name=self.agent_name,
                      agent_type=getattr(self, 'agent_type', 'unknown'),
                      execution_time=elapsed)
        return result

    @abstractmethod
    async def _process_core_logic(self, state: ConversationState) -> Dict[str, Any]:
        """
        Abstract method for agent-specific logic
        
        Must be implemented by each agent subclass
        """
        pass
    
    async def call_llm(self,
                       prompt: str,
                       system_prompt: Optional[str] = None,
                       max_output_tokens: Optional[int] = None) -> LLMCompletion:
        """One real LLM completion through the injected provider.

        There is deliberately NO simulation fallback here: an agent that
        needs generation either has a configured provider or surfaces the
        typed error to its caller.

        Raises:
            LLMNotConfiguredError: no provider was injected.
            LLMResponseError: the provider call failed.
        """

        if self.llm is None:
            raise LLMNotConfiguredError(
                f"{self.agent_name}: no LLM provider configured"
            )

        completion = await self.llm.complete(
            [{"role": "user", "content": prompt}],
            system=system_prompt,
            max_output_tokens=max_output_tokens or self.config.max_output_tokens,
            temperature=self.config.llm_temperature,
        )
        self.total_api_cost += completion.cost
        return completion

    def parse_json_response(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Parse a JSON object out of an LLM response with error handling
        """
        
        try:
            # Find JSON boundaries
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                self.logger.warning(f"{self.agent_name}: No JSON found in response")
                return None
            
            json_content = content[start_idx:end_idx]
            
            import json
            return json.loads(json_content)
            
        except json.JSONDecodeError as e:
            self.logger.warning("Response JSON could not be decoded")
            return None
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this agent"""
        
        avg_execution_time = (
            self.total_execution_time / max(self.total_calls, 1)
        )
        
        error_rate = self.total_errors / max(self.total_calls, 1)
        
        return {
            "agent_name": self.agent_name,
            "total_calls": self.total_calls,
            "total_errors": self.total_errors,
            "error_rate": error_rate,
            "avg_execution_time": avg_execution_time,
            "total_api_cost": self.total_api_cost,
            "status": "healthy" if error_rate < 0.1 else "degraded" if error_rate < 0.5 else "unhealthy"
        }
    
    def extract_financial_amounts(self, text: str) -> List[float]:
        """Compatibility entry point for the shared money parser."""
        return financial_amounts(text)

    def extract_time_references(self, text: str) -> List[str]:
        """Extract time references from text"""
        
        import re
        
        time_patterns = [
            r'(\d+)\s*(?:years?|yrs?)',
            r'(\d+)\s*months?',
            r'by\s*(\d{4})',  # by 2025
            r'in\s*(\d+)\s*(?:years?|months?)',
            r'(?:retire|retirement)\s*(?:at|by)\s*(\d+)',
        ]
        
        time_refs = []
        
        for pattern in time_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            time_refs.extend(matches)
        
        return time_refs