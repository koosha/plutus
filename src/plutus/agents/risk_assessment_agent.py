"""
Risk Assessment Agent - Phase 3 Advanced Agent
==============================================

This agent specializes in analyzing financial risk across multiple dimensions
including investment risk, income stability, debt burden, and overall financial
vulnerability. It provides comprehensive risk analysis and mitigation strategies.

Key Capabilities:
1. Assess investment portfolio risk and diversification
2. Analyze income stability and employment risk
3. Evaluate debt-to-income ratios and debt risk
4. Assess emergency fund adequacy
5. Calculate overall financial risk score
6. Recommend risk mitigation strategies
7. Provide risk-adjusted investment guidance
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import math

from .base_agent import BaseAgent
from .boundaries import failure, number, measurement, known_accounts, unknown_assessment, is_liability, is_liquid
from ..models.state import ConversationState, UserContext
from ..core.config import get_config

logger = logging.getLogger(__name__)


class RiskAssessmentAgent(BaseAgent):
    """
    Advanced agent for comprehensive financial risk assessment.
    
    This agent evaluates multiple risk factors and provides actionable
    strategies for risk management and mitigation.
    """
    
    def __init__(self):
        super().__init__("Risk Assessment Agent")
        self.agent_type = "risk_assessment"
        
        # Risk assessment frameworks
        self.risk_categories = {
            "investment_risk": {
                "weight": 0.30,
                "description": "Portfolio volatility and concentration risk"
            },
            "income_risk": {
                "weight": 0.25,
                "description": "Employment stability and income diversification"
            },
            "debt_risk": {
                "weight": 0.20,
                "description": "Debt burden and payment obligations"
            },
            "liquidity_risk": {
                "weight": 0.15,
                "description": "Emergency fund and cash availability"
            },
            "insurance_risk": {
                "weight": 0.10,
                "description": "Protection against major losses"
            }
        }
        
        # Risk tolerance profiles
        self.risk_profiles = {
            "conservative": {
                "score_range": (0, 30),
                "description": "Low risk tolerance, prioritizes capital preservation",
                "max_stock_allocation": 0.40,
                "recommended_emergency_months": 9
            },
            "moderate": {
                "score_range": (31, 60),
                "description": "Balanced approach to risk and return",
                "max_stock_allocation": 0.70,
                "recommended_emergency_months": 6
            },
            "aggressive": {
                "score_range": (61, 100),
                "description": "High risk tolerance, seeks maximum growth",
                "max_stock_allocation": 0.90,
                "recommended_emergency_months": 3
            }
        }
        
        # Industry risk classifications
        self.industry_risk_levels = {
            "technology": {"risk_level": "high", "volatility": 0.8},
            "healthcare": {"risk_level": "medium", "volatility": 0.4},
            "finance": {"risk_level": "medium", "volatility": 0.5},
            "education": {"risk_level": "low", "volatility": 0.2},
            "government": {"risk_level": "low", "volatility": 0.1},
            "retail": {"risk_level": "high", "volatility": 0.7},
            "construction": {"risk_level": "high", "volatility": 0.9},
            "utilities": {"risk_level": "low", "volatility": 0.2},
            "manufacturing": {"risk_level": "medium", "volatility": 0.4}
        }
    
    async def _process_core_logic(self, state: ConversationState) -> Dict[str, Any]:
        """
        Perform comprehensive risk assessment of user's financial situation.
        
        Args:
            state: Current conversation state
            
        Returns:
            Dictionary containing risk analysis and recommendations
        """
        
        try:
            logger.info(f"⚠️ Risk Assessment Agent processing...")
            
            user_message = state.get("user_message", "")
            user_context = state.get("user_context", {})
            
            # 1. Analyze if user is asking about risk
            risk_inquiry = await self._analyze_risk_inquiry(user_message)
            
            # 2. Perform comprehensive risk assessment
            risk_assessment = await self._perform_comprehensive_risk_assessment(user_context)
            
            # 3. Calculate overall risk score
            overall_risk_score = await self._calculate_overall_risk_score(risk_assessment)
            
            # 4. Identify risk factors and mitigation strategies
            risk_factors = await self._identify_risk_factors(risk_assessment, user_context)
            mitigation_strategies = await self._generate_mitigation_strategies(risk_factors, user_context)
            
            # 5. Generate risk-adjusted recommendations
            risk_recommendations = await self._generate_risk_recommendations(
                overall_risk_score, risk_factors, user_context
            )
            
            # 6. Create response
            response_text = await self._generate_risk_response(
                risk_inquiry, risk_assessment, overall_risk_score, 
                risk_factors, mitigation_strategies
            )
            
            # 7. Prepare agent results
            agent_result = {
                "agent_name": self.agent_name,
                "agent_type": self.agent_type,
                "success": True,
                "response": response_text,
                "analysis": {
                    "overall_risk_score": overall_risk_score,
                    "risk_profile": user_context.get("risk_tolerance") if user_context.get("risk_tolerance") in self.risk_profiles else "unknown",
                    "risk_level": self._determine_risk_profile(overall_risk_score),
                    "policy_version": "risk-heuristics-v1",
                    "coverage": sum(item.get("score") is not None for item in risk_assessment.values()) / len(risk_assessment),
                    "primary_risk_factors": risk_factors[:3],  # Top 3 risks
                    "risk_inquiry_detected": risk_inquiry["is_risk_related"]
                },
                "risk_assessment": risk_assessment,
                "risk_factors": risk_factors,
                "mitigation_strategies": mitigation_strategies,
                "recommendations": risk_recommendations,
                "processing_time": 0.0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"✅ Risk Assessment Agent completed - Overall Risk Score: {overall_risk_score}/100")
            return agent_result
            
        except Exception as e:
            logger.error("Specialist failed: category=%s", type(e).__name__)
            return self._create_error_response("analysis_failed")
    
    async def _analyze_risk_inquiry(self, message: str) -> Dict[str, Any]:
        """Analyze if the user is asking about risk"""
        
        message_lower = message.lower()
        
        # Risk-related keywords
        risk_keywords = [
            "risk", "risky", "safe", "safety", "secure", "dangerous",
            "volatile", "volatility", "stable", "stability", "conservative",
            "aggressive", "lose money", "loss", "protection", "hedge"
        ]
        
        # Investment risk keywords
        investment_risk_keywords = [
            "portfolio risk", "market risk", "stock risk", "bond risk",
            "diversification", "concentration", "correlation"
        ]
        
        # Income/employment risk keywords
        income_risk_keywords = [
            "job security", "employment", "income stability", "recession",
            "layoff", "unemployment", "career risk"
        ]
        
        # Check for risk-related content
        risk_keywords_found = [kw for kw in risk_keywords if kw in message_lower]
        investment_risk_found = [kw for kw in investment_risk_keywords if kw in message_lower]
        income_risk_found = [kw for kw in income_risk_keywords if kw in message_lower]
        
        is_risk_related = bool(risk_keywords_found or investment_risk_found or income_risk_found)
        
        # Determine specific risk inquiry type
        inquiry_type = "general"
        if investment_risk_found:
            inquiry_type = "investment_risk"
        elif income_risk_found:
            inquiry_type = "income_risk"
        elif any(kw in message_lower for kw in ["safe", "conservative", "protection"]):
            inquiry_type = "risk_mitigation"
        elif any(kw in message_lower for kw in ["aggressive", "high risk", "volatile"]):
            inquiry_type = "risk_tolerance"
        
        return {
            "is_risk_related": is_risk_related,
            "inquiry_type": inquiry_type,
            "keywords_found": risk_keywords_found,
            "investment_risk_keywords": investment_risk_found,
            "income_risk_keywords": income_risk_found
        }
    
    async def _perform_comprehensive_risk_assessment(self, user_context: Dict) -> Dict[str, Any]:
        """Perform comprehensive risk assessment across all categories"""
        
        assessment = {}
        
        # 1. Investment Risk Assessment
        assessment["investment_risk"] = await self._assess_investment_risk(user_context)
        
        # 2. Income Risk Assessment
        assessment["income_risk"] = await self._assess_income_risk(user_context)
        
        # 3. Debt Risk Assessment
        assessment["debt_risk"] = await self._assess_debt_risk(user_context)
        
        # 4. Liquidity Risk Assessment
        assessment["liquidity_risk"] = await self._assess_liquidity_risk(user_context)
        
        # 5. Insurance Risk Assessment
        assessment["insurance_risk"] = await self._assess_insurance_risk(user_context)
        
        return assessment
    
    async def _assess_investment_risk(self, user_context: Dict) -> Dict[str, Any]:
        """Assess concentration from eligible holdings, never account count."""
        provenance = user_context.get("data_provenance", {}).get("holdings", {})
        holdings = user_context.get("holdings")
        if (provenance.get("availability") in ("withheld", "failed", "unavailable")
                or not isinstance(holdings, list) or not holdings
                or any(not isinstance(item, dict) or item.get("currency") != "USD"
                       or number(item.get("value")) is None or item["value"] < 0
                       for item in holdings)):
            return {**unknown_assessment("eligible_holdings"), "largest_holding_percentage": None,
                    "concentration_risk": None, "diversification_score": None}
        # Combine the same security across accounts before measuring its weight.
        by_security = {}
        for item in holdings:
            security = item.get("security_id") or item.get("symbol") or item.get("ticker")
            if not security:
                return {**unknown_assessment("holding_identity"), "concentration_risk": None}
            by_security[security] = by_security.get(security, 0) + item["value"]
        total = sum(by_security.values())
        if total <= 0:
            return unknown_assessment("positive_holding_values")
        largest = max(by_security.values()) / total
        concentrated = largest > 0.25
        return {"score": 60 if concentrated else 20,
                "risk_level": "high" if concentrated else "low",
                "concentration_risk": concentrated, "largest_holding_percentage": largest,
                "diversification_score": None,
                "factors": ["A single holding exceeds 25% of supplied investment value"] if concentrated else [],
                "availability": "available", "policy_version": "risk-heuristics-v1",
                "evidence": {"currency": "USD", "holdings_count": len(holdings),
                             "scope": "supplied holdings concentration only"}}

    async def _assess_income_risk(self, user_context: Dict) -> Dict[str, Any]:
        """Assess income stability and employment risk"""
        
        monthly_income = measurement(user_context, "monthly_income")
        employment_type = user_context.get("employment_type")
        industry = user_context.get("industry")
        years_with_employer = number(user_context.get("years_with_employer"))
        
        risk_score = 0
        risk_factors = []
        
        # Employment type risk
        if employment_type == "contract":
            risk_score += 40
            risk_factors.append("Contract employment increases income volatility")
        elif employment_type == "part_time":
            risk_score += 30
            risk_factors.append("Part-time employment may limit income growth")
        elif employment_type == "self_employed":
            risk_score += 50
            risk_factors.append("Self-employment income can be highly variable")
        
        # Industry risk
        industry_data = self.industry_risk_levels.get(industry, {"risk_level": "medium", "volatility": 0.5})
        if industry_data["risk_level"] == "high":
            risk_score += 25
            risk_factors.append(f"{industry.title()} industry has higher employment volatility")
        elif industry_data["risk_level"] == "low":
            risk_score -= 10  # Reduce risk for stable industries
        
        # Job tenure risk
        if years_with_employer is not None and years_with_employer < 1:
            risk_score += 20
            risk_factors.append("Short tenure with current employer")
        elif years_with_employer is not None and years_with_employer > 5:
            risk_score -= 10  # Reduce risk for stable employment
        
        # Income diversification
        has_side_income = user_context.get("has_side_income")
        if has_side_income is False:
            risk_score += 15
            risk_factors.append("Single source of income increases risk")
        
        # Age and career stage risk
        age = number(user_context.get("age"))
        if age is not None and age > 55:
            risk_score += 20
            risk_factors.append("Older workers may face age discrimination in job search")
        elif age is not None and age < 25:
            risk_score += 10
            risk_factors.append("Early career stage may have less job security")
        
        missing = [key for key in ("employment_type", "industry", "years_with_employer", "has_side_income", "age")
                   if user_context.get(key) is None]
        if missing:
            return {**unknown_assessment(*missing), "employment_type": employment_type,
                    "years_with_employer": years_with_employer,
                    "has_income_diversification": has_side_income, "factors": risk_factors}
        risk_level = "low" if risk_score < 30 else "medium" if risk_score < 60 else "high"
        
        return {
            "score": min(max(risk_score, 0), 100),
            "risk_level": risk_level,
            "employment_type": employment_type,
            "industry_risk": industry_data["risk_level"],
            "years_with_employer": years_with_employer,
            "has_income_diversification": has_side_income,
            "factors": risk_factors
        }
    
    async def _assess_debt_risk(self, user_context: Dict) -> Dict[str, Any]:
        """Assess debt burden and payment risk"""
        
        monthly_income = measurement(user_context, "monthly_income")
        accounts = known_accounts(user_context)
        if monthly_income is None or monthly_income <= 0 or accounts is None:
            return unknown_assessment("monthly_income", "eligible_accounts")
        if any(number(item.get("interest_rate")) is None for item in accounts if is_liability(item)):
            return unknown_assessment("debt_interest_rates")
        
        # Calculate total debt
        debt_accounts = [acc for acc in accounts if is_liability(acc)]
        total_debt = sum(abs(acc.get("balance", 0)) for acc in debt_accounts)
        
        # Calculate debt-to-income ratio
        annual_income = monthly_income * 12
        debt_to_income = total_debt / max(annual_income, 1)
        
        # Calculate monthly debt payments (estimate)
        estimated_monthly_payments = 0
        high_interest_debt = 0
        
        for debt in debt_accounts:
            balance = abs(debt.get("balance", 0))
            interest_rate = debt.get("interest_rate", 0.15)  # Assume 15% if not specified
            
            if interest_rate > 0.20:  # High interest debt (credit cards)
                high_interest_debt += balance
                # Assume minimum payment of 2% of balance
                estimated_monthly_payments += balance * 0.02
            else:
                # Assume minimum payment of 1% of balance for other debt
                estimated_monthly_payments += balance * 0.01
        
        debt_service_ratio = estimated_monthly_payments / max(monthly_income, 1)
        
        # Calculate debt risk score
        risk_score = 0
        risk_factors = []
        
        # Debt-to-income risk
        if debt_to_income > 3.0:  # More than 3x annual income
            risk_score += 50
            risk_factors.append(f"High debt-to-income ratio: {debt_to_income:.1f}x")
        elif debt_to_income > 2.0:
            risk_score += 30
            risk_factors.append(f"Elevated debt-to-income ratio: {debt_to_income:.1f}x")
        elif debt_to_income > 1.0:
            risk_score += 15
            risk_factors.append(f"Moderate debt-to-income ratio: {debt_to_income:.1f}x")
        
        # Debt service ratio risk
        if debt_service_ratio > 0.4:  # More than 40% of income to debt payments
            risk_score += 40
            risk_factors.append(f"High debt service ratio: {debt_service_ratio:.1%}")
        elif debt_service_ratio > 0.28:
            risk_score += 20
            risk_factors.append(f"Elevated debt service ratio: {debt_service_ratio:.1%}")
        
        # High interest debt risk
        if high_interest_debt > monthly_income * 6:  # More than 6 months income
            risk_score += 30
            risk_factors.append(f"Significant high-interest debt: ${high_interest_debt:,.0f}")
        elif high_interest_debt > 0:
            risk_score += 15
            risk_factors.append("Some high-interest debt present")
        
        # Number of debt accounts
        if len(debt_accounts) > 5:
            risk_score += 15
            risk_factors.append("Multiple debt obligations to manage")
        
        risk_level = "low" if risk_score < 30 else "medium" if risk_score < 60 else "high"
        
        return {
            "score": min(risk_score, 100),
            "risk_level": risk_level,
            "total_debt": total_debt,
            "debt_to_income_ratio": debt_to_income,
            "debt_service_ratio": debt_service_ratio,
            "high_interest_debt": high_interest_debt,
            "number_of_debts": len(debt_accounts),
            "factors": risk_factors
        }
    
    async def _assess_liquidity_risk(self, user_context: Dict) -> Dict[str, Any]:
        """Assess emergency fund and cash availability risk"""
        
        monthly_expenses = measurement(user_context, "monthly_expenses")
        accounts = known_accounts(user_context)
        if monthly_expenses is None or monthly_expenses <= 0 or accounts is None:
            return unknown_assessment("monthly_expenses", "eligible_accounts")
        
        # Calculate liquid assets (checking, savings)
        liquid_accounts = [
            acc for acc in accounts 
            if is_liquid(acc)
        ]
        total_liquid = sum(acc.get("balance", 0) for acc in liquid_accounts)
        
        # Calculate emergency fund coverage
        emergency_fund_months = total_liquid / max(monthly_expenses, 1)
        
        # Calculate risk score
        risk_score = 0
        risk_factors = []
        
        # Emergency fund adequacy
        if emergency_fund_months < 1:
            risk_score += 70
            risk_factors.append("Critically low emergency fund (less than 1 month)")
        elif emergency_fund_months < 3:
            risk_score += 50
            risk_factors.append("Insufficient emergency fund (less than 3 months)")
        elif emergency_fund_months < 6:
            risk_score += 25
            risk_factors.append("Below recommended emergency fund (less than 6 months)")
        elif emergency_fund_months > 12:
            risk_score += 10
            risk_factors.append("Excess cash may not be earning optimal returns")
        
        # Liquidity concentration
        checking_balance = sum(
            acc.get("balance", 0) for acc in accounts 
            if acc.get("type") == "checking" or acc.get("subtype") == "checking"
        )
        if checking_balance > monthly_expenses * 2:
            risk_score += 5
            risk_factors.append("Excess cash in low-yield checking account")
        
        risk_level = "low" if risk_score < 30 else "medium" if risk_score < 60 else "high"
        
        return {
            "score": min(risk_score, 100),
            "risk_level": risk_level,
            "emergency_fund_months": emergency_fund_months,
            "total_liquid_assets": total_liquid,
            "monthly_expenses": monthly_expenses,
            "factors": risk_factors
        }
    
    async def _assess_insurance_risk(self, user_context: Dict) -> Dict[str, Any]:
        """Report only explicitly supplied coverage facts."""
        keys = ("has_health_insurance", "has_life_insurance", "has_disability_insurance",
                "has_homeowners_insurance", "has_dependents", "owns_home")
        facts = {key: user_context.get(key) if isinstance(user_context.get(key), bool) else None for key in keys}
        missing = [key for key, value in facts.items() if value is None]
        factors, score = [], 0
        for absent, relevant, penalty, description in (
            (facts['has_health_insurance'] is False, True, 40, 'No health insurance reported'),
            (facts['has_life_insurance'] is False, facts['has_dependents'] is True, 30, 'No life insurance reported with dependents'),
            (facts['has_homeowners_insurance'] is False, facts['owns_home'] is True, 35, 'No homeowners insurance reported for owned home'),
        ):
            if absent and relevant:
                score += penalty
                factors.append(description)
        result = unknown_assessment(*missing) if missing else {
            'score': min(score, 100), 'risk_level': 'high' if score >= 60 else 'medium' if score >= 30 else 'low',
            'availability': 'available', 'policy_version': 'risk-heuristics-v1'}
        return {**result, **facts, 'factors': factors, 'evidence': {'source': 'user_reported'}}

    async def _calculate_overall_risk_score(self, risk_assessment: Dict) -> int:
        """Calculate weighted overall risk score"""
        
        total_score = 0
        total_weight = 0
        
        for category, weight_data in self.risk_categories.items():
            if category in risk_assessment:
                score = number(risk_assessment[category].get("score"))
                if score is None:
                    return None
                weight = weight_data["weight"]
                total_score += score * weight
                total_weight += weight
        
        overall_score = total_score / total_weight if total_weight else 0
        return round(overall_score)
    
    async def _identify_risk_factors(self, risk_assessment: Dict, user_context: Dict) -> List[Dict[str, Any]]:
        """Identify and prioritize risk factors"""
        
        risk_factors = []
        
        for category, assessment in risk_assessment.items():
            category_weight = self.risk_categories.get(category, {}).get("weight", 0)
            risk_score = assessment.get("score", 0)
            risk_level = assessment.get("risk_level", "low")
            factors = assessment.get("factors", [])
            
            if risk_score is not None and risk_score > 30:  # Only include significant risks
                risk_factors.append({
                    "category": category,
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                    "weight": category_weight,
                    "priority_score": risk_score * category_weight,
                    "factors": factors,
                    "description": self.risk_categories[category]["description"]
                })
        
        # Sort by priority score (risk score * weight)
        risk_factors.sort(key=lambda x: x["priority_score"], reverse=True)
        
        return risk_factors
    
    async def _generate_mitigation_strategies(self, risk_factors: List[Dict], user_context: Dict) -> List[Dict[str, Any]]:
        """Generate risk mitigation strategies"""
        
        strategies = []
        
        for risk_factor in risk_factors[:5]:  # Top 5 risks
            category = risk_factor["category"]
            
            if category == "liquidity_risk":
                strategies.append({
                    "risk_category": category,
                    "strategy": "Build Emergency Fund",
                    "description": "Increase emergency fund to 6 months of expenses",
                    "priority": "high",
                    "timeline": "6-12 months",
                    "actions": [
                        "Open high-yield savings account",
                        "Set up automatic transfers",
                        "Target 6 months of expenses"
                    ]
                })
            
            elif category == "debt_risk":
                strategies.append({
                    "risk_category": category,
                    "strategy": "Debt Reduction Plan",
                    "description": "Implement aggressive debt payoff strategy",
                    "priority": "high",
                    "timeline": "2-5 years",
                    "actions": [
                        "List all debts by interest rate",
                        "Focus extra payments on highest rate debt",
                        "Consider debt consolidation options"
                    ]
                })
            
            elif category == "investment_risk":
                strategies.append({
                    "risk_category": category,
                    "strategy": "Portfolio Diversification",
                    "description": "Improve portfolio diversification and risk management",
                    "priority": "medium",
                    "timeline": "3-6 months",
                    "actions": [
                        "Review current asset allocation",
                        "Add international diversification",
                        "Consider index funds for broader exposure"
                    ]
                })
            
            elif category == "income_risk":
                strategies.append({
                    "risk_category": category,
                    "strategy": "Income Diversification",
                    "description": "Develop multiple income streams",
                    "priority": "medium",
                    "timeline": "6-12 months",
                    "actions": [
                        "Develop marketable skills",
                        "Create side income opportunities",
                        "Build professional network"
                    ]
                })
            
            elif category == "insurance_risk":
                strategies.append({
                    "risk_category": category,
                    "strategy": "Insurance Coverage Review",
                    "description": "Ensure adequate insurance protection",
                    "priority": "high",
                    "timeline": "1-3 months",
                    "actions": [
                        "Review current insurance policies",
                        "Get quotes for missing coverage",
                        "Consider umbrella policy if high net worth"
                    ]
                })
        
        return strategies
    
    async def _generate_risk_recommendations(self, overall_risk_score: int, risk_factors: List[Dict], user_context: Dict) -> List[Dict[str, Any]]:
        """Generate risk-specific recommendations"""
        
        recommendations = []
        risk_profile = self._determine_risk_profile(overall_risk_score)
        
        # Overall risk management recommendation
        if overall_risk_score is not None and overall_risk_score > 70:
            recommendations.append({
                "type": "high_risk_alert",
                "priority": "critical",
                "title": "Address High Financial Risk",
                "description": f"Your overall risk score of {overall_risk_score}/100 indicates significant financial vulnerability",
                "action": "Focus on the top 2-3 risk factors immediately"
            })
        
        # Specific recommendations based on top risk factors
        for risk_factor in risk_factors[:3]:
            category = risk_factor["category"]
            
            if category == "liquidity_risk" and risk_factor["risk_score"] > 50:
                recommendations.append({
                    "type": "emergency_fund_urgent",
                    "priority": "high",
                    "title": "Build Emergency Fund Immediately",
                    "description": "Low emergency fund creates significant financial vulnerability",
                    "action": "Save aggressively to build 3-month emergency fund as priority #1"
                })
            
            elif category == "debt_risk" and risk_factor["risk_score"] > 50:
                recommendations.append({
                    "type": "debt_reduction_urgent",
                    "priority": "high", 
                    "title": "Address High Debt Burden",
                    "description": "High debt levels increase financial stress and limit options",
                    "action": "Create debt payoff plan focusing on highest interest rates first"
                })
        
        return recommendations
    
    async def _generate_risk_response(
        self, 
        risk_inquiry: Dict, 
        risk_assessment: Dict, 
        overall_risk_score: int,
        risk_factors: List[Dict], 
        mitigation_strategies: List[Dict]
    ) -> str:
        """Generate natural language response about risk"""
        
        if overall_risk_score is None:
            return "There is insufficient verified information for an overall risk score. Supplied facts can support only a partial assessment."
        if not risk_inquiry["is_risk_related"] and overall_risk_score < 40:
            return ""  # Don't overwhelm with risk info if not requested and risk is low
        
        response_parts = []
        
        # Overall risk assessment
        risk_profile = self._determine_risk_profile(overall_risk_score)
        
        if risk_inquiry["is_risk_related"]:
            response_parts.append("I've analyzed your financial risk profile comprehensively.")
        
        response_parts.append(f"Your overall financial risk score is {overall_risk_score}/100, indicating {risk_profile} financial vulnerability under this heuristic policy.")
        
        # Highlight top risks
        if risk_factors:
            response_parts.append(f"\n**Primary Risk Areas:**")
            for i, risk in enumerate(risk_factors[:3], 1):
                category_name = risk["category"].replace("_", " ").title()
                response_parts.append(f"{i}. {category_name} (Risk Score: {risk['risk_score']}/100)")
                if risk["factors"]:
                    response_parts.append(f"   • {risk['factors'][0]}")
        
        # Mitigation strategies
        if mitigation_strategies:
            top_strategy = mitigation_strategies[0]
            response_parts.append(f"\n**Priority Action:** {top_strategy['strategy']}")
            response_parts.append(f"{top_strategy['description']}")
        
        # Risk-specific guidance
        if overall_risk_score > 60:
            response_parts.append(f"\n⚠️ Your elevated risk level suggests focusing on financial stability before pursuing aggressive growth strategies.")
        elif overall_risk_score < 30:
            response_parts.append(f"\n✅ Your low risk profile indicates good financial stability. You may be able to pursue more growth-oriented strategies.")
        
        return " ".join(response_parts)
    
    # Helper methods
    def _determine_risk_profile(self, overall_risk_score: int) -> str:
        """Determine risk profile based on overall score"""
        if overall_risk_score is None:
            return "unknown"
        return "low" if overall_risk_score < 30 else "medium" if overall_risk_score < 60 else "high"

    def _identify_investment_risk_factors(self, investment_pct: float, diversification: int, concentration: bool, age: int) -> List[str]:
        """Identify specific investment risk factors"""
        factors = []
        
        if investment_pct > 0.8:
            factors.append("Very high allocation to investments increases volatility")
        if diversification < 50:
            factors.append("Poor diversification increases concentration risk")
        if concentration:
            factors.append("High concentration in single investments")
        if age > 50 and investment_pct > 0.7:
            factors.append("High equity allocation may be inappropriate for age")
        
        return factors
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create error response"""
        return {
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "success": False,
            **failure(),
            "response": "I encountered an issue while assessing financial risk. Please try again.",
            "processing_time": 0.0,
            "timestamp": datetime.utcnow().isoformat()
        }
