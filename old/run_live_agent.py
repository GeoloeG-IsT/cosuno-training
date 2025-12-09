#!/usr/bin/env python3
"""Live agent demo - improved version with fallback to regex parsing."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from construction_assistant import LangGraphAgent


def main():
    print("=" * 80)
    print("🚀 LangGraph Agent - Demo with Fallback Parsing")
    print("=" * 80)
    print()
    
    # Initialize agent in demo mode (no API quota issues)
    # Set use_llm=False to use regex-based parsing instead of Gemini
    print("📦 Initializing LangGraphAgent...")
    agent = LangGraphAgent(api_key="demo", top_n=2, use_llm=False)
    print("✅ Agent initialized (using regex parsing for demo)\n")
    
    # Example prompts
    prompts = [
        "Get subcontractor bids for foundation works on project P-2025-001",
        "I need excavation services for project BuildingXYZ - get me the best options",
        "Find the cheapest contractors for roofing on project ALPHA-2025",
    ]
    
    for i, prompt in enumerate(prompts, 1):
        print("-" * 80)
        print(f"📝 Request #{i}:")
        print(f"   {prompt}")
        print("-" * 80)
        
        try:
            # Run with verbose=True to see detailed execution
            result = agent.run(prompt, verbose=False)
            
            print(f"✅ Project ID: {result.get('project_id')}")
            print(f"📋 Scope: {result.get('scope')}")
            print()
            
            bids = result.get("bids", [])
            if bids:
                print("💰 Top Bids:")
                for bid in bids[:2]:
                    print(f"   • {bid.get('subcontractor')}: ${bid.get('price'):,} ({bid.get('lead_time_days')}d lead time)")
            print()
            
            print("📌 Recommendation:")
            rec = result.get('recommendation', 'No recommendation generated')
            for line in rec.split('\n'):
                print(f"   {line}")
            print()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    print("=" * 80)
    print("✅ Demo completed!")
    print()
    print("💡 To use real Gemini API:")
    print("   1. Make sure GOOGLE_API_KEY is set in .env")
    print("   2. Create agent with: LangGraphAgent(use_llm=True)")
    print("   3. Run: python run_live_agent.py")
    print("=" * 80)


if __name__ == "__main__":
    main()
