# Cosuno Use-Case: LangGraph-Based Procurement Assistant

This document explains the real-world use-case for the scaffold and how it connects to Cosuno's platform.

## Use-Case Summary

**Goal**: Build an agent that helps a project manager (PM) quickly fetch subcontractor bids, compare options, and get a recommendation.

**Why Cosuno**: Cosuno specializes in procurement and subcontractor management. This scaffold demonstrates how an LLM-powered agent can:
- Parse procurement requests (extract project ID, scope, quantity)
- Call procurement APIs (fetch available bids)
- Aggregate and rank options (lowest cost, fastest delivery, best fit)
- Present recommendations in human-readable format

## The Agent Flow

Our `LangGraphAgent` implements a simple but realistic procurement workflow:

```
START
  ↓
[parse] — Extract project_id and scope from user prompt
  ↓
[fetch] — Call fetch_subcontractor_bids(project_id) to get available bids
  ↓
[compare] — Rank bids by price, compute averages
  ↓
[format] — Create recommendation text with top N bids
  ↓
END
```

Each step is a **LangGraph node** that accepts state and returns updated state.

## Implementation Details

**State definition** (in real use, would be TypedDict):
```python
{
    "prompt": str,
    "project_id": str | None,
    "scope": str | None,
    "bids": list[dict],
    "comparison": dict,
    "recommendation": str
}
```

**Nodes**:
- `_parse_node`: uses regex to extract `project_id` (e.g., "P-123") and `scope` from free-form text
- `_fetch_node`: calls `fetch_subcontractor_bids(prompt, project_id)` mock tool
- `_compare_node`: calls `compare_bids(bids, top_n)` mock tool
- `_format_node`: generates recommendation text

**Tools** (mocked, but show real patterns):
- `fetch_subcontractor_bids(prompt, project_id, api_key)` — returns list of bids with price, lead time, subcontractor name
- `compare_bids(bids, top_n)` — returns sorted list and average price

## Example Interaction

**User prompt**:
```
Get subcontractor bids for foundation works on project P-123 and recommend the best two.
```

**Agent process**:
1. Parse: Extract `project_id="P-123"`, `scope="foundation works"`
2. Fetch: Call mock API, get 3 bids (deterministic by project_id)
3. Compare: Sort by price, pick top 2
4. Format: Create recommendation with subcontractor names, prices, lead times

**Output**:
```
Recommendation (top 2):
  • Builders Co. — $9,512 — 10d lead time
  • ACME Excavation — $10,010 — 7d lead time

(source: mock-cosuno)
```

## Session Exercise

During the 90-minute session, you will:

1. **Add a new node** (e.g., `estimate_labor_cost`) that computes labor hours based on scope
2. **Insert it into the graph** between existing nodes
3. **Wire edges** properly (update transitions)
4. **Write tests** for the new node
5. **Run `pytest`** to validate

This teaches the core LangGraph pattern: add node → define its function → add edges → test → compile → invoke.

## Swapping Mock Tools for Real APIs

The mock tools (`fetch_subcontractor_bids`, `compare_bids`) are **deterministic** and don't require credentials. To use real Cosuno APIs:

1. Get API credentials (API key, base URL) from Cosuno
2. Create a new module with real HTTP clients:
   ```python
   import httpx
   
   async def fetch_subcontractor_bids_real(project_id, api_key):
       async with httpx.AsyncClient() as client:
           resp = await client.get(
               f"https://api.cosuno.com/projects/{project_id}/bids",
               headers={"Authorization": f"Bearer {api_key}"}
           )
       return resp.json()
   ```
3. Inject via constructor or environment variables (never hardcode)
4. Keep the same function signature so tests can mock it

## Real LangGraph Enhancements

Our scaffold uses **real `langgraph`**, so you can easily add:

1. **LLM node** — call ChatGPT/Claude to refine recommendations:
   ```python
   def llm_node(state):
       llm = ChatOpenAI(model="gpt-4")
       msg = llm.invoke([{"role": "user", "content": state["bids_summary"]}])
       return {"llm_response": msg.content}
   ```

2. **Conditional branching** — route based on cost threshold:
   ```python
   def should_negotiate(state):
       avg = state["comparison"]["average_price"]
       return "negotiate" if avg > THRESHOLD else "accept"
   
   graph.add_conditional_edges("compare", should_negotiate)
   ```

3. **Tool calling** — let LLM decide which tools to use (agent loop)
4. **Streaming** — return results as they're computed (`.stream()`)

## Quick Commands

```bash
# Install and run tests
uv sync
uv run pytest -q

# View full test output
pytest -v

# Run only Cosuno tests
pytest -k "cosuno" -v
```

## Next Steps

1. Run the current scaffold: `uv sync && pytest -q` (all pass ✓)
2. Review `src/construction_assistant/langgraph_agent.py` — see how StateGraph and nodes work
3. Review `src/construction_assistant/tests/test_langgraph_agent.py` — see test patterns
4. During the session: add a new node, add tests, run `pytest`
5. After: integrate with real Cosuno API using the patterns shown above
