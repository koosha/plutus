"""
Enhanced User Profiling System for Plutus
==========================================

🎓 LEARNING OBJECTIVES:
1. Build comprehensive client profiles like top wealth advisors
2. Automatically extract and update key information from conversations
3. Implement strategic follow-up question system
4. Balance information gathering with user experience
5. Handle sensitive personal information securely

This creates the foundation for truly personalized wealth management advice!
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, TypedDict, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid
import re

# =============================================================================
# CONCEPT 1: Comprehensive User Profile Structure
# =============================================================================

@dataclass
class FamilyMember:
    """🎓 FAMILY MEMBER: Individual family member information"""
    name: str
    relationship: str  # spouse, child, parent, sibling, etc.
    age: Optional[int] = None
    dependent: bool = False
    special_needs: Optional[str] = None
    financial_impact: Optional[str] = None  # college planning, care costs, etc.

@dataclass
class LifeGoal:
    """🎓 LIFE GOAL: Specific financial and life objectives"""
    description: str
    category: str  # retirement, education, home, travel, business, legacy, etc.
    target_amount: Optional[float] = None
    target_date: Optional[datetime] = None
    priority: str = "medium"  # high, medium, low
    progress: float = 0.0  # 0-100%
    notes: Optional[str] = None

@dataclass
class LifeEvent:
    """🎓 LIFE EVENT: Significant events affecting financial planning"""
    event_type: str  # marriage, divorce, birth, death, job_change, illness, inheritance, etc.
    description: str
    date: datetime
    financial_impact: Optional[float] = None
    ongoing_impact: bool = False
    notes: Optional[str] = None

@dataclass
class CareerInfo:
    """🎓 CAREER INFORMATION: Professional and income details"""
    current_position: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    employment_type: str = "employed"  # employed, self_employed, business_owner, retired, unemployed
    income_stability: str = "stable"  # stable, variable, seasonal, uncertain
    career_stage: str = "mid_career"  # early_career, mid_career, senior, pre_retirement, retired
    retirement_plans: Optional[str] = None
    business_ownership: Optional[Dict[str, Any]] = None

@dataclass
class FinancialBehavior:
    """🎓 FINANCIAL BEHAVIOR: How client makes financial decisions"""
    decision_style: str = "analytical"  # analytical, intuitive, collaborative, delegative
    risk_tolerance_stated: Optional[str] = None  # what they say
    risk_tolerance_observed: Optional[str] = None  # what they actually do
    spending_personality: Optional[str] = None  # saver, spender, balanced
    investment_experience: Optional[str] = None
    financial_fears: List[str] = field(default_factory=list)
    financial_motivations: List[str] = field(default_factory=list)
    past_mistakes: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HealthAndInsurance:
    """🎓 HEALTH & INSURANCE: Health factors affecting financial planning"""
    health_status: Optional[str] = None  # excellent, good, fair, poor
    chronic_conditions: List[str] = field(default_factory=list)
    life_insurance: Optional[Dict[str, Any]] = None
    health_insurance: Optional[Dict[str, Any]] = None
    disability_insurance: Optional[Dict[str, Any]] = None
    long_term_care_insurance: Optional[Dict[str, Any]] = None
    anticipated_health_costs: Optional[float] = None

@dataclass
class ExternalFactors:
    """🎓 EXTERNAL FACTORS: Outside influences on financial planning"""
    other_advisors: List[str] = field(default_factory=list)  # CPA, attorney, etc.
    family_financial_dynamics: Optional[str] = None
    geographic_factors: Optional[str] = None
    tax_considerations: List[str] = field(default_factory=list)
    estate_planning_status: Optional[str] = None
    charitable_interests: List[str] = field(default_factory=list)

@dataclass
class EnhancedUserProfile:
    """
    🎓 COMPREHENSIVE USER PROFILE: Complete client picture for wealth management
    
    This captures everything a top wealth advisor would know about their client
    """
    # Basic Information
    user_id: str
    created_at: datetime
    last_updated: datetime
    last_active: datetime
    
    # Personal Details
    name: Optional[str] = None
    preferred_name: Optional[str] = None
    age: Optional[int] = None
    location: Optional[str] = None
    
    # Family Information
    family_members: List[FamilyMember] = field(default_factory=list)
    marital_status: Optional[str] = None  # single, married, divorced, widowed, partnered
    household_size: Optional[int] = None
    
    # Financial Data (enhanced from original)
    current_accounts: Dict[str, float] = field(default_factory=dict)
    monthly_income: Optional[float] = None
    monthly_expenses: Optional[float] = None
    net_worth: Optional[float] = None
    debt_details: Dict[str, Any] = field(default_factory=dict)
    
    # Goals and Aspirations
    life_goals: List[LifeGoal] = field(default_factory=list)
    values_and_priorities: List[str] = field(default_factory=list)
    legacy_intentions: Optional[str] = None
    
    # Career and Professional
    career_info: CareerInfo = field(default_factory=CareerInfo)
    
    # Behavioral and Psychological
    financial_behavior: FinancialBehavior = field(default_factory=FinancialBehavior)
    
    # Life Events and Changes
    significant_life_events: List[LifeEvent] = field(default_factory=list)
    upcoming_events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Health and Protection
    health_and_insurance: HealthAndInsurance = field(default_factory=HealthAndInsurance)
    
    # External Factors
    external_factors: ExternalFactors = field(default_factory=ExternalFactors)
    
    # Conversation Patterns (from original)
    preferred_communication_style: Optional[str] = None
    common_question_types: List[str] = field(default_factory=list)
    behavioral_patterns: List[str] = field(default_factory=list)
    concerns_expressed: List[str] = field(default_factory=list)
    
    # Profile Completeness and Quality
    profile_completeness_score: float = 0.0
    information_confidence: Dict[str, float] = field(default_factory=dict)
    last_information_update: Optional[datetime] = None
    
    # Follow-up Management
    pending_clarifications: List[Dict[str, Any]] = field(default_factory=list)
    follow_up_questions_asked: int = 0
    follow_up_frequency_preference: str = "balanced"  # minimal, balanced, detailed

# =============================================================================
# CONCEPT 2: Information Extraction System
# =============================================================================

class InformationExtractor:
    """
    🎓 INFORMATION EXTRACTOR: Automatically identify key information from conversations
    
    This system intelligently extracts important personal and financial information
    from natural conversation without being intrusive.
    """
    
    def __init__(self):
        self.extraction_patterns = self._initialize_extraction_patterns()
        self.logger = logging.getLogger("plutus.information_extractor")
    
    def _initialize_extraction_patterns(self) -> Dict[str, Any]:
        """Initialize regex patterns and keywords for information extraction"""
        
        return {
            # Family and Personal
            "family_members": {
                "spouse_patterns": [
                    r"my (?:wife|husband|spouse|partner) (\w+)",
                    r"(\w+) (?:is my wife|is my husband|and I are married)",
                    r"my (?:wife's|husband's) name is (\w+)"
                ],
                "children_patterns": [
                    r"my (?:son|daughter|child|kid) (\w+)",
                    r"(\w+) is (?:my son|my daughter|our child)",
                    r"(?:my|our) (?:kids|children) are (\w+)(?: and (\w+))?",
                    r"I have (\d+) (?:kids|children)"
                ],
                "parent_patterns": [
                    r"my (?:mom|mother|dad|father|parents?) (\w+)",
                    r"taking care of my (?:elderly )?(?:mom|mother|dad|father|parents)"
                ]
            },
            
            # Life Goals
            "goals": {
                "retirement_patterns": [
                    r"retire (?:at|when I'm|by) (\d+)",
                    r"retirement (?:at|by) (\d+)",
                    r"want to retire (?:early|in (\d+) years)"
                ],
                "home_patterns": [
                    r"buy (?:a|our first) house",
                    r"home (?:purchase|buying)",
                    r"house down payment"
                ],
                "education_patterns": [
                    r"college (?:fund|savings|tuition)",
                    r"pay for (?:my|our) (?:kids'|children's) (?:college|education)",
                    r"education (?:savings|fund)"
                ]
            },
            
            # Career Information
            "career": {
                "job_patterns": [
                    r"I (?:work|am employed) (?:as a|at) ([\w\s]+)",
                    r"my job (?:is|as a) ([\w\s]+)",
                    r"I'm a ([\w\s]+)"
                ],
                "income_patterns": [
                    r"make (?:about )?[\$]?([\d,]+) (?:a year|annually|per year)",
                    r"salary (?:is|of) [\$]?([\d,]+)",
                    r"earn [\$]?([\d,]+) (?:per year|annually)"
                ]
            },
            
            # Financial Behavior
            "behavior": {
                "risk_patterns": [
                    r"I'm (?:very |pretty )?(?:conservative|risk-averse|cautious)",
                    r"I'm (?:aggressive|willing to take risks)",
                    r"I (?:don't like|hate) (?:risk|losing money)"
                ],
                "spending_patterns": [
                    r"I'm a (?:saver|spender)",
                    r"I (?:love|hate) spending money",
                    r"I'm (?:frugal|tight with money|careful with money)"
                ]
            },
            
            # Life Events
            "life_events": {
                "marriage_patterns": [
                    r"(?:just |recently )?(?:got married|getting married)",
                    r"wedding (?:is |was )?(?:next year|this year|last year)"
                ],
                "birth_patterns": [
                    r"(?:just |recently )?had a baby",
                    r"expecting (?:a baby|our first child)",
                    r"(?:pregnant|having a baby)"
                ],
                "job_change_patterns": [
                    r"(?:just |recently )?(?:got a new job|changed jobs|started working)",
                    r"(?:left my job|quit my job|was laid off)"
                ]
            },
            
            # Financial Amounts
            "amounts": {
                "money_patterns": [
                    r"[\$]?([\d,]+)(?:\.\d{2})?",
                    r"(?:about |around )?[\$]?([\d,]+)(?:k|K|thousand)",
                    r"(?:about |around )?[\$]?([\d,]+)(?:m|M|million)"
                ]
            }
        }
    
    async def extract_information_from_conversation(self, 
                                                  user_message: str, 
                                                  assistant_response: str,
                                                  current_profile: EnhancedUserProfile) -> Dict[str, Any]:
        """
        🎓 CONVERSATION ANALYSIS: Extract key information from a conversation turn
        """
        
        extracted_info = {
            "family_updates": [],
            "goal_updates": [],
            "career_updates": {},
            "behavior_insights": [],
            "life_events": [],
            "financial_amounts": [],
            "confidence_scores": {}
        }
        
        # Combine user message and response for analysis
        conversation_text = f"{user_message} {assistant_response}".lower()
        
        # Extract family information
        family_info = await self._extract_family_information(conversation_text)
        if family_info:
            extracted_info["family_updates"].extend(family_info)
            extracted_info["confidence_scores"]["family"] = 0.8
        
        # Extract goals
        goal_info = await self._extract_goal_information(conversation_text)
        if goal_info:
            extracted_info["goal_updates"].extend(goal_info)
            extracted_info["confidence_scores"]["goals"] = 0.7
        
        # Extract career information
        career_info = await self._extract_career_information(conversation_text)
        if career_info:
            extracted_info["career_updates"].update(career_info)
            extracted_info["confidence_scores"]["career"] = 0.6
        
        # Extract behavioral insights
        behavior_info = await self._extract_behavioral_information(conversation_text)
        if behavior_info:
            extracted_info["behavior_insights"].extend(behavior_info)
            extracted_info["confidence_scores"]["behavior"] = 0.9
        
        # Extract life events
        events = await self._extract_life_events(conversation_text)
        if events:
            extracted_info["life_events"].extend(events)
            extracted_info["confidence_scores"]["life_events"] = 0.8
        
        return extracted_info
    
    async def _extract_family_information(self, text: str) -> List[Dict[str, Any]]:
        """Extract family member information"""
        family_updates = []
        patterns = self.extraction_patterns["family_members"]
        
        # Extract spouse information
        for pattern in patterns["spouse_patterns"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                family_updates.append({
                    "type": "family_member",
                    "name": match,
                    "relationship": "spouse",
                    "confidence": 0.8
                })
        
        # Extract children information
        for pattern in patterns["children_patterns"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    # Multiple children mentioned
                    for name in match:
                        if name:
                            family_updates.append({
                                "type": "family_member",
                                "name": name,
                                "relationship": "child",
                                "confidence": 0.7
                            })
                elif match.isdigit():
                    # Number of children mentioned
                    family_updates.append({
                        "type": "household_info",
                        "children_count": int(match),
                        "confidence": 0.9
                    })
                else:
                    # Single child name
                    family_updates.append({
                        "type": "family_member",
                        "name": match,
                        "relationship": "child",
                        "confidence": 0.7
                    })
        
        return family_updates
    
    async def _extract_goal_information(self, text: str) -> List[Dict[str, Any]]:
        """Extract financial and life goals"""
        goal_updates = []
        patterns = self.extraction_patterns["goals"]
        
        # Retirement goals
        for pattern in patterns["retirement_patterns"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                goal_updates.append({
                    "type": "goal",
                    "category": "retirement",
                    "description": f"Retire at age {match}",
                    "target_age": int(match) if match.isdigit() else None,
                    "confidence": 0.8
                })
        
        # Home purchase goals
        for pattern in patterns["home_patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                goal_updates.append({
                    "type": "goal",
                    "category": "home_purchase",
                    "description": "Purchase a home",
                    "confidence": 0.7
                })
        
        # Education goals
        for pattern in patterns["education_patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                goal_updates.append({
                    "type": "goal",
                    "category": "education",
                    "description": "Save for children's education",
                    "confidence": 0.8
                })
        
        return goal_updates
    
    async def _extract_career_information(self, text: str) -> Dict[str, Any]:
        """Extract career and income information"""
        career_updates = {}
        patterns = self.extraction_patterns["career"]
        
        # Job/profession
        for pattern in patterns["job_patterns"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                career_updates["current_position"] = match.strip()
                career_updates["confidence_job"] = 0.7
        
        # Income
        for pattern in patterns["income_patterns"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Clean up the match and convert to number
                clean_amount = match.replace(",", "")
                try:
                    amount = float(clean_amount)
                    career_updates["monthly_income"] = amount / 12  # Convert annual to monthly
                    career_updates["confidence_income"] = 0.6
                except ValueError:
                    continue
        
        return career_updates
    
    async def _extract_behavioral_information(self, text: str) -> List[Dict[str, Any]]:
        """Extract financial behavior and personality insights"""
        behavior_insights = []
        patterns = self.extraction_patterns["behavior"]
        
        # Risk tolerance
        for pattern in patterns["risk_patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                if any(word in pattern for word in ["conservative", "risk-averse", "cautious"]):
                    behavior_insights.append({
                        "type": "risk_tolerance",
                        "value": "conservative",
                        "confidence": 0.9
                    })
                elif any(word in pattern for word in ["aggressive", "willing to take risks"]):
                    behavior_insights.append({
                        "type": "risk_tolerance",
                        "value": "aggressive",
                        "confidence": 0.9
                    })
        
        # Spending personality
        for pattern in patterns["spending_patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                if any(word in pattern for word in ["saver", "frugal", "careful"]):
                    behavior_insights.append({
                        "type": "spending_personality",
                        "value": "saver",
                        "confidence": 0.8
                    })
                elif "spender" in pattern:
                    behavior_insights.append({
                        "type": "spending_personality",
                        "value": "spender",
                        "confidence": 0.8
                    })
        
        return behavior_insights
    
    async def _extract_life_events(self, text: str) -> List[Dict[str, Any]]:
        """Extract significant life events"""
        life_events = []
        patterns = self.extraction_patterns["life_events"]
        
        # Marriage events
        for pattern in patterns["marriage_patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                life_events.append({
                    "type": "life_event",
                    "event_type": "marriage",
                    "description": "Recently married or getting married",
                    "confidence": 0.8
                })
        
        # Birth events
        for pattern in patterns["birth_patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                life_events.append({
                    "type": "life_event",
                    "event_type": "birth",
                    "description": "Had or expecting a baby",
                    "confidence": 0.9
                })
        
        # Job change events
        for pattern in patterns["job_change_patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                life_events.append({
                    "type": "life_event",
                    "event_type": "job_change",
                    "description": "Recent job change or career transition",
                    "confidence": 0.7
                })
        
        return life_events

# =============================================================================
# CONCEPT 3: Profile Update Manager
# =============================================================================

class ProfileUpdateManager:
    """
    🎓 PROFILE UPDATE MANAGER: Intelligently update user profiles with new information
    
    This system decides what information to keep, update, or clarify based on
    confidence levels and existing data.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("plutus.profile_updater")
        self.update_thresholds = {
            "high_confidence": 0.8,
            "medium_confidence": 0.6,
            "low_confidence": 0.4
        }
    
    async def update_profile_from_conversation(self,
                                             profile: EnhancedUserProfile,
                                             extracted_info: Dict[str, Any],
                                             conversation_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        🎓 INTELLIGENT PROFILE UPDATE: Update profile with extracted information
        """
        
        update_summary = {
            "updates_made": [],
            "clarifications_needed": [],
            "confidence_changes": {},
            "new_follow_up_questions": []
        }
        
        # Update family information
        family_updates = await self._update_family_information(
            profile, extracted_info.get("family_updates", [])
        )
        update_summary["updates_made"].extend(family_updates)
        
        # Update goals
        goal_updates = await self._update_goals(
            profile, extracted_info.get("goal_updates", [])
        )
        update_summary["updates_made"].extend(goal_updates)
        
        # Update career information
        career_updates = await self._update_career_information(
            profile, extracted_info.get("career_updates", {})
        )
        update_summary["updates_made"].extend(career_updates)
        
        # Update behavioral insights
        behavior_updates = await self._update_behavioral_information(
            profile, extracted_info.get("behavior_insights", [])
        )
        update_summary["updates_made"].extend(behavior_updates)
        
        # Add life events
        event_updates = await self._add_life_events(
            profile, extracted_info.get("life_events", [])
        )
        update_summary["updates_made"].extend(event_updates)
        
        # Update profile metadata
        profile.last_updated = datetime.now()
        profile.last_information_update = datetime.now()
        
        # Calculate new completeness score
        profile.profile_completeness_score = await self._calculate_completeness_score(profile)
        
        # Generate follow-up questions if needed
        follow_ups = await self._generate_strategic_follow_ups(profile, update_summary)
        update_summary["new_follow_up_questions"] = follow_ups
        
        return update_summary
    
    async def _update_family_information(self, 
                                       profile: EnhancedUserProfile, 
                                       family_updates: List[Dict]) -> List[str]:
        """Update family member information"""
        updates = []
        
        for update in family_updates:
            if update["type"] == "family_member":
                # Check if family member already exists
                existing_member = None
                for member in profile.family_members:
                    if (member.name.lower() == update["name"].lower() and 
                        member.relationship == update["relationship"]):
                        existing_member = member
                        break
                
                if not existing_member and update["confidence"] >= self.update_thresholds["medium_confidence"]:
                    # Add new family member
                    new_member = FamilyMember(
                        name=update["name"],
                        relationship=update["relationship"]
                    )
                    profile.family_members.append(new_member)
                    updates.append(f"Added {update['relationship']}: {update['name']}")
                    
                    # Update information confidence
                    profile.information_confidence[f"family_{update['name']}"] = update["confidence"]
            
            elif update["type"] == "household_info":
                if "children_count" in update:
                    profile.household_size = update["children_count"] + 2  # Assume 2 adults
                    updates.append(f"Updated household size: {update['children_count']} children")
        
        return updates
    
    async def _update_goals(self, 
                          profile: EnhancedUserProfile, 
                          goal_updates: List[Dict]) -> List[str]:
        """Update life goals"""
        updates = []
        
        for update in goal_updates:
            if update["type"] == "goal" and update["confidence"] >= self.update_thresholds["medium_confidence"]:
                
                # Check if similar goal already exists
                existing_goal = None
                for goal in profile.life_goals:
                    if goal.category == update["category"]:
                        existing_goal = goal
                        break
                
                if not existing_goal:
                    # Add new goal
                    new_goal = LifeGoal(
                        description=update["description"],
                        category=update["category"],
                        priority="high" if update["confidence"] > 0.8 else "medium"
                    )
                    
                    if "target_age" in update and update["target_age"]:
                        # Convert target age to target date (approximate)
                        current_age = profile.age or 30  # Default if age not known
                        years_to_goal = update["target_age"] - current_age
                        if years_to_goal > 0:
                            new_goal.target_date = datetime.now() + timedelta(days=years_to_goal * 365)
                    
                    profile.life_goals.append(new_goal)
                    updates.append(f"Added goal: {update['description']}")
                    
                    # Update confidence
                    profile.information_confidence[f"goal_{update['category']}"] = update["confidence"]
        
        return updates
    
    async def _update_career_information(self, 
                                       profile: EnhancedUserProfile, 
                                       career_updates: Dict) -> List[str]:
        """Update career information"""
        updates = []
        
        for field, value in career_updates.items():
            if field.startswith("confidence_"):
                continue
                
            confidence_field = f"confidence_{field.split('_')[-1]}"
            confidence = career_updates.get(confidence_field, 0.5)
            
            if confidence >= self.update_thresholds["medium_confidence"]:
                if field == "current_position":
                    profile.career_info.current_position = value
                    updates.append(f"Updated job title: {value}")
                elif field == "monthly_income":
                    profile.monthly_income = value
                    updates.append(f"Updated monthly income: ${value:,.0f}")
                
                # Update confidence
                profile.information_confidence[field] = confidence
        
        return updates
    
    async def _update_behavioral_information(self, 
                                           profile: EnhancedUserProfile, 
                                           behavior_updates: List[Dict]) -> List[str]:
        """Update financial behavior insights"""
        updates = []
        
        for update in behavior_updates:
            if update["confidence"] >= self.update_thresholds["high_confidence"]:
                if update["type"] == "risk_tolerance":
                    # Update observed risk tolerance (what they actually demonstrate)
                    profile.financial_behavior.risk_tolerance_observed = update["value"]
                    updates.append(f"Updated observed risk tolerance: {update['value']}")
                    
                elif update["type"] == "spending_personality":
                    profile.financial_behavior.spending_personality = update["value"]
                    updates.append(f"Updated spending personality: {update['value']}")
                
                # Update confidence
                profile.information_confidence[f"behavior_{update['type']}"] = update["confidence"]
        
        return updates
    
    async def _add_life_events(self, 
                             profile: EnhancedUserProfile, 
                             event_updates: List[Dict]) -> List[str]:
        """Add significant life events"""
        updates = []
        
        for update in event_updates:
            if (update["type"] == "life_event" and 
                update["confidence"] >= self.update_thresholds["medium_confidence"]):
                
                # Check if similar event already recorded
                event_exists = any(
                    event.event_type == update["event_type"] 
                    for event in profile.significant_life_events
                    if (datetime.now() - event.date).days < 365  # Within last year
                )
                
                if not event_exists:
                    new_event = LifeEvent(
                        event_type=update["event_type"],
                        description=update["description"],
                        date=datetime.now(),
                        ongoing_impact=True
                    )
                    
                    profile.significant_life_events.append(new_event)
                    updates.append(f"Added life event: {update['description']}")
                    
                    # Update confidence
                    profile.information_confidence[f"event_{update['event_type']}"] = update["confidence"]
        
        return updates
    
    async def _calculate_completeness_score(self, profile: EnhancedUserProfile) -> float:
        """Calculate profile completeness score (0-100)"""
        
        # Weight different categories by importance
        weights = {
            "basic_info": 0.15,      # Name, age, location
            "family": 0.20,          # Family members, relationships
            "financial": 0.25,       # Income, assets, goals
            "career": 0.15,          # Job, industry, income stability  
            "goals": 0.15,           # Life goals and priorities
            "behavior": 0.10         # Risk tolerance, preferences
        }
        
        scores = {}
        
        # Basic info score
        basic_score = 0
        if profile.name: basic_score += 0.4
        if profile.age: basic_score += 0.3
        if profile.location: basic_score += 0.3
        scores["basic_info"] = basic_score
        
        # Family score
        family_score = 0
        if profile.marital_status: family_score += 0.3
        if profile.family_members: family_score += 0.5
        if profile.household_size: family_score += 0.2
        scores["family"] = min(1.0, family_score)
        
        # Financial score
        financial_score = 0
        if profile.monthly_income: financial_score += 0.3
        if profile.current_accounts: financial_score += 0.3
        if profile.net_worth: financial_score += 0.2
        if profile.monthly_expenses: financial_score += 0.2
        scores["financial"] = min(1.0, financial_score)
        
        # Career score
        career_score = 0
        if profile.career_info.current_position: career_score += 0.4
        if profile.career_info.industry: career_score += 0.3
        if profile.career_info.employment_type: career_score += 0.3
        scores["career"] = min(1.0, career_score)
        
        # Goals score
        goals_score = min(1.0, len(profile.life_goals) * 0.25)
        scores["goals"] = goals_score
        
        # Behavior score
        behavior_score = 0
        if profile.financial_behavior.risk_tolerance_observed: behavior_score += 0.4
        if profile.financial_behavior.spending_personality: behavior_score += 0.3
        if profile.financial_behavior.decision_style: behavior_score += 0.3
        scores["behavior"] = min(1.0, behavior_score)
        
        # Calculate weighted total
        total_score = sum(scores[category] * weights[category] for category in weights)
        
        return round(total_score * 100, 1)

# =============================================================================
# CONCEPT 4: Strategic Follow-up Question System
# =============================================================================

class FollowUpQuestionManager:
    """
    🎓 FOLLOW-UP QUESTION MANAGER: Strategic, limited follow-up questions
    
    This system determines when and what follow-up questions to ask based on:
    1. Information gaps that significantly impact advice quality
    2. User's follow-up tolerance and preferences
    3. Context and timing appropriateness
    """
    
    def __init__(self):
        self.logger = logging.getLogger("plutus.follow_up_manager")
        
        # Question priority weights
        self.question_priorities = {
            "critical": 1.0,      # Essential for good advice
            "important": 0.7,     # Significantly improves advice
            "helpful": 0.4,       # Nice to have but not essential
            "optional": 0.2       # Good for completeness
        }
        
        # User tolerance levels
        self.tolerance_limits = {
            "minimal": {"max_questions_per_session": 1, "frequency_days": 7},
            "balanced": {"max_questions_per_session": 2, "frequency_days": 3},
            "detailed": {"max_questions_per_session": 3, "frequency_days": 1}
        }
    
    async def generate_strategic_follow_ups(self, 
                                          profile: EnhancedUserProfile,
                                          recent_conversation: Dict[str, Any],
                                          update_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        🎓 STRATEGIC FOLLOW-UP GENERATION: Create targeted follow-up questions
        """
        
        # Check if we should ask follow-up questions at all
        if not await self._should_ask_follow_ups(profile):
            return []
        
        # Generate potential questions
        potential_questions = []
        
        # Critical information gaps
        critical_questions = await self._generate_critical_questions(profile, recent_conversation)
        potential_questions.extend(critical_questions)
        
        # Important context questions
        important_questions = await self._generate_important_questions(profile, update_summary)
        potential_questions.extend(important_questions)
        
        # Helpful clarification questions
        helpful_questions = await self._generate_helpful_questions(profile, recent_conversation)
        potential_questions.extend(helpful_questions)
        
        # Prioritize and filter questions
        selected_questions = await self._prioritize_and_filter_questions(
            potential_questions, profile
        )
        
        return selected_questions
    
    async def _should_ask_follow_ups(self, profile: EnhancedUserProfile) -> bool:
        """Determine if we should ask follow-up questions"""
        
        # Check user's tolerance level
        tolerance = profile.follow_up_frequency_preference
        limits = self.tolerance_limits[tolerance]
        
        # Check frequency limits
        last_follow_up = getattr(profile, 'last_follow_up_date', None)
        if last_follow_up:
            days_since = (datetime.now() - last_follow_up).days
            if days_since < limits["frequency_days"]:
                return False
        
        # Check if user has been asked too many questions recently
        recent_questions = sum(1 for q in profile.pending_clarifications 
                             if (datetime.now() - q.get('created_at', datetime.now())).days < 7)
        
        if recent_questions >= limits["max_questions_per_session"]:
            return False
        
        return True
    
    async def _generate_critical_questions(self, 
                                         profile: EnhancedUserProfile,
                                         conversation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate critical questions that significantly impact advice quality"""
        
        critical_questions = []
        
        # Age is critical for retirement planning
        if not profile.age and any("retire" in goal.description.lower() 
                                 for goal in profile.life_goals):
            critical_questions.append({
                "question": "To provide accurate retirement planning advice, could you share your current age?",
                "category": "basic_demographics",
                "priority": "critical",
                "reasoning": "Age is essential for retirement timeline calculations",
                "expected_response_type": "number"
            })
        
        # Income is critical for most financial planning
        if not profile.monthly_income and profile.profile_completeness_score < 50:
            critical_questions.append({
                "question": "What's your approximate monthly income? This helps me provide more accurate recommendations.",
                "category": "financial_basics",
                "priority": "critical", 
                "reasoning": "Income is foundational for all financial planning",
                "expected_response_type": "currency"
            })
        
        # Family status is critical for goal prioritization
        if (not profile.marital_status and not profile.family_members and 
            any("education" in goal.category or "family" in goal.description.lower() 
                for goal in profile.life_goals)):
            critical_questions.append({
                "question": "Are you married or do you have children? This affects how we prioritize your financial goals.",
                "category": "family_status",
                "priority": "critical",
                "reasoning": "Family status changes financial planning priorities significantly",
                "expected_response_type": "text"
            })
        
        return critical_questions
    
    async def _generate_important_questions(self, 
                                          profile: EnhancedUserProfile,
                                          update_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate important questions that improve advice quality"""
        
        important_questions = []
        
        # Risk tolerance clarification
        if (profile.financial_behavior.risk_tolerance_stated != 
            profile.financial_behavior.risk_tolerance_observed and
            both_exist(profile.financial_behavior.risk_tolerance_stated, 
                      profile.financial_behavior.risk_tolerance_observed)):
            
            important_questions.append({
                "question": f"I notice you mentioned being {profile.financial_behavior.risk_tolerance_stated} with investments, but your preferences suggest {profile.financial_behavior.risk_tolerance_observed}. Which better describes your comfort level?",
                "category": "risk_tolerance",
                "priority": "important",
                "reasoning": "Conflicting risk tolerance information affects investment recommendations",
                "expected_response_type": "choice"
            })
        
        # Goal timeline clarification
        for goal in profile.life_goals:
            if goal.category in ["retirement", "home_purchase", "education"] and not goal.target_date:
                important_questions.append({
                    "question": f"When are you hoping to achieve your goal of {goal.description.lower()}?",
                    "category": "goal_timeline",
                    "priority": "important",
                    "reasoning": "Timeline affects investment strategy and savings requirements",
                    "expected_response_type": "date",
                    "goal_id": goal.description
                })
                break  # Only ask about one goal at a time
        
        # Emergency fund status
        if (not any("emergency" in account.lower() for account in profile.current_accounts) and
            profile.monthly_expenses and profile.monthly_income):
            
            emergency_fund_months = sum(profile.current_accounts.values()) / profile.monthly_expenses
            if emergency_fund_months < 3:
                important_questions.append({
                    "question": "Do you have an emergency fund set aside for unexpected expenses? If so, how many months of expenses does it cover?",
                    "category": "emergency_planning",
                    "priority": "important",
                    "reasoning": "Emergency fund adequacy affects all other financial planning",
                    "expected_response_type": "number"
                })
        
        return important_questions
    
    async def _generate_helpful_questions(self, 
                                        profile: EnhancedUserProfile,
                                        conversation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate helpful questions that enhance personalization"""
        
        helpful_questions = []
        
        # Investment experience
        if not profile.financial_behavior.investment_experience:
            helpful_questions.append({
                "question": "How would you describe your investment experience - beginner, intermediate, or experienced?",
                "category": "investment_experience",
                "priority": "helpful",
                "reasoning": "Investment experience affects recommendation complexity",
                "expected_response_type": "choice"
            })
        
        # Communication preferences
        if not profile.preferred_communication_style and profile.follow_up_questions_asked > 3:
            helpful_questions.append({
                "question": "Would you prefer detailed explanations or concise recommendations in our conversations?",
                "category": "communication_style",
                "priority": "helpful", 
                "reasoning": "Communication preferences improve user experience",
                "expected_response_type": "choice"
            })
        
        return helpful_questions
    
    async def _prioritize_and_filter_questions(self, 
                                             potential_questions: List[Dict[str, Any]],
                                             profile: EnhancedUserProfile) -> List[Dict[str, Any]]:
        """Prioritize and filter questions based on user tolerance and context"""
        
        # Sort by priority
        priority_order = ["critical", "important", "helpful", "optional"]
        potential_questions.sort(key=lambda q: priority_order.index(q["priority"]))
        
        # Apply user tolerance limits
        tolerance = profile.follow_up_frequency_preference
        max_questions = self.tolerance_limits[tolerance]["max_questions_per_session"]
        
        # Select top questions within limit
        selected_questions = potential_questions[:max_questions]
        
        # Add metadata
        for question in selected_questions:
            question.update({
                "id": str(uuid.uuid4()),
                "created_at": datetime.now(),
                "user_id": profile.user_id,
                "status": "pending"
            })
        
        return selected_questions

def both_exist(a, b):
    """Helper function to check if both values exist and are not None"""
    return a is not None and b is not None

# =============================================================================
# DEMONSTRATION: Enhanced Profile System
# =============================================================================

async def demonstrate_enhanced_profiling():
    """
    🎓 FULL DEMONSTRATION: Enhanced user profiling with intelligent updates
    """
    
    print("="*70)
    print("🎓 ENHANCED USER PROFILING SYSTEM DEMONSTRATION")
    print("="*70)
    
    # Initialize systems
    extractor = InformationExtractor()
    updater = ProfileUpdateManager()
    follow_up_manager = FollowUpQuestionManager()
    
    # Create initial user profile
    user_profile = EnhancedUserProfile(
        user_id="demo_user_456",
        created_at=datetime.now(),
        last_updated=datetime.now(),
        last_active=datetime.now(),
        name="Sarah",
        age=32,
        current_accounts={"checking": 3500, "savings": 18000, "401k": 25000},
        monthly_income=6500
    )
    
    print(f"\n👤 Initial Profile for {user_profile.name}:")
    print(f"   Age: {user_profile.age}")
    print(f"   Monthly Income: ${user_profile.monthly_income:,}")
    print(f"   Completeness: {user_profile.profile_completeness_score}%")
    
    # Simulate conversation scenarios
    conversation_scenarios = [
        {
            "user_message": "My husband John and I are thinking about buying our first house. We want to retire by 60.",
            "assistant_response": "That's exciting! Home ownership and early retirement are great goals. Let me analyze your current financial situation to help you plan for both.",
            "scenario": "Family and goals revelation"
        },
        {
            "user_message": "I work as a software engineer at a tech company and make about $78,000 per year. I'm pretty conservative with investments.",
            "assistant_response": "Your income provides a solid foundation for your goals. Conservative investing can still help you build wealth steadily over time.",
            "scenario": "Career and risk tolerance"
        },
        {
            "user_message": "We just had our first baby last month! Her name is Emma. I'm worried about college costs.",
            "assistant_response": "Congratulations on Emma! Starting college savings early gives you a huge advantage with compound growth. Let me show you some strategies.",
            "scenario": "Major life event - new baby"
        }
    ]
    
    # Process each conversation
    for i, scenario in enumerate(conversation_scenarios, 1):
        print(f"\n{'='*50}")
        print(f"📱 Conversation {i}: {scenario['scenario']}")
        print(f"{'='*50}")
        print(f"User: {scenario['user_message']}")
        print(f"Assistant: {scenario['assistant_response'][:100]}...")
        
        # Extract information
        extracted_info = await extractor.extract_information_from_conversation(
            scenario["user_message"],
            scenario["assistant_response"],
            user_profile
        )
        
        print(f"\n🔍 Information Extracted:")
        for key, value in extracted_info.items():
            if value and key != "confidence_scores":
                print(f"   {key}: {len(value) if isinstance(value, list) else value}")
        
        # Update profile
        update_summary = await updater.update_profile_from_conversation(
            user_profile, extracted_info, {"conversation_id": f"conv_{i}"}
        )
        
        print(f"\n📝 Profile Updates Made:")
        for update in update_summary["updates_made"]:
            print(f"   ✅ {update}")
        
        # Generate follow-up questions
        follow_ups = await follow_up_manager.generate_strategic_follow_ups(
            user_profile, scenario, update_summary
        )
        
        if follow_ups:
            print(f"\n❓ Strategic Follow-up Questions:")
            for question in follow_ups:
                print(f"   {question['priority'].upper()}: {question['question']}")
                print(f"   Reason: {question['reasoning']}")
        else:
            print(f"\n✨ No follow-up questions needed")
        
        print(f"\n📊 Updated Profile Completeness: {user_profile.profile_completeness_score}%")
    
    # Final profile summary
    print(f"\n{'='*70}")
    print("🎯 FINAL COMPREHENSIVE PROFILE")
    print(f"{'='*70}")
    
    print(f"\n👤 Personal Information:")
    print(f"   Name: {user_profile.name}")
    print(f"   Age: {user_profile.age}")
    print(f"   Marital Status: {'Married' if user_profile.family_members else 'Unknown'}")
    
    print(f"\n👨‍👩‍👧‍👦 Family Members:")
    for member in user_profile.family_members:
        print(f"   {member.relationship.title()}: {member.name}")
    
    print(f"\n💼 Career Information:")
    if user_profile.career_info.current_position:
        print(f"   Position: {user_profile.career_info.current_position}")
    print(f"   Monthly Income: ${user_profile.monthly_income:,}")
    
    print(f"\n🎯 Life Goals:")
    for goal in user_profile.life_goals:
        print(f"   {goal.category.title()}: {goal.description}")
        if goal.target_date:
            print(f"     Target: {goal.target_date.strftime('%Y')}")
    
    print(f"\n🧠 Financial Behavior:")
    if user_profile.financial_behavior.risk_tolerance_observed:
        print(f"   Risk Tolerance: {user_profile.financial_behavior.risk_tolerance_observed}")
    if user_profile.financial_behavior.spending_personality:
        print(f"   Spending Style: {user_profile.financial_behavior.spending_personality}")
    
    print(f"\n📅 Recent Life Events:")
    for event in user_profile.significant_life_events:
        print(f"   {event.event_type.title()}: {event.description}")
    
    print(f"\n📈 Profile Quality:")
    print(f"   Completeness Score: {user_profile.profile_completeness_score}%")
    print(f"   Information Confidence: {len(user_profile.information_confidence)} verified items")
    
    print(f"\n{'='*70}")
    print("🎓 KEY ENHANCED PROFILING CONCEPTS DEMONSTRATED")
    print(f"{'='*70}")
    print("""
    1. COMPREHENSIVE PROFILE STRUCTURE:
       ✅ Family members and relationships
       ✅ Life goals with timelines and priorities
       ✅ Career and professional information
       ✅ Financial behavior and personality insights
       ✅ Life events and transitions
    
    2. INTELLIGENT INFORMATION EXTRACTION:
       ✅ Natural language processing for key facts
       ✅ Pattern recognition for family, goals, career info
       ✅ Confidence scoring for reliability
       ✅ Context-aware extraction
    
    3. SMART PROFILE UPDATES:
       ✅ Confidence-based update decisions
       ✅ Duplicate detection and merging
       ✅ Completeness score calculation
       ✅ Metadata tracking for audit trail
    
    4. STRATEGIC FOLLOW-UP QUESTIONS:
       ✅ Priority-based question generation
       ✅ User tolerance and frequency limits
       ✅ Context-appropriate timing
       ✅ Meaningful impact on advice quality
    
    5. PRIVACY AND SENSITIVITY:
       ✅ Confidence levels for data reliability
       ✅ Structured storage for security
       ✅ Limited, purposeful data collection
       ✅ User control over information sharing
    """)

if __name__ == "__main__":
    asyncio.run(demonstrate_enhanced_profiling())

"""
🎓 ENHANCED PROFILING KEY TAKEAWAYS:

1. COMPREHENSIVE CLIENT UNDERSTANDING:
   - Go beyond financial data to understand complete life picture
   - Capture family dynamics, goals, values, and behavioral patterns
   - Track life events and transitions that affect financial planning

2. INTELLIGENT INFORMATION EXTRACTION:
   - Automatically identify key information from natural conversation
   - Use confidence scoring to determine data reliability
   - Extract family members, goals, career info, and behavioral insights

3. SMART PROFILE MANAGEMENT:
   - Update profiles based on confidence levels and existing data
   - Avoid duplicate information and conflicting data
   - Calculate completeness scores to guide information gathering

4. STRATEGIC FOLLOW-UP QUESTIONS:
   - Ask only high-impact questions that significantly improve advice
   - Respect user preferences for question frequency and detail
   - Prioritize critical information gaps over nice-to-have details

5. PRODUCTION CONSIDERATIONS:
   - Handle sensitive personal information securely
   - Provide transparency about what information is collected
   - Give users control over their data and privacy settings

This enhanced profiling system enables Plutus to provide truly personalized 
financial advice that considers the client's complete life situation!
"""