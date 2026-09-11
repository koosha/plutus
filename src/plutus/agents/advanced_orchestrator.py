"""
Advanced Orchestrator - Phase 3 Multi-Agent Workflow
====================================================

This is the advanced orchestrator that coordinates all specialized agents
using sophisticated LangGraph workflows. It intelligently routes conversations
to the appropriate agents and synthesizes results.

Key Capabilities:
1. Intelligent agent routing based on conversation analysis
2. Parallel agent execution for complex queries
3. Result synthesis and prioritization
4. Context management across agents
5. Conversation memory and continuity
6. Adaptive workflow based on user needs
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
import math

# LangGraph imports
try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    logging.warning("LangGraph not available - using simplified orchestration")
    StateGraph = None
    END = None
    LANGGRAPH_AVAILABLE = False

from .base_agent import BaseAgent
from .boundaries import failure
from .prompt_context import compose_prompt
from .financial_analysis_agent import FinancialAnalysisAgent
from .goal_extraction_agent import GoalExtractionAgent
from .recommendation_agent import RecommendationAgent
from .risk_assessment_agent import RiskAssessmentAgent
from dataclasses import asdict

from ..llm import (
    LLMError,
    LLMNotConfiguredError,
    LLMProvider,
    LLMResponseError,
    OpenAIProvider,
)
from ..models.state import AgentResult, ConversationState, UserContext
from ..services.context_service import get_context_service
from ..core.config import get_config

logger = logging.getLogger(__name__)

# Educational-scope guardrails + output contract for the synthesis call.
# Every real completion goes through this system prompt.
ADVISOR_SYSTEM_PROMPT = """You are Plutus, the AI financial guide inside the Wealthify app.

Strict scope and safety rules:
- Provide educational, general financial information grounded ONLY in the user data supplied in the request. Do not invent numbers that are not present; say plainly when data is missing.
- Missing, withheld, failed or omitted context is unknown, never zero. Respect availability/provenance and prompt_metadata; heuristic findings are limited to their stated evidence and policy.
- Do NOT give individualized investment advice: never recommend buying, selling, or holding any specific security, fund, or asset. Discuss categories, trade-offs, and widely accepted principles instead.
- Never claim to execute trades, move money, open or close accounts, or take any action. You cannot take actions.
- For decisions with tax, legal, or large financial consequences, remind the user to consult a licensed professional.
- Keep a supportive, plain-language tone; be concise.

Output contract — respond with a single JSON object and nothing else (no markdown fences):
{"response": string, "insights": [string, ...], "recommendations": [string, ...], "confidence": number}
- "response": the reply shown to the user (plain text, may use simple bullet lines).
- "insights": up to 5 short observations grounded in the data (may be empty).
- "recommendations": up to 5 short educational next steps (may be empty).
- "confidence": 0..1, your confidence given the data completeness."""


class AdvancedOrchestrator(BaseAgent):
    """
    Advanced orchestrator that coordinates multiple specialized agents
    using LangGraph for sophisticated conversation workflows.
    """
    
    def __init__(self, provider: Optional[LLMProvider] = None):
        config = get_config()

        # Resolve the LLM provider: explicit injection wins (tests, custom
        # vendors); otherwise build the production provider from the
        # environment. An unconfigured environment leaves the provider as
        # None and process_message returns a typed error response.
        #
        # The configured timeout and retry budget are handed to the SDK here.
        # They used to be declared in PlutusConfig and never read, so the
        # provider silently used its own defaults and the config was a claim
        # about a control nobody applied.
        if provider is None:
            try:
                provider = OpenAIProvider(
                    timeout=config.request_timeout,
                    max_retries=config.max_retries,
                )
            except LLMNotConfiguredError:
                logger.info(
                    "No LLM provider configured (OPENAI_API_KEY absent) — "
                    "orchestrator will return llm_not_configured errors"
                )
                provider = None

        super().__init__("Advanced Orchestrator", provider=provider)
        self.agent_type = "advanced_orchestrator"

        # Initialize specialized agents (deterministic analyses)
        self.financial_agent = FinancialAnalysisAgent()
        self.goal_agent = GoalExtractionAgent()
        self.recommendation_agent = RecommendationAgent()
        self.risk_agent = RiskAssessmentAgent()
        
        # Context service
        self.context_service = get_context_service()
        
        # Agent routing patterns
        self.routing_patterns = {
            "financial_analysis": {
                "keywords": ["financial health", "net worth", "portfolio", "balance", "wealth score"],
                "agents": ["financial_analysis"],
                "priority": "high"
            },
            "goal_planning": {
                "keywords": ["goal", "save for", "planning", "target", "want to"],
                "agents": ["goal_extraction", "recommendation"],
                "priority": "high"
            },
            "risk_assessment": {
                "keywords": ["risk", "safe", "volatile", "protection", "conservative", "aggressive"],
                "agents": ["risk_assessment", "recommendation"],
                "priority": "medium"
            },
            "investment_advice": {
                "keywords": ["invest", "stocks", "bonds", "portfolio", "allocation"],
                "agents": ["financial_analysis", "risk_assessment", "recommendation"],
                "priority": "high"
            },
            "debt_management": {
                "keywords": ["debt", "loan", "pay off", "credit card"],
                "agents": ["financial_analysis", "risk_assessment", "recommendation"],
                "priority": "high"
            },
            "comprehensive_analysis": {
                "keywords": ["advice", "recommendation", "what should", "help me"],
                "agents": ["financial_analysis", "goal_extraction", "risk_assessment", "recommendation"],
                "priority": "medium"
            }
        }
        
        # Initialize LangGraph workflow if available
        self.workflow = None
        if LANGGRAPH_AVAILABLE:
            self.workflow = self._build_langgraph_workflow()
    
    async def _process_core_logic(self, state: ConversationState) -> Dict[str, Any]:
        """
        Orchestrator uses process_message instead of the standard process flow.
        This method delegates to process_message for consistency.
        """
        user_message = state.get("user_message", "")
        user_id = state.get("user_id", "unknown")
        session_id = state.get("session_id")
        
        return await self.process_message(user_message, user_id, session_id)
    
    async def process_message(
        self,
        user_message: str,
        user_id: str,
        session_id: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None,
        output_contract: str = "chat",
    ) -> Dict[str, Any]:
        """
        Process user message through advanced multi-agent workflow.

        Args:
            user_message: User's input message
            user_id: User identifier
            session_id: Optional session identifier for conversation continuity
            user_context: Integration-supplied financial context (e.g. built
                by the host app from its live database). When provided it is
                used verbatim and the internal context service is bypassed.

        Returns:
            Comprehensive response from coordinated agents
        """
        
        result = None
        try:
            logger.info(f"Advanced Orchestrator processing message for user {user_id}")

            start_time = datetime.utcnow()

            # 0. Typed refusal when no provider is configured. Plutus does
            # not fabricate advice: without a real LLM the caller gets a
            # machine-readable error and decides how to degrade.
            if self.llm is None:
                return self._create_error_response(
                    "LLM provider is not configured (set OPENAI_API_KEY)",
                    error_type="llm_not_configured",
                )

            # 1. Build conversation state
            state = await self._build_conversation_state(
                user_message, user_id, session_id, user_context
            )

            state["output_contract"] = output_contract

            # 2. Analyze conversation and determine agent routing
            routing_analysis = await self._analyze_conversation_routing(user_message, state)

            # 3. Execute appropriate workflow (deterministic specialist analyses)
            if self.workflow and LANGGRAPH_AVAILABLE:
                result = await self._execute_langgraph_workflow(state, routing_analysis)
            else:
                result = await self._execute_fallback_workflow(state, routing_analysis)

            # 4. Real LLM synthesis: compose the financial context and the
            # specialist findings into one completion that produces the
            # user-facing response (validated into AgentResult).
            #
            # Bounded by the configured wall-clock deadline. The SDK's own
            # per-attempt timeout does not cap total time once retries are in
            # play, so without this a "30 second timeout" can hold a caller's
            # request open for two minutes.
            try:
                result = await asyncio.wait_for(
                    self._synthesize_with_llm(state, result),
                    timeout=self.config.llm_deadline_seconds,
                )
            except asyncio.TimeoutError as exc:
                raise LLMResponseError(
                    "LLM synthesis exceeded "
                    f"{self.config.llm_deadline_seconds:.0f}s"
                ) from exc

            # 5. Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            result["metadata"]["processing_time"] = processing_time

            logger.info(f"Advanced Orchestrator completed in {processing_time:.2f}s")
            return result

        except LLMNotConfiguredError as e:
            logger.warning("Response provider is not configured")
            return self._create_error_response("provider_failed", error_type="llm_not_configured", workflow_result=result)
        except LLMError as e:
            logger.error("Response provider failed: category=%s", type(e).__name__)
            return self._create_error_response("provider_failed", error_type="llm_error", workflow_result=result)
        except Exception as e:
            logger.error("Orchestration failed: category=%s", type(e).__name__)
            return self._create_error_response("analysis_failed", workflow_result=result)
    
    async def _build_conversation_state(
        self,
        user_message: str,
        user_id: str,
        session_id: Optional[str],
        user_context: Optional[Dict[str, Any]] = None,
    ) -> ConversationState:
        """Build comprehensive conversation state.

        An integration-supplied `user_context` wins; otherwise the internal
        context service builds one (standalone mode).
        """

        if user_context is None:
            built = await self.context_service.get_user_context(user_id)
            user_context = (
                built.to_dict() if hasattr(built, "to_dict") else built
            )

        # Build conversation state
        state: ConversationState = {
            "user_message": user_message,
            "user_id": user_id,
            "session_id": session_id or f"session_{user_id}_{datetime.utcnow().timestamp()}",
            "user_context": user_context,
            "agent_results": [],
            "conversation_history": [],
            "metadata": {
                "start_time": datetime.utcnow().isoformat(),
                "orchestrator_type": "advanced",
                "agents_used": [],
                "routing_decisions": []
            }
        }
        
        return state
    
    async def _analyze_conversation_routing(
        self, 
        user_message: str, 
        state: ConversationState
    ) -> Dict[str, Any]:
        """Analyze conversation to determine optimal agent routing"""
        
        message_lower = user_message.lower()
        routing_scores = {}
        
        # Score each routing pattern
        for pattern_name, pattern_data in self.routing_patterns.items():
            score = 0
            matched_keywords = []
            
            # Keyword matching
            for keyword in pattern_data["keywords"]:
                if keyword in message_lower:
                    score += 1
                    matched_keywords.append(keyword)
            
            # Priority weighting
            if pattern_data["priority"] == "high":
                score *= 1.5
            elif pattern_data["priority"] == "medium":
                score *= 1.2
            
            routing_scores[pattern_name] = {
                "score": score,
                "matched_keywords": matched_keywords,
                "agents": pattern_data["agents"],
                "priority": pattern_data["priority"]
            }
        
        # Determine best routing
        best_routing = max(routing_scores.items(), key=lambda x: x[1]["score"])
        routing_name, routing_data = best_routing
        
        # If no strong match, use comprehensive analysis
        if routing_data["score"] < 1:
            routing_name = "comprehensive_analysis"
            routing_data = routing_scores["comprehensive_analysis"]
        
        # Determine execution strategy
        agents_to_run = routing_data["agents"]
        execution_strategy = "parallel" if len(agents_to_run) > 1 else "single"
        
        analysis = {
            "selected_routing": routing_name,
            "routing_confidence": min(routing_data["score"] / 3, 1.0),  # Normalize to 0-1
            "matched_keywords": routing_data["matched_keywords"],
            "agents_to_run": agents_to_run,
            "execution_strategy": execution_strategy,
            "all_scores": routing_scores
        }
        
        logger.info(f"🎯 Routing analysis: {routing_name} ({analysis['routing_confidence']:.1%} confidence)")
        return analysis
    
    def _build_langgraph_workflow(self) -> Optional[Any]:
        """The optional graph consumes exactly the same execution plan."""
        if not LANGGRAPH_AVAILABLE:
            return None
        workflow = StateGraph(dict)
        workflow.add_node("execute_plan", self._langgraph_execute_plan)
        workflow.set_entry_point("execute_plan")
        workflow.add_edge("execute_plan", END)
        return workflow.compile()

    async def _langgraph_execute_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {**state, "workflow_result": await self._execute_plan(state, state["routing_analysis"])}

    async def _execute_langgraph_workflow(self, state, routing_analysis):
        graph_state = {**state, "routing_analysis": routing_analysis}
        result = await self.workflow.ainvoke(graph_state)
        workflow_result = result["workflow_result"]
        workflow_result["metadata"]["workflow_type"] = "langgraph"
        return workflow_result

    async def _execute_fallback_workflow(self, state, routing_analysis):
        return await self._execute_plan(state, routing_analysis)

    async def _execute_plan(self, state, routing_analysis):
        """Run an ordered plan once, retaining every specialist's outcome.

        Both executors share deadlines, concurrency, cancellation and result
        ordering. Workflow failures are never retried through another path.
        """
        agents = list(dict.fromkeys(routing_analysis["agents_to_run"]))
        strategy = routing_analysis["execution_strategy"]
        semaphore = asyncio.Semaphore(self.config.max_parallel_agents)

        async def run(name):
            async with semaphore:
                return await self._run_agent(name, state)

        if strategy == "parallel":
            tasks = [asyncio.create_task(run(name)) for name in agents]
            try:
                results = await asyncio.gather(*tasks)
            finally:
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
        else:
            results = []
            for name in agents:
                results.append(await run(name))
                state = {**state, "agent_results": list(results)}
        successful = [item for item in results if item.get("success") is True]
        return {
            "success": bool(successful),
            "response": await self._synthesize_agent_results(results, state),
            "metadata": {
                **state.get("metadata", {}), "workflow_type": "fallback",
                "execution_strategy": strategy, "routing_analysis": routing_analysis,
                "agents_used": [item["agent_name"] for item in successful],
                "agents_run": len(results), "successful_agents": len(successful),
                "partial": len(successful) < len(results),
            },
            "agent_results": results,
        }

    async def _run_agent(
        self,
        agent_name: str,
        state: ConversationState,
    ) -> Dict[str, Any]:
        """Run one specialist under the configured per-agent deadline.

        A specialist that hangs must not hang the conversation. On timeout it
        yields the same error-shaped result an exception would, so the
        synthesis step sees one failed agent rather than never running.
        """
        agent = self._get_agent_by_name(agent_name)
        if agent is None:
            return {**failure("agent_contract_error"), "agent_name": agent_name,
                    "agent_type": agent_name, "execution_time": 0.0}
        try:
            return await asyncio.wait_for(
                agent.process(state),
                timeout=self.config.agent_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error(
                "Agent %s exceeded %.0fs and was cancelled",
                agent_name,
                self.config.agent_timeout_seconds,
            )
            return {**failure("agent_timeout"), "agent_name": agent_name,
                    "agent_type": agent_name,
                    "execution_time": self.config.agent_timeout_seconds}
        except Exception as exc:
            result = failure()
            logger.error("Specialist failed: category=%s request_id=%s",
                         type(exc).__name__, result["request_id"])
            return {**result, "agent_name": agent_name, "agent_type": agent_name,
                    "execution_time": 0.0}

    async def _synthesize_with_llm(
        self,
        state: ConversationState,
        workflow_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Produce the user-facing answer with ONE real LLM completion.

        The specialists' deterministic analyses plus the user's financial
        context become the user prompt; ADVISOR_SYSTEM_PROMPT carries the
        educational-scope guardrails and the JSON output contract. The
        completion is parsed and validated into an AgentResult that is
        appended to agent_results, and its "response" replaces the template
        synthesis.

        Raises:
            LLMNotConfiguredError / LLMResponseError: bubbled to
            process_message, which maps them to typed error responses.
        """

        prompt = self._compose_synthesis_prompt(state, workflow_result)

        call_started = datetime.utcnow()
        system_prompt = ADVISOR_SYSTEM_PROMPT
        if state.get("output_contract") == "brief":
            system_prompt = ADVISOR_SYSTEM_PROMPT.split("Output contract")[0] + (
                "Output contract: return only a JSON array of brief cards with string fields "
                "tone, title, body and action. Return [] if nothing is notable."
            )
        completion = await self.call_llm(prompt, system_prompt=system_prompt)
        call_seconds = (datetime.utcnow() - call_started).total_seconds()
        workflow_result.setdefault("metadata", {})["llm"] = {
            "model": completion.model, "input_tokens": completion.input_tokens,
            "output_tokens": completion.output_tokens, "api_cost": completion.cost,
            "cost_status": "known" if completion.cost is not None else "unknown",
            "pricing_version": completion.pricing_version,
        }

        if state.get("output_contract") == "brief":
            # The host applies the dedicated card schema and policy gates.
            # Preserve raw output and usage even when that validation rejects it.
            metadata = dict(workflow_result.get("metadata", {}))
            metadata["llm"] = {"model": completion.model,
                "input_tokens": completion.input_tokens, "output_tokens": completion.output_tokens,
                "api_cost": completion.cost, "cost_status": "known" if completion.cost is not None else "unknown",
                "pricing_version": completion.pricing_version}
            brief_text = completion.text
            try:
                wrapped = json.loads(brief_text)
                if isinstance(wrapped, dict) and isinstance(wrapped.get("response"), str):
                    brief_text = wrapped["response"]
            except (ValueError, TypeError):
                pass
            return {**workflow_result, "success": True, "response": brief_text, "metadata": metadata}
        parsed = self.parse_json_response(completion.text)

        response_text = ""
        insights: List[str] = []
        recommendations: List[str] = []
        confidence = 0.5
        if isinstance(parsed, dict):
            raw_response = parsed.get("response")
            if isinstance(raw_response, str):
                response_text = raw_response.strip()
            for key in ("insights", "recommendations"):
                values = parsed.get(key, [])
                if not isinstance(values, list) or len(values) > 5 or any(not isinstance(item, str) or len(item) > 2000 for item in values):
                    raise LLMResponseError("LLM returned invalid list fields")
            insights = parsed.get("insights", [])
            recommendations = parsed.get("recommendations", [])
            try:
                confidence = min(1.0, max(0.0, float(parsed.get("confidence", 0.5))))
                if not math.isfinite(float(parsed.get("confidence", 0.5))):
                    confidence = 0.5
            except (TypeError, ValueError):
                confidence = 0.5
        if not response_text and (isinstance(parsed, dict) or completion.text.lstrip().startswith(("{", "["))):
            raise LLMResponseError("LLM returned an invalid response object")
        if not response_text:
            # Contract violation (non-JSON or empty "response"): the raw
            # completion is still a real model answer — use it verbatim
            # rather than failing the conversation.
            response_text = completion.text.strip()
        if not response_text:
            raise LLMResponseError("LLM returned an empty completion")

        synthesis = AgentResult(
            agent_name="llm_synthesis",
            success=True,
            execution_time=call_seconds,
            analysis={"model": completion.model, "parsed_contract": bool(parsed)},
            recommendations=recommendations,
            insights=insights,
            confidence_score=confidence,
            tokens_used=completion.input_tokens + completion.output_tokens,
            api_cost=completion.cost,
        )

        agent_results = list(workflow_result.get("agent_results", []))
        agent_results.append(asdict(synthesis))

        metadata = dict(workflow_result.get("metadata", {}))
        metadata["agents_used"] = list(metadata.get("agents_used", [])) + [
            "llm_synthesis"
        ]
        metadata["llm"] = {
            "model": completion.model,
            "input_tokens": completion.input_tokens,
            "output_tokens": completion.output_tokens,
            "api_cost": completion.cost,
            "cost_status": "known" if completion.cost is not None else "unknown",
            "pricing_version": completion.pricing_version,
            "parsed_contract": bool(parsed),
        }
        metadata["confidence"] = confidence

        return {
            **workflow_result,
            "success": True,
            "response": response_text,
            "insights": insights,
            "recommendations": recommendations,
            "agent_results": agent_results,
            "metadata": metadata,
        }

    def _compose_synthesis_prompt(
        self,
        state: ConversationState,
        workflow_result: Dict[str, Any],
    ) -> str:
        """Build the user prompt: message + financial context + findings."""

        compact_findings = []
        for item in workflow_result.get("agent_results", []):
            if not item.get("success"):
                continue
            compact_findings.append(
                {
                    "agent": item.get("agent_type") or item.get("agent_name"),
                    "analysis": item.get("analysis"),
                    "recommendations": item.get("recommendations"),
                    "insights": item.get("insights"),
                }
            )

        return compose_prompt(state.get("user_message", ""),
                              state.get("user_context") or {}, compact_findings,
                              self.config.max_output_tokens)

    async def _synthesize_agent_results(
        self,
        agent_results: List[Dict[str, Any]],
        state: ConversationState
    ) -> str:
        """Synthesize results from multiple agents into coherent response"""
        
        successful_results = [r for r in agent_results if r.get("success")]
        
        if not successful_results:
            return "I apologize, but I encountered issues analyzing your request. Please try again."
        
        response_parts = []
        
        # Prioritize responses based on agent importance and content quality
        prioritized_results = self._prioritize_agent_results(successful_results)
        
        # Financial analysis (if present)
        financial_result = next((r for r in prioritized_results if r.get("agent_type") == "financial_analysis"), None)
        if financial_result and financial_result.get("response"):
            response_parts.append(financial_result["response"])
        
        # Goal extraction insights (if present)
        goal_result = next((r for r in prioritized_results if r.get("agent_type") == "goal_extraction"), None)
        if goal_result and goal_result.get("response"):
            response_parts.append(goal_result["response"])
        
        # Risk assessment (if significant)
        risk_result = next((r for r in prioritized_results if r.get("agent_type") == "risk_assessment"), None)
        if risk_result and risk_result.get("response"):
            risk_score = risk_result.get("analysis", {}).get("overall_risk_score", 0)
            if risk_score is not None and risk_score > 40:  # Only include if meaningful risk
                response_parts.append(risk_result["response"])
        
        # Recommendations (always include if present)
        rec_result = next((r for r in prioritized_results if r.get("agent_type") == "recommendation"), None)
        if rec_result and rec_result.get("response"):
            response_parts.append(rec_result["response"])
        
        # If no specific responses, provide summary
        if not response_parts:
            response_parts.append("I've analyzed your financial situation across multiple dimensions. While I don't have specific recommendations at this moment, more verified context is needed to assess your financial health.")
        
        # Add closing if multiple agents provided input
        if len(successful_results) > 1:
            response_parts.append("\nThis analysis considered the available financial context including goals, risk factors, and opportunities for optimization.")
        
        return "\n\n".join(response_parts)
    
    def _prioritize_agent_results(self, agent_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize agent results based on relevance and quality"""
        
        def calculate_priority_score(result: Dict[str, Any]) -> float:
            score = 0.0
            
            # Base scores by agent type
            agent_type = result.get("agent_type", "")
            type_scores = {
                "financial_analysis": 1.0,
                "recommendation": 0.9,
                "goal_extraction": 0.8,
                "risk_assessment": 0.7
            }
            score += type_scores.get(agent_type, 0.5)
            
            # Response quality
            response = result.get("response", "")
            if len(response) > 100:  # Substantial response
                score += 0.3
            elif len(response) > 50:
                score += 0.1
            
            # Analysis depth
            analysis = result.get("analysis", {})
            if analysis:
                score += 0.2
            
            # Confidence/success indicators
            if result.get("success", False):
                score += 0.1
            
            return score
        
        return sorted(agent_results, key=calculate_priority_score, reverse=True)
    
    def _get_agent_by_name(self, agent_name: str) -> Optional[BaseAgent]:
        """Get agent instance by name"""
        
        agent_map = {
            "financial_analysis": self.financial_agent,
            "goal_extraction": self.goal_agent,
            "recommendation": self.recommendation_agent,
            "risk_assessment": self.risk_agent
        }
        
        return agent_map.get(agent_name)
    
    def _create_error_response(
        self, error_message: str, error_type: str = "orchestration_error",
        workflow_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Keep the compatibility argument without exposing exception text."""
        safe = failure(error_type)
        logger.warning("Request failed: category=%s request_id=%s", safe["error_type"], safe["request_id"])
        previous = workflow_result or {}
        return {
            **safe,
            "metadata": {
                **previous.get("metadata", {}),
                "orchestrator_type": "advanced", "workflow_type": "error",
                "error_type": safe["error_type"], "request_id": safe["request_id"],
                "processing_time": 0.0, "timestamp": datetime.utcnow().isoformat(),
            },
            "agent_results": previous.get("agent_results", []),
        }
