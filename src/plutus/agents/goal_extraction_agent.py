"""
Goal Extraction Agent - Phase 3 Advanced Agent
==============================================

This agent specializes in extracting, analyzing, and updating financial goals
from user conversations. It can identify new goals, update existing ones,
and track progress towards goal completion.

Key Capabilities:
1. Extract goals from natural language conversations
2. Categorize goals by type (retirement, emergency fund, house, etc.)
3. Identify target amounts, deadlines, and priority levels
4. Update existing goals based on user input
5. Track goal progress and suggest adjustments
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import re

from .base_agent import BaseAgent
from ..models.state import ConversationState, UserContext
from ..core.config import get_config

logger = logging.getLogger(__name__)


class GoalExtractionAgent(BaseAgent):
    """
    Advanced agent for extracting and managing financial goals from conversations.
    
    This agent uses sophisticated NLP to understand user intent around goals
    and maintains a comprehensive goal management system.
    """
    
    def __init__(self):
        super().__init__()
        self.agent_name = "Goal Extraction Agent"
        self.agent_type = "goal_extraction"
        self.config = get_config()
        
        # Goal types and their characteristics
        self.goal_types = {
            "emergency_fund": {
                "typical_amount_range": (1000, 50000),
                "typical_timeline_months": (3, 24),
                "priority": "high",
                "description": "Emergency fund for unexpected expenses"
            },
            "retirement": {
                "typical_amount_range": (100000, 2000000),
                "typical_timeline_months": (120, 480),  # 10-40 years
                "priority": "high",
                "description": "Long-term retirement savings"
            },
            "house_purchase": {
                "typical_amount_range": (20000, 200000),  # Down payment
                "typical_timeline_months": (12, 60),
                "priority": "medium",
                "description": "Home down payment savings"
            },
            "vacation": {
                "typical_amount_range": (1000, 20000),
                "typical_timeline_months": (3, 18),
                "priority": "low",
                "description": "Vacation or travel fund"
            },
            "debt_payoff": {
                "typical_amount_range": (1000, 100000),
                "typical_timeline_months": (6, 60),
                "priority": "high",
                "description": "Pay off existing debt"
            },
            "education": {
                "typical_amount_range": (5000, 100000),
                "typical_timeline_months": (12, 48),
                "priority": "medium",
                "description": "Education or training expenses"
            },
            "investment": {
                "typical_amount_range": (1000, 500000),
                "typical_timeline_months": (6, 120),
                "priority": "medium",
                "description": "Investment opportunity fund"
            },
            "car_purchase": {
                "typical_amount_range": (5000, 80000),
                "typical_timeline_months": (6, 36),
                "priority": "medium",
                "description": "Vehicle purchase fund"
            }
        }
        
        # Keywords for goal identification
        self.goal_keywords = {
            "emergency_fund": ["emergency", "emergency fund", "safety net", "rainy day", "unexpected"],
            "retirement": ["retirement", "retire", "401k", "pension", "IRA", "retirement fund"],
            "house_purchase": ["house", "home", "down payment", "mortgage", "buy a house", "property"],
            "vacation": ["vacation", "travel", "trip", "holiday", "cruise", "flight"],
            "debt_payoff": ["debt", "pay off", "credit card", "loan", "student loan", "mortgage"],
            "education": ["education", "school", "college", "training", "course", "certification"],
            "investment": ["invest", "investment", "stocks", "portfolio", "trading", "market"],
            "car_purchase": ["car", "vehicle", "auto", "truck", "motorcycle", "transportation"]
        }
    
    async def process(self, state: ConversationState) -> Dict[str, Any]:
        """
        Extract and analyze goals from the conversation state.
        
        Args:
            state: Current conversation state
            
        Returns:
            Dictionary containing extracted goals and analysis
        """
        
        try:
            logger.info(f"🎯 Goal Extraction Agent processing message...")
            
            user_message = state.get("user_message", "")
            user_context = state.get("user_context", {})
            
            # 1. Analyze message for goal-related content
            goal_analysis = await self._analyze_message_for_goals(user_message)
            
            # 2. Extract specific goals mentioned
            extracted_goals = await self._extract_goals_from_text(user_message)
            
            # 3. Compare with existing user goals
            existing_goals = user_context.get("goals", [])
            goal_updates = await self._identify_goal_updates(extracted_goals, existing_goals)
            
            # 4. Generate goal recommendations
            goal_recommendations = await self._generate_goal_recommendations(
                user_context, extracted_goals
            )
            
            # 5. Create response
            response_text = await self._generate_goal_response(
                goal_analysis, extracted_goals, goal_updates, goal_recommendations
            )
            
            # 6. Prepare agent results
            agent_result = {
                "agent_name": self.agent_name,
                "agent_type": self.agent_type,
                "success": True,
                "response": response_text,
                "analysis": {
                    "goal_related": goal_analysis["is_goal_related"],
                    "goal_intent": goal_analysis["intent"],
                    "confidence": goal_analysis["confidence"],
                    "extracted_goals": extracted_goals,
                    "goal_updates": goal_updates,
                    "recommendations": goal_recommendations
                },
                "processing_time": 0.0,  # Will be calculated by base class
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"✅ Goal Extraction Agent completed analysis")
            return agent_result
            
        except Exception as e:
            logger.error(f"❌ Goal Extraction Agent error: {e}")
            return self._create_error_response(f"Goal extraction failed: {str(e)}")
    
    async def _analyze_message_for_goals(self, message: str) -> Dict[str, Any]:
        """Analyze if the message is related to financial goals"""
        
        message_lower = message.lower()
        
        # Check for goal-related keywords
        goal_keywords_found = []
        for goal_type, keywords in self.goal_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    goal_keywords_found.append((goal_type, keyword))
        
        # Check for goal-related verbs and phrases
        goal_verbs = ["want to", "planning to", "hoping to", "saving for", "goal", "target", "aim"]
        goal_verbs_found = [verb for verb in goal_verbs if verb in message_lower]
        
        # Check for amounts and timeframes
        amount_pattern = r'\$[\d,]+|\b\d+\s*(?:thousand|million|k|m)\b'
        amounts_found = re.findall(amount_pattern, message_lower)
        
        time_pattern = r'\b(?:in\s+)?(\d+)\s*(year|month|week)s?\b'
        timeframes_found = re.findall(time_pattern, message_lower)
        
        # Determine if message is goal-related
        is_goal_related = bool(goal_keywords_found or goal_verbs_found)
        
        # Determine intent
        intent = "unknown"
        if any("save" in message_lower or "saving" in message_lower for _ in [1]):
            intent = "saving_for_goal"
        elif any("plan" in message_lower or "planning" in message_lower for _ in [1]):
            intent = "planning_goal"
        elif any("want" in message_lower or "hoping" in message_lower for _ in [1]):
            intent = "expressing_goal"
        elif any("how much" in message_lower or "when" in message_lower for _ in [1]):
            intent = "asking_about_goal"
        elif goal_keywords_found:
            intent = "discussing_goal"
        
        # Calculate confidence
        confidence = 0.0
        if goal_keywords_found:
            confidence += 0.4
        if goal_verbs_found:
            confidence += 0.3
        if amounts_found:
            confidence += 0.2
        if timeframes_found:
            confidence += 0.1
        
        confidence = min(confidence, 1.0)
        
        return {
            "is_goal_related": is_goal_related,
            "intent": intent,
            "confidence": confidence,
            "keywords_found": goal_keywords_found,
            "verbs_found": goal_verbs_found,
            "amounts_found": amounts_found,
            "timeframes_found": timeframes_found
        }
    
    async def _extract_goals_from_text(self, message: str) -> List[Dict[str, Any]]:
        """Extract specific goals mentioned in the text"""
        
        extracted_goals = []
        message_lower = message.lower()
        
        # Extract amounts
        amount_pattern = r'\$?([\d,]+(?:\.\d{2})?)\s*(?:thousand|million|k|m)?'
        amounts = []
        for match in re.finditer(amount_pattern, message_lower):
            amount_str = match.group(1).replace(',', '')
            try:
                amount = float(amount_str)
                # Handle k/m suffixes
                if 'thousand' in match.group(0) or 'k' in match.group(0):
                    amount *= 1000
                elif 'million' in match.group(0) or 'm' in match.group(0):
                    amount *= 1000000
                amounts.append(amount)
            except ValueError:
                continue
        
        # Extract timeframes
        time_pattern = r'(?:in\s+)?(\d+)\s*(year|month|week)s?'
        timeframes = []
        for match in re.finditer(time_pattern, message_lower):
            num = int(match.group(1))
            unit = match.group(2)
            if unit.startswith('year'):
                months = num * 12
            elif unit.startswith('month'):
                months = num
            else:  # weeks
                months = num / 4.33
            timeframes.append(months)
        
        # Try to match goals with amounts and timeframes
        for goal_type, keywords in self.goal_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    goal = {
                        "type": goal_type,
                        "description": self.goal_types[goal_type]["description"],
                        "mentioned_keyword": keyword,
                        "extracted_from": message,
                        "confidence": 0.8
                    }
                    
                    # Try to associate amount
                    if amounts:
                        goal["target_amount"] = amounts[0]  # Take first amount found
                        goal["confidence"] += 0.1
                    
                    # Try to associate timeframe
                    if timeframes:
                        goal["timeline_months"] = timeframes[0]  # Take first timeframe found
                        goal["confidence"] += 0.1
                    
                    extracted_goals.append(goal)
                    break  # Only one goal per type per message
        
        return extracted_goals
    
    async def _identify_goal_updates(self, extracted_goals: List[Dict], existing_goals: List[Dict]) -> List[Dict[str, Any]]:
        """Identify updates to existing goals"""
        
        updates = []
        
        for extracted_goal in extracted_goals:
            extracted_type = extracted_goal["type"]
            
            # Find matching existing goal
            matching_goal = None
            for existing_goal in existing_goals:
                if existing_goal.get("type") == extracted_type:
                    matching_goal = existing_goal
                    break
            
            if matching_goal:
                # Identify what changed
                changes = {}
                
                if "target_amount" in extracted_goal:
                    old_amount = matching_goal.get("target_amount", 0)
                    new_amount = extracted_goal["target_amount"]
                    if abs(new_amount - old_amount) > 100:  # Significant change
                        changes["target_amount"] = {
                            "old": old_amount,
                            "new": new_amount
                        }
                
                if "timeline_months" in extracted_goal:
                    old_timeline = matching_goal.get("timeline_months", 0)
                    new_timeline = extracted_goal["timeline_months"]
                    if abs(new_timeline - old_timeline) > 1:  # Significant change
                        changes["timeline_months"] = {
                            "old": old_timeline,
                            "new": new_timeline
                        }
                
                if changes:
                    updates.append({
                        "goal_type": extracted_type,
                        "goal_id": matching_goal.get("id"),
                        "changes": changes,
                        "update_type": "modification"
                    })
            else:
                # New goal
                updates.append({
                    "goal_type": extracted_type,
                    "goal_data": extracted_goal,
                    "update_type": "new_goal"
                })
        
        return updates
    
    async def _generate_goal_recommendations(self, user_context: Dict, extracted_goals: List[Dict]) -> List[Dict[str, Any]]:
        """Generate recommendations based on goals and user context"""
        
        recommendations = []
        
        # Check if user has emergency fund goal
        has_emergency_fund = any(
            goal.get("type") == "emergency_fund" 
            for goal in user_context.get("goals", []) + extracted_goals
        )
        
        if not has_emergency_fund:
            monthly_expenses = user_context.get("monthly_expenses", 3000)
            recommended_amount = monthly_expenses * 6  # 6 months of expenses
            
            recommendations.append({
                "type": "emergency_fund_recommendation",
                "priority": "high",
                "title": "Consider Building an Emergency Fund",
                "description": f"Based on your monthly expenses, consider saving ${recommended_amount:,.0f} for emergencies",
                "target_amount": recommended_amount,
                "timeline_months": 12,
                "reasoning": "Emergency funds provide financial security and peace of mind"
            })
        
        # Check retirement savings
        user_age = user_context.get("age", 30)
        monthly_income = user_context.get("monthly_income", 5000)
        
        if user_age < 50:  # Focus on retirement for younger users
            has_retirement_goal = any(
                goal.get("type") == "retirement"
                for goal in user_context.get("goals", []) + extracted_goals
            )
            
            if not has_retirement_goal:
                # Rule of thumb: save 10-15% of income for retirement
                recommended_monthly = monthly_income * 0.15
                years_to_retirement = 65 - user_age
                
                recommendations.append({
                    "type": "retirement_recommendation",
                    "priority": "high",
                    "title": "Start Retirement Savings",
                    "description": f"Consider saving ${recommended_monthly:,.0f}/month for retirement",
                    "monthly_contribution": recommended_monthly,
                    "timeline_months": years_to_retirement * 12,
                    "reasoning": "Starting early gives your money more time to grow through compound interest"
                })
        
        # Analyze goal prioritization for multiple goals
        if len(extracted_goals) > 1:
            prioritized_goals = sorted(
                extracted_goals,
                key=lambda g: self.goal_types[g["type"]]["priority"] == "high",
                reverse=True
            )
            
            recommendations.append({
                "type": "goal_prioritization",
                "priority": "medium",
                "title": "Consider Goal Prioritization",
                "description": "With multiple goals, focus on high-priority ones first",
                "suggested_order": [goal["type"] for goal in prioritized_goals],
                "reasoning": "Prioritizing goals helps ensure you achieve the most important ones first"
            })
        
        return recommendations
    
    async def _generate_goal_response(
        self, 
        analysis: Dict, 
        extracted_goals: List[Dict], 
        updates: List[Dict], 
        recommendations: List[Dict]
    ) -> str:
        """Generate a natural language response about goals"""
        
        if not analysis["is_goal_related"]:
            return ""
        
        response_parts = []
        
        # Acknowledge goal discussion
        if analysis["intent"] == "expressing_goal":
            response_parts.append("I understand you're thinking about your financial goals.")
        elif analysis["intent"] == "planning_goal":
            response_parts.append("It's great that you're planning ahead for your financial goals.")
        elif analysis["intent"] == "asking_about_goal":
            response_parts.append("Let me help you with your goal planning question.")
        
        # Discuss extracted goals
        if extracted_goals:
            for goal in extracted_goals:
                goal_type = goal["type"].replace("_", " ").title()
                response_parts.append(f"I see you're interested in {goal_type.lower()}.")
                
                if "target_amount" in goal:
                    amount = goal["target_amount"]
                    response_parts.append(f"Your target of ${amount:,.0f} is noted.")
                
                if "timeline_months" in goal:
                    months = goal["timeline_months"]
                    if months < 12:
                        timeframe = f"{months:.0f} months"
                    else:
                        timeframe = f"{months/12:.1f} years"
                    response_parts.append(f"Your timeline of {timeframe} gives us a clear target to work with.")
        
        # Mention updates
        if updates:
            new_goals = [u for u in updates if u["update_type"] == "new_goal"]
            modifications = [u for u in updates if u["update_type"] == "modification"]
            
            if new_goals:
                response_parts.append(f"I'll help you track {len(new_goals)} new goal(s).")
            
            if modifications:
                response_parts.append("I've noted the updates to your existing goals.")
        
        # Share recommendations
        if recommendations:
            high_priority_recs = [r for r in recommendations if r["priority"] == "high"]
            if high_priority_recs:
                rec = high_priority_recs[0]
                response_parts.append(f"💡 {rec['title']}: {rec['description']}")
        
        if not response_parts:
            response_parts.append("I'm here to help you plan and achieve your financial goals.")
        
        return " ".join(response_parts)
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create error response"""
        return {
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "success": False,
            "error": error_message,
            "response": "I encountered an issue while analyzing your goals. Please try again.",
            "processing_time": 0.0,
            "timestamp": datetime.utcnow().isoformat()
        }