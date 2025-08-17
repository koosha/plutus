"""
Agent Mixins - Common Functionality
===================================

This module provides reusable mixins for common agent functionality
to reduce code duplication and ensure consistency.
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from abc import ABC

logger = logging.getLogger(__name__)


class FinancialCalculationMixin:
    """Mixin providing common financial calculation utilities."""
    
    def calculate_net_worth(self, accounts: List[Dict[str, Any]]) -> float:
        """Calculate net worth from account balances."""
        total = 0.0
        for account in accounts:
            balance = account.get('balance', 0)
            if isinstance(balance, (int, float)):
                total += balance
        return total
    
    def calculate_monthly_cash_flow(self, income: float, expenses: float) -> Dict[str, float]:
        """Calculate monthly cash flow metrics."""
        surplus = income - expenses
        savings_rate = (surplus / income) * 100 if income > 0 else 0
        
        return {
            "monthly_surplus": surplus,
            "monthly_savings_rate": savings_rate,
            "annual_surplus": surplus * 12
        }
    
    def calculate_emergency_fund_ratio(self, liquid_savings: float, monthly_expenses: float) -> Dict[str, Union[float, str]]:
        """Calculate emergency fund coverage."""
        if monthly_expenses <= 0:
            return {"months_covered": 0, "status": "insufficient_data"}
        
        months_covered = liquid_savings / monthly_expenses
        
        if months_covered >= 6:
            status = "excellent"
        elif months_covered >= 3:
            status = "good"
        elif months_covered >= 1:
            status = "minimal"
        else:
            status = "insufficient"
        
        return {
            "months_covered": months_covered,
            "status": status,
            "target_amount": monthly_expenses * 6,
            "shortfall": max(0, (monthly_expenses * 6) - liquid_savings)
        }


class TextParsingMixin:
    """Mixin providing common text parsing utilities."""
    
    def extract_financial_amounts(self, text: str) -> List[float]:
        """Extract monetary amounts from text."""
        money_patterns = [
            r'\$([0-9,]+(?:\.[0-9]{2})?)',           # $1,000.00
            r'([0-9,]+(?:\.[0-9]{2})?) dollars',    # 1000 dollars
            r'([0-9,]+)k',                          # 50k
            r'([0-9,]+) thousand',                  # 50 thousand
        ]
        
        amounts = []
        
        for pattern in money_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    clean_amount = match.replace(',', '')
                    amount = float(clean_amount)
                    
                    if 'k' in match.lower() or 'thousand' in text.lower():
                        amount *= 1000
                    
                    amounts.append(amount)
                except ValueError:
                    continue
        
        return amounts
    
    def extract_time_references(self, text: str) -> List[Dict[str, Any]]:
        """Extract time references from text."""
        time_patterns = [
            (r'(\d+)\s*(?:years?|yrs?)', 'years'),
            (r'(\d+)\s*months?', 'months'),
            (r'by\s*(\d{4})', 'target_year'),
            (r'in\s*(\d+)\s*(?:years?|months?)', 'duration'),
        ]
        
        time_refs = []
        
        for pattern, ref_type in time_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    time_refs.append({
                        "value": int(match),
                        "type": ref_type,
                        "text": match
                    })
                except ValueError:
                    continue
        
        return time_refs
    
    def extract_goal_keywords(self, text: str, goal_keywords: Dict[str, List[str]]) -> List[str]:
        """Extract goal types mentioned in text."""
        text_lower = text.lower()
        found_goals = []
        
        for goal_type, keywords in goal_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    if goal_type not in found_goals:
                        found_goals.append(goal_type)
                    break
        
        return found_goals


class ResponseFormattingMixin:
    """Mixin providing consistent response formatting."""
    
    def format_currency(self, amount: float) -> str:
        """Format currency amount with proper formatting."""
        if amount >= 1_000_000:
            return f"${amount/1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"${amount/1_000:.1f}K"
        else:
            return f"${amount:.2f}"
    
    def format_percentage(self, value: float, decimal_places: int = 1) -> str:
        """Format percentage with proper precision."""
        return f"{value:.{decimal_places}f}%"
    
    def create_structured_response(
        self, 
        analysis: Dict[str, Any], 
        recommendations: List[Dict[str, Any]], 
        confidence: float,
        agent_type: str
    ) -> str:
        """Create a well-structured response with consistent formatting."""
        
        response_parts = []
        
        # Analysis summary
        if analysis:
            response_parts.append("## Analysis Summary")
            for key, value in analysis.items():
                if isinstance(value, (int, float)):
                    if 'amount' in key.lower() or 'worth' in key.lower():
                        response_parts.append(f"- {key.replace('_', ' ').title()}: {self.format_currency(value)}")
                    elif 'rate' in key.lower() or 'score' in key.lower():
                        response_parts.append(f"- {key.replace('_', ' ').title()}: {self.format_percentage(value)}")
                    else:
                        response_parts.append(f"- {key.replace('_', ' ').title()}: {value}")
                else:
                    response_parts.append(f"- {key.replace('_', ' ').title()}: {value}")
        
        # Recommendations
        if recommendations:
            response_parts.append("\n## Recommendations")
            for i, rec in enumerate(recommendations[:5], 1):  # Limit to top 5
                title = rec.get('title', f'Recommendation {i}')
                description = rec.get('description', 'No description available')
                response_parts.append(f"{i}. **{title}**")
                response_parts.append(f"   {description}")
        
        # Confidence indicator
        confidence_text = "High" if confidence > 0.8 else "Medium" if confidence > 0.5 else "Low"
        response_parts.append(f"\n*Analysis Confidence: {confidence_text}*")
        
        return "\n".join(response_parts)


class ClaudePromptMixin:
    """Mixin providing standardized Claude prompt patterns."""
    
    def create_analysis_prompt(
        self, 
        user_message: str, 
        user_context: Dict[str, Any], 
        analysis_type: str,
        specific_instructions: str = ""
    ) -> str:
        """Create standardized analysis prompt for Claude."""
        
        context_summary = self._summarize_user_context(user_context)
        
        prompt = f"""
You are an expert financial {analysis_type} agent. Analyze the following user message and financial context to provide specific insights.

User Message: "{user_message}"

User Financial Context:
{context_summary}

{specific_instructions}

Please provide your analysis in JSON format with the following structure:
{{
    "analysis": {{
        // Key metrics and findings
    }},
    "recommendations": [
        {{
            "title": "Recommendation title",
            "description": "Detailed description",
            "priority": "high|medium|low",
            "timeline": "immediate|short_term|long_term"
        }}
    ],
    "confidence_score": 0.8, // 0-1 scale
    "reasoning": "Brief explanation of analysis approach"
}}
"""
        return prompt.strip()
    
    def _summarize_user_context(self, user_context: Dict[str, Any]) -> str:
        """Create a concise summary of user context for prompts."""
        summary_parts = []
        
        # Basic info
        if user_context.get('monthly_income'):
            summary_parts.append(f"Monthly Income: {self.format_currency(user_context['monthly_income'])}")
        
        if user_context.get('monthly_expenses'):
            summary_parts.append(f"Monthly Expenses: {self.format_currency(user_context['monthly_expenses'])}")
        
        # Accounts
        accounts = user_context.get('accounts', [])
        if accounts:
            total_balance = sum(acc.get('balance', 0) for acc in accounts)
            summary_parts.append(f"Total Account Balance: {self.format_currency(total_balance)}")
        
        # Goals
        goals = user_context.get('goals', [])
        if goals:
            summary_parts.append(f"Financial Goals: {len(goals)} active goals")
        
        return "\n".join(summary_parts) if summary_parts else "Limited financial context available"


class ValidationMixin:
    """Mixin providing input validation utilities."""
    
    def validate_user_context(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean user context data."""
        validated = {}
        
        # Validate numeric fields
        numeric_fields = ['monthly_income', 'monthly_expenses', 'net_worth']
        for field in numeric_fields:
            value = user_context.get(field)
            if isinstance(value, (int, float)) and value >= 0:
                validated[field] = float(value)
        
        # Validate accounts
        accounts = user_context.get('accounts', [])
        if isinstance(accounts, list):
            validated_accounts = []
            for account in accounts:
                if isinstance(account, dict) and 'balance' in account:
                    validated_accounts.append(account)
            validated['accounts'] = validated_accounts
        
        # Validate goals
        goals = user_context.get('goals', [])
        if isinstance(goals, list):
            validated['goals'] = [goal for goal in goals if isinstance(goal, dict)]
        
        return validated
    
    def validate_amount(self, amount: Any) -> Optional[float]:
        """Validate and convert amount to float."""
        try:
            if isinstance(amount, str):
                # Remove currency symbols and commas
                clean_amount = re.sub(r'[$,]', '', amount)
                return float(clean_amount)
            elif isinstance(amount, (int, float)):
                return float(amount)
        except (ValueError, TypeError):
            pass
        return None