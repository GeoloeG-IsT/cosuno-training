# Advanced LangGraph Features - Use-Case Documentation

## Overview

This document explains the advanced LangGraph features implemented in the `EnhancedLangGraphAgent`, which extends the basic linear workflow with production-ready patterns.

## Features Implemented

### 1. **Conditional Routing** (Branching Logic)

Conditional routing allows the graph to take different paths based on state values.

#### Pattern: `add_conditional_edges()`

```python
self.graph.add_conditional_edges(
    source_node="validate_parse",
    path_function=self._router_after_validation,
    mapping={
        "fetch": "fetch",      # → proceed to fetch
        "clarify": "clarify",  # → request clarification
    }
)
```

#### Implementation:

**Router Function:**
```python
def _router_after_validation(self, state: AgentState) -> Literal["fetch", "clarify"]:
    """Decide next node based on validation result."""
    validation_passed = state.get("_validation_passed", False)
    
    if validation_passed:
        return "fetch"  # Valid parse → fetch bids
    else:
        return "clarify"  # Invalid parse → clarify with user/LLM
```

#### Use Cases:
- ✅ Success vs. failure paths
- ✅ High-confidence vs. low-confidence routing
- ✅ Different processing based on input type
- ✅ Early termination for certain conditions

#### Real-World Example:
```
INPUT: "I need bids for the downtown project"
         ↓
    [parse] → project_id=None (no project code found)
         ↓
   [validate] → confidence=0.2 (too low)
         ↓
[conditional] → "clarify" path taken
         ↓
[clarify] → assign default project_id="UNKNOWN"
```

---

### 2. **Loops** (Retry Logic)

Loops allow nodes to execute multiple times until a condition is met.

#### Pattern: Conditional Edge Back to Previous Node

```python
self.graph.add_conditional_edges(
    source_node="fetch",
    path_function=self._router_after_fetch,
    mapping={
        "compare": "compare",  # Proceed to next stage
        "refetch": "refetch",  # Go back and retry with different params
    }
)

self.graph.add_edge("refetch", "compare")  # Loop back after refetch
```

#### Implementation:

**Fetch Node:**
```python
def _fetch_node(self, state: AgentState) -> dict:
    """Fetch bids and mark if refetch is needed."""
    bids = fetch_subcontractor_bids(...)
    fetch_attempts = state.get("_fetch_attempts", 0)
    
    needs_refetch = (
        len(bids) < self.min_bids and 
        fetch_attempts < self.max_retries
    )
    
    return {
        "bids": bids,
        "_fetch_attempts": fetch_attempts + 1,
        "_needs_refetch": needs_refetch,
    }
```

**Router Function:**
```python
def _router_after_fetch(self, state: AgentState) -> Literal["compare", "refetch"]:
    """Check if we need to retry."""
    if state.get("_needs_refetch", False):
        return "refetch"  # Retry
    else:
        return "compare"  # Proceed
```

**Refetch Node:**
```python
def _refetch_node(self, state: AgentState) -> dict:
    """Retry with expanded search parameters."""
    existing_bids = state.get("bids", [])
    new_bids = fetch_subcontractor_bids(...)  # Retry with different params
    
    return {
        "bids": existing_bids + new_bids,  # Merge results
        "_fetch_attempts": state.get("_fetch_attempts", 0) + 1,
    }
```

#### Loop Flow:
```
[fetch] → Found 1 bid (min_bids=2)
  ↓
[validate] → needs_refetch=True
  ↓
[refetch] → Found 2 more bids
  ↓
[validate] → needs_refetch=False (now have 3 bids)
  ↓
[compare] → Proceed
```

#### Use Cases:
- ✅ Retry with backoff
- ✅ Expand search if results insufficient
- ✅ Multi-pass validation
- ✅ Timeout/attempt limits
- ✅ Recursive decomposition

---

### 3. **Multi-Stage Validation**

Use multiple validation nodes throughout the graph, not just at the beginning.

#### Validation Points:

```
[parse] → [validate_parse] → [validate_comparison] → [format]
   ↓          ↓                    ↓
  parse    confidence check    result quality check
```

#### Implementation:

**First Validation (after parse):**
```python
def _validate_parse_node(self, state: AgentState) -> dict:
    """Validate parsing results with confidence score."""
    project_id = state.get("project_id")
    confidence = state.get("_parse_confidence", 0.0)
    
    validation_passed = project_id is not None and confidence > 0.5
    
    return {"_validation_passed": validation_passed}
```

**Second Validation (after comparison):**
```python
def _validate_comparison_node(self, state: AgentState) -> dict:
    """Validate that we have results to work with."""
    comparison = state.get("comparison", {})
    top_bids = comparison.get("top", [])
    
    is_valid = len(top_bids) > 0
    
    return {"_comparison_valid": is_valid}
```

#### Benefits:
- ✅ Fail fast on invalid intermediate results
- ✅ Prevent cascading errors
- ✅ Quality gates at each stage
- ✅ Observable state at decision points

---

### 4. **Fallback Mechanisms**

Graceful degradation when primary methods fail.

#### LLM Fallback to Regex:
```python
def _parse_with_llm(self, prompt: str) -> dict:
    """Try LLM first."""
    try:
        response = self.llm.invoke(extraction_prompt)
        return json.loads(response.content)
    except Exception as e:
        # Fall back to regex
        return self._parse_with_regex(prompt)
```

#### Clarification Node:
```python
def _clarify_node(self, state: AgentState) -> dict:
    """Handle parsing failures with more aggressive extraction."""
    project_id = state.get("project_id") or "UNKNOWN"
    scope = state.get("scope") or "general construction"
    
    return {
        "project_id": project_id,
        "scope": scope,
        "_validation_passed": True,  # Accept clarified values
    }
```

#### Formatting Fallback:
```python
def _format_node(self, state: AgentState) -> dict:
    """Try LLM, fallback to simple format."""
    if self.use_llm and self.llm:
        recommendation = self._format_with_llm(...)
    else:
        recommendation = self._format_default(...)
    
    return {"recommendation": recommendation}
```

#### Fallback Chain:
```
LLM Extraction
    ↓ (fails)
Regex Extraction
    ↓ (finds nothing)
Clarification Node (assigns defaults)
    ↓
Continue with processing
```

---

## Graph Architecture

### Linear vs. Enhanced Flow

#### Basic Flow (langgraph_agent.py):
```
START → parse → fetch → compare → format → END
```

#### Enhanced Flow (enhanced_langgraph_agent.py):
```
        ┌─→ fetch ─┐
        │          ├→ refetch (loop) ─┐
START → parse ─→ validate_parse       ├→ compare → validate_comparison → format → END
        └─→ clarify ────────────────┘
```

### Nodes

| Node | Purpose | Type | Returns |
|------|---------|------|---------|
| `parse` | Extract project_id, scope | Processing | `{project_id, scope, _parse_confidence}` |
| `validate_parse` | Check parse quality | Validation | `{_validation_passed}` |
| `clarify` | Handle parse failures | Fallback | `{project_id, scope}` |
| `fetch` | Fetch bids from API | Processing | `{bids, _fetch_attempts, _needs_refetch}` |
| `refetch` | Retry fetch with params | Processing | `{bids, _fetch_attempts}` |
| `compare` | Rank bids | Processing | `{comparison}` |
| `validate_comparison` | Check results quality | Validation | `{_comparison_valid}` |
| `format` | Create recommendation | Processing | `{recommendation}` |

### Routers

| Router | Source | Decision | Targets |
|--------|--------|----------|---------|
| `_router_after_validation` | `validate_parse` | Parse valid? | `fetch` or `clarify` |
| `_router_after_fetch` | `fetch` | Enough bids? | `compare` or `refetch` |

---

## Advanced Features Summary

### What This Demonstrates

✅ **Conditional Routing**: Multiple execution paths based on state  
✅ **Loops**: Retry logic with attempt counting  
✅ **Multi-Stage Validation**: Quality gates throughout graph  
✅ **Fallback Mechanisms**: Graceful degradation  
✅ **State Management**: Tracking confidence, attempts, validation flags  
✅ **Error Recovery**: Clarification node for handling failures  
✅ **Adaptive Behavior**: Different strategies based on input quality  

### LangGraph Concepts Used

| Concept | Method | Purpose |
|---------|--------|---------|
| **Conditional Edges** | `add_conditional_edges()` | Branch based on router function |
| **Router Functions** | Return Literal["path1", "path2"] | Decide next node |
| **State Reducers** | TypedDict merging | Accumulate state updates |
| **Explicit Edges** | `add_edge()` | Linear transitions |
| **Subgraphs** | (Not used, but can be) | Modular graph composition |

---

## Real-World Application

### Use Case: Procurement Assistant

**Scenario**: Project manager submits ambiguous request
```
"Get me the cheapest bids for our new project"
```

**Flow with conditional routing & loops:**

1. **Parse Phase**: Try to extract project_id
   - ❌ Fails: No project code in text
   - Confidence: 0.3

2. **Validation**: Check confidence threshold
   - Result: validation_passed = False
   - Route: → `clarify`

3. **Clarification**: Assign default project
   - project_id = "UNKNOWN"
   - scope = "general construction"

4. **Fetch Phase**: Get bids
   - Found: 1 bid (below min_bids threshold)
   - Route: → `refetch`

5. **Refetch Phase**: Retry with expanded params
   - Found: 2 more bids
   - Total: 3 bids (meets threshold)

6. **Comparison Phase**: Rank results
   - Top bid selected

7. **Validation**: Check results exist
   - ✅ Passed

8. **Format**: Create recommendation
   - Return professional recommendation

---

## Testing Advanced Features

```python
# Test conditional routing
agent = EnhancedLangGraphAgent(use_llm=False)

# This should trigger clarify path (no project code)
result = agent.run("I need excavation services")

# This should trigger refetch loop if min_bids is high
result = agent.run("Get bids for P-123")

# This should go straight through (valid input)
result = agent.run("Get bids for foundation works on project P-2025")
```

---

## Extension Points

### Add More Validation Stages
```python
def _validate_before_format(self, state: AgentState) -> dict:
    """Extra validation before formatting."""
    bids = state.get("bids", [])
    return {"_has_bids": len(bids) > 0}
```

### Add Sub-Paths
```python
self.graph.add_conditional_edges(
    "validate_comparison",
    self._router_quality_check,
    {
        "high_quality": "format",
        "low_quality": "refetch",  # Retry entire flow
        "no_results": "error_handler",  # New node
    }
)
```

### Add Parallel Processing
```python
# LangGraph supports subgraphs (not implemented here)
# Could parallelize multiple fetch attempts
```

---

## Conclusion

The `EnhancedLangGraphAgent` demonstrates production-ready LangGraph patterns:

1. **Conditional routing** for intelligent branching
2. **Loops** for retry logic with limits
3. **Multi-stage validation** for quality gates
4. **Fallback mechanisms** for graceful degradation
5. **State tracking** for observability

These patterns enable building robust, maintainable agents that handle real-world complexity.
