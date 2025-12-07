# Adding Custom Tools to the Agent

## Overview

The tool system is designed to be extensible. You can add new tools following the established pattern without modifying the core agent logic.

## Step-by-Step: Add a New Tool

### Step 1: Define the Tool Class

Create a new tool class with the required interface:

```python
class SupplierVerificationTool:
    """Verify supplier credentials and certifications."""
    
    name = "supplier_verifier"
    description = "Verify supplier licenses, ratings, and certifications"
    
    @staticmethod
    def execute(supplier_name: str) -> dict:
        """
        Verify a supplier's credentials.
        
        Args:
            supplier_name: Name of the supplier/contractor
            
        Returns:
            Verification result with status and details
        """
        # Simulated supplier verification database
        suppliers = {
            "ABC Contractors": {
                "rating": 4.8,
                "verified": True,
                "licenses": ["OSHA", "ISSA"],
                "years_in_business": 15
            },
            "Builders Co.": {
                "rating": 4.5,
                "verified": True,
                "licenses": ["OSHA"],
                "years_in_business": 8
            },
            "Quick Build": {
                "rating": 3.2,
                "verified": False,
                "licenses": [],
                "years_in_business": 1
            }
        }
        
        data = suppliers.get(supplier_name, {
            "rating": None,
            "verified": False,
            "licenses": [],
            "years_in_business": 0
        })
        
        return {
            "supplier": supplier_name,
            "verified": data.get("verified"),
            "rating": data.get("rating"),
            "licenses": data.get("licenses"),
            "years_in_business": data.get("years_in_business"),
            "recommended": data.get("verified") and data.get("rating", 0) >= 4.0
        }
```

### Step 2: Register the Tool

Add it to the `AVAILABLE_TOOLS` dictionary:

```python
AVAILABLE_TOOLS = {
    MarketDataTool.name: MarketDataTool,
    CostEstimatorTool.name: CostEstimatorTool,
    SupplierVerificationTool.name: SupplierVerificationTool,  # NEW TOOL
}
```

### Step 3: Use in Agent (Optional)

If you want the tool automatically used, modify `_use_tools_node`:

```python
def _use_tools_node(self, state: AgentState) -> dict:
    """Use available tools to gather market data and cost estimates."""
    scope = state.get("scope", "general")
    bids = state.get("bids", [])
    
    tool_calls = []
    tool_results = {}
    
    # Existing tools...
    # [market data and cost estimator code here]
    
    # NEW: Verify suppliers
    try:
        verified_bids = []
        for bid in bids:
            supplier_name = bid.get("subcontractor")
            verification = AVAILABLE_TOOLS["supplier_verifier"].execute(supplier_name)
            tool_calls.append({
                "tool": "supplier_verifier",
                "params": {"supplier_name": supplier_name},
                "status": "success"
            })
            verified_bids.append({
                **bid,
                "verification": verification
            })
        
        tool_results["supplier_verifications"] = verified_bids
    except Exception as e:
        logger.warning(f"Supplier verification failed: {e}")
    
    return {
        "tool_calls": tool_calls,
        "tool_results": tool_results,
    }
```

## Example Tools to Add

### Example 1: Schedule/Timeline Tool

```python
class SchedulingTool:
    """Estimate project timeline based on scope and complexity."""
    
    name = "scheduler"
    description = "Estimate project timeline and critical milestones"
    
    @staticmethod
    def execute(scope: str, team_size: int = 5) -> dict:
        """Estimate timeline for a project."""
        timelines = {
            "excavation": {"duration_days": 14, "phases": 3},
            "roofing": {"duration_days": 21, "phases": 4},
            "concrete": {"duration_days": 10, "phases": 2},
            "general": {"duration_days": 30, "phases": 5},
        }
        
        timeline = timelines.get(scope.lower(), timelines["general"])
        
        # Adjust for team size
        efficiency_factor = team_size / 5.0
        duration = max(int(timeline["duration_days"] / efficiency_factor), 5)
        
        return {
            "scope": scope,
            "estimated_duration_days": duration,
            "team_size": team_size,
            "critical_path": timeline["phases"],
            "start_date": "2025-12-15",
            "end_date": f"2025-12-{15+duration}"
        }
```

Usage:
```python
schedule = SchedulingTool.execute("roofing", team_size=8)
print(f"Project duration: {schedule['estimated_duration_days']} days")
```

### Example 2: Weather/Environmental Tool

```python
class WeatherTool:
    """Get weather forecasts relevant to construction."""
    
    name = "weather_checker"
    description = "Check weather conditions and environmental constraints"
    
    @staticmethod
    def execute(location: str, scope: str) -> dict:
        """Check weather impact on construction."""
        # Simulated weather data
        conditions = {
            "excavation": {
                "rain_impact": "high",
                "wind_impact": "low",
                "temperature_critical": False,
            },
            "roofing": {
                "rain_impact": "high",
                "wind_impact": "high",
                "temperature_critical": True,
            },
            "concrete": {
                "rain_impact": "high",
                "wind_impact": "low",
                "temperature_critical": True,
            }
        }
        
        weather = conditions.get(scope.lower(), {
            "rain_impact": "medium",
            "wind_impact": "medium",
            "temperature_critical": False,
        })
        
        return {
            "location": location,
            "scope": scope,
            **weather,
            "best_season": "spring/fall" if weather["temperature_critical"] else "year-round",
            "risk_level": "high" if weather["rain_impact"] == "high" else "medium"
        }
```

Usage:
```python
weather = WeatherTool.execute("New York", "roofing")
if weather["risk_level"] == "high":
    logger.warning("Weather risk is high for roofing project")
```

### Example 3: Material Availability Tool

```python
class MaterialAvailabilityTool:
    """Check material availability and lead times."""
    
    name = "material_checker"
    description = "Check material availability and supplier lead times"
    
    @staticmethod
    def execute(scope: str, quantity: int = 1) -> dict:
        """Check material availability."""
        materials = {
            "excavation": {
                "primary": "Heavy machinery",
                "lead_days": 3,
                "availability": "High"
            },
            "roofing": {
                "primary": "Roofing materials",
                "lead_days": 7,
                "availability": "Medium"
            },
            "concrete": {
                "primary": "Concrete mix",
                "lead_days": 1,
                "availability": "High"
            },
        }
        
        material = materials.get(scope.lower(), {
            "primary": "General materials",
            "lead_days": 5,
            "availability": "Medium"
        })
        
        # Adjust for quantity
        lead_days = material["lead_days"]
        if quantity > 10:
            lead_days += 3
        
        return {
            "scope": scope,
            "primary_material": material["primary"],
            "lead_time_days": lead_days,
            "availability": material["availability"],
            "current_price_trend": "stable",
            "recommended_order_date": "ASAP" if lead_days > 5 else "Flexible"
        }
```

Usage:
```python
materials = MaterialAvailabilityTool.execute("roofing", quantity=15)
print(f"Material lead time: {materials['lead_time_days']} days")
```

### Example 4: Compliance Tool

```python
class ComplianceTool:
    """Check regulatory and compliance requirements."""
    
    name = "compliance_checker"
    description = "Check building codes and compliance requirements"
    
    @staticmethod
    def execute(scope: str, region: str = "general") -> dict:
        """Check compliance requirements."""
        requirements = {
            "excavation": {
                "permits_required": ["Excavation", "Environmental"],
                "inspections": 2,
                "documentation": ["Survey", "Soil analysis"]
            },
            "roofing": {
                "permits_required": ["Building"],
                "inspections": 1,
                "documentation": ["Design plans"]
            },
            "concrete": {
                "permits_required": ["Building"],
                "inspections": 2,
                "documentation": ["Mix design", "Test results"]
            }
        }
        
        reqs = requirements.get(scope.lower(), {
            "permits_required": ["General"],
            "inspections": 1,
            "documentation": []
        })
        
        return {
            "scope": scope,
            "region": region,
            "permits": reqs["permits_required"],
            "required_inspections": reqs["inspections"],
            "required_documentation": reqs["documentation"],
            "estimated_compliance_cost": 2000 + len(reqs["permits_required"]) * 500
        }
```

Usage:
```python
compliance = ComplianceTool.execute("roofing", region="New York")
for permit in compliance["permits"]:
    print(f"Required permit: {permit}")
```

## Tool Integration Patterns

### Pattern: Tools with Dependencies

```python
def _use_tools_node(self, state):
    scope = state.get("scope")
    
    # Tool 1: Get market data first
    market = MarketDataTool.execute(scope)
    
    # Tool 2: Use market data to inform material check
    lead_days = 1 if market["current_trend"] == "stable" else 5
    materials = MaterialAvailabilityTool.execute(scope)
    
    # Tool 3: Use both previous results
    if materials["lead_time_days"] > 7:
        logger.warning("Long material lead time impacts schedule")
    
    return {
        "tool_results": {
            "market": market,
            "materials": materials,
        }
    }
```

### Pattern: Conditional Tool Selection

```python
def _use_tools_node(self, state):
    scope = state.get("scope")
    project_value = state.get("project_value", 10000)
    
    tool_results = {}
    
    # Always check market and cost
    tool_results["market"] = MarketDataTool.execute(scope)
    tool_results["estimate"] = CostEstimatorTool.execute(scope)
    
    # Only check compliance for high-value projects
    if project_value > 50000:
        tool_results["compliance"] = ComplianceTool.execute(scope)
    
    # Only schedule for long projects
    if "roofing" in scope.lower() or "concrete" in scope.lower():
        tool_results["schedule"] = SchedulingTool.execute(scope)
    
    return {"tool_results": tool_results}
```

### Pattern: Tool Chaining for Rich Insights

```python
def _use_tools_node(self, state):
    scope = state.get("scope")
    
    # Chain 1: Understand market
    market = MarketDataTool.execute(scope)
    
    # Chain 2: Estimate costs (uses market context internally)
    estimate = CostEstimatorTool.execute(scope)
    
    # Chain 3: Check materials (affects timeline)
    materials = MaterialAvailabilityTool.execute(scope)
    
    # Chain 4: Determine schedule (considers materials)
    schedule = SchedulingTool.execute(scope)
    
    # Chain 5: Verify compliance (uses all above info)
    compliance = ComplianceTool.execute(scope)
    
    return {
        "tool_results": {
            "market": market,
            "estimate": estimate,
            "materials": materials,
            "schedule": schedule,
            "compliance": compliance,
        }
    }
```

## Best Practices for Custom Tools

### 1. Consistent Interface

All tools should follow the same pattern:

```python
class MyTool:
    name = "identifier"
    description = "What it does"
    
    @staticmethod
    def execute(**kwargs) -> dict:
        # Implementation
        return {"key": "value"}
```

### 2. Error Handling

Tools should be resilient:

```python
@staticmethod
def execute(param: str) -> dict:
    try:
        # Implementation
        return {"status": "success", "data": ...}
    except Exception as e:
        logger.error(f"Tool failed: {e}")
        return {"status": "error", "error": str(e)}
```

### 3. Documentation

Clear docstrings help adoption:

```python
@staticmethod
def execute(scope: str, level: int = 1) -> dict:
    """
    Brief description.
    
    Args:
        scope: What it applies to
        level: Optional parameter (1-5)
        
    Returns:
        dict with keys: status, data, ...
        
    Raises:
        ValueError: If scope is invalid
    """
```

### 4. Testability

Make tools independently testable:

```python
def test_my_tool():
    result = MyTool.execute("test_input")
    assert result["status"] == "success"
    assert "data" in result
```

### 5. Reasonable Defaults

Tools should work with minimal parameters:

```python
@staticmethod
def execute(scope: str, complexity: str = "medium", optional: bool = False):
    # Parameters have sensible defaults
```

## Tool Lifecycle

### Discovery (at app start)

```python
# Framework can discover tools automatically
available = AVAILABLE_TOOLS.keys()  # Get all tool names
```

### Selection (in agent)

```python
# Agent decides which tools to use
if needs_market_data:
    market = AVAILABLE_TOOLS["market_data_fetcher"].execute(scope)
```

### Execution (in tool node)

```python
# Tools execute and return results
result = tool_class.execute(**params)
tool_results[name] = result
```

### Integration (in downstream nodes)

```python
# Results used in other nodes
market = state.get("tool_results", {}).get("market_data")
```

## Testing Custom Tools

### Unit Test Template

```python
def test_my_tool():
    # Setup
    test_input = "excavation"
    
    # Execute
    result = MyTool.execute(test_input)
    
    # Assert structure
    assert isinstance(result, dict)
    assert "status" in result
    
    # Assert content
    assert result["status"] == "success"
    assert result.get("data") is not None
```

### Integration Test Template

```python
def test_agent_with_custom_tool():
    agent = EnhancedLangGraphAgent(use_llm=False)
    agent.build_graph()
    
    result = agent.run("Get bids for excavation")
    
    # Verify tool was called
    tool_names = [call["tool"] for call in result.get("tool_calls", [])]
    assert "my_tool" in tool_names
    
    # Verify results present
    assert "my_tool_results" in result.get("tool_results", {})
```

## Summary

Adding custom tools is straightforward:

1. ✅ Create class with `name`, `description`, and `execute()` method
2. ✅ Register in `AVAILABLE_TOOLS` dictionary
3. ✅ Call in `_use_tools_node` (or other nodes)
4. ✅ Access results via `state.get("tool_results")`
5. ✅ Test independently and in integration

Tools unlock rich, context-aware agent behavior!
