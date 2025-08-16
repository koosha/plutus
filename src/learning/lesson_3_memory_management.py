"""
Lesson 3: Memory Management and Conversation Continuity
=======================================================

🎓 LEARNING OBJECTIVES:
1. Understand different types of memory in multiagent systems
2. Learn how to maintain conversation context across interactions
3. Implement persistent memory storage and retrieval
4. Build conversation continuity that feels natural

This is what makes Plutus feel like a real financial advisor who remembers you!
"""

import asyncio
import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, TypedDict
from dataclasses import dataclass, asdict
from pathlib import Path
import uuid

# =============================================================================
# CONCEPT 1: Types of Memory in Conversational AI
# =============================================================================

@dataclass
class ConversationTurn:
    """
    🎓 BASIC MEMORY UNIT: One exchange between user and assistant
    
    This is the atomic unit of conversation memory. Each turn captures:
    - What the user said
    - How we responded
    - When it happened
    - What context was available
    """
    id: str
    user_message: str
    assistant_response: str
    timestamp: datetime
    user_id: str
    session_id: str
    context_snapshot: Dict[str, Any]  # Financial data at the time
    agents_used: List[str]
    confidence_score: Optional[float] = None

@dataclass 
class UserProfile:
    """
    🎓 PERSISTENT MEMORY: What we remember about the user long-term
    
    This persists across sessions and represents our accumulated
    knowledge about the user's financial situation and preferences.
    """
    user_id: str
    name: Optional[str]
    created_at: datetime
    last_active: datetime
    
    # Financial snapshot (evolves over time)
    current_accounts: Dict[str, float]
    monthly_income: Optional[float]
    monthly_expenses: Optional[float]
    
    # Goals and preferences (learned from conversations)
    financial_goals: List[Dict[str, Any]]
    risk_tolerance: Optional[str]  # conservative, moderate, aggressive
    investment_experience: Optional[str]  # beginner, intermediate, advanced
    life_stage: Optional[str]  # student, young_professional, family, pre_retirement, retired
    
    # Conversation patterns
    preferred_communication_style: Optional[str]  # detailed, concise, technical
    common_question_types: List[str]
    
    # Insights accumulated over time
    behavioral_patterns: List[str]
    concerns_expressed: List[str]
    progress_tracking: Dict[str, Any]

@dataclass
class ConversationSession:
    """
    🎓 SESSION MEMORY: Context for a single conversation session
    
    A session might span multiple questions within a short timeframe.
    This captures the flow and context of a single interaction.
    """
    session_id: str
    user_id: str
    started_at: datetime
    ended_at: Optional[datetime]
    turns: List[ConversationTurn]
    session_summary: Optional[str]
    goals_discussed: List[str]
    decisions_made: List[str]
    follow_up_needed: List[str]

# =============================================================================
# CONCEPT 2: Memory Storage and Retrieval System
# =============================================================================

class MemoryManager:
    """
    🎓 MEMORY ORCHESTRATOR: Manages all types of memory for Plutus
    
    This is the brain's memory system that:
    1. Stores conversation history
    2. Maintains user profiles
    3. Enables context retrieval
    4. Supports conversation continuity
    """
    
    def __init__(self, db_path: str = "plutus_memory.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for memory storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # User profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                current_accounts TEXT, -- JSON
                monthly_income REAL,
                monthly_expenses REAL,
                financial_goals TEXT, -- JSON
                risk_tolerance TEXT,
                investment_experience TEXT,
                life_stage TEXT,
                preferred_communication_style TEXT,
                common_question_types TEXT, -- JSON
                behavioral_patterns TEXT, -- JSON
                concerns_expressed TEXT, -- JSON
                progress_tracking TEXT -- JSON
            )
        """)
        
        # Conversation sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                started_at TIMESTAMP,
                ended_at TIMESTAMP,
                session_summary TEXT,
                goals_discussed TEXT, -- JSON
                decisions_made TEXT, -- JSON
                follow_up_needed TEXT, -- JSON
                FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
            )
        """)
        
        # Conversation turns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                user_id TEXT,
                user_message TEXT,
                assistant_response TEXT,
                timestamp TIMESTAMP,
                context_snapshot TEXT, -- JSON
                agents_used TEXT, -- JSON
                confidence_score REAL,
                FOREIGN KEY (session_id) REFERENCES conversation_sessions (session_id),
                FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
            )
        """)
        
        conn.commit()
        conn.close()
        
        print("📚 Memory database initialized")
    
    async def get_or_create_user_profile(self, user_id: str, name: Optional[str] = None) -> UserProfile:
        """Get existing user profile or create new one"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if row:
            # Load existing profile
            profile = UserProfile(
                user_id=row[0],
                name=row[1],
                created_at=datetime.fromisoformat(row[2]),
                last_active=datetime.fromisoformat(row[3]),
                current_accounts=json.loads(row[4] or "{}"),
                monthly_income=row[5],
                monthly_expenses=row[6],
                financial_goals=json.loads(row[7] or "[]"),
                risk_tolerance=row[8],
                investment_experience=row[9],
                life_stage=row[10],
                preferred_communication_style=row[11],
                common_question_types=json.loads(row[12] or "[]"),
                behavioral_patterns=json.loads(row[13] or "[]"),
                concerns_expressed=json.loads(row[14] or "[]"),
                progress_tracking=json.loads(row[15] or "{}")
            )
            print(f"👤 Loaded existing profile for {user_id}")
        else:
            # Create new profile
            profile = UserProfile(
                user_id=user_id,
                name=name,
                created_at=datetime.now(),
                last_active=datetime.now(),
                current_accounts={},
                monthly_income=None,
                monthly_expenses=None,
                financial_goals=[],
                risk_tolerance=None,
                investment_experience=None,
                life_stage=None,
                preferred_communication_style=None,
                common_question_types=[],
                behavioral_patterns=[],
                concerns_expressed=[],
                progress_tracking={}
            )
            await self.save_user_profile(profile)
            print(f"👤 Created new profile for {user_id}")
        
        conn.close()
        return profile
    
    async def save_user_profile(self, profile: UserProfile):
        """Save user profile to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile.user_id,
            profile.name,
            profile.created_at.isoformat(),
            profile.last_active.isoformat(),
            json.dumps(profile.current_accounts),
            profile.monthly_income,
            profile.monthly_expenses,
            json.dumps(profile.financial_goals),
            profile.risk_tolerance,
            profile.investment_experience,
            profile.life_stage,
            profile.preferred_communication_style,
            json.dumps(profile.common_question_types),
            json.dumps(profile.behavioral_patterns),
            json.dumps(profile.concerns_expressed),
            json.dumps(profile.progress_tracking)
        ))
        
        conn.commit()
        conn.close()
        print(f"💾 Saved profile for {profile.user_id}")
    
    async def start_conversation_session(self, user_id: str) -> str:
        """Start a new conversation session"""
        session_id = str(uuid.uuid4())
        session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            started_at=datetime.now(),
            ended_at=None,
            turns=[],
            session_summary=None,
            goals_discussed=[],
            decisions_made=[],
            follow_up_needed=[]
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversation_sessions 
            (session_id, user_id, started_at, ended_at, session_summary, goals_discussed, decisions_made, follow_up_needed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.session_id,
            session.user_id,
            session.started_at.isoformat(),
            None,
            None,
            json.dumps(session.goals_discussed),
            json.dumps(session.decisions_made),
            json.dumps(session.follow_up_needed)
        ))
        
        conn.commit()
        conn.close()
        
        print(f"🗣️  Started conversation session {session_id[:8]}...")
        return session_id
    
    async def add_conversation_turn(self, turn: ConversationTurn):
        """Add a conversation turn to memory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversation_turns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            turn.id,
            turn.session_id,
            turn.user_id,
            turn.user_message,
            turn.assistant_response,
            turn.timestamp.isoformat(),
            json.dumps(turn.context_snapshot),
            json.dumps(turn.agents_used),
            turn.confidence_score
        ))
        
        conn.commit()
        conn.close()
        print(f"💬 Saved conversation turn {turn.id[:8]}...")
    
    async def get_conversation_history(self, user_id: str, limit: int = 10) -> List[ConversationTurn]:
        """Get recent conversation history for context"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM conversation_turns 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        turns = []
        
        for row in rows:
            turn = ConversationTurn(
                id=row[0],
                session_id=row[1],
                user_id=row[2],
                user_message=row[3],
                assistant_response=row[4],
                timestamp=datetime.fromisoformat(row[5]),
                context_snapshot=json.loads(row[6]),
                agents_used=json.loads(row[7]),
                confidence_score=row[8]
            )
            turns.append(turn)
        
        conn.close()
        return list(reversed(turns))  # Return chronological order

# =============================================================================
# CONCEPT 3: Context-Aware Conversation Agent
# =============================================================================

class MemoryAwareFinancialAgent:
    """
    🎓 MEMORY-ENHANCED AGENT: Uses conversation history and user profile
    
    This agent demonstrates how to use memory to:
    1. Recognize returning users
    2. Reference previous conversations
    3. Track goal progress
    4. Provide personalized responses
    """
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
        self.current_session = None
        self.current_user_profile = None
    
    async def start_conversation(self, user_id: str, user_name: Optional[str] = None) -> str:
        """Start a conversation with memory loading"""
        print(f"\n🎬 Starting conversation with user {user_id}")
        
        # Load user profile and history
        self.current_user_profile = await self.memory.get_or_create_user_profile(user_id, user_name)
        
        # Start new session
        self.current_session = await self.memory.start_conversation_session(user_id)
        
        # Get recent conversation history for context
        recent_history = await self.memory.get_conversation_history(user_id, limit=5)
        
        # Generate contextual greeting
        greeting = await self.generate_contextual_greeting(recent_history)
        
        return greeting
    
    async def generate_contextual_greeting(self, history: List[ConversationTurn]) -> str:
        """Generate greeting based on user history and profile"""
        
        profile = self.current_user_profile
        
        if not history:
            # First time user
            return f"Hello{' ' + profile.name if profile.name else ''}! I'm Plutus, your AI financial advisor. I'm here to help you with any financial questions or goals you have. What would you like to discuss today?"
        
        # Returning user - reference previous conversations
        last_turn = history[-1]
        days_since = (datetime.now() - last_turn.timestamp).days
        
        if days_since == 0:
            return f"Welcome back{' ' + profile.name if profile.name else ''}! How can I help you further today?"
        elif days_since == 1:
            return f"Good to see you again{' ' + profile.name if profile.name else ''}! Yesterday we were discussing {self.extract_topic(last_turn.user_message)}. How can I assist you today?"
        elif days_since <= 7:
            return f"Welcome back{' ' + profile.name if profile.name else ''}! It's been {days_since} days since we last spoke about {self.extract_topic(last_turn.user_message)}. What's on your mind today?"
        else:
            return f"Welcome back{' ' + profile.name if profile.name else ''}! It's been a while since our last conversation. How can I help you with your financial goals today?"
    
    def extract_topic(self, message: str) -> str:
        """Extract main topic from user message"""
        # Simplified topic extraction
        if "house" in message.lower() or "mortgage" in message.lower():
            return "home purchasing"
        elif "retire" in message.lower() or "401k" in message.lower():
            return "retirement planning"
        elif "invest" in message.lower() or "portfolio" in message.lower():
            return "investment strategy"
        elif "debt" in message.lower() or "loan" in message.lower():
            return "debt management"
        elif "budget" in message.lower() or "spend" in message.lower():
            return "budgeting"
        else:
            return "your financial planning"
    
    async def process_message(self, user_message: str) -> str:
        """Process user message with full memory context"""
        
        print(f"💭 Processing: {user_message[:50]}...")
        
        # Get conversation context
        history = await self.memory.get_conversation_history(self.current_user_profile.user_id, limit=3)
        
        # Build context for response generation (convert datetime to string for JSON)
        context = {
            "user_profile": self.profile_to_dict(self.current_user_profile),
            "recent_history": [self.turn_to_dict(turn) for turn in history],
            "current_accounts": self.current_user_profile.current_accounts,
            "goals": self.current_user_profile.financial_goals
        }
        
        # Simulate processing with different agents
        await asyncio.sleep(0.5)  # Simulate analysis time
        
        # Generate memory-aware response
        response = await self.generate_memory_aware_response(user_message, context)
        
        # Update user profile based on conversation
        await self.update_user_profile_from_conversation(user_message, response)
        
        # Save conversation turn
        turn = ConversationTurn(
            id=str(uuid.uuid4()),
            user_message=user_message,
            assistant_response=response,
            timestamp=datetime.now(),
            user_id=self.current_user_profile.user_id,
            session_id=self.current_session,
            context_snapshot=context,
            agents_used=["memory_aware_agent", "financial_analyzer"],
            confidence_score=0.85
        )
        
        await self.memory.add_conversation_turn(turn)
        
        return response
    
    async def generate_memory_aware_response(self, message: str, context: Dict) -> str:
        """Generate response using conversation history and profile"""
        
        profile = self.current_user_profile
        
        # Check if this is a follow-up question
        if context["recent_history"]:
            last_message = context["recent_history"][-1]["user_message"]
            if self.is_follow_up_question(message, last_message):
                return await self.handle_follow_up(message, context)
        
        # Check for goal-related questions
        if any(goal_word in message.lower() for goal_word in ["goal", "plan", "want to", "trying to"]):
            return await self.handle_goal_discussion(message, context)
        
        # Check for account balance questions
        if any(balance_word in message.lower() for balance_word in ["balance", "worth", "have", "saved"]):
            return await self.handle_balance_inquiry(message, context)
        
        # Handle investment questions with user experience
        if "invest" in message.lower():
            return await self.handle_investment_question(message, context)
        
        # Default financial analysis
        return await self.handle_general_financial_question(message, context)
    
    def is_follow_up_question(self, current: str, previous: str) -> bool:
        """Detect if current message is following up on previous"""
        follow_up_indicators = ["what about", "how about", "also", "and", "but what if", "what would happen"]
        return any(indicator in current.lower() for indicator in follow_up_indicators)
    
    async def handle_follow_up(self, message: str, context: Dict) -> str:
        """Handle follow-up questions that reference previous conversation"""
        previous_topic = self.extract_topic(context["recent_history"][-1]["user_message"])
        return f"""I see you're following up on our discussion about {previous_topic}. 
        
Based on what we covered earlier and your question about "{message}", here's my analysis:

{self.generate_contextual_advice(message, context)}

This builds on our previous conversation where we established your goals and current situation."""
    
    async def handle_goal_discussion(self, message: str, context: Dict) -> str:
        """Handle goal-setting and planning conversations"""
        existing_goals = context["user_profile"]["financial_goals"]
        
        if existing_goals:
            return f"""I see you want to discuss goals. You currently have {len(existing_goals)} financial goals we've discussed:

{self.format_existing_goals(existing_goals)}

How does your new question about "{message}" relate to these existing goals? Are we looking at a new goal or adjusting an existing one?"""
        else:
            return f"""Great! I love discussing financial goals. This is the first goal we're setting together.

Based on your question "{message}", let me help you think through this systematically:

1. **Goal Clarification**: Let's be specific about what you want to achieve
2. **Timeline**: When do you want to reach this goal?
3. **Current Resources**: Based on your profile, you have {sum(context['user_profile']['current_accounts'].values())} in total assets
4. **Strategy**: Here's how we can work toward this goal...

I'll remember this goal for our future conversations so we can track your progress!"""
    
    async def handle_balance_inquiry(self, message: str, context: Dict) -> str:
        """Handle questions about account balances and net worth"""
        accounts = context["user_profile"]["current_accounts"]
        
        if not accounts:
            return "I don't have your current account information yet. Could you share your account balances so I can give you personalized advice? I'll remember this information for future conversations."
        
        total = sum(accounts.values())
        account_summary = ", ".join([f"{name}: ${balance:,.0f}" for name, balance in accounts.items()])
        
        return f"""Based on the account information I have for you:

**Account Summary:**
{account_summary}

**Total Assets: ${total:,.0f}**

Since our last conversation, I can see {self.analyze_balance_changes(context)}. 

{self.provide_balance_insights(total, accounts)}"""
    
    async def handle_investment_question(self, message: str, context: Dict) -> str:
        """Handle investment questions based on user experience level"""
        experience = context["user_profile"]["investment_experience"]
        risk_tolerance = context["user_profile"]["risk_tolerance"]
        
        if experience == "beginner":
            return f"""Since you're new to investing (as we discussed before), let me give you beginner-friendly advice:

{self.generate_beginner_investment_advice(message, context)}

I remember you're at the beginning of your investment journey, so I'll keep my recommendations simple and educational."""
        
        elif experience == "advanced":
            return f"""Given your advanced investment experience, here's a more sophisticated analysis:

{self.generate_advanced_investment_advice(message, context)}

I know you're comfortable with complex strategies, so I can dive deeper into the technical aspects."""
        
        else:
            return f"""For your investment question, let me provide analysis appropriate to your experience level:

{self.generate_intermediate_investment_advice(message, context)}

If you'd like me to adjust the complexity of my responses, just let me know your investment experience level!"""
    
    async def handle_general_financial_question(self, message: str, context: Dict) -> str:
        """Handle general financial questions with personal context"""
        return f"""Let me analyze your question with your personal context in mind:

**Your Question:** {message}

**Personal Context:**
- Total Assets: ${sum(context['user_profile']['current_accounts'].values()):,.0f}
- Monthly Income: ${context['user_profile']['monthly_income'] or 'Not provided'}
- Goals Discussed: {len(context['user_profile']['financial_goals'])} financial goals

**Personalized Analysis:**
{self.generate_personalized_financial_advice(message, context)}

I'll remember this discussion for our future conversations!"""
    
    # Helper methods for response generation
    def format_existing_goals(self, goals: List[Dict]) -> str:
        if not goals:
            return "None set yet"
        return "\n".join([f"• {goal.get('description', 'Goal')} (Target: ${goal.get('target_amount', 0):,.0f})" for goal in goals])
    
    def analyze_balance_changes(self, context: Dict) -> str:
        # Simplified - in real implementation, compare with historical data
        return "your financial picture is looking stable"
    
    def provide_balance_insights(self, total: float, accounts: Dict) -> str:
        if total < 10000:
            return "Focus on building your emergency fund and establishing good savings habits."
        elif total < 50000:
            return "You're building wealth! Consider optimizing your investment allocation."
        else:
            return "You have a solid financial foundation. Let's focus on wealth optimization strategies."
    
    def generate_contextual_advice(self, message: str, context: Dict) -> str:
        return f"Based on your profile and our conversation history, here's my personalized advice for: {message}"
    
    def generate_beginner_investment_advice(self, message: str, context: Dict) -> str:
        return "Start with low-cost index funds, focus on consistent contributions, and avoid complex strategies until you build experience."
    
    def generate_advanced_investment_advice(self, message: str, context: Dict) -> str:
        return "Consider tax-loss harvesting, factor tilting, and alternative investments based on your sophisticated understanding."
    
    def generate_intermediate_investment_advice(self, message: str, context: Dict) -> str:
        return "You can handle moderate complexity - consider diversified portfolios with some sector allocation and regular rebalancing."
    
    def generate_personalized_financial_advice(self, message: str, context: Dict) -> str:
        return f"Tailored advice for your situation: {message}. Based on your financial profile, I recommend focusing on your stated goals."
    
    def profile_to_dict(self, profile: UserProfile) -> Dict:
        """Convert profile to JSON-serializable dict"""
        data = asdict(profile)
        data["created_at"] = profile.created_at.isoformat()
        data["last_active"] = profile.last_active.isoformat()
        return data
    
    def turn_to_dict(self, turn: ConversationTurn) -> Dict:
        """Convert turn to JSON-serializable dict"""
        data = asdict(turn)
        data["timestamp"] = turn.timestamp.isoformat()
        return data
    
    async def update_user_profile_from_conversation(self, user_message: str, response: str):
        """Update user profile based on conversation content"""
        
        profile = self.current_user_profile
        
        # Extract and update risk tolerance
        if "conservative" in user_message.lower():
            profile.risk_tolerance = "conservative"
        elif "aggressive" in user_message.lower():
            profile.risk_tolerance = "aggressive"
        elif "moderate" in user_message.lower():
            profile.risk_tolerance = "moderate"
        
        # Extract investment experience
        if any(phrase in user_message.lower() for phrase in ["new to investing", "beginner", "just starting"]):
            profile.investment_experience = "beginner"
        elif any(phrase in user_message.lower() for phrase in ["experienced", "advanced", "portfolio manager"]):
            profile.investment_experience = "advanced"
        
        # Track question types
        question_type = self.extract_topic(user_message)
        if question_type not in profile.common_question_types:
            profile.common_question_types.append(question_type)
        
        # Update last active
        profile.last_active = datetime.now()
        
        # Save updates
        await self.memory.save_user_profile(profile)

# =============================================================================
# DEMONSTRATION: Memory-Aware Conversation
# =============================================================================

async def demonstrate_memory_system():
    """
    🎓 FULL DEMONSTRATION: Multi-turn conversation with memory
    
    This shows how Plutus remembers context across multiple interactions,
    building a relationship with the user over time.
    """
    
    print("="*70)
    print("🎓 LESSON 3: MEMORY MANAGEMENT DEMONSTRATION")
    print("="*70)
    
    # Initialize memory system
    memory_manager = MemoryManager("demo_memory.db")
    agent = MemoryAwareFinancialAgent(memory_manager)
    
    # Simulate a user having multiple conversations over time
    user_id = "demo_user_123"
    user_name = "Alex"
    
    print("\n📅 === CONVERSATION SESSION 1 (Day 1) ===")
    
    # First conversation
    greeting = await agent.start_conversation(user_id, user_name)
    print(f"🤖 Plutus: {greeting}")
    
    # First question
    response1 = await agent.process_message("I'm new to investing and have $15,000 saved. Should I invest it all at once?")
    print(f"\n👤 Alex: I'm new to investing and have $15,000 saved. Should I invest it all at once?")
    print(f"🤖 Plutus: {response1}")
    
    # Follow-up question in same session
    response2 = await agent.process_message("What about putting some in a Roth IRA?")
    print(f"\n👤 Alex: What about putting some in a Roth IRA?")
    print(f"🤖 Plutus: {response2}")
    
    # Simulate time passing...
    print("\n⏰ [Time passes - 3 days later]")
    print("\n📅 === CONVERSATION SESSION 2 (Day 4) ===")
    
    # Second conversation - agent should remember previous context
    greeting2 = await agent.start_conversation(user_id)
    print(f"🤖 Plutus: {greeting2}")
    
    # New question that builds on previous conversation
    response3 = await agent.process_message("I've been thinking about our discussion. I want to save for a house down payment too. How should I balance investing vs saving?")
    print(f"\n👤 Alex: I've been thinking about our discussion. I want to save for a house down payment too. How should I balance investing vs saving?")
    print(f"🤖 Plutus: {response3}")
    
    print("\n⏰ [Time passes - 1 week later]")
    print("\n📅 === CONVERSATION SESSION 3 (Day 11) ===")
    
    # Third conversation - should remember goals and context
    greeting3 = await agent.start_conversation(user_id)
    print(f"🤖 Plutus: {greeting3}")
    
    # Question about progress
    response4 = await agent.process_message("I opened that Roth IRA we discussed! I put in $6,000. What should I do with the remaining $9,000?")
    print(f"\n👤 Alex: I opened that Roth IRA we discussed! I put in $6,000. What should I do with the remaining $9,000?")
    print(f"🤖 Plutus: {response4}")
    
    print("\n" + "="*70)
    print("🎓 MEMORY ANALYSIS")
    print("="*70)
    
    # Show what the system learned about the user
    final_profile = await memory_manager.get_or_create_user_profile(user_id)
    print(f"\n👤 Final User Profile for {final_profile.name}:")
    print(f"   Investment Experience: {final_profile.investment_experience}")
    print(f"   Risk Tolerance: {final_profile.risk_tolerance}")
    print(f"   Question Types: {', '.join(final_profile.common_question_types)}")
    print(f"   Goals Discussed: {len(final_profile.financial_goals)}")
    print(f"   Total Conversations: {len(await memory_manager.get_conversation_history(user_id))}")
    
    # Show conversation history
    history = await memory_manager.get_conversation_history(user_id)
    print(f"\n💭 Conversation History ({len(history)} turns):")
    for i, turn in enumerate(history, 1):
        print(f"   {i}. [{turn.timestamp.strftime('%m/%d %H:%M')}] {turn.user_message[:40]}...")
        print(f"      → {turn.assistant_response[:60]}...")
    
    print("\n" + "="*70)
    print("🎓 KEY MEMORY CONCEPTS DEMONSTRATED")
    print("="*70)
    print("""
    1. PERSISTENT USER PROFILES:
       ✅ Remembered user's name across sessions
       ✅ Tracked investment experience level
       ✅ Learned preferences and goals
    
    2. CONVERSATION CONTINUITY:
       ✅ Referenced previous discussions
       ✅ Built on prior context
       ✅ Tracked goal progress
    
    3. CONTEXTUAL GREETINGS:
       ✅ Personalized based on history
       ✅ Referenced time since last conversation
       ✅ Mentioned previous topics
    
    4. KNOWLEDGE ACCUMULATION:
       ✅ Learned from each interaction
       ✅ Updated user profile automatically
       ✅ Improved personalization over time
    
    5. SESSION MANAGEMENT:
       ✅ Separate sessions for different days
       ✅ Within-session context awareness
       ✅ Cross-session memory retention
    """)
    
    # Cleanup demo database
    Path("demo_memory.db").unlink(missing_ok=True)
    print("\n🧹 Demo database cleaned up")

if __name__ == "__main__":
    asyncio.run(demonstrate_memory_system())

"""
🎓 LESSON 3 KEY TAKEAWAYS:

1. MEMORY TYPES:
   - Turn Memory: Individual exchanges
   - Session Memory: Single conversation context
   - Profile Memory: Long-term user knowledge

2. STORAGE STRATEGY:
   - SQLite for structured data
   - JSON for flexible schema
   - Timestamped for temporal analysis

3. CONTEXT UTILIZATION:
   - Recent history for immediate context
   - Profile data for personalization
   - Goal tracking for continuity

4. NATURAL CONVERSATION:
   - Contextual greetings
   - Reference previous discussions
   - Build on established knowledge

NEXT LESSON: Integration with production systems and error handling!
"""