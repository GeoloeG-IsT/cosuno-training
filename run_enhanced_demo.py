#!/usr/bin/env python3
"""Demo the enhanced agent with advanced LangGraph features."""

import sys
from pathlib import Path
import logging

# Setup logging to see all the advanced features in action
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s'
)

sys.path.insert(0, str(Path(__file__).parent / "src"))

from construction_assistant import EnhancedLangGraphAgent


def main():
    print("\n" + "=" * 80)
    print("🚀 Enhanced LangGraph Agent - Advanced Features Demo")
    print("=" * 80)
    print("\nFeatures demonstrated:")
    print("  ✅ Conditional routing (validation → clarify or fetch)")
    print("  ✅ Loops (fetch → refetch if insufficient bids)")
    print("  ✅ Multi-stage validation (parse + comparison)")
    print("  ✅ Fallback strategies (LLM → regex)")
    print("\n" + "=" * 80 + "\n")
    
    # Initialize with lower min_bids threshold for demo
    agent = EnhancedLangGraphAgent(
        use_llm=False,  # Demo mode
        min_bids=2,
        max_retries=2
    )
    
    # Test cases that exercise different paths
    test_cases = [
        {
            "name": "Valid Request",
            "prompt": "Get bids for foundation works on project P-2025-001",
            "notes": "Parse succeeds → fetch → compare"
        },
        {
            "name": "Ambiguous Project ID",
            "prompt": "I need excavation for the downtown project",
            "notes": "Parse fails → clarify → fetch → compare"
        },
        {
            "name": "Request with Multiple Refetch Triggers",
            "prompt": "Find contractors for roofing on project ALPHA-2025",
            "notes": "May trigger refetch loop if bids < min_bids"
        },
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'─' * 80}")
        print(f"Test {i}: {test['name']}")
        print(f"Notes: {test['notes']}")
        print(f"{'─' * 80}")
        print(f"Prompt: {test['prompt']}\n")
        
        try:
            result = agent.run(test['prompt'], verbose=False)
            
            print(f"\n✅ Results:")
            print(f"   Project ID: {result.get('project_id')}")
            print(f"   Scope: {result.get('scope')}")
            print(f"   Bids Retrieved: {len(result.get('bids', []))}")
            
            if result.get('comparison', {}).get('top'):
                print(f"   Top Bid: {result['comparison']['top'][0]['subcontractor']} - ${result['comparison']['top'][0]['price']:,}")
            
            print(f"\nRecommendation:")
            for line in result.get('recommendation', '').split('\n'):
                print(f"   {line}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("✅ Advanced Features Demo Complete!")
    print("\nKey Features Used:")
    print("  1. Conditional Routing:")
    print("     - validate_parse → clarify OR fetch")
    print("     - fetch → refetch OR compare")
    print("\n  2. Loops:")
    print("     - Retries fetch if insufficient bids")
    print("     - Respects max_retries parameter")
    print("\n  3. Multi-stage Validation:")
    print("     - Parse validation with confidence scores")
    print("     - Comparison result validation")
    print("\n  4. Fallback Mechanisms:")
    print("     - LLM → regex parsing")
    print("     - Clarification node for ambiguous inputs")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
