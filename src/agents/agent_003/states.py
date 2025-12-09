from typing import TypedDict, Annotated
import operator

from langchain.messages import AnyMessage
from langgraph.graph.message import add_messages, MessagesState


class InputState(TypedDict):
    user: str
    question: str


class OutputState(TypedDict):
    answer: str


class Agent003State(MessagesState):
    user: str
    question: str
    answer: str
