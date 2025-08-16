#!/usr/bin/env python3
"""
Plutus Demo Script
==================

Demonstrates the Plutus AI system with sample users and questions
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add src to path so we can import plutus
sys.path.insert(0, str(Path(__file__).parent / "src"))

from plutus.agents.orchestrator import PlutusOrchestrator
from plutus.services.data_service import get_data_service
from plutus.testing.plutus_test import PlutusTestFramework
from plutus.core.config import get_config

async def demo_single_conversation():
    """Demo a single conversation with Plutus"""
    
    print("🎯 PLUTUS SINGLE CONVERSATION DEMO")
    print("=" * 50)
    
    # Initialize Plutus
    orchestrator = PlutusOrchestrator()
    data_service = get_data_service()
    
    # Get a sample user
    users = await data_service.get_all_users()
    if not users:
        print("❌ No sample users found")
        return
    
    user = users[0]  # Use first user (Sarah Chen)
    user_id = user["user_id"]
    user_name = user["name"]
    
    print(f"\n👤 Demo User: {user_name}")
    print(f"   Age: {user['age']}")
    print(f"   Wealth Score: {user['wealth_health']['overall_score']}/100")
    print(f"   Net Worth: ${user['monthly_income'] * 12 - user['monthly_expenses'] * 12:,.0f} (estimated)")
    
    # Demo questions
    demo_questions = [
        "What's my current financial health?",
        "Should I pay off my credit card debt or invest in the stock market?",
        "How much should I save for retirement?"
    ]
    
    for i, question in enumerate(demo_questions, 1):
        print(f"\n🔸 Question {i}: {question}")
        
        try:
            # Process the question
            response = await orchestrator.process_message(
                user_message=question,
                user_id=user_id
            )
            
            if response["success"]:
                print(f"✅ Response ({response['metadata']['processing_time']:.2f}s):")
                print(f"   Intent: {response['metadata']['intent']}")
                print(f"   Complexity: {response['metadata']['complexity']}")
                print(f"   Agents: {', '.join(response['metadata']['agents_used'])}")
                print(f"   Confidence: {response['metadata']['confidence']:.1%}")
                print(f"\n💬 Plutus: {response['response']}")
            else:
                print(f"❌ Error: {response.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
        
        print("-" * 40)

async def demo_multi_user_test():
    """Demo testing with multiple users"""
    
    print("\n🎯 PLUTUS MULTI-USER DEMO")
    print("=" * 50)
    
    # Initialize test framework
    test_framework = PlutusTestFramework()
    data_service = get_data_service()
    
    # Get all users
    users = await data_service.get_all_users()
    
    print(f"\n📊 Testing {len(users)} users with sample questions:")
    
    for user in users:
        user_id = user["user_id"]
        user_name = user["name"]
        wealth_score = user["wealth_health"]["overall_score"]
        
        print(f"\n👤 {user_name} (Wealth Score: {wealth_score}/100)")
        
        # Test with 2 questions
        questions = await data_service.get_random_questions(2)
        
        for question_data in questions:
            question = question_data["question"]
            complexity = question_data["complexity"]
            
            print(f"   🔸 [{complexity}] {question[:60]}...")
            
            try:
                response = await test_framework.orchestrator.process_message(
                    user_message=question,
                    user_id=user_id
                )
                
                if response["success"]:
                    metadata = response["metadata"]
                    print(f"      ✅ {metadata['processing_time']:.2f}s | "
                          f"{metadata['complexity']} | "
                          f"{len(metadata['agents_used'])} agents | "
                          f"{metadata['confidence']:.0%} confidence")
                else:
                    print(f"      ❌ Failed: {response.get('error', 'Unknown')}")
                    
            except Exception as e:
                print(f"      ❌ Exception: {str(e)}")

async def demo_comprehensive_test():
    """Demo comprehensive testing"""
    
    print("\n🎯 PLUTUS COMPREHENSIVE TEST DEMO")
    print("=" * 50)
    
    # Run comprehensive test
    test_framework = PlutusTestFramework()
    
    print("\n🚀 Running comprehensive test suite...")
    print("   This will test all users with questions of different complexities")
    
    try:
        results = await test_framework.run_comprehensive_test()
        
        print("\n📈 TEST RESULTS SUMMARY:")
        print("=" * 30)
        
        summary = results.get("summary", {})
        print(f"Total Tests: {summary.get('total_tests', 0)}")
        print(f"Success Rate: {summary.get('success_rate', 0):.1%}")
        print(f"Avg Response Time: {summary.get('avg_response_time', 0):.2f}s")
        print(f"Avg Quality Score: {summary.get('avg_quality_score', 0):.1%}")
        
        # Complexity breakdown
        complexity_analysis = results.get("complexity_analysis", {})
        if complexity_analysis:
            print(f"\n📊 COMPLEXITY BREAKDOWN:")
            for complexity, stats in complexity_analysis.items():
                print(f"  {complexity:12}: {stats['success_rate']:.1%} success | {stats['avg_time']:.2f}s avg")
        
        # Agent usage
        agent_usage = results.get("agent_usage", {})
        if agent_usage:
            print(f"\n🤖 AGENT USAGE:")
            for agent, count in list(agent_usage.items())[:5]:
                print(f"  {agent:25}: {count} times")
        
        print(f"\n✅ Comprehensive test completed successfully!")
        
    except Exception as e:
        print(f"❌ Comprehensive test failed: {str(e)}")

async def demo_configuration():
    """Demo configuration and setup"""
    
    print("\n🎯 PLUTUS CONFIGURATION DEMO")
    print("=" * 50)
    
    config = get_config()
    data_service = get_data_service()
    
    print(f"\n⚙️  Configuration:")
    print(f"   Model: {config.claude_model}")
    print(f"   Max Tokens: {config.max_tokens}")
    print(f"   Temperature: {config.temperature}")
    print(f"   API Key: {'✅ Configured' if config.anthropic_api_key else '❌ Missing (simulation mode)'}")
    print(f"   Daily Cost Limit: ${config.daily_cost_limit}")
    
    # Load sample data
    users_data = await data_service.load_sample_users()
    questions_data = await data_service.load_sample_questions()
    
    users = users_data.get("users", [])
    questions = questions_data.get("questions", [])
    
    print(f"\n📊 Sample Data:")
    print(f"   Users: {len(users)}")
    print(f"   Questions: {len(questions)}")
    
    # User breakdown
    if users:
        print(f"\n👥 User Profiles:")
        for user in users:
            wealth_score = user["wealth_health"]["overall_score"]
            print(f"   {user['name']:20}: Age {user['age']:2} | Wealth Score {wealth_score:2}/100")
    
    # Question breakdown
    if questions:
        complexities = {}
        for q in questions:
            complexity = q.get("complexity", "unknown")
            complexities[complexity] = complexities.get(complexity, 0) + 1
        
        print(f"\n❓ Question Complexity:")
        for complexity, count in complexities.items():
            percentage = (count / len(questions)) * 100
            print(f"   {complexity:12}: {count:3} questions ({percentage:.1f}%)")

async def interactive_demo():
    """Interactive demo where user can ask questions"""
    
    print("\n🎯 PLUTUS INTERACTIVE DEMO")
    print("=" * 50)
    
    orchestrator = PlutusOrchestrator()
    data_service = get_data_service()
    
    # Get users
    users = await data_service.get_all_users()
    if not users:
        print("❌ No sample users found")
        return
    
    print(f"\n👥 Available Users:")
    for i, user in enumerate(users):
        wealth_score = user["wealth_health"]["overall_score"]
        print(f"   {i+1}. {user['name']} (Age {user['age']}, Wealth Score: {wealth_score}/100)")
    
    print(f"\nSelect a user (1-{len(users)}) or press Enter for user 1:")
    try:
        user_choice = input().strip()
        if user_choice:
            user_index = int(user_choice) - 1
        else:
            user_index = 0
        
        if user_index < 0 or user_index >= len(users):
            user_index = 0
            
    except (ValueError, KeyboardInterrupt):
        user_index = 0
    
    selected_user = users[user_index]
    user_id = selected_user["user_id"]
    user_name = selected_user["name"]
    
    print(f"\n👤 Selected: {user_name}")
    print(f"💬 You can now ask financial questions. Type 'quit' to exit.")
    print("-" * 50)
    
    while True:
        try:
            question = input(f"\n💬 Ask {user_name}: ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                break
                
            if not question:
                continue
            
            print(f"🧠 Plutus is thinking...")
            
            # Process the question
            response = await orchestrator.process_message(
                user_message=question,
                user_id=user_id
            )
            
            if response["success"]:
                metadata = response["metadata"]
                print(f"\n🎯 Analysis:")
                print(f"   Intent: {metadata['intent']}")
                print(f"   Complexity: {metadata['complexity']}")
                print(f"   Processing Time: {metadata['processing_time']:.2f}s")
                print(f"   Confidence: {metadata['confidence']:.1%}")
                print(f"   Agents Used: {', '.join(metadata['agents_used'])}")
                
                print(f"\n💡 Plutus Response:")
                print(f"   {response['response']}")
            else:
                print(f"❌ Error: {response.get('error', 'Unknown error')}")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print(f"\n👋 Thanks for testing Plutus!")

async def main():
    """Main demo function"""
    
    print("🤖 WELCOME TO PLUTUS AI DEMO")
    print("=" * 60)
    print("Plutus is an AI-powered wealth management brain for Wealthify")
    print("This demo showcases the multi-agent conversation system")
    print("=" * 60)
    
    demos = [
        ("1", "Single Conversation Demo", demo_single_conversation),
        ("2", "Multi-User Test Demo", demo_multi_user_test),
        ("3", "Comprehensive Test Suite", demo_comprehensive_test),
        ("4", "Configuration Overview", demo_configuration),
        ("5", "Interactive Demo", interactive_demo),
    ]
    
    print(f"\n📋 Available Demos:")
    for key, title, _ in demos:
        print(f"   {key}. {title}")
    
    print(f"\nSelect demo (1-{len(demos)}) or press Enter for all:")
    
    try:
        choice = input().strip()
        
        if not choice:
            # Run all demos
            for key, title, demo_func in demos:
                print(f"\n" + "="*60)
                print(f"Running: {title}")
                print("="*60)
                await demo_func()
        else:
            # Run specific demo
            demo_found = False
            for key, title, demo_func in demos:
                if choice == key:
                    await demo_func()
                    demo_found = True
                    break
            
            if not demo_found:
                print(f"Invalid choice: {choice}")
                
    except KeyboardInterrupt:
        print(f"\n👋 Demo cancelled by user")
    except Exception as e:
        print(f"❌ Demo error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())