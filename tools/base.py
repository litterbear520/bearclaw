from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    name: str = ""
    description: str = ""
    params: dict = {}

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        pass
    
    def to_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.params,
            }
        }