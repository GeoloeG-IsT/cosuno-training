"""A LangGraph-backed agent implementation for the Cosuno use-case.

This agent builds a StateGraph with nodes for parsing input, fetching bids,
comparing them, and formatting output.

Uses the real `langgraph` library from LangChain.
"""
try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    raise ImportError(
        "langgraph is required. Install it with: pip install langgraph"
    )

from .agent import fetch_subcontractor_bids, compare_bids
from .schema import AgentState


class LangGraphAgent:
    """Constructs a StateGraph-based agent for Cosuno procurement flows.

    This agent demonstrates the key LangGraph pattern:
    1. Define state schema (AgentState TypedDict)
    2. Add nodes (functions that take state and return dict with updated fields)
    3. Add edges (transitions between nodes)
    4. Compile and invoke with initial state
    """

    def __init__(self, api_key: str | None = None, top_n: int = 1):
        self.api_key = api_key
        self.top_n = top_n
        self.graph = StateGraph(AgentState)
        self.compiled_graph = None

    def _parse_node(self, state: AgentState) -> AgentState:
        """Parse node: extract project_id and scope from prompt."""
        import re

        prompt = state.get("prompt", "")
        # look for project id like P-123
        m = re.search(r"\b([A-Z]-?\d+)\b", prompt)
        project_id = m.group(1) if m else None
        # scope: first noun after 'for'
        scope = None
        m2 = re.search(r"for ([a-zA-Z ]+?)(?: on | for |$)", prompt.lower())
        if m2:
            scope = m2.group(1).strip()
        return {"project_id": project_id, "scope": scope}

    def _fetch_node(self, state: AgentState) -> AgentState:
        """Tool node: call fetch_subcontractor_bids with project context."""
        prompt = state.get("prompt", "")
        project_id = state.get("project_id")
        bids_result = fetch_subcontractor_bids(prompt, project_id=project_id, api_key=self.api_key)
        return {"bids": bids_result.get("bids", [])}

    def _compare_node(self, state: AgentState) -> AgentState:
        """Analysis node: compare bids and select top candidates."""
        bids = state.get("bids", [])
        compare_result = compare_bids(bids, top_n=self.top_n)
        return {"comparison": compare_result}

    def _format_node(self, state: AgentState) -> AgentState:
        """Output node: format recommendation text."""
        comparison = state.get("comparison", {})
        top = comparison.get("top", [])
        lines = [f"Recommendation (top {len(top)}):"]
        for bid in top:
            subcontractor = bid.get("subcontractor", "Unknown")
            price = bid.get("price", 0)
            lead_days = bid.get("lead_time_days", "?")
            lines.append(f"  • {subcontractor} — ${price:,} — {lead_days}d lead time")
        lines.append("\n(source: mock-cosuno)")
        recommendation_text = "\n".join(lines)
        return {"recommendation": recommendation_text}

    def build_graph(self):
        """Build the StateGraph with nodes and edges."""
        # Add nodes
        self.graph.add_node("parse", self._parse_node)
        self.graph.add_node("fetch", self._fetch_node)
        self.graph.add_node("compare", self._compare_node)
        self.graph.add_node("format", self._format_node)

        # Add edges: START -> parse -> fetch -> compare -> format -> END
        self.graph.add_edge(START, "parse")
        self.graph.add_edge("parse", "fetch")
        self.graph.add_edge("fetch", "compare")
        self.graph.add_edge("compare", "format")
        self.graph.add_edge("format", END)

        # Compile for execution
        self.compiled_graph = self.graph.compile()

    def run(self, prompt: str) -> AgentState:
        """Execute the agent: invoke the compiled graph with initial state."""
        if self.compiled_graph is None:
            self.build_graph()

        initial_state: AgentState = {
            "prompt": prompt,
            "project_id": None,
            "scope": None,
            "bids": [],
            "comparison": {},
            "recommendation": "",
        }
        final_state = self.compiled_graph.invoke(initial_state)

        return {
            "prompt": final_state.get("prompt", prompt),
            "project_id": final_state.get("project_id"),
            "scope": final_state.get("scope"),
            "bids": final_state.get("bids", []),
            "comparison": final_state.get("comparison", {}),
            "recommendation": final_state.get("recommendation"),
        }
