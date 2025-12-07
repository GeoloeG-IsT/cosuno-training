# Tool System Architecture Overview

## Visual Architecture

### Complete Agent Graph with Tools

```
START
  |
  v
┌─────────────┐
│    PARSE    │  Extract project_id and scope
└─────────────┘
  |
  v
┌──────────────────┐
│ VALIDATE_PARSE   │  Check parse quality
└──────────────────┘
  |
  +─────────────────────────────┐
  |                             |
  v (if valid)            v (if invalid)
┌─────────────────┐     ┌──────────┐
│  FETCH BIDS     │     │ CLARIFY  │  Request user clarification
└─────────────────┘     └──────────┘
  |                           |
  +─────────────────────────────+
  |
  v
┌────────────────────────────────────────┐
│          USE TOOLS (NEW)               │
│  ┌──────────────────────────────────┐  │
│  │ MarketDataTool.execute(scope)    │  │  Fetch market benchmarks
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │ CostEstimatorTool.execute(scope) │  │  Estimate costs
│  └──────────────────────────────────┘  │
│                                        │
│  Returns: tool_calls, tool_results    │
└────────────────────────────────────────┘
  |
  v
┌──────────────────┐
│  COMPARISON      │  (router) Enough bids?
└──────────────────┘
  |         |
  | YES     | NO
  |         v
  |     ┌──────────┐
  |     │ REFETCH  │  Get more bids
  |     └──────────┘
  |         |
  |<────────+
  |
  v
┌──────────────────────┐
│ VALIDATE_COMPARISON  │  Check results exist
└──────────────────────┘
  |
  v
┌────────────────────────────────────────┐
│        FORMAT (uses tool results)      │  
│  Include market context and budgets    │
│  in final recommendation               │
└────────────────────────────────────────┘
  |
  v
 END
```

## Tool Node Detail

### _use_tools_node Implementation

```
┌─────────────────────────────────────────────────────────┐
│           USE TOOLS NODE (_use_tools_node)              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  INPUT: state with scope and bids                      │
│                                                         │
│  EXECUTION:                                             │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Tool 1: MarketDataTool                             │ │
│  │ ─────────────────────────────                      │ │
│  │ Input:  scope = "excavation"                       │ │
│  │ Execute: MarketDataTool.execute("excavation")     │ │
│  │ Output: {                                          │ │
│  │   "scope": "excavation",                           │ │
│  │   "market_suppliers": 47,                          │ │
│  │   "avg_cost_per_day": 1500,                        │ │
│  │   "current_trend": "stable"                        │ │
│  │ }                                                  │ │
│  │ Status: ✅ Success                                 │ │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Tool 2: CostEstimatorTool                          │ │
│  │ ────────────────────────────                       │ │
│  │ Input:  scope = "excavation", complexity = "med"  │ │
│  │ Execute: CostEstimatorTool.execute(...)           │ │
│  │ Output: {                                          │ │
│  │   "scope": "excavation",                           │ │
│  │   "estimated_total": 10000,                        │ │
│  │   "confidence": "high",                            │ │
│  │   "breakdown": {...}                              │ │
│  │ }                                                  │ │
│  │ Status: ✅ Success                                 │ │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  OUTPUT STATE UPDATES:                                  │
│  {                                                      │
│    "tool_calls": [                                      │
│      {"tool": "market_data_fetcher", "status": "success"},
│      {"tool": "cost_estimator", "status": "success"}   │
│    ],                                                   │
│    "tool_results": {                                    │
│      "market_data": {...},                             │
│      "cost_estimate": {...}                            │
│    }                                                    │
│  }                                                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Tool Lifecycle

```
APP START
  |
  v
┌────────────────────────────────────────┐
│  Tool Registration                     │
│  AVAILABLE_TOOLS = {                   │
│    "market_data_fetcher": MarketDataTool,
│    "cost_estimator": CostEstimatorTool,
│    ...                                  │
│  }                                      │
└────────────────────────────────────────┘
  |
  v
AGENT RUN (for each execution)
  |
  +─────────────────────────────────────┐
  |                                     |
  v                                     |
┌──────────────────┐                    |
│  Parse Input     │                    |
│  Extract Scope   │                    |
└──────────────────┘                    |
  |                                     |
  v                                     |
┌──────────────────┐                    |
│ Fetch Bids       │                    |
│ (3 bids)         │                    |
└──────────────────┘                    |
  |                                     |
  v                                     |
┌────────────────────────────────────────────┐
│  USE TOOLS NODE                            │
│  ┌────────────────────────────────────────┐│
│  │ For each tool in AVAILABLE_TOOLS:      ││
│  │  1. Get tool class                     ││
│  │  2. Call tool.execute(params)          ││
│  │  3. Catch exceptions                   ││
│  │  4. Store result or error              ││
│  │  5. Log status                         ││
│  └────────────────────────────────────────┘│
└────────────────────────────────────────────┘
  |
  v
┌────────────────────────┐
│ Format Recommendation  │
│ (uses tool results)    │
└────────────────────────┘
  |
  v
RETURN RESULT
  |
  +─→ recommendation
  +─→ bids
  +─→ tool_calls (what was called)
  +─→ tool_results (what was returned)
```

## State Flow with Tools

```
INITIAL STATE
┌────────────────────────────────────────┐
│ prompt: "Get excavation bids for P-25" │
│ project_id: null                       │
│ scope: null                            │
│ bids: []                               │
│ tool_calls: null                       │
│ tool_results: null                     │
└────────────────────────────────────────┘
         |
         v (after parse)
┌────────────────────────────────────────┐
│ project_id: "P-2025"                   │
│ scope: "excavation"                    │
│ + other fields unchanged               │
└────────────────────────────────────────┘
         |
         v (after fetch)
┌────────────────────────────────────────┐
│ bids: [                                │
│   {"subcontractor": "ABC", "price": 95}, ... 
│ ]                                      │
│ _fetch_attempts: 1                     │
│ + other fields unchanged               │
└────────────────────────────────────────┘
         |
         v (after use_tools) ← ← ← NEW STEP
┌────────────────────────────────────────┐
│ tool_calls: [                          │
│   {"tool": "market_data_fetcher",      │
│    "status": "success"}                │
│ ]                                      │
│ tool_results: {                        │
│   "market_data": {                     │
│     "scope": "excavation",             │
│     "market_suppliers": 47,            │
│     ...                                │
│   },                                   │
│   "cost_estimate": {                   │
│     "estimated_total": 10000,          │
│     ...                                │
│   }                                    │
│ }                                      │
│ + other fields unchanged               │
└────────────────────────────────────────┘
         |
         v (after format)
┌────────────────────────────────────────┐
│ recommendation: "Recommended ABC...    │
│ Market: 47 suppliers (stable)...      │
│ Budget: $10,000..."                   │
│ + all previous fields                 │
└────────────────────────────────────────┘
         |
         v
      RETURN
```

## Tool Data Models

### Tool Call Record

```
{
  "tool": "market_data_fetcher",    ← Tool identifier
  "params": {"scope": "excavation"}, ← What was passed in
  "status": "success",              ← success | failed
  "error": null                     ← Error message if failed
}
```

### Tool Results Storage

```
tool_results = {
  "market_data": {
    "scope": "excavation",
    "market_suppliers": 47,
    "avg_cost_per_day": 1500,
    "current_trend": "stable",
    "timestamp": "2025-12-06"
  },
  "cost_estimate": {
    "scope": "excavation",
    "complexity": "medium",
    "estimated_total": 10000,
    "confidence": "high",
    "breakdown": {
      "base": 5000,
      "labor": 3000,
      "equipment": 2000
    }
  }
}
```

## Tool Execution Decision Tree

```
                           use_tools_node
                                |
                        ────────────────────
                        |                  |
                        v                  v
                   Tool 1: Market    Tool 2: Cost
                        |                  |
                ────────┴──────────────────┴────────
                |       |       |       |       |
                v       v       v       v       v
              TRY    EXECUTE  SUCCESS CATCH   RETURN
               |        |        |      |        |
             Try to   Get scope  Store  Handle   Update
             execute   and run  results error    state
             tool    tool logic  and
                               record
                               status
```

## Comparison: With vs Without Tools

### Without Tools

```
AGENT INPUT
  ↓
PARSE & EXTRACT
  ↓
FETCH BIDS
  ↓
COMPARE (no context)
  ↓
GENERATE RECOMMENDATION (LLM guessing)
  ↓
OUTPUT

Limitations:
❌ No market awareness
❌ No budget guidance
❌ Purely text-based decisions
❌ No real-world validation
```

### With Tools

```
AGENT INPUT
  ↓
PARSE & EXTRACT
  ↓
FETCH BIDS
  ↓
USE TOOLS (gather market data, estimate costs)
  ↓
COMPARE (with market context)
  ↓
GENERATE RECOMMENDATION (market-aware, budget-aware)
  ↓
OUTPUT + TOOL INSIGHTS

Advantages:
✅ Market-aware decisions
✅ Budget-informed estimates
✅ Real-world validation
✅ Richer recommendations
✅ Extensible architecture
```

## Tool Error Handling Flow

```
                    use_tools_node
                          |
                          v
                   For each tool:
                          |
          ┌───────────────┼───────────────┐
          |               |               |
          v               v               v
       TRY          EXECUTE          CATCH
          |               |               |
          |        Tool returns         |
          |         dict result     Exception
          |               |               |
          |               v               v
          |         Store in         Log warning
          |         tool_results     Store error
          |               |          in tool_calls
          |               |               |
          |               |         Mark status:
          |               |         "failed"
          |               |               |
          └───────────────┼───────────────┘
                          |
                          v
                    Return state:
                    - tool_calls (all calls)
                    - tool_results (successful ones)
                    
Note: Agent continues regardless
      of tool failures!
```

## Tool Integration Points

```
Available in these nodes:
  ✅ _format_node     (uses results to enhance recommendation)
  ✅ _compare_node    (could use to validate bids)
  ✅ Routers          (could influence routing decisions)
  ✅ Any downstream   (accessed via state.get("tool_results"))

Not used in:
  ❌ _parse_node      (happens before tools)
  ❌ _fetch_node      (happens before tools)
  ❌ _clarify_node    (fallback, happens before tools)
```

## Summary: Tool System Layers

```
LAYER 1: TOOL DEFINITIONS
┌─────────────────────────────────────┐
│ MarketDataTool                      │
│ CostEstimatorTool                   │
│ [CustomTools...]                    │
└─────────────────────────────────────┘
         ↑
         └─────────────┬──────────────────┐
                       |                  |
LAYER 2: TOOL REGISTRY v                  v
┌─────────────────────────────────────┐
│ AVAILABLE_TOOLS = {                 │
│   "name": ToolClass,                │
│   ...                               │
│ }                                   │
└─────────────────────────────────────┘
         ↑
         |
LAYER 3: EXECUTION (in _use_tools_node)
┌─────────────────────────────────────┐
│ For each tool:                      │
│   Execute & track results           │
│   Handle errors gracefully          │
│   Store in state                    │
└─────────────────────────────────────┘
         ↑
         |
LAYER 4: CONSUMPTION (downstream nodes)
┌─────────────────────────────────────┐
│ _format_node reads tool_results     │
│ Routers can use tool results        │
│ Other nodes access via state        │
└─────────────────────────────────────┘
         ↑
         |
LAYER 5: OUTPUT
┌─────────────────────────────────────┐
│ Final recommendation with:          │
│ - Tool insights                     │
│ - Tool call logs                    │
│ - Tool results for transparency     │
└─────────────────────────────────────┘
```

This layered approach makes tools:
- Easy to add (new layer 1 class)
- Easy to extend (register in layer 2)
- Easy to test (layer 3 independent)
- Easy to use (layers 4-5 integration)
