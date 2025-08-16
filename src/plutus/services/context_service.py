"""
Plutus Context Service
=====================

Manages user context building, caching, and updates.
Integrates with the memory system and provides rich context for agents.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import asdict

from ..core.config import get_config
from ..models.state import UserContext, ConversationState
from ..services.data_service import get_data_service

logger = logging.getLogger(__name__)

class ContextService:
    """
    Service for managing user context and conversation state
    
    Responsibilities:
    - Build comprehensive user context from multiple sources
    - Cache context for performance
    - Update context based on conversations
    - Provide context-aware insights
    """
    
    def __init__(self):
        self.config = get_config()
        self.data_service = get_data_service()
        self._context_cache: Dict[str, UserContext] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
    
    async def get_user_context(self, user_id: str, force_refresh: bool = False) -> UserContext:
        """
        Get comprehensive user context with caching
        
        Args:
            user_id: The user identifier
            force_refresh: Whether to bypass cache and rebuild context
            
        Returns:
            UserContext object with all available user information
        """
        
        # Check cache first (unless force refresh)
        if not force_refresh and self._is_context_cached_and_fresh(user_id):
            logger.debug(f"Returning cached context for user {user_id}")
            return self._context_cache[user_id]
        
        logger.info(f"Building fresh context for user {user_id}")
        
        # Build context from data sources
        context = await self._build_fresh_context(user_id)
        
        # Cache the context
        self._context_cache[user_id] = context
        self._cache_timestamps[user_id] = datetime.now()
        
        return context
    
    def _is_context_cached_and_fresh(self, user_id: str) -> bool:
        """Check if context is cached and still fresh"""
        
        if user_id not in self._context_cache:
            return False
        
        if user_id not in self._cache_timestamps:
            return False
        
        # Check if cache is still fresh
        cache_age = datetime.now() - self._cache_timestamps[user_id]
        max_age = timedelta(seconds=self.config.context_ttl_seconds)
        
        return cache_age < max_age
    
    async def _build_fresh_context(self, user_id: str) -> UserContext:
        """Build fresh user context from all available sources"""
        
        # Get base context from data service
        context = await self.data_service.build_user_context(user_id)
        
        # Enhance with conversation insights
        context = await self._enhance_with_conversation_insights(context)
        
        # Add real-time analysis
        context = await self._add_realtime_analysis(context)
        
        return context
    
    async def _enhance_with_conversation_insights(self, context: UserContext) -> UserContext:
        """
        Enhance context with insights from previous conversations
        
        In production, this would query the conversation database
        """
        
        # For now, add some sample conversation insights
        context.recent_topics = [
            "retirement planning",
            "emergency fund",
            "investment allocation"
        ]
        
        context.common_questions = [
            "How much should I save for retirement?",
            "What's my investment risk level?",
            "Should I pay off debt or invest?"
        ]
        
        return context
    
    async def _add_realtime_analysis(self, context: UserContext) -> UserContext:
        """Add real-time financial analysis to context"""
        
        try:
            # Calculate financial health metrics
            if context.monthly_income > 0 and context.monthly_expenses > 0:
                savings_rate = (context.monthly_income - context.monthly_expenses) / context.monthly_income
                
                # Add to financial personality
                if savings_rate > 0.2:
                    context.financial_personality["savings_behavior"] = "high_saver"
                elif savings_rate > 0.1:
                    context.financial_personality["savings_behavior"] = "moderate_saver"
                else:
                    context.financial_personality["savings_behavior"] = "low_saver"
                
                context.financial_personality["savings_rate"] = savings_rate
            
            # Analyze goal progress
            if context.goals:
                on_track_goals = 0
                for goal in context.goals:
                    goal_id = goal.get("goal_id", "")
                    if goal_id in context.goal_progress:
                        if context.goal_progress[goal_id] > 0.1:  # More than 10% progress
                            on_track_goals += 1
                
                context.financial_personality["goal_achievement"] = on_track_goals / len(context.goals)
            
            # Update context version and timestamp
            context.context_version += 1
            context.last_updated = datetime.now()
            
        except Exception as e:
            logger.error(f"Error in real-time analysis: {e}")
        
        return context
    
    async def update_context_from_conversation(self, 
                                             user_id: str, 
                                             conversation_state: ConversationState) -> None:
        """
        Update user context based on conversation insights
        
        Args:
            user_id: User identifier
            conversation_state: Current conversation state with agent results
        """
        
        try:
            # Get current context
            context = await self.get_user_context(user_id)
            
            # Extract insights from conversation
            insights = self._extract_conversation_insights(conversation_state)
            
            # Update context with new insights
            context = await self._apply_insights_to_context(context, insights)
            
            # Update cache
            self._context_cache[user_id] = context
            self._cache_timestamps[user_id] = datetime.now()
            
            logger.info(f"Updated context for user {user_id} with {len(insights)} new insights")
            
        except Exception as e:
            logger.error(f"Error updating context from conversation: {e}")
    
    def _extract_conversation_insights(self, state: ConversationState) -> Dict[str, Any]:
        """Extract insights from conversation state"""
        
        insights = {
            "topics_discussed": [],
            "goals_mentioned": [],
            "concerns_expressed": [],
            "preferences_indicated": [],
            "financial_details_shared": {}
        }
        
        user_message = state["user_message"].lower()
        
        # Extract topics
        financial_keywords = {
            "retirement": "retirement planning",
            "invest": "investment strategy", 
            "house": "home purchase",
            "debt": "debt management",
            "emergency": "emergency planning",
            "college": "education planning"
        }
        
        for keyword, topic in financial_keywords.items():
            if keyword in user_message:
                insights["topics_discussed"].append(topic)
        
        # Extract concerns
        concern_keywords = ["worried", "concerned", "afraid", "nervous", "risk"]
        if any(word in user_message for word in concern_keywords):
            insights["concerns_expressed"].append("expressed financial anxiety")
        
        # Extract preferences
        if any(word in user_message for word in ["conservative", "safe", "careful"]):
            insights["preferences_indicated"].append("conservative_approach")
        elif any(word in user_message for word in ["aggressive", "growth", "risky"]):
            insights["preferences_indicated"].append("aggressive_approach")
        
        return insights
    
    async def _apply_insights_to_context(self, 
                                       context: UserContext, 
                                       insights: Dict[str, Any]) -> UserContext:
        """Apply extracted insights to user context"""
        
        # Update recent topics
        new_topics = insights.get("topics_discussed", [])
        for topic in new_topics:
            if topic not in context.recent_topics:
                context.recent_topics.append(topic)
        
        # Keep only recent topics (last 10)
        context.recent_topics = context.recent_topics[-10:]
        
        # Update financial personality
        preferences = insights.get("preferences_indicated", [])
        for preference in preferences:
            if preference == "conservative_approach":
                context.financial_personality["observed_risk_tolerance"] = "conservative"
            elif preference == "aggressive_approach":
                context.financial_personality["observed_risk_tolerance"] = "aggressive"
        
        # Update concerns
        concerns = insights.get("concerns_expressed", [])
        if "financial_anxiety" not in context.financial_personality:
            context.financial_personality["financial_anxiety"] = []
        
        for concern in concerns:
            if concern not in context.financial_personality["financial_anxiety"]:
                context.financial_personality["financial_anxiety"].append(concern)
        
        # Update metadata
        context.last_updated = datetime.now()
        context.context_version += 1
        
        return context
    
    async def get_context_summary(self, user_id: str) -> Dict[str, Any]:
        """Get a summary of user context for agent consumption"""
        
        context = await self.get_user_context(user_id)
        
        summary = {
            "user_profile": {
                "name": context.name,
                "age": context.age,
                "risk_tolerance": context.risk_tolerance,
                "investment_experience": context.investment_experience,
                "location": context.location
            },
            
            "financial_snapshot": {
                "net_worth": context.net_worth,
                "monthly_income": context.monthly_income,
                "monthly_expenses": context.monthly_expenses,
                "wealth_health_score": context.wealth_health_score,
                "component_scores": context.component_scores
            },
            
            "goals_overview": {
                "total_goals": len(context.goals),
                "active_goals": [goal for goal in context.goals if goal.get("status") != "completed"],
                "goal_categories": list(set(goal.get("category", "") for goal in context.goals))
            },
            
            "account_summary": {
                "total_accounts": len(context.accounts),
                "account_types": list(set(account.get("type", "") for account in context.accounts)),
                "has_investment_accounts": any(
                    account.get("type") in ["401k", "roth_ira", "traditional_ira", "brokerage"] 
                    for account in context.accounts
                ),
                "has_debt": any(
                    account.get("balance", 0) < 0 
                    for account in context.accounts
                )
            },
            
            "conversation_context": {
                "recent_topics": context.recent_topics,
                "common_questions": context.common_questions,
                "communication_preferences": context.preferences
            },
            
            "behavioral_insights": context.financial_personality,
            
            "metadata": {
                "completeness_score": context.completeness_score,
                "context_version": context.context_version,
                "last_updated": context.last_updated.isoformat()
            }
        }
        
        return summary
    
    async def clear_cache(self, user_id: Optional[str] = None) -> None:
        """Clear context cache for specific user or all users"""
        
        if user_id:
            self._context_cache.pop(user_id, None)
            self._cache_timestamps.pop(user_id, None)
            logger.info(f"Cleared context cache for user {user_id}")
        else:
            self._context_cache.clear()
            self._cache_timestamps.clear()
            logger.info("Cleared all context cache")

# Global instance
context_service = ContextService()

def get_context_service() -> ContextService:
    """Get the global context service instance"""
    return context_service