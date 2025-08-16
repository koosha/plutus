"""
Lesson 2: Conditional Routing and Dynamic Agent Selection
=========================================================

🎓 LEARNING OBJECTIVES:
1. Understand conditional routing vs fixed flows
2. Learn how to make dynamic decisions in graphs
3. Implement intelligent agent selection
4. Handle different complexity levels automatically

This is where LangGraph becomes MUCH more powerful than traditional chains!
"""

from typing import TypedDict, List, Optional, Dict, Any, Literal
from langgraph.graph import StateGraph, END
import asyncio
from datetime import datetime

class SmartFinancialState(TypedDict):
    """
    🎓 LEARNING POINT: State Design for Conditional Routing
    
    Notice the new fields that help with routing decisions:
    - complexity_level: Determines which agents to use
    - requires_deep_analysis: Boolean flag for routing
    - user_profile: Affects which recommendations to give
    """
    
    # Input data
    user_question: str
    account_balances: Dict[str, float]
    monthly_income: float
    monthly_expenses: float
    user_profile: Dict[str, Any]  # New: affects routing
    
    # Classification outputs
    question_type: Optional[str]
    complexity_level: Optional[Literal["simple", "moderate", "complex"]]
    requires_deep_analysis: Optional[bool]
    
    # Analysis outputs
    basic_analysis: Optional[str]
    detailed_analysis: Optional[str]
    risk_assessment: Optional[str]
    market_context: Optional[str]
    
    # Final outputs
    recommendations: Optional[List[str]]
    confidence_score: Optional[float]
    
    # Execution tracking
    agents_used: List[str]
    execution_path: List[str]

class ConditionalRoutingDemo:
    """
    🎓 DEMONSTRATES: How agents make intelligent routing decisions
    """
    
    async def question_classifier(self, state: Dict) -> Dict:
        """
        🎓 ROUTING AGENT: Makes decisions about the execution path
        
        This is the "traffic controller" of your multiagent system.
        It decides which agents are needed based on:
        - Question complexity
        - User profile
        - Available data
        """
        
        print("🧭 Question Classifier: Analyzing complexity...")
        await asyncio.sleep(0.3)
        
        question = state["user_question"].lower()
        user_profile = state.get("user_profile", {})
        
        # Determine question type
        if any(word in question for word in ["house", "mortgage", "buy", "purchase"]):
            question_type = "major_purchase"
        elif any(word in question for word in ["invest", "portfolio", "stocks", "bonds"]):
            question_type = "investment"
        elif any(word in question for word in ["budget", "save", "spend"]):
            question_type = "budgeting"
        elif any(word in question for word in ["retire", "pension", "401k"]):
            question_type = "retirement"
        else:
            question_type = "general"
        
        # Determine complexity based on multiple factors
        complexity_factors = 0
        
        # Factor 1: Question type complexity
        complex_types = ["major_purchase", "investment", "retirement"]
        if question_type in complex_types:
            complexity_factors += 2
        
        # Factor 2: User experience level
        experience = user_profile.get("financial_experience", "beginner")
        if experience == "advanced":
            complexity_factors += 1  # Advanced users can handle complex analysis
        elif experience == "beginner":
            complexity_factors -= 1  # Beginners need simpler explanations
        
        # Factor 3: Portfolio size
        total_assets = sum(state["account_balances"].values())
        if total_assets > 100000:
            complexity_factors += 2  # High net worth = more complex needs
        elif total_assets < 10000:
            complexity_factors -= 1  # Lower assets = simpler needs
        
        # Factor 4: Question length/detail
        if len(state["user_question"]) > 100:
            complexity_factors += 1  # Detailed questions = complex needs
        
        # Determine final complexity
        if complexity_factors >= 4:
            complexity_level = "complex"
            requires_deep_analysis = True
        elif complexity_factors >= 2:
            complexity_level = "moderate"
            requires_deep_analysis = False
        else:
            complexity_level = "simple"
            requires_deep_analysis = False
        
        print(f"   ✅ Type: {question_type}, Complexity: {complexity_level}")
        print(f"   📊 Complexity factors: {complexity_factors}")
        print(f"   🔍 Deep analysis needed: {requires_deep_analysis}")
        
        return {
            "question_type": question_type,
            "complexity_level": complexity_level,
            "requires_deep_analysis": requires_deep_analysis,
            "agents_used": ["classifier"],
            "execution_path": [f"CLASSIFIED: {question_type} ({complexity_level})"]
        }
    
    async def basic_analyzer(self, state: Dict) -> Dict:
        """
        🎓 ALWAYS RUNS: Basic analysis for all questions
        
        This agent provides fundamental analysis that every
        financial question needs, regardless of complexity.
        """
        
        print("📊 Basic Analyzer: Performing core analysis...")
        await asyncio.sleep(0.8)
        
        total_assets = sum(state["account_balances"].values())
        monthly_savings = state["monthly_income"] - state["monthly_expenses"]
        savings_rate = monthly_savings / state["monthly_income"] if state["monthly_income"] > 0 else 0
        
        analysis = f"""
            🔍 BASIC FINANCIAL ANALYSIS:
            • Total Assets: ${total_assets:,.2f}
            • Monthly Savings: ${monthly_savings:,.2f}
            • Savings Rate: {savings_rate:.1%}
            • Financial Health: {'Strong' if savings_rate > 0.2 else 'Moderate' if savings_rate > 0.1 else 'Needs Improvement'}
            """
        
        # Calculate basic confidence
        confidence = 0.6  # Base confidence for basic analysis
        if total_assets > 0:
            confidence += 0.1
        if monthly_savings > 0:
            confidence += 0.1
        
        print("   ✅ Basic analysis complete")
        
        return {
            "basic_analysis": analysis,
            "confidence_score": confidence,
            "agents_used": state.get("agents_used", []) + ["basic_analyzer"],
            "execution_path": state.get("execution_path", []) + ["BASIC ANALYSIS completed"]
        }
    
    async def detailed_analyzer(self, state: Dict) -> Dict:
        """
        🎓 CONDITIONAL AGENT: Only runs for moderate/complex questions
        
        This demonstrates how some agents only run when needed,
        saving compute time and providing appropriate depth.
        """
        
        print("🔬 Detailed Analyzer: Deep dive analysis...")
        await asyncio.sleep(1.5)  # More time for detailed work
        
        question_type = state["question_type"]
        total_assets = sum(state["account_balances"].values())
        monthly_savings = state["monthly_income"] - state["monthly_expenses"]
        
        # Type-specific detailed analysis
        if question_type == "major_purchase":
            # Home buying analysis
            down_payment_potential = total_assets * 0.8  # Keep some for emergency
            affordable_home = down_payment_potential * 5  # 20% down payment rule
            
            analysis = f"""
🏠 DETAILED HOME PURCHASE ANALYSIS:
• Down Payment Available: ${down_payment_potential:,.0f}
• Affordable Home Price: ${affordable_home:,.0f}
• Time to Save Additional 20%: {(affordable_home * 0.04) / monthly_savings:.1f} months
• Recommended Emergency Reserve: ${state['monthly_expenses'] * 6:,.0f}
• Post-Purchase Monthly Budget Impact: ~${affordable_home * 0.005:,.0f}/month (est. mortgage)
"""
        
        elif question_type == "investment":
            # Investment analysis
            investable_assets = total_assets - (state["monthly_expenses"] * 6)  # Keep emergency fund
            risk_capacity = "High" if monthly_savings > 2000 else "Moderate" if monthly_savings > 1000 else "Conservative"
            
            analysis = f"""
💰 DETAILED INVESTMENT ANALYSIS:
• Investable Assets: ${max(0, investable_assets):,.0f}
• Risk Capacity: {risk_capacity}
• Recommended Portfolio Allocation:
  - Emergency Fund: ${state['monthly_expenses'] * 6:,.0f}
  - Conservative (Bonds): {30 if risk_capacity == 'Conservative' else 20 if risk_capacity == 'Moderate' else 10}%
  - Growth (Stocks): {70 if risk_capacity == 'Conservative' else 80 if risk_capacity == 'Moderate' else 90}%
• Monthly Investment Capacity: ${monthly_savings * 0.8:,.0f}
"""
        
        else:
            # General detailed analysis
            net_worth = total_assets  # Simplified (no liabilities in our demo)
            analysis = f"""
📈 DETAILED FINANCIAL ANALYSIS:
• Net Worth: ${net_worth:,.0f}
• Liquidity Ratio: {total_assets / (state['monthly_expenses'] * 3):.1f}x (target: 2.0x+)
• Savings Momentum: ${monthly_savings * 12:,.0f}/year
• Financial Independence Progress: {(net_worth / (state['monthly_expenses'] * 300)):.1%}
• Recommended Next Steps: Focus on {'debt reduction' if monthly_savings < 1000 else 'investment growth'}
"""
        
        print("   ✅ Detailed analysis complete")
        
        # Calculate confidence boost
        current_confidence = state.get("confidence_score") or 0.6
        new_confidence = current_confidence + 0.2
        
        return {
            "detailed_analysis": analysis,
            "confidence_score": new_confidence,
            "agents_used": state.get("agents_used", []) + ["detailed_analyzer"],
            "execution_path": state.get("execution_path", []) + ["DETAILED ANALYSIS completed"]
        }
    
    async def risk_assessor(self, state: Dict) -> Dict:
        """
        🎓 CONDITIONAL AGENT: Only runs for complex questions
        
        Risk assessment is computationally expensive and only needed
        for major financial decisions.
        """
        
        print("⚠️  Risk Assessor: Evaluating financial risks...")
        await asyncio.sleep(1.0)
        
        risks = []
        risk_score = 50  # Neutral starting point
        
        total_assets = sum(state["account_balances"].values())
        monthly_expenses = state["monthly_expenses"]
        monthly_savings = state["monthly_income"] - monthly_expenses
        
        # Emergency fund risk
        emergency_fund_months = total_assets / monthly_expenses if monthly_expenses > 0 else 0
        if emergency_fund_months < 3:
            risks.append("🚨 Critical: Emergency fund below 3 months")
            risk_score += 30
        elif emergency_fund_months < 6:
            risks.append("⚠️ Moderate: Emergency fund below 6 months")
            risk_score += 15
        else:
            risks.append("✅ Good: Emergency fund adequate")
            risk_score -= 10
        
        # Income stability risk
        if monthly_savings < 0:
            risks.append("🚨 Critical: Spending exceeds income")
            risk_score += 40
        elif monthly_savings / state["monthly_income"] < 0.1:
            risks.append("⚠️ Moderate: Low savings rate")
            risk_score += 20
        else:
            risks.append("✅ Good: Healthy savings rate")
            risk_score -= 15
        
        # Asset diversification risk (simplified)
        checking_ratio = state["account_balances"].get("Checking", 0) / total_assets if total_assets > 0 else 0
        if checking_ratio > 0.5:
            risks.append("⚠️ Moderate: Too much cash in checking")
            risk_score += 10
        
        risk_score = max(0, min(100, risk_score))
        
        assessment = f"""
⚠️ RISK ASSESSMENT:
• Overall Risk Score: {risk_score}/100 ({'HIGH' if risk_score > 70 else 'MODERATE' if risk_score > 40 else 'LOW'})
• Emergency Fund Coverage: {emergency_fund_months:.1f} months
• Key Risk Factors:
{chr(10).join(f'  {risk}' for risk in risks)}
"""
        
        print(f"   ✅ Risk assessment complete (Score: {risk_score}/100)")
        
        # Calculate confidence boost
        current_confidence = state.get("confidence_score") or 0.8
        new_confidence = current_confidence + 0.1
        
        return {
            "risk_assessment": assessment,
            "confidence_score": new_confidence,
            "agents_used": state.get("agents_used", []) + ["risk_assessor"],
            "execution_path": state.get("execution_path", []) + [f"RISK ASSESSMENT completed (Score: {risk_score})"]
        }
    
    async def recommendation_engine(self, state: Dict) -> Dict:
        """
        🎓 SYNTHESIS AGENT: Combines all available analysis
        
        This agent adapts its recommendations based on which
        other agents have run and what analysis is available.
        """
        
        print("💡 Recommendation Engine: Synthesizing advice...")
        await asyncio.sleep(0.5)
        
        recommendations = []
        
        # Always have basic recommendations
        basic_analysis = state.get("basic_analysis") or ""
        if "Needs Improvement" in basic_analysis:
            recommendations.append("🎯 PRIORITY: Improve your savings rate to at least 20%")
        
        # Add detailed recommendations if available
        if state.get("detailed_analysis"):
            question_type = state["question_type"]
            
            if question_type == "major_purchase":
                recommendations.append("🏠 Home Purchase: Save for 20% down payment plus closing costs")
                recommendations.append("📋 Home Purchase: Get pre-approved to understand your budget")
            
            elif question_type == "investment":
                recommendations.append("💰 Investment: Start with low-cost index funds")
                recommendations.append("📊 Investment: Rebalance portfolio quarterly")
            
            recommendations.append("📈 Continue building emergency fund while pursuing goals")
        
        # Add risk-based recommendations if available
        risk_assessment = state.get("risk_assessment") or ""
        if risk_assessment:
            if "Critical" in risk_assessment:
                recommendations.insert(0, "🚨 URGENT: Address critical risk factors before other goals")
            elif "Moderate" in risk_assessment:
                recommendations.append("⚠️ Monitor and gradually improve risk factors")
        
        # Complexity-based recommendations
        complexity = state.get("complexity_level", "simple")
        if complexity == "complex":
            recommendations.append("🧑‍💼 Consider consulting a financial advisor for complex strategies")
        elif complexity == "simple":
            recommendations.append("📚 Great start! Keep learning about personal finance basics")
        
        # User experience-based recommendations
        experience = state.get("user_profile", {}).get("financial_experience", "beginner")
        if experience == "beginner":
            recommendations.append("🎓 Focus on fundamental habits: budgeting, emergency fund, then investing")
        elif experience == "advanced":
            recommendations.append("🚀 Consider advanced strategies like tax optimization and estate planning")
        
        print(f"   ✅ Generated {len(recommendations)} personalized recommendations")
        
        return {
            "recommendations": recommendations,
            "agents_used": state.get("agents_used", []) + ["recommendation_engine"],
            "execution_path": state.get("execution_path", []) + [f"RECOMMENDATIONS generated ({len(recommendations)} items)"]
        }

def route_after_classification(state: Dict) -> str:
    """
    🎓 ROUTING FUNCTION: The heart of conditional routing!
    
    This function decides which agent to run next based on the state.
    It's called by LangGraph to determine the execution path.
    
    Return values must match the edge names in your graph!
    """
    
    complexity = state.get("complexity_level", "simple")
    
    if complexity == "simple":
        # Simple questions: Skip detailed analysis, go straight to basic
        return "basic_analysis"
    elif complexity == "moderate":
        # Moderate questions: Do detailed analysis but skip risk assessment
        return "detailed_analysis"
    else:
        # Complex questions: Do detailed analysis first, then risk assessment
        return "detailed_analysis"

def route_after_detailed_analysis(state: Dict) -> str:
    """
    🎓 MULTI-HOP ROUTING: Decisions can chain together!
    
    After detailed analysis, we decide whether to do risk assessment
    or go straight to recommendations.
    """
    
    if state.get("requires_deep_analysis", False):
        # Complex questions need risk assessment
        return "risk_assessment"
    else:
        # Moderate questions can skip to recommendations
        return "recommendations"

def route_after_basic_analysis(state: Dict) -> str:
    """
    🎓 SIMPLE PATH ROUTING: Sometimes we skip ahead!
    
    For simple questions, we might skip detailed analysis entirely.
    """
    
    complexity = state.get("complexity_level", "simple")
    
    if complexity == "simple":
        # Skip detailed analysis for simple questions
        return "recommendations"
    else:
        # This shouldn't happen in our current logic, but good to handle
        return "detailed_analysis"

def create_conditional_routing_graph():
    """
    🎓 GRAPH WITH CONDITIONAL ROUTING
    
    This graph adapts its execution path based on the content!
    
    Possible paths:
    1. Simple: classifier → basic → recommendations
    2. Moderate: classifier → detailed → recommendations  
    3. Complex: classifier → detailed → risk → recommendations
    """
    
    agents = ConditionalRoutingDemo()
    workflow = StateGraph(SmartFinancialState)
    
    # Add all possible nodes
    workflow.add_node("classifier", agents.question_classifier)
    workflow.add_node("basic_analysis", agents.basic_analyzer)
    workflow.add_node("detailed_analysis", agents.detailed_analyzer)
    workflow.add_node("risk_assessment", agents.risk_assessor)
    workflow.add_node("recommendations", agents.recommendation_engine)
    
    # Set entry point
    workflow.set_entry_point("classifier")
    
    # 🎓 KEY CONCEPT: CONDITIONAL EDGES
    # These make routing decisions based on state content!
    
    workflow.add_conditional_edges(
        "classifier",                    # From this node
        route_after_classification,      # Use this function to decide
        {
            "basic_analysis": "basic_analysis",        # If function returns "basic_analysis"
            "detailed_analysis": "detailed_analysis"   # If function returns "detailed_analysis"
        }
    )
    
    workflow.add_conditional_edges(
        "basic_analysis",
        route_after_basic_analysis,
        {
            "recommendations": "recommendations",
            "detailed_analysis": "detailed_analysis"
        }
    )
    
    workflow.add_conditional_edges(
        "detailed_analysis", 
        route_after_detailed_analysis,
        {
            "risk_assessment": "risk_assessment",
            "recommendations": "recommendations"
        }
    )
    
    # Fixed edges (always go to same place)
    workflow.add_edge("risk_assessment", "recommendations")
    workflow.add_edge("recommendations", END)
    
    return workflow.compile()

async def test_conditional_routing():
    """
    🎓 DEMONSTRATES: How the same graph handles different complexity levels
    """
    
    print("="*70)
    print("🎓 LESSON 2: CONDITIONAL ROUTING DEMONSTRATION")
    print("="*70)
    
    app = create_conditional_routing_graph()
    
    # Test scenarios with different complexity levels
    test_scenarios = [
        {
            "name": "SIMPLE QUESTION",
            "question": "How much should I save each month?",
            "profile": {"financial_experience": "beginner"},
            "accounts": {"Checking": 3000, "Savings": 5000},
            "income": 4000,
            "expenses": 3000
        },
        {
            "name": "MODERATE QUESTION", 
            "question": "Should I invest in index funds or individual stocks for my portfolio?",
            "profile": {"financial_experience": "intermediate"},
            "accounts": {"Checking": 8000, "Savings": 15000, "Investment": 25000},
            "income": 6000,
            "expenses": 4000
        },
        {
            "name": "COMPLEX QUESTION",
            "question": "I want to buy a house in 18 months while maximizing my investment returns. I'm also considering starting a family. What's the best strategy?",
            "profile": {"financial_experience": "advanced"},
            "accounts": {"Checking": 15000, "Savings": 40000, "Investment": 75000},
            "income": 10000,
            "expenses": 6000
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'='*20} SCENARIO {i}: {scenario['name']} {'='*20}")
        print(f"💭 Question: {scenario['question']}")
        print(f"👤 Profile: {scenario['profile']}")
        print(f"💰 Assets: ${sum(scenario['accounts'].values()):,.0f}")
        
        initial_state = {
            "user_question": scenario["question"],
            "account_balances": scenario["accounts"],
            "monthly_income": scenario["income"],
            "monthly_expenses": scenario["expenses"],
            "user_profile": scenario["profile"],
            # All other fields start as None
            "question_type": None,
            "complexity_level": None,
            "requires_deep_analysis": None,
            "basic_analysis": None,
            "detailed_analysis": None,
            "risk_assessment": None,
            "market_context": None,
            "recommendations": None,
            "confidence_score": None,
            "agents_used": [],
            "execution_path": []
        }
        
        print(f"\n🚀 Executing adaptive analysis...")
        start_time = datetime.now()
        
        result = await app.ainvoke(initial_state)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        print(f"\n⏱️  Completed in {duration:.1f}s")
        print(f"🤖 Agents used: {', '.join(result['agents_used'])}")
        print(f"🛤️  Execution path:")
        for step in result["execution_path"]:
            print(f"    {step}")
        
        print(f"\n💡 Final recommendations:")
        for rec in result.get("recommendations", []):
            print(f"  • {rec}")
        
        print(f"\n📊 Confidence: {result.get('confidence_score', 0):.0%}")
    
    print("\n" + "="*70)
    print("🎓 ROUTING ANALYSIS")
    print("="*70)
    print("""
    Notice the different execution paths:
    
    SIMPLE (Beginner + Basic Question):
    classifier → basic_analysis → recommendations
    
    MODERATE (Intermediate + Investment Question):  
    classifier → detailed_analysis → recommendations
    
    COMPLEX (Advanced + Multi-factor Question):
    classifier → detailed_analysis → risk_assessment → recommendations
    
    Key Benefits:
    ✅ Faster execution for simple questions
    ✅ Appropriate depth for each complexity level
    ✅ No wasted computation on unnecessary analysis
    ✅ Personalized based on user experience
    """)

if __name__ == "__main__":
    asyncio.run(test_conditional_routing())

"""
🎓 LESSON 2 KEY TAKEAWAYS:

1. CONDITIONAL ROUTING:
   - Routes are determined by state content, not fixed structure
   - Same graph can have completely different execution paths
   - Routing functions make the decisions

2. PERFORMANCE OPTIMIZATION:
   - Simple questions complete faster (skip unnecessary agents)
   - Complex questions get thorough analysis
   - Resources used efficiently based on need

3. PERSONALIZATION:
   - User profile affects routing decisions
   - Experience level changes recommendation style
   - Account size influences analysis depth

4. ROUTING PATTERNS:
   - Single-hop: A → B or C
   - Multi-hop: A → B → (C or D)
   - Skip patterns: A → C (skipping B)

NEXT LESSON: Memory management and conversation continuity!
"""