# Quick Reference: Built-in Tools

## Tool Definitions

### MarketDataTool

Fetches market benchmarks and supplier availability for construction scopes.

| Property | Value |
|----------|-------|
| **Name** | `market_data_fetcher` |
| **Class** | `MarketDataTool` |
| **Purpose** | Market intelligence for competitive analysis |

#### Method Signature

```python
MarketDataTool.execute(scope: str) -> dict
```

#### Parameters

| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| `scope` | str | Construction scope (e.g., "excavation", "roofing") | Yes |

#### Returns

```python
{
    "scope": "excavation",                    # Scope queried
    "avg_cost_per_day": 1500,                # Average daily rate
    "avg_cost_per_cubic_yard": 8,            # Alternative metric
    "market_suppliers": 47,                   # Number of suppliers
    "current_trend": "stable",                # Market trend
    "timestamp": "2025-12-06"                 # When data was fetched
}
```

#### Data by Scope

| Scope | Avg Cost | Suppliers | Trend |
|-------|----------|-----------|-------|
| excavation | $1,500/day | 47 | stable |
| roofing | $12/sqft | 63 | increasing |
| concrete | $180/yard | 52 | stable |
| general | $2,000/day | 100 | varies |

#### Example Usage

```python
# Get market data for excavation
market = MarketDataTool.execute("excavation")
print(f"Market rate: ${market['avg_cost_per_day']}/day")
print(f"Available suppliers: {market['market_suppliers']}")

# Validate a bid against market average
bid_price = 1800
if bid_price > market['avg_cost_per_day']:
    print(f"Warning: bid is {(bid_price/market['avg_cost_per_day']-1)*100:.0f}% above market")
```

#### Error Handling

```python
try:
    market = MarketDataTool.execute("excavation")
except Exception as e:
    logger.warning(f"Market tool failed: {e}")
    # Continue without market data
```

---

### CostEstimatorTool

Estimates project costs based on scope and complexity level.

| Property | Value |
|----------|-------|
| **Name** | `cost_estimator` |
| **Class** | `CostEstimatorTool` |
| **Purpose** | Budget estimation and cost forecasting |

#### Method Signature

```python
CostEstimatorTool.execute(scope: str, complexity: str = "medium") -> dict
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scope` | str | - | Construction scope (required) |
| `complexity` | str | "medium" | "low", "medium", or "high" |

#### Returns

```python
{
    "scope": "roofing",                      # Scope estimated
    "complexity": "high",                    # Complexity level
    "estimated_total": 36000,                # Total budget
    "confidence": "medium",                  # Estimate confidence
    "breakdown": {                           # Cost breakdown
        "base": 18000,
        "labor": 7500,
        "materials": 10500
    }
}
```

#### Complexity Multipliers

| Complexity | Multiplier | Use Case |
|-----------|------------|----------|
| low | 0.8x | Simple, straightforward projects |
| medium | 1.0x | Standard projects (default) |
| high | 1.5x | Complex, high-risk projects |

#### Cost by Scope (Medium Complexity)

| Scope | Base | Labor | Materials | Total |
|-------|------|-------|-----------|-------|
| excavation | $5,000 | $3,000 | $2,000 | $10,000 |
| roofing | $12,000 | $5,000 | $7,000 | $24,000 |
| concrete | $8,000 | $3,000 | $5,000 | $16,000 |
| general | $10,000 | $6,000 | $4,000 | $20,000 |

#### Example Usage

```python
# Estimate costs for a medium complexity roofing project
estimate = CostEstimatorTool.execute("roofing", "medium")
print(f"Estimated budget: ${estimate['estimated_total']:,}")
print(f"Breakdown:")
for category, cost in estimate['breakdown'].items():
    print(f"  {category}: ${cost:,}")

# High complexity roofing would be 1.5x higher
high_estimate = CostEstimatorTool.execute("roofing", "high")
print(f"High complexity estimate: ${high_estimate['estimated_total']:,}")
```

#### Complexity Auto-Detection

```python
# Determine complexity based on scope
complexity = "medium"
if "roofing" in scope.lower():
    complexity = "high"
elif "excavation" in scope.lower():
    complexity = "medium"

estimate = CostEstimatorTool.execute(scope, complexity)
```

#### Error Handling

```python
try:
    estimate = CostEstimatorTool.execute("roofing", "high")
except Exception as e:
    logger.warning(f"Cost estimator failed: {e}")
    # Use fallback estimate
    estimate = {"estimated_total": 20000, "confidence": "low"}
```

---

## Tool Usage in Agent

### Where Tools Are Used

```
fetch → use_tools → (router) → refetch or compare
           ↑
       Executes both:
       - MarketDataTool
       - CostEstimatorTool
```

### Tool Results in State

After tool execution, the state contains:

```python
state = {
    "tool_calls": [
        {
            "tool": "market_data_fetcher",
            "params": {"scope": "excavation"},
            "status": "success"
        },
        {
            "tool": "cost_estimator",
            "params": {"scope": "excavation", "complexity": "medium"},
            "status": "success"
        }
    ],
    "tool_results": {
        "market_data": { ... },
        "cost_estimate": { ... }
    }
}
```

### Accessing Tool Results

```python
def _format_node(self, state):
    tool_results = state.get("tool_results", {})
    
    market = tool_results.get("market_data", {})
    estimate = tool_results.get("cost_estimate", {})
    
    # Use in recommendation
    return {"recommendation": f"...{market['market_suppliers']} suppliers..."}
```

---

## Common Patterns

### Pattern: Validate Bid Against Market

```python
def validate_bid_against_market(bid_price, scope):
    market = MarketDataTool.execute(scope)
    market_rate = market["avg_cost_per_day"]
    
    if bid_price > market_rate * 1.5:
        return ("overpriced", bid_price - market_rate)
    elif bid_price < market_rate * 0.5:
        return ("suspicious_low", market_rate - bid_price)
    else:
        return ("competitive", 0)
```

### Pattern: Estimate + Bid Comparison

```python
def compare_bid_to_estimate(bid_price, scope):
    estimate = CostEstimatorTool.execute(scope)
    estimated = estimate["estimated_total"]
    
    percentage = (bid_price / estimated) * 100
    
    if percentage < 80:
        assessment = "Well under budget"
    elif percentage > 120:
        assessment = "Exceeds estimate"
    else:
        assessment = "Within budget"
    
    return assessment
```

### Pattern: Complexity-Based Estimation

```python
def estimate_with_complexity(scope, project_difficulty):
    complexity = "high" if project_difficulty > 7 else "medium" if project_difficulty > 3 else "low"
    return CostEstimatorTool.execute(scope, complexity)
```

### Pattern: Multiple Scope Estimation

```python
def estimate_project(scopes: list[str]):
    total = 0
    breakdown = {}
    
    for scope in scopes:
        estimate = CostEstimatorTool.execute(scope)
        breakdown[scope] = estimate["estimated_total"]
        total += estimate["estimated_total"]
    
    return {"total": total, "by_scope": breakdown}
```

---

## API Reference

### MarketDataTool API

```python
class MarketDataTool:
    name = "market_data_fetcher"
    description = "Fetch market pricing data and benchmarks for construction scopes"
    
    @staticmethod
    def execute(scope: str) -> dict:
        """
        Fetch market data for a construction scope.
        
        Args:
            scope: Construction scope string
            
        Returns:
            dict with keys:
                - scope: Input scope
                - avg_cost_per_day: Daily rate
                - avg_cost_per_cubic_yard: Volume rate
                - market_suppliers: Number of suppliers
                - current_trend: Market trend
                - timestamp: When fetched
                
        Raises:
            Exception: If scope not recognized or API fails
        """
```

### CostEstimatorTool API

```python
class CostEstimatorTool:
    name = "cost_estimator"
    description = "Estimate project costs based on scope, size, and complexity"
    
    @staticmethod
    def execute(scope: str, complexity: str = "medium") -> dict:
        """
        Estimate costs for a project.
        
        Args:
            scope: Construction scope string
            complexity: "low", "medium", or "high"
            
        Returns:
            dict with keys:
                - scope: Input scope
                - complexity: Input complexity
                - estimated_total: Total estimated cost
                - confidence: Estimate confidence level
                - breakdown: dict with categories and costs
                
        Raises:
            Exception: If scope not recognized or calculation fails
        """
```

---

## Tool Discovery

### List Available Tools

```python
from src.construction_assistant.enhanced_langgraph_agent import AVAILABLE_TOOLS

for name, tool_class in AVAILABLE_TOOLS.items():
    print(f"{name}: {tool_class.description}")
```

Output:
```
market_data_fetcher: Fetch market pricing data and benchmarks for construction scopes
cost_estimator: Estimate project costs based on scope, size, and complexity
```

### Check Tool Status

```python
def check_tool_status(scope):
    status = {}
    
    for name, tool_class in AVAILABLE_TOOLS.items():
        try:
            result = tool_class.execute(scope)
            status[name] = "✅ Available"
        except Exception as e:
            status[name] = f"❌ Failed: {e}"
    
    return status
```

---

## Testing Tools

### Unit Test Example

```python
def test_market_tool():
    result = MarketDataTool.execute("excavation")
    
    # Assertions
    assert result["scope"] == "excavation"
    assert result["market_suppliers"] > 0
    assert result["current_trend"] in ["stable", "increasing"]
    assert "timestamp" in result
```

### Integration Test Example

```python
def test_agent_uses_tools():
    agent = EnhancedLangGraphAgent(use_llm=False)
    agent.build_graph()
    
    result = agent.run("Get excavation bids for P-2025")
    
    # Verify tools were called
    assert result["tool_calls"] is not None
    assert any(call["tool"] == "market_data_fetcher" for call in result["tool_calls"])
    assert any(call["tool"] == "cost_estimator" for call in result["tool_calls"])
    
    # Verify results present
    assert "market_data" in result["tool_results"]
    assert "cost_estimate" in result["tool_results"]
```

---

## Summary Table

| Tool | Input | Output | Purpose |
|------|-------|--------|---------|
| **MarketDataTool** | scope | market rates, supplier count, trend | Validate competitiveness |
| **CostEstimatorTool** | scope, complexity | budget, breakdown, confidence | Set expectations |

Both tools:
- ✅ Execute synchronously
- ✅ Return JSON-serializable dicts
- ✅ Handle errors gracefully
- ✅ Work with or without API keys
- ✅ Can be easily extended
