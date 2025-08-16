"""
Lesson 1: Your First LangGraph Agent
=====================================

Learning Objectives:
1. Understand the basic structure of a LangGraph agent
2. Learn about state management
3. Create a simple financial analysis agent
4. Understand message passing between components

This is a standalone learning module - we'll integrate concepts into Plutus later.
"""

from typing import TypedDict, List, Optional, Dict, Any
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
import asyncio
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# CONCEPT 1: STATE DEFINITION
# =============================================================================

class FinancialAnalysisState(TypedDict):
    """
    🎓 LEARNING POINT: State in LangGraph
    
    State is like a shared whiteboard that all agents can read from and write to.
    Think of it as the "context" that gets passed between agents.
    
    Why TypedDict?
    - Type safety: We know what data structure to expect
    - IDE support: Auto-completion and error checking
    - Documentation: Clear interface definition
    """
    
    # User input and conversation
    messages: List[Any]  # Conversation history
    user_question: str   # Current question
    
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

# =============================================================================
# CONCEPT 2: AGENT FUNCTIONS
# =============================================================================

class FinancialAnalysisAgent:
    """
    🎓 LEARNING POINT: Agent Design Patterns
    
    Each agent is a function that:
    1. Takes the current state
    2. Performs some processing (often with an LLM)
    3. Returns an updated state
    
    This is the core pattern of LangGraph agents.
    """
    
    def __init__(self):
        # Initialize Claude AI model
        # In production, this would use environment variables
        self.llm = ChatAnthropic(
            model="claude-3-5-haiku-20241022",  # Fast, cost-effective model
            temperature=0.1  # Low temperature for consistent financial analysis
        )
    
    async def conversation_agent(self, state: FinancialAnalysisState) -> FinancialAnalysisState:
        """
        🎓 LEARNING POINT: Entry Point Agent
        
        This agent:
        1. Receives user input
        2. Analyzes the type of financial question
        3. Sets up the analysis pipeline
        
        Think of this as the "receptionist" who understands what the user wants
        and routes them to the right specialist.
        """
        
        user_question = state["user_question"]
        
        # Use Claude to understand the type of financial question
        classification_prompt = f"""
        You are a financial question classifier. Analyze this user question and determine:
        1. What type of financial analysis is needed?
        2. What data would be most relevant?
        
        User question: {user_question}
        
        Available account data: {list(state['account_balances'].keys())}
        Monthly income: ${state.get('monthly_income', 'Unknown')}
        Monthly expenses: ${state.get('monthly_expenses', 'Unknown')}
        
        Respond with JSON in this format:
        {{
            "analysis_type": "cashflow|budgeting|investment|general",
            "data_needed": ["list", "of", "data", "types"],
            "complexity": "simple|moderate|complex"
        }}
        """
        
        # Call Claude AI
        classification_response = await self.llm.ainvoke([
            SystemMessage(content="You are a helpful financial analysis classifier."),
            HumanMessage(content=classification_prompt)
        ])
        
        # Parse the response (in production, add error handling)
        try:
            analysis_info = json.loads(classification_response.content)
            analysis_type = analysis_info.get("analysis_type", "general")
        except:
            analysis_type = "general"  # Fallback
        
        # Update state
        updated_state = state.copy()
        updated_state["analysis_type"] = analysis_type
        updated_state["messages"].append(HumanMessage(content=user_question))
        
        print(f"🤖 Conversation Agent: Classified question as '{analysis_type}'")
        
        return updated_state
    
    async def financial_analyzer(self, state: FinancialAnalysisState) -> FinancialAnalysisState:
        """
        🎓 LEARNING POINT: Specialized Processing Agent
        
        This agent:
        1. Takes financial data from state
        2. Performs calculations and analysis
        3. Generates insights using Claude AI
        
        This is where the "heavy lifting" happens - actual financial analysis.
        """
        
        # Prepare financial summary
        total_balance = sum(state["account_balances"].values())
        account_summary = ", ".join([f"{acc}: ${bal:,.2f}" for acc, bal in state["account_balances"].items()])
        
        analysis_prompt = f"""
        You are an expert financial analyst. Analyze this user's financial situation:
        
        User Question: {state['user_question']}
        Analysis Type: {state.get('analysis_type', 'general')}
        
        Financial Data:
        - Account Balances: {account_summary}
        - Total Balance: ${total_balance:,.2f}
        - Monthly Income: ${state.get('monthly_income', 'Not provided')}
        - Monthly Expenses: ${state.get('monthly_expenses', 'Not provided')}
        
        Provide a comprehensive financial analysis that:
        1. Summarizes their current situation
        2. Identifies key insights
        3. Highlights any concerns or opportunities
        
        Keep it clear and actionable.
        """
        
        # Get analysis from Claude
        analysis_response = await self.llm.ainvoke([
            SystemMessage(content="You are a professional financial analyst providing clear, actionable insights."),
            HumanMessage(content=analysis_prompt)
        ])
        
        # Update state
        updated_state = state.copy()
        updated_state["financial_summary"] = analysis_response.content
        updated_state["analysis_complete"] = True
        updated_state["confidence_score"] = 0.85  # In production, this would be calculated
        
        print(f"💰 Financial Analyzer: Completed {state.get('analysis_type')} analysis")
        
        return updated_state
    
    async def recommendation_agent(self, state: FinancialAnalysisState) -> FinancialAnalysisState:
        """
        🎓 LEARNING POINT: Output Synthesis Agent
        
        This agent:
        1. Takes the analysis results
        2. Generates actionable recommendations
        3. Formats the final response
        
        This is the "advisor" who takes the analysis and provides guidance.
        """
        
        recommendation_prompt = f"""
        Based on this financial analysis, provide specific, actionable recommendations:
        
        Analysis Type: {state.get('analysis_type')}
        Financial Summary: {state.get('financial_summary')}
        User Question: {state['user_question']}
        
        Provide 3-5 specific, actionable recommendations that address the user's question.
        Format each recommendation clearly and explain why it's important.
        """
        
        # Get recommendations from Claude
        rec_response = await self.llm.ainvoke([
            SystemMessage(content="You are a wealth building coach providing specific, actionable advice."),
            HumanMessage(content=recommendation_prompt)
        ])
        
        # Parse recommendations (simplified - in production, you'd extract structured data)
        recommendations = rec_response.content.split('\n')
        recommendations = [rec.strip() for rec in recommendations if rec.strip()]
        
        # Update state
        updated_state = state.copy()
        updated_state["recommendations"] = recommendations
        updated_state["messages"].append(AIMessage(content=rec_response.content))
        
        print(f"💡 Recommendation Agent: Generated {len(recommendations)} recommendations")
        
        return updated_state

# =============================================================================
# CONCEPT 3: GRAPH CONSTRUCTION
# =============================================================================

def create_financial_analysis_graph():
    """
    🎓 LEARNING POINT: Graph Construction
    
    This is where we define the flow of our multiagent system:
    1. Add nodes (agents)
    2. Define connections (edges)
    3. Set entry and exit points
    
    Think of this as drawing a flowchart of how agents work together.
    """
    
    # Initialize our agent class
    agent = FinancialAnalysisAgent()
    
    # Create the graph
    workflow = StateGraph(FinancialAnalysisState)
    
    # Add agent nodes
    workflow.add_node("conversation", agent.conversation_agent)
    workflow.add_node("analyzer", agent.financial_analyzer)
    workflow.add_node("recommendations", agent.recommendation_agent)
    
    # Define the flow
    workflow.set_entry_point("conversation")
    workflow.add_edge("conversation", "analyzer")
    workflow.add_edge("analyzer", "recommendations")
    workflow.add_edge("recommendations", END)
    
    # Compile the graph
    app = workflow.compile()
    
    print("🏗️  Financial Analysis Graph Created!")
    print("Flow: conversation → analyzer → recommendations → END")
    
    return app

# =============================================================================
# CONCEPT 4: RUNNING THE SYSTEM
# =============================================================================

async def run_financial_analysis_demo():
    """
    🎓 LEARNING POINT: Executing a Graph
    
    This demonstrates how to:
    1. Create initial state
    2. Run the graph
    3. Access results
    """
    
    print("="*60)
    print("🎓 LESSON 1: Your First LangGraph Agent")
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
    
    # Create initial state
    initial_state = {
        "messages": [],
        "user_question": user_question,
        "account_balances": sample_financial_data["account_balances"],
        "monthly_income": sample_financial_data["monthly_income"],
        "monthly_expenses": sample_financial_data["monthly_expenses"],
        "financial_summary": None,
        "analysis_complete": False,
        "recommendations": [],
        "analysis_type": None,
        "confidence_score": None
    }
    
    print(f"\n💭 User Question: {user_question}")
    print(f"💰 Sample Data: {sample_financial_data}")
    print("\n🚀 Running Analysis...")
    print("-" * 40)
    
    # Run the graph
    final_state = await app.ainvoke(initial_state)
    
    # Display results
    print("\n" + "="*60)
    print("📊 ANALYSIS RESULTS")
    print("="*60)
    
    print(f"\n🎯 Analysis Type: {final_state['analysis_type']}")
    print(f"📈 Confidence Score: {final_state.get('confidence_score', 'N/A')}")
    
    print(f"\n📝 Financial Analysis:")
    print("-" * 30)
    print(final_state.get('financial_summary', 'No analysis available'))
    
    print(f"\n💡 Recommendations:")
    print("-" * 30)
    for i, rec in enumerate(final_state.get('recommendations', []), 1):
        if rec.strip():
            print(f"{i}. {rec}")
    
    print("\n" + "="*60)
    print("🎉 Analysis Complete!")
    print("="*60)
    
    return final_state

# =============================================================================
# RUN THE DEMO
# =============================================================================

if __name__ == "__main__":
    # Note: You'll need to set ANTHROPIC_API_KEY in your environment
    asyncio.run(run_financial_analysis_demo())

"""
🎓 KEY LEARNING POINTS SUMMARY:

1. STATE MANAGEMENT:
   - State is shared data structure passed between agents
   - Use TypedDict for type safety and documentation
   - Each agent reads from and updates the state

2. AGENT DESIGN:
   - Each agent is a specialized function
   - Takes state as input, returns updated state
   - Use Claude AI for reasoning and analysis

3. GRAPH CONSTRUCTION:
   - Add nodes (agents) to the graph
   - Define edges (connections) between agents
   - Set entry point and end conditions

4. EXECUTION MODEL:
   - Graph runs asynchronously
   - State flows from agent to agent
   - Final state contains all results

NEXT LESSON: We'll learn about conditional routing and more complex agent interactions!
"""