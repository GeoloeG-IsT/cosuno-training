from .state import Agent001State


class WelcomeNode:
    def __init__(self, name: str):
        self.name = name

    def __call__(self, state: Agent001State) -> Agent001State:
        return {"welcome": f"Welcome {state["user"]}, I am {self.name}!"}
