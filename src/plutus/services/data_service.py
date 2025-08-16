"""
Plutus Data Service
==================

Handles loading and managing sample user data and questions.
In production, this will interface with Wealthify's database.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

from ..core.config import get_config
from ..models.state import UserContext

logger = logging.getLogger(__name__)

class PlutusDataService:
    """
    Data service for loading user data and test questions
    
    Currently uses flat files, will be replaced with Wealthify database integration
    """
    
    def __init__(self):
        self.config = get_config()
        self._users_cache: Optional[Dict[str, Any]] = None
        self._questions_cache: Optional[Dict[str, Any]] = None
    
    async def load_sample_users(self) -> Dict[str, Any]:
        """Load sample users from JSON file"""
        
        if self._users_cache is None:
            try:
                with open(self.config.sample_users_path, 'r') as f:
                    self._users_cache = json.load(f)
                logger.info(f"Loaded {len(self._users_cache['users'])} sample users")
            except FileNotFoundError:
                logger.error(f"Sample users file not found: {self.config.sample_users_path}")
                self._users_cache = {"users": []}
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing sample users JSON: {e}")
                self._users_cache = {"users": []}
        
        return self._users_cache
    
    async def load_sample_questions(self) -> Dict[str, Any]:
        """Load sample questions from JSON file"""
        
        if self._questions_cache is None:
            try:
                with open(self.config.sample_questions_path, 'r') as f:
                    self._questions_cache = json.load(f)
                logger.info(f"Loaded {len(self._questions_cache['questions'])} sample questions")
            except FileNotFoundError:
                logger.error(f"Sample questions file not found: {self.config.sample_questions_path}")
                self._questions_cache = {"questions": []}
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing sample questions JSON: {e}")
                self._questions_cache = {"questions": []}
        
        return self._questions_cache
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user data by user ID"""
        
        users_data = await self.load_sample_users()
        
        for user in users_data.get("users", []):
            if user["user_id"] == user_id:
                return user
        
        logger.warning(f"User not found: {user_id}")
        return None
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all sample users"""
        
        users_data = await self.load_sample_users()
        return users_data.get("users", [])
    
    async def get_user_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's financial accounts"""
        
        user = await self.get_user_by_id(user_id)
        if user:
            return user.get("accounts", [])
        return []
    
    async def get_user_goals(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's financial goals"""
        
        user = await self.get_user_by_id(user_id)
        if user:
            return user.get("goals", [])
        return []
    
    async def get_user_wealth_health(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's wealth health score and components"""
        
        user = await self.get_user_by_id(user_id)
        if user:
            return user.get("wealth_health")
        return None
    
    async def calculate_user_net_worth(self, user_id: str) -> float:
        """Calculate user's net worth from accounts"""
        
        accounts = await self.get_user_accounts(user_id)
        
        assets = 0.0
        liabilities = 0.0
        
        for account in accounts:
            balance = account.get("balance", 0)
            account_type = account.get("type", "")
            
            if account_type in ["mortgage", "student_loan", "credit_card"]:
                # These are typically negative balances (liabilities)
                liabilities += abs(balance)
            else:
                # Assets (checking, savings, investments, real estate)
                assets += balance
        
        return assets - liabilities
    
    async def build_user_context(self, user_id: str) -> UserContext:
        """
        Build comprehensive user context from sample data
        
        In production, this will aggregate data from multiple Wealthify tables
        """
        
        user = await self.get_user_by_id(user_id)
        if not user:
            return UserContext(user_id=user_id)
        
        # Calculate derived metrics
        net_worth = await self.calculate_user_net_worth(user_id)
        accounts = await self.get_user_accounts(user_id)
        goals = await self.get_user_goals(user_id)
        wealth_health = await self.get_user_wealth_health(user_id)
        
        # Build context
        context = UserContext(
            user_id=user_id,
            name=user.get("name"),
            age=user.get("age"),
            location=user.get("location"),
            
            # Financial data
            accounts=accounts,
            net_worth=net_worth,
            monthly_income=user.get("monthly_income", 0),
            monthly_expenses=user.get("monthly_expenses", 0),
            
            # Goals
            goals=goals,
            goal_progress={goal["goal_id"]: goal.get("current_amount", 0) / max(goal.get("target_amount", 1), 1) 
                          for goal in goals},
            
            # Wealth health
            wealth_health_score=wealth_health.get("overall_score", 0) if wealth_health else 0,
            component_scores=wealth_health.get("component_scores", {}) if wealth_health else {},
            
            # Behavioral
            risk_tolerance=user.get("risk_tolerance"),
            investment_experience=user.get("investment_experience"),
            financial_personality=user.get("financial_behavior", {}),
            
            # Preferences
            preferences=user.get("preferences", {}),
            
            # Calculate completeness
            completeness_score=self._calculate_context_completeness(user)
        )
        
        logger.info(f"Built context for user {user_id}: {context.completeness_score:.1%} complete")
        return context
    
    def _calculate_context_completeness(self, user_data: Dict[str, Any]) -> float:
        """Calculate how complete the user context is (0.0 to 1.0)"""
        
        # Define required fields and their weights
        required_fields = {
            "name": 0.1,
            "age": 0.1,
            "monthly_income": 0.2,
            "monthly_expenses": 0.1,
            "risk_tolerance": 0.1,
            "accounts": 0.2,
            "goals": 0.15,
            "wealth_health": 0.05
        }
        
        total_score = 0.0
        
        for field, weight in required_fields.items():
            if field in user_data and user_data[field]:
                if field == "accounts":
                    # Give partial credit based on number of accounts
                    account_count = len(user_data[field])
                    total_score += weight * min(1.0, account_count / 3)  # Full credit for 3+ accounts
                elif field == "goals":
                    # Give partial credit based on number of goals
                    goal_count = len(user_data[field])
                    total_score += weight * min(1.0, goal_count / 2)  # Full credit for 2+ goals
                else:
                    total_score += weight
        
        return total_score
    
    async def get_questions_by_complexity(self, complexity: str) -> List[Dict[str, Any]]:
        """Get questions filtered by complexity level"""
        
        questions_data = await self.load_sample_questions()
        questions = questions_data.get("questions", [])
        
        return [q for q in questions if q.get("complexity") == complexity]
    
    async def get_questions_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get questions filtered by category"""
        
        questions_data = await self.load_sample_questions()
        questions = questions_data.get("questions", [])
        
        return [q for q in questions if category in q.get("category", [])]
    
    async def get_random_questions(self, count: int = 10, 
                                 complexity: Optional[str] = None,
                                 category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get random sample of questions with optional filters"""
        
        import random
        
        questions_data = await self.load_sample_questions()
        questions = questions_data.get("questions", [])
        
        # Apply filters
        if complexity:
            questions = [q for q in questions if q.get("complexity") == complexity]
        
        if category:
            questions = [q for q in questions if category in q.get("category", [])]
        
        # Return random sample
        sample_size = min(count, len(questions))
        return random.sample(questions, sample_size) if questions else []

# Global instance
data_service = PlutusDataService()

def get_data_service() -> PlutusDataService:
    """Get the global data service instance"""
    return data_service