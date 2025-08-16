"""
Lesson 1 Exercise: Clean Parallel Execution Demo
=================================================

🎓 CRITICAL LEARNING: Parallel execution in LangGraph requires careful state management!

This version properly handles parallel updates without conflicts.
"""

from typing import TypedDict, List, Optional, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
import asyncio
from datetime import datetime
import operator

class FinancialAnalysisState(TypedDict):
    """
    🎓 KEY INSIGHT: In parallel execution, each agent must update DIFFERENT fields
    or use Annotated fields that can be merged.
    
    Rule: If two agents run in parallel, they cannot update the same non-annotated field!
    """
    
    # Mergeable fields (can be updated by multiple agents)
    processing_steps: Annotated[List[str], operator.add]
    
    # Input data (set once, never changed)
    user_question: str
    account_balances: Dict[str, float]  
    monthly_income: float
    monthly_expenses: float
    
    # Conversation agent outputs (only it updates these)
    analysis_type: Optional[str]
    
    # Financial analyzer outputs (only it updates these)
    financial_summary: Optional[str]
    confidence_score: Optional[float]
    
    # Risk assessor outputs (only it updates these)  
    risk_score: Optional[int]
    risk_factors: Optional[List[str]]
    
    # Synthesizer outputs (only it updates these)
    final_recommendations: Optional[List[str]]
    final_response: Optional[str]

class ParallelAgentsDemo:
    """Clean implementation of parallel agents"""
    
    async def conversation_agent(self, state: Dict) -> Dict:
        """Entry point - runs alone, no parallel conflicts"""
        print("🤖 Conversation Agent: Analyzing question...")
        await asyncio.sleep(0.3)
        
        analysis_type = "home_purchase" if "house" in state["user_question"].lower() else "general"
        print(f"   ✅ Type: {analysis_type}")
        
        # Only update fields this agent owns
        return {
            "analysis_type": analysis_type,
            "processing_steps": [f"[CONVERSATION] Classified as {analysis_type}"]
        }
    
    async def financial_analyzer(self, state: Dict) -> Dict:
        """Parallel Agent 1 - only updates its own fields"""
        print("💰 Financial Analyzer: Processing...")
        await asyncio.sleep(1.0)  # Simulate work
        
        total = sum(state["account_balances"].values())
        savings = state["monthly_income"] - state["monthly_expenses"]
        
        summary = f"Assets: ${total:,.0f}, Monthly savings: ${savings:,.0f}"
        print("   ✅ Analysis complete")
        
        # Only return fields this agent owns
        return {
            "financial_summary": summary,
            "confidence_score": 0.85,
            "processing_steps": [f"[ANALYZER] Completed"]
        }
    
    async def risk_assessor(self, state: Dict) -> Dict:
        """Parallel Agent 2 - only updates its own fields"""
        print("⚠️  Risk Assessor: Evaluating...")
        await asyncio.sleep(0.8)  # Simulate work
        
        total = sum(state["account_balances"].values())
        months_covered = total / state["monthly_expenses"] if state["monthly_expenses"] > 0 else 0
        
        risk_score = 30 if months_covered > 6 else 70
        risk_factors = [
            f"Emergency fund: {months_covered:.1f} months",
            f"Savings rate: {((state['monthly_income']-state['monthly_expenses'])/state['monthly_income']*100):.0f}%"
        ]
        
        print(f"   ✅ Risk score: {risk_score}/100")
        
        # Only return fields this agent owns
        return {
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "processing_steps": [f"[RISK] Score: {risk_score}"]
        }
    
    async def synthesizer(self, state: Dict) -> Dict:
        """Combines outputs from parallel agents"""
        print("💡 Synthesizer: Combining results...")
        await asyncio.sleep(0.3)
        
        # Now we can safely read from both parallel agents
        recommendations = []
        
        if state.get("risk_score", 0) > 50:
            recommendations.append("⚠️ Address risk factors first")
        
        if "house" in state.get("analysis_type", ""):
            recommendations.append("🏠 Continue saving for down payment")
        
        recommendations.append("💰 Maintain emergency fund")
        
        response = f"""
Financial Summary: {state.get('financial_summary', 'N/A')}
Risk Score: {state.get('risk_score', 'N/A')}/100
Risk Factors: {', '.join(state.get('risk_factors', []))}

Recommendations:
{chr(10).join(f'  • {r}' for r in recommendations)}
"""
        
        print(f"   ✅ Generated {len(recommendations)} recommendations")
        
        return {
            "final_recommendations": recommendations,
            "final_response": response,
            "processing_steps": [f"[SYNTHESIZER] Combined results"]
        }

def create_clean_parallel_graph():
    """Creates a properly configured parallel graph"""
    
    agents = ParallelAgentsDemo()
    workflow = StateGraph(FinancialAnalysisState)
    
    # Add nodes
    workflow.add_node("conversation", agents.conversation_agent)
    workflow.add_node("analyzer", agents.financial_analyzer)
    workflow.add_node("risk", agents.risk_assessor)
    workflow.add_node("synthesizer", agents.synthesizer)
    
    # Define flow
    workflow.set_entry_point("conversation")
    
    # Parallel branches
    workflow.add_edge("conversation", "analyzer")
    workflow.add_edge("conversation", "risk")
    
    # Merge point
    workflow.add_edge("analyzer", "synthesizer")
    workflow.add_edge("risk", "synthesizer")
    
    workflow.add_edge("synthesizer", END)
    
    return workflow.compile()

async def run_demo():
    """Demonstrates clean parallel execution"""
    
    print("="*60)
    print("🎓 CLEAN PARALLEL EXECUTION")
    print("="*60)
    
    app = create_clean_parallel_graph()
    
    initial_state = {
        "user_question": "Should I buy a house?",
        "account_balances": {"Checking": 10000, "Savings": 30000},
        "monthly_income": 6000.0,
        "monthly_expenses": 4000.0,
        "processing_steps": [],
        # All optional fields start as None
        "analysis_type": None,
        "financial_summary": None,
        "confidence_score": None,
        "risk_score": None,
        "risk_factors": None,
        "final_recommendations": None,
        "final_response": None
    }
    
    print("\n⏱️  Starting timer...")
    start = datetime.now()
    
    print("\n🚀 Executing graph...")
    print("-" * 40)
    
    result = await app.ainvoke(initial_state)
    
    duration = (datetime.now() - start).total_seconds()
    
    print("-" * 40)
    print(f"✅ Complete in {duration:.1f}s")
    
    print("\n📊 FINAL RESULT:")
    print(result.get("final_response", "No response"))
    
    print("\n🔍 Execution trace:")
    for step in result.get("processing_steps", []):
        print(f"  {step}")
    
    print("\n" + "="*60)
    print("🎓 WHAT WE LEARNED:")
    print("="*60)
    print("""
    1. PARALLEL SAFETY:
       • Each agent updates ONLY its own fields
       • No conflicts possible
       • Clean, predictable execution
    
    2. PERFORMANCE GAIN:
       • Analyzer (1.0s) and Risk (0.8s) ran simultaneously
       • Total ≈ 1.0s instead of 1.8s sequential
    
    3. BEST PRACTICES:
       • Design state schema carefully
       • Assign clear ownership of fields
       • Use Annotated for shared fields
       • Test parallel paths thoroughly
    """)

if __name__ == "__main__":
    asyncio.run(run_demo())

"""
🎓 HOMEWORK QUESTIONS:

1. What would happen if both parallel agents tried to update 'confidence_score'?
2. How would you add a third parallel agent without conflicts?
3. When is parallel execution NOT appropriate?
4. How would you handle one parallel agent failing?

Next lesson: Conditional routing and dynamic flows!
"""