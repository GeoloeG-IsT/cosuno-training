"""LangChain tools for construction agent.

Demonstrates the proper @tool decorator pattern from LangChain:
- Uses type hints for automatic schema inference
- Includes detailed docstrings for LLM context
- Uses ToolException for proper error handling
- Tools are ready for LLM binding via bind_tools()
- Optional caching layer for expensive tool calls

Caching Example:
    from construction_assistant.tool_cache import init_tool_cache, create_cached_tool_wrapper
    cache = init_tool_cache()
    cached_fetch = create_cached_tool_wrapper(fetch_market_data, cache)
"""
import logging
from langchain_core.tools import tool
from langchain_core.tools.base import ToolException

logger = logging.getLogger(__name__)


@tool
def fetch_market_data(scope: str) -> dict:
    """Fetch market pricing data and benchmarks for construction scopes.
    
    This tool provides market intelligence for construction projects including:
    - Average pricing for different scopes
    - Number of available suppliers in the market
    - Current market trends (stable/increasing/decreasing)
    
    Args:
        scope: Construction scope such as 'excavation', 'roofing', 'concrete', etc.
        
    Returns:
        Dictionary containing market benchmarks with keys:
        - avg_cost_*: Average costs for the scope
        - market_suppliers: Number of suppliers available
        - current_trend: Market trend indicator
        - scope: The scope queried
        - timestamp: When data was fetched
        
    Raises:
        ToolException: If scope is invalid or data unavailable
    """
    if not scope or not isinstance(scope, str):
        raise ToolException("Scope must be a non-empty string")
    
    market_benchmarks = {
        "excavation": {
            "avg_cost_per_day": 1500,
            "avg_cost_per_cubic_yard": 8,
            "market_suppliers": 47,
            "current_trend": "stable",
        },
        "roofing": {
            "avg_cost_per_sqft": 12,
            "avg_cost_per_project": 15000,
            "market_suppliers": 63,
            "current_trend": "increasing",
        },
        "concrete": {
            "avg_cost_per_cubic_yard": 180,
            "avg_cost_per_sqft": 8,
            "market_suppliers": 52,
            "current_trend": "stable",
        },
        "general": {
            "avg_cost_per_day": 2000,
            "market_suppliers": 100,
            "current_trend": "unknown",
        },
    }
    
    try:
        data = market_benchmarks.get(scope.lower(), market_benchmarks["general"])
        result = {
            "scope": scope,
            "timestamp": "2025-12-06",
            **data,  # Spread market data
        }
        return result
    except Exception as e:
        raise ToolException(f"Failed to fetch market data: {str(e)}")


@tool
def estimate_project_cost(scope: str, complexity: str = "medium") -> dict:
    """Estimate project costs based on scope and complexity.
    
    This tool provides cost estimations for construction projects including:
    - Total estimated budget
    - Cost breakdown by category (labor, materials, equipment, etc.)
    - Confidence level of the estimate
    
    Args:
        scope: Construction scope such as 'excavation', 'roofing', 'concrete', etc.
        complexity: Project complexity level - 'low', 'medium', or 'high'.
                   Defaults to 'medium'.
        
    Returns:
        Dictionary containing cost estimates with keys:
        - scope: The scope queried
        - complexity: Complexity level used
        - breakdown: Dictionary with cost breakdown by category
        - estimated_total: Total estimated cost in dollars
        - confidence: Confidence level of estimate (high/medium/low)
        
    Raises:
        ToolException: If scope/complexity are invalid
    """
    if not scope or not isinstance(scope, str):
        raise ToolException("Scope must be a non-empty string")
    
    valid_complexities = {"low", "medium", "high"}
    if complexity.lower() not in valid_complexities:
        raise ToolException(f"Complexity must be one of {valid_complexities}")
    
    try:
        complexity_multipliers = {"low": 0.8, "medium": 1.0, "high": 1.5}
        multiplier = complexity_multipliers.get(complexity.lower(), 1.0)
        
        scope_estimates = {
            "excavation": {"base": 5000, "labor": 3000, "equipment": 2000},
            "roofing": {"base": 12000, "labor": 5000, "materials": 7000},
            "concrete": {"base": 8000, "labor": 3000, "materials": 5000},
            "general": {"base": 10000, "labor": 6000, "materials": 4000},
        }
        
        estimate = scope_estimates.get(scope.lower(), scope_estimates["general"])
        total = sum(estimate.values()) * multiplier
        
        return {
            "scope": scope,
            "complexity": complexity,
            "breakdown": {k: int(v * multiplier) for k, v in estimate.items()},
            "estimated_total": int(total),
            "confidence": "high" if complexity != "high" else "medium",
        }
    except Exception as e:
        raise ToolException(f"Failed to estimate project cost: {str(e)}")


# List of available tools for binding to LLM
AVAILABLE_TOOLS = [fetch_market_data, estimate_project_cost]
