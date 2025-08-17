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

# LangGraph imports
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.sqlite import SqliteSaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    logging.warning("LangGraph not available - using simplified orchestration")
    StateGraph = None
    END = None
    SqliteSaver = None
    LANGGRAPH_AVAILABLE = False

from .base_agent import BaseAgent
from .financial_analysis_agent import FinancialAnalysisAgent
from .goal_extraction_agent import GoalExtractionAgent
from .recommendation_agent import RecommendationAgent
from .risk_assessment_agent import RiskAssessmentAgent
from ..models.state import ConversationState, UserContext
from ..services.context_service import get_context_service
from ..core.config import get_config

logger = logging.getLogger(__name__)


class AdvancedOrchestrator(BaseAgent):
    """
    Advanced orchestrator that coordinates multiple specialized agents
    using LangGraph for sophisticated conversation workflows.
    """
    
    def __init__(self):
        super().__init__("Advanced Orchestrator")
        self.agent_type = "advanced_orchestrator"
        
        # Initialize specialized agents
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
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process user message through advanced multi-agent workflow.
        
        Args:
            user_message: User's input message
            user_id: User identifier
            session_id: Optional session identifier for conversation continuity
            
        Returns:
            Comprehensive response from coordinated agents
        """
        
        try:
            logger.info(f"🎯 Advanced Orchestrator processing message for user {user_id}")
            
            start_time = datetime.utcnow()
            
            # 1. Build conversation state
            state = await self._build_conversation_state(user_message, user_id, session_id)
            
            # 2. Analyze conversation and determine agent routing
            routing_analysis = await self._analyze_conversation_routing(user_message, state)
            
            # 3. Execute appropriate workflow
            if self.workflow and LANGGRAPH_AVAILABLE:
                result = await self._execute_langgraph_workflow(state, routing_analysis)
            else:
                result = await self._execute_fallback_workflow(state, routing_analysis)
            
            # 4. Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            result["metadata"]["processing_time"] = processing_time
            
            logger.info(f"✅ Advanced Orchestrator completed in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"❌ Advanced Orchestrator error: {e}")
            return self._create_error_response(f"Advanced orchestration failed: {str(e)}")
    
    async def _build_conversation_state(
        self, 
        user_message: str, 
        user_id: str, 
        session_id: Optional[str]
    ) -> ConversationState:
        """Build comprehensive conversation state"""
        
        # Get user context
        user_context = await self.context_service.get_user_context(user_id)
        
        # Build conversation state
        state: ConversationState = {
            "user_message": user_message,
            "user_id": user_id,
            "session_id": session_id or f"session_{user_id}_{datetime.utcnow().timestamp()}",
            "user_context": user_context.to_dict() if hasattr(user_context, 'to_dict') else user_context,
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
        """Build LangGraph workflow for advanced orchestration"""
        
        if not LANGGRAPH_AVAILABLE:
            return None
        
        try:
            # Create state graph
            workflow = StateGraph(dict)  # Use dict as state type for flexibility
            
            # Add agent nodes
            workflow.add_node("analyze_routing", self._langgraph_analyze_routing)
            workflow.add_node("financial_analysis", self._langgraph_financial_analysis)
            workflow.add_node("goal_extraction", self._langgraph_goal_extraction)
            workflow.add_node("risk_assessment", self._langgraph_risk_assessment)
            workflow.add_node("generate_recommendations", self._langgraph_generate_recommendations)
            workflow.add_node("synthesize_results", self._langgraph_synthesize_results)
            
            # Set entry point
            workflow.set_entry_point("analyze_routing")
            
            # Add conditional routing
            workflow.add_conditional_edges(
                "analyze_routing",
                self._langgraph_route_conversation,
                {
                    "financial_only": "financial_analysis",
                    "goal_only": "goal_extraction", 
                    "risk_only": "risk_assessment",
                    "financial_and_risk": "financial_analysis",
                    "comprehensive": "financial_analysis",
                    "end": END
                }
            )
            
            # Add edges for complex workflows
            workflow.add_edge("financial_analysis", "synthesize_results")
            workflow.add_edge("goal_extraction", "generate_recommendations")
            workflow.add_edge("risk_assessment", "generate_recommendations")
            workflow.add_edge("generate_recommendations", "synthesize_results")
            workflow.add_edge("synthesize_results", END)
            
            # Compile workflow
            compiled_workflow = workflow.compile()
            logger.info("✅ LangGraph workflow compiled successfully")
            return compiled_workflow
            
        except Exception as e:
            logger.error(f"❌ Failed to build LangGraph workflow: {e}")
            return None
    
    async def _execute_langgraph_workflow(
        self, 
        state: ConversationState, 
        routing_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute LangGraph workflow"""
        
        try:
            # Prepare state for LangGraph
            graph_state = {
                **state,
                "routing_analysis": routing_analysis,
                "agent_results": [],
                "final_response": ""
            }
            
            # Run workflow
            result = await self.workflow.ainvoke(graph_state)
            
            # Extract results
            return {
                "success": True,
                "response": result.get("final_response", ""),
                "metadata": {
                    **state.get("metadata", {}),
                    "workflow_type": "langgraph",
                    "agents_used": [r.get("agent_name") for r in result.get("agent_results", [])],
                    "routing_analysis": routing_analysis
                },
                "agent_results": result.get("agent_results", []),
                "routing_decisions": result.get("routing_decisions", [])
            }
            
        except Exception as e:
            logger.error(f"❌ LangGraph workflow execution failed: {e}")
            # Fallback to simple workflow
            return await self._execute_fallback_workflow(state, routing_analysis)
    
    async def _execute_fallback_workflow(
        self, 
        state: ConversationState, 
        routing_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute fallback workflow when LangGraph is not available"""
        
        agents_to_run = routing_analysis["agents_to_run"]
        execution_strategy = routing_analysis["execution_strategy"]
        
        logger.info(f"🔄 Executing {execution_strategy} workflow with agents: {agents_to_run}")
        
        agent_results = []
        
        try:
            if execution_strategy == "parallel":
                # Run agents in parallel
                tasks = []
                for agent_name in agents_to_run:
                    agent = self._get_agent_by_name(agent_name)
                    if agent:
                        tasks.append(agent.process(state))
                
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, Exception):
                            logger.error(f"Agent execution error: {result}")
                        else:
                            agent_results.append(result)
            
            else:
                # Run agents sequentially
                for agent_name in agents_to_run:
                    agent = self._get_agent_by_name(agent_name)
                    if agent:
                        result = await agent.process(state)
                        agent_results.append(result)
                        
                        # Update state with results for next agent
                        state["agent_results"] = agent_results
            
            # Synthesize results
            final_response = await self._synthesize_agent_results(agent_results, state)
            
            return {
                "success": True,
                "response": final_response,
                "metadata": {
                    **state.get("metadata", {}),
                    "workflow_type": "fallback",
                    "execution_strategy": execution_strategy,
                    "agents_used": [r.get("agent_name") for r in agent_results if r.get("success")],
                    "routing_analysis": routing_analysis,
                    "agents_run": len(agent_results),
                    "successful_agents": len([r for r in agent_results if r.get("success")])
                },
                "agent_results": agent_results
            }
            
        except Exception as e:
            logger.error(f"❌ Fallback workflow execution failed: {e}")
            return self._create_error_response(f"Workflow execution failed: {str(e)}")
    
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
            if risk_score > 40:  # Only include if meaningful risk
                response_parts.append(risk_result["response"])
        
        # Recommendations (always include if present)
        rec_result = next((r for r in prioritized_results if r.get("agent_type") == "recommendation"), None)
        if rec_result and rec_result.get("response"):
            response_parts.append(rec_result["response"])
        
        # If no specific responses, provide summary
        if not response_parts:
            response_parts.append("I've analyzed your financial situation across multiple dimensions. While I don't have specific recommendations at this moment, your overall financial health appears to be on track.")
        
        # Add closing if multiple agents provided input
        if len(successful_results) > 1:
            response_parts.append("\nThis analysis considered your complete financial picture including goals, risk factors, and opportunities for optimization.")
        
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
    
    # LangGraph node functions (for when LangGraph is available)
    async def _langgraph_analyze_routing(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph node for routing analysis"""
        routing_analysis = await self._analyze_conversation_routing(
            state["user_message"], state
        )
        state["routing_analysis"] = routing_analysis
        return state
    
    async def _langgraph_financial_analysis(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph node for financial analysis"""
        result = await self.financial_agent.process(state)
        state["agent_results"].append(result)
        return state
    
    async def _langgraph_goal_extraction(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph node for goal extraction"""
        result = await self.goal_agent.process(state)
        state["agent_results"].append(result)
        return state
    
    async def _langgraph_risk_assessment(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph node for risk assessment"""
        result = await self.risk_agent.process(state)
        state["agent_results"].append(result)
        return state
    
    async def _langgraph_generate_recommendations(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph node for generating recommendations"""
        result = await self.recommendation_agent.process(state)
        state["agent_results"].append(result)
        return state
    
    async def _langgraph_synthesize_results(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph node for synthesizing results"""
        final_response = await self._synthesize_agent_results(
            state["agent_results"], state
        )
        state["final_response"] = final_response
        return state
    
    def _langgraph_route_conversation(self, state: Dict[str, Any]) -> str:
        """LangGraph routing function"""
        
        routing_analysis = state.get("routing_analysis", {})
        selected_routing = routing_analysis.get("selected_routing", "comprehensive")
        agents_to_run = routing_analysis.get("agents_to_run", [])
        
        # Map routing decisions to workflow paths
        if selected_routing == "financial_analysis" and len(agents_to_run) == 1:
            return "financial_only"
        elif selected_routing == "goal_planning" and "goal_extraction" in agents_to_run:
            return "goal_only"
        elif selected_routing == "risk_assessment" and len(agents_to_run) <= 2:
            return "risk_only"
        elif "financial_analysis" in agents_to_run and "risk_assessment" in agents_to_run:
            return "financial_and_risk"
        else:
            return "comprehensive"
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create error response"""
        return {
            "success": False,
            "error": error_message,
            "response": "I encountered an issue processing your request. Please try rephrasing your question.",
            "metadata": {
                "orchestrator_type": "advanced",
                "workflow_type": "error",
                "processing_time": 0.0,
                "timestamp": datetime.utcnow().isoformat()
            },
            "agent_results": []
        }