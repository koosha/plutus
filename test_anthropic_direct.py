#!/usr/bin/env python3
"""
Test Anthropic Library Directly
===============================

Tests the Anthropic library directly to see if it's working.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Load environment
from dotenv import load_dotenv
load_dotenv()

def test_anthropic():
    """Test Anthropic library directly."""
    
    print("🧪 TESTING ANTHROPIC LIBRARY DIRECTLY")
    print("="*50)
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    print(f"API Key: {'✅ Found' if api_key else '❌ Not found'}")
    
    try:
        from anthropic import Anthropic
        print("✅ anthropic library imported successfully")
        
        # Try to create client
        client = Anthropic(api_key=api_key)
        print("✅ Anthropic client created")
        
        # Try a simple test call
        print("\n🤖 Testing simple API call...")
        
        try:
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=50,
                messages=[
                    {"role": "user", "content": "Say 'Hello from Plutus!' and nothing else."}
                ]
            )
            
            print("✅ API call successful!")
            print(f"Response: {response.content[0].text}")
            print(f"Tokens used: {response.usage.input_tokens} in, {response.usage.output_tokens} out")
            return True
            
        except Exception as e:
            print(f"❌ API call failed: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Failed to import anthropic: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_anthropic()
    
    if success:
        print("\n🎉 Claude API is working perfectly!")
        print("Plutus can make real AI-powered responses!")
    else:
        print("\n❌ Claude API is not working.")
        print("Check your API key and internet connection.")