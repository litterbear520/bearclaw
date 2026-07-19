from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCallRequest:
    id: str
    name: str
    args: Any


@dataclass
class LLMResponse:
    content: str | None = None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    finish_reason: str = "stop"

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class LLMProvider(ABC):
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    def chat(
        self, 
        messages: list[dict[str, Any]], 
        tools: list[dict], 
        model: str | None = None, 
        max_tokens: int = 4096
    ) -> LLMResponse:
        pass