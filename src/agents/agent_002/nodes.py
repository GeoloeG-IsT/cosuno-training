from langchain_mistralai import ChatMistralAI

from .states import Agent002State, OutputState


class AnswerNode:
    def __init__(self, name: str):
        self.name = name
        self.llm = ChatMistralAI(model="ministral-3b-latest", temperature=0.0)

    def __call__(self, state: Agent002State) -> OutputState:
        prompt = f"User {state['user']} asked: {state['question']}. Provide a concise and accurate answer."
        response = self.llm.invoke(prompt)
        return {"answer": response.content}
