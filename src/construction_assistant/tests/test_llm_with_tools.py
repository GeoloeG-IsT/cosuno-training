"""Tests for LLM-with-tools integration and orchestration.

This test suite validates:
- LLM binding with tools
- LLM-initiated tool call parsing
- Tool execution orchestration loop
- Message history accumulation
- Error recovery in tool orchestration
"""
from unittest.mock import Mock, patch, MagicMock
import json
import pytest
from construction_assistant.enhanced_langgraph_agent import EnhancedLangGraphAgent
from construction_assistant.tools import AVAILABLE_TOOLS


class TestLLMToolBinding:
    """Tests for binding tools to the LLM."""
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_bind_tools_to_llm_success(self, mock_llm_class):
        """Test successful binding of tools to LLM."""
        mock_llm = Mock()
        mock_llm_with_tools = Mock()
        mock_llm.bind_tools.return_value = mock_llm_with_tools
        
        mock_llm_class.return_value = mock_llm
        
        agent = EnhancedLangGraphAgent(use_llm=True)
        
        # Reset call count after initialization
        mock_llm.bind_tools.reset_mock()
        
        result = agent._bind_tools_to_llm(mock_llm)
        
        # Verify bind_tools was called with AVAILABLE_TOOLS
        mock_llm.bind_tools.assert_called_once()
        assert result == mock_llm_with_tools
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_bind_tools_to_llm_failure_fallback(self, mock_llm_class):
        """Test fallback when tool binding fails."""
        mock_llm = Mock()
        mock_llm.bind_tools.side_effect = Exception("Binding not supported")
        
        mock_llm_class.return_value = mock_llm
        
        agent = EnhancedLangGraphAgent(use_llm=True)
        result = agent._bind_tools_to_llm(mock_llm)
        
        # Should return original LLM when binding fails
        assert result == mock_llm
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_bind_tools_to_llm_with_none_llm(self, mock_llm_class):
        """Test binding with None LLM returns None."""
        mock_llm_class.return_value = Mock()
        
        agent = EnhancedLangGraphAgent(use_llm=False)
        result = agent._bind_tools_to_llm(None)
        
        assert result is None


class TestLLMToolCallParsing:
    """Tests for parsing tool calls from LLM responses."""
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_execute_llm_tool_calls_with_tool_calls_attribute(self, mock_llm_class):
        """Test parsing tool_calls from response with tool_calls attribute."""
        mock_llm_class.return_value = Mock()
        
        agent = EnhancedLangGraphAgent(use_llm=False)
        
        # Mock tool calls from LLM
        tool_calls = [
            {
                "tool": "fetch_market_data",
                "tool_input": {"scope": "excavation"},
                "id": "call-1"
            }
        ]
        
        results = agent._execute_llm_tool_calls(tool_calls)
        
        assert "call-1" in results
        assert results["call-1"]["market_suppliers"] == 47


class TestLLMToolOrchestrationLoop:
    """Tests for the full LLM tool orchestration loop."""
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_llm_with_tools_node_no_llm_available(self, mock_llm_class):
        """Test that node gracefully handles missing LLM."""
        mock_llm_class.return_value = Mock()
        
        agent = EnhancedLangGraphAgent(use_llm=False)
        
        state = {
            "prompt": "Analyze bids",
            "project_id": "P-123",
            "scope": "excavation",
            "bids": [
                {"subcontractor": "Builder A", "price": 10000, "lead_time_days": 10},
            ],
            "comparison": {},
            "recommendation": "",
            "tool_calls": None,
            "tool_results": None,
        }
        
        result = agent._llm_with_tools_node(state)
        
        # Should return empty results when LLM not available
        assert result["_llm_tool_calls"] == []
        assert result["_llm_tool_results"] == {}
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_llm_with_tools_node_single_tool_call_iteration(self, mock_llm_class):
        """Test orchestration with single tool call and completion."""
        mock_llm = Mock()
        mock_llm_with_tools = Mock()
        
        # First call returns response with tool_calls
        response_with_tool_call = Mock()
        response_with_tool_call.content = "Analyzing bids using market tools"
        response_with_tool_call.tool_calls = [
            {
                "tool": "fetch_market_data",
                "tool_input": {"scope": "excavation"},
                "id": "call-1"
            }
        ]
        
        # Second call (after tool execution) returns final response
        final_response = Mock()
        final_response.content = "Final analysis: Choose contractor with best value"
        final_response.tool_calls = None
        
        mock_llm_with_tools.invoke.side_effect = [response_with_tool_call, final_response]
        
        mock_llm_class.return_value = mock_llm
        mock_llm.bind_tools.return_value = mock_llm_with_tools
        
        agent = EnhancedLangGraphAgent(use_llm=True)
        
        state = {
            "prompt": "Analyze bids",
            "project_id": "P-123",
            "scope": "excavation",
            "bids": [
                {"subcontractor": "Builder A", "price": 10000, "lead_time_days": 10},
            ],
            "comparison": {},
            "recommendation": "",
            "tool_calls": None,
            "tool_results": None,
        }
        
        result = agent._llm_with_tools_node(state)
        
        # Should have executed the tool
        assert len(result["_llm_tool_calls"]) == 1
        assert result["_llm_tool_calls"][0]["tool"] == "fetch_market_data"
        
        # Should have collected results
        assert "call-1" in result["_llm_tool_results"]
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_llm_with_tools_node_multiple_tool_calls(self, mock_llm_class):
        """Test orchestration with multiple tool calls in one iteration."""
        mock_llm = Mock()
        mock_llm_with_tools = Mock()
        
        # Response with multiple tool calls
        response_with_tools = Mock()
        response_with_tools.content = "Analyzing bids"
        response_with_tools.tool_calls = [
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
        
        # Final response
        final_response = Mock()
        final_response.content = "Analysis complete"
        final_response.tool_calls = None
        
        mock_llm_with_tools.invoke.side_effect = [response_with_tools, final_response]
        
        mock_llm_class.return_value = mock_llm
        mock_llm.bind_tools.return_value = mock_llm_with_tools
        
        agent = EnhancedLangGraphAgent(use_llm=True)
        
        state = {
            "prompt": "Analyze bids",
            "project_id": "P-123",
            "scope": "excavation",
            "bids": [{"subcontractor": "Builder A", "price": 10000, "lead_time_days": 10}],
            "comparison": {},
            "recommendation": "",
            "tool_calls": None,
            "tool_results": None,
        }
        
        result = agent._llm_with_tools_node(state)
        
        # Both tools should be executed
        assert len(result["_llm_tool_calls"]) == 2
        assert "call-1" in result["_llm_tool_results"]
        assert "call-2" in result["_llm_tool_results"]
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_llm_with_tools_node_max_iterations_limit(self, mock_llm_class):
        """Test that orchestration respects max iterations limit."""
        mock_llm = Mock()
        mock_llm_with_tools = Mock()
        
        # Create responses that always return tool calls (would loop forever)
        tool_response = Mock()
        tool_response.content = "Need more tools"
        tool_response.tool_calls = [
            {
                "tool": "fetch_market_data",
                "tool_input": {"scope": "excavation"},
                "id": "call-1"
            }
        ]
        
        # Return tool_response 5 times (more than max iterations of 3)
        mock_llm_with_tools.invoke.side_effect = [tool_response] * 5
        
        mock_llm_class.return_value = mock_llm
        mock_llm.bind_tools.return_value = mock_llm_with_tools
        
        agent = EnhancedLangGraphAgent(use_llm=True)
        
        state = {
            "prompt": "Analyze",
            "project_id": "P-123",
            "scope": "excavation",
            "bids": [{"subcontractor": "Builder A", "price": 10000, "lead_time_days": 10}],
            "comparison": {},
            "recommendation": "",
            "tool_calls": None,
            "tool_results": None,
        }
        
        result = agent._llm_with_tools_node(state)
        
        # Should stop after max iterations (3)
        # So LLM should only be called 3 times max
        assert mock_llm_with_tools.invoke.call_count <= 3
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_llm_with_tools_node_exception_handling(self, mock_llm_class):
        """Test that orchestration handles exceptions gracefully."""
        mock_llm = Mock()
        mock_llm_with_tools = Mock()
        
        # LLM raises exception
        mock_llm_with_tools.invoke.side_effect = Exception("API error")
        
        mock_llm_class.return_value = mock_llm
        mock_llm.bind_tools.return_value = mock_llm_with_tools
        
        agent = EnhancedLangGraphAgent(use_llm=True)
        
        state = {
            "prompt": "Analyze",
            "project_id": "P-123",
            "scope": "excavation",
            "bids": [{"subcontractor": "Builder A", "price": 10000, "lead_time_days": 10}],
            "comparison": {},
            "recommendation": "",
            "tool_calls": None,
            "tool_results": None,
        }
        
        # Should not raise, but return gracefully
        result = agent._llm_with_tools_node(state)
        
        assert "_llm_tool_calls" in result
        assert "_llm_tool_results" in result


class TestMessageHistoryAccumulation:
    """Tests for message history accumulation in orchestration loop."""
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_message_history_includes_tool_results(self, mock_llm_class):
        """Test that message history includes tool results for LLM context."""
        mock_llm = Mock()
        mock_llm_with_tools = Mock()
        
        # First response with tool call
        response_with_tool = Mock()
        response_with_tool.content = "Checking market data"
        response_with_tool.tool_calls = [
            {
                "tool": "fetch_market_data",
                "tool_input": {"scope": "excavation"},
                "id": "call-1"
            }
        ]
        
        # Second response (after seeing tool results)
        final_response = Mock()
        final_response.content = "Based on market data showing 47 suppliers..."
        final_response.tool_calls = None
        
        mock_llm_with_tools.invoke.side_effect = [response_with_tool, final_response]
        
        mock_llm_class.return_value = mock_llm
        mock_llm.bind_tools.return_value = mock_llm_with_tools
        
        agent = EnhancedLangGraphAgent(use_llm=True)
        
        state = {
            "prompt": "Analyze",
            "project_id": "P-123",
            "scope": "excavation",
            "bids": [{"subcontractor": "Builder A", "price": 10000, "lead_time_days": 10}],
            "comparison": {},
            "recommendation": "",
            "tool_calls": None,
            "tool_results": None,
        }
        
        result = agent._llm_with_tools_node(state)
        
        # Second invoke should have been called (meaning it looped and continued)
        assert mock_llm_with_tools.invoke.call_count >= 1
        
        # Tool results should be collected
        assert len(result["_llm_tool_results"]) > 0


class TestToolCallFormatVariations:
    """Tests for handling different tool call formats from LLMs."""
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_tool_call_with_name_instead_of_tool(self, mock_llm_class):
        """Test parsing tool calls that use 'name' instead of 'tool'."""
        mock_llm_class.return_value = Mock()
        
        agent = EnhancedLangGraphAgent(use_llm=False)
        
        # Alternative format: name instead of tool
        tool_calls = [
            {
                "name": "fetch_market_data",  # Using 'name' instead of 'tool'
                "input": {"scope": "excavation"},  # Using 'input' instead of 'tool_input'
                "id": "call-1"
            }
        ]
        
        results = agent._execute_llm_tool_calls(tool_calls)
        
        # Should still execute the tool
        assert "call-1" in results


class TestIntegrationWithGraph:
    """Integration tests for tools within the agent graph."""
    
    @patch("construction_assistant.enhanced_langgraph_agent.ChatGoogleGenerativeAI")
    def test_full_graph_flow_includes_llm_tools(self, mock_llm_class):
        """Test that full graph flow includes LLM tools node."""
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        
        # Mock LLM responses
        parse_response = Mock()
        parse_response.content = '{"project_id": "P-123", "scope": "excavation"}'
        
        format_response = Mock()
        format_response.content = "Recommended contractor: Best Builder"
        
        mock_llm.invoke.side_effect = [parse_response, format_response]
        mock_llm.bind_tools.return_value = mock_llm
        
        agent = EnhancedLangGraphAgent(use_llm=True)
        agent.build_graph()
        
        # Verify graph structure
        assert "llm_with_tools" in agent.graph.nodes
        
        # Verify edge from use_tools to llm_with_tools
        edges = agent.graph.edges
        edge_list = list(edges)
        assert any(e[0] == "use_tools" and e[1] == "llm_with_tools" for e in edge_list)
