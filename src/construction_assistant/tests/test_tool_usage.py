"""Tests for tool usage in the enhanced agent.

This test suite validates:
- Tool invocation and result collection
- tool_calls and tool_results in agent state
- Error handling in tool execution
- LLM tool binding and orchestration
"""
from unittest.mock import Mock, patch, MagicMock
import pytest
from construction_assistant.enhanced_langgraph_agent import EnhancedLangGraphAgent
from construction_assistant.tools import fetch_market_data, estimate_project_cost, AVAILABLE_TOOLS


class TestToolInvocation:
    """Tests for basic tool invocation via .invoke()"""
    
    def test_fetch_market_data_invoke_valid_scope(self):
        """Test that fetch_market_data tool can be invoked with valid scope."""
        result = fetch_market_data.invoke({"scope": "excavation"})
        
        assert isinstance(result, dict)
        assert result["scope"] == "excavation"
        assert "market_suppliers" in result
        assert "timestamp" in result
        assert result["market_suppliers"] == 47
    
    def test_estimate_project_cost_invoke_valid_scope(self):
        """Test that estimate_project_cost tool can be invoked with valid scope."""
        result = estimate_project_cost.invoke({
            "scope": "roofing",
            "complexity": "high"
        })
        
        assert isinstance(result, dict)
        assert result["scope"] == "roofing"
        assert result["complexity"] == "high"
        assert "estimated_total" in result
        assert "breakdown" in result
        assert "confidence" in result
        assert result["estimated_total"] == 36000
    
    def test_fetch_market_data_invalid_scope_raises_exception(self):
        """Test that invalid scope raises ToolException."""
        from langchain_core.tools.base import ToolException
        
        with pytest.raises(ToolException):
            fetch_market_data.invoke({"scope": ""})
    
    def test_estimate_project_cost_invalid_complexity_raises_exception(self):
        """Test that invalid complexity raises ToolException."""
        from langchain_core.tools.base import ToolException
        
        with pytest.raises(ToolException):
            estimate_project_cost.invoke({
                "scope": "roofing",
                "complexity": "invalid"
            })


class TestToolsAvailable:
    """Tests for tool availability and configuration."""
    
    def test_available_tools_list(self):
        """Test that AVAILABLE_TOOLS contains expected tools."""
        assert len(AVAILABLE_TOOLS) == 2
        tool_names = [t.name for t in AVAILABLE_TOOLS]
        assert "fetch_market_data" in tool_names
        assert "estimate_project_cost" in tool_names
    
    def test_tools_have_proper_schema(self):
        """Test that tools have proper schema for LLM binding."""
        for tool in AVAILABLE_TOOLS:
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "args_schema")
            assert tool.name in ["fetch_market_data", "estimate_project_cost"]
            assert len(tool.description) > 0


class TestAgentToolUsage:
    """Tests for tool usage within the enhanced agent."""
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_agent_use_tools_node_returns_tool_calls_and_results(self, mock_llm_class):
        """Test that _use_tools_node populates tool_calls and tool_results in state."""
        mock_llm_class.return_value = Mock()
        
        agent = EnhancedLangGraphAgent(use_llm=False)
        
        state = {
            "prompt": "Get excavation bids",
            "scope": "excavation",
            "bids": [],
            "comparison": {},
            "recommendation": "",
            "tool_calls": None,
            "tool_results": None,
        }
        
        result = agent._use_tools_node(state)
        
        assert "tool_calls" in result
        assert "tool_results" in result
        assert isinstance(result["tool_calls"], list)
        assert isinstance(result["tool_results"], dict)
        assert len(result["tool_calls"]) == 2  # Two tools called
        assert "market_data" in result["tool_results"]
        assert "cost_estimate" in result["tool_results"]
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_agent_run_includes_tool_results_in_output(self, mock_llm_class):
        """Test that agent.run() returns tool_calls and tool_results."""
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        
        # Mock LLM responses
        parse_response = Mock()
        parse_response.content = '{"project_id": "P-123", "scope": "excavation"}'
        
        format_response = Mock()
        format_response.content = "Recommended contractor with best rates."
        
        mock_llm.invoke.side_effect = [parse_response, format_response]
        
        agent = EnhancedLangGraphAgent(use_llm=True)
        result = agent.run("Get excavation bids for P-123")
        
        # Verify tool fields are in output
        assert "tool_calls" in result
        assert "tool_results" in result
        
        # Tool calls should be populated
        if result["tool_calls"]:
            assert isinstance(result["tool_calls"], list)
            assert len(result["tool_calls"]) > 0
            # Each tool call should have tool name, params, status
            for call in result["tool_calls"]:
                assert "tool" in call
                assert "params" in call
                assert "status" in call
        
        # Tool results should have market_data and/or cost_estimate
        if result["tool_results"]:
            assert isinstance(result["tool_results"], dict)
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_agent_graph_includes_use_tools_node(self, mock_llm_class):
        """Test that the compiled graph includes the use_tools node."""
        mock_llm_class.return_value = Mock()
        
        agent = EnhancedLangGraphAgent(use_llm=False)
        agent.build_graph()
        
        assert "use_tools" in agent.graph.nodes
        assert "llm_with_tools" in agent.graph.nodes


class TestToolExecutionOrchestration:
    """Tests for LLM-initiated tool execution and results aggregation."""
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_execute_llm_tool_calls_valid_tools(self, mock_llm_class):
        """Test _execute_llm_tool_calls with valid tool calls."""
        mock_llm_class.return_value = Mock()
        
        agent = EnhancedLangGraphAgent(use_llm=False)
        
        tool_calls = [
            {
                "tool": "fetch_market_data",
                "tool_input": {"scope": "excavation"},
                "id": "call-1"
            },
            {
                "tool": "estimate_project_cost",
                "tool_input": {"scope": "excavation", "complexity": "medium"},
                "id": "call-2"
            }
        ]
        
        results = agent._execute_llm_tool_calls(tool_calls)
        
        assert "call-1" in results
        assert "call-2" in results
        assert results["call-1"]["market_suppliers"] == 47
        assert results["call-2"]["estimated_total"] == 10000
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_execute_llm_tool_calls_nonexistent_tool(self, mock_llm_class):
        """Test _execute_llm_tool_calls with nonexistent tool."""
        mock_llm_class.return_value = Mock()
        
        agent = EnhancedLangGraphAgent(use_llm=False)
        
        tool_calls = [
            {
                "tool": "nonexistent_tool",
                "tool_input": {"param": "value"},
                "id": "call-1"
            }
        ]
        
        results = agent._execute_llm_tool_calls(tool_calls)
        
        assert "call-1" in results
        assert "error" in results["call-1"]
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_execute_llm_tool_calls_accumulates_results(self, mock_llm_class):
        """Test that _execute_llm_tool_calls accumulates results in provided dict."""
        mock_llm_class.return_value = Mock()
        
        agent = EnhancedLangGraphAgent(use_llm=False)
        
        existing_results = {"previous": "result"}
        
        tool_calls = [
            {
                "tool": "fetch_market_data",
                "tool_input": {"scope": "roofing"},
                "id": "call-1"
            }
        ]
        
        results = agent._execute_llm_tool_calls(tool_calls, existing_results)
        
        assert "previous" in results  # Existing result preserved
        assert "call-1" in results  # New result added
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_llm_with_tools_node_returns_proper_structure(self, mock_llm_class):
        """Test that _llm_with_tools_node returns proper state structure."""
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        
        agent = EnhancedLangGraphAgent(use_llm=False)  # LLM not initialized
        
        state = {
            "prompt": "Analyze bids",
            "project_id": "P-123",
            "scope": "excavation",
            "bids": [
                {"subcontractor": "Builder A", "price": 10000, "lead_time_days": 10},
                {"subcontractor": "Builder B", "price": 11000, "lead_time_days": 5},
            ],
            "comparison": {},
            "recommendation": "",
            "tool_calls": None,
            "tool_results": None,
        }
        
        result = agent._llm_with_tools_node(state)
        
        assert "_llm_tool_calls" in result
        assert "_llm_tool_results" in result
        assert isinstance(result["_llm_tool_calls"], list)
        assert isinstance(result["_llm_tool_results"], dict)


class TestToolErrorHandling:
    """Tests for error handling in tool execution."""
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_use_tools_node_handles_tool_exceptions(self, mock_llm_class):
        """Test that _use_tools_node gracefully handles tool exceptions."""
        mock_llm_class.return_value = Mock()
        
        agent = EnhancedLangGraphAgent(use_llm=False)
        
        # Invalid scope should cause tool exception
        state = {
            "prompt": "Get bids",
            "scope": "",  # Invalid - empty scope
            "bids": [],
            "comparison": {},
            "recommendation": "",
            "tool_calls": None,
            "tool_results": None,
        }
        
        # This should not raise, but should handle gracefully
        result = agent._use_tools_node(state)
        
        assert "tool_calls" in result
        assert isinstance(result["tool_calls"], list)
        # Should have recorded the error in tool_calls
        for call in result["tool_calls"]:
            if call["status"] != "success":
                assert "error" in call
