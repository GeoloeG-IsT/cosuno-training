## Usage & Workshop Notes

This document explains setup, key concepts, and how to run tests for the 90-minute live coding session.

**Prerequisites**
- GitHub account and Codespaces (recommended for the live session)
- Python 3.11+ (automatically available in Codespaces)
- `uv` package manager (or use `pip` as fallback)

**Quick start with `uv` (recommended)**

1. Clone/open the repo in Codespaces
2. Install dependencies and set up environment:
   ```bash
   uv sync
   ```
3. Run all tests:
   ```bash
   uv run pytest -q
   ```
4. Or activate venv and run manually:
   ```bash
   source .venv/bin/activate
   pytest -q
   ```

**Alternative: with `pip` + venv**

```bash
python -m venv .venv
source .venv/bin/activate
pip install langgraph pytest
pytest -q
```

**About `uv`**

`uv` is a fast Python package installer and resolver. Key commands for this project:

- `uv sync` — install all dependencies from `pyproject.toml` into `.venv`
- `uv run pytest -q` — run pytest using the managed environment (no activation needed)
- `uv add <package>` — add a new dependency to the project
- `uv lock` — update lockfile if you modify `pyproject.toml`

For more: https://docs.astral.sh/uv/

**LangGraph (conceptual primer)**

This project uses the **real `langgraph` library** from LangChain. Key concepts:

- **StateGraph**: container for nodes and edges that defines an agent's flow
- **Nodes**: Python functions that accept state and return updated state
- **Edges**: connections between nodes; must include `START` → first node and last node → `END`
- **State**: shared dict (or TypedDict) passed through all nodes
- **Tools**: external callables invoked from within nodes (not at graph level)
- **Compilation**: `.compile()` prepares the graph for execution

Example flow:
```
START -> parse_node -> fetch_node -> compare_node -> format_node -> END
```

In this project: `src/construction_assistant/langgraph_agent.py` shows the pattern.

**Real LangGraph vs. simplified adapter**

Early versions used a lightweight fallback adapter (`langgraph_adapter.py`). The current version uses the **real `langgraph` package** so you practice with the actual library. This means:

- You learn real LangGraph APIs (StateGraph, START, END, .compile(), .invoke())
- Easier to swap demo code into production LangGraph workflows
- Full compatibility with LangChain tools and LLMs

**pytest tips**

```bash
# Run all tests
pytest -q

# Run specific test file
pytest -q src/construction_assistant/tests/test_langgraph_agent.py

# Run tests matching a pattern
pytest -k "langgraph" -q

# Verbose output
pytest -v
```

**90-minute session plan (suggested)**

| Time | Topic |
|------|-------|
| 0–10 min | Introductions & environment check (Codespaces, GitHub, `uv sync`) |
| 10–25 min | Walk through scaffold: files, LangGraph StateGraph, mock tools |
| 25–55 min | **Live-coding**: add a new node (e.g., `estimate_labor_cost`), wire it into the graph, update edges |
| 55–75 min | **Live-coding**: add tests for the new node, run `pytest` |
| 75–85 min | Discuss: how to swap mock tools for real APIs, handle credentials with env vars |
| 85–90 min | Q&A and next steps (real Cosuno integration, LLM nodes, streaming) |

**Key files to review before the session**

- `README.md` — quick overview
- `pyproject.toml` — dependencies and pytest config
- `src/construction_assistant/langgraph_agent.py` — the real LangGraph implementation
- `src/construction_assistant/agent.py` — mock tools (deterministic for testing)
- `src/construction_assistant/tests/test_langgraph_agent.py` — example tests
- `docs/LANGGRAPH_PATTERNS.md` — detailed LangGraph reference
