"""
Recommendation Agent - Phase 3 Advanced Agent
=============================================

This agent specializes in generating specific, actionable financial recommendations
based on user context, goals, and financial situation. It provides personalized
advice for wealth building, optimization, and financial decision-making.

Key Capabilities:
1. Generate personalized investment recommendations
2. Suggest debt payoff strategies
3. Recommend budget optimizations
4. Provide tax-efficient strategies
5. Suggest goal achievement pathways
6. Risk-adjusted portfolio recommendations
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json

from .base_agent import BaseAgent
from ..models.state import ConversationState, UserContext
from ..core.config import get_config

logger = logging.getLogger(__name__)


class RecommendationAgent(BaseAgent):
    """
    Advanced agent for generating personalized financial recommendations.
    
    This agent analyzes user's complete financial picture and provides
    specific, actionable advice tailored to their situation and goals.
    """
    
    def __init__(self):
        super().__init__()
        self.agent_name = "Recommendation Agent"
        self.agent_type = "recommendation"
        self.config = get_config()
        
        # Investment allocation models by risk tolerance
        self.allocation_models = {
            "conservative": {
                "stocks": 0.30,
                "bonds": 0.60,
                "cash": 0.10,
                "description": "Low risk, steady growth"
            },
            "moderate": {
                "stocks": 0.60,
                "bonds": 0.30,
                "cash": 0.10,
                "description": "Balanced risk and growth"
            },
            "aggressive": {
                "stocks": 0.80,
                "bonds": 0.15,
                "cash": 0.05,
                "description": "Higher risk, higher potential returns"
            }
        }
        
        # Debt payoff strategies
        self.debt_strategies = {
            "avalanche": {
                "description": "Pay minimum on all debts, then focus extra payments on highest interest rate debt",
                "best_for": "Mathematically optimal, saves most money on interest"
            },
            "snowball": {
                "description": "Pay minimum on all debts, then focus extra payments on smallest balance",
                "best_for": "Psychological motivation, builds momentum with quick wins"
            },
            "hybrid": {
                "description": "Combination approach based on balance size and interest rates",
                "best_for": "Balanced approach between savings and motivation"
            }
        }
        
        # Emergency fund recommendations
        self.emergency_fund_guidelines = {
            "stable_job": {"months": 3, "description": "3 months for stable employment"},
            "variable_income": {"months": 6, "description": "6 months for variable income"},
            "single_income": {"months": 6, "description": "6 months for single-income households"},
            "high_risk_job": {"months": 9, "description": "9 months for high-risk employment"}
        }
    
    async def process(self, state: ConversationState) -> Dict[str, Any]:
        """
        Generate personalized financial recommendations based on user context.
        
        Args:
            state: Current conversation state
            
        Returns:
            Dictionary containing recommendations and analysis
        """
        
        try:
            logger.info(f"💡 Recommendation Agent processing...")
            
            user_message = state.get("user_message", "")
            user_context = state.get("user_context", {})
            
            # 1. Analyze what type of recommendations are needed
            recommendation_needs = await self._analyze_recommendation_needs(user_message, user_context)
            
            # 2. Generate specific recommendations
            recommendations = await self._generate_recommendations(recommendation_needs, user_context)
            
            # 3. Prioritize recommendations
            prioritized_recommendations = await self._prioritize_recommendations(recommendations, user_context)
            
            # 4. Generate action plans
            action_plans = await self._create_action_plans(prioritized_recommendations, user_context)
            
            # 5. Create response
            response_text = await self._generate_recommendation_response(
                prioritized_recommendations, action_plans, user_context
            )
            
            # 6. Prepare agent results
            agent_result = {
                "agent_name": self.agent_name,
                "agent_type": self.agent_type,
                "success": True,
                "response": response_text,
                "analysis": {
                    "recommendation_needs": recommendation_needs,
                    "total_recommendations": len(recommendations),
                    "high_priority_count": len([r for r in prioritized_recommendations if r["priority"] == "high"]),
                    "categories": list(set(r["category"] for r in recommendations))
                },
                "recommendations": prioritized_recommendations,
                "action_plans": action_plans,
                "processing_time": 0.0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"✅ Recommendation Agent generated {len(recommendations)} recommendations")
            return agent_result
            
        except Exception as e:
            logger.error(f"❌ Recommendation Agent error: {e}")
            return self._create_error_response(f"Recommendation generation failed: {str(e)}")
    
    async def _analyze_recommendation_needs(self, message: str, user_context: Dict) -> Dict[str, Any]:
        """Analyze what types of recommendations the user needs"""
        
        message_lower = message.lower()
        
        # Categories of recommendations to consider
        needs = {
            "investment": False,
            "debt_management": False,
            "budgeting": False,
            "emergency_fund": False,
            "retirement": False,
            "tax_optimization": False,
            "goal_planning": False,
            "insurance": False
        }
        
        # Analyze message for specific needs
        if any(word in message_lower for word in ["invest", "investment", "portfolio", "stocks", "bonds"]):
            needs["investment"] = True
        
        if any(word in message_lower for word in ["debt", "loan", "credit card", "pay off", "payoff"]):
            needs["debt_management"] = True
        
        if any(word in message_lower for word in ["budget", "spending", "expenses", "save money"]):
            needs["budgeting"] = True
        
        if any(word in message_lower for word in ["emergency", "emergency fund", "safety net"]):
            needs["emergency_fund"] = True
        
        if any(word in message_lower for word in ["retirement", "401k", "ira", "retire"]):
            needs["retirement"] = True
        
        if any(word in message_lower for word in ["tax", "taxes", "tax-efficient", "deduction"]):
            needs["tax_optimization"] = True
        
        if any(word in message_lower for word in ["goal", "goals", "plan", "planning"]):
            needs["goal_planning"] = True
        
        # Analyze user context for implicit needs
        net_worth = user_context.get("net_worth", 0)
        monthly_income = user_context.get("monthly_income", 0)
        monthly_expenses = user_context.get("monthly_expenses", 0)
        
        # Emergency fund analysis
        emergency_fund_balance = self._calculate_emergency_fund_balance(user_context)
        recommended_emergency_fund = monthly_expenses * 6
        if emergency_fund_balance < recommended_emergency_fund:
            needs["emergency_fund"] = True
        
        # Investment analysis
        investment_accounts = [acc for acc in user_context.get("accounts", []) if acc.get("type") == "investment"]
        total_investment = sum(acc.get("balance", 0) for acc in investment_accounts)
        if total_investment < net_worth * 0.1:  # Less than 10% invested
            needs["investment"] = True
        
        # Debt analysis
        debt_accounts = [acc for acc in user_context.get("accounts", []) if acc.get("balance", 0) < 0]
        total_debt = sum(abs(acc.get("balance", 0)) for acc in debt_accounts)
        if total_debt > monthly_income * 3:  # More than 3 months of income in debt
            needs["debt_management"] = True
        
        # Retirement analysis
        age = user_context.get("age", 30)
        retirement_balance = sum(
            acc.get("balance", 0) for acc in user_context.get("accounts", [])
            if "401k" in acc.get("name", "").lower() or "ira" in acc.get("name", "").lower()
        )
        expected_retirement_balance = monthly_income * 12 * (age - 22) * 0.15  # 15% savings rate
        if retirement_balance < expected_retirement_balance * 0.5:
            needs["retirement"] = True
        
        return {
            "explicit_needs": {k: v for k, v in needs.items() if v and any(word in message_lower for word in ["invest", "debt", "budget", "emergency", "retirement", "tax", "goal"])},
            "implicit_needs": {k: v for k, v in needs.items() if v},
            "priority_order": self._prioritize_needs(needs, user_context)
        }
    
    async def _generate_recommendations(self, needs: Dict, user_context: Dict) -> List[Dict[str, Any]]:
        """Generate specific recommendations based on identified needs"""
        
        recommendations = []
        implicit_needs = needs.get("implicit_needs", {})
        
        # Emergency Fund Recommendations
        if implicit_needs.get("emergency_fund"):
            recommendations.extend(await self._generate_emergency_fund_recommendations(user_context))
        
        # Debt Management Recommendations
        if implicit_needs.get("debt_management"):
            recommendations.extend(await self._generate_debt_recommendations(user_context))
        
        # Investment Recommendations
        if implicit_needs.get("investment"):
            recommendations.extend(await self._generate_investment_recommendations(user_context))
        
        # Retirement Recommendations
        if implicit_needs.get("retirement"):
            recommendations.extend(await self._generate_retirement_recommendations(user_context))
        
        # Budgeting Recommendations
        if implicit_needs.get("budgeting"):
            recommendations.extend(await self._generate_budgeting_recommendations(user_context))
        
        # Goal Planning Recommendations
        if implicit_needs.get("goal_planning"):
            recommendations.extend(await self._generate_goal_planning_recommendations(user_context))
        
        # Tax Optimization Recommendations
        if implicit_needs.get("tax_optimization"):
            recommendations.extend(await self._generate_tax_recommendations(user_context))
        
        return recommendations
    
    async def _generate_emergency_fund_recommendations(self, user_context: Dict) -> List[Dict[str, Any]]:
        """Generate emergency fund recommendations"""
        
        recommendations = []
        monthly_expenses = user_context.get("monthly_expenses", 3000)
        current_emergency_fund = self._calculate_emergency_fund_balance(user_context)
        
        # Determine appropriate emergency fund size
        job_stability = user_context.get("job_stability", "stable_job")
        target_months = self.emergency_fund_guidelines.get(job_stability, {"months": 6})["months"]
        target_amount = monthly_expenses * target_months
        
        if current_emergency_fund < target_amount:
            shortfall = target_amount - current_emergency_fund
            monthly_savings_needed = shortfall / 12  # Build over 1 year
            
            recommendations.append({
                "id": "emergency_fund_build",
                "category": "emergency_fund",
                "priority": "high",
                "title": "Build Your Emergency Fund",
                "description": f"Increase your emergency fund from ${current_emergency_fund:,.0f} to ${target_amount:,.0f}",
                "target_amount": target_amount,
                "current_amount": current_emergency_fund,
                "monthly_contribution": monthly_savings_needed,
                "timeline_months": 12,
                "reasoning": f"Based on your expenses, you need {target_months} months of coverage for financial security",
                "specific_action": f"Set up automatic transfer of ${monthly_savings_needed:,.0f}/month to high-yield savings account"
            })
        
        return recommendations
    
    async def _generate_debt_recommendations(self, user_context: Dict) -> List[Dict[str, Any]]:
        """Generate debt management recommendations"""
        
        recommendations = []
        accounts = user_context.get("accounts", [])
        debt_accounts = [acc for acc in accounts if acc.get("balance", 0) < 0]
        
        if not debt_accounts:
            return recommendations
        
        total_debt = sum(abs(acc.get("balance", 0)) for acc in debt_accounts)
        monthly_income = user_context.get("monthly_income", 5000)
        
        # High interest debt check
        high_interest_debt = [
            acc for acc in debt_accounts 
            if acc.get("interest_rate", 0) > 15  # Credit cards typically
        ]
        
        if high_interest_debt:
            total_high_interest = sum(abs(acc.get("balance", 0)) for acc in high_interest_debt)
            
            recommendations.append({
                "id": "high_interest_debt_focus",
                "category": "debt_management",
                "priority": "high",
                "title": "Prioritize High-Interest Debt",
                "description": f"Focus on paying off ${total_high_interest:,.0f} in high-interest debt first",
                "debt_amount": total_high_interest,
                "strategy": "avalanche",
                "reasoning": "High-interest debt costs you significantly more over time",
                "specific_action": "Pay minimum on all debts, then put all extra payments toward highest interest rate debt"
            })
        
        # Debt consolidation analysis
        if len(debt_accounts) > 3:
            recommendations.append({
                "id": "debt_consolidation",
                "category": "debt_management",
                "priority": "medium",
                "title": "Consider Debt Consolidation",
                "description": "Consolidate multiple debts into a single lower-interest loan",
                "total_debt": total_debt,
                "reasoning": "Simplifies payments and may reduce overall interest rate",
                "specific_action": "Research personal loans or balance transfer cards with lower rates"
            })
        
        return recommendations
    
    async def _generate_investment_recommendations(self, user_context: Dict) -> List[Dict[str, Any]]:
        """Generate investment recommendations"""
        
        recommendations = []
        age = user_context.get("age", 30)
        risk_tolerance = user_context.get("risk_tolerance", "moderate")
        monthly_income = user_context.get("monthly_income", 5000)
        net_worth = user_context.get("net_worth", 0)
        
        # Investment allocation recommendation
        allocation = self.allocation_models.get(risk_tolerance, self.allocation_models["moderate"])
        
        investment_accounts = [acc for acc in user_context.get("accounts", []) if acc.get("type") == "investment"]
        total_investments = sum(acc.get("balance", 0) for acc in investment_accounts)
        
        # Recommend starting investments if none exist
        if total_investments < 1000:
            recommended_monthly = min(monthly_income * 0.15, 1000)  # 15% of income or $1000, whichever is less
            
            recommendations.append({
                "id": "start_investing",
                "category": "investment",
                "priority": "high",
                "title": "Start Your Investment Journey",
                "description": f"Begin investing ${recommended_monthly:,.0f}/month in diversified portfolio",
                "monthly_amount": recommended_monthly,
                "allocation": allocation,
                "reasoning": f"At age {age}, you have time for growth through compound interest",
                "specific_action": "Open investment account and set up automatic monthly contributions"
            })
        
        # Portfolio rebalancing recommendation
        elif total_investments > 10000:
            recommendations.append({
                "id": "portfolio_rebalancing",
                "category": "investment",
                "priority": "medium",
                "title": "Review Portfolio Allocation",
                "description": f"Consider rebalancing to match your {risk_tolerance} risk profile",
                "target_allocation": allocation,
                "current_value": total_investments,
                "reasoning": "Regular rebalancing maintains your desired risk level",
                "specific_action": "Review current holdings and adjust to target allocation"
            })
        
        return recommendations
    
    async def _generate_retirement_recommendations(self, user_context: Dict) -> List[Dict[str, Any]]:
        """Generate retirement savings recommendations"""
        
        recommendations = []
        age = user_context.get("age", 30)
        monthly_income = user_context.get("monthly_income", 5000)
        annual_income = monthly_income * 12
        
        # Find retirement accounts
        retirement_accounts = [
            acc for acc in user_context.get("accounts", [])
            if "401k" in acc.get("name", "").lower() or "ira" in acc.get("name", "").lower()
        ]
        total_retirement = sum(acc.get("balance", 0) for acc in retirement_accounts)
        
        # Rule of thumb: should have 1x annual salary by 30, 3x by 40, etc.
        target_multiplier = max(1, (age - 20) // 10)
        target_retirement_savings = annual_income * target_multiplier
        
        if total_retirement < target_retirement_savings:
            shortfall = target_retirement_savings - total_retirement
            recommended_monthly = annual_income * 0.15 / 12  # 15% of income
            
            recommendations.append({
                "id": "increase_retirement_savings",
                "category": "retirement",
                "priority": "high",
                "title": "Boost Retirement Savings",
                "description": f"Increase retirement savings to ${recommended_monthly:,.0f}/month",
                "current_amount": total_retirement,
                "target_amount": target_retirement_savings,
                "monthly_contribution": recommended_monthly,
                "reasoning": f"At age {age}, aim for {target_multiplier}x annual salary in retirement savings",
                "specific_action": "Increase 401(k) contribution or open IRA if not available"
            })
        
        # 401(k) match optimization
        employer_match = user_context.get("employer_401k_match", 0)
        current_401k_contribution = user_context.get("current_401k_contribution", 0)
        
        if employer_match > 0 and current_401k_contribution < employer_match:
            recommendations.append({
                "id": "maximize_employer_match",
                "category": "retirement",
                "priority": "high",
                "title": "Maximize Employer 401(k) Match",
                "description": f"Increase 401(k) contribution to get full employer match",
                "current_contribution": current_401k_contribution,
                "target_contribution": employer_match,
                "free_money": (employer_match - current_401k_contribution) * annual_income,
                "reasoning": "Employer match is free money - 100% return on investment",
                "specific_action": f"Increase 401(k) contribution to {employer_match * 100:.0f}% of salary"
            })
        
        return recommendations
    
    async def _generate_budgeting_recommendations(self, user_context: Dict) -> List[Dict[str, Any]]:
        """Generate budgeting and expense optimization recommendations"""
        
        recommendations = []
        monthly_income = user_context.get("monthly_income", 5000)
        monthly_expenses = user_context.get("monthly_expenses", 4000)
        
        savings_rate = (monthly_income - monthly_expenses) / monthly_income if monthly_income > 0 else 0
        
        # Low savings rate recommendation
        if savings_rate < 0.15:  # Less than 15% savings rate
            target_savings = monthly_income * 0.20  # Aim for 20%
            expense_reduction_needed = monthly_expenses - (monthly_income - target_savings)
            
            recommendations.append({
                "id": "increase_savings_rate",
                "category": "budgeting",
                "priority": "high",
                "title": "Optimize Your Savings Rate",
                "description": f"Increase savings rate from {savings_rate:.1%} to 20%",
                "current_savings_rate": savings_rate,
                "target_savings_rate": 0.20,
                "expense_reduction_needed": expense_reduction_needed,
                "reasoning": "Higher savings rate accelerates wealth building and financial independence",
                "specific_action": f"Reduce monthly expenses by ${expense_reduction_needed:,.0f} through budget review"
            })
        
        # Analyze spending categories
        recent_transactions = user_context.get("recent_transactions", [])
        if recent_transactions:
            spending_analysis = self._analyze_spending_patterns(recent_transactions)
            
            # Find high spending categories
            high_spending_categories = [
                cat for cat, amount in spending_analysis.items()
                if amount > monthly_income * 0.1  # More than 10% of income
            ]
            
            for category in high_spending_categories:
                if category not in ["rent", "mortgage", "utilities"]:  # Don't optimize essential expenses
                    recommendations.append({
                        "id": f"optimize_{category}_spending",
                        "category": "budgeting",
                        "priority": "medium",
                        "title": f"Review {category.title()} Spending",
                        "description": f"High spending in {category} category detected",
                        "monthly_amount": spending_analysis[category],
                        "percentage_of_income": spending_analysis[category] / monthly_income,
                        "reasoning": f"{category.title()} represents a large portion of your budget",
                        "specific_action": f"Review {category} expenses for potential savings opportunities"
                    })
        
        return recommendations
    
    async def _generate_goal_planning_recommendations(self, user_context: Dict) -> List[Dict[str, Any]]:
        """Generate goal planning recommendations"""
        
        recommendations = []
        goals = user_context.get("goals", [])
        
        if not goals:
            recommendations.append({
                "id": "set_financial_goals",
                "category": "goal_planning",
                "priority": "medium",
                "title": "Set Clear Financial Goals",
                "description": "Establish specific, measurable financial objectives",
                "reasoning": "Clear goals provide direction and motivation for financial decisions",
                "specific_action": "Define 3-5 specific financial goals with target amounts and deadlines"
            })
        else:
            # Analyze existing goals
            for goal in goals:
                target_amount = goal.get("target_amount", 0)
                current_amount = goal.get("current_amount", 0)
                target_date = goal.get("target_date")
                
                if target_date and target_amount > current_amount:
                    # Calculate if on track
                    from datetime import datetime
                    target_datetime = datetime.fromisoformat(target_date.replace("Z", "+00:00"))
                    months_remaining = max(1, (target_datetime - datetime.now()).days / 30.44)
                    
                    needed_monthly = (target_amount - current_amount) / months_remaining
                    
                    recommendations.append({
                        "id": f"goal_progress_{goal.get('id', 'unknown')}",
                        "category": "goal_planning",
                        "priority": "medium",
                        "title": f"Stay On Track: {goal.get('name', 'Goal')}",
                        "description": f"Save ${needed_monthly:,.0f}/month to reach your goal",
                        "goal_name": goal.get("name"),
                        "target_amount": target_amount,
                        "current_amount": current_amount,
                        "monthly_needed": needed_monthly,
                        "months_remaining": months_remaining,
                        "reasoning": "Consistent progress ensures you'll reach your goal on time",
                        "specific_action": f"Set up automatic transfer of ${needed_monthly:,.0f}/month to goal account"
                    })
        
        return recommendations
    
    async def _generate_tax_recommendations(self, user_context: Dict) -> List[Dict[str, Any]]:
        """Generate tax optimization recommendations"""
        
        recommendations = []
        annual_income = user_context.get("monthly_income", 5000) * 12
        
        # Tax-advantaged account recommendations
        retirement_contribution = user_context.get("current_401k_contribution", 0) * annual_income
        max_401k_contribution = 22500  # 2023 limit
        
        if retirement_contribution < max_401k_contribution:
            additional_contribution = min(
                max_401k_contribution - retirement_contribution,
                annual_income * 0.10  # Don't recommend more than 10% additional
            )
            
            tax_savings = additional_contribution * 0.22  # Assume 22% tax bracket
            
            recommendations.append({
                "id": "maximize_401k_tax_benefit",
                "category": "tax_optimization",
                "priority": "medium",
                "title": "Maximize Tax-Advantaged Savings",
                "description": f"Increase 401(k) contribution for ${tax_savings:,.0f} annual tax savings",
                "additional_contribution": additional_contribution,
                "tax_savings": tax_savings,
                "reasoning": "Pre-tax contributions reduce current taxable income",
                "specific_action": f"Increase 401(k) contribution by ${additional_contribution/12:,.0f}/month"
            })
        
        return recommendations
    
    async def _prioritize_recommendations(self, recommendations: List[Dict], user_context: Dict) -> List[Dict[str, Any]]:
        """Prioritize recommendations based on user context and impact"""
        
        # Priority scoring factors
        def calculate_priority_score(rec: Dict) -> float:
            score = 0.0
            
            # Base priority
            if rec["priority"] == "high":
                score += 100
            elif rec["priority"] == "medium":
                score += 50
            else:
                score += 10
            
            # Category-based adjustments
            category = rec["category"]
            if category == "emergency_fund" and user_context.get("net_worth", 0) < 10000:
                score += 50  # Emergency fund is critical for low net worth
            elif category == "debt_management" and "high_interest" in rec.get("id", ""):
                score += 40  # High interest debt is urgent
            elif category == "retirement" and user_context.get("age", 30) < 35:
                score += 30  # Retirement savings more important when young
            
            # Impact-based adjustments
            if "tax_savings" in rec:
                score += rec["tax_savings"] / 100  # $100 tax savings = 1 point
            
            if "free_money" in rec:
                score += rec["free_money"] / 100  # Employer match value
            
            return score
        
        # Sort by priority score
        prioritized = sorted(recommendations, key=calculate_priority_score, reverse=True)
        
        # Add priority rank
        for i, rec in enumerate(prioritized):
            rec["priority_rank"] = i + 1
            rec["priority_score"] = calculate_priority_score(rec)
        
        return prioritized
    
    async def _create_action_plans(self, recommendations: List[Dict], user_context: Dict) -> List[Dict[str, Any]]:
        """Create detailed action plans for top recommendations"""
        
        action_plans = []
        
        # Create action plans for top 3 recommendations
        for rec in recommendations[:3]:
            action_plan = {
                "recommendation_id": rec["id"],
                "title": rec["title"],
                "priority": rec["priority"],
                "timeline": "30 days",
                "steps": []
            }
            
            # Generate specific steps based on recommendation type
            if rec["category"] == "emergency_fund":
                action_plan["steps"] = [
                    "Research high-yield savings accounts with competitive rates",
                    f"Open dedicated emergency fund account",
                    f"Set up automatic transfer of ${rec.get('monthly_contribution', 0):,.0f}/month",
                    "Monitor progress monthly and adjust if needed"
                ]
            
            elif rec["category"] == "debt_management":
                action_plan["steps"] = [
                    "List all debts with balances and interest rates",
                    "Choose debt payoff strategy (avalanche recommended)",
                    "Calculate extra payment amount for target debt",
                    "Set up automatic payments and track progress"
                ]
            
            elif rec["category"] == "investment":
                action_plan["steps"] = [
                    "Research low-cost index funds or ETFs",
                    "Open investment account with reputable broker",
                    "Set up automatic monthly investments",
                    "Review and rebalance quarterly"
                ]
            
            elif rec["category"] == "retirement":
                action_plan["steps"] = [
                    "Review current 401(k) contribution percentage",
                    "Contact HR or plan administrator to increase contribution",
                    "Consider opening IRA if 401(k) not available",
                    "Review investment options within retirement accounts"
                ]
            
            else:
                action_plan["steps"] = [
                    "Review current situation and gather necessary information",
                    "Research options and compare alternatives",
                    "Implement chosen solution",
                    "Monitor progress and adjust as needed"
                ]
            
            action_plans.append(action_plan)
        
        return action_plans
    
    async def _generate_recommendation_response(
        self, 
        recommendations: List[Dict], 
        action_plans: List[Dict], 
        user_context: Dict
    ) -> str:
        """Generate natural language response with recommendations"""
        
        if not recommendations:
            return "I've analyzed your financial situation and you're doing well overall. Keep up the good work with your current financial habits!"
        
        response_parts = []
        
        # Introduction
        response_parts.append("Based on your financial situation, I have some personalized recommendations to help you build wealth more effectively:")
        
        # Top 3 recommendations
        for i, rec in enumerate(recommendations[:3], 1):
            priority_emoji = "🔥" if rec["priority"] == "high" else "💡" if rec["priority"] == "medium" else "📝"
            
            response_parts.append(f"\n{priority_emoji} **{i}. {rec['title']}**")
            response_parts.append(f"{rec['description']}")
            
            if "specific_action" in rec:
                response_parts.append(f"*Action:* {rec['specific_action']}")
            
            if "reasoning" in rec:
                response_parts.append(f"*Why:* {rec['reasoning']}")
        
        # Action plan mention
        if action_plans:
            response_parts.append(f"\nI've created detailed action plans for your top priorities. Would you like me to walk you through the specific steps for any of these recommendations?")
        
        # Encouragement
        response_parts.append(f"\nThese recommendations are tailored to your specific situation. Even small steps toward these goals will compound over time to significantly improve your financial position.")
        
        return " ".join(response_parts)
    
    # Helper methods
    def _calculate_emergency_fund_balance(self, user_context: Dict) -> float:
        """Calculate current emergency fund balance"""
        accounts = user_context.get("accounts", [])
        emergency_accounts = [
            acc for acc in accounts
            if acc.get("type") in ["savings", "checking"] and 
            "emergency" in acc.get("name", "").lower()
        ]
        
        if emergency_accounts:
            return sum(acc.get("balance", 0) for acc in emergency_accounts)
        
        # If no dedicated emergency fund, assume savings accounts
        savings_accounts = [acc for acc in accounts if acc.get("type") == "savings"]
        return sum(acc.get("balance", 0) for acc in savings_accounts)
    
    def _analyze_spending_patterns(self, transactions: List[Dict]) -> Dict[str, float]:
        """Analyze spending patterns by category"""
        spending_by_category = {}
        
        for transaction in transactions:
            amount = transaction.get("amount", 0)
            category = transaction.get("category", "other")
            
            if amount < 0:  # Expenses
                spending_by_category[category] = spending_by_category.get(category, 0) + abs(amount)
        
        return spending_by_category
    
    def _prioritize_needs(self, needs: Dict, user_context: Dict) -> List[str]:
        """Prioritize recommendation needs based on user context"""
        priority_order = []
        
        # High priority needs
        if needs.get("emergency_fund"):
            priority_order.append("emergency_fund")
        if needs.get("debt_management"):
            priority_order.append("debt_management")
        
        # Medium priority needs
        if needs.get("retirement"):
            priority_order.append("retirement")
        if needs.get("investment"):
            priority_order.append("investment")
        
        # Lower priority needs
        if needs.get("budgeting"):
            priority_order.append("budgeting")
        if needs.get("goal_planning"):
            priority_order.append("goal_planning")
        if needs.get("tax_optimization"):
            priority_order.append("tax_optimization")
        
        return priority_order
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create error response"""
        return {
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "success": False,
            "error": error_message,
            "response": "I encountered an issue while generating recommendations. Please try again.",
            "processing_time": 0.0,
            "timestamp": datetime.utcnow().isoformat()
        }