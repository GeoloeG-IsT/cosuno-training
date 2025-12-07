from typing import TypedDict


class AgentState(TypedDict):
    """Defines the state schema for the Cosuno agent graph."""
    prompt: str
    project_id: str | None
    scope: str | None
    bids: list
    comparison: dict
    recommendation: str
    # Tool usage fields
    tool_calls: list[dict] | None
    tool_results: dict | None

