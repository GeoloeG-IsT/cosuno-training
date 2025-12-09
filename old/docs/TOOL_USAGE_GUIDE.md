# Tool Usage in LangGraph Agents

## Overview

The enhanced agent demonstrates how to integrate **external tools** into LangGraph workflows. Tools are functions that agents call to gather information, make decisions, or perform actions that would be difficult with only the LLM.

## Architecture

### Tool Definition Pattern

Each tool follows a consistent pattern:

```python
class MyTool:
    """Description of what the tool does."""
    
    name = "tool_identifier"  # Unique name
    description = "What the tool does and why it's useful"
    
    @staticmethod
    def execute(param1: str, param2: str = "default") -> dict:
        """Execute the tool.
        
        Args:
            param1: First parameter
            param2: Optional second parameter
            
        Returns:
            Dictionary with results
        """
        # Implementation
        return {
            "result": "value",
            "status": "success",
            "metadata": {}
        }
```

### Registration

Tools are registered in a central dictionary:

```python
AVAILABLE_TOOLS = {
    "tool_name": ToolClass,
    "another_tool": AnotherTool,
}
```

This allows:
- Dynamic tool discovery
- Easy extension with new tools
- Serialization for APIs

## Built-in Tools

### 1. MarketDataTool

**Purpose**: Fetch market pricing benchmarks and supplier availability

**Input**:
- `scope`: Construction scope (e.g., "excavation", "roofing", "concrete")

**Output**:
```python
{
    "scope": "excavation",
    "avg_cost_per_day": 1500,          # Market rate
    "market_suppliers": 47,             # Number of suppliers
    "current_trend": "stable",          # Market condition
    "timestamp": "2025-12-06"
}
```

**Use Case**: Validate that bids are competitive with market rates

```python
market = MarketDataTool.execute("excavation")
if bid_price > market["avg_cost_per_day"]:
    print("Warning: bid exceeds market average")
```

### 2. CostEstimatorTool

**Purpose**: Estimate project costs based on scope and complexity

**Input**:
- `scope`: Construction scope
- `complexity`: "low", "medium", or "high" (default: "medium")

**Output**:
```python
{
    "scope": "roofing",
    "complexity": "high",
    "estimated_total": 36000,
    "confidence": "medium",
    "breakdown": {
        "base": 18000,
        "labor": 7500,
        "materials": 10500
    }
}
```

**Use Case**: Set budget expectations and validate estimates

```python
estimate = CostEstimatorTool.execute("roofing", complexity="high")
budget = estimate["estimated_total"]
print(f"Expected budget: ${budget:,}")
```

## Integration in Agent Workflow

### Graph Structure with Tools

```
START
  ↓
parse ─→ validate_parse
  ↓         ↓
clarify ← ─┴→ fetch
           ↓
         use_tools  ← ← ← TOOL NODE (new)
           ↓
       (router)
       ↙     ↖
   compare   refetch ─┐
      ↓               │
      └─ (loop) ──────┘
      ↓
  validate_comparison
      ↓
    format  ← ← ← Tools results used here
      ↓
      END
```

### Tool Node Implementation

The `_use_tools_node` is a regular LangGraph node that:

1. **Identifies applicable tools**: Based on scope/context
2. **Executes tools**: Calls tool's `execute()` method
3. **Handles errors**: Gracefully catches exceptions
4. **Tracks execution**: Records all tool calls and results
5. **Returns state updates**: Only modified fields

```python
def _use_tools_node(self, state: AgentState) -> dict:
    """Use available tools to enrich agent decisions."""
    scope = state.get("scope", "general")
    
    tool_calls = []
    tool_results = {}
    
    # Execute each tool
    for tool_name, tool_class in AVAILABLE_TOOLS.items():
        try:
            result = tool_class.execute(scope)
            tool_calls.append({
                "tool": tool_name,
                "status": "success"
            })
            tool_results[tool_name] = result
        except Exception as e:
            tool_calls.append({
                "tool": tool_name,
                "status": "failed",
                "error": str(e)
            })
    
    return {
        "tool_calls": tool_calls,
        "tool_results": tool_results
    }
```

## Tool Usage Patterns

### Pattern 1: Sequential Execution

Execute tools one after another:

```python
def _use_tools_node(self, state):
    results = {}
    
    # Tool 1
    market = AVAILABLE_TOOLS["market_data_fetcher"].execute(scope)
    results["market"] = market
    
    # Tool 2 (might depend on tool 1)
    estimate = AVAILABLE_TOOLS["cost_estimator"].execute(scope)
    results["estimate"] = estimate
    
    return {"tool_results": results}
```

### Pattern 2: Conditional Tool Selection

Use different tools based on state:

```python
def _use_tools_node(self, state):
    results = {}
    scope = state.get("scope")
    
    # Only use market tool if scope is specific
    if scope in ["excavation", "roofing", "concrete"]:
        results["market"] = MarketDataTool.execute(scope)
    
    # Always estimate costs
    results["estimate"] = CostEstimatorTool.execute(scope)
    
    return {"tool_results": results}
```

### Pattern 3: Tool Chaining

Tools that use results from other tools:

```python
def _use_tools_node(self, state):
    # Tool 1: Get market data
    market = MarketDataTool.execute(scope)
    
    # Tool 2: Uses market data for decision
    complexity = "high" if market["current_trend"] == "increasing" else "medium"
    estimate = CostEstimatorTool.execute(scope, complexity)
    
    return {"tool_results": {
        "market": market,
        "estimate": estimate
    }}
```

## Using Tool Results in Decisions

### In Router Functions

Tools can inform routing decisions:

```python
def _router_after_tools(self, state) -> Literal["format", "refetch"]:
    """Decide if we need more data based on tool results."""
    market = state.get("tool_results", {}).get("market_data")
    
    if market and market["market_suppliers"] < 10:
        return "refetch"  # Too few suppliers, try broader search
    else:
        return "format"   # Enough market data, proceed
```

### In Other Nodes

Tools enrich the recommendation:

```python
def _format_node(self, state):
    """Include tool insights in final recommendation."""
    tool_results = state.get("tool_results", {})
    market = tool_results.get("market_data", {})
    estimate = tool_results.get("cost_estimate", {})
    
    recommendation = f"""
    Recommended contractor: {top_bid}
    Market context: {market['market_suppliers']} suppliers available
    Budget estimate: ${estimate['estimated_total']:,}
    """
    
    return {"recommendation": recommendation}
```

## Error Handling

### Graceful Degradation

Tools should never crash the agent:

```python
def _use_tools_node(self, state):
    tool_results = {}
    
    try:
        tool_results["market"] = MarketDataTool.execute(scope)
    except Exception as e:
        logger.warning(f"Market tool failed: {e}")
        # Continue without market data
    
    try:
        tool_results["estimate"] = CostEstimatorTool.execute(scope)
    except Exception as e:
        logger.warning(f"Estimate tool failed: {e}")
        # Continue without estimate
    
    return {"tool_results": tool_results}
```

### Error Tracking

Record which tools succeeded/failed:

```python
tool_calls = [
    {"tool": "market_data_fetcher", "status": "success"},
    {"tool": "cost_estimator", "status": "failed", "error": "API down"},
]

# Later, check what tools worked
if all(call["status"] == "success" for call in tool_calls):
    logger.info("All tools executed successfully")
```

## Extending with New Tools

### Adding a Tool

1. **Define the tool class**:
```python
class SupplierVerificationTool:
    name = "supplier_verifier"
    description = "Verify supplier credentials and ratings"
    
    @staticmethod
    def execute(supplier_id: str) -> dict:
        # Implementation
        return {
            "supplier_id": supplier_id,
            "rating": 4.8,
            "verified": True,
            "licenses": ["OSHA", "ISSA"]
        }
```

2. **Register the tool**:
```python
AVAILABLE_TOOLS = {
    MarketDataTool.name: MarketDataTool,
    CostEstimatorTool.name: CostEstimatorTool,
    SupplierVerificationTool.name: SupplierVerificationTool,  # NEW
}
```

3. **Use in agent**:
```python
def _use_tools_node(self, state):
    tool_results = {}
    
    # Use new tool
    for bid in state.get("bids", []):
        supplier_id = bid.get("supplier_id")
        verification = AVAILABLE_TOOLS["supplier_verifier"].execute(supplier_id)
        tool_results[f"verification_{supplier_id}"] = verification
    
    return {"tool_results": tool_results}
```

## Advanced Tool Patterns

### Pattern: Tool Caching

Avoid re-executing the same tool with same parameters:

```python
class CachedToolNode:
    def __init__(self):
        self.cache = {}
    
    def _use_tools_node(self, state):
        scope = state.get("scope")
        cache_key = f"market_{scope}"
        
        if cache_key in self.cache:
            return {"tool_results": self.cache[cache_key]}
        
        result = MarketDataTool.execute(scope)
        self.cache[cache_key] = result
        return {"tool_results": {"market": result}}
```

### Pattern: Parallel Tool Execution

Execute multiple tools concurrently:

```python
import asyncio

async def _use_tools_node_async(self, state):
    """Execute tools in parallel."""
    scope = state.get("scope")
    
    # All tools run simultaneously
    market, estimate = await asyncio.gather(
        asyncio.to_thread(MarketDataTool.execute, scope),
        asyncio.to_thread(CostEstimatorTool.execute, scope)
    )
    
    return {
        "tool_results": {
            "market": market,
            "estimate": estimate
        }
    }
```

### Pattern: Tool Fallback Chain

Try tools in order until one succeeds:

```python
def _get_market_data(self, scope):
    """Try multiple market data sources."""
    tools = [
        PrimaryMarketTool,
        SecondaryMarketTool,
        FallbackEstimateTool
    ]
    
    for tool in tools:
        try:
            return tool.execute(scope)
        except Exception:
            continue
    
    # All failed, return default
    return {"market_suppliers": 0, "status": "unavailable"}
```

## Tool Discovery

Agents can discover available tools dynamically:

```python
def get_available_tools(self) -> list[dict]:
    """List all available tools for the agent."""
    return [
        {
            "name": tool_class.name,
            "description": tool_class.description
        }
        for tool_class in AVAILABLE_TOOLS.values()
    ]
```

This enables:
- User-facing documentation
- LLM-assisted tool selection
- Tool recommendations to users

## Practical Examples

### Example 1: Market Validation

```python
def _use_tools_node(self, state):
    bids = state.get("bids", [])
    scope = state.get("scope")
    
    # Get market data
    market = MarketDataTool.execute(scope)
    
    # Validate bids against market
    for bid in bids:
        if bid["price"] > market["avg_cost_per_day"] * 1.5:
            logger.warning(f"Bid from {bid['name']} exceeds market by 50%")
    
    return {"tool_results": {"market": market}}
```

### Example 2: Budget Awareness

```python
def _format_node(self, state):
    estimate = state.get("tool_results", {}).get("cost_estimate", {})
    top_bid = state.get("bids", [{}])[0]
    
    recommendation = f"Recommended: {top_bid['name']}"
    
    if estimate:
        if top_bid["price"] < estimate["estimated_total"] * 0.8:
            recommendation += " (well under budget)"
        elif top_bid["price"] > estimate["estimated_total"] * 1.2:
            recommendation += " (exceeds estimate)"
    
    return {"recommendation": recommendation}
```

### Example 3: Market Opportunity

```python
def _router_after_tools(self, state):
    market = state.get("tool_results", {}).get("market_data", {})
    
    # If market is increasing, offer to find more bids
    if market.get("current_trend") == "increasing":
        return "refetch"  # Get more bids while prices rising
    else:
        return "format"   # Proceed with current bids
```

## Testing Tools

### Unit Testing a Tool

```python
def test_market_tool():
    result = MarketDataTool.execute("excavation")
    
    assert result["scope"] == "excavation"
    assert "market_suppliers" in result
    assert result["current_trend"] in ["stable", "increasing"]
```

### Integration Testing with Agent

```python
def test_agent_with_tools():
    agent = EnhancedLangGraphAgent(use_llm=False)
    agent.build_graph()
    
    result = agent.run("Get excavation bids for P-2025")
    
    # Verify tools were called
    assert result["tool_calls"] is not None
    assert len(result["tool_calls"]) >= 2
    
    # Verify results are available
    assert "market_data" in result["tool_results"]
    assert "cost_estimate" in result["tool_results"]
```

## Best Practices

1. **Always include error handling**: Graceful failures
2. **Track tool execution**: Log which tools ran and status
3. **Return only modified fields**: LangGraph state best practice
4. **Document parameters and output**: Clear API contracts
5. **Make tools stateless**: No side effects, pure functions
6. **Use consistent naming**: tool names, parameter names
7. **Cache expensive calls**: Avoid redundant execution
8. **Test tools independently**: Unit test before integration
9. **Provide sensible defaults**: Handle missing tool results
10. **Monitor tool performance**: Log execution times

## Summary

Tools enable agents to:
- ✅ Access external data (market, pricing)
- ✅ Compute complex calculations (estimates)
- ✅ Validate decisions against real-world constraints
- ✅ Provide richer, more informed recommendations
- ✅ Handle scenarios LLMs alone can't solve

The key insight: **tools turn agents from text-transformers into decision-makers**.
