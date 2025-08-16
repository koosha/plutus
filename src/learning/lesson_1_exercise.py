"""
Lesson 1 Exercise: Adding a Risk Assessment Agent
==================================================

🎓 LEARNING EXERCISE: Let's extend our graph with a new agent!

This exercise teaches:
1. How to add new agents to existing graphs
2. Parallel execution patterns
3. State merging from multiple agents
"""

from typing import TypedDict, List, Optional, Dict, Any, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage
import asyncio
from datetime import datetime
import operator

# Extended state with risk assessment
class FinancialAnalysisState(TypedDict):
    # 🎓 LEARNING POINT: Annotated fields for parallel updates!
    # When multiple agents update the same field in parallel,
    # we need to tell LangGraph how to merge them
    messages: Annotated[Sequence[BaseMessage], operator.add]  # Messages append
    processing_steps: Annotated[List[str], operator.add]  # Steps append
    
    # Single-value fields (only one agent updates these)
    user_question: str
    account_balances: Dict[str, float]
    monthly_income: Optional[float]
    monthly_expenses: Optional[float]
    financial_summary: Optional[str]
    analysis_complete: bool
    recommendations: List[str]
    analysis_type: Optional[str]
    confidence_score: Optional[float]
    # NEW FIELDS for risk assessment
    risk_score: Optional[float]  # 0-100 scale
    risk_factors: List[str]
    risk_summary: Optional[str]

class RiskAssessmentAgent:
    """
    🎓 NEW AGENT: Risk Assessment
    
    This agent evaluates financial risks:
    - Emergency fund adequacy
    - Debt-to-income ratio
    - Investment diversification
    - Cash flow stability
    """
    
    async def assess_risk(self, state: FinancialAnalysisState) -> FinancialAnalysisState:
        print("⚠️  Risk Assessment Agent: Evaluating financial risks...")
        
        # Track processing - for parallel execution, we return NEW list
        new_steps = [f"[{datetime.now().strftime('%H:%M:%S')}] Risk Assessment started"]
        
        # Calculate risk factors
        risk_factors = []
        risk_score = 50  # Start neutral
        
        total_balance = sum(state["account_balances"].values())
        monthly_expenses = state.get("monthly_expenses", 0)
        monthly_income = state.get("monthly_income", 0)
        monthly_savings = monthly_income - monthly_expenses
        
        # Factor 1: Emergency Fund
        if monthly_expenses > 0:
            months_covered = total_balance / monthly_expenses
            if months_covered < 3:
                risk_factors.append("❌ Emergency fund less than 3 months")
                risk_score += 20
            elif months_covered < 6:
                risk_factors.append("⚠️ Emergency fund 3-6 months")
                risk_score += 10
            else:
                risk_factors.append("✅ Emergency fund 6+ months")
                risk_score -= 10
        
        # Factor 2: Savings Rate
        if monthly_income > 0:
            savings_rate = monthly_savings / monthly_income
            if savings_rate < 0.1:
                risk_factors.append("❌ Savings rate below 10%")
                risk_score += 15
            elif savings_rate < 0.2:
                risk_factors.append("⚠️ Savings rate 10-20%")
                risk_score += 5
            else:
                risk_factors.append("✅ Savings rate above 20%")
                risk_score -= 15
        
        # Factor 3: Asset Allocation
        checking_pct = state["account_balances"].get("Checking", 0) / total_balance
        if checking_pct > 0.5:
            risk_factors.append("⚠️ Too much in low-yield checking")
            risk_score += 10
        
        investment_pct = state["account_balances"].get("Investment", 0) / total_balance
        if investment_pct < 0.3:
            risk_factors.append("⚠️ Low investment allocation")
            risk_score += 5
        
        # Bound risk score
        risk_score = max(0, min(100, risk_score))
        
        # Generate risk summary
        if risk_score < 30:
            risk_level = "LOW"
            risk_summary = "Your financial risk profile is healthy with good emergency reserves and savings habits."
        elif risk_score < 60:
            risk_level = "MODERATE"
            risk_summary = "Your financial risk is manageable but there are areas for improvement."
        else:
            risk_level = "HIGH"
            risk_summary = "Your financial situation has elevated risk factors that should be addressed."
        
        risk_summary = f"""
🎯 Risk Level: {risk_level} ({risk_score}/100)

{risk_summary}

Key Risk Factors:
""" + "\n".join(risk_factors)
        
        # Simulate processing time
        await asyncio.sleep(0.5)
        
        # Update state
        new_state = dict(state)
        new_state.update({
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "risk_summary": risk_summary,
            "processing_steps": new_steps + [
                f"[{datetime.now().strftime('%H:%M:%S')}] Risk Assessment completed (Score: {risk_score}/100)"
            ]
        })
        
        print(f"   ✅ Risk assessment complete (Score: {risk_score}/100)")
        
        return new_state

# Import our existing agents
from lesson_1_basic_agent_simulated import FinancialAnalysisAgent, SimulatedClaude

class EnhancedRecommendationAgent:
    """
    🎓 ENHANCED AGENT: Recommendations with Risk Consideration
    
    This shows how agents can use outputs from multiple other agents!
    """
    
    async def generate_risk_aware_recommendations(self, state: FinancialAnalysisState) -> FinancialAnalysisState:
        print("💡 Enhanced Recommendation Agent: Generating risk-aware advice...")
        
        # For the final agent, we can still append since it's not parallel
        new_steps = [f"[{datetime.now().strftime('%H:%M:%S')}] Enhanced Recommendations started"]
        
        recommendations = []
        
        # Base recommendations from original analysis
        if "house" in state["user_question"].lower():
            recommendations.extend([
                "🏠 Continue saving for your house down payment",
                "💳 Monitor and improve your credit score"
            ])
        
        # Add risk-based recommendations
        risk_score = state.get("risk_score", 50)
        
        if risk_score > 60:
            recommendations.insert(0, "🚨 PRIORITY: Address high-risk factors before major purchases")
        
        for factor in state.get("risk_factors", []):
            if "Emergency fund" in factor and "❌" in factor:
                recommendations.append("💰 BUILD: Increase emergency fund to 6 months expenses")
            elif "Savings rate" in factor and "❌" in factor:
                recommendations.append("📊 IMPROVE: Increase savings rate to at least 20%")
            elif "checking" in factor.lower():
                recommendations.append("📈 OPTIMIZE: Move excess checking funds to high-yield savings")
        
        # Add confidence-adjusted disclaimer
        confidence = state.get("confidence_score", 0.5)
        if confidence < 0.8:
            recommendations.append("ℹ️ NOTE: Consider consulting a financial advisor for personalized guidance")
        
        await asyncio.sleep(0.5)
        
        # Update state
        new_state = dict(state)
        new_state.update({
            "recommendations": recommendations,
            "processing_steps": new_steps + [
                f"[{datetime.now().strftime('%H:%M:%S')}] Generated {len(recommendations)} risk-aware recommendations"
            ]
        })
        
        print(f"   ✅ Generated {len(recommendations)} risk-aware recommendations")
        
        return new_state

def create_enhanced_graph():
    """
    🎓 LEARNING POINT: Graph with Parallel Execution
    
    This graph shows:
    1. Multiple agents running in parallel
    2. State merging from parallel branches
    3. Enhanced decision making with multiple inputs
    """
    
    # Initialize agents
    base_agent = FinancialAnalysisAgent()
    risk_agent = RiskAssessmentAgent()
    enhanced_rec_agent = EnhancedRecommendationAgent()
    
    # Create graph
    workflow = StateGraph(FinancialAnalysisState)
    
    # Add nodes
    workflow.add_node("conversation", base_agent.conversation_agent)
    workflow.add_node("analyzer", base_agent.financial_analyzer)
    workflow.add_node("risk_assessment", risk_agent.assess_risk)  # NEW!
    workflow.add_node("recommendations", enhanced_rec_agent.generate_risk_aware_recommendations)  # ENHANCED!
    
    # Define flow with PARALLEL execution
    workflow.set_entry_point("conversation")
    workflow.add_edge("conversation", "analyzer")
    workflow.add_edge("conversation", "risk_assessment")  # PARALLEL PATH!
    
    # Both analyzer and risk_assessment feed into recommendations
    workflow.add_edge("analyzer", "recommendations")
    workflow.add_edge("risk_assessment", "recommendations")
    workflow.add_edge("recommendations", END)
    
    app = workflow.compile()
    
    print("\n🏗️  Enhanced Graph Architecture:")
    print("┌─────────────┐")
    print("│ Conversation│ (Entry Point)")
    print("└──────┬──────┘")
    print("       ├────────────┐")
    print("       ↓            ↓")
    print("┌─────────┐  ┌──────────────┐")
    print("│Analyzer │  │Risk Assessment│ (PARALLEL!)")
    print("└────┬────┘  └──────┬───────┘")
    print("     └──────┬───────┘")
    print("            ↓")
    print("  ┌──────────────────┐")
    print("  │  Recommendations  │ (Merges both inputs)")
    print("  └─────────┬────────┘")
    print("            ↓")
    print("          [END]")
    
    return app

async def run_enhanced_demo():
    """Run the enhanced multiagent system"""
    
    print("="*60)
    print("🎓 LESSON 1 EXERCISE: Enhanced Multiagent System")
    print("="*60)
    
    app = create_enhanced_graph()
    
    # Test data
    test_scenarios = [
        {
            "name": "High Risk Profile",
            "data": {
                "account_balances": {"Checking": 25000.00, "Savings": 2000.00, "Investment": 3000.00},
                "monthly_income": 6000.00,
                "monthly_expenses": 5500.00  # Low savings rate!
            },
            "question": "I want to buy a house in 2 years. Am I ready?"
        },
        {
            "name": "Low Risk Profile",
            "data": {
                "account_balances": {"Checking": 5000.00, "Savings": 25000.00, "Investment": 30000.00},
                "monthly_income": 6000.00,
                "monthly_expenses": 3500.00  # High savings rate!
            },
            "question": "Should I invest more aggressively?"
        }
    ]
    
    # Run first scenario
    scenario = test_scenarios[0]
    print(f"\n📋 Scenario: {scenario['name']}")
    print(f"💭 Question: {scenario['question']}")
    
    initial_state = {
        "messages": [],  # Will be converted to BaseMessage by agents
        "user_question": scenario["question"],
        "account_balances": scenario["data"]["account_balances"],
        "monthly_income": scenario["data"]["monthly_income"],
        "monthly_expenses": scenario["data"]["monthly_expenses"],
        "financial_summary": None,
        "analysis_complete": False,
        "recommendations": [],
        "analysis_type": None,
        "confidence_score": None,
        "processing_steps": [],
        "risk_score": None,
        "risk_factors": [],
        "risk_summary": None
    }
    
    print("\n🚀 Running Enhanced Analysis...")
    print("-" * 40)
    
    final_state = await app.ainvoke(initial_state)
    
    # Display results
    print("\n" + "="*60)
    print("📊 ENHANCED ANALYSIS RESULTS")
    print("="*60)
    
    print(f"\n🎯 Analysis Type: {final_state['analysis_type']}")
    print(f"📈 Confidence: {final_state.get('confidence_score', 0):.0%}")
    print(f"⚠️  Risk Score: {final_state.get('risk_score', 'N/A')}/100")
    
    print(f"\n{final_state.get('risk_summary', 'No risk assessment')}")
    
    print(f"\n💡 Risk-Aware Recommendations:")
    print("-" * 30)
    for rec in final_state.get('recommendations', []):
        print(f"  {rec}")
    
    print("\n🔍 Execution Timeline:")
    print("-" * 30)
    for step in final_state.get('processing_steps', []):
        print(f"  {step}")
    
    print("\n" + "="*60)
    print("🎓 LEARNING INSIGHTS")
    print("="*60)
    print("""
    Notice how:
    1. Risk Assessment ran IN PARALLEL with Financial Analyzer
    2. Recommendations agent waited for BOTH to complete
    3. Final recommendations incorporated risk factors
    4. State accumulated data from all agents
    
    This is the power of multiagent systems:
    - Parallel processing for efficiency
    - Specialized analysis from each agent
    - Comprehensive output from merged insights
    """)

if __name__ == "__main__":
    asyncio.run(run_enhanced_demo())

"""
🎓 KEY LEARNING POINTS FROM THIS EXERCISE:

1. PARALLEL EXECUTION:
   - Multiple agents can run simultaneously
   - Graph waits for all inputs before proceeding
   - Improves performance for independent tasks

2. STATE MERGING:
   - Multiple agents can write to the same state
   - Later agents can read outputs from all previous agents
   - Enables comprehensive decision making

3. AGENT SPECIALIZATION:
   - Risk Assessment focuses only on risk
   - Doesn't need to know about home purchase logic
   - Can be reused in other contexts

4. EXTENSIBILITY:
   - Easy to add new agents without breaking existing ones
   - Graph structure makes dependencies clear
   - Can test new agents in isolation

CHALLENGE: Can you add a "Tax Optimization Agent" that runs in parallel too?
"""