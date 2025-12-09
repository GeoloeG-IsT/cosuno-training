from langgraph.graph import StateGraph, START, END

from logging import getLogger

from .states import InputState, Agent002State, OutputState
from .nodes import AnswerNode

logger = getLogger(__name__)


class Agent002(StateGraph):
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.graph = StateGraph(Agent002State)
        self.compiled_graph = None

    def build(self):
        answer_node = AnswerNode(self.agent_name)
        self.graph.add_node("answer_node", answer_node)
        self.graph.add_edge(START, "answer_node")
        self.graph.add_edge("answer_node", END)
        self.compiled_graph = self.graph.compile(debug=True)

    def run(self, state: InputState) -> OutputState:
        if self.compiled_graph is None:
            logger.info("Graph not compiled, compiling now...")
            self.build()
        return self.compiled_graph.invoke(state)
