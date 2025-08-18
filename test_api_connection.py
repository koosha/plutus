#!/usr/bin/env python3
"""
Test Claude API Connection
===========================

Tests if the Claude API key is working properly.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from plutus.core.config import get_config
from plutus.agents.financial_analysis_agent import FinancialAnalysisAgent

def test_api_key():
    """Test if API key is loaded and working."""
    
    print("🔑 TESTING CLAUDE API CONNECTION")
    print("="*50)
    
    # Check environment variable directly
    api_key = os.getenv("ANTHROPIC_API_KEY")
    print(f"Environment API Key: {'✅ Found' if api_key else '❌ Not found'}")
    if api_key:
        print(f"Key preview: {api_key[:15]}...{api_key[-10:]}")
    
    # Check config loading
    config = get_config()
    print(f"Config API Key: {'✅ Loaded' if config.anthropic_api_key else '❌ Not loaded'}")
    if config.anthropic_api_key:
        print(f"Config key preview: {config.anthropic_api_key[:15]}...{config.anthropic_api_key[-10:]}")
    
    # Test agent initialization
    print("\n🤖 Testing Agent Initialization:")
    agent = FinancialAnalysisAgent()
    print(f"Claude client: {'✅ Initialized' if agent.claude_client else '❌ No client'}")
    
    if agent.claude_client:
        print("🎉 API connection should be working!")
        print("The system can make real Claude API calls.")
    else:
        print("⚠️ Running in simulation mode")
        print("Responses will be simulated instead of using Claude API")
    
    return agent.claude_client is not None

if __name__ == "__main__":
    api_working = test_api_key()
    
    if api_working:
        print("\n✅ Ready for production with full Claude AI capabilities!")
    else:
        print("\n⚠️ Currently running in simulation mode.")
        print("To enable full Claude AI:")
        print("1. Check that .env file has valid ANTHROPIC_API_KEY")
        print("2. Ensure the API key starts with 'sk-ant-api03-'")
        print("3. Verify the key has proper permissions")