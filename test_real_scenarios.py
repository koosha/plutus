#!/usr/bin/env python3
"""
Real Scenario Testing for Plutus
=================================

Tests the system with realistic user profiles and questions.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from plutus.agents.advanced_orchestrator import AdvancedOrchestrator
from plutus.services.memory_service import MemoryService

# Test user profiles
TEST_USERS = {
    "user_1": {
        "user_id": "alex_engineer",
        "name": "Alex Chen",
        "age": 32,
        "occupation": "Software Engineer",
        "monthly_income": 12000,
        "monthly_expenses": 6500,
        "net_worth": 185000,
        "accounts": [
            {"type": "checking", "name": "Chase Checking", "balance": 15000},
            {"type": "savings", "name": "High Yield Savings", "balance": 45000},
            {"type": "investment", "name": "401(k)", "balance": 95000},
            {"type": "investment", "name": "Brokerage", "balance": 30000}
        ],
        "goals": [
            {
                "id": "goal_house",
                "type": "house_purchase",
                "name": "House Down Payment",
                "target_amount": 120000,
                "current_amount": 45000,
                "target_date": "2026-06-01"
            },
            {
                "id": "goal_retirement",
                "type": "retirement",
                "name": "Early Retirement",
                "target_amount": 2000000,
                "current_amount": 95000,
                "target_date": "2050-01-01"
            }
        ],
        "debts": [
            {"type": "student_loan", "balance": 15000, "interest_rate": 0.045, "minimum_payment": 350}
        ],
        "risk_tolerance": "moderate",
        "employment_type": "full_time",
        "industry": "technology",
        "years_with_employer": 4,
        "has_dependents": False
    },
    "user_2": {
        "user_id": "sarah_family",
        "name": "Sarah Johnson",
        "age": 38,
        "occupation": "Marketing Manager",
        "monthly_income": 8500,
        "monthly_expenses": 7200,
        "net_worth": 125000,
        "accounts": [
            {"type": "checking", "name": "Bank of America Checking", "balance": 8000},
            {"type": "savings", "name": "Emergency Fund", "balance": 25000},
            {"type": "investment", "name": "401(k)", "balance": 68000},
            {"type": "investment", "name": "529 Plan", "balance": 24000}
        ],
        "goals": [
            {
                "id": "goal_college",
                "type": "education",
                "name": "Kids College Fund",
                "target_amount": 200000,
                "current_amount": 24000,
                "target_date": "2035-09-01"
            },
            {
                "id": "goal_emergency",
                "type": "emergency_fund",
                "name": "6-Month Emergency Fund",
                "target_amount": 43200,
                "current_amount": 25000,
                "target_date": "2025-12-01"
            }
        ],
        "debts": [
            {"type": "mortgage", "balance": 285000, "interest_rate": 0.0425, "minimum_payment": 1850},
            {"type": "car_loan", "balance": 18000, "interest_rate": 0.055, "minimum_payment": 425}
        ],
        "risk_tolerance": "conservative",
        "employment_type": "full_time",
        "industry": "marketing",
        "years_with_employer": 6,
        "has_dependents": True
    }
}

# Test questions (10 from the 100 sample questions)
TEST_QUESTIONS = [
    "What's my current financial health score?",
    "How much should I be saving for retirement each month?",
    "Should I pay off my student loans or invest more?",
    "What's the best strategy to save for a house down payment?",
    "How can I optimize my investment portfolio?",
    "Am I on track for my financial goals?",
    "What are my biggest financial risks right now?",
    "How much emergency fund do I need?",
    "Should I increase my 401k contributions?",
    "What's my recommended asset allocation?"
]


class TestRunner:
    """Runs tests with real user scenarios."""
    
    def __init__(self):
        self.orchestrator = AdvancedOrchestrator()
        self.memory_service = MemoryService(db_path="test_scenarios.db")
        self.results = []
    
    async def test_user_questions(self, user_profile: Dict[str, Any], questions: List[str]):
        """Test a user profile with multiple questions."""
        
        user_id = user_profile["user_id"]
        user_name = user_profile["name"]
        
        print(f"\n{'='*80}")
        print(f"🧑 Testing User: {user_name} ({user_id})")
        print(f"{'='*80}")
        print(f"Profile Summary:")
        print(f"  • Age: {user_profile['age']}, {user_profile['occupation']}")
        print(f"  • Monthly Income: ${user_profile['monthly_income']:,}")
        print(f"  • Monthly Expenses: ${user_profile['monthly_expenses']:,}")
        print(f"  • Net Worth: ${user_profile['net_worth']:,}")
        print(f"  • Risk Tolerance: {user_profile['risk_tolerance'].title()}")
        print(f"  • Has Dependents: {'Yes' if user_profile['has_dependents'] else 'No'}")
        
        session_id = f"test_session_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        for i, question in enumerate(questions, 1):
            print(f"\n{'-'*60}")
            print(f"📝 Question {i}: {question}")
            print(f"{'-'*60}")
            
            try:
                # Create conversation state with user context
                state = {
                    "user_message": question,
                    "user_id": user_id,
                    "session_id": session_id,
                    "user_context": user_profile,
                    "agent_results": [],
                    "metadata": {}
                }
                
                # Process through orchestrator
                start_time = datetime.now()
                response = await self.orchestrator.process(state)
                end_time = datetime.now()
                processing_time = (end_time - start_time).total_seconds()
                
                if response.get("success"):
                    print(f"\n✅ Response (processed in {processing_time:.2f}s):")
                    print(f"{'-'*40}")
                    
                    # Display the main response
                    if response.get("response"):
                        print(response["response"])
                    
                    # Show which agents were involved
                    agents_used = response.get("metadata", {}).get("agents_used", [])
                    if agents_used:
                        print(f"\n🤖 Agents Used: {', '.join(agents_used)}")
                    
                    # Store result
                    self.results.append({
                        "user": user_name,
                        "question": question,
                        "response": response.get("response", ""),
                        "success": True,
                        "processing_time": processing_time,
                        "agents_used": agents_used
                    })
                    
                    # Store in memory for continuity
                    await self.memory_service.store_conversation(
                        user_id,
                        session_id,
                        question,
                        response.get("response", ""),
                        response.get("agent_results", []),
                        response.get("metadata", {})
                    )
                    
                else:
                    error_msg = response.get("error", "Unknown error")
                    print(f"\n❌ Error: {error_msg}")
                    
                    self.results.append({
                        "user": user_name,
                        "question": question,
                        "response": f"Error: {error_msg}",
                        "success": False,
                        "processing_time": processing_time,
                        "agents_used": []
                    })
                
            except Exception as e:
                print(f"\n❌ Exception occurred: {e}")
                self.results.append({
                    "user": user_name,
                    "question": question,
                    "response": f"Exception: {str(e)}",
                    "success": False,
                    "processing_time": 0,
                    "agents_used": []
                })
            
            # Small delay between questions
            await asyncio.sleep(0.5)
    
    async def run_all_tests(self):
        """Run tests for all users and questions."""
        
        print("\n" + "="*80)
        print("🚀 PLUTUS REAL SCENARIO TESTING")
        print("="*80)
        print(f"Testing {len(TEST_USERS)} users with {len(TEST_QUESTIONS)} questions each")
        
        # Test each user
        for user_key, user_profile in TEST_USERS.items():
            await self.test_user_questions(user_profile, TEST_QUESTIONS)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r["success"])
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\nOverall Results:")
        print(f"  • Total Questions: {total_tests}")
        print(f"  • Successful: {successful_tests}")
        print(f"  • Failed: {total_tests - successful_tests}")
        print(f"  • Success Rate: {success_rate:.1f}%")
        
        # Average processing time
        successful_times = [r["processing_time"] for r in self.results if r["success"]]
        if successful_times:
            avg_time = sum(successful_times) / len(successful_times)
            print(f"  • Avg Processing Time: {avg_time:.2f}s")
        
        # Agent usage statistics
        agent_usage = {}
        for result in self.results:
            for agent in result.get("agents_used", []):
                agent_usage[agent] = agent_usage.get(agent, 0) + 1
        
        if agent_usage:
            print(f"\nAgent Usage Statistics:")
            for agent, count in sorted(agent_usage.items(), key=lambda x: x[1], reverse=True):
                print(f"  • {agent}: {count} times")
        
        # Per-user summary
        print(f"\nPer-User Performance:")
        for user_key, user_profile in TEST_USERS.items():
            user_name = user_profile["name"]
            user_results = [r for r in self.results if r["user"] == user_name]
            user_successful = sum(1 for r in user_results if r["success"])
            user_rate = (user_successful / len(user_results) * 100) if user_results else 0
            print(f"  • {user_name}: {user_successful}/{len(user_results)} successful ({user_rate:.1f}%)")


async def main():
    """Run the test suite."""
    
    runner = TestRunner()
    await runner.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())