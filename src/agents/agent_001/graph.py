from langgraph.graph import StateGraph, START, END

from logging import getLogger

from .state import Agent001State
from .nodes import WelcomeNode

logger = getLogger(__name__)


class Agent001(StateGraph):
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.graph = StateGraph(Agent001State)
        self.compiled_graph = None

    def build(self):
        welcome_node = WelcomeNode(self.agent_name)
        self.graph.add_node("welcome_node", welcome_node)
        self.graph.add_edge(START, "welcome_node")
        self.graph.add_edge("welcome_node", END)
        self.compiled_graph = self.graph.compile(debug=True)

    def run(self, state: Agent001State):
        if self.compiled_graph is None:
            logger.info("Graph not compiled, compiling now...")
            self.build()
        return self.compiled_graph.invoke(state)
