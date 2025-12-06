# LangGraph StateGraph Node Return Patterns

## 🎯 The Official Answer

**Node functions should return only the updated fields as a dict (partial update), NOT the complete state.**

This is the **official pattern** from LangGraph's StateGraph documentation and implementation.

---

## Official Documentation

### From `StateGraph` Help:
```
The signature of each node is `State -> Partial<State>`.
```

**Key Quote from LangGraph Source:**
> The signature of each node is `State -> Partial<State>`.
> Each state key can optionally be annotated with a reducer function that
> will be used to aggregate the values of that key received from multiple nodes.

This explicitly states that nodes should return **`Partial<State>`** (partial updates), not the full state.

---

## Pattern 1: Partial Update (✅ CORRECT)

Node functions return **only the fields they're updating**. LangGraph automatically merges these updates with the existing state.

### Implementation

```python
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

class AgentState(TypedDict):
    """Complete state schema."""
    prompt: str
    project_id: str | None
    scope: str | None
    bids: list
    recommendation: str

def parse_node(state: AgentState) -> dict:
    """Extract project info from prompt.
    
    Only returns the fields being UPDATED.
    Other state fields are preserved automatically.
    """
    prompt = state["prompt"]
    # ... extraction logic ...
    return {
        "project_id": "P-123",
        "scope": "foundation"
    }
    # Note: NOT returning prompt, bids, recommendation
    # They're already in state and will be preserved

def fetch_node(state: AgentState) -> dict:
    """Fetch bids for the project.
    
    Only returns the fields being UPDATED.
    """
    project_id = state["project_id"]
    bids = fetch_bids(project_id)
    return {
        "bids": bids
    }
    # Note: project_id, scope, prompt, recommendation are unchanged

def format_node(state: AgentState) -> dict:
    """Format final recommendation.
    
    Only returns the fields being UPDATED.
    """
    bids = state["bids"]
    recommendation = format_recommendation(bids)
    return {
        "recommendation": recommendation
    }
    # Note: All other fields (prompt, project_id, bids, scope) preserved
```

### State Flow Example

```
Initial State:
{
    "prompt": "Get bids for P-123",
    "project_id": None,
    "scope": None,
    "bids": [],
    "recommendation": ""
}
    ↓
parse_node returns: {"project_id": "P-123", "scope": "foundation"}
    ↓
State after parse (merged):
{
    "prompt": "Get bids for P-123",  ← preserved
    "project_id": "P-123",            ← updated
    "scope": "foundation",            ← updated
    "bids": [],                       ← preserved
    "recommendation": ""              ← preserved
}
    ↓
fetch_node returns: {"bids": [...]}
    ↓
State after fetch (merged):
{
    "prompt": "Get bids for P-123",  ← preserved
    "project_id": "P-123",            ← preserved
    "scope": "foundation",            ← preserved
    "bids": [bid1, bid2, bid3],       ← updated
    "recommendation": ""              ← preserved
}
    ↓
format_node returns: {"recommendation": "..."}
    ↓
Final State (merged):
{
    "prompt": "Get bids for P-123",  ← preserved
    "project_id": "P-123",            ← preserved
    "scope": "foundation",            ← preserved
    "bids": [bid1, bid2, bid3],       ← preserved
    "recommendation": "Choose contractor X"  ← updated
}
```

### Key Benefits

1. **Clarity**: Each node's intent is clear (only shows what it changes)
2. **Correctness**: Automatic state merging prevents bugs
3. **Flexibility**: Other nodes don't need to know about all state fields
4. **Composability**: Easy to add new nodes without breaking existing ones

---

## Pattern 2: Full State (❌ INCORRECT, BUT WORKS)

Returning the complete updated state also works in LangGraph because it uses a merge operation, but **this pattern is NOT recommended** and not documented as the official pattern.

### Why It Works (But Shouldn't Be Used)

```python
def parse_node_full(state: AgentState) -> AgentState:
    """ANTIPATTERN: Returning full state."""
    prompt = state["prompt"]
    project_id = extract_project_id(prompt)
    
    # Return COMPLETE state (all fields)
    return {
        "prompt": state["prompt"],        # copied unchanged
        "project_id": project_id,         # modified
        "scope": None,                    # copied unchanged
        "bids": state["bids"],            # copied unchanged
        "recommendation": state["recommendation"]  # copied unchanged
    }
```

### Why This Pattern Is Bad

1. **Redundant**: You're copying fields you're not changing
2. **Error-prone**: Easy to forget a field and lose data
3. **Coupling**: You must know all state fields in every node
4. **Maintainability**: Adding new state fields requires updating all nodes
5. **Against LangGraph Design**: Contradicts the documented `State -> Partial<State>` signature

---

## Real-World Code Example from This Project

### ✅ Correct Implementation (From `langgraph_agent.py`)

```python
def _parse_node(self, state: AgentState) -> AgentState:
    """Parse node: extract project_id and scope from prompt."""
    prompt = state.get("prompt", "")
    
    if self.use_llm and self.llm:
        parsed = self._parse_with_llm(prompt)
    else:
        parsed = self._parse_with_regex(prompt)
    
    # ONLY return the fields being updated
    return {
        "project_id": parsed.get("project_id"),
        "scope": parsed.get("scope")
    }
    # NOT returning: prompt, bids, comparison, recommendation
    # They're already in state and will be preserved

def _fetch_node(self, state: AgentState) -> AgentState:
    """Tool node: call fetch_subcontractor_bids with project context."""
    prompt = state.get("prompt", "")
    project_id = state.get("project_id")
    bids_result = fetch_subcontractor_bids(
        prompt, 
        project_id=project_id, 
        api_key=self.api_key
    )
    
    # ONLY return the field being updated
    return {"bids": bids_result.get("bids", [])}
    # NOT returning: prompt, project_id, scope, comparison, recommendation

def _compare_node(self, state: AgentState) -> AgentState:
    """Analysis node: compare bids and select top candidates."""
    bids = state.get("bids", [])
    compare_result = compare_bids(bids, top_n=self.top_n)
    
    # ONLY return the field being updated
    return {"comparison": compare_result}
    # NOT returning: prompt, project_id, scope, bids, recommendation

def _format_node(self, state: AgentState) -> AgentState:
    """Output node: format a professional recommendation."""
    comparison = state.get("comparison", {})
    top = comparison.get("top", [])
    project_id = state.get("project_id", "Unknown")
    scope = state.get("scope", "construction works")
    
    # ... formatting logic ...
    
    # ONLY return the field being updated
    return {"recommendation": recommendation_text}
    # NOT returning: prompt, project_id, scope, bids, comparison
```

### Why This Works

✅ **Each node returns only what it modifies**
✅ **Other state fields are automatically preserved**
✅ **Follows LangGraph's documented pattern**
✅ **Clear, maintainable code**
✅ **Easy to extend with new nodes**

---

## Comparison Table

| Aspect | Partial Return ✅ | Full Return ❌ |
|--------|------------------|-----------------|
| **Pattern** | `State -> Partial<State>` | `State -> State` |
| **Fields Returned** | Only modified ones | All state fields |
| **LangGraph Recommendation** | ✅ Official pattern | ❌ Not documented |
| **Merging** | Automatic | Works but redundant |
| **Maintainability** | ✅ High | ❌ Low |
| **Error Prone** | ❌ Low | ✅ High (easy to miss fields) |
| **Composability** | ✅ Easy to add nodes | ❌ Must update all nodes |
| **Code Clarity** | ✅ Shows intent | ❌ Noisy with copies |
| **Example Return** | `{"project_id": "P-123"}` | `{"prompt": "...", "project_id": "P-123", "scope": None, ...}` |

---

## LangGraph Reducer Pattern

For more advanced state management, LangGraph supports **reducer functions** on specific state fields. This allows custom merge logic:

```python
from typing_extensions import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END

def append_to_list(current: list, new_value: int | None) -> list:
    """Reducer: append values to a list."""
    if new_value is not None:
        return current + [new_value]
    return current

class State(TypedDict):
    # Without reducer: normal merge (last value wins)
    name: str
    
    # With reducer: custom merge logic (append to list)
    scores: Annotated[list[int], append_to_list]

def node_a(state: State) -> dict:
    return {"scores": 100}  # Will be appended, not replaced

def node_b(state: State) -> dict:
    return {"scores": 95}   # Will be appended, not replaced

graph = StateGraph(State)
graph.add_node("A", node_a)
graph.add_node("B", node_b)
graph.add_edge(START, "A")
graph.add_edge("A", "B")
graph.add_edge("B", END)
compiled = graph.compile()

result = compiled.invoke({"name": "Test", "scores": []})
# Result: {"name": "Test", "scores": [100, 95]}
# Reducer combined both values instead of overwriting
```

---

## Official LangGraph Example (From Documentation)

```python
def reducer(a: list, b: int | None) -> list:
    if b is not None:
        return a + [b]
    return a

class State(TypedDict):
    x: Annotated[list, reducer]

def node(state: State, runtime: Runtime[Context]) -> dict:
    r = runtime.context.get("r", 1.0)
    x = state["x"][-1]
    next_value = x * r * (1 - x)
    return {"x": next_value}  # ← PARTIAL UPDATE: only returning x field
    # NOT returning the full state

graph = StateGraph(state_schema=State, context_schema=Context)
graph.add_node("A", node)
graph.set_entry_point("A")
graph.set_finish_point("A")
compiled = graph.compile()

step1 = compiled.invoke({"x": 0.5}, context={"r": 3.0})
# Result: {'x': [0.5, 0.75]}
# The reducer was applied: [0.5] + [0.75] = [0.5, 0.75]
```

---

## Summary & Best Practices

### ✅ DO

1. **Return partial updates**: Only return dict keys you're actually modifying
2. **Rely on LangGraph merging**: Let the framework handle combining updates
3. **Keep nodes focused**: Each node should do one thing and update one or a few fields
4. **Use reducers for custom logic**: For complex merge behavior, define reducers in state schema
5. **Follow the pattern**: `State -> Partial<State>` is the documented, tested, proven pattern

### ❌ DON'T

1. **Don't return the full state**: Avoid copying unchanged fields
2. **Don't couple nodes**: Don't make nodes depend on knowing all state fields
3. **Don't recreate the full state**: Let LangGraph handle state management
4. **Don't deviate from the pattern**: The partial update pattern is battle-tested

---

## Testing the Pattern

```python
def test_node_returns_partial_update():
    """Verify nodes return only modified fields."""
    state: AgentState = {
        "prompt": "Original",
        "project_id": None,
        "scope": None,
        "bids": [],
        "recommendation": ""
    }
    
    agent = LangGraphAgent()
    result = agent._parse_node(state)
    
    # Node only returns what it modifies
    assert "project_id" in result
    assert "scope" in result
    assert "prompt" not in result  # Not in return value
    assert "bids" not in result     # Not in return value
    assert len(result) == 2         # Only 2 fields returned
```

---

## Conclusion

**LangGraph StateGraph node functions should return only the updated fields as a dict (partial update).** This is:

- ✅ The official documented pattern (`State -> Partial<State>`)
- ✅ How the framework is designed to work
- ✅ Best practice for maintainability and composability
- ✅ Implemented correctly in this project (`langgraph_agent.py`)

Returning the full state works but is an antipattern that goes against the framework's design and makes code harder to maintain.
