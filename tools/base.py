from __future__ import annotations

import typing

from abc import ABC, abstractmethod
from typing import Any

if typing.TYPE_CHECKING:
    from tools.context import ToolContext


class Tool(ABC):
    name: str = ""
    description: str = ""
    params: dict = {}

    @classmethod
    def create(cls, ctx: ToolContext) -> Tool:
        return cls()

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