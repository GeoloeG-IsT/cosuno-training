# cosuno-training

This repository contains a complete scaffold for a 90-minute live-coding interview exercise: a **construction project assistant** built with **LangGraph** (real library), featuring tools for procurement and bidding. Perfect for practicing LangGraph concepts, `uv` package management, and `pytest`.

**What's included**
- **Real LangGraph agent** (`src/construction_assistant/langgraph_agent.py`) — uses actual `langgraph.graph.StateGraph`
- **Mock tools** (`src/construction_assistant/agent.py`) — deterministic `fetch_subcontractor_bids`, `compare_bids` for testing without API calls
- **Full test suite** (`src/construction_assistant/tests/`) — 6 passing tests with `pytest`
- **Comprehensive docs** — LangGraph patterns, uv workflow, and Cosuno use-case walkthrough
- **Modern `pyproject.toml`** — PEP 518 format with uv/pytest config built-in

**Quick start**
```bash
# Install with uv
uv sync

# Run all tests
uv run pytest -q

# Or activate venv and run directly
source .venv/bin/activate
pytest -q
```

See `docs/USAGE.md` for the 90-minute session plan, `docs/LANGGRAPH_PATTERNS.md` for LangGraph deep-dive, and `docs/COSUNO_USECASE.md` for domain context.
