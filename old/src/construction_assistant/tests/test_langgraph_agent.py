from unittest.mock import Mock, patch
from construction_assistant import LangGraphAgent


def test_langgraph_agent_builds_graph():
    """Test that agent can build and compile a StateGraph."""
    with patch("construction_assistant.langgraph_agent.ChatGoogleGenerativeAI"):
        agent = LangGraphAgent(api_key="dummy")
        agent.build_graph()
        assert agent.compiled_graph is not None
        assert "parse" in agent.graph.nodes
        assert "fetch" in agent.graph.nodes
        assert "compare" in agent.graph.nodes
        assert "format" in agent.graph.nodes


def test_langgraph_agent_runs_full_flow():
    """Test end-to-end execution of the agent on a procurement request."""
    with patch("construction_assistant.langgraph_agent.ChatGoogleGenerativeAI") as mock_llm_class:
        # Mock the LLM instance
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        
        # Mock parse response: extract project_id and scope as JSON
        parse_response = Mock()
        parse_response.content = '{"project_id": "P-123", "scope": "foundation works"}'
        
        # Mock format response: format a professional recommendation
        format_response = Mock()
        format_response.content = "Recommendation: Choose contractor with best value and timeline."
        
        # Set up side effects to return different responses for parse vs format
        mock_llm.invoke.side_effect = [parse_response, format_response]
        
        agent = LangGraphAgent(api_key="dummy", top_n=2)
        result = agent.run("Get subcontractor bids for foundation works on project P-123")
        
        assert isinstance(result, dict)
        assert "prompt" in result
        assert "recommendation" in result
        assert "Recommendation" in result["recommendation"]
        assert isinstance(result.get("top_bids", []), list)
        # Should have found project ID from mock LLM
        assert result.get("project_id") == "P-123"

