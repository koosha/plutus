"""
Plutus Orchestrator Agent
=========================

The main orchestrator that routes conversations and coordinates specialist agents.
This is the entry point for all user interactions with Plutus.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
import json

from .base_agent import BaseAgent
from ..models.state import ConversationState, AgentResult
from ..services.context_service import get_context_service

class OrchestratorAgent(BaseAgent):
    """
    Orchestrator Agent - Routes conversations and coordinates specialist agents
    
    Responsibilities:
    - Classify user intent and complexity
    - Determine which agents to invoke
    - Prepare context for agents
    - Coordinate agent execution
    - Synthesize final response
    """
    
    def __init__(self):
        super().__init__("orchestrator")
        self.context_service = get_context_service()
    
    async def _execute_core_logic(self, state: ConversationState) -> AgentResult:
        """Main orchestrator logic"""
        
        # Step 1: Classify intent and complexity
        classification = await self._classify_user_intent(state)
        
        # Step 2: Determine agent routing
        agents_to_invoke = await self._determine_agent_routing(state, classification)
        
        # Step 3: Prepare enhanced context
        enhanced_context = await self._prepare_enhanced_context(state)
        
        # Update state
        state["intent_classification"] = classification["intent"]
        state["complexity_level"] = classification["complexity"]
        state["confidence_score"] = classification["confidence"]
        state["agents_to_invoke"] = agents_to_invoke
        state["user_context"] = enhanced_context
        
        return AgentResult(
            agent_name=self.agent_name,
            success=True,
            execution_time=0,  # Will be set by base class
            analysis={
                "intent": classification["intent"],
                "complexity": classification["complexity"],
                "agents_to_invoke": agents_to_invoke,
                "routing_confidence": classification["confidence"]
            },
            recommendations=[],
            confidence_score=classification["confidence"]
        )
    
    async def _classify_user_intent(self, state: ConversationState) -> Dict[str, Any]:
        """
        Classify user intent and determine complexity level
        """
        
        user_message = state["user_message"].lower()
        
        # Intent classification
        intent_keywords = {
            "financial_analysis": ["balance", "worth", "assets", "financial health", "overview"],
            "goal_planning": ["goal", "save for", "plan", "target", "achieve", "retire"],
            "investment_advice": ["invest", "portfolio", "stocks", "bonds", "allocation"],
            "debt_management": ["debt", "loan", "pay off", "credit card", "mortgage"],
            "risk_assessment": ["risk", "safe", "conservative", "aggressive", "volatile"],
            "quick_question": ["what is", "how much", "when should", "simple question"],
            "general_advice": ["should I", "what do you think", "advice", "recommend"]
        }
        
        # Score each intent
        intent_scores = {}
        for intent, keywords in intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in user_message)
            if score > 0:
                intent_scores[intent] = score
        
        # Determine primary intent
        if intent_scores:
            primary_intent = max(intent_scores, key=intent_scores.get)
            confidence = intent_scores[primary_intent] / len(intent_keywords[primary_intent])
        else:
            primary_intent = "general_advice"
            confidence = 0.5
        
        # Complexity classification
        complexity_indicators = {
            "simple": ["what is", "how much", "when", "simple"],
            "complex": ["multiple", "both", "optimize", "strategy", "comprehensive", "analysis"]
        }
        
        complexity = "intermediate"  # Default
        
        # Check for simple indicators
        if any(indicator in user_message for indicator in complexity_indicators["simple"]):
            complexity = "simple"
        # Check for complex indicators
        elif any(indicator in user_message for indicator in complexity_indicators["complex"]):
            complexity = "complex"
        
        # Adjust complexity based on context richness
        if len(user_message.split()) > 30:  # Long messages tend to be more complex
            if complexity == "simple":
                complexity = "intermediate"
            elif complexity == "intermediate":
                complexity = "complex"
        
        return {
            "intent": primary_intent,
            "complexity": complexity,
            "confidence": min(confidence, 1.0),
            "all_intents": intent_scores
        }
    
    async def _determine_agent_routing(self, 
                                     state: ConversationState, 
                                     classification: Dict[str, Any]) -> List[str]:
        """
        Determine which agents should be invoked based on intent and complexity
        """
        
        intent = classification["intent"]
        complexity = classification["complexity"]
        
        agents = []
        
        # Route based on complexity first
        if complexity == "simple":
            agents.append("quick_response_agent")
            return agents
        
        # Route based on intent for intermediate/complex queries
        if intent in ["financial_analysis", "general_advice"]:
            agents.append("financial_analysis_agent")
        
        if intent in ["risk_assessment", "investment_advice"] or "risk" in state["user_message"].lower():
            agents.append("risk_assessment_agent")
        
        if intent in ["goal_planning"] or any(goal_word in state["user_message"].lower() 
                                            for goal_word in ["goal", "save for", "plan to"]):
            agents.append("goal_planning_agent")
        
        if intent in ["investment_advice"] or "invest" in state["user_message"].lower():
            agents.append("portfolio_analysis_agent")
        
        # Always include recommendation engine for complex queries
        if complexity == "complex" or len(agents) > 1:
            agents.append("recommendation_engine")
        
        # Always update context and memory
        agents.append("context_memory_agent")
        
        # Ensure we have at least one analysis agent
        if not any(agent in agents for agent in ["financial_analysis_agent", "quick_response_agent"]):
            agents.insert(0, "financial_analysis_agent")
        
        return agents
    
    async def _prepare_enhanced_context(self, state: ConversationState) -> Dict[str, Any]:
        """
        Prepare enhanced context for agents
        """
        
        user_id = state["user_id"]
        
        # Get comprehensive user context
        user_context = await self.context_service.get_user_context(user_id)
        context_summary = await self.context_service.get_context_summary(user_id)
        
        return context_summary
    
    def _generate_simulated_response(self, prompt: str) -> str:
        """Generate simulated orchestrator response"""
        
        return json.dumps({
            "intent": "general_advice",
            "complexity": "intermediate",
            "confidence": 0.8,
            "agents_to_invoke": ["financial_analysis_agent", "recommendation_engine"],
            "reasoning": "Simulated orchestrator classification"
        })

class PlutusOrchestrator:
    """
    High-level orchestrator that manages the entire conversation flow
    """
    
    def __init__(self):
        self.orchestrator_agent = OrchestratorAgent()
        self.context_service = get_context_service()
        self.logger = self.orchestrator_agent.logger
    
    async def process_message(self, 
                            user_message: str,
                            user_id: str,
                            session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a user message through the complete Plutus system
        
        This is the main entry point for all user interactions
        """
        
        start_time = time.time()
        
        try:
            # Create conversation state
            from ..models.state import create_conversation_state
            state = create_conversation_state(
                user_message=user_message,
                user_id=user_id,
                session_id=session_id
            )
            
            self.logger.info(f"Processing message for user {user_id}: {user_message[:50]}...")
            
            # Step 1: Orchestrator analysis
            orchestrator_result = await self.orchestrator_agent.execute(state)
            
            if not orchestrator_result.success:
                return self._create_error_response(
                    "Failed to analyze request", 
                    state, 
                    time.time() - start_time
                )
            
            # Step 2: Get agents to invoke
            agents_to_invoke = state.get("agents_to_invoke", [])
            
            # Step 3: Execute agents (for now, simulate their responses)
            agent_results = await self._execute_agents(state, agents_to_invoke)
            
            # Step 4: Synthesize final response
            final_response = await self._synthesize_response(state, agent_results)
            
            # Step 5: Update context
            await self.context_service.update_context_from_conversation(user_id, state)
            
            total_time = time.time() - start_time
            
            self.logger.info(f"Completed message processing in {total_time:.2f}s")
            
            return {
                "success": True,
                "response": final_response,
                "metadata": {
                    "intent": state.get("intent_classification"),
                    "complexity": state.get("complexity_level"),
                    "agents_used": agents_to_invoke,
                    "processing_time": total_time,
                    "confidence": state.get("confidence_score", 0.0)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            return self._create_error_response(
                str(e), 
                {"user_message": user_message}, 
                time.time() - start_time
            )
    
    async def _execute_agents(self, 
                            state: ConversationState, 
                            agents_to_invoke: List[str]) -> Dict[str, AgentResult]:
        """
        Execute the specified agents
        
        For now, this simulates agent execution. In full implementation,
        this would actually invoke the real agent classes.
        """
        
        results = {}
        
        # Simulate agent execution
        for agent_name in agents_to_invoke:
            try:
                # Simulate processing time
                await asyncio.sleep(0.2)
                
                # Create simulated result
                results[agent_name] = AgentResult(
                    agent_name=agent_name,
                    success=True,
                    execution_time=0.2,
                    analysis=self._get_simulated_agent_analysis(agent_name, state),
                    recommendations=self._get_simulated_recommendations(agent_name, state),
                    confidence_score=0.8
                )
                
            except Exception as e:
                results[agent_name] = AgentResult(
                    agent_name=agent_name,
                    success=False,
                    execution_time=0.0,
                    error_message=str(e),
                    confidence_score=0.0
                )
        
        return results
    
    def _get_simulated_agent_analysis(self, agent_name: str, state: ConversationState) -> Dict[str, Any]:
        """Get simulated analysis from different agent types"""
        
        user_context = state.get("user_context", {})
        financial_snapshot = user_context.get("financial_snapshot", {})
        
        if agent_name == "financial_analysis_agent":
            return {
                "net_worth": financial_snapshot.get("net_worth", 50000),
                "monthly_cash_flow": 2500,
                "savings_rate": 0.18,
                "financial_health_score": 75,
                "key_insights": [
                    "Strong savings rate above recommended 15%",
                    "Net worth growing steadily",
                    "Good emergency fund coverage"
                ]
            }
        
        elif agent_name == "risk_assessment_agent":
            return {
                "overall_risk_score": 65,
                "risk_level": "moderate",
                "key_risks": [
                    "Liquidity risk: Emergency fund could be larger",
                    "Market risk: Portfolio concentration in growth stocks"
                ],
                "mitigation_strategies": [
                    "Build 6-month emergency fund",
                    "Diversify investment portfolio"
                ]
            }
        
        elif agent_name == "goal_planning_agent":
            return {
                "identified_goals": [
                    "Emergency fund completion",
                    "House down payment savings",
                    "Retirement planning"
                ],
                "goal_prioritization": [
                    {"goal": "Emergency fund", "priority": "high", "timeline": "6 months"},
                    {"goal": "House down payment", "priority": "medium", "timeline": "3 years"}
                ]
            }
        
        elif agent_name == "quick_response_agent":
            return {
                "quick_answer": "Based on your financial profile, you're in good shape with room for improvement",
                "key_metric": financial_snapshot.get("wealth_health_score", 70),
                "immediate_insight": "Your wealth health score is above average"
            }
        
        else:
            return {"simulated_analysis": f"Analysis from {agent_name}"}
    
    def _get_simulated_recommendations(self, agent_name: str, state: ConversationState) -> List[str]:
        """Get simulated recommendations from different agent types"""
        
        if agent_name == "financial_analysis_agent":
            return [
                "Continue your strong savings habits",
                "Consider optimizing your account allocation"
            ]
        
        elif agent_name == "risk_assessment_agent":
            return [
                "Build emergency fund to 6 months of expenses",
                "Consider diversifying your investment portfolio"
            ]
        
        elif agent_name == "recommendation_engine":
            return [
                "Focus on emergency fund completion as top priority",
                "Set up automatic transfers to high-yield savings",
                "Review investment allocation quarterly"
            ]
        
        else:
            return [f"Recommendation from {agent_name}"]
    
    async def _synthesize_response(self, 
                                 state: ConversationState, 
                                 agent_results: Dict[str, AgentResult]) -> str:
        """
        Synthesize agent results into a coherent response
        """
        
        # Collect successful results
        successful_results = {
            name: result for name, result in agent_results.items() 
            if result.success
        }
        
        if not successful_results:
            return "I apologize, but I'm having trouble analyzing your request right now. Please try again."
        
        # Build response based on complexity and available results
        complexity = state.get("complexity_level", "intermediate")
        
        if complexity == "simple" and "quick_response_agent" in successful_results:
            # Simple response
            quick_result = successful_results["quick_response_agent"]
            analysis = quick_result.analysis or {}
            return analysis.get("quick_answer", "Here's a quick answer to your question.")
        
        else:
            # Comprehensive response
            response_parts = []
            
            # Add financial analysis
            if "financial_analysis_agent" in successful_results:
                financial_result = successful_results["financial_analysis_agent"]
                analysis = financial_result.analysis or {}
                
                response_parts.append(
                    f"Based on your financial profile, here's what I see:\n"
                    f"• Net worth: ${analysis.get('net_worth', 0):,.0f}\n"
                    f"• Financial health score: {analysis.get('financial_health_score', 0)}/100\n"
                    f"• Monthly cash flow: ${analysis.get('monthly_cash_flow', 0):,.0f}"
                )
            
            # Add risk assessment
            if "risk_assessment_agent" in successful_results:
                risk_result = successful_results["risk_assessment_agent"]
                analysis = risk_result.analysis or {}
                
                response_parts.append(
                    f"\nRisk Assessment:\n"
                    f"• Overall risk level: {analysis.get('risk_level', 'moderate')}\n"
                    f"• Key concerns: {', '.join(analysis.get('key_risks', [])[:2])}"
                )
            
            # Add recommendations
            all_recommendations = []
            for result in successful_results.values():
                all_recommendations.extend(result.recommendations)
            
            if all_recommendations:
                response_parts.append(
                    f"\nMy recommendations:\n" + 
                    "\n".join(f"• {rec}" for rec in all_recommendations[:3])
                )
            
            return "\n".join(response_parts) if response_parts else "I've analyzed your situation and have some insights to share."
    
    def _create_error_response(self, error_message: str, state: Any, processing_time: float) -> Dict[str, Any]:
        """Create standardized error response"""
        
        return {
            "success": False,
            "error": error_message,
            "response": "I'm sorry, I encountered an issue processing your request. Please try again or rephrase your question.",
            "metadata": {
                "processing_time": processing_time,
                "error_details": error_message
            }
        }