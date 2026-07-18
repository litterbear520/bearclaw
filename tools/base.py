from abc import ABC, abstractmethod


class Tool(ABC):
    name: str = ""
    description: str = ""
    params: dict = {}

    @abstractmethod
    def run(self, **kwargs: str) -> str:
        pass
    
    def to_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.params
        }