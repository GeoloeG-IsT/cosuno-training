from langchain_mistralai import ChatMistralAI

from .states import Agent003State, OutputState
from .tools import add_numbers, multiply_numbers


class AnswerNode:
    def __init__(self, name: str):
        self.name = name
        self.llm = ChatMistralAI(model="mistral-large-2512", temperature=0.0)
        self.llm.bind_tools([add_numbers, multiply_numbers])

    def __call__(self, state: Agent003State) -> OutputState:
        prompt = f"User {state['user']} asked: {state['question']}. Provide a concise and accurate answer."
        response = self.llm.invoke(prompt)
        return {"answer": response.content}


class ToolNode:
    def __init__(self, name: str):
        self.name = name
        self.llm = ChatMistralAI(model="mistral-large-2512", temperature=0.0)
        self.llm.bind_tools([add_numbers, multiply_numbers])

    def __call__(self, state: Agent003State) -> Agent003State:
        response = self.llm.invoke(state["messages"][-1])
        state["messages"].append({"role": "assistant", "content": response.content})
        return state
