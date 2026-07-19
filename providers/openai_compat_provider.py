import json

from typing import Any
from openai import OpenAI

from providers.base import LLMProvider, LLMResponse, ToolCallRequest


class OpenAICompatProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = "deepseek-v4-flash",
    ):
        super().__init__(api_key, base_url)
        self.default_model = default_model
        self._client = OpenAI(api_key=api_key or "no key", base_url=base_url)

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "max_tokens": max_tokens
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self._client.chat.completions.create(**kwargs)
        return self._parse(response)

    def _parse(self, response: Any) -> LLMResponse:
        if not response.choices:
            return LLMResponse(content="Error: API returned empty choices.", finish_reason="error")

        choice = response.choices[0]
        msg = choice.message
        content = msg.content
        finish_reason = choice.finish_reason or "stop"

        tool_calls: list[ToolCallRequest] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                args = tc.function.arguments
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                tool_calls.append(ToolCallRequest(
                    id=tc.id,
                    name=tc.function.name,
                    args=args
                ))
            
        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason
        )