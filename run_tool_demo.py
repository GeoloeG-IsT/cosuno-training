#!/usr/bin/env python3
"""Demo showing tool usage in EnhancedLangGraphAgent.

This demonstrates how the agent uses multiple tools to enrich recommendations:
- MarketDataTool: Fetches market benchmarks and supplier counts
- CostEstimatorTool: Estimates project budgets

Tools are executed as part of the agent workflow and results are included
in the final recommendation.
"""
import logging
from src.construction_assistant.enhanced_langgraph_agent import EnhancedLangGraphAgent

# Setup logging to see all agent steps
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(message)s"
)

logger = logging.getLogger(__name__)


def test_with_tools(prompt: str, test_name: str):
    """Run agent with tool usage."""
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}")
    print(f"INPUT: {prompt}\n")
    
    # Create agent with tool usage capability
    agent = EnhancedLangGraphAgent(
        use_llm=False,  # Use regex for demo
        min_bids=2,
        max_retries=1
    )
    agent.build_graph()
    
    # Run agent
    logger.info(f"🚀 Starting agent with prompt: {prompt[:50]}...")
    result = agent.run(prompt, verbose=True)
    
    # Display results
    print("\n" + "="*70)
    print("RESULTS:")
    print("="*70)
    
    print(f"\n✅ Project ID: {result.get('project_id')}")
    print(f"✅ Scope: {result.get('scope')}")
    print(f"✅ Bids Retrieved: {len(result.get('bids', []))}")
    
    # Show tool calls and results
    tool_calls = result.get("tool_calls")
    tool_results = result.get("tool_results")
    
    if tool_calls:
        print(f"\n🔧 TOOLS USED ({len(tool_calls)}):")
        for call in tool_calls:
            status = "✅" if call.get("status") == "success" else "❌"
            tool_name = call.get("tool")
            params = call.get("params", {})
            print(f"  {status} {tool_name}")
            print(f"     Params: {params}")
            
            if call.get("status") == "success":
                if "market_data" in tool_results:
                    market = tool_results["market_data"]
                    print(f"     → Market suppliers: {market['market_suppliers']}")
                    print(f"     → Trend: {market['current_trend']}")
                if "cost_estimate" in tool_results:
                    estimate = tool_results["cost_estimate"]
                    print(f"     → Estimated cost: ${estimate['estimated_total']:,}")
                    print(f"     → Breakdown: {estimate['breakdown']}")
    
    # Show top bid comparison
    if result.get("comparison"):
        comparison = result.get("comparison")
        top_bids = comparison.get("top", [])
        
        if top_bids:
            print(f"\n📊 TOP BIDS ({len(top_bids)}):")
            for i, bid in enumerate(top_bids, 1):
                print(f"  {i}. {bid.get('subcontractor', 'Unknown')}")
                print(f"     Price: ${bid.get('price', 0):,}")
                print(f"     Lead time: {bid.get('lead_time_days', '?')} days")
    
    # Show final recommendation
    if result.get("recommendation"):
        print(f"\n💡 RECOMMENDATION:")
        print(f"  {result['recommendation']}")
    
    return result


if __name__ == "__main__":
    print("\n" + "="*70)
    print("TOOL USAGE DEMONSTRATION")
    print("="*70)
    print("\nThis demo shows how agents can use external tools to enrich decisions.")
    print("Two tools are available:")
    print("  1. MarketDataTool - Market benchmarks and supplier counts")
    print("  2. CostEstimatorTool - Budget estimation based on scope")
    print()
    
    # Test 1: Excavation project (medium complexity)
    test_with_tools(
        "Get bids for excavation work on project P-2025",
        "Excavation Project with Market Tools"
    )
    
    # Test 2: Roofing project (high complexity)
    test_with_tools(
        "I need roofing contractors for ALPHA-2025",
        "Roofing Project with Cost Estimation"
    )
    
    # Test 3: Concrete work (stable market)
    test_with_tools(
        "Concrete work needed for project BETA-100",
        "Concrete Project with Market Data"
    )
    
    print("\n" + "="*70)
    print("KEY OBSERVATIONS:")
    print("="*70)
    print("""
1. MarketDataTool provides:
   - Average costs and market rates
   - Number of suppliers in market
   - Current market trends (stable/increasing)
   
2. CostEstimatorTool provides:
   - Budget breakdown by category
   - Total estimated cost
   - Confidence levels
   
3. Tool results are used in recommendation formatting:
   - Market context added to final recommendation
   - Budget estimates inform decision confidence
   - Supplier availability noted in output

4. Tool execution is part of the graph flow:
   - Happens after fetch node
   - Before comparison and formatting
   - Failures handled gracefully with logging
   
5. Tools can be extended:
   - Add new tools by implementing same pattern
   - Register in AVAILABLE_TOOLS dictionary
   - Execute method returns data for agent to use
    """)
