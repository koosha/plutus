#!/usr/bin/env python3
"""
Production Readiness Test
=========================

Tests that Plutus is ready for Wealthify integration.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_production_readiness():
    """Test production readiness."""
    
    print("🚀 PLUTUS PRODUCTION READINESS TEST")
    print("="*50)
    
    results = {"passed": 0, "total": 0}
    
    # Test 1: Configuration loading
    results["total"] += 1
    try:
        from plutus.core.config import get_config
        config = get_config()
        print("✅ Configuration loading: OK")
        print(f"   Integration mode: {config.integration_mode}")
        print(f"   API key available: {'Yes' if config.anthropic_api_key else 'No'}")
        results["passed"] += 1
    except Exception as e:
        print(f"❌ Configuration loading: FAILED - {e}")
    
    # Test 2: Core agents import
    results["total"] += 1
    try:
        from plutus.agents.advanced_orchestrator import AdvancedOrchestrator
        from plutus.agents.financial_analysis_agent import FinancialAnalysisAgent
        from plutus.agents.goal_extraction_agent import GoalExtractionAgent
        from plutus.agents.recommendation_agent import RecommendationAgent
        from plutus.agents.risk_assessment_agent import RiskAssessmentAgent
        print("✅ Agent imports: OK")
        results["passed"] += 1
    except Exception as e:
        print(f"❌ Agent imports: FAILED - {e}")
    
    # Test 3: Memory service
    results["total"] += 1
    try:
        from plutus.services.memory_service import MemoryService
        memory = MemoryService(db_path=":memory:")
        print("✅ Memory service: OK")
        results["passed"] += 1
    except Exception as e:
        print(f"❌ Memory service: FAILED - {e}")
    
    # Test 4: Orchestrator initialization
    results["total"] += 1
    try:
        orchestrator = AdvancedOrchestrator()
        print("✅ Orchestrator initialization: OK")
        print(f"   Claude client: {'Available' if orchestrator.claude_client else 'Simulation mode'}")
        results["passed"] += 1
    except Exception as e:
        print(f"❌ Orchestrator initialization: FAILED - {e}")
    
    # Test 5: Minimal workflow test
    results["total"] += 1
    try:
        test_state = {
            "user_message": "What's my financial health?",
            "user_id": "test_user",
            "user_context": {
                "monthly_income": 5000,
                "monthly_expenses": 3000,
                "net_worth": 50000,
                "accounts": [{"type": "checking", "balance": 10000}]
            }
        }
        
        # This will run in simulation mode if no credits
        import asyncio
        async def test_workflow():
            result = await orchestrator.process(test_state)
            return result.get("success", False)
        
        success = asyncio.run(test_workflow())
        if success:
            print("✅ Workflow processing: OK")
            results["passed"] += 1
        else:
            print("❌ Workflow processing: FAILED - No response generated")
    except Exception as e:
        print(f"❌ Workflow processing: FAILED - {e}")
    
    # Test 6: Dependencies check
    results["total"] += 1
    try:
        import anthropic
        import httpx
        import tenacity
        print("✅ Required dependencies: OK")
        print(f"   Anthropic version: {anthropic.__version__}")
        results["passed"] += 1
    except ImportError as e:
        print(f"❌ Required dependencies: FAILED - {e}")
    
    # Summary
    print("\n" + "="*50)
    success_rate = (results["passed"] / results["total"]) * 100
    print(f"📊 PRODUCTION READINESS: {results['passed']}/{results['total']} ({success_rate:.1f}%)")
    
    if success_rate >= 100:
        print("🎉 FULLY READY for Wealthify integration!")
        return True
    elif success_rate >= 80:
        print("⚠️ MOSTLY READY - minor issues to address")
        return True
    else:
        print("❌ NOT READY - significant issues need fixing")
        return False

if __name__ == "__main__":
    ready = test_production_readiness()
    
    if ready:
        print("\n🚀 Integration Steps:")
        print("1. Copy src/plutus to wealthify/app/services/plutus")
        print("2. Add Plutus dependencies to Wealthify's requirements.txt")
        print("3. Add ANTHROPIC_API_KEY to Wealthify's environment")
        print("4. Include Plutus router in Wealthify's API")
        print("5. Deploy and test!")
    else:
        print("\n🔧 Fix the issues above before integration.")