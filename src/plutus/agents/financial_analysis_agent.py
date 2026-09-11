"""
Financial Analysis Agent
========================

Analyzes user's financial health, calculates key metrics, and provides
comprehensive financial overview and insights.
"""

import json
from typing import Dict, List, Any, Optional

from .base_agent import BaseAgent
from .boundaries import measurement, number, known_accounts, is_liability, is_liquid
from .mixins import FinancialCalculationMixin, ResponseFormattingMixin
from ..models.state import ConversationState

class FinancialAnalysisAgent(BaseAgent, FinancialCalculationMixin, ResponseFormattingMixin):
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
        net_worth = measurement(user_context, "net_worth")
        monthly_income = measurement(user_context, "monthly_income")
        monthly_expenses = measurement(user_context, "monthly_expenses")
        wealth_health_score = measurement(user_context, "wealth_health_score")
        
        # Calculate key metrics
        monthly_savings = monthly_income - monthly_expenses if monthly_income is not None and monthly_expenses is not None else None
        savings_rate = monthly_savings / monthly_income if monthly_savings is not None and monthly_income > 0 else None
        
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
            "policy_version": "financial-heuristics-v1",
            "financial_health_grade": self._calculate_health_grade(wealth_health_score)
        }
    
    def _calculate_emergency_fund_months(self, user_context):
        expenses = measurement(user_context, "monthly_expenses")
        measured = user_context.get("financial_measurements", {}).get("emergency_assets")
        if isinstance(measured, dict):
            liquid = number(measured.get("total")) if measured.get("complete") is True and measured.get("currency") == "USD" else None
        else:
            accounts = known_accounts(user_context)
            liquid = sum(max(0, item["balance"]) for item in accounts if is_liquid(item)) if accounts is not None else None
        if liquid is None or expenses is None or expenses <= 0:
            return None
        return liquid / expenses

    def _analyze_debt_situation(self, user_context):
        accounts = known_accounts(user_context)
        income = measurement(user_context, "monthly_income")
        total = sum(abs(item["balance"]) for item in accounts if is_liability(item)) if accounts is not None else None
        ratio = total / (income * 12) if total is not None and income is not None and income > 0 else None
        return {"has_debt": total > 0 if total is not None else None,
                "estimated_total_debt": total, "total_debt": total,
                "debt_to_income_ratio": ratio,
                "debt_level": "unknown" if ratio is None else "high" if ratio > 0.4 else "moderate" if ratio > 0.2 else "low" if total else "none",
                "needs_attention": ratio > 0.3 if ratio is not None else None,
                "evidence": "supplied USD account balances", "policy_version": "financial-heuristics-v1"}

    def _calculate_financial_ratios(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate key financial ratios"""
        
        financial_snapshot = user_context.get("financial_snapshot", {})
        
        net_worth = measurement(user_context, "net_worth")
        monthly_income = measurement(user_context, "monthly_income")
        monthly_expenses = measurement(user_context, "monthly_expenses")
        
        # Calculate ratios
        monthly_savings = monthly_income - monthly_expenses if monthly_income is not None and monthly_expenses is not None else None
        savings_rate = monthly_savings / monthly_income if monthly_savings is not None and monthly_income > 0 else None
        
        # Net worth to income ratio
        annual_income = monthly_income * 12 if monthly_income is not None else None
        net_worth_to_income = net_worth / annual_income if net_worth is not None and annual_income is not None and annual_income > 0 else None
        
        return {
            "savings_rate": savings_rate,
            "net_worth_to_income_ratio": net_worth_to_income,
            "monthly_surplus": monthly_savings,
            "expense_ratio": monthly_expenses / monthly_income if monthly_expenses is not None and monthly_income is not None and monthly_income > 0 else None
        }
    
    def _assess_account_diversification(self, user_context):
        accounts = known_accounts(user_context)
        return {"total_accounts": len(accounts) if accounts is not None else None,
                "account_types_count": len({item.get("type") for item in accounts}) if accounts is not None else None,
                "has_investment_accounts": any(item.get("type") == "investment" for item in accounts) if accounts is not None else None,
                "diversification_score": None, "needs_diversification": None}

    def _generate_financial_insights(self, 
                                   savings_rate: float,
                                   emergency_fund_months: float,
                                   debt_analysis: Dict[str, Any],
                                   wealth_health_score: float) -> List[str]:
        """Generate key financial insights"""
        
        insights = []
        
        if savings_rate is not None:
            # Savings rate insights
            if savings_rate > 0.2:
                insights.append("Excellent savings rate - you're saving over 20% of income")
            elif savings_rate > 0.15:
                insights.append("Good savings rate - you're meeting the 15% recommendation")
            elif savings_rate > 0.1:
                insights.append("Moderate savings rate - consider increasing to 15% if possible")
            else:
                insights.append("Low savings rate - focus on increasing monthly savings")

        if emergency_fund_months is not None:
            # Emergency fund insights
            if emergency_fund_months >= 6:
                insights.append("Strong emergency fund - you have 6+ months of expenses covered")
            elif emergency_fund_months >= 3:
                insights.append("Adequate emergency fund - consider building to 6 months")
            else:
                insights.append("Emergency fund needs attention - aim for 3-6 months of expenses")

        if debt_analysis.get("has_debt") is not None:
            # Debt insights
            if debt_analysis.get("needs_attention", False):
                insights.append("High debt levels detected - prioritize debt reduction strategy")
            elif debt_analysis.get("has_debt", False):
                insights.append("Manageable debt levels - maintain current payment strategy")
            else:
                insights.append("No significant debt - great position for wealth building")

        if wealth_health_score is not None:
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
        
        if wealth_health_score is None:
            return "unknown"
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
        if emergency_fund_months is not None and emergency_fund_months < 3:
            recommendations.append("Build emergency fund to 3-6 months of expenses as top priority")
        elif emergency_fund_months is not None and emergency_fund_months < 6:
            recommendations.append("Continue building emergency fund to 6 months of expenses")
        
        # Savings rate recommendations
        savings_rate = analysis.get("savings_rate", 0)
        if savings_rate is not None and savings_rate < 0.15:
            recommendations.append("Increase savings rate to at least 15% of income")
        
        # Debt recommendations
        debt_analysis = analysis.get("debt_analysis", {})
        if debt_analysis.get("needs_attention", False):
            recommendations.append("Focus on paying down high-interest debt aggressively")
        
        # Investment recommendations
        account_diversification = analysis.get("account_diversification", {})
        if account_diversification.get("has_investment_accounts") is False:
            recommendations.append("Consider opening investment accounts for long-term growth")
        
        # Wealth health recommendations
        wealth_health_score = analysis.get("wealth_health_score", 0)
        if wealth_health_score is not None and wealth_health_score < 70:
            recommendations.append("Focus on foundational financial health improvements")
        
        return recommendations
    
    def _calculate_confidence(self, user_context: Dict[str, Any]) -> float:
        """Calculate confidence based on data availability"""
        
        financial_snapshot = user_context.get("financial_snapshot", {})
        
        # Check data completeness
        required_fields = ["net_worth", "monthly_income", "monthly_expenses"]
        available_fields = sum(1 for field in required_fields if measurement(user_context, field) is not None)
        
        base_confidence = available_fields / len(required_fields)
        
        # Adjust based on wealth health score availability
        if measurement(user_context, "wealth_health_score") is not None:
            base_confidence += 0.2
        
        return min(1.0, base_confidence)
