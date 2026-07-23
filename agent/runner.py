from dataclasses import dataclass, field
from typing import Any

from providers.base import LLMProvider
from tools.registry import ToolRegistry


@dataclass
class AgentRunSpec:
    initial_messages: list[dict[str, Any]]
    tools: ToolRegistry
    provider: LLMProvider
    max_iterations: int = 50


@dataclass
class AgentRunResult:
    final_content: str | None
    messages: list[dict[str, Any]] = field(default_factory=list)


class AgentRunner:

    def run(self, spec: AgentRunSpec) -> AgentRunResult:

        messages = list(spec.initial_messages)

        for iteration in range(spec.max_iterations):
            response = spec.provider.chat(
                tools=spec.tools.get_schema(),
                messages=messages,
                max_tokens=10000,
            )
            ai_msg = {"role": "assistant", "content": response.content}
            if response.tool_calls:
                ai_msg["tool_calls"] = [
                    {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": tc.args}}
                    for tc in response.tool_calls
                ]
            messages.append(ai_msg)

            if response.finish_reason != "tool_calls":
                return AgentRunResult(
                    final_content=response.content,
                    messages=messages
                )

            for tc in response.tool_calls:
                print(f"使用工具：{tc.name}, 参数：{tc.args}")
                output = spec.tools.run(tc.name, **(tc.args if isinstance(tc.args, dict) else {}))
                print(f"工具结果：{output}")
                tool_msg = {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.name,
                    "content": output,
                }
                messages.append(tool_msg)

        return AgentRunResult(final_content=None, messages=messages)