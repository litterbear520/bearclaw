from anthropic import Anthropic
from typing import Any
from providers.base import LLMProvider, LLMResponse, ToolCallRequest


class AnthropicProvider(LLMProvider):
    def __init__(
        self, 
        api_key: str | None = None, 
        base_url: str | None = None,
        default_model: str = "claude-sonnet-4-20250514"
        ):
        super().__init__(api_key, base_url)
        self.default_model = default_model
        self._client = Anthropic(api_key=api_key, base_url=base_url)

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int =4096,
    ) -> LLMResponse:
        system, chat_messages = self._convert_messages(messages)

        kwargs: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": chat_messages,
            "max_tokens": max_tokens
        }
        if system:
            kwargs["system"] = system
        anthropic_tools = self._convert_tools(tools)
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        response = self._client.messages.create(**kwargs)
        return self._parse_response(response)

    def _convert_messages(self, messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
        system = ""
        result: list[dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role")

            if role == "system":
                system = msg["content"]

            elif role == "tool":
                block = {
                    "type": "tool_result",
                    "tool_use_id": msg["tool_call_id"],
                    "content": msg["content"],
                }
                if result and result[-1]["role"] == "user":
                    result[-1]["content"].append(block)
                else:
                    result.append({"role": "user", "content": [block]})

            elif role == "assistant" and msg.get("tool_calls"):
                blocks: list[dict[str, Any]] = []
                if msg.get("content"):
                    blocks.append({"type": "text", "text": msg["content"]})
                for tc in msg["tool_calls"]:
                    blocks.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": tc["function"]["arguments"]
                    })
                result.append({"role": "assistant", "content": blocks})
            
            else:
                result.append(msg)

        return system, result

    @staticmethod
    def _convert_tools(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        result = []
        for tool in tools:
            func = tool.get("function", tool)
            entry: dict[str, Any] = {
                "name": func.get("name", ""),
                "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
            }
            desc = func.get("description")
            if desc:
                entry["description"] = desc
            result.append(entry)
        return result

    @staticmethod
    def _parse_response(response: Any) -> LLMResponse:
        content_parts: list[str] = []
        tool_calls: list[ToolCallRequest] = []

        for block in response.content:
            if block.type == "text":
                content_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCallRequest(
                    id = block.id,
                    name = block.name,
                    args=block.input
                ))

        stop_map = {"tool_use": "tool_calls", "end_turn": "stop", "max_tokens": "length"}
        finish_reason = stop_map.get(response.stop_reason or "", response.stop_reason or "stop")

        return LLMResponse(
            content="".join(content_parts) or None,
            tool_calls=tool_calls,
            finish_reason=finish_reason
        )