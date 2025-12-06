# LangGraph Patterns & Concepts

This document explains key LangGraph concepts and how they're used in this project. For the live 90-minute session, focus on **State**, **Nodes**, and **Edges**.

## Official Resources
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **GitHub Repo**: https://github.com/langchain-ai/langgraph
- **Python SDK**: `pip install langgraph`

## Core Concepts

### 1. **State** — Shared Data Across Nodes

In LangGraph, all nodes share and update a single state object.

**Real LangGraph** (using TypedDict):
```python
from typing_extensions import TypedDict

class AgentState(TypedDict):
    prompt: str
    project_id: str | None
    bids: list[dict]
    recommendation: str
```

**In this project** (simplified):
```python
state = {
    "prompt": "Get bids for foundation works on project P-123",
    "project_id": "P-123",
    "bids": [...],
    "recommendation": "..."
}
```

### 2. **Nodes** — Functions That Transform State

A node is a function that:
- **Takes** the current state dict as input
- **Returns** an updated state dict (updates are merged)

**Real LangGraph pattern**:
```python
def parse_node(state: AgentState) -> AgentState:
    prompt = state["prompt"]
    project_id = extract_project_id(prompt)
    return {"project_id": project_id}  # merges with existing state
```

**In this project** (`LangGraphAgent._parse_node`):
```python
def _parse_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
    prompt = state.get("prompt", "")
    project_id = extract_from_prompt(prompt)
    return {"project_id": project_id}
```

### 3. **Edges** — Node Transitions

Edges define how the graph flows from one node to another.

```python
graph.add_edge("parse", "fetch")      # after parse, go to fetch
graph.add_edge("fetch", "compare")    # after fetch, go to compare
graph.add_edge("compare", "format")   # after compare, go to format
```

### 4. **StateGraph** — Graph Container

Combines all nodes and edges into a single executable graph.

```python
from langgraph.graph import StateGraph

graph = StateGraph(AgentState)
graph.add_node("parse", parse_node)
graph.add_node("fetch", fetch_node)
graph.add_node("compare", compare_node)
graph.add_node("format", format_node)

graph.add_edge("parse", "fetch")
graph.add_edge("fetch", "compare")
graph.add_edge("compare", "format")
```

### 5. **Compile & Invoke** — Execution

Before running, compile the graph. Then invoke it with initial state.

```python
compiled_graph = graph.compile()
result = compiled_graph.invoke({"prompt": "..."})
```

## Our Implementation

### Project Structure
```
src/construction_assistant/
├── langgraph_adapter.py      # fallback StateGraph (if langgraph not installed)
├── langgraph_agent.py        # LangGraphAgent using the adapter
├── agent.py                  # mock tools (fetch_subcontractor_bids, compare_bids)
└── tests/
    └── test_langgraph_agent.py
```

### LangGraphAgent Walkthrough

The `LangGraphAgent` class demonstrates the real LangGraph pattern:

1. **Define nodes** as methods:
   - `_parse_node`: extract project_id and scope from prompt
   - `_fetch_node`: call `fetch_subcontractor_bids` tool
   - `_compare_node`: rank bids via `compare_bids` tool
   - `_format_node`: produce human-readable recommendation

2. **Build the graph**:
   ```python
   graph = StateGraph()
   graph.add_node("parse", self._parse_node)
   graph.add_node("fetch", self._fetch_node)
   graph.add_node("compare", self._compare_node)
   graph.add_node("format", self._format_node)
   
   graph.add_edge("parse", "fetch")
   graph.add_edge("fetch", "compare")
   graph.add_edge("compare", "format")
   ```

3. **Compile and run**:
   ```python
   compiled_graph = graph.compile()
   state = compiled_graph.invoke({"prompt": "..."})
   ```

## Tool Use Pattern in LangGraph

Tools (like `fetch_subcontractor_bids`, `compare_bids`) are called **within nodes**, not at the graph level. This is the standard LangGraph pattern:

```python
def fetch_node(state: AgentState) -> AgentState:
    # Inside a node, call a tool
    bids = fetch_subcontractor_bids(
        state["prompt"],
        project_id=state.get("project_id"),
        api_key=self.api_key
    )
    # Return updated state
    return {"bids": bids}
```

In the live session, you can:
1. Add a new tool (e.g., `estimate_labor_cost`)
2. Create a new node that calls it
3. Insert it into the graph between existing nodes
4. Write tests for the new node
5. Run `pytest` to validate

## Real LangGraph vs. Adapter

| Feature | Real LangGraph | Our Adapter |
|---------|---|---|
| Type safety | TypedDict / Pydantic | Plain dict |
| Conditional edges | `add_conditional_edges()` | Only sequential edges |
| Streaming | `stream()` method | `invoke()` only |
| LLM integration | Built-in with langchain | Manual |
| Tool calling | via `tool_choice` | Manual function calls |
| State mutation | Merge updates | Merge updates |

## Next Steps for the Interview

1. **Install real LangGraph** (in Codespaces):
   ```bash
   pip install langgraph langchain
   ```

2. **Swap the adapter**:
   - Replace imports of `langgraph_adapter.StateGraph` with `langgraph.graph.StateGraph`
   - Use `TypedDict` for state schema
   - Everything else stays the same

3. **Add an LLM node** (optional, requires API key):
   ```python
   from langchain_openai import ChatOpenAI
   
   def llm_node(state: AgentState) -> AgentState:
       llm = ChatOpenAI(model="gpt-4")
       response = llm.invoke([{"role": "user", "content": state["prompt"]}])
       return {"response": response}
   ```

4. **Practice during the 90-minute session**:
   - Walk through building the graph step-by-step
   - Add a new node (e.g., schedule planning)
   - Write tests with `pytest`
   - Discuss swapping mock tools for real APIs
