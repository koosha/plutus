#!/usr/bin/env python3
"""
Phase 3 Advanced Agents Test Suite
==================================

Comprehensive testing for all Phase 3 specialized agents:
- Goal Extraction Agent
- Recommendation Agent  
- Risk Assessment Agent
- Advanced Orchestrator
- Memory Service

This test suite validates that all advanced features work correctly
before integration with Wealthify.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from plutus.agents.goal_extraction_agent import GoalExtractionAgent
    from plutus.agents.recommendation_agent import RecommendationAgent
    from plutus.agents.risk_assessment_agent import RiskAssessmentAgent
    from plutus.agents.advanced_orchestrator import AdvancedOrchestrator
    from plutus.services.memory_service import MemoryService
    from plutus.models.state import ConversationState
    print("✅ Successfully imported all Phase 3 components")
except ImportError as e:
    print(f"❌ Error importing Phase 3 components: {e}")
    sys.exit(1)


class Phase3TestSuite:
    """Comprehensive test suite for Phase 3 agents"""
    
    def __init__(self):
        self.goal_agent = GoalExtractionAgent()
        self.recommendation_agent = RecommendationAgent()
        self.risk_agent = RiskAssessmentAgent()
        self.advanced_orchestrator = AdvancedOrchestrator()
        self.memory_service = MemoryService(db_path="test_memory.db")
        
        # Test user context
        self.test_user_context = {
            "user_id": "test_user_123",
            "name": "Alex Johnson",
            "age": 35,
            "monthly_income": 7500,
            "monthly_expenses": 5200,
            "net_worth": 125000,
            "accounts": [
                {"type": "checking", "name": "Primary Checking", "balance": 8500},
                {"type": "savings", "name": "Emergency Fund", "balance": 15000},
                {"type": "investment", "name": "401(k)", "balance": 85000},
                {"type": "investment", "name": "Brokerage", "balance": 16500}
            ],
            "goals": [
                {
                    "id": "goal_retirement",
                    "type": "retirement",
                    "name": "Retirement Savings",
                    "target_amount": 1000000,
                    "current_amount": 85000,
                    "target_date": "2055-01-01"
                }
            ],
            "recent_transactions": [
                {"amount": 7500, "category": "salary", "description": "Monthly Salary", "date": "2025-01-01"},
                {"amount": -1200, "category": "rent", "description": "Monthly Rent", "date": "2025-01-01"},
                {"amount": -150, "category": "groceries", "description": "Grocery Store", "date": "2025-01-14"}
            ],
            "risk_tolerance": "moderate",
            "employment_type": "full_time",
            "industry": "technology",
            "years_with_employer": 3,
            "has_dependents": True
        }
    
    async def run_all_tests(self):
        """Run comprehensive test suite"""
        
        print("🚀 PHASE 3 ADVANCED AGENTS TEST SUITE")
        print("=" * 60)
        
        test_results = {}
        
        # Test 1: Goal Extraction Agent
        print("\n1️⃣ Testing Goal Extraction Agent...")
        test_results["goal_extraction"] = await self.test_goal_extraction_agent()
        
        # Test 2: Recommendation Agent
        print("\n2️⃣ Testing Recommendation Agent...")
        test_results["recommendation"] = await self.test_recommendation_agent()
        
        # Test 3: Risk Assessment Agent
        print("\n3️⃣ Testing Risk Assessment Agent...")
        test_results["risk_assessment"] = await self.test_risk_assessment_agent()
        
        # Test 4: Advanced Orchestrator
        print("\n4️⃣ Testing Advanced Orchestrator...")
        test_results["advanced_orchestrator"] = await self.test_advanced_orchestrator()
        
        # Test 5: Memory Service
        print("\n5️⃣ Testing Memory Service...")
        test_results["memory_service"] = await self.test_memory_service()
        
        # Test 6: Integration Test
        print("\n6️⃣ Testing Full Integration...")
        test_results["integration"] = await self.test_full_integration()
        
        # Summary
        print("\n" + "=" * 60)
        self.print_test_summary(test_results)
    
    async def test_goal_extraction_agent(self):
        """Test Goal Extraction Agent"""
        
        test_messages = [
            "I want to save $50,000 for a house down payment in 3 years",
            "My goal is to have an emergency fund of 6 months expenses",
            "I'm planning to retire with $2 million by age 65",
            "Should I invest in stocks or just keep saving money?",
            "What's my current financial health?"
        ]
        
        results = {"total": len(test_messages), "passed": 0, "details": []}
        
        for i, message in enumerate(test_messages, 1):
            try:
                state = self._create_test_state(message)
                result = await self.goal_agent.process(state)
                
                success = result.get("success", False)
                analysis = result.get("analysis", {})
                response = result.get("response", "")
                
                if success:
                    results["passed"] += 1
                    status = "✅"
                else:
                    status = "❌"
                
                results["details"].append({
                    "test": f"Goal Test {i}",
                    "message": message[:40] + "...",
                    "success": success,
                    "goal_related": analysis.get("goal_related", False),
                    "confidence": analysis.get("confidence", 0),
                    "response_length": len(response)
                })
                
                print(f"   {status} Test {i}: Goal related={analysis.get('goal_related', False)}, "
                      f"Confidence={analysis.get('confidence', 0):.1%}")
                
            except Exception as e:
                results["details"].append({
                    "test": f"Goal Test {i}",
                    "message": message[:40] + "...",
                    "success": False,
                    "error": str(e)
                })
                print(f"   ❌ Test {i}: Exception - {e}")
        
        return results
    
    async def test_recommendation_agent(self):
        """Test Recommendation Agent"""
        
        test_scenarios = [
            {
                "message": "What should I do with my money?",
                "context_override": {"monthly_income": 5000, "monthly_expenses": 4800}  # Low savings rate
            },
            {
                "message": "I have debt and don't know what to prioritize",
                "context_override": {"accounts": [{"type": "credit_card", "balance": -15000, "interest_rate": 0.24}]}
            },
            {
                "message": "How should I invest my portfolio?",
                "context_override": {"risk_tolerance": "aggressive", "age": 28}
            },
            {
                "message": "I want to optimize my finances",
                "context_override": {}  # Use default context
            }
        ]
        
        results = {"total": len(test_scenarios), "passed": 0, "details": []}
        
        for i, scenario in enumerate(test_scenarios, 1):
            try:
                # Create test state with context override
                state = self._create_test_state(
                    scenario["message"], 
                    context_override=scenario["context_override"]
                )
                
                result = await self.recommendation_agent.process(state)
                
                success = result.get("success", False)
                recommendations = result.get("recommendations", [])
                analysis = result.get("analysis", {})
                
                if success and recommendations:
                    results["passed"] += 1
                    status = "✅"
                else:
                    status = "❌"
                
                results["details"].append({
                    "test": f"Recommendation Test {i}",
                    "scenario": scenario["message"][:30] + "...",
                    "success": success,
                    "recommendations_count": len(recommendations),
                    "categories": analysis.get("categories", [])
                })
                
                print(f"   {status} Test {i}: {len(recommendations)} recommendations, "
                      f"Categories: {', '.join(analysis.get('categories', []))}")
                
            except Exception as e:
                results["details"].append({
                    "test": f"Recommendation Test {i}",
                    "scenario": scenario["message"][:30] + "...",
                    "success": False,
                    "error": str(e)
                })
                print(f"   ❌ Test {i}: Exception - {e}")
        
        return results
    
    async def test_risk_assessment_agent(self):
        """Test Risk Assessment Agent"""
        
        test_scenarios = [
            {
                "message": "How risky is my financial situation?",
                "context_override": {"monthly_expenses": 4000}  # Good emergency fund
            },
            {
                "message": "Am I taking too much risk?",
                "context_override": {
                    "accounts": [{"type": "investment", "balance": 100000}],
                    "net_worth": 110000  # 90% in investments
                }
            },
            {
                "message": "What are my biggest financial risks?",
                "context_override": {
                    "accounts": [{"type": "checking", "balance": 1000}],  # Low emergency fund
                    "monthly_expenses": 5000
                }
            },
            {
                "message": "Should I be more conservative?",
                "context_override": {"age": 58, "risk_tolerance": "aggressive"}
            }
        ]
        
        results = {"total": len(test_scenarios), "passed": 0, "details": []}
        
        for i, scenario in enumerate(test_scenarios, 1):
            try:
                state = self._create_test_state(
                    scenario["message"],
                    context_override=scenario["context_override"]
                )
                
                result = await self.risk_agent.process(state)
                
                success = result.get("success", False)
                analysis = result.get("analysis", {})
                risk_score = analysis.get("overall_risk_score", 0)
                risk_profile = analysis.get("risk_profile", "")
                
                if success and risk_score > 0:
                    results["passed"] += 1
                    status = "✅"
                else:
                    status = "❌"
                
                results["details"].append({
                    "test": f"Risk Test {i}",
                    "scenario": scenario["message"][:30] + "...",
                    "success": success,
                    "risk_score": risk_score,
                    "risk_profile": risk_profile
                })
                
                print(f"   {status} Test {i}: Risk Score={risk_score}/100, Profile={risk_profile}")
                
            except Exception as e:
                results["details"].append({
                    "test": f"Risk Test {i}",
                    "scenario": scenario["message"][:30] + "...",
                    "success": False,
                    "error": str(e)
                })
                print(f"   ❌ Test {i}: Exception - {e}")
        
        return results
    
    async def test_advanced_orchestrator(self):
        """Test Advanced Orchestrator"""
        
        test_messages = [
            "What's my financial health and what should I do?",  # Comprehensive
            "I want to save for a house",  # Goal-focused
            "Should I invest in stocks?",  # Investment-focused
            "How can I reduce my financial risk?",  # Risk-focused
            "Help me optimize my finances"  # General advice
        ]
        
        results = {"total": len(test_messages), "passed": 0, "details": []}
        
        for i, message in enumerate(test_messages, 1):
            try:
                response = await self.advanced_orchestrator.process_message(
                    user_message=message,
                    user_id=self.test_user_context["user_id"],
                    session_id=f"test_session_{i}"
                )
                
                success = response.get("success", False)
                metadata = response.get("metadata", {})
                agents_used = metadata.get("agents_used", [])
                processing_time = metadata.get("processing_time", 0)
                
                if success and agents_used:
                    results["passed"] += 1
                    status = "✅"
                else:
                    status = "❌"
                
                results["details"].append({
                    "test": f"Orchestrator Test {i}",
                    "message": message[:40] + "...",
                    "success": success,
                    "agents_used": agents_used,
                    "processing_time": processing_time
                })
                
                print(f"   {status} Test {i}: {len(agents_used)} agents, "
                      f"{processing_time:.2f}s, Agents: {', '.join(agents_used)}")
                
            except Exception as e:
                results["details"].append({
                    "test": f"Orchestrator Test {i}",
                    "message": message[:40] + "...",
                    "success": False,
                    "error": str(e)
                })
                print(f"   ❌ Test {i}: Exception - {e}")
        
        return results
    
    async def test_memory_service(self):
        """Test Memory Service"""
        
        test_operations = [
            "store_conversation",
            "get_conversation_history", 
            "store_user_insight",
            "get_user_insights",
            "store_user_preference",
            "get_user_preferences",
            "track_goal_progress",
            "get_conversation_context"
        ]
        
        results = {"total": len(test_operations), "passed": 0, "details": []}
        user_id = self.test_user_context["user_id"]
        session_id = "test_memory_session"
        
        for i, operation in enumerate(test_operations, 1):
            try:
                success = False
                
                if operation == "store_conversation":
                    conv_id = await self.memory_service.store_conversation(
                        user_id, session_id, "Test message", "Test response", [], {}
                    )
                    success = bool(conv_id)
                
                elif operation == "get_conversation_history":
                    history = await self.memory_service.get_conversation_history(user_id)
                    success = isinstance(history, list)
                
                elif operation == "store_user_insight":
                    insight_id = await self.memory_service.store_user_insight(
                        user_id, "test_insight", {"test": "data"}
                    )
                    success = bool(insight_id)
                
                elif operation == "get_user_insights":
                    insights = await self.memory_service.get_user_insights(user_id)
                    success = isinstance(insights, list)
                
                elif operation == "store_user_preference":
                    await self.memory_service.store_user_preference(
                        user_id, "test_pref", "test_value"
                    )
                    success = True
                
                elif operation == "get_user_preferences":
                    prefs = await self.memory_service.get_user_preferences(user_id)
                    success = isinstance(prefs, dict)
                
                elif operation == "track_goal_progress":
                    progress_id = await self.memory_service.track_goal_progress(
                        user_id, "test_goal", {"progress": 50}
                    )
                    success = bool(progress_id)
                
                elif operation == "get_conversation_context":
                    context = await self.memory_service.get_conversation_context(
                        user_id, session_id
                    )
                    success = isinstance(context, dict)
                
                if success:
                    results["passed"] += 1
                    status = "✅"
                else:
                    status = "❌"
                
                results["details"].append({
                    "test": f"Memory Test {i}",
                    "operation": operation,
                    "success": success
                })
                
                print(f"   {status} Test {i}: {operation}")
                
            except Exception as e:
                results["details"].append({
                    "test": f"Memory Test {i}",
                    "operation": operation,
                    "success": False,
                    "error": str(e)
                })
                print(f"   ❌ Test {i}: {operation} - {e}")
        
        return results
    
    async def test_full_integration(self):
        """Test full integration of all Phase 3 components"""
        
        integration_scenarios = [
            {
                "conversation": [
                    "Hi, I'm looking for financial advice",
                    "I want to save for a house down payment of $60,000 in 4 years",
                    "What's the best investment strategy for my situation?",
                    "How risky is my current financial position?"
                ],
                "expected_agents": ["goal_extraction", "recommendation", "risk_assessment"],
                "expected_insights": ["user_goals", "risk_profile"]
            }
        ]
        
        results = {"total": len(integration_scenarios), "passed": 0, "details": []}
        
        for i, scenario in enumerate(integration_scenarios, 1):
            try:
                user_id = f"integration_test_user_{i}"
                session_id = f"integration_session_{i}"
                
                agents_encountered = set()
                insights_stored = []
                
                # Simulate conversation
                for msg_num, message in enumerate(scenario["conversation"]):
                    # Process message through orchestrator
                    response = await self.advanced_orchestrator.process_message(
                        user_message=message,
                        user_id=user_id,
                        session_id=session_id
                    )
                    
                    # Track agents used
                    metadata = response.get("metadata", {})
                    agents_used = metadata.get("agents_used", [])
                    agents_encountered.update(agents_used)
                    
                    # Store conversation in memory
                    if response.get("success"):
                        await self.memory_service.store_conversation(
                            user_id, session_id, message, 
                            response.get("response", ""), 
                            response.get("agent_results", []),
                            metadata
                        )
                
                # Check conversation context
                context = await self.memory_service.get_conversation_context(user_id, session_id)
                
                # Check insights
                user_insights = await self.memory_service.get_user_insights(user_id)
                
                # Evaluate success
                expected_agents = set(scenario["expected_agents"])
                agents_found = agents_encountered.intersection(expected_agents)
                agent_coverage = len(agents_found) / len(expected_agents) if expected_agents else 1
                
                conversation_stored = len(context.get("recent_messages", [])) > 0
                insights_generated = len(user_insights) > 0
                
                overall_success = (
                    agent_coverage >= 0.5 and  # At least 50% of expected agents
                    conversation_stored and 
                    insights_generated
                )
                
                if overall_success:
                    results["passed"] += 1
                    status = "✅"
                else:
                    status = "❌"
                
                results["details"].append({
                    "test": f"Integration Test {i}",
                    "success": overall_success,
                    "agent_coverage": f"{agent_coverage:.1%}",
                    "agents_used": list(agents_encountered),
                    "conversation_messages": len(context.get("recent_messages", [])),
                    "insights_generated": len(user_insights)
                })
                
                print(f"   {status} Test {i}: Agent coverage={agent_coverage:.1%}, "
                      f"Messages stored={len(context.get('recent_messages', []))}, "
                      f"Insights={len(user_insights)}")
                
            except Exception as e:
                results["details"].append({
                    "test": f"Integration Test {i}",
                    "success": False,
                    "error": str(e)
                })
                print(f"   ❌ Test {i}: Exception - {e}")
        
        return results
    
    def _create_test_state(self, message: str, context_override: dict = None) -> dict:
        """Create test conversation state"""
        
        context = self.test_user_context.copy()
        if context_override:
            context.update(context_override)
        
        return {
            "user_message": message,
            "user_id": context["user_id"],
            "session_id": "test_session",
            "user_context": context,
            "agent_results": [],
            "metadata": {}
        }
    
    def print_test_summary(self, test_results: dict):
        """Print comprehensive test summary"""
        
        print("📊 PHASE 3 TEST SUMMARY")
        print("=" * 40)
        
        total_tests = 0
        total_passed = 0
        
        for component, results in test_results.items():
            passed = results["passed"]
            total = results["total"]
            success_rate = (passed / total) * 100 if total > 0 else 0
            
            status = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 60 else "❌"
            
            print(f"{status} {component.replace('_', ' ').title()}: {passed}/{total} ({success_rate:.1f}%)")
            
            total_tests += total
            total_passed += passed
        
        overall_success_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
        overall_status = "✅" if overall_success_rate >= 80 else "⚠️" if overall_success_rate >= 60 else "❌"
        
        print("-" * 40)
        print(f"{overall_status} OVERALL: {total_passed}/{total_tests} ({overall_success_rate:.1f}%)")
        
        # Detailed results
        print(f"\n📋 DETAILED RESULTS:")
        for component, results in test_results.items():
            print(f"\n{component.replace('_', ' ').title()}:")
            for detail in results["details"]:
                test_name = detail["test"]
                success = detail["success"]
                status_icon = "✅" if success else "❌"
                print(f"  {status_icon} {test_name}")
                
                if "error" in detail:
                    print(f"      Error: {detail['error']}")
        
        print(f"\n🎉 Phase 3 Advanced Agents Testing Complete!")
        
        if overall_success_rate >= 80:
            print("✅ All systems ready for Wealthify integration!")
        elif overall_success_rate >= 60:
            print("⚠️ Most systems working - review failed tests before integration")
        else:
            print("❌ Significant issues detected - address before integration")


async def main():
    """Run Phase 3 test suite"""
    
    test_suite = Phase3TestSuite()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())