from langgraph.graph import StateGraph, START, END

from logging import getLogger

from .states import InputState, Agent003State, OutputState
from .nodes import AnswerNode, ToolNode

logger = getLogger(__name__)


class Agent003(StateGraph):
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.graph = StateGraph(Agent003State)
        self.compiled_graph = None

    def answer_action(state: Agent003State) -> str:
        last_answer = state["messages"][-1]["content"]
        if "calculate" in last_answer.lower() or "compute" in last_answer.lower():
            return "Use Tool"
        return "No Tool Needed"

    def build(self):
        answer_node = AnswerNode(self.agent_name)
        self.graph.add_node("answer_node", answer_node)
        tool_node = ToolNode("tool_node")
        self.graph.add_node("tool_node", tool_node)
        self.graph.add_edge(START, "answer_node")
        self.graph.add_conditional_edges(
            "answer_node",
            self.answer_action,
            {"Use Tool": "tool_node", "No Tool Needed": END},
        )
        self.compiled_graph = self.graph.compile(debug=True)

    def run(self, state: InputState) -> OutputState:
        if self.compiled_graph is None:
            logger.info("Graph not compiled, compiling now...")
            self.build()
        return self.compiled_graph.invoke(state)
