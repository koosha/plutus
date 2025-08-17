"""
Plutus Base Agent
================

Base class for all Plutus agents providing common functionality including
error handling, monitoring, Claude API integration, and result formatting.
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod

from ..core.config import get_config
from ..models.state import ConversationState, AgentResult

# Import Claude API components
try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    Base class for all Plutus agents
    
    Provides:
    - Claude API integration
    - Error handling and retries
    - Performance monitoring
    - Standardized result formatting
    - Logging and observability
    """
    
    def __init__(self, agent_name: str = None):
        self.agent_name = agent_name or self.__class__.__name__
        self.config = get_config()
        self.logger = logging.getLogger(f"plutus.agents.{self.agent_name.replace(' ', '_').lower()}")
        
        # Initialize Claude client if available
        self.claude_client = None
        if self.config.anthropic_api_key and ANTHROPIC_AVAILABLE:
            self.claude_client = AsyncAnthropic(api_key=self.config.anthropic_api_key)
        elif not self.config.anthropic_api_key:
            self.logger.warning(f"{agent_name}: No API key found, will use simulation mode")
        
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
        
        start_time = time.time()
        self.total_calls += 1
        
        self.logger.info(f"{self.agent_name}: Starting execution")
        
        try:
            # Execute agent-specific logic
            result = await self._process_core_logic(state)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            self.total_execution_time += execution_time
            
            # Update result metadata
            result.update({
                "agent_name": self.agent_name,
                "agent_type": getattr(self, 'agent_type', 'unknown'),
                "execution_time": execution_time,
                "success": True
            })
            
            self.logger.info(
                f"{self.agent_name}: Completed in {execution_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            self.total_errors += 1
            execution_time = time.time() - start_time
            
            self.logger.error(f"{self.agent_name}: Failed after {execution_time:.2f}s - {str(e)}")
            
            # Return error result
            return {
                "agent_name": self.agent_name,
                "agent_type": getattr(self, 'agent_type', 'unknown'),
                "success": False,
                "execution_time": execution_time,
                "error": str(e),
                "response": f"I encountered an error while processing your request: {str(e)}"
            }
    
    @abstractmethod
    async def _process_core_logic(self, state: ConversationState) -> Dict[str, Any]:
        """
        Abstract method for agent-specific logic
        
        Must be implemented by each agent subclass
        """
        pass
    
    async def call_claude(self, 
                         prompt: str, 
                         system_prompt: Optional[str] = None,
                         max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        Make authenticated call to Claude API with error handling
        """
        
        if not self.claude_client:
            # Fallback to simulation
            return await self._simulate_claude_response(prompt)
        
        try:
            messages = [{"role": "user", "content": prompt}]
            
            response = await self.claude_client.messages.create(
                model=self.config.claude_model,
                max_tokens=max_tokens or self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=messages
            )
            
            # Calculate cost
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = (
                input_tokens * self.config.cost_per_input_token +
                output_tokens * self.config.cost_per_output_token
            )
            
            self.total_api_cost += cost
            
            return {
                "success": True,
                "content": response.content[0].text,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost
            }
            
        except Exception as e:
            self.logger.error(f"{self.agent_name}: Claude API error - {str(e)}")
            # Fallback to simulation
            return await self._simulate_claude_response(prompt)
    
    async def _simulate_claude_response(self, prompt: str) -> Dict[str, Any]:
        """
        Simulate Claude response when API is not available
        """
        
        # Add small delay to simulate API call
        await asyncio.sleep(0.5)
        
        return {
            "success": True,
            "content": self._generate_simulated_response(prompt),
            "input_tokens": len(prompt.split()) * 1.3,  # Rough estimation
            "output_tokens": 200,  # Rough estimation
            "cost": 0.0,
            "simulated": True
        }
    
    def _generate_simulated_response(self, prompt: str) -> str:
        """
        Generate a simulated response based on agent type and prompt
        
        Override in subclasses for agent-specific simulation
        """
        return f"Simulated response from {self.agent_name} for prompt analysis."
    
    def parse_json_response(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON response from Claude with error handling
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
            self.logger.error(f"{self.agent_name}: JSON parsing error - {str(e)}")
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
        """Extract monetary amounts from text"""
        
        import re
        
        # Pattern to match various money formats
        money_patterns = [
            r'\$([0-9,]+(?:\.[0-9]{2})?)',           # $1,000.00
            r'([0-9,]+(?:\.[0-9]{2})?) dollars',    # 1000 dollars
            r'([0-9,]+)k',                          # 50k
            r'([0-9,]+) thousand',                  # 50 thousand
        ]
        
        amounts = []
        
        for pattern in money_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Clean up the match
                    clean_amount = match.replace(',', '')
                    amount = float(clean_amount)
                    
                    # Convert k notation
                    if 'k' in match.lower():
                        amount *= 1000
                    elif 'thousand' in match.lower():
                        amount *= 1000
                    
                    amounts.append(amount)
                except ValueError:
                    continue
        
        return amounts
    
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