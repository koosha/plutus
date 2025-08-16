"""
Question Analyzer and Test Suite for Plutus
============================================

This module provides tools to analyze, categorize, and test
the sample questions for the Plutus multiagent system.
"""

import json
import random
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict
from pathlib import Path

class QuestionAnalyzer:
    """Analyzes the distribution and characteristics of test questions"""
    
    def __init__(self, questions_file: str = "data/sample_questions.json"):
        """Load questions from JSON file"""
        self.questions_file = Path(questions_file)
        self.data = self.load_questions()
        self.questions = self.data["questions"]
    
    def load_questions(self) -> dict:
        """Load questions from JSON file"""
        with open(self.questions_file, 'r') as f:
            return json.load(f)
    
    def analyze_complexity_distribution(self) -> Dict[str, int]:
        """Analyze distribution of question complexity"""
        complexity_counts = Counter()
        for q in self.questions:
            complexity_counts[q["complexity"]] += 1
        return dict(complexity_counts)
    
    def analyze_category_distribution(self) -> Dict[str, int]:
        """Analyze distribution of categories"""
        category_counts = Counter()
        for q in self.questions:
            for category in q["category"]:
                category_counts[category] += 1
        return dict(category_counts.most_common())
    
    def analyze_agent_requirements(self) -> Dict[str, int]:
        """Analyze which agents are most commonly needed"""
        agent_counts = Counter()
        for q in self.questions:
            if "expected_agents" in q:
                for agent in q["expected_agents"]:
                    agent_counts[agent] += 1
        return dict(agent_counts.most_common())
    
    def get_questions_by_complexity(self, complexity: str) -> List[Dict]:
        """Get all questions of a specific complexity level"""
        return [q for q in self.questions if q["complexity"] == complexity]
    
    def get_questions_by_category(self, category: str) -> List[Dict]:
        """Get all questions in a specific category"""
        return [q for q in self.questions if category in q["category"]]
    
    def get_random_questions(self, n: int = 10, complexity: Optional[str] = None) -> List[Dict]:
        """Get random questions for testing"""
        pool = self.questions
        if complexity:
            pool = self.get_questions_by_complexity(complexity)
        
        n = min(n, len(pool))
        return random.sample(pool, n)
    
    def print_analysis_report(self):
        """Print a comprehensive analysis report"""
        print("="*70)
        print("📊 PLUTUS TEST QUESTIONS ANALYSIS REPORT")
        print("="*70)
        
        # Total questions
        print(f"\n📋 Total Questions: {len(self.questions)}")
        
        # Complexity distribution
        print("\n🎯 Complexity Distribution:")
        complexity = self.analyze_complexity_distribution()
        for level, count in complexity.items():
            percentage = (count / len(self.questions)) * 100
            print(f"  {level:12} : {count:3} questions ({percentage:.1f}%)")
        
        # Category distribution
        print("\n📁 Top Categories:")
        categories = self.analyze_category_distribution()
        for i, (cat, count) in enumerate(list(categories.items())[:10], 1):
            print(f"  {i:2}. {cat:20} : {count:3} questions")
        
        # Agent requirements
        print("\n🤖 Most Required Agents:")
        agents = self.analyze_agent_requirements()
        for i, (agent, count) in enumerate(list(agents.items())[:10], 1):
            print(f"  {i:2}. {agent:25} : {count:3} times")
        
        # Complexity by category
        print("\n📊 Complexity by Category:")
        complexity_by_category = self.analyze_complexity_by_category()
        for cat, dist in list(complexity_by_category.items())[:5]:
            print(f"\n  {cat}:")
            for level, count in dist.items():
                print(f"    {level}: {count}")
        
        print("\n" + "="*70)
    
    def analyze_complexity_by_category(self) -> Dict[str, Dict[str, int]]:
        """Analyze complexity distribution within each category"""
        result = defaultdict(lambda: defaultdict(int))
        
        for q in self.questions:
            complexity = q["complexity"]
            for category in q["category"]:
                result[category][complexity] += 1
        
        # Sort by total questions in category
        sorted_result = dict(sorted(
            result.items(), 
            key=lambda x: sum(x[1].values()), 
            reverse=True
        ))
        
        return sorted_result
    
    def generate_test_batch(self, 
                           simple: int = 3, 
                           intermediate: int = 4, 
                           complex: int = 3) -> List[Dict]:
        """Generate a balanced test batch"""
        batch = []
        batch.extend(self.get_random_questions(simple, "simple"))
        batch.extend(self.get_random_questions(intermediate, "intermediate"))
        batch.extend(self.get_random_questions(complex, "complex"))
        random.shuffle(batch)
        return batch
    
    def export_test_scenarios(self, output_file: str = "test_scenarios.json"):
        """Export structured test scenarios for automated testing"""
        scenarios = {
            "quick_test": self.generate_test_batch(2, 2, 1),
            "standard_test": self.generate_test_batch(3, 4, 3),
            "comprehensive_test": self.generate_test_batch(5, 8, 5),
            "simple_only": self.get_random_questions(10, "simple"),
            "complex_only": self.get_random_questions(5, "complex"),
            "retirement_focused": self.get_random_questions_from_category("retirement", 5),
            "investment_focused": self.get_random_questions_from_category("investment", 5),
            "debt_focused": self.get_random_questions_from_category("debt_management", 5)
        }
        
        with open(output_file, 'w') as f:
            json.dump(scenarios, f, indent=2)
        
        print(f"✅ Test scenarios exported to {output_file}")
        return scenarios
    
    def get_random_questions_from_category(self, category: str, n: int) -> List[Dict]:
        """Get random questions from a specific category"""
        category_questions = self.get_questions_by_category(category)
        n = min(n, len(category_questions))
        return random.sample(category_questions, n)

class QuestionRouter:
    """
    Simulates the routing logic for questions based on complexity
    This helps understand which agents would be involved
    """
    
    def __init__(self):
        self.routing_rules = {
            "simple": ["basic_analyzer", "recommendation"],
            "intermediate": ["financial_analyzer", "detailed_analyzer", "recommendation"],
            "complex": ["financial_analyzer", "detailed_analyzer", "risk_assessor", 
                       "tax_planner", "recommendation"]
        }
    
    def route_question(self, question: Dict) -> List[str]:
        """Determine which agents should handle a question"""
        complexity = question["complexity"]
        base_agents = self.routing_rules[complexity]
        
        # Add category-specific agents
        categories = question["category"]
        
        specialized_agents = []
        if "retirement" in categories:
            specialized_agents.append("retirement_calculator")
        if "tax_planning" in categories:
            specialized_agents.append("tax_optimizer")
        if "investment" in categories:
            specialized_agents.append("portfolio_analyzer")
        if "debt_management" in categories:
            specialized_agents.append("debt_analyzer")
        if "home_purchase" in categories:
            specialized_agents.append("mortgage_calculator")
        if "estate_planning" in categories:
            specialized_agents.append("estate_planner")
        
        # Combine and deduplicate
        all_agents = list(dict.fromkeys(specialized_agents + base_agents))
        return all_agents
    
    def estimate_processing_time(self, question: Dict) -> float:
        """Estimate processing time based on complexity and agents"""
        base_times = {
            "simple": 1.5,
            "intermediate": 2.5,
            "complex": 4.0
        }
        
        agents = self.route_question(question)
        
        # Add time for each specialized agent
        specialized_time = len(agents) * 0.3
        
        return base_times[question["complexity"]] + specialized_time

def main():
    """Run analysis and generate test scenarios"""
    print("🚀 Initializing Question Analyzer...")
    
    # Initialize analyzer
    analyzer = QuestionAnalyzer()
    
    # Print analysis report
    analyzer.print_analysis_report()
    
    # Generate test scenarios
    print("\n📝 Generating Test Scenarios...")
    scenarios = analyzer.export_test_scenarios()
    
    # Test routing logic
    print("\n🧭 Testing Routing Logic...")
    router = QuestionRouter()
    
    # Get sample questions of each complexity
    for complexity in ["simple", "intermediate", "complex"]:
        questions = analyzer.get_random_questions(2, complexity)
        print(f"\n{complexity.upper()} Questions:")
        for q in questions:
            agents = router.route_question(q)
            time_est = router.estimate_processing_time(q)
            print(f"  Q{q['id']}: {q['question'][:50]}...")
            print(f"    Agents: {', '.join(agents)}")
            print(f"    Est. Time: {time_est:.1f}s")
    
    # Create a sample test suite
    print("\n📋 Sample Test Suite (10 questions):")
    test_batch = analyzer.generate_test_batch(3, 4, 3)
    for i, q in enumerate(test_batch, 1):
        print(f"  {i}. [{q['complexity']:12}] {q['question'][:60]}...")
    
    print("\n✅ Analysis complete! Ready for testing.")

if __name__ == "__main__":
    main()

"""
🎓 HOW TO USE THIS FOR TESTING:

1. Run analysis to understand question distribution:
   python question_analyzer.py

2. Generate test scenarios for different testing needs:
   - quick_test: 5 questions for rapid testing
   - standard_test: 10 questions for normal testing  
   - comprehensive_test: 18 questions for thorough testing

3. Use the router to understand agent involvement:
   - Shows which agents would handle each question
   - Estimates processing time
   - Helps identify bottlenecks

4. Create custom test batches for specific scenarios:
   - Category-focused testing
   - Complexity-focused testing
   - Edge case testing

This provides a solid foundation for testing Plutus with realistic questions!
"""