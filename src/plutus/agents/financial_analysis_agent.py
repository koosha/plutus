"""
Financial Analysis Agent
========================

Analyzes user's financial health, calculates key metrics, and provides
comprehensive financial overview and insights.
"""

import json
from typing import Dict, List, Any, Optional

from .base_agent import BaseAgent
from .mixins import FinancialCalculationMixin, ResponseFormattingMixin, ClaudePromptMixin
from ..models.state import ConversationState

class FinancialAnalysisAgent(BaseAgent, FinancialCalculationMixin, ResponseFormattingMixin, ClaudePromptMixin):
    """
    Financial Analysis Agent
    
    Responsibilities:
    - Analyze account balances and net worth
    - Calculate financial health metrics
    - Assess cash flow and spending patterns
    - Identify financial strengths and weaknesses
    - Provide actionable financial insights
    """
    
    def __init__(self):
        super().__init__("Financial Analysis Agent")
        self.agent_type = "financial_analysis"
    
    async def _process_core_logic(self, state: ConversationState) -> Dict[str, Any]:
        """Execute financial analysis"""
        
        # Get user context
        user_context = state.get("user_context", {})
        financial_snapshot = user_context.get("financial_snapshot", {})
        
        # Perform financial analysis
        analysis = await self._analyze_financial_health(user_context)
        
        # Generate recommendations
        recommendations = await self._generate_financial_recommendations(analysis, user_context)
        
        # Calculate confidence based on data availability
        confidence = self._calculate_confidence(user_context)
        
        # Create structured response
        response = self.create_structured_response(
            analysis, recommendations, confidence, self.agent_type
        )
        
        return {
            "analysis": analysis,
            "recommendations": recommendations,
            "confidence_score": confidence,
            "response": response,
            "insights": analysis.get("key_insights", [])
        }
    
    async def _analyze_financial_health(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive financial health analysis
        """
        
        financial_snapshot = user_context.get("financial_snapshot", {})
        account_summary = user_context.get("account_summary", {})
        
        # Extract key financial data
        net_worth = financial_snapshot.get("net_worth", 0)
        monthly_income = financial_snapshot.get("monthly_income", 0)
        monthly_expenses = financial_snapshot.get("monthly_expenses", 0)
        wealth_health_score = financial_snapshot.get("wealth_health_score", 0)
        
        # Calculate key metrics
        monthly_savings = monthly_income - monthly_expenses
        savings_rate = monthly_savings / monthly_income if monthly_income > 0 else 0
        
        # Determine emergency fund status
        emergency_fund_months = self._calculate_emergency_fund_months(user_context)
        
        # Assess debt situation
        debt_analysis = self._analyze_debt_situation(user_context)
        
        # Calculate financial ratios
        financial_ratios = self._calculate_financial_ratios(user_context)
        
        # Assess account diversification
        account_diversification = self._assess_account_diversification(user_context)
        
        # Generate insights
        key_insights = self._generate_financial_insights(
            savings_rate, emergency_fund_months, debt_analysis, wealth_health_score
        )
        
        return {
            "net_worth": net_worth,
            "monthly_income": monthly_income,
            "monthly_expenses": monthly_expenses,
            "monthly_savings": monthly_savings,
            "savings_rate": savings_rate,
            "wealth_health_score": wealth_health_score,
            "emergency_fund_months": emergency_fund_months,
            "debt_analysis": debt_analysis,
            "financial_ratios": financial_ratios,
            "account_diversification": account_diversification,
            "key_insights": key_insights,
            "financial_health_grade": self._calculate_health_grade(wealth_health_score)
        }
    
    def _calculate_emergency_fund_months(self, user_context: Dict[str, Any]) -> float:
        """Calculate emergency fund coverage in months"""
        
        financial_snapshot = user_context.get("financial_snapshot", {})
        monthly_expenses = financial_snapshot.get("monthly_expenses", 0)
        
        if monthly_expenses <= 0:
            return 0
        
        # Estimate liquid assets (simplified)
        # In production, would identify specific emergency fund accounts
        net_worth = financial_snapshot.get("net_worth", 0)
        
        # Assume 20% of net worth is liquid for emergency fund
        estimated_liquid = net_worth * 0.2
        
        return estimated_liquid / monthly_expenses
    
    def _analyze_debt_situation(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze debt situation"""
        
        account_summary = user_context.get("account_summary", {})
        financial_snapshot = user_context.get("financial_snapshot", {})
        
        has_debt = account_summary.get("has_debt", False)
        monthly_income = financial_snapshot.get("monthly_income", 0)
        
        # Simplified debt analysis
        # In production, would analyze specific debt accounts
        
        if has_debt:
            # Estimate debt amounts (simplified)
            estimated_debt = financial_snapshot.get("net_worth", 0) * 0.1  # Rough estimate
            debt_to_income_ratio = abs(estimated_debt) / (monthly_income * 12) if monthly_income > 0 else 0
            
            debt_level = "high" if debt_to_income_ratio > 0.4 else "moderate" if debt_to_income_ratio > 0.2 else "low"
            
            return {
                "has_debt": True,
                "estimated_total_debt": abs(estimated_debt),
                "debt_to_income_ratio": debt_to_income_ratio,
                "debt_level": debt_level,
                "needs_attention": debt_to_income_ratio > 0.3
            }
        else:
            return {
                "has_debt": False,
                "estimated_total_debt": 0,
                "debt_to_income_ratio": 0,
                "debt_level": "none",
                "needs_attention": False
            }
    
    def _calculate_financial_ratios(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate key financial ratios"""
        
        financial_snapshot = user_context.get("financial_snapshot", {})
        
        net_worth = financial_snapshot.get("net_worth", 0)
        monthly_income = financial_snapshot.get("monthly_income", 0)
        monthly_expenses = financial_snapshot.get("monthly_expenses", 0)
        
        # Calculate ratios
        monthly_savings = monthly_income - monthly_expenses
        savings_rate = monthly_savings / monthly_income if monthly_income > 0 else 0
        
        # Net worth to income ratio
        annual_income = monthly_income * 12
        net_worth_to_income = net_worth / annual_income if annual_income > 0 else 0
        
        return {
            "savings_rate": savings_rate,
            "net_worth_to_income_ratio": net_worth_to_income,
            "monthly_surplus": monthly_savings,
            "expense_ratio": monthly_expenses / monthly_income if monthly_income > 0 else 0
        }
    
    def _assess_account_diversification(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess account type diversification"""
        
        account_summary = user_context.get("account_summary", {})
        
        total_accounts = account_summary.get("total_accounts", 0)
        account_types = account_summary.get("account_types", [])
        has_investment_accounts = account_summary.get("has_investment_accounts", False)
        
        # Assess diversification
        diversification_score = min(100, (len(account_types) / 5) * 100)  # 5+ types = full score
        
        return {
            "total_accounts": total_accounts,
            "account_types_count": len(account_types),
            "has_investment_accounts": has_investment_accounts,
            "diversification_score": diversification_score,
            "needs_diversification": diversification_score < 60
        }
    
    def _generate_financial_insights(self, 
                                   savings_rate: float,
                                   emergency_fund_months: float,
                                   debt_analysis: Dict[str, Any],
                                   wealth_health_score: float) -> List[str]:
        """Generate key financial insights"""
        
        insights = []
        
        # Savings rate insights
        if savings_rate > 0.2:
            insights.append("Excellent savings rate - you're saving over 20% of income")
        elif savings_rate > 0.15:
            insights.append("Good savings rate - you're meeting the 15% recommendation")
        elif savings_rate > 0.1:
            insights.append("Moderate savings rate - consider increasing to 15% if possible")
        else:
            insights.append("Low savings rate - focus on increasing monthly savings")
        
        # Emergency fund insights
        if emergency_fund_months >= 6:
            insights.append("Strong emergency fund - you have 6+ months of expenses covered")
        elif emergency_fund_months >= 3:
            insights.append("Adequate emergency fund - consider building to 6 months")
        else:
            insights.append("Emergency fund needs attention - aim for 3-6 months of expenses")
        
        # Debt insights
        if debt_analysis.get("needs_attention", False):
            insights.append("High debt levels detected - prioritize debt reduction strategy")
        elif debt_analysis.get("has_debt", False):
            insights.append("Manageable debt levels - maintain current payment strategy")
        else:
            insights.append("No significant debt - great position for wealth building")
        
        # Overall wealth health
        if wealth_health_score >= 80:
            insights.append("Excellent overall financial health")
        elif wealth_health_score >= 60:
            insights.append("Good financial health with room for improvement")
        else:
            insights.append("Financial health needs attention - focus on foundational areas")
        
        return insights
    
    def _calculate_health_grade(self, wealth_health_score: float) -> str:
        """Calculate letter grade for financial health"""
        
        if wealth_health_score >= 90:
            return "A+"
        elif wealth_health_score >= 85:
            return "A"
        elif wealth_health_score >= 80:
            return "A-"
        elif wealth_health_score >= 75:
            return "B+"
        elif wealth_health_score >= 70:
            return "B"
        elif wealth_health_score >= 65:
            return "B-"
        elif wealth_health_score >= 60:
            return "C+"
        elif wealth_health_score >= 55:
            return "C"
        elif wealth_health_score >= 50:
            return "C-"
        else:
            return "D"
    
    async def _generate_financial_recommendations(self, 
                                                analysis: Dict[str, Any],
                                                user_context: Dict[str, Any]) -> List[str]:
        """Generate personalized financial recommendations"""
        
        recommendations = []
        
        # Emergency fund recommendations
        emergency_fund_months = analysis.get("emergency_fund_months", 0)
        if emergency_fund_months < 3:
            recommendations.append("Build emergency fund to 3-6 months of expenses as top priority")
        elif emergency_fund_months < 6:
            recommendations.append("Continue building emergency fund to 6 months of expenses")
        
        # Savings rate recommendations
        savings_rate = analysis.get("savings_rate", 0)
        if savings_rate < 0.15:
            recommendations.append("Increase savings rate to at least 15% of income")
        
        # Debt recommendations
        debt_analysis = analysis.get("debt_analysis", {})
        if debt_analysis.get("needs_attention", False):
            recommendations.append("Focus on paying down high-interest debt aggressively")
        
        # Investment recommendations
        account_diversification = analysis.get("account_diversification", {})
        if not account_diversification.get("has_investment_accounts", False):
            recommendations.append("Consider opening investment accounts for long-term growth")
        
        # Wealth health recommendations
        wealth_health_score = analysis.get("wealth_health_score", 0)
        if wealth_health_score < 70:
            recommendations.append("Focus on foundational financial health improvements")
        
        return recommendations
    
    def _calculate_confidence(self, user_context: Dict[str, Any]) -> float:
        """Calculate confidence based on data availability"""
        
        financial_snapshot = user_context.get("financial_snapshot", {})
        
        # Check data completeness
        required_fields = ["net_worth", "monthly_income", "monthly_expenses"]
        available_fields = sum(1 for field in required_fields if financial_snapshot.get(field, 0) > 0)
        
        base_confidence = available_fields / len(required_fields)
        
        # Adjust based on wealth health score availability
        if financial_snapshot.get("wealth_health_score", 0) > 0:
            base_confidence += 0.2
        
        return min(1.0, base_confidence)
    
    def _generate_simulated_response(self, prompt: str) -> str:
        """Generate simulated response for testing"""
        
        return json.dumps({
            "financial_health_analysis": {
                "net_worth": 85000,
                "savings_rate": 0.18,
                "emergency_fund_months": 4.2,
                "wealth_health_score": 72,
                "financial_health_grade": "B"
            },
            "key_insights": [
                "Good savings rate at 18% of income",
                "Emergency fund needs slight boost to 6 months",
                "Overall financial health is good with room for improvement"
            ],
            "recommendations": [
                "Build emergency fund to 6 months of expenses",
                "Continue strong savings habits",
                "Consider investment account diversification"
            ]
        })