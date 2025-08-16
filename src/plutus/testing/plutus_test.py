"""
Plutus Testing Framework
========================

Tests the Plutus system with sample users and questions
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
import logging

from ..agents.orchestrator import PlutusOrchestrator
from ..services.data_service import get_data_service
from ..core.config import get_config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlutusTestFramework:
    """
    Test framework for validating Plutus functionality
    """
    
    def __init__(self):
        self.orchestrator = PlutusOrchestrator()
        self.data_service = get_data_service()
        self.config = get_config()
        
        self.test_results = []
        self.performance_metrics = {}
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """
        Run comprehensive test suite
        """
        
        logger.info("🚀 Starting Plutus Comprehensive Test")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        # Load test data
        users = await self.data_service.get_all_users()
        questions_data = await self.data_service.load_sample_questions()
        questions = questions_data.get("questions", [])
        
        logger.info(f"📊 Loaded {len(users)} users and {len(questions)} questions")
        
        # Test each user with a sample of questions
        test_results = []
        
        for user in users:
            user_id = user["user_id"]
            user_name = user["name"]
            
            logger.info(f"\n👤 Testing user: {user_name} (ID: {user_id})")
            logger.info(f"   Wealth Score: {user.get('wealth_health', {}).get('overall_score', 'N/A')}")
            
            # Test with different complexity questions
            user_results = await self._test_user_with_questions(user_id, questions)
            test_results.extend(user_results)
        
        total_time = time.time() - start_time
        
        # Analyze results
        analysis = self._analyze_test_results(test_results, total_time)
        
        logger.info(f"\n✅ Test completed in {total_time:.2f} seconds")
        logger.info(f"📈 Success rate: {analysis['success_rate']:.1%}")
        logger.info(f"⚡ Average response time: {analysis['avg_response_time']:.2f}s")
        
        return analysis
    
    async def _test_user_with_questions(self, user_id: str, questions: List[Dict]) -> List[Dict]:
        """Test a specific user with sample questions"""
        
        results = []
        
        # Test with different complexity levels
        complexities = ["simple", "intermediate", "complex"]
        
        for complexity in complexities:
            # Get questions of this complexity
            complexity_questions = [q for q in questions if q.get("complexity") == complexity]
            
            if complexity_questions:
                # Test with 2 questions per complexity level
                test_questions = complexity_questions[:2]
                
                for question_data in test_questions:
                    question = question_data["question"]
                    
                    logger.info(f"   🔸 Testing {complexity} question: {question[:50]}...")
                    
                    result = await self._test_single_question(user_id, question, question_data)
                    results.append(result)
        
        return results
    
    async def _test_single_question(self, 
                                  user_id: str, 
                                  question: str, 
                                  question_data: Dict) -> Dict:
        """Test a single question"""
        
        start_time = time.time()
        
        try:
            # Process the question
            response = await self.orchestrator.process_message(
                user_message=question,
                user_id=user_id
            )
            
            processing_time = time.time() - start_time
            
            # Evaluate response quality
            quality_score = self._evaluate_response_quality(response, question_data)
            
            return {
                "user_id": user_id,
                "question": question,
                "expected_complexity": question_data.get("complexity"),
                "actual_complexity": response.get("metadata", {}).get("complexity"),
                "success": response.get("success", False),
                "processing_time": processing_time,
                "response_length": len(response.get("response", "")),
                "quality_score": quality_score,
                "agents_used": response.get("metadata", {}).get("agents_used", []),
                "confidence": response.get("metadata", {}).get("confidence", 0.0),
                "response": response.get("response", "")
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            return {
                "user_id": user_id,
                "question": question,
                "expected_complexity": question_data.get("complexity"),
                "success": False,
                "processing_time": processing_time,
                "error": str(e),
                "quality_score": 0.0
            }
    
    def _evaluate_response_quality(self, response: Dict, question_data: Dict) -> float:
        """
        Evaluate response quality (0.0 to 1.0)
        """
        
        score = 0.0
        
        # Basic success check
        if response.get("success", False):
            score += 0.3
        
        # Response length check (should have substantial content)
        response_text = response.get("response", "")
        if len(response_text) > 100:
            score += 0.2
        elif len(response_text) > 50:
            score += 0.1
        
        # Complexity matching
        expected_complexity = question_data.get("complexity", "")
        actual_complexity = response.get("metadata", {}).get("complexity", "")
        if expected_complexity == actual_complexity:
            score += 0.2
        
        # Agent appropriateness
        agents_used = response.get("metadata", {}).get("agents_used", [])
        if agents_used:
            score += 0.1
        
        # Confidence check
        confidence = response.get("metadata", {}).get("confidence", 0.0)
        if confidence > 0.7:
            score += 0.2
        elif confidence > 0.5:
            score += 0.1
        
        return min(1.0, score)
    
    def _analyze_test_results(self, results: List[Dict], total_time: float) -> Dict[str, Any]:
        """Analyze test results and generate summary"""
        
        if not results:
            return {"error": "No test results to analyze"}
        
        # Basic metrics
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.get("success", False))
        success_rate = successful_tests / total_tests
        
        # Performance metrics
        processing_times = [r.get("processing_time", 0) for r in results if r.get("processing_time")]
        avg_response_time = sum(processing_times) / len(processing_times) if processing_times else 0
        max_response_time = max(processing_times) if processing_times else 0
        min_response_time = min(processing_times) if processing_times else 0
        
        # Quality metrics
        quality_scores = [r.get("quality_score", 0) for r in results]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Complexity analysis
        complexity_results = {}
        for complexity in ["simple", "intermediate", "complex"]:
            complexity_tests = [r for r in results if r.get("expected_complexity") == complexity]
            if complexity_tests:
                complexity_success = sum(1 for r in complexity_tests if r.get("success", False))
                complexity_results[complexity] = {
                    "total": len(complexity_tests),
                    "successful": complexity_success,
                    "success_rate": complexity_success / len(complexity_tests),
                    "avg_time": sum(r.get("processing_time", 0) for r in complexity_tests) / len(complexity_tests)
                }
        
        # Agent usage analysis
        all_agents = []
        for result in results:
            agents = result.get("agents_used", [])
            all_agents.extend(agents)
        
        from collections import Counter
        agent_usage = Counter(all_agents)
        
        # User performance analysis
        user_performance = {}
        for result in results:
            user_id = result.get("user_id", "unknown")
            if user_id not in user_performance:
                user_performance[user_id] = {"total": 0, "successful": 0, "avg_quality": 0}
            
            user_performance[user_id]["total"] += 1
            if result.get("success", False):
                user_performance[user_id]["successful"] += 1
            user_performance[user_id]["avg_quality"] += result.get("quality_score", 0)
        
        # Calculate averages for user performance
        for user_id, perf in user_performance.items():
            perf["success_rate"] = perf["successful"] / perf["total"]
            perf["avg_quality"] = perf["avg_quality"] / perf["total"]
        
        return {
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": success_rate,
                "total_time": total_time,
                "avg_response_time": avg_response_time,
                "max_response_time": max_response_time,
                "min_response_time": min_response_time,
                "avg_quality_score": avg_quality
            },
            "complexity_analysis": complexity_results,
            "agent_usage": dict(agent_usage.most_common()),
            "user_performance": user_performance,
            "detailed_results": results[:10]  # First 10 for detailed review
        }
    
    async def test_specific_user(self, user_id: str, questions_count: int = 5) -> Dict[str, Any]:
        """Test a specific user with random questions"""
        
        logger.info(f"🧪 Testing specific user: {user_id}")
        
        # Get random questions
        questions = await self.data_service.get_random_questions(questions_count)
        
        results = []
        for question_data in questions:
            question = question_data["question"]
            result = await self._test_single_question(user_id, question, question_data)
            results.append(result)
        
        # Analyze results
        analysis = self._analyze_test_results(results, sum(r.get("processing_time", 0) for r in results))
        
        return analysis
    
    async def test_question_categories(self, category: str, users_count: int = 3) -> Dict[str, Any]:
        """Test specific question category across multiple users"""
        
        logger.info(f"🧪 Testing category: {category}")
        
        # Get questions from category
        questions = await self.data_service.get_questions_by_category(category)
        if not questions:
            return {"error": f"No questions found for category: {category}"}
        
        # Get sample users
        users = await self.data_service.get_all_users()
        test_users = users[:users_count]
        
        results = []
        for user in test_users:
            user_id = user["user_id"]
            
            # Test with first 3 questions from category
            for question_data in questions[:3]:
                question = question_data["question"]
                result = await self._test_single_question(user_id, question, question_data)
                results.append(result)
        
        # Analyze results
        analysis = self._analyze_test_results(results, sum(r.get("processing_time", 0) for r in results))
        analysis["category_tested"] = category
        
        return analysis

# Convenience function for easy testing
async def run_plutus_test():
    """Run basic Plutus test"""
    
    test_framework = PlutusTestFramework()
    return await test_framework.run_comprehensive_test()

async def quick_test():
    """Quick test with one user and a few questions"""
    
    logger.info("🚀 Running Plutus Quick Test")
    
    test_framework = PlutusTestFramework()
    
    # Test first user with 3 questions
    users = await test_framework.data_service.get_all_users()
    if users:
        user_id = users[0]["user_id"]
        return await test_framework.test_specific_user(user_id, 3)
    else:
        return {"error": "No users found for testing"}