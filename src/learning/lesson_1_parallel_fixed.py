"""
Lesson 1 Exercise: Parallel Agents (Fixed Version)
===================================================

🎓 LEARNING POINT: Handling Parallel Execution in LangGraph

This demonstrates a critical concept: when agents run in parallel,
they can't update the same state fields unless we tell LangGraph
how to merge the updates!
"""

from typing import TypedDict, List, Optional, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
import asyncio
from datetime import datetime
import operator

# State with proper annotations for parallel updates
class FinancialAnalysisState(TypedDict):
    """
    🎓 LEARNING POINT: Annotated Fields for Parallel Updates
    
    When multiple agents might update the same field:
    - Use Annotated[type, reducer] syntax
    - operator.add: Appends lists together
    - Custom reducers: Can define your own merge logic
    
    This prevents the "InvalidUpdateError" we saw!
    """
    
    # Fields that can be updated in parallel
    processing_steps: Annotated[List[str], operator.add]  # Merge by appending
    
    # Single-update fields (only one agent touches these)
    user_question: str
    account_balances: Dict[str, float]
    monthly_income: Optional[float]
    monthly_expenses: Optional[float]
    
    # Analyzer outputs
    financial_summary: Optional[str]
    analysis_complete: bool
    analysis_type: Optional[str]
    confidence_score: Optional[float]
    
    # Risk assessor outputs
    risk_score: Optional[float]
    risk_factors: Optional[List[str]]
    risk_summary: Optional[str]
    
    # Final recommendations
    recommendations: Optional[List[str]]
    
    # Messages (simplified for this demo)
    messages: List[str]

class ParallelAgentsDemo:
    """Demonstrates parallel agent execution"""
    
    async def conversation_agent(self, state: FinancialAnalysisState) -> FinancialAnalysisState:
        """Entry point - classifies the question"""
        print("🤖 Conversation Agent: Starting...")
        await asyncio.sleep(0.3)
        
        # Determine analysis type
        question_lower = state["user_question"].lower()
        if "house" in question_lower or "mortgage" in question_lower:
            analysis_type = "home_purchase"
        elif "invest" in question_lower:
            analysis_type = "investment"
        else:
            analysis_type = "general"
        
        print(f"   ✅ Classified as: {analysis_type}")
        
        return {
            **state,
            "analysis_type": analysis_type,
            "processing_steps": [f"[CONVERSATION] Classified as {analysis_type}"],
            "messages": state["messages"] + [f"User: {state['user_question']}"]
        }
    
    async def financial_analyzer(self, state: FinancialAnalysisState) -> FinancialAnalysisState:
        """
        🎓 PARALLEL AGENT 1: Financial Analysis
        Runs at the same time as risk assessment!
        """
        print("💰 Financial Analyzer: Running analysis...")
        await asyncio.sleep(1.0)  # Simulate processing
        
        total = sum(state["account_balances"].values())
        monthly_savings = state["monthly_income"] - state["monthly_expenses"]
        
        if state.get("analysis_type") == "home_purchase":
            summary = f"With ${total:,.0f} saved and ${monthly_savings:,.0f}/month surplus, you can afford a ${total*5:,.0f} home."
        else:
            summary = f"Total assets: ${total:,.0f}, Monthly savings: ${monthly_savings:,.0f}"
        
        print("   ✅ Financial analysis complete")
        
        return {
            **state,
            "financial_summary": summary,
            "analysis_complete": True,
            "confidence_score": 0.85,
            "processing_steps": [f"[ANALYZER] Completed financial analysis"]
        }
    
    async def risk_assessor(self, state: FinancialAnalysisState) -> FinancialAnalysisState:
        """
        🎓 PARALLEL AGENT 2: Risk Assessment
        Runs at the same time as financial analyzer!
        """
        print("⚠️  Risk Assessor: Evaluating risks...")
        await asyncio.sleep(0.8)  # Simulate processing
        
        risk_factors = []
        risk_score = 50
        
        # Check emergency fund
        total = sum(state["account_balances"].values())
        monthly_expenses = state["monthly_expenses"]
        
        if monthly_expenses > 0:
            months_covered = total / monthly_expenses
            if months_covered < 3:
                risk_factors.append("Low emergency fund")
                risk_score += 30
            elif months_covered < 6:
                risk_factors.append("Moderate emergency fund")
                risk_score += 10
            else:
                risk_factors.append("Good emergency fund")
                risk_score -= 10
        
        # Check savings rate
        if state["monthly_income"] > 0:
            savings_rate = (state["monthly_income"] - monthly_expenses) / state["monthly_income"]
            if savings_rate < 0.1:
                risk_factors.append("Low savings rate")
                risk_score += 20
            elif savings_rate > 0.2:
                risk_factors.append("Excellent savings rate")
                risk_score -= 20
        
        risk_score = max(0, min(100, risk_score))
        
        print(f"   ✅ Risk assessment complete (Score: {risk_score}/100)")
        
        return {
            **state,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "risk_summary": f"Risk Level: {'HIGH' if risk_score > 70 else 'MODERATE' if risk_score > 40 else 'LOW'}",
            "processing_steps": [f"[RISK] Assessed risk score: {risk_score}/100"]
        }
    
    async def recommendation_synthesizer(self, state: FinancialAnalysisState) -> FinancialAnalysisState:
        """
        🎓 SYNTHESIS AGENT: Combines outputs from parallel agents
        
        This agent waits for BOTH parallel agents to complete,
        then synthesizes their outputs into final recommendations.
        """
        print("💡 Synthesizer: Creating recommendations from parallel analyses...")
        await asyncio.sleep(0.5)
        
        recommendations = []
        
        # Use financial analysis results
        if state.get("analysis_complete"):
            if "home" in state.get("financial_summary", "").lower():
                recommendations.append("🏠 Continue saving for down payment")
        
        # Use risk assessment results
        risk_score = state.get("risk_score", 50)
        if risk_score > 70:
            recommendations.insert(0, "⚠️ PRIORITY: Reduce financial risks first")
        
        for factor in state.get("risk_factors", []):
            if "emergency" in factor.lower() and "low" in factor.lower():
                recommendations.append("💰 Build emergency fund to 6 months expenses")
            elif "savings rate" in factor.lower() and "excellent" in factor.lower():
                recommendations.append("✅ Maintain excellent savings rate")
        
        # Add confidence-based recommendation
        if state.get("confidence_score", 0) < 0.7:
            recommendations.append("📊 Consider professional financial advice")
        
        print(f"   ✅ Generated {len(recommendations)} recommendations")
        
        response = f"""
Analysis Summary:
{state.get('financial_summary', 'N/A')}

Risk Assessment: {state.get('risk_summary', 'N/A')}
Risk Factors: {', '.join(state.get('risk_factors', []))}

Recommendations:
""" + "\n".join(f"  {r}" for r in recommendations)
        
        return {
            **state,
            "recommendations": recommendations,
            "messages": state["messages"] + [f"Assistant: {response}"],
            "processing_steps": [f"[SYNTHESIZER] Created {len(recommendations)} recommendations"]
        }

def create_parallel_graph():
    """
    🎓 GRAPH STRUCTURE: Parallel Execution Pattern
    
    Entry → Parallel Branch → Synthesis → End
            ├─ Analyzer ─┤
            └─ Risk ─────┘
    """
    
    agents = ParallelAgentsDemo()
    workflow = StateGraph(FinancialAnalysisState)
    
    # Add nodes
    workflow.add_node("conversation", agents.conversation_agent)
    workflow.add_node("analyzer", agents.financial_analyzer)
    workflow.add_node("risk", agents.risk_assessor)
    workflow.add_node("synthesizer", agents.recommendation_synthesizer)
    
    # Define flow with PARALLEL branches
    workflow.set_entry_point("conversation")
    
    # Both run in parallel after conversation
    workflow.add_edge("conversation", "analyzer")
    workflow.add_edge("conversation", "risk")
    
    # Both feed into synthesizer
    workflow.add_edge("analyzer", "synthesizer")
    workflow.add_edge("risk", "synthesizer")
    
    # End after synthesis
    workflow.add_edge("synthesizer", END)
    
    return workflow.compile()

async def demonstrate_parallel_execution():
    """Shows how parallel agents work"""
    
    print("="*60)
    print("🎓 PARALLEL EXECUTION DEMONSTRATION")
    print("="*60)
    
    print("""
    Graph Structure:
    
         [Conversation]
              ↓
         ┌────┴────┐
         ↓         ↓
    [Analyzer]  [Risk]     ← These run IN PARALLEL!
         ↓         ↓
         └────┬────┘
              ↓
        [Synthesizer]      ← Waits for BOTH
              ↓
            [END]
    """)
    
    app = create_parallel_graph()
    
    # Test data
    test_state = {
        "user_question": "Should I buy a house next year?",
        "account_balances": {
            "Checking": 15000,
            "Savings": 25000,
            "Investment": 10000
        },
        "monthly_income": 7000,
        "monthly_expenses": 5000,
        "processing_steps": [],
        "messages": [],
        # All other fields will be None initially
        "financial_summary": None,
        "analysis_complete": False,
        "analysis_type": None,
        "confidence_score": None,
        "risk_score": None,
        "risk_factors": None,
        "risk_summary": None,
        "recommendations": None
    }
    
    print("🚀 Starting parallel execution...")
    print("   Watch the timing - analyzer and risk run simultaneously!")
    print("-" * 40)
    
    start_time = datetime.now()
    
    # Run the graph
    result = await app.ainvoke(test_state)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("-" * 40)
    print(f"⏱️  Total execution time: {duration:.1f} seconds")
    print("   (Notice it's faster than sequential would be!)")
    
    print("\n📊 RESULTS:")
    print("-" * 40)
    print(f"Risk Score: {result.get('risk_score')}/100")
    print(f"Confidence: {result.get('confidence_score', 0):.0%}")
    print(f"\nRecommendations:")
    for rec in result.get("recommendations", []):
        print(f"  {rec}")
    
    print("\n🔍 Execution Order (from processing_steps):")
    for step in result.get("processing_steps", []):
        print(f"  {step}")
    
    print("\n" + "="*60)
    print("🎓 KEY LEARNING POINTS:")
    print("="*60)
    print("""
    1. PARALLEL EXECUTION:
       - Analyzer and Risk ran at the SAME TIME
       - Total time ≈ max(analyzer_time, risk_time), not sum
       - Synthesizer waited for BOTH to complete
    
    2. STATE MERGING:
       - processing_steps used Annotated[List, operator.add]
       - This allowed both parallel agents to add steps
       - Without annotation, we'd get InvalidUpdateError
    
    3. SYNTHESIS PATTERN:
       - Synthesizer had access to outputs from BOTH agents
       - Could make decisions based on combined information
       - More comprehensive than sequential processing
    
    4. WHEN TO USE PARALLEL:
       - When agents don't depend on each other
       - When you want faster execution
       - When combining multiple perspectives
    """)

async def show_sequential_comparison():
    """Shows the difference in execution time"""
    
    print("\n" + "="*60)
    print("⏱️  PERFORMANCE COMPARISON")
    print("="*60)
    
    print("""
    Sequential Execution (traditional):
    Conversation (0.3s) → Analyzer (1.0s) → Risk (0.8s) → Synthesizer (0.5s)
    Total: 2.6 seconds
    
    Parallel Execution (what we just did):
    Conversation (0.3s) → [Analyzer (1.0s) || Risk (0.8s)] → Synthesizer (0.5s)
    Total: 1.8 seconds (saved 0.8s!)
    
    Imagine with real API calls:
    - Each agent might take 2-3 seconds
    - Parallel execution could save 50% of time!
    """)

if __name__ == "__main__":
    asyncio.run(demonstrate_parallel_execution())
    asyncio.run(show_sequential_comparison())

"""
🎓 EXERCISE CHALLENGES:

1. Add a third parallel agent:
   - Create a "Tax Implications Agent"
   - Make it run in parallel with Analyzer and Risk
   - Have Synthesizer use all three outputs

2. Implement conditional parallelism:
   - Only run Risk agent if total balance > $10,000
   - Use add_conditional_edges instead of add_edge

3. Handle agent failures:
   - What if Risk agent fails?
   - Should Synthesizer still run?
   - How to handle partial results?

4. Create a reducer for complex merging:
   - Instead of operator.add, create custom merge logic
   - Example: Keep only unique processing steps
"""