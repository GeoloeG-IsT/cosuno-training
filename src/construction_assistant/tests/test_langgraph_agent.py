from construction_assistant import LangGraphAgent


def test_langgraph_agent_builds_graph():
    """Test that agent can build and compile a StateGraph."""
    agent = LangGraphAgent(api_key="dummy")
    agent.build_graph()
    assert agent.compiled_graph is not None
    assert "parse" in agent.graph.nodes
    assert "fetch" in agent.graph.nodes
    assert "compare" in agent.graph.nodes
    assert "format" in agent.graph.nodes


def test_langgraph_agent_runs_full_flow():
    """Test end-to-end execution of the agent on a procurement request."""
    agent = LangGraphAgent(api_key="dummy", top_n=2)
    result = agent.run("Get subcontractor bids for foundation works on project P-123")
    
    assert isinstance(result, dict)
    assert "prompt" in result
    assert "recommendation" in result
    assert "Recommendation" in result["recommendation"]
    assert isinstance(result.get("top_bids", []), list)
    # Should have found project ID
    assert result.get("project_id") == "P-123"

