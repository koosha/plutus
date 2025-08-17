#!/usr/bin/env python3
"""
Import Validation Script
========================

Validates that all imports work correctly after refactoring.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test all critical imports."""
    
    errors = []
    
    try:
        print("Testing core imports...")
        from plutus.core.config import get_config
        print("✅ Core config import successful")
    except Exception as e:
        errors.append(f"❌ Core config import failed: {e}")
    
    try:
        print("Testing models imports...")
        from plutus.models.state import ConversationState
        print("✅ Models import successful")
    except Exception as e:
        errors.append(f"❌ Models import failed: {e}")
    
    try:
        print("Testing base agent import...")
        from plutus.agents.base_agent import BaseAgent
        print("✅ Base agent import successful")
    except Exception as e:
        errors.append(f"❌ Base agent import failed: {e}")
    
    try:
        print("Testing mixins import...")
        from plutus.agents.mixins import FinancialCalculationMixin
        print("✅ Mixins import successful")
    except Exception as e:
        errors.append(f"❌ Mixins import failed: {e}")
    
    try:
        print("Testing financial analysis agent...")
        from plutus.agents.financial_analysis_agent import FinancialAnalysisAgent
        agent = FinancialAnalysisAgent()
        print("✅ Financial analysis agent import and instantiation successful")
    except Exception as e:
        errors.append(f"❌ Financial analysis agent failed: {e}")
    
    try:
        print("Testing goal extraction agent...")
        from plutus.agents.goal_extraction_agent import GoalExtractionAgent
        agent = GoalExtractionAgent()
        print("✅ Goal extraction agent import and instantiation successful")
    except Exception as e:
        errors.append(f"❌ Goal extraction agent failed: {e}")
    
    try:
        print("Testing recommendation agent...")
        from plutus.agents.recommendation_agent import RecommendationAgent
        agent = RecommendationAgent()
        print("✅ Recommendation agent import and instantiation successful")
    except Exception as e:
        errors.append(f"❌ Recommendation agent failed: {e}")
    
    try:
        print("Testing risk assessment agent...")
        from plutus.agents.risk_assessment_agent import RiskAssessmentAgent
        agent = RiskAssessmentAgent()
        print("✅ Risk assessment agent import and instantiation successful")
    except Exception as e:
        errors.append(f"❌ Risk assessment agent failed: {e}")
    
    try:
        print("Testing advanced orchestrator...")
        from plutus.agents.advanced_orchestrator import AdvancedOrchestrator
        orchestrator = AdvancedOrchestrator()
        print("✅ Advanced orchestrator import and instantiation successful")
    except Exception as e:
        errors.append(f"❌ Advanced orchestrator failed: {e}")
    
    try:
        print("Testing memory service...")
        from plutus.services.memory_service import MemoryService
        memory = MemoryService(db_path="test_memory.db")
        print("✅ Memory service import and instantiation successful")
    except Exception as e:
        errors.append(f"❌ Memory service failed: {e}")
    
    # Summary
    print("\n" + "="*60)
    if errors:
        print("❌ VALIDATION FAILED")
        for error in errors:
            print(error)
        return False
    else:
        print("✅ ALL IMPORTS VALIDATED SUCCESSFULLY")
        return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)