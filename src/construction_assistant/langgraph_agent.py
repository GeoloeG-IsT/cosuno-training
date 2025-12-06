"""A LangGraph-backed agent implementation for the Cosuno use-case.

This agent builds a StateGraph with nodes for parsing input, fetching bids,
comparing them, and formatting output.

Uses the real `langgraph` library from LangChain and Google Gemini for LLM tasks.
"""
import json
import logging
import os
import re
from typing import Any
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    raise ImportError(
        "langgraph is required. Install it with: pip install langgraph"
    )

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    raise ImportError(
        "langchain-google-genai is required. Install it with: pip install langchain-google-genai"
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

    Uses Google Gemini LLM for intelligent parsing and formatting.
    """

    def __init__(
        self,
        api_key: str | None = None,
        top_n: int = 1,
        gemini_api_key: str | None = None,
        use_llm: bool = True,
    ):
        """Initialize the LangGraph agent.
        
        Args:
            api_key: Optional API key for tools (e.g., Cosuno API)
            top_n: Number of top bids to return
            gemini_api_key: Optional Gemini API key (falls back to GOOGLE_API_KEY env var)
            use_llm: If False, use regex-based parsing instead of LLM (useful for demos/testing)
        """
        self.api_key = api_key
        self.top_n = top_n
        self.graph = StateGraph(AgentState)
        self.compiled_graph = None
        self.use_llm = use_llm
        self.llm = None
        
        # Try to initialize Gemini LLM if requested
        if use_llm:
            api_key_to_use = gemini_api_key or os.getenv("GOOGLE_API_KEY")
            if api_key_to_use:
                try:
                    self.llm = ChatGoogleGenerativeAI(
                        model="gemini-3-pro-preview",
                        google_api_key=api_key_to_use,
                        temperature=0.3
                    )
                    logger.info("✅ Gemini LLM initialized successfully")
                except Exception as e:
                    logger.warning(f"Failed to initialize Gemini LLM: {e}. Falling back to regex parsing.")
                    self.use_llm = False
            else:
                logger.info("No GOOGLE_API_KEY found. Using regex-based parsing for demo mode.")
                self.use_llm = False

    def _parse_with_llm(self, prompt: str) -> dict[str, Any]:
        """Use LLM to intelligently extract project_id and scope."""
        extraction_prompt = f"""Extract the following information from the user request:
1. project_id: A project identifier (e.g., P-123, Project-456, or null if not found)
2. scope: The scope of work (e.g., "foundation works", "excavation", etc.)

User request: {prompt}

Respond ONLY with valid JSON (no markdown, no extra text):
{{"project_id": <string or null>, "scope": <string or null>}}"""

        try:
            response = self.llm.invoke(extraction_prompt)
            parsed = json.loads(response.content)
            logger.debug(f"LLM parsed: {parsed}")
            return parsed
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"LLM parsing failed: {e}. Falling back to regex.")
            return self._parse_with_regex(prompt)

    def _parse_with_regex(self, prompt: str) -> dict[str, Any]:
        """Fallback regex-based extraction for project_id and scope."""
        # Extract project_id (patterns like P-123, PROJECT-456, ABC-789)
        project_match = re.search(r'([A-Z]+[-]?\d+|P[-]?\d+)', prompt.upper())
        project_id = project_match.group(1) if project_match else None
        
        # Extract scope (common construction terms)
        scope_keywords = [
            "foundation",
            "excavation",
            "electrical",
            "plumbing",
            "roofing",
            "site clearing",
            "HVAC",
        ]
        scope = None
        for keyword in scope_keywords:
            if keyword.lower() in prompt.lower():
                scope = keyword
                break
        
        logger.debug(f"Regex parsed: project_id={project_id}, scope={scope}")
        return {"project_id": project_id, "scope": scope}

    def _parse_node(self, state: AgentState) -> AgentState:
        """Parse node: extract project_id and scope from prompt.
        
        Uses LLM if available, otherwise falls back to regex extraction.
        """
        prompt = state.get("prompt", "")
        
        if self.use_llm and self.llm:
            parsed = self._parse_with_llm(prompt)
        else:
            parsed = self._parse_with_regex(prompt)
        
        return {
            "project_id": parsed.get("project_id"),
            "scope": parsed.get("scope")
        }

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

    def _format_with_llm(self, bid_text: str, project_id: str, scope: str) -> str:
        """Use LLM to format a professional recommendation."""
        format_prompt = f"""You are a construction project manager assistant. Create a brief, professional recommendation 
for selecting subcontractors based on the provided bids.

Project: {project_id}
Scope: {scope}

Top Bids:
{bid_text}

Write a concise 2-3 sentence recommendation. Be specific about which contractor to choose and why.
Focus on cost-effectiveness and timeline."""

        try:
            response = self.llm.invoke(format_prompt)
            logger.debug("LLM-formatted recommendation")
            return response.content
        except Exception as e:
            logger.warning(f"LLM formatting failed: {e}. Using default format.")
            return None

    def _format_with_default(self, top_bids: list, bid_text: str) -> str:
        """Default formatting for recommendation."""
        lines = [f"Recommendation (top {len(top_bids)}):"]
        for bid in top_bids:
            subcontractor = bid.get("subcontractor", "Unknown")
            price = bid.get("price", 0)
            lead_days = bid.get("lead_time_days", "?")
            lines.append(f"  • {subcontractor} — ${price:,} — {lead_days}d lead time")
        return "\n".join(lines)

    def _format_node(self, state: AgentState) -> AgentState:
        """Output node: format a professional recommendation.
        
        Uses LLM if available, otherwise uses simple formatting.
        """
        comparison = state.get("comparison", {})
        top = comparison.get("top", [])
        project_id = state.get("project_id", "Unknown")
        scope = state.get("scope", "construction works")
        
        # Build bid summary
        bid_text = "\n".join([
            f"- {bid.get('subcontractor')}: ${bid.get('price'):,} (lead time: {bid.get('lead_time_days')}d)"
            for bid in top
        ])
        
        # Format recommendation
        if self.use_llm and self.llm:
            recommendation_text = self._format_with_llm(bid_text, project_id, scope)
            if not recommendation_text:
                recommendation_text = self._format_with_default(top, bid_text)
        else:
            recommendation_text = self._format_with_default(top, bid_text)
        
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

    def run(self, prompt: str, verbose: bool = False) -> AgentState:
        """Execute the agent: invoke the compiled graph with initial state.
        
        Args:
            prompt: The user's procurement request
            verbose: If True, print detailed execution logs
            
        Returns:
            Final agent state with all processing results
        """
        if self.compiled_graph is None:
            self.build_graph()

        if verbose:
            logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        logger.info(f"Starting agent execution with prompt: {prompt[:50]}...")
        
        initial_state: AgentState = {
            "prompt": prompt,
            "project_id": None,
            "scope": None,
            "bids": [],
            "comparison": {},
            "recommendation": "",
        }
        
        final_state = self.compiled_graph.invoke(initial_state)
        
        logger.info("Agent execution completed")

        return {
            "prompt": final_state.get("prompt", prompt),
            "project_id": final_state.get("project_id"),
            "scope": final_state.get("scope"),
            "bids": final_state.get("bids", []),
            "comparison": final_state.get("comparison", {}),
            "recommendation": final_state.get("recommendation"),
        }
