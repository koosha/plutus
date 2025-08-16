"""
Lesson 1: Your First LangGraph Agent (SIMULATED VERSION)
=========================================================

🎓 LEARNING NOTE: This is a simulated version that doesn't require API credits.
We'll simulate Claude's responses to demonstrate the concepts.
Once you have API credits, you can run the full version!

Learning Objectives:
1. Understand the basic structure of a LangGraph agent
2. Learn about state management
3. Create a simple financial analysis agent
4. Understand message passing between components
"""

from typing import TypedDict, List, Optional, Dict, Any
from langgraph.graph import StateGraph, END
import asyncio
import json
from datetime import datetime

# =============================================================================
# CONCEPT 1: STATE DEFINITION
# =============================================================================

class FinancialAnalysisState(TypedDict):
    """
    🎓 LEARNING POINT: State in LangGraph
    
    State is like a shared whiteboard that all agents can read from and write to.
    Think of it as the "context" that gets passed between agents.
    
    Key Principles:
    1. Immutability: Each agent returns a NEW state, not modifying the original
    2. Type Safety: TypedDict ensures we know what data to expect
    3. Accumulation: State accumulates information as it flows through agents
    """
    
    # User input and conversation
    messages: List[Dict[str, str]]  # Conversation history
    user_question: str              # Current question
    
    # Financial data (would come from Wealthify in real implementation)
    account_balances: Dict[str, float]
    monthly_income: Optional[float]
    monthly_expenses: Optional[float]
    
    # Agent outputs
    financial_summary: Optional[str]
    analysis_complete: bool
    recommendations: List[str]
    
    # Metadata
    analysis_type: Optional[str]  # "cashflow", "budgeting", "investment", etc.
    confidence_score: Optional[float]
    processing_steps: List[str]  # Track what each agent does

# =============================================================================
# CONCEPT 2: SIMULATED LLM RESPONSES
# =============================================================================

class SimulatedClaude:
    """
    🎓 LEARNING POINT: LLM Integration Pattern
    
    In production, this would be real Claude API calls.
    For learning, we simulate responses to demonstrate the flow.
    
    Key concepts:
    - Each agent can make multiple LLM calls
    - Responses are parsed and validated
    - Errors are handled gracefully
    """
    
    @staticmethod
    async def classify_question(question: str, financial_data: dict) -> dict:
        """Simulate Claude classifying a financial question"""
        
        # Simulate processing delay
        await asyncio.sleep(0.5)
        
        # Simple rule-based classification for demonstration
        question_lower = question.lower()
        
        if "house" in question_lower or "mortgage" in question_lower:
            return {
                "analysis_type": "home_purchase",
                "data_needed": ["savings", "income", "expenses", "credit"],
                "complexity": "complex"
            }
        elif "retire" in question_lower:
            return {
                "analysis_type": "retirement",
                "data_needed": ["investments", "age", "goals"],
                "complexity": "complex"
            }
        elif "budget" in question_lower or "spend" in question_lower:
            return {
                "analysis_type": "budgeting",
                "data_needed": ["income", "expenses", "categories"],
                "complexity": "moderate"
            }
        else:
            return {
                "analysis_type": "general",
                "data_needed": ["all_accounts"],
                "complexity": "simple"
            }
    
    @staticmethod
    async def analyze_finances(state: dict) -> str:
        """Simulate financial analysis"""
        
        await asyncio.sleep(0.5)
        
        total_balance = sum(state["account_balances"].values())
        monthly_savings = state.get("monthly_income", 0) - state.get("monthly_expenses", 0)
        
        if state.get("analysis_type") == "home_purchase":
            return f"""
📊 HOME PURCHASE ANALYSIS:

Current Financial Position:
• Total Savings: ${total_balance:,.2f}
• Monthly Surplus: ${monthly_savings:,.2f}
• Time to Goal: 2 years (24 months)

Key Insights:
1. **Down Payment Potential**: With ${total_balance:,.2f} saved, you could afford a 20% down payment on a home worth up to ${total_balance * 5:,.2f}

2. **Additional Savings**: Over 2 years, you could save an additional ${monthly_savings * 24:,.2f} at your current rate

3. **Total House Budget**: By your target date, you'd have approximately ${total_balance + (monthly_savings * 24):,.2f} available

4. **Mortgage Readiness**: Your monthly surplus of ${monthly_savings:,.2f} indicates good cash flow for mortgage payments
            """
        else:
            return f"""
📊 FINANCIAL ANALYSIS:

Your total balance across all accounts is ${total_balance:,.2f}.
Monthly cash flow is ${monthly_savings:,.2f} (income - expenses).
This represents a healthy financial position with room for strategic planning.
            """
    
    @staticmethod
    async def generate_recommendations(analysis: str, question: str) -> List[str]:
        """Simulate recommendation generation"""
        
        await asyncio.sleep(0.5)
        
        if "house" in question.lower():
            return [
                "🏠 **Continue Saving**: Maintain your current ${1,500}/month savings rate to reach $81,000 in 2 years",
                "💳 **Credit Score**: Check and improve your credit score now for better mortgage rates",
                "📊 **Budget for Costs**: Plan for additional 3-5% in closing costs beyond your down payment",
                "🎯 **Set Price Range**: Based on your savings, target homes in the $200,000-$250,000 range",
                "💰 **Emergency Fund**: Keep 3-6 months expenses separate from your down payment fund"
            ]
        else:
            return [
                "📈 **Optimize Savings**: Consider high-yield savings accounts for better returns",
                "🎯 **Set Clear Goals**: Define specific financial targets with timelines",
                "💰 **Review Expenses**: Analyze spending patterns for optimization opportunities"
            ]

# =============================================================================
# CONCEPT 3: AGENT FUNCTIONS
# =============================================================================

class FinancialAnalysisAgent:
    """
    🎓 LEARNING POINT: Agent Design Patterns
    
    Each agent follows this pattern:
    1. Receive state (read-only)
    2. Process information (compute, call LLMs, etc.)
    3. Return NEW state with updates
    
    Agents should be:
    - Focused: Do one thing well
    - Deterministic: Same input = same output
    - Transparent: Log what they're doing
    """
    
    def __init__(self):
        self.llm = SimulatedClaude()
    
    async def conversation_agent(self, state: FinancialAnalysisState) -> FinancialAnalysisState:
        """
        🎓 LEARNING POINT: Entry Point Agent
        
        This agent:
        1. Receives user input
        2. Analyzes intent
        3. Routes to appropriate processing
        
        In multiagent systems, the entry agent is crucial for:
        - Understanding user intent
        - Setting up the processing pipeline
        - Initializing context
        """
        
        print("🤖 Conversation Agent: Processing user question...")
        
        # Track processing
        processing_steps = state.get("processing_steps", [])
        processing_steps.append(f"[{datetime.now().strftime('%H:%M:%S')}] Conversation Agent started")
        
        user_question = state["user_question"]
        
        # Simulate Claude classification
        classification = await self.llm.classify_question(
            user_question, 
            state["account_balances"]
        )
        
        # Create new state (immutability!)
        new_state = dict(state)  # Copy existing state
        new_state.update({
            "analysis_type": classification["analysis_type"],
            "messages": state.get("messages", []) + [{"role": "user", "content": user_question}],
            "processing_steps": processing_steps + [
                f"[{datetime.now().strftime('%H:%M:%S')}] Classified as: {classification['analysis_type']}"
            ]
        })
        
        print(f"   ✅ Classified question as: {classification['analysis_type']}")
        print(f"   📊 Complexity: {classification['complexity']}")
        
        return new_state
    
    async def financial_analyzer(self, state: FinancialAnalysisState) -> FinancialAnalysisState:
        """
        🎓 LEARNING POINT: Specialized Processing Agent
        
        This demonstrates:
        1. Reading from accumulated state
        2. Performing complex analysis
        3. Adding results to state
        
        Key principles:
        - Use ALL available context
        - Generate structured output
        - Handle edge cases gracefully
        """
        
        print("💰 Financial Analyzer: Analyzing financial situation...")
        
        # Track processing
        processing_steps = state.get("processing_steps", [])
        processing_steps.append(f"[{datetime.now().strftime('%H:%M:%S')}] Financial Analyzer started")
        
        # Perform analysis
        analysis = await self.llm.analyze_finances(state)
        
        # Calculate confidence based on data completeness
        data_points = 0
        if state.get("monthly_income"): data_points += 1
        if state.get("monthly_expenses"): data_points += 1
        if state.get("account_balances"): data_points += 1
        confidence = min(0.95, 0.5 + (data_points * 0.15))
        
        # Create new state
        new_state = dict(state)
        new_state.update({
            "financial_summary": analysis,
            "analysis_complete": True,
            "confidence_score": confidence,
            "processing_steps": processing_steps + [
                f"[{datetime.now().strftime('%H:%M:%S')}] Analysis completed with {confidence:.0%} confidence"
            ]
        })
        
        print(f"   ✅ Analysis complete (Confidence: {confidence:.0%})")
        
        return new_state
    
    async def recommendation_agent(self, state: FinancialAnalysisState) -> FinancialAnalysisState:
        """
        🎓 LEARNING POINT: Output Synthesis Agent
        
        Final agents in the chain:
        1. Synthesize all previous work
        2. Generate actionable output
        3. Format for user consumption
        
        This agent shows how to:
        - Use accumulated context
        - Generate structured recommendations
        - Prepare final response
        """
        
        print("💡 Recommendation Agent: Generating personalized advice...")
        
        # Track processing
        processing_steps = state.get("processing_steps", [])
        processing_steps.append(f"[{datetime.now().strftime('%H:%M:%S')}] Recommendation Agent started")
        
        # Generate recommendations
        recommendations = await self.llm.generate_recommendations(
            state.get("financial_summary", ""),
            state["user_question"]
        )
        
        # Create final message
        assistant_message = {
            "role": "assistant",
            "content": f"{state.get('financial_summary', '')}\n\n**Recommendations:**\n" + "\n".join(recommendations)
        }
        
        # Create final state
        new_state = dict(state)
        new_state.update({
            "recommendations": recommendations,
            "messages": state.get("messages", []) + [assistant_message],
            "processing_steps": processing_steps + [
                f"[{datetime.now().strftime('%H:%M:%S')}] Generated {len(recommendations)} recommendations",
                f"[{datetime.now().strftime('%H:%M:%S')}] Pipeline complete"
            ]
        })
        
        print(f"   ✅ Generated {len(recommendations)} recommendations")
        
        return new_state

# =============================================================================
# CONCEPT 4: GRAPH CONSTRUCTION
# =============================================================================

def create_financial_analysis_graph():
    """
    🎓 LEARNING POINT: Graph Construction
    
    The graph defines the FLOW of your multiagent system:
    
    1. NODES = Agents (functions that process state)
    2. EDGES = Connections (how state flows between agents)
    3. ENTRY = Where to start
    4. END = Where to stop
    
    Graphs can have:
    - Linear flows (A → B → C)
    - Conditional branches (A → B or C based on state)
    - Loops (A → B → A until condition met)
    - Parallel execution (A → [B and C] → D)
    """
    
    # Initialize our agent class
    agent = FinancialAnalysisAgent()
    
    # Create the graph with our state type
    workflow = StateGraph(FinancialAnalysisState)
    
    # Add nodes (agents) - these are the "workers"
    workflow.add_node("conversation", agent.conversation_agent)
    workflow.add_node("analyzer", agent.financial_analyzer)
    workflow.add_node("recommendations", agent.recommendation_agent)
    
    # Define the flow - how agents connect
    workflow.set_entry_point("conversation")  # Start here
    workflow.add_edge("conversation", "analyzer")  # Then go here
    workflow.add_edge("analyzer", "recommendations")  # Then here
    workflow.add_edge("recommendations", END)  # Then stop
    
    # Compile the graph into an executable app
    app = workflow.compile()
    
    print("\n🏗️  Graph Architecture:")
    print("┌─────────────┐")
    print("│ Conversation│ (Entry Point)")
    print("└──────┬──────┘")
    print("       ↓")
    print("┌─────────────┐")
    print("│  Analyzer   │")
    print("└──────┬──────┘")
    print("       ↓")
    print("┌─────────────┐")
    print("│Recommendations│")
    print("└──────┬──────┘")
    print("       ↓")
    print("     [END]")
    
    return app

# =============================================================================
# CONCEPT 5: RUNNING THE SYSTEM
# =============================================================================

async def run_financial_analysis_demo():
    """
    🎓 LEARNING POINT: Executing a Graph
    
    Execution involves:
    1. Creating initial state
    2. Invoking the graph
    3. Processing through agents
    4. Returning final state
    
    The graph handles:
    - Async execution
    - State passing
    - Error handling
    - Result accumulation
    """
    
    print("="*60)
    print("🎓 LESSON 1: Your First LangGraph Agent")
    print("    (Simulated Version - No API Required)")
    print("="*60)
    
    # Create the graph
    app = create_financial_analysis_graph()
    
    # Sample financial data (in real Plutus, this comes from Wealthify)
    sample_financial_data = {
        "account_balances": {
            "Checking": 5000.00,
            "Savings": 15000.00,
            "Investment": 25000.00
        },
        "monthly_income": 6000.00,
        "monthly_expenses": 4500.00
    }
    
    # User question
    user_question = "I want to buy a house in 2 years. Do I have enough saved up?"
    
    # Create initial state - this is what flows through the graph
    initial_state: FinancialAnalysisState = {
        "messages": [],
        "user_question": user_question,
        "account_balances": sample_financial_data["account_balances"],
        "monthly_income": sample_financial_data["monthly_income"],
        "monthly_expenses": sample_financial_data["monthly_expenses"],
        "financial_summary": None,
        "analysis_complete": False,
        "recommendations": [],
        "analysis_type": None,
        "confidence_score": None,
        "processing_steps": []
    }
    
    print(f"\n💭 User Question: {user_question}")
    print(f"\n💰 Financial Context:")
    print(f"   • Total Assets: ${sum(sample_financial_data['account_balances'].values()):,.2f}")
    print(f"   • Monthly Income: ${sample_financial_data['monthly_income']:,.2f}")
    print(f"   • Monthly Expenses: ${sample_financial_data['monthly_expenses']:,.2f}")
    print(f"   • Monthly Savings: ${sample_financial_data['monthly_income'] - sample_financial_data['monthly_expenses']:,.2f}")
    
    print("\n🚀 Running Multiagent Analysis...")
    print("-" * 40)
    
    # Run the graph - this executes all agents in sequence
    final_state = await app.ainvoke(initial_state)
    
    # Display results
    print("\n" + "="*60)
    print("📊 ANALYSIS RESULTS")
    print("="*60)
    
    print(f"\n🎯 Analysis Type: {final_state['analysis_type']}")
    print(f"📈 Confidence Score: {final_state.get('confidence_score', 0):.0%}")
    
    print(f"\n📝 Financial Analysis:")
    print("-" * 30)
    print(final_state.get('financial_summary', 'No analysis available'))
    
    print(f"\n💡 Recommendations:")
    print("-" * 30)
    for i, rec in enumerate(final_state.get('recommendations', []), 1):
        print(f"{rec}")
    
    print("\n🔍 Processing Steps:")
    print("-" * 30)
    for step in final_state.get('processing_steps', []):
        print(f"  {step}")
    
    print("\n" + "="*60)
    print("🎉 Analysis Complete!")
    print("="*60)
    
    return final_state

# =============================================================================
# LEARNING EXERCISES
# =============================================================================

def learning_exercises():
    """
    🎓 EXERCISES TO UNDERSTAND THE CONCEPTS:
    
    1. STATE MANAGEMENT:
       - Try adding a new field to the state (e.g., 'user_age')
       - See how it flows through agents
    
    2. AGENT MODIFICATION:
       - Add a new agent that calculates debt-to-income ratio
       - Insert it between analyzer and recommendations
    
    3. CONDITIONAL ROUTING:
       - Make the recommendation agent optional based on confidence
       - If confidence < 0.7, skip recommendations
    
    4. ERROR HANDLING:
       - What happens if an agent returns None?
       - How would you handle missing financial data?
    
    5. PARALLEL EXECUTION:
       - Can you make analyzer and a new "risk_assessor" run in parallel?
       - How would you merge their results?
    """
    print("\n" + "="*60)
    print("📚 LEARNING EXERCISES")
    print("="*60)
    print("""
    Try these modifications to deepen your understanding:
    
    1. Add a 'risk_assessment' field to the state
    2. Create a new agent that evaluates investment risk
    3. Add conditional routing based on account balance
    4. Implement error handling for missing data
    5. Add logging to track execution time
    
    Questions to consider:
    - Why is state immutability important?
    - How would you handle agent failures?
    - When would you use parallel vs sequential execution?
    - How would you test individual agents?
    """)

# =============================================================================
# RUN THE DEMO
# =============================================================================

if __name__ == "__main__":
    # Run the main demo
    asyncio.run(run_financial_analysis_demo())
    
    # Show learning exercises
    learning_exercises()

"""
🎓 KEY TAKEAWAYS FROM LESSON 1:

1. MULTIAGENT ARCHITECTURE:
   - Agents are specialized functions
   - Each handles one aspect of the problem
   - They communicate through shared state

2. STATE MANAGEMENT:
   - State flows through the graph
   - Each agent reads and updates state
   - Immutability ensures predictability

3. GRAPH CONSTRUCTION:
   - Nodes are agents
   - Edges define flow
   - Can be linear, branching, or looping

4. BENEFITS OVER SINGLE AGENT:
   - Specialization improves quality
   - Easier to debug and maintain
   - Can parallelize for performance
   - More transparent decision making

NEXT LESSON: Conditional routing and dynamic agent selection!
"""