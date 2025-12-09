#!/usr/bin/env python3
"""Live demo of the LangGraph agent with real Gemini API."""
import sys
sys.path.insert(0, 'src')

from construction_assistant import LangGraphAgent

def main():
    print("🚀 Starting LangGraph Agent with Real Gemini API\n")
    print("=" * 70)
    
    # Initialize agent (will automatically load GOOGLE_API_KEY from .env)
    print("📝 Initializing agent...")
    agent = LangGraphAgent(top_n=2)
    print("✅ Agent initialized successfully!\n")
    
    # Example requests
    requests = [
        "Get subcontractor bids for foundation works on project P-2025-001",
        "I need bids for excavation work. Project is EXC-42 and scope is site clearing",
        "Get bids for electrical installation on project ELEC-99"
    ]
    
    for i, request in enumerate(requests, 1):
        print(f"\n{'=' * 70}")
        print(f"📋 Request {i}:")
        print(f"   {request}")
        print("-" * 70)
        
        try:
            print("⏳ Processing with Gemini LLM...")
            result = agent.run(request)
            
            print("\n✅ Result:")
            print(f"   Project ID: {result.get('project_id', 'N/A')}")
            print(f"   Scope: {result.get('scope', 'N/A')}")
            print(f"   Bids Found: {len(result.get('bids', []))}")
            print(f"\n📊 Recommendation:")
            print("   " + "\n   ".join(result.get('recommendation', '').split('\n')))
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("✅ Demo Complete!\n")

if __name__ == "__main__":
    main()
