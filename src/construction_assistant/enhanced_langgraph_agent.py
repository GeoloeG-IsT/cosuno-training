"""Enhanced LangGraph agent with advanced features: conditionals, loops, and validation.

This demonstrates advanced LangGraph patterns:
- Conditional routing (graph_state_router)
- Loops (validate -> re-fetch if invalid)
- Parallel-like operations (multiple validators)
- Adaptive behavior based on state
- LangChain tool integration with proper tool binding

Original agent is preserved in langgraph_agent.py for basic use cases.
This enhanced version shows production-ready patterns.
"""
import json
import logging
import os
import re
from typing import Any, Literal
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools.base import ToolException

from .agent import fetch_subcontractor_bids, compare_bids
from .schema import AgentState
from .tools import AVAILABLE_TOOLS, fetch_market_data, estimate_project_cost




class EnhancedLangGraphAgent:
    """Advanced agent with conditional routing, validation loops, and error recovery.
    
    Features:
    - Conditional routing: Different paths based on parsing success
    - Validation loops: Re-fetch if initial bids are insufficient
    - Fallback strategies: Graceful degradation when data is incomplete
    - Multi-path execution: Try multiple extraction strategies
    - State tracking: Track iterations and confidence levels
    """

    def __init__(
        self,
        api_key: str | None = None,
        top_n: int = 1,
        gemini_api_key: str | None = None,
        use_llm: bool = True,
        min_bids: int = 2,
        max_retries: int = 2,
    ):
        """Initialize the enhanced agent.
        
        Args:
            api_key: Optional API key for tools
            top_n: Number of top bids to return
            gemini_api_key: Optional Gemini API key
            use_llm: If False, use regex parsing
            min_bids: Minimum bids required before considering successful
            max_retries: Maximum retry attempts for fetching bids
        """
        self.api_key = api_key
        self.top_n = top_n
        self.use_llm = use_llm
        self.llm = None
        self.llm_with_tools = None  # Initialize to None
        self.min_bids = min_bids
        self.max_retries = max_retries
        self.graph = StateGraph(AgentState)
        self.compiled_graph = None

        # Extended state to track iterations
        self.extended_state = {
            "iteration_count": 0,
            "parse_confidence": 0.0,
            "fetch_attempts": 0,
            "validation_passed": False,
        }

        if use_llm:
            api_key_to_use = gemini_api_key or os.getenv("GOOGLE_API_KEY")
            if api_key_to_use:
                try:
                    self.llm = ChatGoogleGenerativeAI(
                        model="gemini-3-pro-preview",
                        google_api_key=api_key_to_use,
                        temperature=0.3
                    )
                    logger.info("✅ Gemini LLM initialized")
                    # Bind tools to LLM for tool-calling capability
                    self.llm_with_tools = self._bind_tools_to_llm(self.llm)
                except Exception as e:
                    logger.warning(f"Failed to init Gemini: {e}. Using regex.")
                    self.use_llm = False

    def _bind_tools_to_llm(self, llm):
        """Bind LangChain tools to the LLM for tool-calling capability.
        
        This demonstrates the proper LangChain pattern for tool binding:
        - Uses bind_tools() to attach tool definitions to LLM
        - Tools are automatically converted to appropriate schema format
        - LLM can now return tool_calls in responses
        
        Returns:
            LLM instance configured for tool calling
        """
        if not self.llm:
            return None
        
        try:
            # Bind tools to LLM - this is the LangChain pattern
            # The bind_tools method handles schema conversion automatically
            llm_with_tools = self.llm.bind_tools(AVAILABLE_TOOLS)
            logger.info(f"✅ Tools bound to LLM: {[t.name for t in AVAILABLE_TOOLS]}")
            return llm_with_tools
        except Exception as e:
            logger.warning(f"Failed to bind tools to LLM: {e}")
            return self.llm

    def _execute_llm_tool_calls(self, tool_calls: list, tool_results: dict = None) -> dict:
        """Execute tool calls returned by the LLM.
        
        This method handles the full LLM-tool loop orchestration:
        1. Parse tool_call messages from LLM response
        2. Execute each tool using AVAILABLE_TOOLS
        3. Collect results for feedback to LLM
        
        Args:
            tool_calls: List of tool call dicts from LLM (typically with 'tool', 'tool_input', 'id')
            tool_results: Optional dict to accumulate results
            
        Returns:
            Updated dict with results keyed by tool name or ID
        """
        if tool_results is None:
            tool_results = {}
        
        for tool_call in tool_calls:
            tool_name = tool_call.get("tool") or tool_call.get("name")
            tool_input = tool_call.get("tool_input") or tool_call.get("input", {})
            tool_id = tool_call.get("id", tool_name)
            
            logger.info(f"🔧 Executing LLM tool call: {tool_name}({tool_input})")
            
            try:
                # Find and execute the matching tool
                matching_tool = next(
                    (t for t in AVAILABLE_TOOLS if t.name == tool_name),
                    None
                )
                
                if matching_tool is None:
                    logger.warning(f"⚠️  Tool '{tool_name}' not found in AVAILABLE_TOOLS")
                    tool_results[tool_id] = {"error": f"Tool '{tool_name}' not found"}
                    continue
                
                # Invoke the tool with the LLM-provided inputs
                result = matching_tool.invoke(tool_input)
                tool_results[tool_id] = result
                logger.info(f"✅ Tool '{tool_name}' executed successfully")
                
            except ToolException as e:
                logger.warning(f"⚠️  Tool '{tool_name}' raised ToolException: {str(e)}")
                tool_results[tool_id] = {"error": f"ToolException: {str(e)}"}
            except Exception as e:
                logger.error(f"❌ Unexpected error executing tool '{tool_name}': {str(e)}")
                tool_results[tool_id] = {"error": f"Unexpected error: {str(e)}"}
        
        return tool_results

    # ==================== PARSING NODES ====================

    def _parse_node(self, state: AgentState) -> dict:
        """Parse and extract project_id and scope."""
        prompt = state.get("prompt", "")
        logger.info(f"Parsing: {prompt[:50]}...")

        # Try LLM first if available
        if self.use_llm and self.llm:
            result = self._parse_with_llm(prompt)
            confidence = 0.9
        else:
            result = self._parse_with_regex(prompt)
            confidence = 0.6 if result["project_id"] else 0.3

        return {
            "project_id": result.get("project_id"),
            "scope": result.get("scope"),
            "_parse_confidence": confidence,
        }

    def _parse_with_llm(self, prompt: str) -> dict[str, Any]:
        """Use LLM for intelligent extraction."""
        extraction_prompt = f"""Extract project_id and scope from: {prompt}
Respond only with JSON: {{"project_id": <string or null>, "scope": <string or null>}}"""
        try:
            response = self.llm.invoke(extraction_prompt)
            return json.loads(response.content)
        except Exception as e:
            logger.warning(f"LLM parsing failed: {e}. Falling back to regex.")
            return self._parse_with_regex(prompt)

    def _parse_with_regex(self, prompt: str) -> dict[str, Any]:
        """Regex-based extraction fallback."""
        project_match = re.search(r'([A-Z]+[-]?\d+|P[-]?\d+)', prompt.upper())
        project_id = project_match.group(1) if project_match else None

        scope_keywords = [
            "foundation", "excavation", "electrical", "plumbing", 
            "roofing", "site clearing", "HVAC"
        ]
        scope = next(
            (kw for kw in scope_keywords if kw.lower() in prompt.lower()),
            None
        )
        return {"project_id": project_id, "scope": scope}

    # ==================== VALIDATION NODE ====================

    def _validate_parse_node(self, state: AgentState) -> dict:
        """Validate parsing results - CONDITIONAL ROUTING POINT.
        
        This node determines the next path:
        - If parse succeeded with high confidence → proceed to fetch
        - If parse failed or low confidence → fallback or request clarification
        """
        project_id = state.get("project_id")
        confidence = state.get("_parse_confidence", 0.0)

        logger.info(f"Validation: project_id={project_id}, confidence={confidence:.1%}")

        # Determine validation result
        validation_passed = project_id is not None and confidence > 0.5

        return {
            "_validation_passed": validation_passed,
            "_parse_confidence": confidence,
        }

    def _router_after_validation(self, state: AgentState) -> Literal["fetch", "clarify"]:
        """Conditional router: decide next node based on validation.
        
        This is a key LangGraph feature - routing decisions based on state.
        """
        validation_passed = state.get("_validation_passed", False)
        
        if validation_passed:
            logger.info("✅ Validation passed → proceeding to fetch")
            return "fetch"
        else:
            logger.warning("❌ Validation failed → requesting clarification")
            return "clarify"

    # ==================== CLARIFICATION NODE ====================

    def _clarify_node(self, state: AgentState) -> dict:
        """Handle cases where parsing failed - fallback logic."""
        logger.info("Attempting clarification with LLM or defaults...")

        # If we have no project_id, try harder to extract it
        prompt = state.get("prompt", "")
        if not state.get("project_id"):
            # More aggressive extraction
            all_numbers = re.findall(r'\b[A-Z]+-\d+\b', prompt)
            if all_numbers:
                project_id = all_numbers[0]
            else:
                project_id = "UNKNOWN"
        else:
            project_id = state.get("project_id")

        # For scope, provide a generic default
        scope = state.get("scope") or "general construction"

        logger.info(f"Clarified: project_id={project_id}, scope={scope}")

        return {
            "project_id": project_id,
            "scope": scope,
            "_validation_passed": True,  # Accept clarified values
        }

    # ==================== FETCH NODE WITH LOOP ====================

    def _fetch_node(self, state: AgentState) -> dict:
        """Fetch bids - can loop if results are insufficient.
        
        This demonstrates the loop pattern in LangGraph:
        - Check result quality
        - If insufficient, mark for retry
        - Router decides whether to retry or continue
        """
        prompt = state.get("prompt", "")
        project_id = state.get("project_id")
        
        fetch_attempts = state.get("_fetch_attempts", 0)
        logger.info(f"Fetching bids (attempt {fetch_attempts + 1}/{self.max_retries})...")

        bids_result = fetch_subcontractor_bids(
            prompt,
            project_id=project_id,
            api_key=self.api_key
        )
        bids = bids_result.get("bids", [])

        return {
            "bids": bids,
            "_fetch_attempts": fetch_attempts + 1,
            "_needs_refetch": len(bids) < self.min_bids and fetch_attempts < self.max_retries,
        }

    def _use_tools_node(self, state: AgentState) -> dict:
        """Execute tools to gather market data and cost estimates.
        
        This demonstrates LangChain tool usage in LangGraph agents:
        - Identify which tools are needed
        - Execute tools using proper LangChain tool.invoke() pattern
        - Store results in state for later nodes
        """
        scope = state.get("scope", "general")
        logger.info(f"Using tools for scope: {scope}")
        
        tool_calls = []
        tool_results = {}
        
        # Tool 1: Fetch market data
        try:
            # Execute tool using LangChain's standard tool invocation
            market_data = fetch_market_data.invoke({"scope": scope})
            tool_calls.append({
                "tool": fetch_market_data.name,
                "params": {"scope": scope},
                "status": "success"
            })
            tool_results["market_data"] = market_data
            logger.info(f"✅ Market data fetched: {market_data['market_suppliers']} suppliers found")
        except ToolException as e:
            logger.warning(f"Market data tool failed: {str(e)}")
            tool_calls.append({
                "tool": fetch_market_data.name,
                "params": {"scope": scope},
                "status": "failed",
                "error": str(e)
            })
        except Exception as e:
            logger.error(f"Unexpected error in market data tool: {str(e)}")
            tool_calls.append({
                "tool": fetch_market_data.name,
                "params": {"scope": scope},
                "status": "error",
                "error": f"Unexpected error: {str(e)}"
            })
        
        # Tool 2: Estimate costs
        try:
            complexity = "medium"
            # Determine complexity based on scope
            if "roofing" in scope.lower():
                complexity = "high"
            elif "excavation" in scope.lower():
                complexity = "medium"
            
            # Execute tool using LangChain's standard tool invocation
            cost_estimate = estimate_project_cost.invoke({
                "scope": scope,
                "complexity": complexity
            })
            tool_calls.append({
                "tool": estimate_project_cost.name,
                "params": {"scope": scope, "complexity": complexity},
                "status": "success"
            })
            tool_results["cost_estimate"] = cost_estimate
            logger.info(f"✅ Cost estimate generated: ${cost_estimate['estimated_total']:,}")
        except ToolException as e:
            logger.warning(f"Cost estimator tool failed: {str(e)}")
            tool_calls.append({
                "tool": estimate_project_cost.name,
                "params": {"scope": scope},
                "status": "failed",
                "error": str(e)
            })
        except Exception as e:
            logger.error(f"Unexpected error in cost estimator tool: {str(e)}")
            tool_calls.append({
                "tool": estimate_project_cost.name,
                "params": {"scope": scope},
                "status": "error",
                "error": f"Unexpected error: {str(e)}"
            })
        
        return {
            "tool_calls": tool_calls,
            "tool_results": tool_results,
        }

    def _llm_with_tools_node(self, state: AgentState) -> dict:
        """Execute LLM with tools bound - demonstrates full LLM-initiated tool-calling loop.
        
        This is the key orchestration node that shows how LangChain + LangGraph
        enables autonomous tool-calling:
        
        1. Call LLM with tools bound
        2. Parse tool_calls from response (if any)
        3. Execute tools using _execute_llm_tool_calls
        4. Loop until LLM returns final response (no more tool_calls)
        
        This enables the LLM to autonomously decide which tools to use and when.
        """
        if not self.llm_with_tools:
            logger.info("ℹ️  LLM-with-tools not available, skipping LLM tool orchestration")
            return {"_llm_tool_calls": [], "_llm_tool_results": {}}
        
        project_id = state.get("project_id", "Unknown")
        scope = state.get("scope", "general")
        bids = state.get("bids", [])
        
        logger.info(f"🤖 Calling LLM with tools bound for analysis of {len(bids)} bids")
        
        llm_tool_calls = []
        llm_tool_results = {}
        max_iterations = 3  # Prevent infinite loops
        iteration = 0
        
        # Build context for LLM
        bid_text = "\n".join([
            f"- {bid.get('subcontractor')}: ${bid.get('price'):,} (lead: {bid.get('lead_time_days')}d)"
            for bid in bids[:5]  # Show top 5
        ]) or "No bids available"
        
        system_prompt = """You are a construction project advisor. Analyze bids and use available tools 
to provide market context and cost validation. Decide which tools are relevant and use them to enrich your analysis."""
        
        user_prompt = f"""Analyze these bids for project {project_id} ({scope}):
{bid_text}

Use tools to:
1. Get market data for this scope
2. Estimate expected costs

Then provide a brief analysis."""
        
        # Initial message to LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Loop: call LLM, execute tools, repeat until no more tool calls
        while iteration < max_iterations:
            iteration += 1
            logger.debug(f"LLM iteration {iteration}/{max_iterations}")
            
            try:
                # Call LLM with tools bound
                response = self.llm_with_tools.invoke(messages)
                
                # Parse response for tool_calls
                # Different providers may format this differently
                tool_calls = []
                
                # Check for tool_calls attribute (LangChain format)
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    tool_calls = response.tool_calls
                    logger.info(f"📋 LLM returned {len(tool_calls)} tool calls")
                
                # Check for tool_call in content (some providers)
                elif hasattr(response, 'content') and isinstance(response.content, list):
                    for item in response.content:
                        if isinstance(item, dict) and item.get('type') == 'tool_use':
                            tool_calls.append({
                                'tool': item.get('name'),
                                'tool_input': item.get('input', {}),
                                'id': item.get('id')
                            })
                
                # If no tool calls, we're done
                if not tool_calls:
                    logger.info(f"✅ LLM finished (no tool calls). Final response received.")
                    break
                
                # Execute the tool calls
                logger.info(f"🔧 Executing {len(tool_calls)} tool calls from LLM")
                new_results = self._execute_llm_tool_calls(tool_calls, llm_tool_results)
                llm_tool_results.update(new_results)
                llm_tool_calls.extend(tool_calls)
                
                # Add assistant message and tool results to message history
                assistant_message = {
                    "role": "assistant",
                    "content": response.content if hasattr(response, 'content') else str(response)
                }
                messages.append(assistant_message)
                
                # Add tool results to messages for LLM to see
                for tool_call in tool_calls:
                    tool_id = tool_call.get('id', tool_call.get('tool'))
                    result = new_results.get(tool_id, {})
                    messages.append({
                        "role": "tool",
                        "tool_use_id": tool_id,
                        "content": json.dumps(result)
                    })
                
                logger.debug(f"Added {len(tool_calls)} tool results to message history")
                
            except Exception as e:
                logger.error(f"Error in LLM tool orchestration iteration {iteration}: {str(e)}")
                break
        
        if iteration >= max_iterations:
            logger.warning(f"⚠️  LLM tool loop reached max iterations ({max_iterations})")
        
        logger.info(f"✅ LLM tool orchestration complete: {len(llm_tool_calls)} tools used")
        return {
            "_llm_tool_calls": llm_tool_calls,
            "_llm_tool_results": llm_tool_results,
        }

    def _router_after_fetch(self, state: AgentState) -> Literal["compare", "refetch"]:
        """Conditional router: decide if we need to retry fetching.
        
        Loop pattern: if not enough bids, fetch again with different parameters.
        """
        needs_refetch = state.get("_needs_refetch", False)
        
        if needs_refetch:
            logger.warning(f"Insufficient bids ({len(state.get('bids', []))} < {self.min_bids}). Retrying...")
            return "refetch"
        else:
            logger.info(f"Sufficient bids ({len(state.get('bids', []))}) → proceeding to compare")
            return "compare"

    def _refetch_node(self, state: AgentState) -> dict:
        """Retry fetching with expanded parameters."""
        logger.info("Refetching with expanded scope...")
        
        # In a real system, would expand search criteria
        prompt = state.get("prompt", "")
        project_id = state.get("project_id")
        
        # Try again (in production, would modify parameters)
        bids_result = fetch_subcontractor_bids(
            prompt,
            project_id=project_id,
            api_key=self.api_key
        )
        bids = bids_result.get("bids", [])
        existing_bids = state.get("bids", [])
        
        # Merge with existing bids
        all_bids = existing_bids + bids
        
        return {
            "bids": all_bids[:10],  # Keep top 10
            "_fetch_attempts": state.get("_fetch_attempts", 0) + 1,
            "_needs_refetch": len(all_bids) < self.min_bids and state.get("_fetch_attempts", 0) < self.max_retries,
        }

    # ==================== ANALYSIS NODES ====================

    def _compare_node(self, state: AgentState) -> dict:
        """Compare and rank bids."""
        bids = state.get("bids", [])
        logger.info(f"Comparing {len(bids)} bids...")

        compare_result = compare_bids(bids, top_n=self.top_n)
        return {"comparison": compare_result}

    def _validate_comparison_node(self, state: AgentState) -> dict:
        """Validate comparison results - another validation point."""
        comparison = state.get("comparison", {})
        top_bids = comparison.get("top", [])
        
        is_valid = len(top_bids) > 0
        logger.info(f"Comparison validation: {len(top_bids)} top bids selected")
        
        return {"_comparison_valid": is_valid}

    # ==================== FORMATTING NODE ====================

    def _format_node(self, state: AgentState) -> dict:
        """Format recommendation based on validated results and tool insights."""
        comparison = state.get("comparison", {})
        top = comparison.get("top", [])
        project_id = state.get("project_id", "Unknown")
        scope = state.get("scope", "construction")
        tool_results = state.get("tool_results", {})

        bid_text = "\n".join([
            f"- {bid.get('subcontractor')}: ${bid.get('price'):,} (lead: {bid.get('lead_time_days')}d)"
            for bid in top
        ])
        
        # Include tool insights in recommendation
        tool_insights = ""
        if tool_results:
            if "market_data" in tool_results:
                market = tool_results["market_data"]
                tool_insights += f"\nMarket Context: {market['market_suppliers']} suppliers available ({market['current_trend']} trend)"
            if "cost_estimate" in tool_results:
                estimate = tool_results["cost_estimate"]
                tool_insights += f"\nEstimated Budget: ${estimate['estimated_total']:,} ({estimate['confidence']} confidence)"

        if self.use_llm and self.llm:
            recommendation = self._format_with_llm(bid_text, project_id, scope, tool_insights)
        else:
            recommendation = self._format_default(top, tool_insights)

        logger.info("Recommendation formatted with tool insights")
        return {"recommendation": recommendation}

    def _format_with_llm(self, bid_text: str, project_id: str, scope: str, insights: str = "") -> str:
        """Format using LLM."""
        prompt = f"""Create a brief professional recommendation for: {project_id} ({scope})
Top Bids:
{bid_text}{insights}
Recommendation (2-3 sentences):"""
        try:
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            logger.warning(f"LLM format failed: {e}")
            return ""

    def _format_default(self, top_bids: list, insights: str = "") -> str:
        """Simple formatting fallback."""
        lines = [f"Recommended {len(top_bids)} contractors:"]
        for bid in top_bids:
            lines.append(
                f"  • {bid.get('subcontractor')}: ${bid.get('price'):,} "
                f"({bid.get('lead_time_days')}d lead)"
            )
        return "\n".join(lines)

    # ==================== GRAPH BUILDING ====================

    def build_graph(self):
        """Build the enhanced graph with conditionals, loops, and tool usage."""
        # Add nodes
        self.graph.add_node("parse", self._parse_node)
        self.graph.add_node("validate_parse", self._validate_parse_node)
        self.graph.add_node("clarify", self._clarify_node)
        self.graph.add_node("fetch", self._fetch_node)
        self.graph.add_node("use_tools", self._use_tools_node)
        self.graph.add_node("llm_with_tools", self._llm_with_tools_node)
        self.graph.add_node("refetch", self._refetch_node)
        self.graph.add_node("compare", self._compare_node)
        self.graph.add_node("validate_comparison", self._validate_comparison_node)
        self.graph.add_node("format", self._format_node)

        # Build edges with conditional routing
        self.graph.add_edge(START, "parse")
        self.graph.add_edge("parse", "validate_parse")
        
        # Conditional router: validate_parse → clarify or fetch
        self.graph.add_conditional_edges(
            "validate_parse",
            self._router_after_validation,
            {
                "fetch": "fetch",
                "clarify": "clarify",
            }
        )
        self.graph.add_edge("clarify", "fetch")
        
        # Tool usage nodes: use_tools → llm_with_tools → compare (or refetch if needed)
        self.graph.add_edge("fetch", "use_tools")
        self.graph.add_edge("use_tools", "llm_with_tools")
        
        # Conditional router: llm_with_tools → refetch or compare (loop)
        self.graph.add_conditional_edges(
            "llm_with_tools",
            self._router_after_fetch,
            {
                "compare": "compare",
                "refetch": "refetch",
            }
        )
        self.graph.add_edge("refetch", "compare")
        
        # Continue with validation and formatting
        self.graph.add_edge("compare", "validate_comparison")
        self.graph.add_edge("validate_comparison", "format")
        self.graph.add_edge("format", END)

        self.compiled_graph = self.graph.compile()
        logger.info("✅ Enhanced graph compiled with conditionals, loops, tools, and LLM orchestration")

    # ==================== EXECUTION ====================

    def run(self, prompt: str, verbose: bool = False) -> AgentState:
        """Execute the enhanced agent."""
        if self.compiled_graph is None:
            self.build_graph()

        if verbose:
            logger.setLevel(logging.DEBUG)

        logger.info(f"Starting enhanced agent: {prompt[:50]}...")

        initial_state: AgentState = {
            "prompt": prompt,
            "project_id": None,
            "scope": None,
            "bids": [],
            "comparison": {},
            "recommendation": "",
            "tool_calls": None,
            "tool_results": None,
        }

        final_state = self.compiled_graph.invoke(initial_state)

        return {
            "prompt": final_state.get("prompt", prompt),
            "project_id": final_state.get("project_id"),
            "scope": final_state.get("scope"),
            "bids": final_state.get("bids", []),
            "comparison": final_state.get("comparison", {}),
            "recommendation": final_state.get("recommendation"),
            "tool_calls": final_state.get("tool_calls"),
            "tool_results": final_state.get("tool_results"),
            "llm_tool_calls": final_state.get("_llm_tool_calls"),
            "llm_tool_results": final_state.get("_llm_tool_results"),
        }
