"""
Plutus state management
=======================

Defines the state structures used throughout the Plutus multi-agent system,
including conversation state, user context and agent communication.
"""

from typing import TypedDict, List, Dict, Any, Optional
from typing_extensions import Annotated
from datetime import datetime
from dataclasses import dataclass, field
import operator
import uuid

# =============================================================================
# Core state definitions
# =============================================================================

class ConversationState(TypedDict):
    """
    Primary state object passed between agents in the LangGraph workflow.

    It holds everything agents need to process user requests and keep the
    conversation context.
    """
    
    # Input information
    user_message: str
    user_id: str
    session_id: str
    message_id: str
    timestamp: str
    
    # User context from Wealthify
    user_context: Dict[str, Any]
    conversation_history: List[Dict[str, Any]]
    
    # Intent and routing
    intent_classification: Optional[str]
    complexity_level: str  # simple, intermediate, complex
    confidence_score: float
    agents_to_invoke: List[str]
    
    # Agent processing results
    financial_analysis: Optional[Dict[str, Any]]
    risk_assessment: Optional[Dict[str, Any]]
    goal_analysis: Optional[Dict[str, Any]]
    portfolio_analysis: Optional[Dict[str, Any]]
    quick_response: Optional[Dict[str, Any]]
    
    # Accumulated results; operator.add merges them across parallel agents
    recommendations: Annotated[List[str], operator.add]
    insights: Annotated[List[str], operator.add]
    follow_up_questions: Annotated[List[str], operator.add]
    
    # Final response
    response_text: str
    response_metadata: Dict[str, Any]
    
    # System state
    processing_errors: Annotated[List[str], operator.add]
    agent_execution_times: Dict[str, float]
    total_processing_time: float
    api_costs: Dict[str, float]

@dataclass
class UserContext:
    """
    User context built from Wealthify data
    """
    
    # Basic information
    user_id: str
    name: Optional[str] = None
    age: Optional[int] = None
    location: Optional[str] = None
    
    # Financial data
    accounts: List[Dict[str, Any]] = field(default_factory=list)
    net_worth: float = 0.0
    monthly_income: float = 0.0
    monthly_expenses: float = 0.0
    
    # Goals and planning
    goals: List[Dict[str, Any]] = field(default_factory=list)
    goal_progress: Dict[str, float] = field(default_factory=dict)
    
    # Wealth health
    wealth_health_score: float = 0.0
    component_scores: Dict[str, float] = field(default_factory=dict)
    
    # Behavioral profile
    risk_tolerance: Optional[str] = None
    investment_experience: Optional[str] = None
    financial_personality: Dict[str, Any] = field(default_factory=dict)
    
    # Conversation context
    recent_topics: List[str] = field(default_factory=list)
    common_questions: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    last_updated: datetime = field(default_factory=datetime.now)
    context_version: int = 1
    completeness_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """JSON-safe dict view of the context.

        Used by `create_conversation_state` and the orchestrator when
        embedding the context into a ConversationState. Datetimes are
        rendered as ISO-8601 strings so the result is serializable.
        """
        from dataclasses import asdict

        data = asdict(self)
        data["last_updated"] = self.last_updated.isoformat()
        return data

@dataclass
class AgentResult:
    """
    Standardized result format from individual agents
    """
    
    agent_name: str
    success: bool
    execution_time: float
    
    # Core results
    analysis: Optional[Dict[str, Any]] = None
    recommendations: List[str] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    
    # Metadata
    confidence_score: float = 0.0
    data_quality: float = 0.0
    
    # API usage
    tokens_used: int = 0
    api_cost: float = 0.0
    
    # Error handling
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    # Follow-up
    follow_up_questions: List[str] = field(default_factory=list)
    suggested_next_actions: List[str] = field(default_factory=list)

# =============================================================================
# Specialized state types
# =============================================================================

class FinancialAnalysisState(TypedDict):
    """State specific to financial analysis agent"""
    
    accounts_data: Dict[str, Any]
    income_data: Dict[str, Any]
    expense_data: Dict[str, Any]
    debt_data: Dict[str, Any]
    
    # Analysis results
    financial_health_score: float
    key_metrics: Dict[str, float]
    cash_flow_analysis: Dict[str, Any]
    debt_analysis: Dict[str, Any]

class RiskAssessmentState(TypedDict):
    """State specific to risk assessment agent"""
    
    portfolio_data: Dict[str, Any]
    insurance_data: Dict[str, Any]
    emergency_fund_data: Dict[str, Any]
    career_data: Dict[str, Any]
    
    # Risk analysis results
    overall_risk_score: float
    risk_breakdown: Dict[str, Any]
    risk_factors: List[str]
    mitigation_strategies: List[str]

class GoalPlanningState(TypedDict):
    """State specific to goal planning agent"""
    
    existing_goals: List[Dict[str, Any]]
    user_priorities: List[str]
    timeline_constraints: Dict[str, Any]
    resource_availability: Dict[str, Any]
    
    # Goal analysis results
    goal_feasibility: Dict[str, float]
    prioritized_goals: List[Dict[str, Any]]
    resource_allocation: Dict[str, Any]
    timeline_recommendations: Dict[str, Any]

# =============================================================================
# Utility functions
# =============================================================================

def create_conversation_state(
    user_message: str,
    user_id: str,
    session_id: Optional[str] = None,
    user_context: Optional[UserContext] = None
) -> ConversationState:
    """
    Create a new conversation state object
    """
    
    return ConversationState(
        # Input
        user_message=user_message,
        user_id=user_id,
        session_id=session_id or str(uuid.uuid4()),
        message_id=str(uuid.uuid4()),
        timestamp=datetime.now().isoformat(),
        
        # Context
        user_context=user_context.to_dict() if user_context else {},
        conversation_history=[],
        
        # Intent and routing
        intent_classification=None,
        complexity_level="unknown",
        confidence_score=0.0,
        agents_to_invoke=[],
        
        # Agent results
        financial_analysis=None,
        risk_assessment=None,
        goal_analysis=None,
        portfolio_analysis=None,
        quick_response=None,
        
        # Accumulated results
        recommendations=[],
        insights=[],
        follow_up_questions=[],
        
        # Final response
        response_text="",
        response_metadata={},
        
        # System state
        processing_errors=[],
        agent_execution_times={},
        total_processing_time=0.0,
        api_costs={}
    )

def update_state_with_agent_result(
    state: ConversationState,
    result: AgentResult
) -> ConversationState:
    """
    Update conversation state with agent result
    """
    
    # Update agent-specific results
    if result.agent_name == "financial_analysis_agent":
        state["financial_analysis"] = result.analysis
    elif result.agent_name == "risk_assessment_agent":
        state["risk_assessment"] = result.analysis
    elif result.agent_name == "goal_planning_agent":
        state["goal_analysis"] = result.analysis
    elif result.agent_name == "portfolio_analysis_agent":
        state["portfolio_analysis"] = result.analysis
    elif result.agent_name == "quick_response_agent":
        state["quick_response"] = result.analysis
    
    # Accumulate results
    state["recommendations"].extend(result.recommendations)
    state["insights"].extend(result.insights)
    state["follow_up_questions"].extend(result.follow_up_questions)
    
    # Update metadata
    state["agent_execution_times"][result.agent_name] = result.execution_time
    state["api_costs"][result.agent_name] = result.api_cost
    
    # Handle errors
    if not result.success:
        state["processing_errors"].append(f"{result.agent_name}: {result.error_message}")
    
    return state

def calculate_overall_confidence(state: ConversationState) -> float:
    """
    Calculate overall confidence score based on agent results
    """
    
    confidence_scores = []
    
    # Collect confidence scores from successful agents
    for agent_name, execution_time in state["agent_execution_times"].items():
        if agent_name not in [error.split(":")[0] for error in state["processing_errors"]]:
            # Agent succeeded, add base confidence
            confidence_scores.append(0.8)
    
    # Factor in data quality and completeness
    if state["user_context"]:
        context_completeness = len(state["user_context"]) / 20  # Normalize to 0-1
        confidence_scores.append(min(1.0, context_completeness))
    
    # Calculate weighted average
    if confidence_scores:
        return sum(confidence_scores) / len(confidence_scores)
    else:
        return 0.0