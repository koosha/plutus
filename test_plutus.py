#!/usr/bin/env python3
"""
Plutus Test Runner
==================

Comprehensive test runner for Plutus AI system including:
1. Production readiness tests
2. 100-question user scenario tests  
3. Live output monitoring
"""

import sys
import json
import asyncio
import time
from pathlib import Path
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from plutus import PlutusConfig, PlutusOrchestrator, set_config
from plutus.core.config import get_config

class PlutusTestRunner:
    def __init__(self):
        self.config = PlutusConfig.development()
        set_config(self.config)
        self.orchestrator = PlutusOrchestrator()
        self.results = {"passed": 0, "failed": 0, "total": 0}
        
    def load_test_data(self):
        """Load test users and questions."""
        try:
            with open("data/sample_users.json", "r") as f:
                self.users_data = json.load(f)
                
            with open("data/sample_questions.json", "r") as f:
                self.questions_data = json.load(f)
                
            print(f"✅ Loaded {len(self.users_data.get('users', []))} users")
            print(f"✅ Loaded {len(self.questions_data.get('questions', []))} questions")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load test data: {e}")
            return False
    
    def run_production_tests(self):
        """Run production readiness tests."""
        print("\n🚀 PLUTUS PRODUCTION READINESS TEST")
        print("="*50)
        
        # Test 1: Configuration
        self.results["total"] += 1
        try:
            config = get_config()
            print("✅ Configuration loading: OK")
            print(f"   Integration mode: {config.integration_mode}")
            print(f"   API key available: {'Yes' if config.anthropic_api_key else 'No (simulation mode)'}")
            self.results["passed"] += 1
        except Exception as e:
            print(f"❌ Configuration test failed: {e}")
            self.results["failed"] += 1
            
        # Test 2: Orchestrator instantiation
        self.results["total"] += 1
        try:
            orchestrator = PlutusOrchestrator()
            print("✅ Orchestrator instantiation: OK")
            self.results["passed"] += 1
        except Exception as e:
            print(f"❌ Orchestrator test failed: {e}")
            self.results["failed"] += 1
            
        # Test 3: Data loading
        self.results["total"] += 1
        if self.load_test_data():
            print("✅ Test data loading: OK")
            self.results["passed"] += 1
        else:
            print("❌ Test data loading: FAILED")
            self.results["failed"] += 1
            
    async def run_user_scenario_test(self, user_index: int = 0, num_questions: int = 100):
        """Run comprehensive test for one user with multiple questions."""
        
        if not hasattr(self, 'users_data') or not hasattr(self, 'questions_data'):
            print("❌ Test data not loaded")
            return
            
        users = self.users_data.get('users', [])
        questions = self.questions_data.get('questions', [])
        
        if user_index >= len(users):
            print(f"❌ User index {user_index} out of range (max: {len(users)-1})")
            return
            
        user = users[user_index]
        test_questions = questions[:num_questions]  # Take first N questions
        
        print(f"\n🧪 TESTING USER SCENARIO: {user['name']}")
        print("="*60)
        print(f"User: {user['name']} ({user['age']} years old)")
        print(f"Job: {user['job_title']} at {user.get('company', 'N/A')}")
        print(f"Income: ${user['annual_income']:,}/year")
        print(f"Risk Tolerance: {user['risk_tolerance']}")
        print(f"Testing with {len(test_questions)} questions...")
        print("-"*60)
        
        # Build user context
        user_context = {
            "user_id": user["user_id"],
            "name": user["name"],
            "age": user["age"],
            "annual_income": user["annual_income"],
            "monthly_income": user["monthly_income"],
            "monthly_expenses": user["monthly_expenses"],
            "risk_tolerance": user["risk_tolerance"],
            "investment_experience": user.get("investment_experience", "beginner"),
            "marital_status": user.get("marital_status", "single"),
            "location": user.get("location", ""),
            "financial_goals": user.get("financial_goals", []),
            "current_investments": user.get("current_investments", {}),
            "debt": user.get("debt", {}),
        }
        
        successful_responses = 0
        failed_responses = 0
        
        # Run questions with live output
        for i, question in enumerate(test_questions, 1):
            question_text = question.get("question", "")
            category = question.get("category", "general")
            complexity = question.get("complexity", "intermediate")
            
            print(f"\n📋 Question {i}/{len(test_questions)}")
            print(f"Category: {category} | Complexity: {complexity}")
            print(f"Q: {question_text}")
            print("Thinking... 🤔", end="", flush=True)
            
            try:
                start_time = time.time()
                
                # Call Plutus orchestrator
                result = await self.orchestrator.process({
                    "user_message": question_text,
                    "user_id": user["user_id"],
                    "user_context": user_context
                })
                
                end_time = time.time()
                response_time = end_time - start_time
                
                print(f"\r✅ Response ({response_time:.1f}s):")
                
                # Print response
                response_text = result.get("response", "No response generated")
                agents_used = result.get("metadata", {}).get("agents_used", [])
                
                # Truncate long responses for readability
                if len(response_text) > 200:
                    display_response = response_text[:200] + "..."
                else:
                    display_response = response_text
                    
                print(f"🤖 {display_response}")
                if agents_used:
                    print(f"🔧 Agents used: {', '.join(agents_used)}")
                    
                successful_responses += 1
                
                # Small delay to see output clearly
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"\r❌ Error: {str(e)[:100]}")
                failed_responses += 1
                
        # Summary
        print(f"\n📊 TEST SUMMARY FOR {user['name'].upper()}")
        print("="*60)
        print(f"Questions processed: {successful_responses + failed_responses}")
        print(f"Successful responses: {successful_responses}")
        print(f"Failed responses: {failed_responses}")
        success_rate = (successful_responses / len(test_questions)) * 100 if test_questions else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        return {
            "user": user["name"],
            "total_questions": len(test_questions),
            "successful": successful_responses,
            "failed": failed_responses,
            "success_rate": success_rate
        }

async def main():
    """Main test function."""
    print("🧠 PLUTUS AI SYSTEM TEST")
    print("="*50)
    
    tester = PlutusTestRunner()
    
    # Run production readiness tests
    tester.run_production_tests()
    
    print(f"\n📋 Production Test Results:")
    print(f"Passed: {tester.results['passed']}/{tester.results['total']}")
    
    if tester.results['passed'] == tester.results['total']:
        print("✅ All production tests passed! Running user scenario test...\n")
        
        # Run user scenario test for first user with 100 questions  
        result = await tester.run_user_scenario_test(user_index=0, num_questions=100)
        
        if result:
            print(f"\n🎉 COMPLETE TEST RESULTS:")
            print(f"Production tests: {tester.results['passed']}/{tester.results['total']}")
            print(f"User scenario: {result['successful']}/{result['total_questions']} ({result['success_rate']:.1f}%)")
            
    else:
        print("❌ Some production tests failed. Fix issues before running scenario tests.")

if __name__ == "__main__":
    asyncio.run(main())